#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
高性能SQLite易学知识库管理工具
支持10万+记录的高效数据操作、FTS5全文搜索、分层存储管理

主要功能:
1. 数据库初始化和连接管理
2. 高性能CRUD操作
3. FTS5全文搜索
4. 分层存储管理 (核心5MB/扩展50MB)
5. 查询性能监控和优化
6. 批量数据导入/导出
7. 数据完整性检查

作者: Claude
创建时间: 2025-08-07
"""

import sqlite3
import json
import time
import os
import logging
from typing import Dict, List, Tuple, Optional, Union, Any
from contextlib import contextmanager
from datetime import datetime
import threading
from dataclasses import dataclass


@dataclass
class QueryPerformance:
    """查询性能统计数据类"""
    query_type: str
    execution_time_ms: int
    result_count: int
    cache_hit: bool = False


class DatabaseManager:
    """高性能SQLite易学知识库管理器"""
    
    def __init__(self, db_path: str = "yixue_knowledge_base.db", 
                 enable_performance_logging: bool = True):
        """
        初始化数据库管理器
        
        Args:
            db_path: 数据库文件路径
            enable_performance_logging: 是否启用性能日志记录
        """
        self.db_path = db_path
        self.enable_performance_logging = enable_performance_logging
        self._connection_cache = threading.local()
        self._query_cache = {}  # 简单查询缓存
        self._cache_size = 1000  # 缓存大小限制
        
        # 设置日志
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # 初始化数据库
        self._initialize_database()
    
    def _initialize_database(self):
        """初始化数据库，创建表结构"""
        schema_path = os.path.join(os.path.dirname(__file__), 'complete_schema.sql')
        
        if os.path.exists(schema_path):
            with open(schema_path, 'r', encoding='utf-8') as f:
                schema_sql = f.read()
            
            try:
                with self.get_connection() as conn:
                    # 分段执行SQL以避免executescript问题
                    statements = schema_sql.split(';')
                    for stmt in statements:
                        stmt = stmt.strip()
                        if stmt and not stmt.startswith('--'):
                            conn.execute(stmt)
                    conn.commit()
                    self.logger.info("数据库架构初始化完成")
            except Exception as e:
                self.logger.error(f"数据库初始化失败: {e}")
                # 如果失败，创建最基本的表结构
                self._create_basic_schema()
        else:
            self.logger.warning(f"架构文件不存在: {schema_path}")
            self._create_basic_schema()
    
    def _create_basic_schema(self):
        """创建基础表结构"""
        basic_schema = '''
        -- 基础表结构
        CREATE TABLE IF NOT EXISTS hexagrams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            gua_number INTEGER NOT NULL UNIQUE,
            gua_name TEXT NOT NULL,
            gua_name_pinyin TEXT NOT NULL,
            upper_trigram TEXT NOT NULL,
            lower_trigram TEXT NOT NULL,
            binary_code TEXT NOT NULL,
            unicode_symbol TEXT,
            basic_meaning TEXT NOT NULL,
            judgement TEXT,
            image TEXT,
            decision TEXT,
            category TEXT,
            nature TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS lines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hexagram_id INTEGER NOT NULL,
            line_position INTEGER NOT NULL,
            line_type INTEGER NOT NULL,
            line_text TEXT NOT NULL,
            line_meaning TEXT,
            line_image TEXT,
            is_changing_line BOOLEAN DEFAULT 0,
            element TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (hexagram_id) REFERENCES hexagrams(id)
        );
        
        CREATE TABLE IF NOT EXISTS interpretations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            target_type TEXT NOT NULL,
            target_id INTEGER NOT NULL,
            author TEXT NOT NULL,
            interpretation_text TEXT NOT NULL,
            dynasty TEXT,
            source_book TEXT,
            interpretation_type TEXT,
            importance_level INTEGER DEFAULT 3,
            is_core_content BOOLEAN DEFAULT 0,
            content_length INTEGER,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS divination_cases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_title TEXT NOT NULL,
            hexagram_id INTEGER NOT NULL,
            question_type TEXT,
            question_detail TEXT,
            interpretation TEXT NOT NULL,
            actual_result TEXT,
            accuracy_rating INTEGER,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (hexagram_id) REFERENCES hexagrams(id)
        );
        
        CREATE TABLE IF NOT EXISTS keywords_tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            keyword TEXT NOT NULL UNIQUE,
            category TEXT,
            frequency INTEGER DEFAULT 1,
            importance_score REAL DEFAULT 1.0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS query_performance_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            query_type TEXT NOT NULL,
            execution_time_ms INTEGER,
            result_count INTEGER,
            cache_hit BOOLEAN DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        '''
        
        try:
            with self.get_connection() as conn:
                conn.executescript(basic_schema)
                conn.commit()
                self.logger.info("基础数据库架构创建完成")
        except Exception as e:
            self.logger.error(f"创建基础架构失败: {e}")
    
    @contextmanager
    def get_connection(self):
        """获取数据库连接 (线程安全)"""
        if not hasattr(self._connection_cache, 'connection'):
            self._connection_cache.connection = sqlite3.connect(
                self.db_path,
                check_same_thread=False,
                timeout=30.0
            )
            # 优化连接设置
            conn = self._connection_cache.connection
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute("PRAGMA journal_mode = WAL") 
            conn.execute("PRAGMA synchronous = NORMAL")
            conn.execute("PRAGMA cache_size = -64000")  # 64MB缓存
            conn.execute("PRAGMA temp_store = MEMORY")
            conn.execute("PRAGMA mmap_size = 268435456")  # 256MB内存映射
            conn.row_factory = sqlite3.Row  # 启用字典式访问
        
        try:
            yield self._connection_cache.connection
        except Exception as e:
            self._connection_cache.connection.rollback()
            self.logger.error(f"数据库操作错误: {e}")
            raise
    
    def _log_performance(self, query_type: str, execution_time_ms: int, 
                        result_count: int, cache_hit: bool = False):
        """记录查询性能"""
        if not self.enable_performance_logging:
            return
            
        perf = QueryPerformance(query_type, execution_time_ms, result_count, cache_hit)
        
        # 记录到数据库
        with self.get_connection() as conn:
            conn.execute("""
                INSERT INTO query_performance_log 
                (query_type, execution_time_ms, result_count, cache_hit)
                VALUES (?, ?, ?, ?)
            """, (perf.query_type, perf.execution_time_ms, 
                  perf.result_count, perf.cache_hit))
            conn.commit()
    
    def _execute_with_performance_tracking(self, query: str, params: tuple = None,
                                         query_type: str = "unknown") -> List[sqlite3.Row]:
        """执行查询并追踪性能"""
        # 检查缓存
        cache_key = f"{query}:{params}"
        if cache_key in self._query_cache:
            self._log_performance(query_type, 0, len(self._query_cache[cache_key]), True)
            return self._query_cache[cache_key]
        
        start_time = time.time()
        
        with self.get_connection() as conn:
            if params:
                cursor = conn.execute(query, params)
            else:
                cursor = conn.execute(query)
            results = cursor.fetchall()
        
        execution_time_ms = int((time.time() - start_time) * 1000)
        
        # 缓存结果 (限制缓存大小)
        if len(self._query_cache) < self._cache_size:
            self._query_cache[cache_key] = results
        
        self._log_performance(query_type, execution_time_ms, len(results))
        return results

    # ========================================================================
    # 卦象管理 (Hexagrams)
    # ========================================================================
    
    def insert_hexagram(self, gua_number: int, gua_name: str, gua_name_pinyin: str,
                       upper_trigram: str, lower_trigram: str, binary_code: str,
                       unicode_symbol: str = None, basic_meaning: str = "",
                       judgement: str = "", image: str = "", decision: str = "",
                       category: str = "", nature: str = "") -> int:
        """插入卦象信息"""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                INSERT INTO hexagrams 
                (gua_number, gua_name, gua_name_pinyin, upper_trigram, lower_trigram,
                 binary_code, unicode_symbol, basic_meaning, judgement, image, 
                 decision, category, nature)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (gua_number, gua_name, gua_name_pinyin, upper_trigram, lower_trigram,
                  binary_code, unicode_symbol, basic_meaning, judgement, image,
                  decision, category, nature))
            conn.commit()
            return cursor.lastrowid
    
    def get_hexagram_by_number(self, gua_number: int) -> Optional[sqlite3.Row]:
        """根据卦号获取卦象"""
        results = self._execute_with_performance_tracking(
            "SELECT * FROM hexagrams WHERE gua_number = ?",
            (gua_number,),
            "get_hexagram_by_number"
        )
        return results[0] if results else None
    
    def get_hexagram_by_name(self, gua_name: str) -> Optional[sqlite3.Row]:
        """根据卦名获取卦象"""
        results = self._execute_with_performance_tracking(
            "SELECT * FROM hexagrams WHERE gua_name = ?",
            (gua_name,),
            "get_hexagram_by_name"
        )
        return results[0] if results else None
    
    def get_complete_hexagram_info(self, hexagram_id: int) -> Dict:
        """获取完整卦象信息 (包含所有爻)"""
        results = self._execute_with_performance_tracking(
            "SELECT * FROM v_complete_hexagrams WHERE hexagram_id = ?",
            (hexagram_id,),
            "get_complete_hexagram_info"
        )
        return dict(results[0]) if results else {}

    # ========================================================================
    # 爻管理 (Lines)
    # ========================================================================
    
    def insert_line(self, hexagram_id: int, line_position: int, line_type: int,
                   line_text: str, line_meaning: str = "", line_image: str = "",
                   is_changing_line: bool = False, element: str = "") -> int:
        """插入爻信息"""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                INSERT INTO lines 
                (hexagram_id, line_position, line_type, line_text, line_meaning,
                 line_image, is_changing_line, element)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (hexagram_id, line_position, line_type, line_text, line_meaning,
                  line_image, is_changing_line, element))
            conn.commit()
            return cursor.lastrowid
    
    def get_lines_by_hexagram(self, hexagram_id: int) -> List[sqlite3.Row]:
        """获取指定卦的所有爻"""
        return self._execute_with_performance_tracking(
            "SELECT * FROM lines WHERE hexagram_id = ? ORDER BY line_position",
            (hexagram_id,),
            "get_lines_by_hexagram"
        )
    
    def get_changing_lines(self, hexagram_id: int) -> List[sqlite3.Row]:
        """获取指定卦的变爻"""
        return self._execute_with_performance_tracking(
            "SELECT * FROM lines WHERE hexagram_id = ? AND is_changing_line = 1",
            (hexagram_id,),
            "get_changing_lines"
        )

    # ========================================================================
    # 注解管理 (Interpretations)
    # ========================================================================
    
    def insert_interpretation(self, target_type: str, target_id: int, author: str,
                            interpretation_text: str, dynasty: str = "",
                            source_book: str = "", interpretation_type: str = "",
                            importance_level: int = 3, keywords: str = "") -> int:
        """插入注解"""
        is_core = importance_level >= 4 or author in ['朱熹', '程颐', '王弼', '孔子']
        
        with self.get_connection() as conn:
            cursor = conn.execute("""
                INSERT INTO interpretations 
                (target_type, target_id, author, dynasty, source_book,
                 interpretation_text, interpretation_type, importance_level,
                 is_core_content, keywords, content_length)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (target_type, target_id, author, dynasty, source_book,
                  interpretation_text, interpretation_type, importance_level,
                  is_core, keywords, len(interpretation_text)))
            conn.commit()
            return cursor.lastrowid
    
    def get_interpretations_by_target(self, target_type: str, target_id: int,
                                    core_only: bool = False) -> List[sqlite3.Row]:
        """获取指定目标的注解"""
        query = """
            SELECT * FROM interpretations 
            WHERE target_type = ? AND target_id = ?
        """
        params = [target_type, target_id]
        
        if core_only:
            query += " AND is_core_content = 1"
        
        query += " ORDER BY importance_level DESC, created_at DESC"
        
        return self._execute_with_performance_tracking(
            query, tuple(params), "get_interpretations_by_target"
        )
    
    def get_core_interpretations(self) -> List[sqlite3.Row]:
        """获取核心注解 (用于分层存储)"""
        return self._execute_with_performance_tracking(
            "SELECT * FROM v_core_interpretations",
            None,
            "get_core_interpretations"
        )

    # ========================================================================
    # 占卜案例管理 (Divination Cases)
    # ========================================================================
    
    def insert_divination_case(self, case_title: str, hexagram_id: int,
                             question_type: str, question_detail: str,
                             interpretation: str, changing_lines: str = "",
                             result_hexagram_id: int = None,
                             actual_result: str = "", accuracy_rating: int = 3,
                             diviner_name: str = "", case_source: str = "",
                             tags: str = "") -> int:
        """插入占卜案例"""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                INSERT INTO divination_cases 
                (case_title, hexagram_id, changing_lines, result_hexagram_id,
                 question_type, question_detail, interpretation, actual_result,
                 accuracy_rating, diviner_name, case_source, tags)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (case_title, hexagram_id, changing_lines, result_hexagram_id,
                  question_type, question_detail, interpretation, actual_result,
                  accuracy_rating, diviner_name, case_source, tags))
            conn.commit()
            return cursor.lastrowid
    
    def get_cases_by_hexagram(self, hexagram_id: int) -> List[sqlite3.Row]:
        """获取指定卦的案例"""
        return self._execute_with_performance_tracking(
            "SELECT * FROM divination_cases WHERE hexagram_id = ? ORDER BY accuracy_rating DESC",
            (hexagram_id,),
            "get_cases_by_hexagram"
        )
    
    def get_popular_cases(self, limit: int = 50) -> List[sqlite3.Row]:
        """获取热门案例"""
        return self._execute_with_performance_tracking(
            "SELECT * FROM v_popular_cases LIMIT ?",
            (limit,),
            "get_popular_cases"
        )

    # ========================================================================
    # 关键词和标签管理 (Keywords & Tags)
    # ========================================================================
    
    def insert_keyword(self, keyword: str, category: str = "", 
                      importance_score: float = 1.0, description: str = "") -> int:
        """插入关键词"""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                INSERT OR IGNORE INTO keywords_tags 
                (keyword, category, importance_score, description)
                VALUES (?, ?, ?, ?)
            """, (keyword, category, importance_score, description))
            conn.commit()
            return cursor.lastrowid
    
    def add_content_tag(self, content_type: str, content_id: int, 
                       keyword: str, relevance_score: float = 1.0) -> bool:
        """为内容添加标签"""
        try:
            # 先确保关键词存在
            keyword_id = self._get_or_create_keyword(keyword)
            
            with self.get_connection() as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO content_tags 
                    (content_type, content_id, keyword_id, relevance_score)
                    VALUES (?, ?, ?, ?)
                """, (content_type, content_id, keyword_id, relevance_score))
                conn.commit()
                return True
        except Exception as e:
            self.logger.error(f"添加标签失败: {e}")
            return False
    
    def _get_or_create_keyword(self, keyword: str) -> int:
        """获取或创建关键词"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                "SELECT id FROM keywords_tags WHERE keyword = ?", (keyword,))
            result = cursor.fetchone()
            
            if result:
                return result[0]
            else:
                cursor = conn.execute(
                    "INSERT INTO keywords_tags (keyword) VALUES (?)", (keyword,))
                return cursor.lastrowid
    
    def get_keyword_stats(self) -> List[sqlite3.Row]:
        """获取关键词统计"""
        return self._execute_with_performance_tracking(
            "SELECT * FROM v_keyword_stats ORDER BY usage_count DESC LIMIT 100",
            None,
            "get_keyword_stats"
        )

    # ========================================================================
    # FTS5全文搜索
    # ========================================================================
    
    def search_hexagrams(self, query: str, limit: int = 20) -> List[Dict]:
        """卦象全文搜索"""
        results = self._execute_with_performance_tracking(
            """
            SELECT h.*, bm25(fts_hexagrams) as relevance
            FROM fts_hexagrams 
            JOIN hexagrams h ON h.id = fts_hexagrams.rowid
            WHERE fts_hexagrams MATCH ?
            ORDER BY relevance LIMIT ?
            """,
            (query, limit),
            "search_hexagrams"
        )
        return [dict(row) for row in results]
    
    def search_lines(self, query: str, limit: int = 50) -> List[Dict]:
        """爻辞全文搜索"""
        results = self._execute_with_performance_tracking(
            """
            SELECT l.*, h.gua_name, bm25(fts_lines) as relevance
            FROM fts_lines
            JOIN lines l ON l.id = fts_lines.rowid
            JOIN hexagrams h ON l.hexagram_id = h.id
            WHERE fts_lines MATCH ?
            ORDER BY relevance LIMIT ?
            """,
            (query, limit),
            "search_lines"
        )
        return [dict(row) for row in results]
    
    def search_interpretations(self, query: str, core_only: bool = False, 
                             limit: int = 50) -> List[Dict]:
        """注解全文搜索"""
        where_clause = "WHERE fts_interpretations MATCH ?"
        params = [query]
        
        if core_only:
            where_clause += " AND i.is_core_content = 1"
        
        results = self._execute_with_performance_tracking(
            f"""
            SELECT i.*, bm25(fts_interpretations) as relevance
            FROM fts_interpretations
            JOIN interpretations i ON i.id = fts_interpretations.rowid
            {where_clause}
            ORDER BY relevance LIMIT ?
            """,
            tuple(params + [limit]),
            "search_interpretations"
        )
        return [dict(row) for row in results]
    
    def search_cases(self, query: str, limit: int = 30) -> List[Dict]:
        """案例全文搜索"""
        results = self._execute_with_performance_tracking(
            """
            SELECT dc.*, h.gua_name as main_hexagram_name, 
                   bm25(fts_cases) as relevance
            FROM fts_cases
            JOIN divination_cases dc ON dc.id = fts_cases.rowid
            JOIN hexagrams h ON dc.hexagram_id = h.id
            WHERE fts_cases MATCH ?
            ORDER BY relevance LIMIT ?
            """,
            (query, limit),
            "search_cases"
        )
        return [dict(row) for row in results]
    
    def universal_search(self, query: str, limit_per_type: int = 10) -> Dict[str, List]:
        """通用搜索 (搜索所有类型)"""
        return {
            'hexagrams': self.search_hexagrams(query, limit_per_type),
            'lines': self.search_lines(query, limit_per_type), 
            'interpretations': self.search_interpretations(query, False, limit_per_type),
            'cases': self.search_cases(query, limit_per_type)
        }

    # ========================================================================
    # 高级查询和分析
    # ========================================================================
    
    def get_hexagram_with_related_content(self, hexagram_id: int) -> Dict:
        """获取卦象及其所有关联内容"""
        hexagram = dict(self.get_complete_hexagram_info(hexagram_id))
        if not hexagram:
            return {}
        
        # 获取所有爻
        lines = [dict(row) for row in self.get_lines_by_hexagram(hexagram_id)]
        
        # 获取卦象注解
        hexagram_interpretations = [dict(row) for row in 
                                   self.get_interpretations_by_target('hexagram', hexagram_id)]
        
        # 获取爻注解
        line_interpretations = []
        for line in lines:
            line_interps = [dict(row) for row in 
                           self.get_interpretations_by_target('line', line['id'])]
            line_interpretations.extend(line_interps)
        
        # 获取相关案例
        cases = [dict(row) for row in self.get_cases_by_hexagram(hexagram_id)]
        
        return {
            'hexagram': hexagram,
            'lines': lines,
            'hexagram_interpretations': hexagram_interpretations,
            'line_interpretations': line_interpretations,
            'cases': cases
        }
    
    def get_similar_hexagrams(self, hexagram_id: int, limit: int = 5) -> List[Dict]:
        """根据卦象特征找相似卦象"""
        hexagram = self.get_hexagram_by_number(hexagram_id)
        if not hexagram:
            return []
        
        # 基于上下卦、性质等找相似卦象
        results = self._execute_with_performance_tracking(
            """
            SELECT h.*, 
                   CASE 
                       WHEN upper_trigram = ? AND lower_trigram = ? THEN 3
                       WHEN upper_trigram = ? OR lower_trigram = ? THEN 2
                       WHEN nature = ? THEN 1
                       ELSE 0
                   END as similarity_score
            FROM hexagrams h
            WHERE h.id != ? AND similarity_score > 0
            ORDER BY similarity_score DESC, gua_number
            LIMIT ?
            """,
            (hexagram['upper_trigram'], hexagram['lower_trigram'],
             hexagram['upper_trigram'], hexagram['lower_trigram'],
             hexagram['nature'], hexagram_id, limit),
            "get_similar_hexagrams"
        )
        return [dict(row) for row in results]

    # ========================================================================
    # 数据库维护和优化
    # ========================================================================
    
    def get_storage_stats(self) -> List[Dict]:
        """获取存储统计信息"""
        results = self._execute_with_performance_tracking(
            "SELECT * FROM v_storage_stats",
            None,
            "get_storage_stats"
        )
        return [dict(row) for row in results]
    
    def get_performance_stats(self, hours: int = 24) -> List[Dict]:
        """获取性能统计"""
        results = self._execute_with_performance_tracking(
            """
            SELECT query_type, 
                   COUNT(*) as query_count,
                   AVG(execution_time_ms) as avg_time_ms,
                   MAX(execution_time_ms) as max_time_ms,
                   AVG(result_count) as avg_result_count,
                   SUM(CASE WHEN cache_hit THEN 1 ELSE 0 END) * 1.0 / COUNT(*) as cache_hit_ratio
            FROM query_performance_log
            WHERE created_at >= datetime('now', '-{} hours')
            GROUP BY query_type
            ORDER BY query_count DESC
            """.format(hours),
            None,
            "get_performance_stats"
        )
        return [dict(row) for row in results]
    
    def check_data_integrity(self) -> List[Dict]:
        """检查数据完整性"""
        results = self._execute_with_performance_tracking(
            "SELECT * FROM v_data_integrity_check",
            None,
            "check_data_integrity"
        )
        return [dict(row) for row in results]
    
    def optimize_database(self):
        """优化数据库"""
        with self.get_connection() as conn:
            self.logger.info("开始优化数据库...")
            
            # 重建索引
            conn.execute("REINDEX")
            
            # 优化FTS索引
            conn.execute("INSERT INTO fts_hexagrams(fts_hexagrams) VALUES('optimize')")
            conn.execute("INSERT INTO fts_lines(fts_lines) VALUES('optimize')")
            conn.execute("INSERT INTO fts_interpretations(fts_interpretations) VALUES('optimize')")
            conn.execute("INSERT INTO fts_cases(fts_cases) VALUES('optimize')")
            
            # 清理过期的性能日志 (保留最近30天)
            conn.execute("""
                DELETE FROM query_performance_log 
                WHERE created_at < datetime('now', '-30 days')
            """)
            
            # 分析表统计信息
            conn.execute("ANALYZE")
            
            conn.commit()
            self.logger.info("数据库优化完成")
    
    def clear_cache(self):
        """清空查询缓存"""
        self._query_cache.clear()
        self.logger.info("查询缓存已清空")
    
    def backup_database(self, backup_path: str) -> bool:
        """备份数据库"""
        try:
            with self.get_connection() as conn:
                with open(backup_path, 'w', encoding='utf-8') as f:
                    for line in conn.iterdump():
                        f.write(f'{line}\n')
            
            self.logger.info(f"数据库备份完成: {backup_path}")
            return True
        except Exception as e:
            self.logger.error(f"备份失败: {e}")
            return False

    # ========================================================================
    # 批量操作
    # ========================================================================
    
    def batch_insert_hexagrams(self, hexagrams_data: List[Dict]) -> List[int]:
        """批量插入卦象"""
        inserted_ids = []
        with self.get_connection() as conn:
            for data in hexagrams_data:
                cursor = conn.execute("""
                    INSERT INTO hexagrams 
                    (gua_number, gua_name, gua_name_pinyin, upper_trigram, 
                     lower_trigram, binary_code, unicode_symbol, basic_meaning,
                     judgement, image, decision, category, nature)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    data['gua_number'], data['gua_name'], data['gua_name_pinyin'],
                    data['upper_trigram'], data['lower_trigram'], data['binary_code'],
                    data.get('unicode_symbol'), data.get('basic_meaning', ''),
                    data.get('judgement', ''), data.get('image', ''),
                    data.get('decision', ''), data.get('category', ''),
                    data.get('nature', '')
                ))
                inserted_ids.append(cursor.lastrowid)
            conn.commit()
        return inserted_ids
    
    def export_to_json(self, output_path: str, table_name: str = None) -> bool:
        """导出数据为JSON格式"""
        try:
            export_data = {}
            
            tables_to_export = [table_name] if table_name else [
                'hexagrams', 'lines', 'interpretations', 
                'divination_cases', 'keywords_tags'
            ]
            
            for table in tables_to_export:
                results = self._execute_with_performance_tracking(
                    f"SELECT * FROM {table}",
                    None,
                    f"export_{table}"
                )
                export_data[table] = [dict(row) for row in results]
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2, default=str)
            
            self.logger.info(f"数据导出完成: {output_path}")
            return True
        except Exception as e:
            self.logger.error(f"导出失败: {e}")
            return False
    
    def close(self):
        """关闭数据库连接"""
        if hasattr(self._connection_cache, 'connection'):
            self._connection_cache.connection.close()
            delattr(self._connection_cache, 'connection')


