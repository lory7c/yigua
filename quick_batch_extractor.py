#!/usr/bin/env python3
"""
快速批量PDF提取器 - 简化版
专注于高效完成191个PDF文件的处理任务
"""

import os
import json
import time
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
import traceback

# PDF处理库
try:
    import pdfplumber
    import fitz  # PyMuPDF
    from tqdm import tqdm
except ImportError as e:
    print(f"缺少依赖: {e}")
    exit(1)

class QuickPDFExtractor:
    """快速PDF提取器"""
    
    def __init__(self, source_dir: str, output_dir: str):
        self.source_dir = Path(source_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 设置日志
        self.logger = self._setup_logging()
        
        # 分类关键词
        self.categories = {
            "六爻": ["六爻", "卜易", "增删", "火珠林", "黄金策", "世应", "用神"],
            "大六壬": ["六壬", "壬学", "课传", "四课", "三传", "神将"],
            "周易基础": ["周易", "易经", "八卦", "卦辞", "象传", "彖传"],
            "梅花易数": ["梅花", "易数", "观梅", "体用", "互卦", "变卦"],
            "紫微斗数": ["紫微", "斗数", "命盘", "宫位", "星曜", "化禄"],
            "奇门遁甲": ["奇门", "遁甲", "九宫", "八门", "三奇", "值符"],
            "八字命理": ["八字", "四柱", "干支", "十神", "用神"],
            "其他术数": ["占卜", "预测", "相术", "风水", "择日"]
        }
    
    def _setup_logging(self):
        """设置日志"""
        logger = logging.getLogger("QuickExtractor")
        logger.setLevel(logging.INFO)
        
        # 清除现有handler
        for handler in logger.handlers:
            logger.removeHandler(handler)
        
        # 文件handler
        log_file = self.output_dir / f"quick_extract_{datetime.now().strftime('%H%M%S')}.log"
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        
        # 控制台handler
        console_handler = logging.StreamHandler()
        
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
        return logger
    
    def extract_text_pdfplumber(self, pdf_path: Path) -> str:
        """使用pdfplumber提取文本"""
        try:
            text_parts = []
            with pdfplumber.open(pdf_path) as pdf:
                max_pages = min(len(pdf.pages), 100)  # 限制页数提高速度
                for i in range(max_pages):
                    try:
                        page = pdf.pages[i]
                        page_text = page.extract_text()
                        if page_text and len(page_text.strip()) > 20:
                            text_parts.append(page_text)
                    except Exception:
                        continue
            return '\n'.join(text_parts)
        except Exception as e:
            raise Exception(f"pdfplumber提取失败: {e}")
    
    def extract_text_pymupdf(self, pdf_path: Path) -> str:
        """使用PyMuPDF提取文本"""
        try:
            text_parts = []
            doc = fitz.open(pdf_path)
            max_pages = min(len(doc), 100)
            
            for page_num in range(max_pages):
                try:
                    page = doc.load_page(page_num)
                    page_text = page.get_text()
                    if page_text and len(page_text.strip()) > 15:
                        text_parts.append(page_text)
                except Exception:
                    continue
            
            doc.close()
            return '\n'.join(text_parts)
        except Exception as e:
            raise Exception(f"PyMuPDF提取失败: {e}")
    
    def classify_content(self, text: str, filename: str) -> str:
        """简单内容分类"""
        if not text:
            return "其他术数"
        
        text_lower = text.lower()
        filename_lower = filename.lower()
        
        for category, keywords in self.categories.items():
            score = 0
            # 文件名匹配
            score += sum(1 for kw in keywords if kw in filename_lower) * 3
            # 内容匹配
            score += sum(1 for kw in keywords if kw in text_lower)
            
            if score >= 2:  # 简单阈值
                return category
        
        return "其他术数"
    
    def process_single_pdf(self, pdf_path: Path) -> Dict[str, Any]:
        """处理单个PDF文件"""
        start_time = time.time()
        
        try:
            # 尝试多种提取方法
            text = ""
            method_used = "failed"
            
            # 方法1: pdfplumber
            try:
                text = self.extract_text_pdfplumber(pdf_path)
                if len(text.strip()) >= 50:
                    method_used = "pdfplumber"
                else:
                    text = ""
            except Exception:
                pass
            
            # 方法2: PyMuPDF（如果pdfplumber失败）
            if not text:
                try:
                    text = self.extract_text_pymupdf(pdf_path)
                    if len(text.strip()) >= 50:
                        method_used = "pymupdf"
                except Exception:
                    pass
            
            if not text or len(text.strip()) < 50:
                return {
                    "file_name": pdf_path.name,
                    "file_path": str(pdf_path),
                    "status": "failed",
                    "error": "文本提取失败或内容过短",
                    "processing_time": time.time() - start_time
                }
            
            # 分类
            category = self.classify_content(text, pdf_path.name)
            
            # 基础统计
            stats = {
                "text_length": len(text),
                "word_count": len(text.split()),
                "line_count": text.count('\n')
            }
            
            # 提取关键信息
            structured_content = self.extract_key_content(text)
            
            result = {
                "file_name": pdf_path.name,
                "file_path": str(pdf_path),
                "file_size": pdf_path.stat().st_size,
                "status": "success",
                "method_used": method_used,
                "category": category,
                "statistics": stats,
                "structured_content": structured_content,
                "raw_text": text[:5000],  # 保存前5000字符
                "processing_time": time.time() - start_time,
                "processed_at": datetime.now().isoformat()
            }
            
            return result
            
        except Exception as e:
            return {
                "file_name": pdf_path.name,
                "file_path": str(pdf_path),
                "status": "failed",
                "error": str(e),
                "processing_time": time.time() - start_time
            }
    
    def extract_key_content(self, text: str) -> Dict[str, Any]:
        """提取关键内容"""
        import re
        
        content = {
            "keywords": [],
            "hexagrams": [],
            "yao_info": [],
            "cases": []
        }
        
        # 提取关键词
        yixue_terms = ["阴阳", "五行", "八卦", "太极", "占卜", "预测", "世应", "六亲", "用神", "忌神"]
        for term in yixue_terms:
            if term in text:
                content["keywords"].append(term)
        
        # 提取64卦名
        hexagram_names = ["乾", "坤", "屯", "蒙", "需", "讼", "师", "比", "小畜", "履"]
        for name in hexagram_names:
            if name in text:
                matches = re.findall(rf"{name}[卦]?[：:]\s*([^。\n]{{10,100}})", text)
                for match in matches[:2]:  # 最多2个
                    content["hexagrams"].append({
                        "name": name,
                        "description": match.strip()
                    })
        
        # 提取爻辞信息
        yao_patterns = [r"(初|二|三|四|五|上)(六|九)[：:]\s*([^。\n]{10,150})"]
        for pattern in yao_patterns:
            matches = re.findall(pattern, text)
            for pos, type_val, desc in matches[:5]:  # 最多5个
                content["yao_info"].append({
                    "position": pos,
                    "type": type_val,
                    "description": desc.strip()
                })
        
        # 提取案例
        case_patterns = [r"例[一二三四五\d]*[：:]\s*([^。]{30,200})"]
        for pattern in case_patterns:
            matches = re.findall(pattern, text, re.DOTALL)
            for match in matches[:3]:  # 最多3个案例
                content["cases"].append(match.strip())
        
        return content
    
    def run_batch_processing(self, max_workers: int = 4) -> Dict[str, Any]:
        """运行批量处理"""
        self.logger.info("🚀 启动快速批量PDF提取")
        
        # 扫描PDF文件
        pdf_files = list(self.source_dir.glob("*.pdf"))
        total_files = len(pdf_files)
        
        if total_files == 0:
            self.logger.error("没有找到PDF文件")
            return {"status": "error", "message": "没有找到PDF文件"}
        
        self.logger.info(f"📋 发现 {total_files} 个PDF文件")
        
        # 按文件大小排序（小文件优先）
        pdf_files.sort(key=lambda f: f.stat().st_size)
        
        results = []
        successful_count = 0
        failed_count = 0
        
        start_time = time.time()
        
        # 使用线程池并发处理
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有任务
            future_to_file = {
                executor.submit(self.process_single_pdf, pdf_file): pdf_file 
                for pdf_file in pdf_files
            }
            
            # 显示进度条并收集结果
            with tqdm(total=total_files, desc="处理PDF文件", unit="文件") as pbar:
                for future in as_completed(future_to_file):
                    pdf_file = future_to_file[future]
                    
                    try:
                        result = future.result(timeout=120)  # 2分钟超时
                        results.append(result)
                        
                        if result["status"] == "success":
                            successful_count += 1
                            pbar.set_postfix({"成功": successful_count, "失败": failed_count})
                        else:
                            failed_count += 1
                            self.logger.warning(f"处理失败: {pdf_file.name} - {result.get('error', 'Unknown')}")
                            
                    except Exception as e:
                        failed_count += 1
                        self.logger.error(f"处理异常: {pdf_file.name} - {str(e)}")
                        results.append({
                            "file_name": pdf_file.name,
                            "status": "failed",
                            "error": f"处理超时或异常: {str(e)}"
                        })
                    
                    pbar.update(1)
        
        total_time = time.time() - start_time
        success_rate = (successful_count / total_files) * 100
        
        # 生成报告
        report = {
            "status": "completed",
            "summary": {
                "total_files": total_files,
                "successful_files": successful_count,
                "failed_files": failed_count,
                "success_rate": success_rate,
                "processing_time_minutes": total_time / 60,
                "files_per_minute": total_files / (total_time / 60)
            },
            "processing_timestamp": datetime.now().isoformat(),
            "results": results
        }
        
        # 保存结果
        self.save_results(report)
        
        self.logger.info(f"✅ 处理完成!")
        self.logger.info(f"📊 成功率: {success_rate:.1f}%")
        self.logger.info(f"⏰ 总耗时: {total_time/60:.1f} 分钟")
        self.logger.info(f"🚀 处理速度: {total_files/(total_time/60):.1f} 文件/分钟")
        
        return report
    
    def save_results(self, report: Dict[str, Any]):
        """保存结果"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 完整结果
        results_file = self.output_dir / f"quick_results_{timestamp}.json"
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        # 按类别统计
        category_stats = {}
        for result in report["results"]:
            if result["status"] == "success":
                category = result["category"]
                if category not in category_stats:
                    category_stats[category] = []
                category_stats[category].append(result["file_name"])
        
        # 分类统计
        stats_file = self.output_dir / f"category_stats_{timestamp}.json"
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump({
                "category_statistics": {cat: len(files) for cat, files in category_stats.items()},
                "category_details": category_stats,
                "total_categories": len(category_stats)
            }, f, ensure_ascii=False, indent=2)
        
        # 简化HTML报告
        self.generate_html_report(report, timestamp)
        
        self.logger.info(f"📄 结果文件: {results_file}")
        self.logger.info(f"📊 统计文件: {stats_file}")
    
    def generate_html_report(self, report: Dict[str, Any], timestamp: str):
        """生成HTML报告"""
        summary = report["summary"]
        
        # 分类统计
        category_stats = {}
        for result in report["results"]:
            if result["status"] == "success":
                category = result["category"]
                category_stats[category] = category_stats.get(category, 0) + 1
        
        html_content = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>快速PDF提取报告 - {timestamp}</title>
    <style>
        body {{ font-family: 'Microsoft YaHei', Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
        .container {{ max-width: 1000px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 0 20px rgba(0,0,0,0.1); }}
        .header {{ text-align: center; color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 20px; margin-bottom: 30px; }}
        .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin: 20px 0; }}
        .stat-card {{ background: linear-gradient(135deg, #3498db, #2980b9); color: white; padding: 20px; border-radius: 8px; text-align: center; }}
        .stat-number {{ font-size: 2.5em; font-weight: bold; }}
        .stat-label {{ margin-top: 10px; opacity: 0.9; }}
        .categories {{ margin-top: 30px; }}
        .category-item {{ background: #ecf0f1; margin: 10px 0; padding: 15px; border-radius: 5px; border-left: 4px solid #3498db; }}
        .success {{ color: #27ae60; }}
        .error {{ color: #e74c3c; }}
        h2 {{ color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }}
        .footer {{ text-align: center; margin-top: 30px; color: #7f8c8d; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 快速PDF提取报告</h1>
            <p>处理时间: {timestamp}</p>
            <p class="{'success' if summary['success_rate'] >= 90 else 'error'}">
                成功率: {summary['success_rate']:.1f}% 
                ({'🎉 优秀!' if summary['success_rate'] >= 90 else '⚠️ 需要优化' if summary['success_rate'] >= 70 else '❌ 失败率过高'})
            </p>
        </div>
        
        <div class="stats">
            <div class="stat-card">
                <div class="stat-number">{summary['total_files']}</div>
                <div class="stat-label">📄 总文件数</div>
            </div>
            <div class="stat-card" style="background: linear-gradient(135deg, #27ae60, #2ecc71);">
                <div class="stat-number">{summary['successful_files']}</div>
                <div class="stat-label">✅ 成功处理</div>
            </div>
            <div class="stat-card" style="background: linear-gradient(135deg, #e74c3c, #c0392b);">
                <div class="stat-number">{summary['failed_files']}</div>
                <div class="stat-label">❌ 处理失败</div>
            </div>
            <div class="stat-card" style="background: linear-gradient(135deg, #f39c12, #e67e22);">
                <div class="stat-number">{summary['processing_time_minutes']:.1f}m</div>
                <div class="stat-label">⏰ 总耗时</div>
            </div>
        </div>
        
        <div class="categories">
            <h2>📚 内容分类分布</h2>
        """
        
        for category, count in sorted(category_stats.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / max(summary['successful_files'], 1)) * 100
            html_content += f"""
            <div class="category-item">
                <strong>{category}</strong>: {count} 个文件 ({percentage:.1f}%)
            </div>
            """
        
        html_content += f"""
        </div>
        
        <div class="footer">
            <p>🤖 快速PDF提取器自动生成 | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p>处理速度: {summary['files_per_minute']:.1f} 文件/分钟</p>
        </div>
    </div>
</body>
</html>
        """
        
        html_file = self.output_dir / f"quick_report_{timestamp}.html"
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        self.logger.info(f"📄 HTML报告: {html_file}")

def main():
    """主函数"""
    print("🚀 快速批量PDF提取器")
    print("专为191个PDF文件快速处理优化")
    print("=" * 50)
    
    source_dir = "/mnt/d/desktop/appp/data"
    output_dir = "/mnt/d/desktop/appp/structured_data"
    
    # 检查源目录
    if not Path(source_dir).exists():
        print(f"❌ 源目录不存在: {source_dir}")
        return
    
    pdf_count = len(list(Path(source_dir).glob("*.pdf")))
    print(f"📋 发现 {pdf_count} 个PDF文件")
    
    if pdf_count == 0:
        print("❌ 没有找到PDF文件")
        return
    
    # 创建提取器并运行
    extractor = QuickPDFExtractor(source_dir, output_dir)
    
    print(f"⚡ 开始快速处理...")
    start_time = time.time()
    
    try:
        # 使用适当的并发数
        max_workers = min(8, pdf_count // 10 + 1)
        report = extractor.run_batch_processing(max_workers=max_workers)
        
        elapsed_time = time.time() - start_time
        
        print(f"\n🎉 处理完成!")
        print(f"📊 总文件: {report['summary']['total_files']}")
        print(f"✅ 成功: {report['summary']['successful_files']}")
        print(f"❌ 失败: {report['summary']['failed_files']}")
        print(f"📈 成功率: {report['summary']['success_rate']:.1f}%")
        print(f"⏰ 总耗时: {elapsed_time/60:.1f} 分钟")
        print(f"🚀 处理速度: {report['summary']['files_per_minute']:.1f} 文件/分钟")
        print(f"📁 结果保存在: {output_dir}")
        
        # 检查是否达到目标
        if report['summary']['success_rate'] >= 90:
            print("🎯 目标达成: 成功率 ≥ 90%!")
        else:
            print(f"⚠️ 成功率({report['summary']['success_rate']:.1f}%) < 90%，需要优化")
            
    except Exception as e:
        print(f"❌ 处理失败: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    main()