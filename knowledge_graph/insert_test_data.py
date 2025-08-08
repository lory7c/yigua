#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
插入易学知识库测试数据
"""

import sqlite3
import sys
from pathlib import Path

def insert_test_data(db_path: str):
    """插入基础测试数据"""
    print(f"向数据库插入测试数据: {db_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # 1. 插入卦象数据
        hexagrams_data = [
            (1, '乾', 'qian', '乾', '乾', '111111', '☰', '天，刚健中正', 
             '元，亨，利，贞。', '天行健，君子以自强不息。', '大哉乾元，万物资始，乃统天。', '乾宫', '阳'),
            (2, '坤', 'kun', '坤', '坤', '000000', '☷', '地，柔顺承载', 
             '元，亨，利牝马之贞。君子有攸往，先迷后得主利。', '地势坤，君子以厚德载物。', '至哉坤元，万物资生，乃顺承天。', '坤宫', '阴'),
            (3, '屯', 'zhun', '坎', '震', '010001', '☵', '困难初创，艰难创业', 
             '元，亨，利，贞，勿用，有攸往，利建侯。', '云，雷，屯；君子以经纶。', '屯，盈也。时乎动，险，大亨贞。', '震宫', '阴'),
            (4, '蒙', 'meng', '艮', '坎', '100010', '☶', '蒙昧无知，启蒙教育', 
             '亨。匪我求童蒙，童蒙求我。初噬告，再三渎，渎则不告。利贞。', '山下出泉，蒙；君子以果行育德。', '蒙，亨，以亨行时中也。', '坎宫', '阳'),
            (5, '需', 'xu', '坎', '乾', '010111', '☵', '等待时机，需要耐心', 
             '有孚，光亨，贞吉。利涉大川。', '云上于天，需；君子以饮食宴乐。', '需，须也，险在前也。刚健而不陷，其义不困穷矣。', '乾宫', '阳'),
            (6, '讼', 'song', '乾', '坎', '111010', '☰', '争讼诉讼，纠纷冲突', 
             '有孚，窒。惕中吉。终凶。利见大人，不利涉大川。', '天与水违行，讼；君子以作事谋始。', '讼，上刚下险，险而健讼。', '坎宫', '阴'),
            (7, '师', 'shi', '坤', '坎', '000010', '☷', '军队师傅，统兵作战', 
             '贞，丈人，吉无咎。', '地中有水，师；君子以容民畜众。', '师，众也，贞正也，能以众正，可以王矣。', '坎宫', '阴'),
            (8, '比', 'bi', '坎', '坤', '010000', '☵', '亲密比较，和睦团结', 
             '吉。原筮元永贞，无咎。不宁方来，后夫凶。', '地上有水，比；先王以建万国，亲诸侯。', '比，吉也，比，辅也，下顺从也。', '坤宫', '阳')
        ]
        
        cursor.executemany("""
            INSERT OR REPLACE INTO hexagrams 
            (gua_number, gua_name, gua_name_pinyin, upper_trigram, lower_trigram, 
             binary_code, unicode_symbol, basic_meaning, judgement, image, decision, category, nature)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, hexagrams_data)
        
        print(f"插入了 {len(hexagrams_data)} 个卦象")
        
        # 2. 插入爻位数据
        lines_data = []
        for hex_id in range(1, 9):  # 对应前8个卦
            for pos in range(1, 7):  # 6个爻位
                line_type = 1 if pos % 2 == 1 else 0  # 简化的阴阳判断
                element = ['木', '火', '土', '金', '水'][pos % 5]
                
                lines_data.append((
                    hex_id, pos, line_type,
                    f'第{pos}爻爻辞',
                    f'第{pos}爻含义解释',
                    f'第{pos}爻象传',
                    0, element
                ))
        
        cursor.executemany("""
            INSERT OR REPLACE INTO lines 
            (hexagram_id, line_position, line_type, line_text, line_meaning, line_image, is_changing_line, element)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, lines_data)
        
        print(f"插入了 {len(lines_data)} 个爻位")
        
        # 3. 插入注解数据
        interpretations_data = [
            ('hexagram', 1, '王弼', '三国时期著名易学家对乾卦的注解：乾，健也。刚健中正，万物资始。', '魏', '周易注', '象数', 5, 1, 50),
            ('hexagram', 2, '程颐', '宋代理学家程颐对坤卦的解释：坤道其顺，承天时行，厚德载物。', '宋', '易传', '义理', 5, 1, 45),
            ('hexagram', 3, '朱熹', '南宋朱熹对屯卦的注解：屯，难也。物之始生，其必有屯。', '宋', '周易本义', '义理', 4, 0, 40),
            ('line', 1, '孔颖达', '唐代孔颖达对乾卦初九的疏解：潜龙勿用，阳气在下，未可施用。', '唐', '周易正义', '象数', 4, 0, 35),
            ('hexagram', 4, '荀爽', '东汉荀爽对蒙卦的解释：蒙，昧也。以阴求阳，以柔求刚。', '汉', '易传', '象数', 4, 0, 30)
        ]
        
        cursor.executemany("""
            INSERT OR REPLACE INTO interpretations 
            (target_type, target_id, author, interpretation_text, dynasty, source_book, interpretation_type, importance_level, is_core_content, content_length)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, interpretations_data)
        
        print(f"插入了 {len(interpretations_data)} 个注解")
        
        # 4. 插入占卜案例
        divination_cases_data = [
            ('乾卦占事业运势', 1, '事业', '问今年事业发展如何？', 
             '得乾卦，天行健，君子以自强不息。今年事业发展顺利，但需要持续努力，保持刚健的品格。', 
             '事业确实发展顺利，获得了重要项目', 4),
            ('坤卦占婚姻感情', 2, '感情', '问与某人感情发展前景？',
             '得坤卦，地势坤，君子以厚德载物。感情需要以柔顺、包容的态度对待，厚德方能载情。',
             '两人关系和谐发展，最终步入婚姻', 5),
            ('屯卦占求财运', 3, '财运', '问投资项目是否可行？',
             '得屯卦，云雷屯，时乎动险。初创项目虽有困难，但坚持可成，不可贸然投入大额资金。',
             '谨慎投资，小有收益，避免了重大损失', 4),
        ]
        
        cursor.executemany("""
            INSERT OR REPLACE INTO divination_cases 
            (case_title, hexagram_id, question_type, question_detail, interpretation, actual_result, accuracy_rating)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, divination_cases_data)
        
        print(f"插入了 {len(divination_cases_data)} 个占卜案例")
        
        # 5. 插入关键词标签
        keywords_data = [
            ('乾卦', '卦象', 10, 5.0),
            ('坤卦', '卦象', 10, 5.0),
            ('天', '自然', 8, 4.5),
            ('地', '自然', 8, 4.5),
            ('刚健', '品德', 6, 4.0),
            ('柔顺', '品德', 6, 4.0),
            ('阴阳', '哲学', 15, 5.0),
            ('五行', '哲学', 12, 4.8),
            ('占卜', '应用', 7, 3.5),
            ('自强不息', '哲理', 5, 4.2)
        ]
        
        cursor.executemany("""
            INSERT OR REPLACE INTO keywords_tags 
            (keyword, category, frequency, importance_score)
            VALUES (?, ?, ?, ?)
        """, keywords_data)
        
        print(f"插入了 {len(keywords_data)} 个关键词")
        
        conn.commit()
        print("✅ 测试数据插入完成！")
        
        # 验证数据
        cursor.execute("SELECT COUNT(*) FROM hexagrams")
        hex_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM lines")
        line_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM interpretations")
        interp_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM divination_cases")
        case_count = cursor.fetchone()[0]
        
        print(f"\n📊 数据库内容统计:")
        print(f"  卦象: {hex_count} 个")
        print(f"  爻位: {line_count} 个") 
        print(f"  注解: {interp_count} 个")
        print(f"  案例: {case_count} 个")
        
    except Exception as e:
        print(f"❌ 插入数据失败: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()
    
    return True

def main():
    """主函数"""
    # 查找数据库
    possible_paths = [
        "../data/database/yixue_knowledge_base.db",
        "../data/database/demo_yixue_kb.db",
        "yixue_knowledge_base.db"
    ]
    
    db_path = None
    for path in possible_paths:
        if Path(path).exists():
            db_path = path
            break
    
    if not db_path:
        print("❌ 找不到数据库文件")
        return
    
    print(f"📍 使用数据库: {Path(db_path).resolve()}")
    
    # 插入测试数据
    success = insert_test_data(db_path)
    
    if success:
        print("\n🚀 现在可以运行RAG系统测试:")
        print("   python simple_demo.py")
    else:
        print("\n❌ 数据插入失败")

if __name__ == "__main__":
    main()