#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SQLite易学知识库性能基准测试
测试查询性能，数据库大小和索引效率
"""

import sqlite3
import time
import json
import sys
from pathlib import Path
from typing import Dict, List, Any, Tuple
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseBenchmark:
    """数据库性能基准测试器"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = None
        self.results = {}
    
    def connect(self):
        """连接数据库"""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        
        # 启用性能优化设置
        self.conn.execute("PRAGMA cache_size = -64000")  # 64MB缓存
        self.conn.execute("PRAGMA temp_store = memory")
        self.conn.execute("PRAGMA mmap_size = 268435456")  # 256MB内存映射
    
    def close(self):
        """关闭连接"""
        if self.conn:
            self.conn.close()
    
    def time_query(self, query: str, params: Tuple = ()) -> Tuple[float, List[Any]]:
        """测量查询执行时间"""
        start_time = time.perf_counter()
        
        cursor = self.conn.cursor()
        cursor.execute(query, params)
        results = cursor.fetchall()
        
        end_time = time.perf_counter()
        execution_time = (end_time - start_time) * 1000  # 转换为毫秒
        
        return execution_time, results
    
    def test_basic_queries(self) -> Dict[str, float]:
        """测试基础查询性能"""
        logger.info("Testing basic queries...")
        
        queries = {
            "hexagram_by_name": (
                "SELECT * FROM hexagrams WHERE name = ?", ('乾',)
            ),
            "hexagram_with_lines": (
                "SELECT h.name, l.position, l.text FROM hexagrams h "
                "LEFT JOIN lines l ON h.id = l.hexagram_id WHERE h.name = ?", 
                ('乾',)
            ),
            "core_hexagrams": (
                "SELECT * FROM hexagrams WHERE data_tier = 1", ()
            ),
            "quality_interpretations": (
                "SELECT * FROM interpretations WHERE quality_score >= 0.9 LIMIT 20", ()
            ),
            "recent_cases": (
                "SELECT * FROM divination_cases ORDER BY created_at DESC LIMIT 10", ()
            )
        }
        
        results = {}
        for test_name, (query, params) in queries.items():
            try:
                exec_time, _ = self.time_query(query, params)
                results[test_name] = exec_time
                logger.info(f"{test_name}: {exec_time:.2f}ms")
            except Exception as e:
                logger.error(f"Error in {test_name}: {e}")
                results[test_name] = -1
        
        return results
    
    def test_fts_queries(self) -> Dict[str, float]:
        """测试全文搜索性能"""
        logger.info("Testing FTS queries...")
        
        queries = {
            "fts_hexagram_simple": (
                "SELECT h.name FROM hexagrams h "
                "JOIN hexagrams_fts ON h.id = hexagrams_fts.rowid "
                "WHERE hexagrams_fts MATCH ?", 
                ('天',)
            ),
            "fts_hexagram_complex": (
                "SELECT h.name, bm25(hexagrams_fts) as score FROM hexagrams h "
                "JOIN hexagrams_fts ON h.id = hexagrams_fts.rowid "
                "WHERE hexagrams_fts MATCH ? AND h.data_tier <= 2 "
                "ORDER BY score LIMIT 10", 
                ('天 AND 龙',)
            ),
            "fts_interpretations": (
                "SELECT i.title FROM interpretations i "
                "JOIN interpretations_fts ON i.id = interpretations_fts.rowid "
                "WHERE interpretations_fts MATCH ?", 
                ('占卜',)
            ),
            "fts_snippet": (
                "SELECT h.name, snippet(hexagrams_fts, -1, '<b>', '</b>', '...', 32) "
                "FROM hexagrams h JOIN hexagrams_fts ON h.id = hexagrams_fts.rowid "
                "WHERE hexagrams_fts MATCH ?", 
                ('乾坤',)
            )
        }
        
        results = {}
        for test_name, (query, params) in queries.items():
            try:
                exec_time, _ = self.time_query(query, params)
                results[test_name] = exec_time
                logger.info(f"{test_name}: {exec_time:.2f}ms")
            except Exception as e:
                logger.error(f"Error in {test_name}: {e}")
                results[test_name] = -1
        
        return results
    
    def test_complex_queries(self) -> Dict[str, float]:
        """测试复杂查询性能"""
        logger.info("Testing complex queries...")
        
        queries = {
            "join_case_hexagram": (
                "SELECT c.title, h.name, c.judgment FROM divination_cases c "
                "JOIN hexagrams h ON c.original_hexagram = h.id "
                "WHERE c.data_tier <= 2 ORDER BY c.accuracy_rating DESC LIMIT 20", ()
            ),
            "aggregation_stats": (
                "SELECT data_tier, COUNT(*) as count, AVG(quality_score) as avg_quality "
                "FROM hexagrams GROUP BY data_tier", ()
            ),
            "knowledge_graph": (
                "SELECT h1.name as from_hex, h2.name as to_hex, kr.relationship_type "
                "FROM knowledge_relationships kr "
                "JOIN hexagrams h1 ON kr.from_id = h1.id AND kr.from_type = 1 "
                "JOIN hexagrams h2 ON kr.to_id = h2.id AND kr.to_type = 1 "
                "WHERE kr.strength >= 0.7 LIMIT 50", ()
            ),
            "multi_table_search": (
                "SELECT 'hexagram' as type, h.name as title FROM hexagrams h "
                "WHERE h.judgment LIKE ? AND h.data_tier <= 2 "
                "UNION ALL "
                "SELECT 'interpretation' as type, i.title FROM interpretations i "
                "WHERE i.content LIKE ? AND i.data_tier <= 2 "
                "LIMIT 30", 
                ('%天%', '%天%')
            )
        }
        
        results = {}
        for test_name, (query, params) in queries.items():
            try:
                exec_time, _ = self.time_query(query, params)
                results[test_name] = exec_time
                logger.info(f"{test_name}: {exec_time:.2f}ms")
            except Exception as e:
                logger.error(f"Error in {test_name}: {e}")
                results[test_name] = -1
        
        return results
    
    def analyze_database_size(self) -> Dict[str, Any]:
        """分析数据库大小"""
        logger.info("Analyzing database size...")
        
        # 数据库总大小
        cursor = self.conn.cursor()
        cursor.execute("SELECT page_count * page_size / (1024.0 * 1024.0) as size_mb "
                      "FROM pragma_page_count(), pragma_page_size()")
        total_size = cursor.fetchone()[0]
        
        # 各表大小分析
        table_sizes = {}
        tables = ['hexagrams', 'lines', 'interpretations', 'divination_cases', 
                 'tags', 'content_tags', 'knowledge_relationships']
        
        for table in tables:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                row_count = cursor.fetchone()[0]
                
                cursor.execute(f"SELECT COUNT(*) FROM {table} WHERE data_tier = 1")
                core_count = cursor.fetchone()[0] if 'data_tier' in self._get_table_columns(table) else 0
                
                table_sizes[table] = {
                    'total_rows': row_count,
                    'core_rows': core_count
                }
            except Exception as e:
                logger.warning(f"Could not analyze table {table}: {e}")
        
        # 索引大小分析
        cursor.execute("""
            SELECT name, SUM(pgsize) / (1024.0 * 1024.0) as size_mb
            FROM dbstat 
            WHERE name LIKE 'idx_%'
            GROUP BY name
            ORDER BY size_mb DESC
            LIMIT 10
        """)
        index_sizes = {row[0]: row[1] for row in cursor.fetchall()}
        
        return {
            'total_size_mb': total_size,
            'table_sizes': table_sizes,
            'index_sizes': index_sizes
        }
    
    def _get_table_columns(self, table_name: str) -> List[str]:
        """获取表的列名"""
        cursor = self.conn.cursor()
        cursor.execute(f"PRAGMA table_info({table_name})")
        return [row[1] for row in cursor.fetchall()]
    
    def test_index_effectiveness(self) -> Dict[str, Any]:
        """测试索引效果"""
        logger.info("Testing index effectiveness...")
        
        # 测试有索引vs无索引的查询
        test_queries = [
            ("indexed_name_lookup", "SELECT * FROM hexagrams WHERE name = '乾'"),
            ("indexed_tier_lookup", "SELECT * FROM hexagrams WHERE data_tier = 1"),
            ("indexed_quality_range", "SELECT * FROM interpretations WHERE quality_score >= 0.8"),
        ]
        
        results = {}
        for test_name, query in test_queries:
            # 获取查询执行计划
            cursor = self.conn.cursor()
            cursor.execute(f"EXPLAIN QUERY PLAN {query}")
            plan = cursor.fetchall()
            
            # 执行查询测试性能
            exec_time, _ = self.time_query(query)
            
            results[test_name] = {
                'execution_time_ms': exec_time,
                'query_plan': [dict(row) for row in plan],
                'uses_index': any('USING INDEX' in str(step) for step in plan)
            }
        
        return results
    
    def benchmark_bulk_operations(self) -> Dict[str, float]:
        """基准测试批量操作"""
        logger.info("Testing bulk operations...")
        
        # 测试批量插入
        test_data = [
            (f'测试卦{i}', f'测试符号{i}', f'测试卦辞{i}', f'测试象辞{i}', 3, 0.5) 
            for i in range(100)
        ]
        
        # 单条插入测试
        start_time = time.perf_counter()
        cursor = self.conn.cursor()
        for data in test_data[:10]:  # 只测试10条，避免影响数据
            cursor.execute("""
                INSERT INTO hexagrams (name, symbol, judgment, image, data_tier, quality_score)
                VALUES (?, ?, ?, ?, ?, ?)
            """, data)
        self.conn.commit()
        single_insert_time = (time.perf_counter() - start_time) * 1000
        
        # 批量插入测试
        start_time = time.perf_counter()
        cursor.executemany("""
            INSERT INTO hexagrams (name, symbol, judgment, image, data_tier, quality_score)
            VALUES (?, ?, ?, ?, ?, ?)
        """, test_data[10:20])  # 另外10条
        self.conn.commit()
        batch_insert_time = (time.perf_counter() - start_time) * 1000
        
        # 清理测试数据
        cursor.execute("DELETE FROM hexagrams WHERE name LIKE '测试卦%'")
        self.conn.commit()
        
        return {
            'single_insert_10_records_ms': single_insert_time,
            'batch_insert_10_records_ms': batch_insert_time,
            'batch_efficiency_ratio': single_insert_time / max(batch_insert_time, 0.001)
        }
    
    def run_full_benchmark(self) -> Dict[str, Any]:
        """运行完整基准测试"""
        logger.info("=== Starting Full Database Benchmark ===")
        
        self.connect()
        
        try:
            # 运行所有测试
            self.results = {
                'basic_queries': self.test_basic_queries(),
                'fts_queries': self.test_fts_queries(),
                'complex_queries': self.test_complex_queries(),
                'database_size': self.analyze_database_size(),
                'index_effectiveness': self.test_index_effectiveness(),
                'bulk_operations': self.benchmark_bulk_operations(),
                'timestamp': time.time()
            }
            
            # 计算汇总统计
            all_times = []
            for category in ['basic_queries', 'fts_queries', 'complex_queries']:
                if category in self.results:
                    all_times.extend([t for t in self.results[category].values() if t > 0])
            
            if all_times:
                self.results['summary'] = {
                    'total_queries_tested': len(all_times),
                    'avg_execution_time_ms': sum(all_times) / len(all_times),
                    'min_execution_time_ms': min(all_times),
                    'max_execution_time_ms': max(all_times),
                    'queries_under_10ms': sum(1 for t in all_times if t < 10),
                    'queries_under_50ms': sum(1 for t in all_times if t < 50),
                    'queries_under_100ms': sum(1 for t in all_times if t < 100)
                }
        
        finally:
            self.close()
        
        return self.results
    
    def save_results(self, output_file: str):
        """保存测试结果到JSON文件"""
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)
        logger.info(f"Benchmark results saved to {output_file}")
    
    def print_summary(self):
        """打印测试总结"""
        if 'summary' not in self.results:
            logger.warning("No summary available")
            return
        
        summary = self.results['summary']
        size_info = self.results.get('database_size', {})
        
        print("\n" + "="*60)
        print("           DATABASE PERFORMANCE BENCHMARK SUMMARY")
        print("="*60)
        
        print(f"Database Size: {size_info.get('total_size_mb', 'N/A'):.2f} MB")
        print(f"Total Queries Tested: {summary['total_queries_tested']}")
        print(f"Average Execution Time: {summary['avg_execution_time_ms']:.2f} ms")
        print(f"Fastest Query: {summary['min_execution_time_ms']:.2f} ms")
        print(f"Slowest Query: {summary['max_execution_time_ms']:.2f} ms")
        
        print(f"\nPerformance Distribution:")
        print(f"  < 10ms:  {summary['queries_under_10ms']:2d} queries ({summary['queries_under_10ms']/summary['total_queries_tested']*100:.1f}%)")
        print(f"  < 50ms:  {summary['queries_under_50ms']:2d} queries ({summary['queries_under_50ms']/summary['total_queries_tested']*100:.1f}%)")
        print(f"  < 100ms: {summary['queries_under_100ms']:2d} queries ({summary['queries_under_100ms']/summary['total_queries_tested']*100:.1f}%)")
        
        # 表大小信息
        if 'table_sizes' in size_info:
            print(f"\nTable Statistics:")
            for table, info in size_info['table_sizes'].items():
                total = info.get('total_rows', 0)
                core = info.get('core_rows', 0)
                print(f"  {table:20s}: {total:6d} total, {core:6d} core")
        
        # 性能建议
        avg_time = summary['avg_execution_time_ms']
        if avg_time < 10:
            status = "EXCELLENT"
        elif avg_time < 50:
            status = "GOOD"
        elif avg_time < 100:
            status = "ACCEPTABLE"
        else:
            status = "NEEDS OPTIMIZATION"
        
        print(f"\nOverall Performance: {status}")
        print("="*60)

def main():
    """主函数"""
    if len(sys.argv) != 2:
        print("Usage: python benchmark.py <database_path>")
        sys.exit(1)
    
    db_path = sys.argv[1]
    
    if not Path(db_path).exists():
        logger.error(f"Database file not found: {db_path}")
        sys.exit(1)
    
    # 运行基准测试
    benchmark = DatabaseBenchmark(db_path)
    results = benchmark.run_full_benchmark()
    
    # 输出结果
    benchmark.print_summary()
    
    # 保存详细结果
    output_file = f"benchmark_results_{int(time.time())}.json"
    benchmark.save_results(output_file)
    
    logger.info("Benchmark completed successfully!")

if __name__ == "__main__":
    main()