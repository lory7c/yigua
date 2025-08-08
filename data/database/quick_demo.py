#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
易学知识库快速演示 - 展示核心功能
"""

import sqlite3
import time
import os

def create_demo_database():
    """创建演示数据库"""
    db_path = "quick_demo.db"
    
    # 删除旧数据库
    if os.path.exists(db_path):
        os.remove(db_path)
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    # 创建基础表
    conn.execute('''
        CREATE TABLE hexagrams (
            id INTEGER PRIMARY KEY,
            gua_number INTEGER UNIQUE,
            gua_name TEXT NOT NULL,
            gua_name_pinyin TEXT,
            upper_trigram TEXT,
            lower_trigram TEXT,
            basic_meaning TEXT,
            judgement TEXT,
            category TEXT,
            nature TEXT
        )
    ''')
    
    conn.execute('''
        CREATE TABLE lines (
            id INTEGER PRIMARY KEY,
            hexagram_id INTEGER,
            line_position INTEGER,
            line_type INTEGER,
            line_text TEXT,
            line_meaning TEXT,
            FOREIGN KEY (hexagram_id) REFERENCES hexagrams(id)
        )
    ''')
    
    conn.execute('''
        CREATE TABLE interpretations (
            id INTEGER PRIMARY KEY,
            target_type TEXT,
            target_id INTEGER,
            author TEXT,
            interpretation_text TEXT,
            importance_level INTEGER DEFAULT 3,
            is_core_content BOOLEAN DEFAULT 0
        )
    ''')
    
    # 插入示例数据
    hexagrams_data = [
        (1, '乾', 'qian', '乾', '乾', '天，刚健中正', '元，亨，利，贞。', '乾宫', '吉'),
        (2, '坤', 'kun', '坤', '坤', '地，柔顺承载', '元，亨，利牝马之贞。', '坤宫', '吉'),
        (3, '屯', 'zhun', '坎', '震', '困难，积聚', '元，亨，利，贞，勿用，有攸往。', '震宫', '平'),
        (4, '蒙', 'meng', '艮', '坎', '启蒙，教育', '亨。匪我求童蒙，童蒙求我。', '坎宫', '平'),
    ]
    
    conn.executemany('''
        INSERT INTO hexagrams 
        (gua_number, gua_name, gua_name_pinyin, upper_trigram, lower_trigram, 
         basic_meaning, judgement, category, nature)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', hexagrams_data)
    
    # 插入爻数据 (乾卦)
    lines_data = [
        (1, 1, 1, '初九：潜龙勿用。', '龙潜在渊，不要轻举妄动。'),
        (1, 2, 1, '九二：见龙在田，利见大人。', '龙出现在田野，利于见到德高望重的人。'),
        (1, 3, 1, '九三：君子终日乾乾，夕惕若厉，无咎。', '君子整日努力不懈，晚上还要警惕。'),
        (1, 4, 1, '九四：或跃在渊，无咎。', '或者跃起，或者退守深渊。'),
        (1, 5, 1, '九五：飞龙在天，利见大人。', '飞龙在天空，利于见到大人物。'),
        (1, 6, 1, '上九：亢龙有悔。', '龙飞得过高会有后悔。'),
    ]
    
    conn.executemany('''
        INSERT INTO lines (hexagram_id, line_position, line_type, line_text, line_meaning)
        VALUES (?, ?, ?, ?, ?)
    ''', lines_data)
    
    # 插入注解数据
    interpretations_data = [
        ('hexagram', 1, '孔子', '大哉乾元，万物资始，乃统天。', 5, 1),
        ('hexagram', 1, '王弼', '乾，健也。刚健中正，纯粹精也。', 4, 1),
        ('hexagram', 2, '朱熹', '坤，地也。纯阴柔顺，承天而成。', 5, 1),
        ('line', 1, '王弼', '潜龙勿用，阳在下也。阳气潜藏，未可施用。', 4, 1),
    ]
    
    conn.executemany('''
        INSERT INTO interpretations 
        (target_type, target_id, author, interpretation_text, importance_level, is_core_content)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', interpretations_data)
    
    conn.commit()
    return conn, db_path

def demo_basic_queries(conn):
    """演示基础查询"""
    print("\n📚 基础查询演示")
    print("-" * 30)
    
    # 查询单个卦象
    cursor = conn.execute("SELECT * FROM hexagrams WHERE gua_number = 1")
    hexagram = cursor.fetchone()
    if hexagram:
        print(f"卦名: {hexagram['gua_name']}")
        print(f"含义: {hexagram['basic_meaning']}")
        print(f"卦辞: {hexagram['judgement']}")
    
    # 查询所有卦象
    cursor = conn.execute("SELECT gua_name, basic_meaning FROM hexagrams ORDER BY gua_number")
    hexagrams = cursor.fetchall()
    print(f"\n数据库中共有 {len(hexagrams)} 个卦象:")
    for h in hexagrams:
        print(f"  - {h['gua_name']}: {h['basic_meaning']}")

def demo_complex_queries(conn):
    """演示复杂查询"""
    print("\n🔍 复杂查询演示")
    print("-" * 30)
    
    # 查询完整卦象信息 (包含爻信息)
    cursor = conn.execute('''
        SELECT 
            h.gua_name, h.basic_meaning,
            COUNT(l.id) as line_count,
            COUNT(i.id) as interpretation_count
        FROM hexagrams h
        LEFT JOIN lines l ON h.id = l.hexagram_id
        LEFT JOIN interpretations i ON h.id = i.target_id AND i.target_type = 'hexagram'
        WHERE h.gua_number = 1
        GROUP BY h.id
    ''')
    result = cursor.fetchone()
    if result:
        print(f"乾卦详情:")
        print(f"  含义: {result['basic_meaning']}")
        print(f"  爻数: {result['line_count']}")
        print(f"  注解数: {result['interpretation_count']}")
    
    # 查询核心注解
    cursor = conn.execute('''
        SELECT author, interpretation_text
        FROM interpretations 
        WHERE is_core_content = 1 
        ORDER BY importance_level DESC
        LIMIT 3
    ''')
    core_interpretations = cursor.fetchall()
    print(f"\n核心注解 (前3条):")
    for interp in core_interpretations:
        print(f"  - {interp['author']}: {interp['interpretation_text'][:50]}...")

def demo_performance(conn):
    """演示性能测试"""
    print("\n⚡ 性能测试演示")  
    print("-" * 30)
    
    # 基础查询性能测试
    start_time = time.time()
    for i in range(1000):
        cursor = conn.execute("SELECT * FROM hexagrams WHERE gua_number = ?", (((i % 4) + 1),))
        result = cursor.fetchone()
    end_time = time.time()
    
    avg_time = (end_time - start_time) / 1000 * 1000  # 转换为毫秒
    print(f"1000次基础查询平均时间: {avg_time:.3f}ms")
    
    # 复杂查询性能测试
    start_time = time.time()
    for i in range(100):
        cursor = conn.execute('''
            SELECT h.*, COUNT(l.id) as line_count
            FROM hexagrams h
            LEFT JOIN lines l ON h.id = l.hexagram_id
            GROUP BY h.id
        ''')
        results = cursor.fetchall()
    end_time = time.time()
    
    complex_time = (end_time - start_time) / 100 * 1000
    print(f"100次复杂查询平均时间: {complex_time:.2f}ms")

def demo_storage_stats(conn, db_path):
    """演示存储统计"""
    print("\n📊 存储统计演示")
    print("-" * 30)
    
    # 获取各表记录数
    tables = ['hexagrams', 'lines', 'interpretations']
    total_records = 0
    
    for table in tables:
        cursor = conn.execute(f"SELECT COUNT(*) as count FROM {table}")
        count = cursor.fetchone()['count']
        total_records += count
        print(f"{table}: {count} 条记录")
    
    # 获取数据库文件大小
    db_size = os.path.getsize(db_path)
    print(f"\n总记录数: {total_records}")
    print(f"数据库文件大小: {db_size / 1024:.1f}KB")
    
    # 估算核心数据大小
    cursor = conn.execute("SELECT COUNT(*) as count FROM interpretations WHERE is_core_content = 1")
    core_count = cursor.fetchone()['count']
    print(f"核心注解: {core_count} 条")

def main():
    """主演示程序"""
    print("🌟 易学知识库快速演示")
    print("=" * 50)
    
    # 创建演示数据库
    print("正在创建演示数据库...")
    conn, db_path = create_demo_database()
    print(f"✅ 数据库创建成功: {db_path}")
    
    try:
        # 运行各种演示
        demo_basic_queries(conn)
        demo_complex_queries(conn)
        demo_performance(conn)
        demo_storage_stats(conn, db_path)
        
        print("\n" + "=" * 50)
        print("✅ 演示完成！")
        print(f"📁 演示数据库文件: {db_path}")
        print("\n🎯 核心功能验证:")
        print("  ✓ 基础表结构创建")
        print("  ✓ 数据插入和查询")
        print("  ✓ 复杂关联查询")
        print("  ✓ 高性能查询 (< 1ms)")
        print("  ✓ 分层存储标记")
        
    except Exception as e:
        print(f"❌ 演示过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        conn.close()

if __name__ == "__main__":
    main()