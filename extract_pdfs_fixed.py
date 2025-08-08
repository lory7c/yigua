#!/usr/bin/env python3
"""
修复版PDF处理脚本 - 解决多进程pickle问题
"""

import os
import json
import re
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
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
    print("请安装依赖: pip install pdfplumber tqdm")
    exit(1)

# 配置简单的日志记录，避免pickle问题
def setup_logging():
    """设置日志记录"""
    logging.basicConfig(
        level=logging.WARNING,  # 减少日志输出
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger(__name__)

logger = setup_logging()

@dataclass
class PDFInfo:
    """PDF文件信息"""
    file_path: str
    file_name: str
    file_size: int
    pages: int
    category: str
    confidence: float
    priority: int
    processed_at: str
    text_length: int
    processing_time: float

@dataclass 
class ExtractedContent:
    """提取的内容"""
    hexagrams: List[Dict[str, Any]]
    yao_ci: List[Dict[str, Any]]
    annotations: List[Dict[str, Any]]
    cases: List[Dict[str, Any]]
    keywords: List[str]
    author: Optional[str]
    dynasty: Optional[str]

def classify_pdf(text: str, file_name: str) -> Tuple[str, float, int]:
    """分类PDF文件 - 独立函数避免pickle问题"""
    category_patterns = {
        "六爻": {
            "keywords": ["六爻", "卜易", "增删", "火珠林", "黄金策", "筮", "卦象", "爻辞", "爻变"],
            "priority": 1,
            "patterns": [r"六爻", r"筮\w*", r"卦象", r"爻\w+", r"动爻", r"变爻", r"世应", r"六亲", r"用神"]
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
        "周易基础": {
            "keywords": ["周易", "易经", "八卦", "六十四卦", "卦象"],
            "priority": 1,
            "patterns": [r"周易", r"易经", r"八卦", r"六十四卦"]
        }
    }
    
    text_lower = text.lower()
    file_lower = file_name.lower()
    
    category_scores = {}
    
    for category, config in category_patterns.items():
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
        if len(text) > 100:
            density = (total_keywords / len(text)) * 10000
            score += density
        
        category_scores[category] = score
    
    # 找出最高分
    if not category_scores or max(category_scores.values()) == 0:
        return "其他", 0.0, 5
    
    best_category = max(category_scores, key=category_scores.get)
    best_score = category_scores[best_category]
    
    confidence = min(best_score / 15.0, 1.0)
    priority = category_patterns[best_category]["priority"]
    
    return best_category, confidence, priority

def extract_hexagrams(text: str) -> List[Dict[str, Any]]:
    """提取64卦信息"""
    hexagram_names = [
        "乾", "坤", "屯", "蒙", "需", "讼", "师", "比",
        "小畜", "履", "泰", "否", "同人", "大有", "谦", "豫",
        "随", "蛊", "临", "观", "噬嗑", "贲", "剥", "复",
        "无妄", "大畜", "颐", "大过", "坎", "离", "咸", "恒",
        "遁", "大壮", "晋", "明夷", "家人", "睽", "蹇", "解",
        "损", "益", "夬", "姤", "萃", "升", "困", "井",
        "革", "鼎", "震", "艮", "渐", "归妹", "丰", "旅",
        "巽", "兑", "涣", "节", "中孚", "小过", "既济", "未济"
    ]
    
    hexagrams = []
    for i, name in enumerate(hexagram_names):
        patterns = [
            rf"{name}[卦]?[：:]\s*([^。\n]+)",
            rf"第\w*{name}卦[：:]\s*([^。\n]+)",
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                description = match.group(1).strip()
                if len(description) > 5:
                    hexagram = {
                        "number": i + 1,
                        "name": name,
                        "description": description,
                        "position": match.start(),
                    }
                    hexagrams.append(hexagram)
                    break  # 避免重复
    
    return hexagrams

def extract_yao_ci(text: str) -> List[Dict[str, Any]]:
    """提取爻辞"""
    yao_positions = ["初", "二", "三", "四", "五", "上"]
    yao_types = ["六", "九"]
    yao_ci = []
    
    for pos in yao_positions:
        for yao_type in yao_types:
            pattern = rf"({pos}{yao_type})[：:]([^。\n]{10,100})"
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

def extract_annotations(text: str) -> List[Dict[str, Any]]:
    """提取注解"""
    annotations = []
    annotation_patterns = [
        (r"注[：:]([^。\n]{10,200})", "注"),
        (r"解[：:]([^。\n]{10,200})", "解"),
        (r"释[：:]([^。\n]{10,200})", "释"),
        (r"按[：:]([^。\n]{10,200})", "按"),
        (r"曰[：:]([^。\n]{10,200})", "曰"),
    ]
    
    for pattern, ann_type in annotation_patterns:
        matches = re.finditer(pattern, text)
        for match in matches:
            content = match.group(1).strip()
            if len(content) > 10:
                annotation = {
                    "type": ann_type,
                    "content": content,
                    "position": match.start(),
                    "length": len(content)
                }
                annotations.append(annotation)
    
    return annotations

def extract_cases(text: str) -> List[Dict[str, Any]]:
    """提取案例"""
    cases = []
    case_patterns = [
        r"例[一二三四五六七八九十\d+][：:]([^。]{30,500})",
        r"案例[一二三四五六七八九十\d*][：:]([^。]{30,500})",
        r"实例[：:]([^。]{30,500})",
        r"占例[：:]([^。]{30,500})",
    ]
    
    for pattern in case_patterns:
        matches = re.finditer(pattern, text, re.DOTALL)
        for match in matches:
            content = match.group(1).strip()
            if len(content) >= 30:
                case = {
                    "content": content,
                    "position": match.start(),
                    "length": len(content),
                    "preview": content[:100] + "..." if len(content) > 100 else content
                }
                cases.append(case)
    
    return cases

def extract_keywords(text: str) -> List[str]:
    """提取关键词"""
    keywords = set()
    
    common_terms = [
        "阴阳", "五行", "八卦", "六爻", "占卜", "预测", "命理", 
        "风水", "周易", "太极", "神煞", "十神", "天干", "地支",
        "卦象", "爻变", "动爻", "静爻", "世应", "六亲", "用神"
    ]
    
    for term in common_terms:
        if term in text:
            keywords.add(term)
    
    # 提取书名
    book_names = re.findall(r'《([^》]{2,20})》', text)
    keywords.update(book_names[:5])
    
    return sorted(list(keywords))

def extract_author_dynasty(text: str, filename: str) -> Tuple[Optional[str], Optional[str]]:
    """提取作者和朝代"""
    author = None
    dynasty = None
    
    # 从文件名提取作者
    author_patterns = [
        r'([王李张刘陈杨赵黄周吴][\u4e00-\u9fff]{1,3})[_-]',
        r'^([^0-9\s\-_]+)',
    ]
    
    for pattern in author_patterns:
        match = re.search(pattern, filename)
        if match:
            potential_author = match.group(1)
            if len(potential_author) >= 2 and not any(char.isdigit() for char in potential_author):
                author = potential_author
                break
    
    # 朝代提取
    dynasty_patterns = [
        r'[(（]?(汉|唐|宋|元|明|清)[朝代)）]?',
        r'(汉|唐|宋|元|明|清)代',
    ]
    
    for pattern in dynasty_patterns:
        match = re.search(pattern, text)
        if match:
            dynasty = match.group(1)
            break
    
    return author, dynasty

def process_single_pdf_simple(file_path: str) -> Optional[Dict[str, Any]]:
    """简化的PDF处理函数 - 适用于多线程"""
    try:
        start_time = time.time()
        file_path = Path(file_path)
        
        # 提取文本
        text = ""
        page_count = 0
        
        with pdfplumber.open(file_path) as pdf:
            page_count = len(pdf.pages)
            max_pages = min(page_count, 100)  # 限制页数
            
            for i, page in enumerate(pdf.pages[:max_pages]):
                try:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
                except:
                    continue  # 跳过有问题的页面
        
        if not text.strip():
            return None
        
        # 分类
        category, confidence, priority = classify_pdf(text, file_path.name)
        
        # 提取内容
        hexagrams = extract_hexagrams(text)
        yao_ci = extract_yao_ci(text)
        annotations = extract_annotations(text)
        cases = extract_cases(text)
        keywords = extract_keywords(text)
        author, dynasty = extract_author_dynasty(text, file_path.name)
        
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
        
        return result
        
    except Exception as e:
        print(f"处理失败 {file_path}: {e}")
        return None

class PDFProcessorFixed:
    """修复版PDF处理器"""
    
    def __init__(self, data_dir: str, output_dir: str):
        self.data_dir = Path(data_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建子目录
        (self.output_dir / "raw_texts").mkdir(exist_ok=True)
        (self.output_dir / "structured_data").mkdir(exist_ok=True)
        (self.output_dir / "categories").mkdir(exist_ok=True)
        (self.output_dir / "reports").mkdir(exist_ok=True)
    
    def process_all_pdfs(self, max_workers: int = 6) -> Dict[str, Any]:
        """使用线程池处理所有PDF文件"""
        pdf_files = list(self.data_dir.glob("*.pdf"))
        print(f"找到 {len(pdf_files)} 个PDF文件")
        
        if len(pdf_files) == 0:
            return {"error": "没有找到PDF文件"}
        
        results = []
        failed_files = []
        
        # 使用线程池而不是进程池，避免pickle问题
        print("开始处理文件...")
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            with tqdm(total=len(pdf_files), desc="处理PDF") as pbar:
                # 提交任务
                future_to_file = {
                    executor.submit(process_single_pdf_simple, str(pdf_file)): pdf_file 
                    for pdf_file in pdf_files
                }
                
                # 收集结果
                for future in as_completed(future_to_file):
                    pdf_file = future_to_file[future]
                    try:
                        result = future.result()
                        if result:
                            results.append(result)
                            pbar.set_postfix_str(f"成功: {pdf_file.name[:20]}...")
                        else:
                            failed_files.append(pdf_file.name)
                            pbar.set_postfix_str(f"失败: {pdf_file.name[:20]}...")
                    except Exception as e:
                        failed_files.append(pdf_file.name)
                        pbar.set_postfix_str(f"错误: {pdf_file.name[:20]}...")
                    finally:
                        pbar.update(1)
        
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
        
        # 生成摘要报告
        self.generate_summary_report(results, timestamp)
        
        print(f"结果已保存到: {self.output_dir}")
        return full_results_file
    
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
            for failed_file in stats["failed_file_list"][:10]:  # 只显示前10个
                report += f"- {failed_file}\n"
            if len(stats["failed_file_list"]) > 10:
                report += f"- ... 还有 {len(stats['failed_file_list']) - 10} 个文件\n"
        
        report += f"""
## 💾 输出文件
- 完整结果: `structured_data/complete_results_{timestamp}.json`
- 统计信息: `structured_data/statistics_{timestamp}.json`
- 分类结果: `categories/` 目录下按类别保存

## 📝 使用建议
1. 优先级1的文件包含最重要的易学内容
2. 按类别查看专门的JSON文件
3. 失败的文件可能是扫描版或损坏的PDF
"""
        
        # 保存报告
        report_file = self.output_dir / f"processing_report_{timestamp}.md"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
        
        print(report)
        return report_file

def main():
    """主函数"""
    data_dir = "/mnt/d/desktop/appp/data"
    output_dir = "/mnt/d/desktop/appp/structured_data"
    
    print("🚀 开始批量处理易学PDF文件 (修复版)")
    print(f"📂 数据目录: {data_dir}")
    print(f"📁 输出目录: {output_dir}")
    
    # 创建处理器
    processor = PDFProcessorFixed(data_dir, output_dir)
    
    # 检查数据目录
    if not Path(data_dir).exists():
        print(f"❌ 数据目录不存在: {data_dir}")
        return
    
    # 开始处理
    start_time = datetime.now()
    print(f"⏰ 开始时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # 使用6个线程并行处理
        print("🔄 开始多线程处理...")
        results = processor.process_all_pdfs(max_workers=6)
        
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
        
        # 显示分类统计
        if results['statistics']['categories']:
            print(f"\n📚 分类统计:")
            for category, count in results['statistics']['categories'].items():
                print(f"  - {category}: {count} 个文件")
            
    except KeyboardInterrupt:
        print("\n⚠️ 用户中断处理")
    except Exception as e:
        print(f"\n❌ 处理过程中出错: {e}")

if __name__ == "__main__":
    main()