#!/usr/bin/env python3
"""
PDF批量处理脚本 - 高性能多进程文本提取与分类系统

功能特性:
- 多进程并行处理200+ PDF文件
- 自动分类识别（增删卜易、梅花易数、大六壬、紫微斗数等）
- 提取64卦、384爻、注解、案例
- 实时进度条显示
- 错误恢复机制
- JSON格式输出

作者: Claude Code
版本: 1.0
"""

import os
import json
import re
import logging
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass, asdict
from datetime import datetime
import time
import traceback

import PyPDF2
import pdfplumber
from tqdm import tqdm
import fitz  # PyMuPDF


@dataclass
class ExtractedContent:
    """提取的PDF内容数据结构"""
    filename: str
    category: str
    confidence: float
    text_length: int
    hexagrams: List[Dict[str, Any]]  # 64卦
    yaos: List[Dict[str, Any]]       # 384爻
    annotations: List[str]           # 注解
    cases: List[Dict[str, Any]]      # 案例
    extraction_time: str
    error_messages: List[str]


class PDFProcessor:
    """PDF处理核心类"""
    
    # 分类关键词字典 - 用于自动识别类别
    CATEGORY_KEYWORDS = {
        '增删卜易': [
            '增删卜易', '野鹤老人', '六爻', '八卦', '装卦', '取象', '摇卦',
            '用神', '原神', '忌神', '世应', '飞神', '伏神', '动变'
        ],
        '梅花易数': [
            '梅花易数', '邵雍', '康节', '体用', '互卦', '变卦', '观梅',
            '先天八卦', '后天八卦', '时间起卦', '数字起卦'
        ],
        '大六壬': [
            '大六壬', '六壬', '壬学', '神将', '天将', '三传', '四课',
            '发用', '贵人', '天乙', '腾蛇', '朱雀', '六合'
        ],
        '紫微斗数': [
            '紫微斗数', '紫微', '斗数', '命宫', '身宫', '十二宫',
            '主星', '辅星', '化权', '化科', '化忌', '化禄'
        ],
        '奇门遁甲': [
            '奇门遁甲', '奇门', '遁甲', '九宫', '八门', '九星',
            '值符', '值使', '时家奇门', '日家奇门'
        ],
        '金口诀': [
            '金口诀', '大六壬金口诀', '孙膑', '四位', '将神',
            '贵神', '人元', '地分'
        ],
        '太乙神数': [
            '太乙神数', '太乙', '神数', '主客', '始击', '定局'
        ],
        '河洛理数': [
            '河洛理数', '河洛', '理数', '先天', '后天', '洛书', '河图'
        ],
        '其他': []  # 默认分类
    }
    
    # 64卦名称模式
    HEXAGRAM_PATTERNS = [
        r'乾卦|坤卦|屯卦|蒙卦|需卦|讼卦|师卦|比卦',
        r'小畜|履卦|泰卦|否卦|同人|大有|谦卦|豫卦',
        r'随卦|蛊卦|临卦|观卦|噬嗑|贲卦|剥卦|复卦',
        r'无妄|大畜|颐卦|大过|坎卦|离卦',
        r'咸卦|恒卦|遁卦|大壮|晋卦|明夷|家人|睽卦',
        r'蹇卦|解卦|损卦|益卦|夬卦|姤卦|萃卦|升卦',
        r'困卦|井卦|革卦|鼎卦|震卦|艮卦|渐卦|归妹',
        r'丰卦|旅卦|巽卦|兑卦|涣卦|节卦|中孚|小过|既济|未济'
    ]
    
    def __init__(self, data_dir: str, output_dir: str):
        """初始化处理器"""
        self.data_dir = Path(data_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 设置日志
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.output_dir / 'processing.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
        # 处理统计
        self.stats = {
            'total_files': 0,
            'processed_files': 0,
            'error_files': 0,
            'categories': {},
            'start_time': None,
            'end_time': None
        }
    
    def get_pdf_files(self) -> List[Path]:
        """获取所有PDF文件"""
        pdf_files = list(self.data_dir.glob('*.pdf'))
        self.logger.info(f"发现 {len(pdf_files)} 个PDF文件")
        return pdf_files
    
    def extract_text_multiple_methods(self, file_path: Path) -> str:
        """使用多种方法提取PDF文本"""
        text = ""
        methods_tried = []
        
        # 方法1: pdfplumber (最佳文本提取)
        try:
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
                methods_tried.append("pdfplumber")
                if len(text.strip()) > 100:  # 如果提取到足够文本，直接返回
                    return text.strip()
        except Exception as e:
            self.logger.debug(f"pdfplumber提取失败: {e}")
        
        # 方法2: PyMuPDF (处理复杂格式)
        try:
            doc = fitz.open(file_path)
            for page in doc:
                page_text = page.get_text()
                if page_text:
                    text += page_text + "\n"
            doc.close()
            methods_tried.append("PyMuPDF")
            if len(text.strip()) > 100:
                return text.strip()
        except Exception as e:
            self.logger.debug(f"PyMuPDF提取失败: {e}")
        
        # 方法3: PyPDF2 (备用方法)
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page in pdf_reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
                methods_tried.append("PyPDF2")
        except Exception as e:
            self.logger.debug(f"PyPDF2提取失败: {e}")
        
        self.logger.debug(f"使用方法: {', '.join(methods_tried)}")
        return text.strip()
    
    def classify_pdf(self, text: str, filename: str) -> Tuple[str, float]:
        """自动分类PDF文档"""
        if not text:
            return '其他', 0.1
        
        text_lower = text.lower()
        filename_lower = filename.lower()
        
        category_scores = {}
        
        for category, keywords in self.CATEGORY_KEYWORDS.items():
            if category == '其他':
                continue
                
            score = 0
            total_keywords = len(keywords)
            
            # 检查文本内容
            for keyword in keywords:
                keyword_lower = keyword.lower()
                # 文本中出现次数
                text_count = text_lower.count(keyword_lower)
                if text_count > 0:
                    score += min(text_count * 10, 50)  # 限制单个关键词最高分数
                
                # 文件名中出现
                if keyword_lower in filename_lower:
                    score += 30
            
            # 归一化分数
            if total_keywords > 0:
                category_scores[category] = score / total_keywords
        
        # 找到最高分数的类别
        if category_scores:
            best_category = max(category_scores, key=category_scores.get)
            confidence = min(category_scores[best_category] / 100, 1.0)
            if confidence > 0.1:
                return best_category, confidence
        
        return '其他', 0.1
    
    def extract_hexagrams(self, text: str) -> List[Dict[str, Any]]:
        """提取64卦相关内容"""
        hexagrams = []
        
        # 合并所有卦名模式
        all_patterns = '|'.join(self.HEXAGRAM_PATTERNS)
        pattern = re.compile(f'({all_patterns})', re.IGNORECASE)
        
        matches = pattern.finditer(text)
        for match in matches:
            hexagram_name = match.group(1)
            start_pos = match.start()
            
            # 提取卦名周围的上下文（前后各200字符）
            context_start = max(0, start_pos - 200)
            context_end = min(len(text), start_pos + 200)
            context = text[context_start:context_end].strip()
            
            hexagram_info = {
                'name': hexagram_name,
                'position': start_pos,
                'context': context,
                'extracted_at': datetime.now().isoformat()
            }
            
            hexagrams.append(hexagram_info)
        
        return hexagrams
    
    def extract_yaos(self, text: str) -> List[Dict[str, Any]]:
        """提取384爻相关内容"""
        yaos = []
        
        # 爻的模式：初九、九二、九三、九四、九五、上九等
        yao_patterns = [
            r'初[九六]',
            r'[九六]二',
            r'[九六]三', 
            r'[九六]四',
            r'[九六]五',
            r'上[九六]'
        ]
        
        for pattern in yao_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                yao_name = match.group(0)
                start_pos = match.start()
                
                # 提取爻辞上下文（前后各150字符）
                context_start = max(0, start_pos - 150)
                context_end = min(len(text), start_pos + 150)
                context = text[context_start:context_end].strip()
                
                yao_info = {
                    'name': yao_name,
                    'position': start_pos,
                    'context': context,
                    'extracted_at': datetime.now().isoformat()
                }
                
                yaos.append(yao_info)
        
        return yaos
    
    def extract_annotations(self, text: str) -> List[str]:
        """提取注解内容"""
        annotations = []
        
        # 注解标识模式
        annotation_patterns = [
            r'注[：:].*?(?=\n|$)',
            r'释[：:].*?(?=\n|$)',
            r'解[：:].*?(?=\n|$)',
            r'按[：:].*?(?=\n|$)',
            r'案[：:].*?(?=\n|$)',
            r'评[：:].*?(?=\n|$)',
            r'注释[：:].*?(?=\n|$)',
            r'注解[：:].*?(?=\n|$)'
        ]
        
        for pattern in annotation_patterns:
            matches = re.findall(pattern, text, re.MULTILINE)
            for match in matches:
                if len(match.strip()) > 10:  # 过滤太短的内容
                    annotations.append(match.strip())
        
        return list(set(annotations))  # 去重
    
    def extract_cases(self, text: str) -> List[Dict[str, Any]]:
        """提取案例内容"""
        cases = []
        
        # 案例标识模式
        case_patterns = [
            r'例[：:].*?(?=例[：:]|$)',
            r'案例[：:].*?(?=案例[：:]|$)',
            r'实例[：:].*?(?=实例[：:]|$)',
            r'验证[：:].*?(?=验证[：:]|$)'
        ]
        
        for i, pattern in enumerate(case_patterns):
            matches = re.finditer(pattern, text, re.DOTALL)
            for j, match in enumerate(matches):
                case_content = match.group(0).strip()
                if len(case_content) > 50:  # 过滤太短的案例
                    case_info = {
                        'id': f"case_{i}_{j}",
                        'content': case_content[:1000],  # 限制长度
                        'length': len(case_content),
                        'extracted_at': datetime.now().isoformat()
                    }
                    cases.append(case_info)
        
        return cases


def process_single_pdf(args: Tuple[Path, Path, int]) -> ExtractedContent:
    """处理单个PDF文件（用于多进程）"""
    file_path, output_dir, file_index = args
    processor = PDFProcessor("", output_dir)  # 临时实例
    
    start_time = time.time()
    error_messages = []
    
    try:
        # 提取文本
        text = processor.extract_text_multiple_methods(file_path)
        
        if not text or len(text) < 50:
            error_messages.append("文本提取失败或内容过短")
            text = ""
        
        # 自动分类
        category, confidence = processor.classify_pdf(text, file_path.name)
        
        # 提取各种内容
        hexagrams = processor.extract_hexagrams(text) if text else []
        yaos = processor.extract_yaos(text) if text else []
        annotations = processor.extract_annotations(text) if text else []
        cases = processor.extract_cases(text) if text else []
        
        # 创建结果对象
        result = ExtractedContent(
            filename=file_path.name,
            category=category,
            confidence=confidence,
            text_length=len(text),
            hexagrams=hexagrams,
            yaos=yaos,
            annotations=annotations,
            cases=cases,
            extraction_time=f"{time.time() - start_time:.2f}秒",
            error_messages=error_messages
        )
        
        return result
        
    except Exception as e:
        error_messages.append(f"处理异常: {str(e)}")
        processor.logger.error(f"处理文件 {file_path} 时出错: {e}")
        processor.logger.error(traceback.format_exc())
        
        return ExtractedContent(
            filename=file_path.name,
            category='其他',
            confidence=0.0,
            text_length=0,
            hexagrams=[],
            yaos=[],
            annotations=[],
            cases=[],
            extraction_time=f"{time.time() - start_time:.2f}秒",
            error_messages=error_messages
        )


class BatchPDFProcessor:
    """批量PDF处理管理器"""
    
    def __init__(self, data_dir: str, output_dir: str, max_workers: int = 4):
        self.data_dir = Path(data_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.max_workers = max_workers
        
        # 设置日志
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.output_dir / 'batch_processing.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
        self.results = []
        self.stats = {
            'total_files': 0,
            'processed_files': 0,
            'error_files': 0,
            'categories': {},
            'start_time': None,
            'end_time': None
        }
    
    def process_all_pdfs(self) -> Dict[str, Any]:
        """处理所有PDF文件"""
        self.logger.info("开始批量处理PDF文件...")
        self.stats['start_time'] = datetime.now()
        
        # 获取所有PDF文件
        pdf_files = list(self.data_dir.glob('*.pdf'))
        self.stats['total_files'] = len(pdf_files)
        
        if not pdf_files:
            self.logger.warning("未找到PDF文件")
            return self.generate_report()
        
        self.logger.info(f"发现 {len(pdf_files)} 个PDF文件")
        
        # 准备处理参数
        process_args = [
            (file_path, self.output_dir, i) 
            for i, file_path in enumerate(pdf_files)
        ]
        
        # 多进程处理
        with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
            # 提交所有任务
            future_to_file = {
                executor.submit(process_single_pdf, args): args[0] 
                for args in process_args
            }
            
            # 使用tqdm显示进度
            with tqdm(
                total=len(pdf_files), 
                desc="处理PDF文件", 
                unit="文件",
                ncols=100
            ) as pbar:
                
                for future in as_completed(future_to_file):
                    file_path = future_to_file[future]
                    
                    try:
                        result = future.result(timeout=300)  # 5分钟超时
                        self.results.append(result)
                        self.stats['processed_files'] += 1
                        
                        # 更新分类统计
                        category = result.category
                        if category not in self.stats['categories']:
                            self.stats['categories'][category] = 0
                        self.stats['categories'][category] += 1
                        
                        # 更新进度条描述
                        pbar.set_postfix({
                            '成功': self.stats['processed_files'],
                            '错误': self.stats['error_files'],
                            '当前': file_path.name[:20] + "..."
                        })
                        
                        if result.error_messages:
                            self.stats['error_files'] += 1
                            self.logger.warning(f"文件 {file_path.name} 处理有警告: {result.error_messages}")
                        
                    except Exception as e:
                        self.stats['error_files'] += 1
                        self.logger.error(f"处理文件 {file_path} 失败: {e}")
                        
                        # 添加错误结果
                        error_result = ExtractedContent(
                            filename=file_path.name,
                            category='其他',
                            confidence=0.0,
                            text_length=0,
                            hexagrams=[],
                            yaos=[],
                            annotations=[],
                            cases=[],
                            extraction_time="0.00秒",
                            error_messages=[f"处理失败: {str(e)}"]
                        )
                        self.results.append(error_result)
                    
                    pbar.update(1)
        
        self.stats['end_time'] = datetime.now()
        self.logger.info("批量处理完成")
        
        # 保存结果
        self.save_results()
        return self.generate_report()
    
    def save_results(self):
        """保存处理结果到JSON文件"""
        # 按类别分组保存
        categories_data = {}
        
        for result in self.results:
            category = result.category
            if category not in categories_data:
                categories_data[category] = []
            
            categories_data[category].append(asdict(result))
        
        # 保存每个类别的数据
        for category, data in categories_data.items():
            category_file = self.output_dir / f"{category}_提取结果.json"
            with open(category_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"保存 {category} 类别 {len(data)} 个文件的结果到 {category_file}")
        
        # 保存完整结果
        all_results_file = self.output_dir / "所有提取结果.json"
        all_data = [asdict(result) for result in self.results]
        with open(all_results_file, 'w', encoding='utf-8') as f:
            json.dump(all_data, f, ensure_ascii=False, indent=2)
        
        self.logger.info(f"保存完整结果到 {all_results_file}")
    
    def generate_report(self) -> Dict[str, Any]:
        """生成处理报告"""
        duration = None
        if self.stats['start_time'] and self.stats['end_time']:
            duration = self.stats['end_time'] - self.stats['start_time']
        
        # 计算详细统计
        successful_files = [r for r in self.results if not r.error_messages]
        error_files = [r for r in self.results if r.error_messages]
        
        total_hexagrams = sum(len(r.hexagrams) for r in successful_files)
        total_yaos = sum(len(r.yaos) for r in successful_files)
        total_annotations = sum(len(r.annotations) for r in successful_files)
        total_cases = sum(len(r.cases) for r in successful_files)
        
        report = {
            'processing_summary': {
                'total_files': self.stats['total_files'],
                'processed_successfully': len(successful_files),
                'files_with_errors': len(error_files),
                'processing_duration': str(duration) if duration else None,
                'start_time': self.stats['start_time'].isoformat() if self.stats['start_time'] else None,
                'end_time': self.stats['end_time'].isoformat() if self.stats['end_time'] else None
            },
            'content_statistics': {
                'total_hexagrams_extracted': total_hexagrams,
                'total_yaos_extracted': total_yaos,
                'total_annotations_extracted': total_annotations,
                'total_cases_extracted': total_cases,
                'average_text_length': sum(r.text_length for r in successful_files) / len(successful_files) if successful_files else 0
            },
            'category_distribution': self.stats['categories'],
            'error_summary': [
                {
                    'filename': r.filename,
                    'errors': r.error_messages
                }
                for r in error_files
            ]
        }
        
        # 保存报告
        report_file = self.output_dir / "处理报告.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        self.logger.info(f"生成处理报告: {report_file}")
        
        # 打印摘要
        print("\n" + "="*60)
        print("PDF批量处理完成报告")
        print("="*60)
        print(f"总文件数: {report['processing_summary']['total_files']}")
        print(f"成功处理: {report['processing_summary']['processed_successfully']}")
        print(f"处理错误: {report['processing_summary']['files_with_errors']}")
        print(f"处理耗时: {report['processing_summary']['processing_duration']}")
        print("\n内容提取统计:")
        print(f"- 提取卦象: {report['content_statistics']['total_hexagrams_extracted']} 个")
        print(f"- 提取爻辞: {report['content_statistics']['total_yaos_extracted']} 个")
        print(f"- 提取注解: {report['content_statistics']['total_annotations_extracted']} 个")
        print(f"- 提取案例: {report['content_statistics']['total_cases_extracted']} 个")
        print("\n类别分布:")
        for category, count in report['category_distribution'].items():
            print(f"- {category}: {count} 个文件")
        print("="*60)
        
        return report


def main():
    """主程序入口"""
    # 配置路径
    DATA_DIR = "/mnt/d/desktop/appp/data"
    OUTPUT_DIR = "/mnt/d/desktop/appp/extracted_data"
    MAX_WORKERS = 6  # 并行进程数
    
    print("PDF批量处理脚本启动")
    print(f"数据目录: {DATA_DIR}")
    print(f"输出目录: {OUTPUT_DIR}")
    print(f"并行进程: {MAX_WORKERS}")
    print("-" * 60)
    
    try:
        # 创建批量处理器
        processor = BatchPDFProcessor(
            data_dir=DATA_DIR,
            output_dir=OUTPUT_DIR,
            max_workers=MAX_WORKERS
        )
        
        # 开始处理
        report = processor.process_all_pdfs()
        
        print("\n处理完成！")
        print(f"结果已保存到: {OUTPUT_DIR}")
        
        return 0
        
    except KeyboardInterrupt:
        print("\n用户中断处理")
        return 1
    except Exception as e:
        print(f"\n处理过程中发生错误: {e}")
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())