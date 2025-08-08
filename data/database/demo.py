#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
易学知识库演示脚本
快速展示数据库功能和性能
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from db_manager import DatabaseManager
import time

def main():
    print("🌟 易学知识库演示")
    print("=" * 50)
    
    # 创建数据库管理器
    db_path = "demo_yixue_kb.db"
    db = DatabaseManager(db_path)
    
    try:
        # 1. 基础查询演示
        print("\n📚 基础查询演示")
        print("-" * 20)
        
        # 查询乾卦
        hexagram = db.get_hexagram_by_number(1)
        if hexagram:
            print(f"卦名: {hexagram['gua_name']}")
            print(f"含义: {hexagram['basic_meaning']}")
            print(f"卦辞: {hexagram['judgement']}")
        
        # 2. 搜索功能演示  
        print("\n🔍 全文搜索演示")
        print("-" * 20)
        
        search_term = "龙"
        results = db.search_hexagrams(search_term, 3)
        print(f"搜索 '{search_term}' 的结果:")
        for result in results:
            print(f"  - {result['gua_name']}: {result['basic_meaning']}")
        
        # 3. 通用搜索演示
        print(f"\n🌐 通用搜索演示")
        print("-" * 20)
        
        universal_results = db.universal_search("君子", 2)
        for content_type, items in universal_results.items():
            if items:
                print(f"{content_type.upper()}:")
                for item in items[:2]:  # 只显示前2个
                    if 'gua_name' in item:
                        print(f"  - {item['gua_name']}")
                    elif 'case_title' in item:
                        print(f"  - {item['case_title']}")
                    elif 'author' in item:
                        print(f"  - {item['author']}")
        
        # 4. 性能测试演示
        print(f"\n⚡ 性能测试演示")
        print("-" * 20)
        
        # 测试基础查询性能
        start_time = time.time()
        for i in range(100):  # 执行100次查询
            db.get_hexagram_by_number((i % 64) + 1)
        end_time = time.time()
        
        avg_time = (end_time - start_time) / 100 * 1000  # 转换为毫秒
        print(f"100次基础查询平均时间: {avg_time:.2f}ms")
        
        # 测试搜索性能
        start_time = time.time()
        for term in ["天", "地", "水", "火", "雷"]:
            db.search_hexagrams(term, 5)
        end_time = time.time()
        
        search_time = (end_time - start_time) / 5 * 1000
        print(f"5次搜索平均时间: {search_time:.2f}ms")
        
        # 5. 数据统计演示
        print(f"\n📊 数据统计演示")
        print("-" * 20)
        
        storage_stats = db.get_storage_stats()
        total_records = sum(stat['record_count'] for stat in storage_stats)
        total_size = sum(stat['estimated_size_bytes'] or 0 for stat in storage_stats)
        
        print(f"总记录数: {total_records:,}")
        print(f"数据库大小: {total_size / 1024 / 1024:.2f}MB")
        
        print("\n各表记录数:")
        for stat in storage_stats:
            if stat['record_count'] > 0:
                size_kb = (stat['estimated_size_bytes'] or 0) / 1024
                print(f"  {stat['table_name']}: {stat['record_count']:,} 条记录 (~{size_kb:.1f}KB)")
        
        print(f"\n✅ 演示完成！数据库文件: {db_path}")
        
    except Exception as e:
        print(f"❌ 演示过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        db.close()

if __name__ == "__main__":
    main()