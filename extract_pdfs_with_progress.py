#!/usr/bin/env python3
"""
带进度条的高效批量易学PDF文件处理脚本
支持200+PDF文件的并行处理、文本提取、自动分类和数据结构化
"""

import os
import json
import re
import logging
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from datetime import datetime
import hashlib
import pickle
from collections import defaultdict
import time

try:
    import pdfplumber
    from tqdm import tqdm
except ImportError:
    print("请安装依赖: python install_dependencies.py")
    exit(1)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('pdf_processing.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class PDFInfo:
    """PDF文件信息"""
    file_path: str
    file_name: str
    file_size: int
    pages: int
    category: str
    confidence: float
    priority: int  # 1-5, 1最高
    processed_at: str
    text_length: int
    processing_time: float
    
@dataclass 
class ExtractedContent:
    """提取的内容"""
    hexagrams: List[Dict[str, Any]]  # 64卦信息
    yao_ci: List[Dict[str, Any]]     # 384爻辞
    annotations: List[Dict[str, Any]] # 注解
    cases: List[Dict[str, Any]]      # 案例
    keywords: List[str]              # 关键词
    author: Optional[str]            # 作者
    dynasty: Optional[str]           # 朝代
    
class PDFProcessorWithProgress:
    """带进度显示的PDF处理器"""
    
    def __init__(self, data_dir: str, output_dir: str):
        self.data_dir = Path(data_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建子目录
        (self.output_dir / "raw_texts").mkdir(exist_ok=True)
        (self.output_dir / "structured_data").mkdir(exist_ok=True)
        (self.output_dir / "categories").mkdir(exist_ok=True)
        (self.output_dir / "cache").mkdir(exist_ok=True)
        (self.output_dir / "reports").mkdir(exist_ok=True)
        
        # 分类模式 - 更精确的匹配
        self.category_patterns = {
            "六爻": {
                "keywords": ["六爻", "卜易", "增删", "火珠林", "黄金策", "筮", "卦象", "爻辞", "爻变"],
                "priority": 1,
                "patterns": [r"六爻", r"筮\w*", r"卦象", r"爻\w+", r"动爻", r"变爻", r"世应", r"六亲", r"用神"]
            },
            "梅花易数": {
                "keywords": ["梅花", "易数", "梅花易", "观梅", "数理", "先天", "后天"],
                "priority": 2,
                "patterns": [r"梅花\w*易\w*", r"观梅", r"易数", r"数理", r"先天\w*数", r"后天\w*数"]
            },
            "大六壬": {
                "keywords": ["六壬", "壬学", "壬占", "课传", "神将", "十二将", "四课", "三传"],
                "priority": 1,
                "patterns": [r"六壬", r"壬占", r"课传", r"神将", r"十二将", r"四课", r"三传"]
            },
            "紫微斗数": {
                "keywords": ["紫微", "斗数", "命盘", "宫位", "星曜", "主星", "辅星"],
                "priority": 2,
                "patterns": [r"紫微\w*斗数", r"命盘", r"宫位", r"星曜", r"主星", r"辅星", r"化\w+"]
            },
            "奇门遁甲": {
                "keywords": ["奇门", "遁甲", "九宫", "八门", "神煞", "三奇", "六仪"],
                "priority": 2,
                "patterns": [r"奇门\w*遁甲", r"九宫", r"八门", r"神煞", r"三奇", r"六仪"]
            },
            "八字命理": {
                "keywords": ["八字", "四柱", "命理", "干支", "纳音", "十神", "喜用神"],
                "priority": 2,
                "patterns": [r"八字", r"四柱", r"命理", r"干支", r"纳音", r"十神", r"喜用神"]
            },
            "金口诀": {
                "keywords": ["金口诀", "金口", "课式", "立课", "四位"],
                "priority": 3,
                "patterns": [r"金口\w*诀", r"金口", r"课式", r"立课", r"四位"]
            },
            "太乙神数": {
                "keywords": ["太乙", "神数", "太乙神数", "太乙式"],
                "priority": 3,
                "patterns": [r"太乙\w*神数", r"太乙", r"太乙式"]
            },
            "河洛理数": {
                "keywords": ["河洛", "理数", "河图", "洛书", "先天卦", "后天卦"],
                "priority": 3,
                "patterns": [r"河洛\w*理数", r"河图", r"洛书", r"先天卦", r"后天卦"]
            },
            "周易基础": {
                "keywords": ["周易", "易经", "八卦", "六十四卦", "卦象", "卦辞", "象传"],
                "priority": 1,
                "patterns": [r"周易", r"易经", r"八卦", r"六十四卦", r"卦辞", r"象传", r"彖传"]
            }
        }
        
        # 64卦名称
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
        
        # 缓存文件路径
        self.cache_file = self.output_dir / "cache" / "processing_cache.pkl"
        self.processed_files = self.load_cache()
        
        # 进度跟踪
        self.progress_bar = None
        self.start_time = None
    
    def load_cache(self) -> Dict[str, Any]:
        """加载缓存"""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'rb') as f:
                    cache_data = pickle.load(f)
                    logger.info(f"加载缓存: {len(cache_data)} 个已处理文件")
                    return cache_data
            except Exception as e:
                logger.warning(f"缓存加载失败: {e}")
        return {}
    
    def save_cache(self):
        """保存缓存"""
        try:
            with open(self.cache_file, 'wb') as f:
                pickle.dump(self.processed_files, f)
            logger.info(f"缓存已保存: {len(self.processed_files)} 个文件")
        except Exception as e:
            logger.error(f"缓存保存失败: {e}")
    
    def get_file_hash(self, file_path: Path) -> str:
        """获取文件哈希"""
        stat = file_path.stat()
        return hashlib.md5(f"{file_path}_{stat.st_size}_{stat.st_mtime}".encode()).hexdigest()
    
    def classify_pdf(self, text: str, file_name: str) -> Tuple[str, float, int]:
        """分类PDF文件 - 改进的分类算法"""
        text_lower = text.lower()
        file_lower = file_name.lower()
        
        category_scores = {}
        
        for category, config in self.category_patterns.items():
            score = 0.0
            
            # 文件名权重更高
            filename_matches = sum(1 for kw in config["keywords"] if kw in file_lower)
            score += filename_matches * 3.0
            
            # 内容模式匹配
            for pattern in config["patterns"]:
                matches = len(re.findall(pattern, text, re.IGNORECASE))
                score += matches * 1.0
            
            # 关键词密度
            total_keywords = sum(text_lower.count(kw) for kw in config["keywords"])
            if len(text) > 100:  # 避免除零
                density = (total_keywords / len(text)) * 10000
                score += density
            
            category_scores[category] = score
        
        # 找出最高分
        if not category_scores or max(category_scores.values()) == 0:
            return "其他", 0.0, 5
        
        best_category = max(category_scores, key=category_scores.get)
        best_score = category_scores[best_category]
        
        # 归一化置信度
        confidence = min(best_score / 15.0, 1.0)  # 调整归一化因子
        priority = self.category_patterns[best_category]["priority"]
        
        return best_category, confidence, priority
    
    def extract_hexagrams(self, text: str) -> List[Dict[str, Any]]:
        """提取64卦信息 - 改进版"""
        hexagrams = []
        
        for i, name in enumerate(self.hexagram_names):
            # 多种卦名匹配模式
            patterns = [
                rf"{name}[卦]?[：:]\s*([^。\n]+)",
                rf"第\w*{name}卦[：:]\s*([^。\n]+)",
                rf"{name}[卦]?\s*([^。\n]{10,50})",
            ]
            
            for pattern in patterns:
                matches = re.finditer(pattern, text)
                for match in matches:
                    description = match.group(1).strip()
                    if len(description) > 5:  # 过滤太短的描述
                        hexagram = {
                            "number": i + 1,
                            "name": name,
                            "description": description,
                            "position": match.start(),
                            "pattern_used": pattern
                        }
                        hexagrams.append(hexagram)
        
        # 去重
        seen = set()
        unique_hexagrams = []
        for h in hexagrams:
            key = (h["name"], h["description"])
            if key not in seen:
                seen.add(key)
                unique_hexagrams.append(h)
        
        return unique_hexagrams
    
    def extract_yao_ci(self, text: str) -> List[Dict[str, Any]]:
        """提取爻辞 - 改进版"""
        yao_positions = ["初", "二", "三", "四", "五", "上"]
        yao_types = ["六", "九"]
        yao_ci = []
        
        for pos in yao_positions:
            for yao_type in yao_types:
                # 多种爻辞格式
                patterns = [
                    rf"({pos}{yao_type})[：:]([^。\n]+[。]?)",
                    rf"({pos}{yao_type})\s*([^。\n]{10,100})",
                ]
                
                for pattern in patterns:
                    matches = re.finditer(pattern, text)
                    for match in matches:
                        yao_text = match.group(2).strip()
                        if len(yao_text) > 5:
                            yao = {
                                "position": pos,
                                "type": yao_type,
                                "full_name": match.group(1),
                                "text": yao_text,
                                "location": match.start()
                            }
                            yao_ci.append(yao)
        
        return yao_ci
    
    def extract_annotations(self, text: str) -> List[Dict[str, Any]]:
        """提取注解 - 改进版"""
        annotations = []
        
        # 更全面的注解模式
        annotation_patterns = [
            (r"注[：:]([^。\n]{10,200})", "注"),
            (r"解[：:]([^。\n]{10,200})", "解"),
            (r"释[：:]([^。\n]{10,200})", "释"),
            (r"按[：:]([^。\n]{10,200})", "按"),
            (r"曰[：:]([^。\n]{10,200})", "曰"),
            (r"述[：:]([^。\n]{10,200})", "述"),
            (r"评[：:]([^。\n]{10,200})", "评"),
        ]
        
        for pattern, ann_type in annotation_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                content = match.group(1).strip()
                if len(content) > 10:  # 过滤太短的注解
                    annotation = {
                        "type": ann_type,
                        "content": content,
                        "position": match.start(),
                        "length": len(content)
                    }
                    annotations.append(annotation)
        
        return annotations
    
    def extract_cases(self, text: str) -> List[Dict[str, Any]]:
        """提取案例 - 改进版"""
        cases = []
        
        # 更多案例模式
        case_patterns = [
            r"例[一二三四五六七八九十\d+][：:]([^。]{30,500})",
            r"案例[一二三四五六七八九十\d*][：:]([^。]{30,500})",
            r"实例[一二三四五六七八九十\d*][：:]([^。]{30,500})",
            r"占例[一二三四五六七八九十\d*][：:]([^。]{30,500})",
            r"测例[一二三四五六七八九十\d*][：:]([^。]{30,500})",
        ]
        
        for pattern in case_patterns:
            matches = re.finditer(pattern, text, re.DOTALL)
            for match in matches:
                content = match.group(1).strip()
                if len(content) >= 30:  # 确保案例有足够内容
                    case = {
                        "content": content,
                        "position": match.start(),
                        "length": len(content),
                        "preview": content[:100] + "..." if len(content) > 100 else content
                    }
                    cases.append(case)
        
        return cases
    
    def extract_keywords(self, text: str) -> List[str]:
        """提取关键词 - 改进版"""
        keywords = set()
        
        # 分类别的术语
        term_categories = {
            "基础概念": ["阴阳", "五行", "八卦", "六爻", "占卜", "预测", "命理", "风水", "周易", "太极"],
            "六爻术语": ["神煞", "六亲", "用神", "世应", "动爻", "静爻", "变爻", "飞神", "伏神"],
            "八字术语": ["十神", "天干", "地支", "纳音", "喜用神", "忌神", "格局", "运势"],
            "紫微术语": ["命宫", "身宫", "主星", "辅星", "化禄", "化权", "化科", "化忌"],
            "奇门术语": ["九宫", "八门", "三奇", "六仪", "值符", "值使", "天盘", "地盘"]
        }
        
        for category, terms in term_categories.items():
            for term in terms:
                if term in text:
                    keywords.add(term)
        
        # 提取书名
        book_names = re.findall(r'《([^》]{2,20})》', text)
        keywords.update(book_names[:5])  # 限制书名数量
        
        # 提取人名（可能的作者）
        author_patterns = re.findall(r'([王李张刘陈杨赵黄周吴徐孙胡朱高林何郭马罗梁宋郑谢韩唐冯于董萧程曹袁邓许傅沈曾彭吕苏卢蒋蔡贾丁魏薛叶阎余潘杜戴夏钟汪田任姜范方石姚谭廖邹熊金陆郝孔白崔康毛邱秦江史顾侯邵孟龙万段雷钱汤尹黎易常武乔贺赖龚文][\u4e00-\u9fff]{1,3})', text)
        keywords.update(author_patterns[:3])  # 限制人名数量
        
        return sorted(list(keywords))
    
    def extract_author_dynasty(self, text: str, filename: str) -> Tuple[Optional[str], Optional[str]]:
        """提取作者和朝代 - 改进版"""
        author = None
        dynasty = None
        
        # 从文件名提取作者
        filename_patterns = [
            r'([王李张刘陈杨赵黄周吴徐孙胡朱高林何郭马罗梁宋郑谢韩唐冯于董萧程曹袁邓许傅沈曾彭吕苏卢蒋蔡贾丁魏薛叶阎余潘杜戴夏钟汪田任姜范方石姚谭廖邹熊金陆郝孔白崔康毛邱秦江史顾侯邵孟龙万段雷钱汤尹黎易常武乔贺赖龚文][\u4e00-\u9fff]{1,3})[_-]',
            r'^([^0-9\s\-_]+)',
        ]
        
        for pattern in filename_patterns:
            match = re.search(pattern, filename)
            if match:
                potential_author = match.group(1)
                if len(potential_author) >= 2 and not any(char.isdigit() for char in potential_author):
                    author = potential_author
                    break
        
        # 朝代模式 - 更精确
        dynasty_patterns = [
            r'[(（]?(汉|唐|宋|元|明|清)[朝代)）]?',
            r'(汉|唐|宋|元|明|清)[·•]',
            r'(汉|唐|宋|元|明|清)代',
        ]
        
        for pattern in dynasty_patterns:
            match = re.search(pattern, text)
            if match:
                dynasty = match.group(1)
                break
        
        return author, dynasty
    
    def process_single_pdf(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """处理单个PDF文件"""
        start_time = time.time()
        
        try:
            # 检查缓存
            file_hash = self.get_file_hash(file_path)
            if file_hash in self.processed_files:
                if self.progress_bar:
                    self.progress_bar.set_postfix_str(f"缓存: {file_path.name[:30]}...")
                return self.processed_files[file_hash]
            
            if self.progress_bar:
                self.progress_bar.set_postfix_str(f"处理: {file_path.name[:30]}...")
            
            # 提取文本
            text = ""
            page_count = 0
            
            with pdfplumber.open(file_path) as pdf:
                page_count = len(pdf.pages)
                # 限制提取页数，避免超大文件
                max_pages = min(page_count, 200)  # 最多处理200页
                
                for i, page in enumerate(pdf.pages[:max_pages]):
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
            
            if not text.strip():
                logger.warning(f"无法提取文本: {file_path.name}")
                return None
            
            # 分类
            category, confidence, priority = self.classify_pdf(text, file_path.name)
            
            # 提取结构化内容
            hexagrams = self.extract_hexagrams(text)
            yao_ci = self.extract_yao_ci(text)
            annotations = self.extract_annotations(text)
            cases = self.extract_cases(text)
            keywords = self.extract_keywords(text)
            author, dynasty = self.extract_author_dynasty(text, file_path.name)
            
            processing_time = time.time() - start_time
            
            # 创建结果
            result = {
                "pdf_info": {
                    "file_path": str(file_path),
                    "file_name": file_path.name,
                    "file_size": file_path.stat().st_size,
                    "pages": page_count,
                    "category": category,
                    "confidence": confidence,
                    "priority": priority,
                    "processed_at": datetime.now().isoformat(),
                    "text_length": len(text),
                    "processing_time": processing_time
                },
                "content": {
                    "hexagrams": hexagrams,
                    "yao_ci": yao_ci,
                    "annotations": annotations,
                    "cases": cases,
                    "keywords": keywords,
                    "author": author,
                    "dynasty": dynasty
                },
                "statistics": {
                    "hexagram_count": len(hexagrams),
                    "yao_ci_count": len(yao_ci),
                    "annotation_count": len(annotations),
                    "case_count": len(cases),
                    "keyword_count": len(keywords)
                }
            }
            
            # 保存到缓存
            self.processed_files[file_hash] = result
            
            # 保存原始文本（可选）
            if len(text) < 100000:  # 只保存较小的文本文件
                text_file = self.output_dir / "raw_texts" / f"{file_path.stem}.txt"
                with open(text_file, 'w', encoding='utf-8') as f:
                    f.write(text)
            
            return result
            
        except Exception as e:
            logger.error(f"处理文件失败 {file_path.name}: {e}")
            return None
    
    def process_all_pdfs(self, max_workers: int = 4) -> Dict[str, Any]:
        """并行处理所有PDF文件 - 带进度条"""
        pdf_files = list(self.data_dir.glob("*.pdf"))
        logger.info(f"找到 {len(pdf_files)} 个PDF文件")
        
        if len(pdf_files) == 0:
            return {"error": "没有找到PDF文件"}
        
        # 过滤已处理的文件
        unprocessed_files = []
        for pdf_file in pdf_files:
            file_hash = self.get_file_hash(pdf_file)
            if file_hash not in self.processed_files:
                unprocessed_files.append(pdf_file)
        
        logger.info(f"需要处理 {len(unprocessed_files)} 个新文件，{len(pdf_files) - len(unprocessed_files)} 个已缓存")
        
        results = []
        failed_files = []
        
        # 创建进度条
        self.progress_bar = tqdm(total=len(pdf_files), desc="处理PDF文件", unit="文件")
        
        # 添加已缓存的结果
        for pdf_file in pdf_files:
            file_hash = self.get_file_hash(pdf_file)
            if file_hash in self.processed_files:
                results.append(self.processed_files[file_hash])
                self.progress_bar.update(1)
        
        if unprocessed_files:
            with ProcessPoolExecutor(max_workers=max_workers) as executor:
                # 提交任务
                future_to_file = {
                    executor.submit(self.process_single_pdf, pdf_file): pdf_file 
                    for pdf_file in unprocessed_files
                }
                
                # 收集结果
                for future in as_completed(future_to_file):
                    pdf_file = future_to_file[future]
                    try:
                        result = future.result()
                        if result:
                            results.append(result)
                        else:
                            failed_files.append(pdf_file.name)
                    except Exception as e:
                        logger.error(f"任务失败 {pdf_file.name}: {e}")
                        failed_files.append(pdf_file.name)
                    finally:
                        self.progress_bar.update(1)
                        
                        # 定期保存缓存
                        if len(results) % 10 == 0:
                            self.save_cache()
        
        self.progress_bar.close()
        
        # 最终保存缓存
        self.save_cache()
        
        # 按优先级和类别组织结果
        categorized_results = defaultdict(list)
        priority_results = defaultdict(list)
        
        for result in results:
            category = result["pdf_info"]["category"]
            priority = result["pdf_info"]["priority"]
            
            categorized_results[category].append(result)
            priority_results[priority].append(result)
        
        # 计算统计信息
        total_hexagrams = sum(r.get("statistics", {}).get("hexagram_count", 0) for r in results)
        total_yao_ci = sum(r.get("statistics", {}).get("yao_ci_count", 0) for r in results)
        total_annotations = sum(r.get("statistics", {}).get("annotation_count", 0) for r in results)
        total_cases = sum(r.get("statistics", {}).get("case_count", 0) for r in results)
        
        # 统计信息
        stats = {
            "total_files": len(pdf_files),
            "processed_successfully": len(results),
            "failed_files": len(failed_files),
            "cached_files": len(pdf_files) - len(unprocessed_files),
            "categories": {cat: len(files) for cat, files in categorized_results.items()},
            "priorities": {f"优先级{p}": len(files) for p, files in priority_results.items()},
            "content_statistics": {
                "total_hexagrams": total_hexagrams,
                "total_yao_ci": total_yao_ci,
                "total_annotations": total_annotations,
                "total_cases": total_cases,
                "avg_per_file": {
                    "hexagrams": total_hexagrams / max(len(results), 1),
                    "yao_ci": total_yao_ci / max(len(results), 1),
                    "annotations": total_annotations / max(len(results), 1),
                    "cases": total_cases / max(len(results), 1)
                }
            },
            "failed_file_list": failed_files,
            "processing_time": datetime.now().isoformat()
        }
        
        return {
            "statistics": stats,
            "results": results,
            "by_category": dict(categorized_results),
            "by_priority": dict(priority_results)
        }
    
    def save_results(self, results: Dict[str, Any]):
        """保存处理结果"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 保存完整结果
        full_results_file = self.output_dir / "structured_data" / f"complete_results_{timestamp}.json"
        with open(full_results_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        # 按类别保存
        for category, files in results["by_category"].items():
            category_dir = self.output_dir / "categories" / category
            category_dir.mkdir(exist_ok=True)
            
            category_file = category_dir / f"{category}_{timestamp}.json"
            with open(category_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "category": category,
                    "file_count": len(files),
                    "files": files
                }, f, ensure_ascii=False, indent=2)
        
        # 保存统计信息
        stats_file = self.output_dir / "structured_data" / f"statistics_{timestamp}.json"
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump(results["statistics"], f, ensure_ascii=False, indent=2)
        
        # 生成HTML报告
        self.generate_html_report(results, timestamp)
        
        # 生成摘要报告
        self.generate_summary_report(results, timestamp)
        
        logger.info(f"结果已保存到: {self.output_dir}")
        return full_results_file
    
    def generate_html_report(self, results: Dict[str, Any], timestamp: str):
        """生成HTML可视化报告"""
        stats = results["statistics"]
        
        html_content = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>易学PDF处理报告 - {timestamp}</title>
    <style>
        body {{ font-family: 'Microsoft YaHei', sans-serif; margin: 20px; background: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        .header {{ text-align: center; border-bottom: 3px solid #4CAF50; padding-bottom: 20px; margin-bottom: 30px; }}
        .stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin-bottom: 30px; }}
        .stat-card {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 10px; text-align: center; }}
        .stat-number {{ font-size: 2.5em; font-weight: bold; margin-bottom: 10px; }}
        .stat-label {{ font-size: 1.1em; opacity: 0.9; }}
        .category-section {{ margin: 30px 0; }}
        .category-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; }}
        .category-item {{ background: #e8f5e8; padding: 15px; border-radius: 8px; border-left: 4px solid #4CAF50; }}
        .priority-section {{ background: #f9f9f9; padding: 20px; border-radius: 10px; margin: 20px 0; }}
        h1 {{ color: #333; }}
        h2 {{ color: #4CAF50; border-bottom: 2px solid #4CAF50; padding-bottom: 10px; }}
        .failed-files {{ background: #ffebee; padding: 15px; border-radius: 8px; border-left: 4px solid #f44336; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔮 易学PDF批量处理报告</h1>
            <p>处理时间: {timestamp}</p>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-number">{stats['total_files']}</div>
                <div class="stat-label">总文件数</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{stats['processed_successfully']}</div>
                <div class="stat-label">成功处理</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{stats.get('cached_files', 0)}</div>
                <div class="stat-label">缓存文件</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{stats['processed_successfully']/max(stats['total_files'], 1)*100:.1f}%</div>
                <div class="stat-label">成功率</div>
            </div>
        </div>
        
        <div class="category-section">
            <h2>📚 分类统计</h2>
            <div class="category-grid">
        """
        
        for category, count in stats["categories"].items():
            percentage = count / max(stats['processed_successfully'], 1) * 100
            html_content += f"""
                <div class="category-item">
                    <strong>{category}</strong><br>
                    {count} 个文件 ({percentage:.1f}%)
                </div>
            """
        
        html_content += """
            </div>
        </div>
        
        <div class="priority-section">
            <h2>⭐ 优先级分布</h2>
            <div class="category-grid">
        """
        
        for priority, count in stats["priorities"].items():
            html_content += f"""
                <div class="category-item">
                    <strong>{priority}</strong><br>
                    {count} 个文件
                </div>
            """
        
        html_content += "</div></div>"
        
        # 内容统计
        if "content_statistics" in stats:
            content_stats = stats["content_statistics"]
            html_content += f"""
            <div class="category-section">
                <h2>📖 内容统计</h2>
                <div class="stats-grid">
                    <div class="stat-card" style="background: linear-gradient(135deg, #ff7b7b 0%, #d63384 100%);">
                        <div class="stat-number">{content_stats['total_hexagrams']}</div>
                        <div class="stat-label">总卦象</div>
                    </div>
                    <div class="stat-card" style="background: linear-gradient(135deg, #20c997 0%, #0d7377 100%);">
                        <div class="stat-number">{content_stats['total_yao_ci']}</div>
                        <div class="stat-label">总爻辞</div>
                    </div>
                    <div class="stat-card" style="background: linear-gradient(135deg, #fd7e14 0%, #e55100 100%);">
                        <div class="stat-number">{content_stats['total_annotations']}</div>
                        <div class="stat-label">总注解</div>
                    </div>
                    <div class="stat-card" style="background: linear-gradient(135deg, #6610f2 0%, #4c1a57 100%);">
                        <div class="stat-number">{content_stats['total_cases']}</div>
                        <div class="stat-label">总案例</div>
                    </div>
                </div>
            </div>
            """
        
        # 失败文件
        if stats["failed_files"] > 0:
            html_content += f"""
            <div class="failed-files">
                <h2>❌ 失败文件 ({stats['failed_files']} 个)</h2>
                <ul>
            """
            for failed_file in stats["failed_file_list"]:
                html_content += f"<li>{failed_file}</li>"
            html_content += "</ul></div>"
        
        html_content += """
        </div>
    </body>
    </html>
        """
        
        # 保存HTML报告
        html_file = self.output_dir / "reports" / f"report_{timestamp}.html"
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        logger.info(f"HTML报告已生成: {html_file}")
    
    def generate_summary_report(self, results: Dict[str, Any], timestamp: str):
        """生成摘要报告"""
        stats = results["statistics"]
        
        report = f"""
# 📋 PDF处理摘要报告
**时间**: {timestamp}

## 📊 处理统计
- **总文件数**: {stats['total_files']}
- **成功处理**: {stats['processed_successfully']}
- **失败数量**: {stats['failed_files']}
- **缓存文件**: {stats.get('cached_files', 0)}
- **成功率**: {stats['processed_successfully']/max(stats['total_files'], 1)*100:.1f}%

## 📚 分类统计
"""
        
        for category, count in sorted(stats["categories"].items(), key=lambda x: x[1], reverse=True):
            percentage = count / max(stats['processed_successfully'], 1) * 100
            report += f"- **{category}**: {count} 个文件 ({percentage:.1f}%)\n"
        
        report += "\n## ⭐ 优先级分布\n"
        for priority in sorted(stats["priorities"].keys()):
            count = stats["priorities"][priority]
            report += f"- **{priority}**: {count} 个文件\n"
        
        # 内容统计
        if "content_statistics" in stats:
            content_stats = stats["content_statistics"]
            report += f"""
## 📖 内容提取统计
- **总卦象**: {content_stats['total_hexagrams']} 个
- **总爻辞**: {content_stats['total_yao_ci']} 个
- **总注解**: {content_stats['total_annotations']} 个
- **总案例**: {content_stats['total_cases']} 个

### 平均每文件
- **卦象**: {content_stats['avg_per_file']['hexagrams']:.1f} 个
- **爻辞**: {content_stats['avg_per_file']['yao_ci']:.1f} 个
- **注解**: {content_stats['avg_per_file']['annotations']:.1f} 个
- **案例**: {content_stats['avg_per_file']['cases']:.1f} 个
"""
        
        if stats["failed_files"] > 0:
            report += f"\n## ❌ 失败文件 ({stats['failed_files']} 个)\n"
            for failed_file in stats["failed_file_list"]:
                report += f"- {failed_file}\n"
        
        report += f"""
## 💾 输出文件
- 完整结果: `structured_data/complete_results_{timestamp}.json`
- 统计信息: `structured_data/statistics_{timestamp}.json`
- HTML报告: `reports/report_{timestamp}.html`
- 分类结果: `categories/` 目录下按类别保存
- 原始文本: `raw_texts/` 目录下（小文件）

## 📝 使用建议
1. 优先级1的文件包含最重要的易学内容
2. 查看HTML报告获得可视化统计
3. 按类别查看专门的JSON文件
4. 失败的文件可能需要手动处理
"""
        
        # 保存报告
        report_file = self.output_dir / f"processing_report_{timestamp}.md"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
        
        print(report)
        return report_file

def main():
    """主函数"""
    # 配置路径
    data_dir = "/mnt/d/desktop/appp/data"
    output_dir = "/mnt/d/desktop/appp/structured_data"
    
    print("🚀 开始批量处理易学PDF文件...")
    print(f"📂 数据目录: {data_dir}")
    print(f"📁 输出目录: {output_dir}")
    
    # 创建处理器
    processor = PDFProcessorWithProgress(data_dir, output_dir)
    
    # 检查数据目录
    if not Path(data_dir).exists():
        print(f"❌ 数据目录不存在: {data_dir}")
        return
    
    # 统计PDF文件
    pdf_count = len(list(Path(data_dir).glob("*.pdf")))
    print(f"📋 找到 {pdf_count} 个PDF文件")
    
    if pdf_count == 0:
        print("❌ 没有找到PDF文件")
        return
    
    # 开始处理
    start_time = datetime.now()
    processor.start_time = start_time
    print(f"⏰ 开始时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # 使用4个进程并行处理
        print("🔄 开始并行处理...")
        results = processor.process_all_pdfs(max_workers=4)
        
        if "error" in results:
            print(f"❌ {results['error']}")
            return
        
        # 保存结果
        print("\n💾 保存处理结果...")
        result_file = processor.save_results(results)
        
        end_time = datetime.now()
        duration = end_time - start_time
        
        print(f"\n✅ 处理完成!")
        print(f"⏰ 总耗时: {duration}")
        print(f"📊 成功处理: {results['statistics']['processed_successfully']}/{results['statistics']['total_files']}")
        print(f"🗂️ 主要结果文件: {result_file}")
        print(f"📁 所有结果保存在: {output_dir}")
        
        # 显示分类统计
        print(f"\n📚 分类统计:")
        for category, count in results['statistics']['categories'].items():
            print(f"  - {category}: {count} 个文件")
            
    except KeyboardInterrupt:
        print("\n⚠️ 用户中断处理")
        processor.save_cache()  # 保存已处理的缓存
        print("💾 已保存处理进度，下次运行将从断点继续")
    except Exception as e:
        print(f"\n❌ 处理过程中出错: {e}")
        logger.error(f"处理异常: {e}", exc_info=True)
        processor.save_cache()  # 保存已处理的缓存

if __name__ == "__main__":
    main()