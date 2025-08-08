#!/usr/bin/env python3
"""
PDF处理结果分析脚本
提供结果查询、统计和导出功能
"""

import json
import os
from pathlib import Path
from datetime import datetime
from collections import defaultdict, Counter
import re

class ResultAnalyzer:
    """结果分析器"""
    
    def __init__(self, structured_data_dir: str):
        self.structured_data_dir = Path(structured_data_dir)
        self.results = None
        self.stats = None
        
    def load_latest_results(self):
        """加载最新的处理结果"""
        results_dir = self.structured_data_dir / "structured_data"
        if not results_dir.exists():
            print("❌ 未找到结果目录")
            return False
            
        # 查找最新的结果文件
        result_files = list(results_dir.glob("complete_results_*.json"))
        if not result_files:
            print("❌ 未找到结果文件")
            return False
            
        latest_file = max(result_files, key=lambda x: x.stat().st_mtime)
        
        try:
            with open(latest_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.results = data.get('results', [])
                self.stats = data.get('statistics', {})
                
            print(f"✅ 加载结果文件: {latest_file.name}")
            print(f"📊 共 {len(self.results)} 个处理结果")
            return True
            
        except Exception as e:
            print(f"❌ 加载结果失败: {e}")
            return False
    
    def show_overview(self):
        """显示概览统计"""
        if not self.stats:
            print("❌ 未加载结果数据")
            return
            
        print("\n" + "="*60)
        print("📋 处理结果概览")
        print("="*60)
        
        print(f"📁 总文件数: {self.stats['total_files']}")
        print(f"✅ 成功处理: {self.stats['processed_successfully']}")
        print(f"❌ 失败文件: {self.stats['failed_files']}")
        print(f"💾 缓存文件: {self.stats.get('cached_files', 0)}")
        print(f"🎯 成功率: {self.stats['processed_successfully']/max(self.stats['total_files'], 1)*100:.1f}%")
        
        # 分类统计
        print(f"\n📚 分类统计:")
        categories = sorted(self.stats['categories'].items(), key=lambda x: x[1], reverse=True)
        for category, count in categories:
            percentage = count / max(self.stats['processed_successfully'], 1) * 100
            print(f"  {category}: {count} 个文件 ({percentage:.1f}%)")
        
        # 内容统计
        if 'content_statistics' in self.stats:
            content = self.stats['content_statistics']
            print(f"\n📖 内容提取统计:")
            print(f"  🔮 总卦象: {content['total_hexagrams']}")
            print(f"  📜 总爻辞: {content['total_yao_ci']}")
            print(f"  📝 总注解: {content['total_annotations']}")
            print(f"  📋 总案例: {content['total_cases']}")
    
    def search_by_category(self, category: str):
        """按类别搜索"""
        if not self.results:
            print("❌ 未加载结果数据")
            return
            
        matches = [r for r in self.results if r['pdf_info']['category'].lower() == category.lower()]
        
        if not matches:
            available_categories = set(r['pdf_info']['category'] for r in self.results)
            print(f"❌ 未找到类别 '{category}' 的文件")
            print(f"可用类别: {', '.join(available_categories)}")
            return
        
        print(f"\n🔍 类别 '{category}' 的文件 ({len(matches)} 个):")
        print("-" * 80)
        
        for i, result in enumerate(matches, 1):
            info = result['pdf_info']
            stats = result.get('statistics', {})
            
            print(f"{i}. {info['file_name']}")
            print(f"   📊 优先级: {info['priority']} | 置信度: {info['confidence']:.2f}")
            print(f"   📖 页数: {info['pages']} | 文本长度: {info['text_length']:,}")
            print(f"   🔮 卦象: {stats.get('hexagram_count', 0)} | 爻辞: {stats.get('yao_ci_count', 0)} | 注解: {stats.get('annotation_count', 0)} | 案例: {stats.get('case_count', 0)}")
            print()
    
    def search_by_keyword(self, keyword: str):
        """按关键词搜索"""
        if not self.results:
            print("❌ 未加载结果数据")
            return
            
        matches = []
        for result in self.results:
            # 在文件名中搜索
            if keyword.lower() in result['pdf_info']['file_name'].lower():
                matches.append((result, '文件名'))
                continue
            
            # 在关键词中搜索
            keywords = result['content'].get('keywords', [])
            if any(keyword.lower() in kw.lower() for kw in keywords):
                matches.append((result, '关键词'))
                continue
            
            # 在作者中搜索
            author = result['content'].get('author', '')
            if author and keyword.lower() in author.lower():
                matches.append((result, '作者'))
        
        if not matches:
            print(f"❌ 未找到包含 '{keyword}' 的文件")
            return
        
        print(f"\n🔍 包含 '{keyword}' 的文件 ({len(matches)} 个):")
        print("-" * 80)
        
        for i, (result, match_type) in enumerate(matches, 1):
            info = result['pdf_info']
            content = result['content']
            
            print(f"{i}. {info['file_name']} (匹配: {match_type})")
            print(f"   📂 类别: {info['category']} | 优先级: {info['priority']}")
            if content.get('author'):
                print(f"   👤 作者: {content['author']}")
            if content.get('dynasty'):
                print(f"   🏛️ 朝代: {content['dynasty']}")
            print(f"   🏷️ 关键词: {', '.join(content.get('keywords', [])[:5])}")
            print()
    
    def show_top_files(self, by: str = 'content', top_n: int = 10):
        """显示Top文件"""
        if not self.results:
            print("❌ 未加载结果数据")
            return
        
        if by == 'content':
            # 按内容丰富度排序
            sorted_results = sorted(
                self.results,
                key=lambda x: (
                    x.get('statistics', {}).get('hexagram_count', 0) +
                    x.get('statistics', {}).get('yao_ci_count', 0) +
                    x.get('statistics', {}).get('annotation_count', 0) +
                    x.get('statistics', {}).get('case_count', 0)
                ),
                reverse=True
            )
            title = f"📈 内容最丰富的 Top {top_n} 文件:"
            
        elif by == 'priority':
            # 按优先级和置信度排序
            sorted_results = sorted(
                self.results,
                key=lambda x: (x['pdf_info']['priority'], -x['pdf_info']['confidence'])
            )
            title = f"⭐ 最高优先级的 Top {top_n} 文件:"
            
        elif by == 'size':
            # 按文件大小排序
            sorted_results = sorted(
                self.results,
                key=lambda x: x['pdf_info']['file_size'],
                reverse=True
            )
            title = f"📏 文件最大的 Top {top_n} 文件:"
            
        else:
            print(f"❌ 不支持的排序方式: {by}")
            return
        
        print(f"\n{title}")
        print("-" * 80)
        
        for i, result in enumerate(sorted_results[:top_n], 1):
            info = result['pdf_info']
            stats = result.get('statistics', {})
            content = result['content']
            
            print(f"{i}. {info['file_name']}")
            print(f"   📂 类别: {info['category']} | 优先级: {info['priority']} | 置信度: {info['confidence']:.2f}")
            print(f"   📖 大小: {info['file_size']:,} bytes | 页数: {info['pages']}")
            
            total_content = (
                stats.get('hexagram_count', 0) +
                stats.get('yao_ci_count', 0) +
                stats.get('annotation_count', 0) +
                stats.get('case_count', 0)
            )
            print(f"   🔮 内容: 卦象{stats.get('hexagram_count', 0)} | 爻辞{stats.get('yao_ci_count', 0)} | 注解{stats.get('annotation_count', 0)} | 案例{stats.get('case_count', 0)} (总计{total_content})")
            
            if content.get('author'):
                print(f"   👤 作者: {content['author']}")
            print()
    
    def export_category_summary(self, output_file: str = None):
        """导出分类汇总"""
        if not self.results:
            print("❌ 未加载结果数据")
            return
        
        if not output_file:
            output_file = f"category_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        
        # 按类别组织数据
        by_category = defaultdict(list)
        for result in self.results:
            category = result['pdf_info']['category']
            by_category[category].append(result)
        
        # 生成Markdown报告
        content = f"# 📚 易学PDF分类汇总报告\n\n"
        content += f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        content += f"**总文件数**: {len(self.results)}\n\n"
        
        for category in sorted(by_category.keys()):
            files = by_category[category]
            content += f"## {category} ({len(files)} 个文件)\n\n"
            
            # 统计这个类别的内容
            total_hexagrams = sum(f.get('statistics', {}).get('hexagram_count', 0) for f in files)
            total_yao_ci = sum(f.get('statistics', {}).get('yao_ci_count', 0) for f in files)
            total_annotations = sum(f.get('statistics', {}).get('annotation_count', 0) for f in files)
            total_cases = sum(f.get('statistics', {}).get('case_count', 0) for f in files)
            
            content += f"**内容统计**: 卦象{total_hexagrams} | 爻辞{total_yao_ci} | 注解{total_annotations} | 案例{total_cases}\n\n"
            
            # 按优先级排序
            files.sort(key=lambda x: (x['pdf_info']['priority'], -x['pdf_info']['confidence']))
            
            for i, file_result in enumerate(files, 1):
                info = file_result['pdf_info']
                stats = file_result.get('statistics', {})
                file_content = file_result['content']
                
                content += f"### {i}. {info['file_name']}\n"
                content += f"- **优先级**: {info['priority']} | **置信度**: {info['confidence']:.2f}\n"
                content += f"- **页数**: {info['pages']} | **文本长度**: {info['text_length']:,}\n"
                content += f"- **内容**: 卦象{stats.get('hexagram_count', 0)} | 爻辞{stats.get('yao_ci_count', 0)} | 注解{stats.get('annotation_count', 0)} | 案例{stats.get('case_count', 0)}\n"
                
                if file_content.get('author'):
                    content += f"- **作者**: {file_content['author']}\n"
                if file_content.get('dynasty'):
                    content += f"- **朝代**: {file_content['dynasty']}\n"
                if file_content.get('keywords'):
                    keywords = ', '.join(file_content['keywords'][:8])
                    content += f"- **关键词**: {keywords}\n"
                
                content += "\n"
            
            content += "\n"
        
        # 保存文件
        output_path = Path(output_file)
        if not output_path.is_absolute():
            output_path = self.structured_data_dir / output_file
            
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"✅ 分类汇总已导出到: {output_path}")
        return output_path
    
    def interactive_menu(self):
        """交互式菜单"""
        while True:
            print("\n" + "="*60)
            print("🔮 PDF处理结果分析器")
            print("="*60)
            print("1. 📋 显示处理概览")
            print("2. 🔍 按类别搜索")
            print("3. 🔎 按关键词搜索")
            print("4. 📈 显示Top文件")
            print("5. 📤 导出分类汇总")
            print("6. 🔄 重新加载结果")
            print("0. 🚪 退出")
            print("-"*60)
            
            choice = input("请选择操作 (0-6): ").strip()
            
            if choice == '0':
                print("👋 再见！")
                break
            elif choice == '1':
                self.show_overview()
            elif choice == '2':
                category = input("请输入类别名称: ").strip()
                if category:
                    self.search_by_category(category)
            elif choice == '3':
                keyword = input("请输入关键词: ").strip()
                if keyword:
                    self.search_by_keyword(keyword)
            elif choice == '4':
                print("排序方式: content(内容), priority(优先级), size(大小)")
                by = input("请选择排序方式 (默认content): ").strip() or "content"
                top_n = input("显示数量 (默认10): ").strip()
                try:
                    top_n = int(top_n) if top_n else 10
                    self.show_top_files(by, top_n)
                except ValueError:
                    print("❌ 无效的数量")
            elif choice == '5':
                filename = input("输出文件名 (默认自动生成): ").strip()
                self.export_category_summary(filename if filename else None)
            elif choice == '6':
                self.load_latest_results()
            else:
                print("❌ 无效的选择")

def main():
    """主函数"""
    structured_data_dir = "/mnt/d/desktop/appp/structured_data"
    
    print("🔍 PDF处理结果分析器")
    
    analyzer = ResultAnalyzer(structured_data_dir)
    
    if not analyzer.load_latest_results():
        print("请先运行PDF处理脚本生成结果文件")
        return
    
    # 显示快速概览
    analyzer.show_overview()
    
    # 启动交互式菜单
    try:
        analyzer.interactive_menu()
    except KeyboardInterrupt:
        print("\n👋 用户退出")

if __name__ == "__main__":
    main()