# ========================================================================
# 命令行工具
# ========================================================================

def main():
    """命令行主程序"""
    import argparse
    
    parser = argparse.ArgumentParser(description='易学知识库管理工具')
    parser.add_argument('--db', default='yixue_knowledge_base.db', 
                       help='数据库文件路径')
    parser.add_argument('--init', action='store_true', help='初始化数据库')
    parser.add_argument('--optimize', action='store_true', help='优化数据库')
    parser.add_argument('--stats', action='store_true', help='显示统计信息')
    parser.add_argument('--search', type=str, help='全文搜索')
    parser.add_argument('--backup', type=str, help='备份数据库到指定路径')
    parser.add_argument('--export', type=str, help='导出数据到JSON文件')
    
    args = parser.parse_args()
    
    db = DatabaseManager(args.db)
    
    try:
        if args.init:
            print("数据库初始化完成")
        
        if args.optimize:
            db.optimize_database()
            print("数据库优化完成")
        
        if args.stats:
            storage_stats = db.get_storage_stats()
            print("\n=== 存储统计 ===")
            for stat in storage_stats:
                print(f"{stat['table_name']}: {stat['record_count']} 记录, "
                      f"~{stat['estimated_size_bytes'] / 1024:.1f}KB")
            
            perf_stats = db.get_performance_stats(24)
            print("\n=== 性能统计 (24小时) ===")
            for stat in perf_stats:
                print(f"{stat['query_type']}: {stat['query_count']} 次查询, "
                      f"平均 {stat['avg_time_ms']:.1f}ms, "
                      f"缓存命中率 {stat['cache_hit_ratio']:.1%}")
        
        if args.search:
            results = db.universal_search(args.search, 5)
            print(f"\n=== 搜索结果: {args.search} ===")
            for content_type, items in results.items():
                if items:
                    print(f"\n{content_type.upper()}:")
                    for item in items:
                        if content_type == 'hexagrams':
                            print(f"  - {item['gua_name']}: {item['basic_meaning']}")
                        elif content_type == 'lines':
                            print(f"  - {item['gua_name']} Line {item['line_position']}: {item['line_text'][:50]}...")
                        elif content_type == 'interpretations':
                            print(f"  - {item['author']}: {item['interpretation_text'][:50]}...")
                        elif content_type == 'cases':
                            print(f"  - {item['case_title']}: {item['question_detail'][:50]}...")
        
        if args.backup:
            if db.backup_database(args.backup):
                print(f"数据库备份到: {args.backup}")
            else:
                print("备份失败")
        
        if args.export:
            if db.export_to_json(args.export):
                print(f"数据导出到: {args.export}")
            else:
                print("导出失败")
    
    finally:
        db.close()


if __name__ == "__main__":
    main()