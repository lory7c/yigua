#!/usr/bin/env python3
"""
PDF处理测试版本 - 只处理前5个文件
"""

import os
import json
from pathlib import Path
from extract_pdfs_with_progress import PDFProcessorWithProgress

def main():
    """测试主函数"""
    data_dir = "/mnt/d/desktop/appp/data"
    output_dir = "/mnt/d/desktop/appp/test_results"
    
    print("🧪 PDF处理测试版本")
    print(f"📂 数据目录: {data_dir}")
    print(f"📁 输出目录: {output_dir}")
    
    # 创建测试处理器
    processor = PDFProcessorWithProgress(data_dir, output_dir)
    
    # 获取前5个PDF文件
    pdf_files = list(Path(data_dir).glob("*.pdf"))[:5]
    print(f"📋 测试文件 ({len(pdf_files)} 个):")
    for i, pdf_file in enumerate(pdf_files, 1):
        print(f"  {i}. {pdf_file.name}")
    
    if not pdf_files:
        print("❌ 没有找到PDF文件")
        return
    
    print(f"\n🚀 开始处理...")
    
    # 手动处理测试文件
    results = []
    for pdf_file in pdf_files:
        print(f"📄 处理: {pdf_file.name}")
        try:
            result = processor.process_single_pdf(pdf_file)
            if result:
                results.append(result)
                info = result['pdf_info']
                stats = result.get('statistics', {})
                print(f"   ✅ 类别: {info['category']} | 置信度: {info['confidence']:.2f}")
                print(f"   📊 内容: 卦{stats.get('hexagram_count', 0)} 爻{stats.get('yao_ci_count', 0)} 注{stats.get('annotation_count', 0)} 例{stats.get('case_count', 0)}")
            else:
                print(f"   ❌ 处理失败")
        except Exception as e:
            print(f"   ❌ 错误: {e}")
    
    if results:
        # 保存测试结果
        test_result = {
            "test_info": {
                "total_test_files": len(pdf_files),
                "successful_files": len(results),
                "test_time": "test_run"
            },
            "results": results
        }
        
        output_file = Path(output_dir) / "test_results.json"
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(test_result, f, ensure_ascii=False, indent=2)
        
        print(f"\n✅ 测试完成!")
        print(f"📊 成功处理: {len(results)}/{len(pdf_files)}")
        print(f"💾 结果保存到: {output_file}")
        
        # 显示分类统计
        categories = {}
        for result in results:
            category = result['pdf_info']['category']
            categories[category] = categories.get(category, 0) + 1
        
        print(f"\n📚 分类统计:")
        for category, count in categories.items():
            print(f"  {category}: {count} 个文件")
    else:
        print("❌ 没有成功处理任何文件")

if __name__ == "__main__":
    main()