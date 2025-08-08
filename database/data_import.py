#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SQLite易学知识库数据导入脚本
高效批量导入，支持数据验证、去重和分层处理
优化目标: 核心包<10MB，高质量数据优先
"""

import sqlite3
import json
import hashlib
import time
import os
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import logging
from datetime import datetime

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class ImportStats:
    """导入统计信息"""
    total_processed: int = 0
    successful_imports: int = 0
    duplicates_skipped: int = 0
    low_quality_filtered: int = 0
    errors: List[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
    
    @property
    def success_rate(self) -> float:
        return (self.successful_imports / max(self.total_processed, 1)) * 100

class YiGuaDataImporter:
    """易经数据导入器"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn: Optional[sqlite3.Connection] = None
        self.stats = ImportStats()
        
        # 质量过滤阈值
        self.quality_thresholds = {
            'core': 0.9,      # 核心数据需要90%以上质量
            'extended': 0.7,  # 扩展数据需要70%以上质量
            'cloud': 0.5      # 云端数据需要50%以上质量
        }
    
    def __enter__(self):
        """上下文管理器入口"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.close()
    
    def connect(self):
        """连接数据库"""
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.execute("PRAGMA foreign_keys = ON")
            self.conn.execute("PRAGMA journal_mode = WAL")
            logger.info(f"Connected to database: {self.db_path}")
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise
    
    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed")
    
    def execute_schema(self, schema_file: str):
        """执行数据库架构脚本"""
        try:
            with open(schema_file, 'r', encoding='utf-8') as f:
                schema_sql = f.read()
            
            # 按分号分割SQL语句并执行
            statements = [stmt.strip() for stmt in schema_sql.split(';') if stmt.strip()]
            
            for statement in statements:
                if statement:
                    self.conn.execute(statement)
            
            self.conn.commit()
            logger.info(f"Schema executed successfully from {schema_file}")
            
        except Exception as e:
            logger.error(f"Failed to execute schema: {e}")
            raise
    
    def import_base_trigrams(self) -> int:
        """导入八卦基础数据"""
        trigrams_data = [
            (1, '乾', '☰', '111', '天', '刚健', '西北', '秋冬', '父', 1),
            (2, '兑', '☱', '110', '泽', '喜悦', '西', '秋', '少女', 1),
            (3, '离', '☲', '101', '火', '光明', '南', '夏', '中女', 1),
            (4, '震', '☳', '100', '雷', '震动', '东', '春', '长男', 1),
            (5, '巽', '☴', '011', '风', '顺入', '东南', '春夏', '长女', 1),
            (6, '坎', '☵', '010', '水', '陷险', '北', '冬', '中男', 1),
            (7, '艮', '☶', '001', '山', '止静', '东北', '冬春', '少男', 1),
            (8, '坤', '☷', '000', '地', '柔顺', '西南', '夏秋', '母', 1),
        ]
        
        cursor = self.conn.cursor()
        cursor.executemany('''
            INSERT OR REPLACE INTO trigrams 
            (id, name, symbol, binary, nature, attribute, direction, season, family_role, data_tier)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', trigrams_data)
        
        self.conn.commit()
        logger.info(f"Imported {len(trigrams_data)} trigrams")
        return len(trigrams_data)
    
    def calculate_hexagram_properties(self, binary: str) -> Dict[str, Any]:
        """计算卦象属性"""
        upper = int(binary[:3], 2) + 1  # 上卦
        lower = int(binary[3:], 2) + 1  # 下卦
        
        # 计算宫位 (根据下卦)
        palace = lower
        
        return {
            'upper_trigram': upper,
            'lower_trigram': lower,
            'palace': palace,
            'binary_value': binary
        }
    
    def import_hexagrams_from_json(self, json_file: str) -> int:
        """从JSON文件导入卦象数据"""
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                hexagrams_data = json.load(f)
            
            cursor = self.conn.cursor()
            imported_count = 0
            
            for hex_data in hexagrams_data:
                try:
                    # 数据验证和清洗
                    if not self._validate_hexagram_data(hex_data):
                        continue
                    
                    # 计算卦象属性
                    binary = hex_data.get('binary', '111111')
                    properties = self.calculate_hexagram_properties(binary)
                    
                    # 质量评分 (根据数据完整性)
                    quality_score = self._calculate_quality_score(hex_data)
                    
                    # 确定数据层级
                    data_tier = self._determine_data_tier(quality_score)
                    
                    cursor.execute('''
                        INSERT OR REPLACE INTO hexagrams 
                        (id, name, chinese_name, symbol, upper_trigram, lower_trigram, 
                         judgment, image, sequence_king_wen, sequence_fuxi, binary_value, 
                         palace, data_tier, quality_score)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        hex_data['id'],
                        hex_data['name'],
                        hex_data.get('chinese_name', hex_data['name']),
                        hex_data.get('symbol', ''),
                        properties['upper_trigram'],
                        properties['lower_trigram'],
                        hex_data.get('judgment', ''),
                        hex_data.get('image', ''),
                        hex_data.get('sequence_king_wen', hex_data['id']),
                        hex_data.get('sequence_fuxi', hex_data['id']),
                        properties['binary_value'],
                        properties['palace'],
                        data_tier,
                        quality_score
                    ))
                    
                    imported_count += 1
                    self.stats.successful_imports += 1
                    
                    # 导入爻辞数据
                    if 'lines' in hex_data:
                        self._import_lines_for_hexagram(hex_data['id'], hex_data['lines'], cursor)
                    
                except Exception as e:
                    logger.error(f"Error importing hexagram {hex_data.get('id', 'unknown')}: {e}")
                    self.stats.errors.append(f"Hexagram {hex_data.get('id')}: {str(e)}")
                    continue
            
            self.conn.commit()
            logger.info(f"Imported {imported_count} hexagrams from {json_file}")
            return imported_count
            
        except Exception as e:
            logger.error(f"Failed to import hexagrams from {json_file}: {e}")
            raise
    
    def _import_lines_for_hexagram(self, hexagram_id: int, lines_data: List[Dict], cursor):
        """为指定卦象导入爻辞数据"""
        for line_data in lines_data:
            try:
                line_type = 1 if line_data.get('type') == '阳' else 0
                position = line_data.get('position', 1)
                
                cursor.execute('''
                    INSERT OR REPLACE INTO lines 
                    (hexagram_id, position, type, text, image, data_tier)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    hexagram_id,
                    position,
                    line_type,
                    line_data.get('text', ''),
                    line_data.get('image', ''),
                    self._determine_data_tier(0.9)  # 爻辞默认高质量
                ))
                
            except Exception as e:
                logger.error(f"Error importing line {position} for hexagram {hexagram_id}: {e}")
    
    def import_interpretations_batch(self, interpretations_data: List[Dict]) -> int:
        """批量导入解释数据"""
        cursor = self.conn.cursor()
        imported_count = 0
        
        # 准备批量插入数据
        batch_data = []
        
        for interp in interpretations_data:
            try:
                # 数据验证
                if not self._validate_interpretation_data(interp):
                    continue
                
                # 质量评分
                quality_score = self._calculate_interpretation_quality(interp)
                
                # 内容长度
                content_length = len(interp.get('content', ''))
                
                # 可读性评分 (简化计算)
                readability_score = min(1.0, content_length / 500)  # 500字为满分
                
                batch_data.append((
                    interp['target_type'],
                    interp['target_id'],
                    interp.get('category', 2),
                    interp['title'],
                    interp['content'],
                    interp.get('author'),
                    interp.get('source_book'),
                    content_length,
                    readability_score,
                    self._determine_data_tier(quality_score),
                    quality_score
                ))
                
            except Exception as e:
                logger.error(f"Error processing interpretation: {e}")
                continue
        
        # 执行批量插入
        if batch_data:
            cursor.executemany('''
                INSERT INTO interpretations 
                (target_type, target_id, category, title, content, author, source_book,
                 content_length, readability_score, data_tier, quality_score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', batch_data)
            
            imported_count = len(batch_data)
            self.stats.successful_imports += imported_count
        
        self.conn.commit()
        logger.info(f"Batch imported {imported_count} interpretations")
        return imported_count
    
    def import_divination_cases_batch(self, cases_data: List[Dict]) -> int:
        """批量导入占卜案例"""
        cursor = self.conn.cursor()
        imported_count = 0
        
        for case in cases_data:
            try:
                # 数据验证和清洗
                if not self._validate_case_data(case):
                    continue
                
                # 解析变爻
                changing_lines = json.dumps(case.get('changing_lines', []))
                
                # 准确度评分
                accuracy_rating = self._calculate_case_accuracy(case)
                
                cursor.execute('''
                    INSERT INTO divination_cases 
                    (title, question, method, original_hexagram, changed_hexagram, 
                     changing_lines, analysis_process, judgment, result_verification,
                     author, source_document, difficulty_level, case_category,
                     data_tier, accuracy_rating, divination_time)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    case['title'],
                    case['question'],
                    case.get('method', 1),
                    case['original_hexagram'],
                    case.get('changed_hexagram'),
                    changing_lines,
                    case['analysis_process'],
                    case['judgment'],
                    case.get('result_verification'),
                    case.get('author'),
                    case.get('source_document'),
                    case.get('difficulty_level', 2),
                    case.get('case_category', '其他'),
                    self._determine_data_tier(accuracy_rating),
                    accuracy_rating,
                    case.get('divination_time')
                ))
                
                imported_count += 1
                self.stats.successful_imports += 1
                
            except Exception as e:
                logger.error(f"Error importing case '{case.get('title', 'unknown')}': {e}")
                continue
        
        self.conn.commit()
        logger.info(f"Imported {imported_count} divination cases")
        return imported_count
    
    def _validate_hexagram_data(self, data: Dict) -> bool:
        """验证卦象数据完整性"""
        required_fields = ['id', 'name']
        for field in required_fields:
            if field not in data or not data[field]:
                self.stats.errors.append(f"Missing required field: {field}")
                return False
        
        # 验证ID范围
        if not (1 <= data['id'] <= 64):
            self.stats.errors.append(f"Invalid hexagram ID: {data['id']}")
            return False
        
        return True
    
    def _validate_interpretation_data(self, data: Dict) -> bool:
        """验证解释数据完整性"""
        required_fields = ['target_type', 'target_id', 'title', 'content']
        for field in required_fields:
            if field not in data or not data[field]:
                return False
        return True
    
    def _validate_case_data(self, data: Dict) -> bool:
        """验证案例数据完整性"""
        required_fields = ['title', 'question', 'original_hexagram', 'analysis_process', 'judgment']
        for field in required_fields:
            if field not in data or not data[field]:
                return False
        return True
    
    def _calculate_quality_score(self, data: Dict) -> float:
        """计算数据质量评分"""
        score = 0.0
        total_weight = 0.0
        
        # 基础字段完整性 (40%)
        basic_fields = ['name', 'judgment', 'image']
        basic_weight = 0.4
        basic_score = sum(1 for field in basic_fields if data.get(field)) / len(basic_fields)
        score += basic_score * basic_weight
        total_weight += basic_weight
        
        # 内容长度和丰富性 (30%)
        content_weight = 0.3
        judgment_length = len(data.get('judgment', ''))
        image_length = len(data.get('image', ''))
        content_score = min(1.0, (judgment_length + image_length) / 200)  # 200字为满分
        score += content_score * content_weight
        total_weight += content_weight
        
        # 结构化数据完整性 (20%)
        struct_weight = 0.2
        struct_fields = ['symbol', 'sequence_king_wen', 'binary']
        struct_score = sum(1 for field in struct_fields if data.get(field)) / len(struct_fields)
        score += struct_score * struct_weight
        total_weight += struct_weight
        
        # 扩展信息 (10%)
        ext_weight = 0.1
        ext_fields = ['lines', 'annotations']
        ext_score = sum(1 for field in ext_fields if data.get(field)) / len(ext_fields)
        score += ext_score * ext_weight
        total_weight += ext_weight
        
        return score / total_weight if total_weight > 0 else 0.0
    
    def _calculate_interpretation_quality(self, data: Dict) -> float:
        """计算解释质量评分"""
        score = 0.0
        
        # 内容长度评分 (50%)
        content_length = len(data.get('content', ''))
        length_score = min(1.0, content_length / 300)  # 300字为满分
        score += length_score * 0.5
        
        # 作者权威性 (25%)
        author_score = 0.8 if data.get('author') else 0.2
        score += author_score * 0.25
        
        # 来源可信度 (25%)
        source_score = 0.9 if data.get('source_book') else 0.3
        score += source_score * 0.25
        
        return score
    
    def _calculate_case_accuracy(self, data: Dict) -> float:
        """计算案例准确度评分"""
        score = 0.7  # 基础分
        
        # 有结果验证 (+0.2)
        if data.get('result_verification'):
            score += 0.2
        
        # 分析过程详细 (+0.1)
        analysis_length = len(data.get('analysis_process', ''))
        if analysis_length > 200:
            score += 0.1
        
        return min(1.0, score)
    
    def _determine_data_tier(self, quality_score: float) -> int:
        """根据质量评分确定数据层级"""
        if quality_score >= self.quality_thresholds['core']:
            return 1  # core
        elif quality_score >= self.quality_thresholds['extended']:
            return 2  # extended
        else:
            return 3  # cloud
    
    def estimate_database_size(self) -> Dict[str, Any]:
        """估算数据库大小"""
        cursor = self.conn.cursor()
        
        # 获取各表行数
        tables = ['hexagrams', 'lines', 'interpretations', 'divination_cases']
        size_info = {}
        
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            
            cursor.execute(f"SELECT COUNT(*) FROM {table} WHERE data_tier = 1")
            core_count = cursor.fetchone()[0]
            
            cursor.execute(f"SELECT AVG(LENGTH(judgment || image)) FROM {table}" if table == 'hexagrams' 
                          else f"SELECT AVG(LENGTH(content)) FROM {table}" if 'content' in ['interpretations', 'divination_cases']
                          else f"SELECT AVG(LENGTH(text)) FROM {table}")
            
            avg_size = cursor.fetchone()[0] or 0
            
            size_info[table] = {
                'total_rows': count,
                'core_rows': core_count,
                'avg_content_size': avg_size,
                'estimated_size_mb': (count * avg_size) / (1024 * 1024)
            }
        
        return size_info
    
    def optimize_for_core_package(self, target_size_mb: float = 5.0):
        """优化核心数据包大小"""
        logger.info(f"Optimizing core package to target size: {target_size_mb}MB")
        
        current_size = self.estimate_database_size()
        total_core_size = sum(info['estimated_size_mb'] for info in current_size.values())
        
        logger.info(f"Current estimated core size: {total_core_size:.2f}MB")
        
        if total_core_size > target_size_mb:
            # 降级部分数据到extended层
            self._downgrade_excessive_data(target_size_mb)
        
        # VACUUM优化
        self.conn.execute("VACUUM")
        logger.info("Database optimized and compacted")
    
    def _downgrade_excessive_data(self, target_size_mb: float):
        """降级过量数据到扩展层"""
        cursor = self.conn.cursor()
        
        # 优先降级低质量解释数据
        cursor.execute('''
            UPDATE interpretations 
            SET data_tier = 2 
            WHERE data_tier = 1 
            AND quality_score < 0.95 
            ORDER BY quality_score ASC, content_length ASC
            LIMIT (
                SELECT COUNT(*) / 4 FROM interpretations WHERE data_tier = 1
            )
        ''')
        
        # 降级部分案例数据
        cursor.execute('''
            UPDATE divination_cases 
            SET data_tier = 2 
            WHERE data_tier = 1 
            AND accuracy_rating < 0.9
            ORDER BY accuracy_rating ASC, difficulty_level DESC
            LIMIT (
                SELECT COUNT(*) / 3 FROM divination_cases WHERE data_tier = 1
            )
        ''')
        
        self.conn.commit()
        logger.info("Downgraded excessive data to extended tier")

def main():
    """主函数 - 数据导入示例"""
    db_path = "/mnt/d/desktop/appp/database/yigua_knowledge.db"
    schema_path = "/mnt/d/desktop/appp/database/schema.sql"
    indexes_path = "/mnt/d/desktop/appp/database/indexes.sql"
    
    try:
        with YiGuaDataImporter(db_path) as importer:
            # 1. 执行数据库架构
            if os.path.exists(schema_path):
                importer.execute_schema(schema_path)
            
            # 2. 导入基础八卦数据
            importer.import_base_trigrams()
            
            # 3. 导入64卦数据 (示例数据)
            sample_hexagrams = [
                {
                    "id": 1,
                    "name": "乾",
                    "chinese_name": "乾为天",
                    "symbol": "☰",
                    "binary": "111111",
                    "judgment": "乾：元、亨、利、贞。",
                    "image": "天行健，君子以自强不息。",
                    "sequence_king_wen": 1,
                    "lines": [
                        {"position": 1, "type": "阳", "text": "初九：潜龙，勿用。", "image": "潜龙勿用，阳在下也。"},
                        {"position": 2, "type": "阳", "text": "九二：见龙在田，利见大人。", "image": "见龙在田，德施普也。"},
                        {"position": 3, "type": "阳", "text": "九三：君子终日乾乾，夕惕若，厉无咎。", "image": "终日乾乾，反复道也。"},
                        {"position": 4, "type": "阳", "text": "九四：或跃在渊，无咎。", "image": "或跃在渊，进无咎也。"},
                        {"position": 5, "type": "阳", "text": "九五：飞龙在天，利见大人。", "image": "飞龙在天，大人造也。"},
                        {"position": 6, "type": "阳", "text": "上九：亢龙有悔。", "image": "亢龙有悔，盈不可久也。"}
                    ]
                },
                {
                    "id": 2,
                    "name": "坤",
                    "chinese_name": "坤为地",
                    "symbol": "☷",
                    "binary": "000000",
                    "judgment": "坤：元亨，利牝马之贞。",
                    "image": "地势坤，君子以厚德载物。",
                    "sequence_king_wen": 2
                }
            ]
            
            # 临时写入JSON文件进行测试
            import json
            temp_json = "/tmp/sample_hexagrams.json"
            with open(temp_json, 'w', encoding='utf-8') as f:
                json.dump(sample_hexagrams, f, ensure_ascii=False, indent=2)
            
            importer.import_hexagrams_from_json(temp_json)
            
            # 4. 创建索引
            if os.path.exists(indexes_path):
                importer.execute_schema(indexes_path)
            
            # 5. 优化核心包大小
            importer.optimize_for_core_package(target_size_mb=5.0)
            
            # 6. 输出统计信息
            size_info = importer.estimate_database_size()
            logger.info("=== Import Statistics ===")
            logger.info(f"Success Rate: {importer.stats.success_rate:.1f}%")
            logger.info(f"Total Processed: {importer.stats.total_processed}")
            logger.info(f"Successful Imports: {importer.stats.successful_imports}")
            
            logger.info("=== Database Size Estimation ===")
            for table, info in size_info.items():
                logger.info(f"{table}: {info['core_rows']} core rows, ~{info['estimated_size_mb']:.2f}MB")
            
            total_size = sum(info['estimated_size_mb'] for info in size_info.values())
            logger.info(f"Total estimated core package size: {total_size:.2f}MB")
            
            if importer.stats.errors:
                logger.warning(f"Errors encountered: {len(importer.stats.errors)}")
                for error in importer.stats.errors[:5]:  # 显示前5个错误
                    logger.warning(f"  - {error}")
            
            logger.info("Data import completed successfully!")
            
    except Exception as e:
        logger.error(f"Import failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()