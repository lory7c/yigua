#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据导入脚本 - 将JSON数据导入到应用中
"""

import json
import sqlite3
import os
from datetime import datetime

class DataImporter:
    def __init__(self):
        self.db_path = 'yigua.db'
        self.conn = None
        self.cursor = None
        
    def connect_db(self):
        """连接数据库"""
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()
        print(f"✅ 已连接数据库: {self.db_path}")
        
    def create_tables(self):
        """创建数据表"""
        # 64卦表
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS hexagrams (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                symbol TEXT,
                number TEXT,
                meaning TEXT,
                judgment TEXT,
                image TEXT,
                interpretations TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 爻辞表
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS yao_texts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                hexagram_id INTEGER,
                position INTEGER,
                text TEXT,
                meaning TEXT,
                FOREIGN KEY (hexagram_id) REFERENCES hexagrams(id)
            )
        ''')
        
        # 周公解梦表
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS dreams (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT,
                keyword TEXT,
                content TEXT,
                fortune TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 黄历表
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS calendar (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT UNIQUE,
                lunar_date TEXT,
                lunar_month TEXT,
                lunar_day TEXT,
                ganzhi_year TEXT,
                ganzhi_month TEXT,
                ganzhi_day TEXT,
                yi TEXT,
                ji TEXT,
                solar_term TEXT,
                festival TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        self.conn.commit()
        print("✅ 数据表创建完成")
        
    def import_hexagrams(self, json_file):
        """导入64卦数据"""
        if not os.path.exists(json_file):
            print(f"❌ 文件不存在: {json_file}")
            return
            
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        hexagrams = data.get('hexagrams', [])
        imported = 0
        
        for hexagram in hexagrams:
            try:
                # 插入卦象主表
                self.cursor.execute('''
                    INSERT OR REPLACE INTO hexagrams 
                    (id, name, symbol, number, meaning, judgment, image, interpretations)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    hexagram['id'],
                    hexagram['name'],
                    hexagram.get('symbol', ''),
                    hexagram.get('number', ''),
                    hexagram.get('meaning', ''),
                    hexagram.get('judgment', ''),
                    hexagram.get('image', ''),
                    json.dumps(hexagram.get('interpretations', {}), ensure_ascii=False)
                ))
                
                # 插入爻辞
                for yao in hexagram.get('yao_texts', []):
                    self.cursor.execute('''
                        INSERT INTO yao_texts (hexagram_id, position, text, meaning)
                        VALUES (?, ?, ?, ?)
                    ''', (
                        hexagram['id'],
                        yao['position'],
                        yao['text'],
                        yao.get('meaning', '')
                    ))
                    
                imported += 1
                
            except Exception as e:
                print(f"⚠️ 导入卦象 {hexagram.get('name', '未知')} 失败: {e}")
                
        self.conn.commit()
        print(f"✅ 成功导入 {imported} 个卦象")
        
    def import_dreams(self, json_file):
        """导入周公解梦数据"""
        if not os.path.exists(json_file):
            print(f"❌ 文件不存在: {json_file}")
            return
            
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        dreams = data.get('dreams', [])
        imported = 0
        
        for dream in dreams:
            try:
                self.cursor.execute('''
                    INSERT INTO dreams (category, keyword, content, fortune)
                    VALUES (?, ?, ?, ?)
                ''', (
                    dream.get('category', '其他'),
                    dream['keyword'],
                    dream['content'],
                    dream.get('fortune', '')
                ))
                imported += 1
                
            except Exception as e:
                print(f"⚠️ 导入梦境 {dream.get('keyword', '未知')} 失败: {e}")
                
        self.conn.commit()
        print(f"✅ 成功导入 {imported} 条梦境解释")
        
    def import_calendar(self, json_file):
        """导入黄历数据"""
        if not os.path.exists(json_file):
            print(f"❌ 文件不存在: {json_file}")
            return
            
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        calendar_data = data.get('calendar', [])
        imported = 0
        
        for day in calendar_data:
            try:
                self.cursor.execute('''
                    INSERT OR REPLACE INTO calendar 
                    (date, lunar_date, yi, ji, solar_term, festival)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    day['date'],
                    day.get('lunar', ''),
                    json.dumps(day.get('yi', []), ensure_ascii=False),
                    json.dumps(day.get('ji', []), ensure_ascii=False),
                    day.get('solar_term', ''),
                    day.get('festival', '')
                ))
                imported += 1
                
            except Exception as e:
                print(f"⚠️ 导入日期 {day.get('date', '未知')} 失败: {e}")
                
        self.conn.commit()
        print(f"✅ 成功导入 {imported} 天黄历数据")
        
    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()
            print("✅ 数据库连接已关闭")
            
    def verify_data(self):
        """验证导入的数据"""
        # 检查64卦
        self.cursor.execute("SELECT COUNT(*) FROM hexagrams")
        hexagram_count = self.cursor.fetchone()[0]
        
        # 检查爻辞
        self.cursor.execute("SELECT COUNT(*) FROM yao_texts")
        yao_count = self.cursor.fetchone()[0]
        
        # 检查梦境
        self.cursor.execute("SELECT COUNT(*) FROM dreams")
        dream_count = self.cursor.fetchone()[0]
        
        # 检查黄历
        self.cursor.execute("SELECT COUNT(*) FROM calendar")
        calendar_count = self.cursor.fetchone()[0]
        
        print("\n📊 数据统计:")
        print(f"  - 卦象: {hexagram_count}/64")
        print(f"  - 爻辞: {yao_count}/384 (64卦×6爻)")
        print(f"  - 梦境: {dream_count} 条")
        print(f"  - 黄历: {calendar_count} 天")
        
        if hexagram_count == 64:
            print("  ✅ 64卦数据完整")
        else:
            print(f"  ⚠️ 缺少 {64 - hexagram_count} 个卦")
            
def main():
    """主函数"""
    print("="*50)
    print("易卦APP数据导入工具 v1.0")
    print("="*50)
    
    importer = DataImporter()
    
    try:
        # 连接数据库
        importer.connect_db()
        
        # 创建表
        importer.create_tables()
        
        # 导入数据
        print("\n📥 开始导入数据...")
        
        # 导入64卦
        hexagram_file = 'hexagrams.json'
        if os.path.exists(hexagram_file):
            print(f"\n正在导入: {hexagram_file}")
            importer.import_hexagrams(hexagram_file)
        else:
            print(f"⚠️ 跳过: {hexagram_file} (文件不存在)")
            
        # 导入周公解梦
        dream_file = 'dreams.json'
        if os.path.exists(dream_file):
            print(f"\n正在导入: {dream_file}")
            importer.import_dreams(dream_file)
        else:
            print(f"⚠️ 跳过: {dream_file} (文件不存在)")
            
        # 导入黄历
        calendar_file = 'calendar_2025.json'
        if os.path.exists(calendar_file):
            print(f"\n正在导入: {calendar_file}")
            importer.import_calendar(calendar_file)
        else:
            print(f"⚠️ 跳过: {calendar_file} (文件不存在)")
            
        # 验证数据
        print("\n🔍 验证数据完整性...")
        importer.verify_data()
        
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        
    finally:
        importer.close()
        
    print("\n✅ 数据导入完成！")
    print("="*50)

if __name__ == "__main__":
    main()