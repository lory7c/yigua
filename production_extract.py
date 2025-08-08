#!/usr/bin/env python3
"""
生产级易学PDF文档批量提取管道 - Production Extract Pipeline
整合最佳提取方法、并发处理、断点续传、标准化输出

基于ETL_Architecture_Design.md方案实现
- pdfplumber+PyMuPDF双重提取
- multiprocessing并发批处理
- 智能断点续传机制
- 标准化JSON输出格式
- 实时进度监控和错误处理
- 内存优化和性能调优

目标: 191个PDF文件，3小时内完成处理
"""

import os
import sys
import json
import re
import time
import pickle
import hashlib
import logging
import multiprocessing as mp
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, NamedTuple
from dataclasses import dataclass, asdict
from concurrent.futures import ProcessPoolExecutor, as_completed
import signal
import psutil
import gc
import resource
from collections import defaultdict, deque

# PDF处理库
try:
    import pdfplumber
    import fitz  # PyMuPDF
    import PyPDF2
    from tqdm import tqdm
    import pandas as pd
    from functools import lru_cache
except ImportError as e:
    print(f"缺少依赖库: {e}")
    print("请安装: pip install pdfplumber pymupdf tqdm pandas")
    sys.exit(1)


# ============================================================================
# 数据结构定义
# ============================================================================

@dataclass
class ProcessingConfig:
    """处理配置"""
    source_dir: str
    output_dir: str
    max_workers: int = 6
    batch_size: int = 8
    memory_limit_gb: float = 3.0
    time_limit_hours: float = 3.0
    cache_enabled: bool = True
    resume_enabled: bool = True
    min_text_length: int = 50
    max_pages_per_file: int = 500
    
@dataclass
class FileMetadata:
    """文件元数据"""
    file_path: str
    file_name: str
    file_size: int
    file_hash: str
    pages: int
    category: str
    priority: int
    confidence: float
    processing_time: float
    processed_at: str
    method_used: str

@dataclass 
class ExtractionResult:
    """提取结果"""
    metadata: FileMetadata
    raw_text: str
    structured_content: Dict[str, Any]
    statistics: Dict[str, int]
    quality_metrics: Dict[str, float]
    error_log: List[str]

class ProcessingProgress(NamedTuple):
    """处理进度"""
    completed: int
    total: int
    success: int
    failed: int
    cached: int
    elapsed_time: float
    estimated_remaining: float


# ============================================================================
# 核心提取引擎
# ============================================================================

