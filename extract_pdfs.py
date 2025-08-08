#!/usr/bin/env python3
"""
高效批量易学PDF文件处理脚本
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

try:
    import pdfplumber
except ImportError:
    print("请安装pdfplumber: pip install pdfplumber")
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
    
class PDFProcessor:
    """PDF处理器"""
    
    def __init__(self, data_dir: str, output_dir: str):
        self.data_dir = Path(data_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建子目录
        (self.output_dir / "raw_texts").mkdir(exist_ok=True)
        (self.output_dir / "structured_data").mkdir(exist_ok=True)
        (self.output_dir / "categories").mkdir(exist_ok=True)
        (self.output_dir / "cache").mkdir(exist_ok=True)
        
        # 分类模式
        self.category_patterns = {
            "六爻": {
                "keywords": ["六爻", "卜易", "增删", "火珠林", "黄金策", "筮", "卦象", "爻辞"],
                "priority": 1,
                "patterns": [r"六爻", r"筮\w*", r"卦象", r"爻\w+", r"动爻", r"变爻"]
            },
            "梅花易数": {
                "keywords": ["梅花", "易数", "梅花易", "观梅", "数理"],
                "priority": 2,
                "patterns": [r"梅花\w*易\w*", r"观梅", r"易数", r"数理"]
            },
            "大六壬": {
                "keywords": ["六壬", "壬学", "壬占", "课传", "神将", "十二将"],
                "priority": 1,
                "patterns": [r"六壬", r"壬占", r"课传", r"神将", r"十二将"]
            },
            "紫微斗数": {
                "keywords": ["紫微", "斗数", "命盘", "宫位", "星曜"],
                "priority": 2,
                "patterns": [r"紫微\w*斗数", r"命盘", r"宫位", r"星曜"]
            },
            "奇门遁甲": {
                "keywords": ["奇门", "遁甲", "九宫", "八门", "神煞"],
                "priority": 2,
                "patterns": [r"奇门\w*遁甲", r"九宫", r"八门", r"神煞"]
            },
            "八字命理": {
                "keywords": ["八字", "四柱", "命理", "干支", "纳音"],
                "priority": 2,
                "patterns": [r"八字", r"四柱", r"命理", r"干支", r"纳音"]
            },
            "金口诀": {
                "keywords": ["金口诀", "金口", "课式"],
                "priority": 3,
                "patterns": [r"金口\w*诀", r"金口", r"课式"]
            },
            "太乙神数": {
                "keywords": ["太乙", "神数", "太乙神数"],
                "priority": 3,
                "patterns": [r"太乙\w*神数", r"太乙"]
            },
            "河洛理数": {
                "keywords": ["河洛", "理数", "河图", "洛书"],
                "priority": 3,
                "patterns": [r"河洛\w*理数", r"河图", r"洛书"]
            },
            "周易基础": {
                "keywords": ["周易", "易经", "八卦", "六十四卦", "卦象"],
                "priority": 1,
                "patterns": [r"周易", r"易经", r"八卦", r"六十四卦"]
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
    
    def load_cache(self) -> Dict[str, Any]:
        """加载缓存"""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'rb') as f:
                    return pickle.load(f)
            except Exception as e:
                logger.warning(f"缓存加载失败: {e}")
        return {}
    
    def save_cache(self):
        """保存缓存"""
        try:
            with open(self.cache_file, 'wb') as f:
                pickle.dump(self.processed_files, f)
        except Exception as e:
            logger.error(f"缓存保存失败: {e}")
    
    def get_file_hash(self, file_path: Path) -> str:
        """获取文件哈希"""
        stat = file_path.stat()
        return hashlib.md5(f"{file_path}_{stat.st_size}_{stat.st_mtime}".encode()).hexdigest()
    
    def classify_pdf(self, text: str, file_name: str) -> Tuple[str, float, int]:
        """分类PDF文件"""
        text_lower = text.lower()
        file_lower = file_name.lower()
        
        best_category = "其他"
        best_confidence = 0.0
        best_priority = 5
        
        for category, config in self.category_patterns.items():
            confidence = 0.0
            
            # 文件名匹配
            for keyword in config["keywords"]:
                if keyword in file_lower:
                    confidence += 2.0
            
            # 内容模式匹配
            for pattern in config["patterns"]:
                matches = len(re.findall(pattern, text, re.IGNORECASE))
                confidence += matches * 0.5
            
            # 关键词密度
            total_keywords = sum(text_lower.count(kw) for kw in config["keywords"])
            if len(text) > 0:
                confidence += (total_keywords / len(text)) * 1000
            
            if confidence > best_confidence:
                best_confidence = confidence
                best_category = category
                best_priority = config["priority"]
        
        # 归一化置信度
        confidence_normalized = min(best_confidence / 10.0, 1.0)
        
        return best_category, confidence_normalized, best_priority
    
    def extract_hexagrams(self, text: str) -> List[Dict[str, Any]]:
        """提取64卦信息"""
        hexagrams = []
        
        for i, name in enumerate(self.hexagram_names):
            # 查找卦名及其描述
            pattern = rf"{name}[卦]?[：:]\s*([^。]+[。]?)"
            matches = re.finditer(pattern, text)
            
            for match in matches:
                hexagram = {
                    "number": i + 1,
                    "name": name,
                    "description": match.group(1).strip(),
                    "position": match.start()
                }
                hexagrams.append(hexagram)
        
        return hexagrams
    
    def extract_yao_ci(self, text: str) -> List[Dict[str, Any]]:
        """提取爻辞"""
        yao_positions = ["初", "二", "三", "四", "五", "上"]
        yao_types = ["六", "九"]
        yao_ci = []
        
        for pos in yao_positions:
            for yao_type in yao_types:
                # 匹配爻辞格式：初六、九二等
                pattern = rf"({pos}{yao_type})[：:]([^。]+[。]?)"
                matches = re.finditer(pattern, text)
                
                for match in matches:
                    yao = {
                        "position": pos,
                        "type": yao_type,
                        "full_name": match.group(1),
                        "text": match.group(2).strip(),
                        "location": match.start()
                    }
                    yao_ci.append(yao)
        
        return yao_ci
    
    def extract_annotations(self, text: str) -> List[Dict[str, Any]]:
        """提取注解"""
        annotations = []
        
        # 注解模式
        annotation_patterns = [
            r"注[：:]([^。]+[。]?)",
            r"解[：:]([^。]+[。]?)",
            r"释[：:]([^。]+[。]?)",
            r"按[：:]([^。]+[。]?)",
            r"曰[：:]([^。]+[。]?)"
        ]
        
        for pattern in annotation_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                annotation = {
                    "type": match.group(0)[0],
                    "content": match.group(1).strip(),
                    "position": match.start()
                }
                annotations.append(annotation)
        
        return annotations
    
    def extract_cases(self, text: str) -> List[Dict[str, Any]]:
        """提取案例"""
        cases = []
        
        # 案例模式
        case_patterns = [
            r"例[一二三四五六七八九十\d+][：:]([^。]{20,}[。])",
            r"案例[：:]([^。]{20,}[。])",
            r"实例[：:]([^。]{20,}[。])",
            r"占例[：:]([^。]{20,}[。])"
        ]
        
        for pattern in case_patterns:
            matches = re.finditer(pattern, text, re.DOTALL)
            for match in matches:
                case = {
                    "content": match.group(1).strip(),
                    "position": match.start(),
                    "length": len(match.group(1))
                }
                cases.append(case)
        
        return cases
    
    def extract_keywords(self, text: str) -> List[str]:
        """提取关键词"""
        keywords = set()
        
        # 常见易学术语
        common_terms = [
            "阴阳", "五行", "八卦", "六爻", "占卜", "预测", "命理", 
            "风水", "周易", "太极", "神煞", "十神", "天干", "地支",
            "卦象", "爻变", "动爻", "静爻", "世应", "六亲", "用神"
        ]
        
        for term in common_terms:
            if term in text:
                keywords.add(term)
        
        # 提取专有名词
        proper_nouns = re.findall(r'《([^》]+)》', text)
        keywords.update(proper_nouns[:10])  # 限制数量
        
        return sorted(list(keywords))
    
    def extract_author_dynasty(self, text: str, filename: str) -> Tuple[Optional[str], Optional[str]]:
        """提取作者和朝代"""
        author = None
        dynasty = None
        
        # 从文件名提取
        author_match = re.search(r'([^-_\s]+)[_-]', filename)
        if author_match:
            potential_author = author_match.group(1)
            if not any(char.isdigit() for char in potential_author):
                author = potential_author
        
        # 朝代模式
        dynasty_patterns = [
            r'(宋|明|清|元|唐|汉)[朝代]?',
            r'[(（](宋|明|清|元|唐|汉)[)）]'
        ]
        
        for pattern in dynasty_patterns:
            match = re.search(pattern, text)
            if match:
                dynasty = match.group(1)
                break
        
        return author, dynasty
    
    def process_single_pdf(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """处理单个PDF文件"""
        try:
            # 检查缓存
            file_hash = self.get_file_hash(file_path)
            if file_hash in self.processed_files:
                logger.info(f"跳过已处理文件: {file_path.name}")
                return self.processed_files[file_hash]
            
            logger.info(f"处理文件: {file_path.name}")
            
            # 提取文本
            text = ""
            page_count = 0
            
            with pdfplumber.open(file_path) as pdf:
                page_count = len(pdf.pages)
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
            
            if not text.strip():
                logger.warning(f"无法提取文本: {file_path.name}")
                return None
            
            # 分类
            category, confidence, priority = self.classify_pdf(text, file_path.name)
            
            # 创建PDF信息
            pdf_info = PDFInfo(
                file_path=str(file_path),
                file_name=file_path.name,
                file_size=file_path.stat().st_size,
                pages=page_count,
                category=category,
                confidence=confidence,
                priority=priority,
                processed_at=datetime.now().isoformat(),
                text_length=len(text)
            )
            
            # 提取结构化内容
            extracted_content = ExtractedContent(
                hexagrams=self.extract_hexagrams(text),
                yao_ci=self.extract_yao_ci(text),
                annotations=self.extract_annotations(text),
                cases=self.extract_cases(text),
                keywords=self.extract_keywords(text),
                *self.extract_author_dynasty(text, file_path.name)
            )
            
            # 构建结果
            result = {
                "pdf_info": asdict(pdf_info),
                "content": asdict(extracted_content),
                "raw_text": text[:5000] + "..." if len(text) > 5000 else text  # 截取前5000字符
            }
            
            # 保存到缓存
            self.processed_files[file_hash] = result
            
            # 保存原始文本
            text_file = self.output_dir / "raw_texts" / f"{file_path.stem}.txt"
            with open(text_file, 'w', encoding='utf-8') as f:
                f.write(text)
            
            return result
            
        except Exception as e:
            logger.error(f"处理文件失败 {file_path.name}: {e}")
            return None
    
    def process_all_pdfs(self, max_workers: int = 4) -> Dict[str, Any]:
        """并行处理所有PDF文件"""
        pdf_files = list(self.data_dir.glob("*.pdf"))
        logger.info(f"找到 {len(pdf_files)} 个PDF文件")
        
        results = []
        failed_files = []
        
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            # 提交任务
            future_to_file = {
                executor.submit(self.process_single_pdf, pdf_file): pdf_file 
                for pdf_file in pdf_files
            }
            
            # 收集结果
            for i, future in enumerate(as_completed(future_to_file)):
                pdf_file = future_to_file[future]
                try:
                    result = future.result()
                    if result:
                        results.append(result)
                        logger.info(f"完成 {i+1}/{len(pdf_files)}: {pdf_file.name}")
                    else:
                        failed_files.append(pdf_file.name)
                except Exception as e:
                    logger.error(f"任务失败 {pdf_file.name}: {e}")
                    failed_files.append(pdf_file.name)
                
                # 定期保存缓存
                if (i + 1) % 10 == 0:
                    self.save_cache()
        
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
        
        # 统计信息
        stats = {
            "total_files": len(pdf_files),
            "processed_successfully": len(results),
            "failed_files": len(failed_files),
            "categories": {cat: len(files) for cat, files in categorized_results.items()},
            "priorities": {f"优先级{p}": len(files) for p, files in priority_results.items()},
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
            category_file = self.output_dir / "categories" / f"{category}_{timestamp}.json"
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
        
        # 生成摘要报告
        self.generate_summary_report(results, timestamp)
        
        logger.info(f"结果已保存到: {self.output_dir}")
        logger.info(f"完整结果: {full_results_file}")
        logger.info(f"统计信息: {stats_file}")
    
    def generate_summary_report(self, results: Dict[str, Any], timestamp: str):
        """生成摘要报告"""
        stats = results["statistics"]
        
        report = f"""