class ProductionPDFExtractor:
    """生产级PDF提取器 - 多方法融合"""
    
    def __init__(self, config: ProcessingConfig):
        self.config = config
        self.logger = self._setup_logging()
        
        # 64卦名称和易学术语
        self.hexagram_names = [
            "乾", "坤", "屯", "蒙", "需", "讼", "师", "比",
            "小畜", "履", "泰", "否", "同人", "大有", "谦", "豫",
            "随", "蛊", "临", "观", "噬嗑", "贲", "剥", "复",
            "无妄", "大畜", "颐", "大过", "坎", "离", "咸", "恒",
            "遁", "大壮", "晋", "明夷", "家人", "睽", "蹇", "解",
            "损", "益", "夬", "姤", "萃", "升", "困", "井",
            "革", "鼎", "震", "艮", "渐", "归妹", "丰", "旅",
            "巽", "兑", "涣", "节", "中孚", "小过", "既济", "未济"
        ]
        
        # 分类模式 - 精确匹配
        self.category_patterns = {
            "六爻": {
                "keywords": ["六爻", "卜易", "增删", "火珠林", "黄金策", "筮", "卦象", "爻辞", "世应", "六亲"],
                "priority": 1,
                "patterns": [r"六爻", r"世应", r"用神", r"忌神", r"动爻", r"变爻", r"飞神", r"伏神"]
            },
            "大六壬": {
                "keywords": ["六壬", "壬学", "壬占", "课传", "神将", "四课", "三传", "十二神"],
                "priority": 1,
                "patterns": [r"六壬", r"课传", r"四课", r"三传", r"天罡", r"太冲"]
            },
            "周易基础": {
                "keywords": ["周易", "易经", "八卦", "六十四卦", "卦辞", "象传", "彖传"],
                "priority": 1,
                "patterns": [r"周易", r"易经", r"八卦", r"卦辞", r"象传", r"彖传"]
            },
            "梅花易数": {
                "keywords": ["梅花", "易数", "观梅", "数理", "先天", "后天", "体用"],
                "priority": 2,
                "patterns": [r"梅花.{0,3}易", r"观梅", r"体卦", r"用卦", r"互卦", r"变卦"]
            },
            "紫微斗数": {
                "keywords": ["紫微", "斗数", "命盘", "宫位", "星曜", "主星", "化禄", "化权", "化科", "化忌"],
                "priority": 2,
                "patterns": [r"紫微.{0,3}斗数", r"命宫", r"身宫", r"十二宫", r"十四主星"]
            },
            "奇门遁甲": {
                "keywords": ["奇门", "遁甲", "九宫", "八门", "三奇", "六仪", "值符", "值使"],
                "priority": 2,
                "patterns": [r"奇门.{0,3}遁甲", r"九宫", r"八门", r"三奇六仪", r"值符", r"值使"]
            },
            "八字命理": {
                "keywords": ["八字", "四柱", "命理", "干支", "纳音", "十神", "用神", "喜用神"],
                "priority": 2,
                "patterns": [r"八字", r"四柱", r"十神", r"食神", r"伤官", r"正财", r"偏财"]
            },
            "金口诀": {
                "keywords": ["金口诀", "金口", "课式", "立课", "四位", "贵神"],
                "priority": 3,
                "patterns": [r"金口.{0,3}诀", r"立课", r"四位", r"贵神"]
            },
            "其他术数": {
                "keywords": ["太乙", "河洛", "风水", "相术", "占卜", "预测"],
                "priority": 4,
                "patterns": [r"太乙", r"河洛", r"理数", r"河图", r"洛书"]
            }
        }
        
        # 性能监控
        self._method_performance = defaultdict(lambda: {"success": 0, "failure": 0, "total_time": 0.0})
        self._memory_usage_history = deque(maxlen=100)
        
    def _setup_logging(self) -> logging.Logger:
        """设置日志系统"""
        log_dir = Path(self.config.output_dir) / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        
        logger = logging.getLogger("ProductionExtractor")
        logger.setLevel(logging.INFO)
        
        # 清除现有的handler
        for handler in logger.handlers:
            logger.removeHandler(handler)
        
        # 文件handler
        file_handler = logging.FileHandler(
            log_dir / f"production_extract_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log",
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        
        # 控制台handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # 格式化
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
        return logger
    
    def get_file_hash(self, file_path: Path) -> str:
        """计算文件哈希"""
        stat = file_path.stat()
        content = f"{file_path}_{stat.st_size}_{stat.st_mtime}_{stat.st_ctime}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def extract_with_pdfplumber(self, pdf_path: Path) -> Tuple[str, Dict[str, Any]]:
        """pdfplumber提取 - 主要方法"""
        start_time = time.time()
        text_parts = []
        metadata = {
            'method': 'pdfplumber',
            'pages_processed': [],
            'tables_extracted': 0,
            'errors': []
        }
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                total_pages = len(pdf.pages)
                metadata['total_pages'] = total_pages
                max_pages = min(total_pages, self.config.max_pages_per_file)
                
                for i in range(max_pages):
                    try:
                        page = pdf.pages[i]
                        
                        # 优化参数的文本提取
                        page_text = page.extract_text(
                            x_tolerance=3,
                            y_tolerance=3,
                            layout=True,
                            use_text_flow=True
                        )
                        
                        if page_text and len(page_text.strip()) > 20:
                            text_parts.append(page_text)
                            metadata['pages_processed'].append(i + 1)
                        
                        # 表格提取 - 仅前50页，避免性能问题
                        if i < 50 and len(page_text.strip()) < 2000:
                            try:
                                tables = page.extract_tables()
                                for table in tables[:2]:  # 最多2个表格
                                    if len(table) <= 30:  # 避免巨大表格
                                        table_text = self._format_table(table)
                                        if table_text:
                                            text_parts.append(f"\n[表格{metadata['tables_extracted']+1}]\n{table_text}\n[/表格]\n")
                                            metadata['tables_extracted'] += 1
                            except Exception as e:
                                metadata['errors'].append(f"表格提取失败 页{i+1}: {str(e)}")
                        
                        # 内存管理
                        if i > 0 and i % 50 == 0:
                            gc.collect()
                            
                    except Exception as e:
                        metadata['errors'].append(f"页面{i+1}处理失败: {str(e)}")
                        continue
                
                if max_pages < total_pages:
                    metadata['truncated_pages'] = total_pages - max_pages
                    
        except Exception as e:
            raise Exception(f"pdfplumber处理失败: {e}")
        
        full_text = '\n'.join(text_parts)
        processing_time = time.time() - start_time
        
        # 记录性能
        self._method_performance['pdfplumber']['total_time'] += processing_time
        self._method_performance['pdfplumber']['success'] += 1
        
        metadata.update({
            'processing_time': processing_time,
            'text_length': len(full_text),
            'pages_ratio': len(metadata['pages_processed']) / total_pages if total_pages > 0 else 0
        })
        
        return full_text, metadata
    
    def extract_with_pymupdf(self, pdf_path: Path) -> Tuple[str, Dict[str, Any]]:
        """PyMuPDF提取 - 备选方法"""
        start_time = time.time()
        text_parts = []
        metadata = {
            'method': 'pymupdf',
            'pages_processed': [],
            'images_processed': 0,
            'errors': []
        }
        
        doc = None
        try:
            doc = fitz.open(pdf_path)
            total_pages = len(doc)
            metadata['total_pages'] = total_pages
            max_pages = min(total_pages, self.config.max_pages_per_file)
            
            for page_num in range(max_pages):
                try:
                    page = doc.load_page(page_num)
                    
                    # 文本提取
                    page_text = page.get_text("text", 
                                            flags=fitz.TEXT_PRESERVE_WHITESPACE | fitz.TEXT_PRESERVE_IMAGES)
                    
                    if page_text and len(page_text.strip()) > 15:
                        text_parts.append(page_text)
                        metadata['pages_processed'].append(page_num + 1)
                    
                    # 图片文字识别 - 仅前20页，文字少的页面
                    elif len(page_text.strip()) < 50 and page_num < 20:
                        try:
                            # 简单图片转文字（不依赖OCR）
                            image_list = page.get_images()
                            if image_list:
                                metadata['images_processed'] += len(image_list)
                                # 这里可以添加OCR逻辑，但为保持性能暂时跳过
                        except Exception as e:
                            metadata['errors'].append(f"图片处理失败 页{page_num+1}: {str(e)}")
                    
                    # 内存管理
                    if page_num > 0 and page_num % 100 == 0:
                        gc.collect()
                        
                except Exception as e:
                    metadata['errors'].append(f"页面{page_num+1}处理失败: {str(e)}")
                    continue
            
            if max_pages < total_pages:
                metadata['truncated_pages'] = total_pages - max_pages
                
        finally:
            if doc:
                doc.close()
        
        full_text = '\n'.join(text_parts)
        processing_time = time.time() - start_time
        
        # 记录性能
        self._method_performance['pymupdf']['total_time'] += processing_time
        self._method_performance['pymupdf']['success'] += 1
        
        metadata.update({
            'processing_time': processing_time,
            'text_length': len(full_text),
            'pages_ratio': len(metadata['pages_processed']) / total_pages if total_pages > 0 else 0
        })
        
        return full_text, metadata
    
    def extract_with_pypdf2(self, pdf_path: Path) -> Tuple[str, Dict[str, Any]]:
        """PyPDF2提取 - 最后备选"""
        start_time = time.time()
        text_parts = []
        metadata = {
            'method': 'pypdf2',
            'pages_processed': [],
            'errors': []
        }
        
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                total_pages = len(pdf_reader.pages)
                metadata['total_pages'] = total_pages
                max_pages = min(total_pages, 100)  # PyPDF2性能较慢，限制更少页数
                
                for i in range(max_pages):
                    try:
                        page = pdf_reader.pages[i]
                        page_text = page.extract_text()
                        
                        if page_text and len(page_text.strip()) > 10:
                            text_parts.append(page_text)
                            metadata['pages_processed'].append(i + 1)
                            
                    except Exception as e:
                        metadata['errors'].append(f"页面{i+1}处理失败: {str(e)}")
                        continue
                
                if max_pages < total_pages:
                    metadata['truncated_pages'] = total_pages - max_pages
                    
        except Exception as e:
            raise Exception(f"PyPDF2处理失败: {e}")
        
        full_text = '\n'.join(text_parts)
        processing_time = time.time() - start_time
        
        # 记录性能
        self._method_performance['pypdf2']['total_time'] += processing_time
        self._method_performance['pypdf2']['success'] += 1
        
        metadata.update({
            'processing_time': processing_time,
            'text_length': len(full_text),
            'pages_ratio': len(metadata['pages_processed']) / total_pages if total_pages > 0 else 0
        })
        
        return full_text, metadata
    
    def _format_table(self, table) -> str:
        """格式化表格数据"""
        try:
            formatted_rows = []
            for row in table:
                if row and any(cell for cell in row):
                    formatted_row = '\t'.join([
                        str(cell).strip() if cell is not None else '' 
                        for cell in row
                    ])
                    if formatted_row.strip():
                        formatted_rows.append(formatted_row)
            return '\n'.join(formatted_rows)
        except Exception:
            return ''
    
    def classify_content(self, text: str, filename: str) -> Tuple[str, float, int]:
        """智能分类算法"""
        if not text:
            return "其他术数", 0.0, 5
        
        text_lower = text.lower()
        filename_lower = filename.lower()
        
        category_scores = {}
        
        for category, config in self.category_patterns.items():
            score = 0.0
            
            # 文件名匹配 (权重高)
            filename_matches = sum(1 for kw in config["keywords"] if kw in filename_lower)
            score += filename_matches * 5.0
            
            # 正则模式匹配
            for pattern in config["patterns"]:
                matches = len(re.findall(pattern, text, re.IGNORECASE))
                score += matches * 2.0
            
            # 关键词密度
            total_keywords = sum(text_lower.count(kw) for kw in config["keywords"])
            if len(text) > 100:
                density = (total_keywords / len(text)) * 10000
                score += density
            
            # 特殊加分项
            if category == "六爻" and any(name in text for name in ["王虎应", "增删卜易", "火珠林"]):
                score += 10.0
            elif category == "周易基础" and any(name in text for name in self.hexagram_names[:10]):
                score += 8.0
            elif category == "大六壬" and "壬占" in text:
                score += 8.0
            
            category_scores[category] = score
        
        if not category_scores or max(category_scores.values()) == 0:
            return "其他术数", 0.0, 5
        
        best_category = max(category_scores, key=category_scores.get)
        best_score = category_scores[best_category]
        
        # 归一化置信度
        confidence = min(best_score / 20.0, 1.0)
        priority = self.category_patterns[best_category]["priority"]
        
        return best_category, confidence, priority
    
    def extract_structured_content(self, text: str) -> Dict[str, Any]:
        """提取结构化内容"""
        content = {
            "hexagrams": [],
            "yao_ci": [],
            "annotations": [],
            "cases": [],
            "keywords": [],
            "author": None,
            "dynasty": None
        }
        
        # 提取64卦信息
        for i, name in enumerate(self.hexagram_names):
            patterns = [
                rf"(?:第?\s*)?{name}[卦]?[：:]\s*([^。\n]{10,200})",
                rf"{name}[卦]?\s*([^。\n]{20,100})"
            ]
            
            for pattern in patterns:
                matches = re.finditer(pattern, text)
                for match in matches:
                    description = match.group(1).strip()
                    if len(description) >= 10:
                        content["hexagrams"].append({
                            "number": i + 1,
                            "name": name,
                            "description": description,
                            "position": match.start()
                        })
                        break
        
        # 提取爻辞
        yao_positions = ["初", "二", "三", "四", "五", "上"]
        yao_types = ["六", "九"]
        
        for pos in yao_positions:
            for yao_type in yao_types:
                pattern = rf"({pos}{yao_type})[：:]\s*([^。\n]{10,200})"
                matches = re.finditer(pattern, text)
                
                for match in matches:
                    content["yao_ci"].append({
                        "position": pos,
                        "type": yao_type,
                        "full_name": match.group(1),
                        "text": match.group(2).strip(),
                        "location": match.start()
                    })
        
        # 提取注解
        annotation_patterns = [
            (r"注[：:]\s*([^。\n]{15,300})", "注"),
            (r"解[：:]\s*([^。\n]{15,300})", "解"), 
            (r"释[：:]\s*([^。\n]{15,300})", "释"),
            (r"按[：:]\s*([^。\n]{15,300})", "按"),
            (r"曰[：:]\s*([^。\n]{15,300})", "曰")
        ]
        
        for pattern, ann_type in annotation_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                content["annotations"].append({
                    "type": ann_type,
                    "content": match.group(1).strip(),
                    "position": match.start()
                })
        
        # 提取案例
        case_patterns = [
            r"例[一二三四五六七八九十\d]*[：:]\s*([^。]{50,800})",
            r"案例[：:]\s*([^。]{50,800})",
            r"实例[：:]\s*([^。]{50,800})",
            r"占例[：:]\s*([^。]{50,800})"
        ]
        
        for pattern in case_patterns:
            matches = re.finditer(pattern, text, re.DOTALL)
            for match in matches:
                case_text = match.group(1).strip()
                if len(case_text) >= 50:
                    content["cases"].append({
                        "content": case_text,
                        "position": match.start(),
                        "length": len(case_text)
                    })
        
        # 提取关键词
        keyword_terms = [
            "阴阳", "五行", "八卦", "太极", "无极", "先天", "后天",
            "占卜", "预测", "命理", "相术", "风水", "择日",
            "世应", "六亲", "用神", "忌神", "元神", "仇神",
            "动爻", "变爻", "飞神", "伏神", "月建", "日建",
            "子孙", "妻财", "兄弟", "官鬼", "父母",
            "青龙", "朱雀", "勾陈", "螣蛇", "白虎", "玄武"
        ]
        
        found_keywords = []
        for term in keyword_terms:
            if term in text:
                found_keywords.append(term)
        
        # 提取书名
        book_names = re.findall(r'《([^》]{2,30})》', text)
        found_keywords.extend(book_names[:5])
        
        content["keywords"] = list(set(found_keywords))
        
        # 提取作者信息（简化版）
        author_patterns = [
            r'(?:著|撰|编)[者]?[：:]?\s*([王李张刘陈杨赵黄周吴徐孙胡朱高林何郭马][\u4e00-\u9fff]{1,3})',
            r'([王李张刘陈杨赵黄周吴徐孙胡朱高林何郭马][\u4e00-\u9fff]{1,3})\s*(?:著|撰|编)'
        ]
        
        for pattern in author_patterns:
            match = re.search(pattern, text)
            if match:
                content["author"] = match.group(1)
                break
        
        # 提取朝代
        dynasty_patterns = [
            r'[(（]?(汉|唐|宋|元|明|清)[朝代)）]?',
            r'(汉|唐|宋|元|明|清)[·•]',
            r'(汉|唐|宋|元|明|清)代'
        ]
        
        for pattern in dynasty_patterns:
            match = re.search(pattern, text)
            if match:
                content["dynasty"] = match.group(1)
                break
        
        return content
    
    def calculate_quality_metrics(self, text: str, metadata: Dict[str, Any]) -> Dict[str, float]:
        """计算质量指标"""
        if not text:
            return {"overall": 0.0, "completeness": 0.0, "accuracy": 0.0, "relevance": 0.0}
        
        metrics = {}
        
        # 完整性评分
        text_length = len(text)
        page_ratio = metadata.get('pages_ratio', 0)
        completeness = min(1.0, (text_length / 5000) * 0.7 + page_ratio * 0.3)
        metrics["completeness"] = completeness
        
        # 准确性评分（基于中文字符比例和编码质量）
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
        chinese_ratio = chinese_chars / text_length if text_length > 0 else 0
        encoding_quality = 1.0 - (text.count('�') / max(text_length, 1))
        accuracy = chinese_ratio * 0.6 + encoding_quality * 0.4
        metrics["accuracy"] = accuracy
        
        # 相关性评分（基于易学术语密度）
        yixue_terms = ["易", "卦", "爻", "阴", "阳", "五行", "八卦", "占", "卜"]
        term_count = sum(text.count(term) for term in yixue_terms)
        term_density = term_count / max(text_length / 1000, 1)  # 每千字术语数
        relevance = min(1.0, term_density / 10)
        metrics["relevance"] = relevance
        
        # 综合评分
        overall = (completeness * 0.3 + accuracy * 0.4 + relevance * 0.3)
        metrics["overall"] = overall
        
        return metrics
    
    def process_single_file(self, file_path: Path) -> Optional[ExtractionResult]:
        """处理单个PDF文件 - 核心方法"""
        start_time = time.time()
        error_log = []
        
        try:
            self.logger.debug(f"开始处理: {file_path.name}")
            
            # 文件基本信息
            stat = file_path.stat()
            file_hash = self.get_file_hash(file_path)
            
            # 多方法提取，优先使用pdfplumber
            extraction_methods = [
                ("pdfplumber", self.extract_with_pdfplumber),
                ("pymupdf", self.extract_with_pymupdf), 
                ("pypdf2", self.extract_with_pypdf2)
            ]
            
            best_text = ""
            best_metadata = {}
            best_method = "failed"
            
            for method_name, method_func in extraction_methods:
                try:
                    text, metadata = method_func(file_path)
                    
                    if text and len(text.strip()) >= self.config.min_text_length:
                        # 选择最佳结果（文本长度 + 页面比例）
                        score = len(text) * metadata.get('pages_ratio', 0)
                        best_score = len(best_text) * best_metadata.get('pages_ratio', 0)
                        
                        if score > best_score:
                            best_text = text
                            best_metadata = metadata
                            best_method = method_name
                        
                        self.logger.debug(f"{method_name} 成功提取 {len(text)} 字符")
                        break  # 找到有效提取就使用，不需要尝试所有方法
                        
                except Exception as e:
                    error_msg = f"{method_name} 失败: {str(e)}"
                    error_log.append(error_msg)
                    self.logger.debug(error_msg)
                    self._method_performance[method_name]['failure'] += 1
                    continue
            
            if not best_text:
                error_log.append("所有提取方法均失败")
                return None
            
            # 内容分类
            category, confidence, priority = self.classify_content(best_text, file_path.name)
            
            # 提取结构化内容
            structured_content = self.extract_structured_content(best_text)
            
            # 计算质量指标
            quality_metrics = self.calculate_quality_metrics(best_text, best_metadata)
            
            # 统计信息
            statistics = {
                "text_length": len(best_text),
                "word_count": len(best_text.split()),
                "line_count": best_text.count('\n'),
                "hexagram_count": len(structured_content["hexagrams"]),
                "yao_ci_count": len(structured_content["yao_ci"]),
                "annotation_count": len(structured_content["annotations"]),
                "case_count": len(structured_content["cases"]),
                "keyword_count": len(structured_content["keywords"])
            }
            
            # 处理时间
            processing_time = time.time() - start_time
            
            # 创建文件元数据
            file_metadata = FileMetadata(
                file_path=str(file_path),
                file_name=file_path.name,
                file_size=stat.st_size,
                file_hash=file_hash,
                pages=best_metadata.get('total_pages', 0),
                category=category,
                priority=priority,
                confidence=confidence,
                processing_time=processing_time,
                processed_at=datetime.now().isoformat(),
                method_used=best_method
            )
            
            # 创建提取结果
            result = ExtractionResult(
                metadata=file_metadata,
                raw_text=best_text,
                structured_content=structured_content,
                statistics=statistics,
                quality_metrics=quality_metrics,
                error_log=error_log
            )
            
            self.logger.debug(f"完成处理: {file_path.name}, 耗时: {processing_time:.2f}s")
            return result
            
        except Exception as e:
            error_msg = f"处理失败 {file_path.name}: {str(e)}"
            error_log.append(error_msg)
            self.logger.error(error_msg)
            return None
        finally:
            # 内存管理
            gc.collect()


# ============================================================================
# 生产级批处理管道
# ============================================================================

class ProductionPipeline:
    """生产级处理管道"""
    
    def __init__(self, config: ProcessingConfig):
        self.config = config
        self.extractor = ProductionPDFExtractor(config)
        self.logger = self.extractor.logger
        
        # 创建输出目录结构
        self.output_dir = Path(config.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.raw_texts_dir = self.output_dir / "raw_texts"
        self.structured_data_dir = self.output_dir / "structured_data"
        self.categories_dir = self.output_dir / "categories"
        self.cache_dir = self.output_dir / "cache"
        self.reports_dir = self.output_dir / "reports"
        
        for dir_path in [self.raw_texts_dir, self.structured_data_dir, 
                        self.categories_dir, self.cache_dir, self.reports_dir]:
            dir_path.mkdir(exist_ok=True)
        
        # 缓存和断点续传
        self.cache_file = self.cache_dir / "processing_cache.pkl"
        self.progress_file = self.cache_dir / "progress.json"
        self.processed_cache = self._load_cache()
        
        # 性能监控
        self.start_time = None
        self.processed_count = 0
        self.failed_count = 0
        self.cached_count = 0
        
        # 信号处理（优雅退出）
        self._setup_signal_handlers()
    
    def _setup_signal_handlers(self):
        """设置信号处理器"""
        def signal_handler(signum, frame):
            self.logger.info(f"接收到信号 {signum}，正在安全退出...")
            self._save_cache()
            self._save_progress()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    def _load_cache(self) -> Dict[str, Any]:
        """加载缓存"""
        if not self.config.cache_enabled or not self.cache_file.exists():
            return {}
        
        try:
            with open(self.cache_file, 'rb') as f:
                cache_data = pickle.load(f)
                self.logger.info(f"加载缓存: {len(cache_data)} 个已处理文件")
                return cache_data
        except Exception as e:
            self.logger.warning(f"缓存加载失败: {e}")
            return {}
    
    def _save_cache(self):
        """保存缓存"""
        if not self.config.cache_enabled:
            return
        
        try:
            with open(self.cache_file, 'wb') as f:
                pickle.dump(self.processed_cache, f)
            self.logger.debug(f"缓存已保存: {len(self.processed_cache)} 个文件")
        except Exception as e:
            self.logger.error(f"缓存保存失败: {e}")
    
    def _save_progress(self):
        """保存进度"""
        progress_data = {
            "processed_count": self.processed_count,
            "failed_count": self.failed_count,
            "cached_count": self.cached_count,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "last_update": datetime.now().isoformat()
        }
        
        try:
            with open(self.progress_file, 'w', encoding='utf-8') as f:
                json.dump(progress_data, f, indent=2)
        except Exception as e:
            self.logger.error(f"进度保存失败: {e}")
    
    def _check_memory_usage(self) -> Dict[str, float]:
        """检查内存使用情况"""
        memory = psutil.virtual_memory()
        process = psutil.Process()
        
        return {
            "system_used_gb": memory.used / (1024**3),
            "system_available_gb": memory.available / (1024**3),
            "system_percent": memory.percent,
            "process_memory_gb": process.memory_info().rss / (1024**3),
            "memory_limit_gb": self.config.memory_limit_gb
        }
    
    def _should_reduce_workers(self, memory_info: Dict[str, float]) -> bool:
        """判断是否需要减少工作进程"""
        return (memory_info["process_memory_gb"] > self.config.memory_limit_gb * 0.8 or
                memory_info["system_percent"] > 85)
    
    def process_file_batch(self, pdf_files: List[Path]) -> List[Optional[ExtractionResult]]:
        """处理文件批次"""
        results = []
        
        # 检查缓存，过滤已处理文件
        unprocessed_files = []
        for pdf_file in pdf_files:
            file_hash = self.extractor.get_file_hash(pdf_file)
            if file_hash in self.processed_cache:
                results.append(self.processed_cache[file_hash])
                self.cached_count += 1
            else:
                unprocessed_files.append(pdf_file)
        
        if not unprocessed_files:
            return results
        
        # 内存检查和动态调整
        memory_info = self._check_memory_usage()
        if self._should_reduce_workers(memory_info):
            actual_workers = max(1, self.config.max_workers // 2)
            self.logger.warning(f"内存使用过高，减少工作进程至 {actual_workers}")
        else:
            actual_workers = self.config.max_workers
        
        # 并发处理
        batch_results = []
        with ProcessPoolExecutor(max_workers=actual_workers) as executor:
            # 提交任务
            future_to_file = {
                executor.submit(process_single_file_worker, file_path, self.config): file_path
                for file_path in unprocessed_files
            }
            
            # 收集结果
            for future in as_completed(future_to_file):
                file_path = future_to_file[future]
                try:
                    result = future.result(timeout=300)  # 5分钟超时
                    if result:
                        batch_results.append(result)
                        self.processed_count += 1
                        
                        # 加入缓存
                        file_hash = result.metadata.file_hash
                        self.processed_cache[file_hash] = result
                    else:
                        self.failed_count += 1
                        
                except Exception as e:
                    self.logger.error(f"处理任务失败 {file_path}: {e}")
                    self.failed_count += 1
        
        results.extend(batch_results)
        
        # 定期保存缓存
        if (self.processed_count + self.failed_count) % 10 == 0:
            self._save_cache()
            self._save_progress()
        
        return results
    
    def run_full_pipeline(self) -> Dict[str, Any]:
        """运行完整管道"""
        self.start_time = datetime.now()
        self.logger.info("=" * 80)
        self.logger.info("🚀 启动生产级PDF提取管道")
        self.logger.info(f"📂 源目录: {self.config.source_dir}")
        self.logger.info(f"📁 输出目录: {self.config.output_dir}")
        self.logger.info(f"⚡ 最大工作进程: {self.config.max_workers}")
        self.logger.info(f"📦 批处理大小: {self.config.batch_size}")
        self.logger.info(f"💾 内存限制: {self.config.memory_limit_gb:.1f} GB")
        self.logger.info(f"⏰ 时间限制: {self.config.time_limit_hours:.1f} 小时")
        self.logger.info("=" * 80)
        
        # 扫描PDF文件
        source_path = Path(self.config.source_dir)
        pdf_files = list(source_path.glob("*.pdf"))
        total_files = len(pdf_files)
        
        if total_files == 0:
            self.logger.error("❌ 没有找到PDF文件")
            return {"status": "error", "message": "没有找到PDF文件"}
        
        self.logger.info(f"📋 发现 {total_files} 个PDF文件")
        
        # 按文件大小排序（小文件优先处理）
        pdf_files.sort(key=lambda f: f.stat().st_size)
        
        # 计算总数据量
        total_size_mb = sum(f.stat().st_size for f in pdf_files) / (1024 * 1024)
        self.logger.info(f"💿 总数据量: {total_size_mb:.2f} MB")
        
        # 批次处理
        all_results = []
        time_limit_seconds = self.config.time_limit_hours * 3600
        
        # 进度条
        with tqdm(total=total_files, desc="处理PDF文件", unit="文件") as pbar:
            
            for i in range(0, total_files, self.config.batch_size):
                batch = pdf_files[i:i + self.config.batch_size]
                batch_num = i // self.config.batch_size + 1
                
                # 时间检查
                elapsed_time = (datetime.now() - self.start_time).total_seconds()
                if elapsed_time > time_limit_seconds:
                    self.logger.warning("⏰ 达到时间限制，停止处理")
                    break
                
                self.logger.info(f"📦 处理批次 {batch_num}: {len(batch)} 个文件")
                
                # 处理批次
                batch_start_time = time.time()
                batch_results = self.process_file_batch(batch)
                batch_time = time.time() - batch_start_time
                
                # 统计批次结果
                successful_batch = [r for r in batch_results if r is not None]
                all_results.extend(successful_batch)
                
                # 更新进度条
                pbar.update(len(batch))
                pbar.set_postfix({
                    "成功": len(successful_batch),
                    "失败": len(batch) - len(successful_batch),
                    "用时": f"{batch_time:.1f}s"
                })
                
                # 批次性能报告
                files_per_sec = len(batch) / batch_time if batch_time > 0 else 0
                self.logger.info(f"批次 {batch_num} 完成: {len(successful_batch)}/{len(batch)} 成功, "
                               f"耗时 {batch_time:.2f}s, 速度 {files_per_sec:.2f} 文件/秒")
                
                # 预估剩余时间
                if self.processed_count > 0:
                    avg_time_per_file = elapsed_time / (self.processed_count + self.failed_count)
                    remaining_files = total_files - (self.processed_count + self.failed_count + self.cached_count)
                    estimated_remaining_hours = (avg_time_per_file * remaining_files) / 3600
                    
                    self.logger.info(f"📊 进度: {self.processed_count + self.failed_count + self.cached_count}/{total_files}, "
                                   f"预计剩余: {estimated_remaining_hours:.2f} 小时")
                
                # 内存清理
                gc.collect()
        
        # 最终保存
        self._save_cache()
        self._save_progress()
        
        # 生成处理报告
        total_time = (datetime.now() - self.start_time).total_seconds()
        report = self._generate_final_report(all_results, total_time, total_files)
        
        # 保存结果
        self._save_results(all_results, report)
        
        return report
    
    def _generate_final_report(self, results: List[ExtractionResult], 
                             total_time: float, total_files: int) -> Dict[str, Any]:
        """生成最终报告"""
        successful_results = [r for r in results if r is not None]
        
        # 按类别统计
        category_stats = defaultdict(int)
        priority_stats = defaultdict(int)
        method_stats = defaultdict(int)
        
        total_text_length = 0
        total_hexagrams = 0
        total_yao_ci = 0
        total_annotations = 0
        total_cases = 0
        
        for result in successful_results:
            category_stats[result.metadata.category] += 1
            priority_stats[f"优先级{result.metadata.priority}"] += 1
            method_stats[result.metadata.method_used] += 1
            
            total_text_length += result.statistics["text_length"]
            total_hexagrams += result.statistics["hexagram_count"]
            total_yao_ci += result.statistics["yao_ci_count"]
            total_annotations += result.statistics["annotation_count"]
            total_cases += result.statistics["case_count"]
        
        # 质量统计
        quality_scores = [r.quality_metrics["overall"] for r in successful_results]
        avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0
        
        # 性能统计
        processing_times = [r.metadata.processing_time for r in successful_results]
        avg_processing_time = sum(processing_times) / len(processing_times) if processing_times else 0
        
        report = {
            "status": "completed",
            "summary": {
                "total_files": total_files,
                "processed_files": len(successful_results),
                "failed_files": self.failed_count,
                "cached_files": self.cached_count,
                "success_rate": len(successful_results) / total_files * 100 if total_files > 0 else 0,
                "total_processing_time_hours": total_time / 3600,
                "average_file_processing_time": avg_processing_time,
                "files_per_second": len(successful_results) / total_time if total_time > 0 else 0
            },
            "content_statistics": {
                "total_text_length": total_text_length,
                "total_hexagrams": total_hexagrams,
                "total_yao_ci": total_yao_ci,
                "total_annotations": total_annotations,
                "total_cases": total_cases,
                "average_quality_score": avg_quality
            },
            "category_distribution": dict(category_stats),
            "priority_distribution": dict(priority_stats),
            "method_distribution": dict(method_stats),
            "performance_metrics": {
                "memory_peak_gb": max([info.get("process_memory_gb", 0) 
                                     for info in self.extractor._memory_usage_history] or [0]),
                "method_performance": dict(self.extractor._method_performance)
            },
            "processing_timestamp": datetime.now().isoformat(),
            "config_used": asdict(self.config)
        }
        
        return report
    
    def _save_results(self, results: List[ExtractionResult], report: Dict[str, Any]):
        """保存处理结果"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 保存完整结果
        complete_results = []
        for result in results:
            if result:
                result_dict = {
                    "metadata": asdict(result.metadata),
                    "statistics": result.statistics,
                    "quality_metrics": result.quality_metrics,
                    "structured_content": result.structured_content,
                    "error_log": result.error_log
                }
                complete_results.append(result_dict)
        
        complete_file = self.structured_data_dir / f"complete_results_{timestamp}.json"
        with open(complete_file, 'w', encoding='utf-8') as f:
            json.dump(complete_results, f, ensure_ascii=False, indent=2)
        
        # 按类别保存
        category_results = defaultdict(list)
        for result in results:
            if result:
                category_results[result.metadata.category].append(asdict(result.metadata))
        
        for category, files in category_results.items():
            category_file = self.categories_dir / f"{category}_{timestamp}.json"
            with open(category_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "category": category,
                    "file_count": len(files),
                    "files": files
                }, f, ensure_ascii=False, indent=2)
        
        # 保存处理报告
        report_file = self.structured_data_dir / f"processing_report_{timestamp}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        # 生成HTML报告
        self._generate_html_report(report, timestamp)
        
        # 保存原始文本（小文件）
        for result in results:
            if result and len(result.raw_text) < 200000:  # 小于200KB的文本
                text_file = self.raw_texts_dir / f"{Path(result.metadata.file_name).stem}.txt"
                with open(text_file, 'w', encoding='utf-8') as f:
                    f.write(result.raw_text)
        
        self.logger.info(f"✅ 结果已保存")
        self.logger.info(f"📄 完整结果: {complete_file}")
        self.logger.info(f"📊 处理报告: {report_file}")
        self.logger.info(f"📁 分类结果: {self.categories_dir}")
    
    def _generate_html_report(self, report: Dict[str, Any], timestamp: str):
        """生成HTML可视化报告"""
        summary = report["summary"]
        content_stats = report["content_statistics"]
        category_dist = report["category_distribution"]
        
        html_content = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>生产级PDF提取报告 - {timestamp}</title>
    <style>
        body {{ 
            font-family: 'Microsoft YaHei', -apple-system, BlinkMacSystemFont, sans-serif; 
            margin: 20px; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }}
        .container {{ 
            max-width: 1200px; 
            margin: 0 auto; 
            background: white; 
            padding: 30px; 
            border-radius: 20px; 
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
        }}
        .header {{ 
            text-align: center; 
            border-bottom: 4px solid #4CAF50; 
            padding-bottom: 20px; 
            margin-bottom: 30px; 
        }}
        .header h1 {{
            color: #2c3e50;
            margin-bottom: 10px;
            font-size: 2.5em;
        }}
        .stats-grid {{ 
            display: grid; 
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); 
            gap: 25px; 
            margin-bottom: 40px; 
        }}
        .stat-card {{ 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
            color: white; 
            padding: 25px; 
            border-radius: 15px; 
            text-align: center;
            transition: transform 0.3s ease;
        }}
        .stat-card:hover {{
            transform: translateY(-5px);
        }}
        .stat-number {{ 
            font-size: 3em; 
            font-weight: bold; 
            margin-bottom: 10px; 
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }}
        .stat-label {{ 
            font-size: 1.2em; 
            opacity: 0.9; 
        }}
        .section {{
            margin: 40px 0;
            padding: 25px;
            border-radius: 15px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.08);
        }}
        .category-section {{ 
            background: linear-gradient(135deg, #e8f5e8 0%, #f0f9ff 100%);
        }}
        .performance-section {{
            background: linear-gradient(135deg, #fff3e0 0%, #fce4ec 100%);
        }}
        .content-section {{
            background: linear-gradient(135deg, #f3e5f5 0%, #e8f5e8 100%);
        }}
        .category-grid {{ 
            display: grid; 
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); 
            gap: 20px; 
            margin-top: 20px;
        }}
        .category-item {{ 
            background: white; 
            padding: 20px; 
            border-radius: 12px; 
            border-left: 6px solid #4CAF50;
            box-shadow: 0 3px 10px rgba(0,0,0,0.1);
            transition: transform 0.2s ease;
        }}
        .category-item:hover {{
            transform: scale(1.02);
        }}
        .progress-bar {{
            background: #e0e0e0;
            border-radius: 10px;
            height: 8px;
            margin: 10px 0;
            overflow: hidden;
        }}
        .progress-fill {{
            background: linear-gradient(135deg, #4CAF50, #45a049);
            height: 100%;
            border-radius: 10px;
            transition: width 0.3s ease;
        }}
        h2 {{ 
            color: #2c3e50; 
            border-bottom: 3px solid #4CAF50; 
            padding-bottom: 10px;
            margin-bottom: 20px;
            font-size: 1.8em;
        }}
        .highlight {{
            background: linear-gradient(135deg, #ff6b6b, #ee5a24);
            color: white;
            padding: 3px 8px;
            border-radius: 5px;
            font-weight: bold;
        }}
        .success {{
            color: #27ae60;
            font-weight: bold;
        }}
        .footer {{
            text-align: center;
            margin-top: 40px;
            padding: 20px;
            color: #7f8c8d;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 生产级PDF提取报告</h1>
            <p style="font-size: 1.2em; color: #7f8c8d;">处理时间: {timestamp}</p>
            <p style="font-size: 1.1em;">基于ETL_Architecture_Design.md方案实现</p>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-number">{summary['total_files']}</div>
                <div class="stat-label">📄 总文件数</div>
            </div>
            <div class="stat-card" style="background: linear-gradient(135deg, #00b894 0%, #00cec9 100%);">
                <div class="stat-number">{summary['processed_files']}</div>
                <div class="stat-label">✅ 成功处理</div>
            </div>
            <div class="stat-card" style="background: linear-gradient(135deg, #fdcb6e 0%, #e17055 100%);">
                <div class="stat-number">{summary.get('cached_files', 0)}</div>
                <div class="stat-label">💾 缓存命中</div>
            </div>
            <div class="stat-card" style="background: linear-gradient(135deg, #6c5ce7 0%, #a29bfe 100%);">
                <div class="stat-number">{summary['success_rate']:.1f}%</div>
                <div class="stat-label">📈 成功率</div>
            </div>
            <div class="stat-card" style="background: linear-gradient(135deg, #fd79a8 0%, #fdcb6e 100%);">
                <div class="stat-number">{summary['total_processing_time_hours']:.2f}h</div>
                <div class="stat-label">⏱️ 总耗时</div>
            </div>
            <div class="stat-card" style="background: linear-gradient(135deg, #00b894 0%, #55a3ff 100%);">
                <div class="stat-number">{summary['files_per_second']:.2f}</div>
                <div class="stat-label">🔥 文件/秒</div>
            </div>
        </div>
        
        <div class="section category-section">
            <h2>📚 内容分类统计</h2>
            <div class="category-grid">
        """
        
        # 添加分类统计
        total_processed = summary['processed_files']
        for category, count in sorted(category_dist.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / max(total_processed, 1)) * 100
            html_content += f"""
                <div class="category-item">
                    <h3 style="margin: 0 0 10px 0; color: #2c3e50;">{category}</h3>
                    <div style="font-size: 1.4em; font-weight: bold; color: #27ae60;">{count} 个文件</div>
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: {percentage}%"></div>
                    </div>
                    <div style="text-align: right; color: #7f8c8d; margin-top: 5px;">{percentage:.1f}%</div>
                </div>
            """
        
        html_content += """
            </div>
        </div>
        
        <div class="section content-section">
            <h2>📖 内容提取统计</h2>
            <div class="stats-grid">
        """
        
        # 内容统计卡片
        content_cards = [
            ("total_hexagrams", "🔮 卦象总数", "#e74c3c"),
            ("total_yao_ci", "📿 爻辞总数", "#3498db"),
            ("total_annotations", "📝 注解总数", "#f39c12"),
            ("total_cases", "📋 案例总数", "#9b59b6")
        ]
        
        for key, label, color in content_cards:
            value = content_stats.get(key, 0)
            html_content += f"""
                <div class="stat-card" style="background: linear-gradient(135deg, {color}, {color}aa);">
                    <div class="stat-number">{value}</div>
                    <div class="stat-label">{label}</div>
                </div>
            """
        
        html_content += f"""
            </div>
            <div style="text-align: center; margin-top: 30px; font-size: 1.3em;">
                📊 平均质量评分: <span class="highlight">{content_stats.get('average_quality_score', 0):.3f}</span>
                📏 总文本长度: <span class="highlight">{content_stats.get('total_text_length', 0):,}</span> 字符
            </div>
        </div>
        
        <div class="section performance-section">
            <h2>⚡ 性能指标</h2>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 25px;">
                <div style="background: white; padding: 20px; border-radius: 12px;">
                    <h3>🎯 目标达成情况</h3>
                    <p>⏰ <strong>目标时间</strong>: 3.0 小时</p>
                    <p>⏱️ <strong>实际用时</strong>: <span class="{'success' if summary['total_processing_time_hours'] <= 3.0 else 'highlight'}">{summary['total_processing_time_hours']:.2f} 小时</span></p>
                    <p>🎯 <strong>目标达成</strong>: <span class="{'success' if summary['total_processing_time_hours'] <= 3.0 else 'highlight'}">{'✅ 是' if summary['total_processing_time_hours'] <= 3.0 else '❌ 否'}</span></p>
                </div>
                
                <div style="background: white; padding: 20px; border-radius: 12px;">
                    <h3>🔧 处理方法统计</h3>
        """
        
        method_dist = report.get("method_distribution", {})
        for method, count in method_dist.items():
            html_content += f"<p><strong>{method}</strong>: {count} 次使用</p>"
        
        html_content += f"""
                </div>
            </div>
        </div>
        
        <div class="footer">
            <p>🤖 由Production Extract Pipeline自动生成</p>
            <p>基于ETL_Architecture_Design.md方案 | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
    </div>
</body>
</html>
        """
        
        # 保存HTML报告
        html_file = self.reports_dir / f"production_report_{timestamp}.html"
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        self.logger.info(f"📄 HTML报告已生成: {html_file}")


# ============================================================================
# 工作进程函数（用于multiprocessing）
# ============================================================================

def process_single_file_worker(file_path: Path, config: ProcessingConfig) -> Optional[ExtractionResult]:
    """工作进程处理单个文件（用于multiprocessing）"""
    try:
        extractor = ProductionPDFExtractor(config)
        return extractor.process_single_file(file_path)
    except Exception as e:
        logging.getLogger("Worker").error(f"工作进程处理失败 {file_path}: {e}")
        return None


# ============================================================================
# 主程序入口
# ============================================================================

def main():
    """主程序"""
    print("🚀 生产级易学PDF文档批量提取管道")
    print("=" * 80)
    print("基于ETL_Architecture_Design.md方案实现")
    print("整合pdfplumber+PyMuPDF+multiprocessing+断点续传")
    print("目标: 191个PDF文件，3小时内完成处理")
    print("=" * 80)
    
    # 检查数据目录
    data_dir = "/mnt/d/desktop/appp/data"
    output_dir = "/mnt/d/desktop/appp/structured_data"
    
    if not Path(data_dir).exists():
        print(f"❌ 数据目录不存在: {data_dir}")
        return
    
    # 统计PDF文件
    pdf_files = list(Path(data_dir).glob("*.pdf"))
    print(f"📋 发现 {len(pdf_files)} 个PDF文件")
    
    if len(pdf_files) == 0:
        print("❌ 没有找到PDF文件")
        return
    
    # 检查系统资源
    memory = psutil.virtual_memory()
    cpu_count = psutil.cpu_count()
    
    print(f"💻 系统资源:")
    print(f"   CPU核心: {cpu_count}")
    print(f"   总内存: {memory.total / (1024**3):.1f} GB")
    print(f"   可用内存: {memory.available / (1024**3):.1f} GB")
    
    # 动态计算最优配置
    optimal_workers = min(cpu_count - 1, 8)  # 保留1个核心给系统
    optimal_batch_size = max(4, min(optimal_workers * 2, 12))
    memory_limit_gb = min(memory.available / (1024**3) * 0.7, 3.0)  # 使用70%可用内存
    
    print(f"⚙️ 优化配置:")
    print(f"   工作进程: {optimal_workers}")
    print(f"   批处理大小: {optimal_batch_size}")
    print(f"   内存限制: {memory_limit_gb:.1f} GB")
    
    # 用户确认
    print(f"\n📁 输出目录: {output_dir}")
    print(f"⏰ 预计处理时间: < 3.0 小时")
    print("\n🚀 自动开始处理...")  # 去除交互式确认
    
    # 创建配置
    config = ProcessingConfig(
        source_dir=data_dir,
        output_dir=output_dir,
        max_workers=optimal_workers,
        batch_size=optimal_batch_size,
        memory_limit_gb=memory_limit_gb,
        time_limit_hours=3.0,
        cache_enabled=True,
        resume_enabled=True,
        min_text_length=50,
        max_pages_per_file=500
    )
    
    # 运行管道
    pipeline = ProductionPipeline(config)
    
    try:
        print(f"\n⚡ 启动处理管道...")
        start_time = time.time()
        
        report = pipeline.run_full_pipeline()
        
        end_time = time.time()
        total_time_hours = (end_time - start_time) / 3600
        
        print(f"\n✅ 处理完成!")
        print(f"⏰ 实际耗时: {total_time_hours:.2f} 小时")
        print(f"📊 成功率: {report['summary']['success_rate']:.1f}%")
        print(f"📄 处理文件: {report['summary']['processed_files']}/{report['summary']['total_files']}")
        print(f"🎯 目标达成: {'✅ 是' if total_time_hours <= 3.0 else '❌ 否'}")
        print(f"📁 结果保存在: {output_dir}")
        
        # 显示核心统计
        content_stats = report["content_statistics"]
        print(f"\n📖 提取内容统计:")
        print(f"   🔮 卦象: {content_stats['total_hexagrams']} 个")
        print(f"   📿 爻辞: {content_stats['total_yao_ci']} 个")
        print(f"   📝 注解: {content_stats['total_annotations']} 个")
        print(f"   📋 案例: {content_stats['total_cases']} 个")
        print(f"   📏 文本: {content_stats['total_text_length']:,} 字符")
        
        print(f"\n🎉 生产级PDF提取管道执行完毕!")
        
    except KeyboardInterrupt:
        print("\n⚠️ 用户中断处理")
        pipeline._save_cache()
        pipeline._save_progress()
        print("💾 已保存处理进度，下次运行将从断点继续")
        
    except Exception as e:
        print(f"\n❌ 处理过程中出错: {e}")
        import traceback
        traceback.print_exc()
        pipeline._save_cache()
        pipeline._save_progress()


if __name__ == "__main__":
    main()