# PDF处理摘要报告
时间: {timestamp}

## 处理统计
- 总文件数: {stats['total_files']}
- 成功处理: {stats['processed_successfully']}
- 失败数量: {stats['failed_files']}
- 成功率: {stats['processed_successfully']/stats['total_files']*100:.1f}%

## 分类统计
"""
        
        for category, count in stats["categories"].items():
            report += f"- {category}: {count} 个文件\n"
        
        report += "\n## 优先级分布\n"
        for priority, count in stats["priorities"].items():
            report += f"- {priority}: {count} 个文件\n"
        
        if stats["failed_files"]:
            report += f"\n## 失败文件\n"
            for failed_file in stats["failed_file_list"]:
                report += f"- {failed_file}\n"
        
        # 保存报告
        report_file = self.output_dir / f"processing_report_{timestamp}.md"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
        
        print(report)

def main():
    """主函数"""
    # 配置路径
    data_dir = "/mnt/d/desktop/appp/data"
    output_dir = "/mnt/d/desktop/appp/structured_data"
    
    print("🚀 开始批量处理易学PDF文件...")
    print(f"📂 数据目录: {data_dir}")
    print(f"📁 输出目录: {output_dir}")
    
    # 创建处理器
    processor = PDFProcessor(data_dir, output_dir)
    
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
    print(f"⏰ 开始时间: {start_time}")
    
    try:
        # 使用4个进程并行处理
        results = processor.process_all_pdfs(max_workers=4)
        
        # 保存结果
        processor.save_results(results)
        
        end_time = datetime.now()
        duration = end_time - start_time
        
        print(f"\n✅ 处理完成!")
        print(f"⏰ 耗时: {duration}")
        print(f"📊 成功处理: {results['statistics']['processed_successfully']}/{results['statistics']['total_files']}")
        print(f"📁 结果保存在: {output_dir}")
        
    except KeyboardInterrupt:
        print("\n⚠️ 用户中断处理")
        processor.save_cache()  # 保存已处理的缓存
    except Exception as e:
        print(f"\n❌ 处理过程中出错: {e}")
        logger.error(f"处理异常: {e}", exc_info=True)

if __name__ == "__main__":
    main()