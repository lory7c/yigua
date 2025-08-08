#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库查询优化器
自动分析和优化数据库查询性能，创建索引，优化FTS搜索
目标：所有查询 < 10ms，FTS搜索 < 15ms
"""

import sqlite3
import time
import logging
import json
import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
import statistics
from performance_optimizer import PerformanceOptimizer


@dataclass
class QueryAnalysis:
    """查询分析结果"""
    query: str
    query_type: str
    execution_time_ms: float
    rows_examined: int
    rows_returned: int
    uses_index: bool
    index_names: List[str]
    bottlenecks: List[str]
    recommendations: List[str]
    complexity_score: float


@dataclass  
class IndexRecommendation:
    """索引推荐"""
    table_name: str
    column_names: List[str]
    index_type: str  # 'btree', 'fts', 'covering'
    estimated_improvement: float
    priority: int  # 1-10, 10 is highest
    reason: str
    size_estimate_mb: float


class QueryOptimizer:
    """查询优化器"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
        
        # 初始化性能优化器
        self.perf_optimizer = PerformanceOptimizer(db_path, enable_monitoring=True)
        
        # 查询分析结果
        self.analyzed_queries = []
        self.slow_queries = []
        self.index_recommendations = []
        
    def analyze_database_schema(self) -> Dict[str, Any]:
        """分析数据库模式"""
        self.logger.info("分析数据库模式...")
        
        schema_info = {
            'tables': {},
            'indexes': {},
            'fts_tables': {},
            'statistics': {}
        }
        
        with self.perf_optimizer.connection_pool.get_connection() as conn:
            # 获取表信息
            tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
            
            for table_row in tables:
                table_name = table_row[0]
                
                # 跳过系统表
                if table_name.startswith('sqlite_'):
                    continue
                
                # 获取表结构
                columns = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
                
                # 获取表统计
                count_result = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()
                row_count = count_result[0] if count_result else 0
                
                schema_info['tables'][table_name] = {
                    'columns': [{'name': col[1], 'type': col[2], 'notnull': col[3], 'pk': col[5]} for col in columns],
                    'row_count': row_count
                }
            
            # 获取索引信息
            indexes = conn.execute("SELECT name, tbl_name, sql FROM sqlite_master WHERE type='index'").fetchall()
            
            for index_row in indexes:
                index_name, table_name, sql = index_row
                
                if not index_name.startswith('sqlite_autoindex'):
                    schema_info['indexes'][index_name] = {
                        'table': table_name,
                        'sql': sql
                    }
            
            # 识别FTS表
            fts_tables = conn.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND sql LIKE '%FTS%'
            """).fetchall()
            
            for fts_row in fts_tables:
                fts_name = fts_row[0]
                schema_info['fts_tables'][fts_name] = {
                    'type': 'fts5' if 'fts5' in fts_name else 'fts4'
                }
        
        return schema_info
    
    def analyze_query_performance(self, query: str, params: tuple = None, 
                                 iterations: int = 10) -> QueryAnalysis:
        """分析单个查询的性能"""
        
        if params is None:
            params = ()
        
        # 执行多次获取平均时间
        execution_times = []
        
        with self.perf_optimizer.connection_pool.get_connection() as conn:
            
            # 获取查询计划
            explain_query = f"EXPLAIN QUERY PLAN {query}"
            query_plan = conn.execute(explain_query, params).fetchall()
            
            # 分析查询计划
            uses_index = False
            index_names = []
            bottlenecks = []
            
            for step in query_plan:
                step_detail = str(step).upper()
                
                if 'USING INDEX' in step_detail:
                    uses_index = True
                    # 提取索引名
                    index_match = re.search(r'USING INDEX (\w+)', step_detail)
                    if index_match:
                        index_names.append(index_match.group(1))
                
                if 'SCAN TABLE' in step_detail:
                    bottlenecks.append("全表扫描，建议创建索引")
                
                if 'TEMP B-TREE' in step_detail:
                    bottlenecks.append("使用临时表，可能由于复杂的GROUP BY或ORDER BY造成")
                
                if 'SORT' in step_detail:
                    bottlenecks.append("排序操作可能消耗大量资源")
            
            # 执行性能测试
            for _ in range(iterations):
                start_time = time.time()
                cursor = conn.execute(query, params)
                results = cursor.fetchall()
                execution_time = (time.time() - start_time) * 1000
                execution_times.append(execution_time)
            
            rows_returned = len(results)
        
        # 计算统计指标
        avg_time = statistics.mean(execution_times)
        
        # 估算检查的行数（基于查询计划）
        rows_examined = self._estimate_rows_examined(query_plan)
        
        # 计算复杂度评分
        complexity_score = self._calculate_complexity_score(query, query_plan)
        
        # 生成优化建议
        recommendations = self._generate_query_recommendations(query, query_plan, avg_time)
        
        # 确定查询类型
        query_type = self._classify_query(query)
        
        analysis = QueryAnalysis(
            query=query,
            query_type=query_type,
            execution_time_ms=avg_time,
            rows_examined=rows_examined,
            rows_returned=rows_returned,
            uses_index=uses_index,
            index_names=index_names,
            bottlenecks=bottlenecks,
            recommendations=recommendations,
            complexity_score=complexity_score
        )
        
        self.analyzed_queries.append(analysis)
        
        if avg_time > 10:  # 慢查询阈值
            self.slow_queries.append(analysis)
        
        return analysis
    
    def _estimate_rows_examined(self, query_plan: List) -> int:
        """估算检查的行数"""
        rows_examined = 0
        
        for step in query_plan:
            step_detail = str(step).upper()
            
            if 'SCAN TABLE' in step_detail:
                # 全表扫描，估算为表的行数
                rows_examined += 10000  # 默认估算值
            elif 'SEARCH TABLE' in step_detail and 'USING INDEX' in step_detail:
                # 索引搜索，估算检查较少行数
                rows_examined += 100
            elif 'SCAN SUBQUERY' in step_detail:
                rows_examined += 1000
        
        return max(rows_examined, 1)
    
    def _calculate_complexity_score(self, query: str, query_plan: List) -> float:
        """计算查询复杂度评分 (0-10)"""
        score = 0
        
        query_upper = query.upper()
        
        # 基础复杂度
        if 'SELECT' in query_upper:
            score += 1
        
        # JOIN 复杂度
        join_count = query_upper.count('JOIN')
        score += join_count * 1.5
        
        # 子查询复杂度
        subquery_count = query_upper.count('SELECT') - 1  # 减去主查询
        score += subquery_count * 2
        
        # WHERE 条件复杂度
        if 'WHERE' in query_upper:
            score += 0.5
            # 复杂条件
            if 'LIKE' in query_upper:
                score += 1
            if 'IN (' in query_upper:
                score += 0.5
        
        # GROUP BY / ORDER BY
        if 'GROUP BY' in query_upper:
            score += 1
        if 'ORDER BY' in query_upper:
            score += 0.5
        
        # 查询计划复杂度
        for step in query_plan:
            step_detail = str(step).upper()
            if 'TEMP B-TREE' in step_detail:
                score += 1.5
            if 'SCAN TABLE' in step_detail:
                score += 2
        
        return min(10, score)
    
    def _classify_query(self, query: str) -> str:
        """分类查询类型"""
        query_upper = query.upper().strip()
        
        if query_upper.startswith('SELECT'):
            if 'JOIN' in query_upper:
                return 'join_query'
            elif 'GROUP BY' in query_upper or 'COUNT(' in query_upper:
                return 'aggregation'
            elif 'LIKE' in query_upper or 'MATCH' in query_upper:
                return 'search_query'
            elif 'ORDER BY' in query_upper:
                return 'sorted_query'
            else:
                return 'simple_select'
        elif query_upper.startswith('INSERT'):
            return 'insert'
        elif query_upper.startswith('UPDATE'):
            return 'update'
        elif query_upper.startswith('DELETE'):
            return 'delete'
        else:
            return 'other'
    
    def _generate_query_recommendations(self, query: str, query_plan: List, 
                                      execution_time: float) -> List[str]:
        """生成查询优化建议"""
        recommendations = []
        
        query_upper = query.upper()
        
        # 基于执行时间的建议
        if execution_time > 50:
            recommendations.append("查询执行时间过长，需要重点优化")
        elif execution_time > 10:
            recommendations.append("查询执行时间较长，建议优化")
        
        # 基于查询计划的建议
        has_table_scan = False
        has_temp_btree = False
        
        for step in query_plan:
            step_detail = str(step).upper()
            
            if 'SCAN TABLE' in step_detail:
                has_table_scan = True
                table_match = re.search(r'SCAN TABLE (\w+)', step_detail)
                if table_match:
                    table_name = table_match.group(1)
                    recommendations.append(f"在表 {table_name} 上创建索引以避免全表扫描")
            
            if 'TEMP B-TREE' in step_detail:
                has_temp_btree = True
        
        # 特定模式的建议
        if 'LIKE' in query_upper and '%' in query:
            if not query.startswith('%'):
                recommendations.append("对于前缀搜索，考虑创建前缀索引")
            else:
                recommendations.append("对于全文搜索，考虑使用FTS索引")
        
        if 'ORDER BY' in query_upper and has_temp_btree:
            recommendations.append("为ORDER BY字段创建索引以避免排序开销")
        
        if 'GROUP BY' in query_upper and has_temp_btree:
            recommendations.append("为GROUP BY字段创建索引以提高分组性能")
        
        if 'JOIN' in query_upper:
            recommendations.append("确保JOIN条件字段都有适当的索引")
        
        return recommendations
    
    def generate_index_recommendations(self, schema_info: Dict[str, Any]) -> List[IndexRecommendation]:
        """生成索引推荐"""
        self.logger.info("生成索引推荐...")
        
        recommendations = []
        
        # 基于慢查询分析生成索引建议
        for query_analysis in self.slow_queries:
            query = query_analysis.query.upper()
            
            # 提取表名和条件字段
            table_columns = self._extract_query_columns(query)
            
            for table_name, columns in table_columns.items():
                if table_name in schema_info['tables']:
                    
                    # WHERE条件索引
                    where_columns = columns.get('where', [])
                    if where_columns:
                        rec = IndexRecommendation(
                            table_name=table_name,
                            column_names=where_columns,
                            index_type='btree',
                            estimated_improvement=0.6,  # 60%改进估算
                            priority=8,
                            reason=f"优化WHERE条件查询: {', '.join(where_columns)}",
                            size_estimate_mb=self._estimate_index_size(schema_info['tables'][table_name], where_columns)
                        )
                        recommendations.append(rec)
                    
                    # ORDER BY索引
                    order_columns = columns.get('order_by', [])
                    if order_columns:
                        rec = IndexRecommendation(
                            table_name=table_name,
                            column_names=order_columns,
                            index_type='btree',
                            estimated_improvement=0.4,
                            priority=6,
                            reason=f"优化ORDER BY排序: {', '.join(order_columns)}",
                            size_estimate_mb=self._estimate_index_size(schema_info['tables'][table_name], order_columns)
                        )
                        recommendations.append(rec)
                    
                    # 复合索引建议
                    if len(where_columns) > 1:
                        rec = IndexRecommendation(
                            table_name=table_name,
                            column_names=where_columns,
                            index_type='btree',
                            estimated_improvement=0.7,
                            priority=9,
                            reason=f"复合索引优化多条件查询",
                            size_estimate_mb=self._estimate_index_size(schema_info['tables'][table_name], where_columns)
                        )
                        recommendations.append(rec)
        
        # 基于表大小和访问模式的索引建议
        for table_name, table_info in schema_info['tables'].items():
            if table_info['row_count'] > 10000:  # 大表
                
                # 为主要字段推荐索引
                important_columns = []
                for col in table_info['columns']:
                    col_name = col['name'].lower()
                    if any(keyword in col_name for keyword in ['id', 'name', 'category', 'type', 'status']):
                        important_columns.append(col['name'])
                
                if important_columns:
                    for col_name in important_columns:
                        rec = IndexRecommendation(
                            table_name=table_name,
                            column_names=[col_name],
                            index_type='btree',
                            estimated_improvement=0.5,
                            priority=7,
                            reason=f"大表 {table_name} 的重要字段索引",
                            size_estimate_mb=self._estimate_index_size(table_info, [col_name])
                        )
                        recommendations.append(rec)
        
        # 去重和排序
        self.index_recommendations = self._deduplicate_recommendations(recommendations)
        
        return self.index_recommendations
    
    def _extract_query_columns(self, query: str) -> Dict[str, Dict[str, List[str]]]:
        """从查询中提取表和字段信息"""
        result = {}
        
        # 简化的SQL解析（实际应用中建议使用专业的SQL解析器）
        
        # 提取表名
        from_match = re.search(r'FROM\s+(\w+)', query)
        if not from_match:
            return result
        
        table_name = from_match.group(1).lower()
        result[table_name] = {'where': [], 'order_by': [], 'group_by': []}
        
        # 提取WHERE条件字段
        where_pattern = r'WHERE.*?(?=ORDER BY|GROUP BY|$)'
        where_match = re.search(where_pattern, query, re.DOTALL)
        if where_match:
            where_clause = where_match.group(0)
            
            # 提取字段名（简化版）
            column_pattern = r'(\w+)\s*[=<>!]'
            columns = re.findall(column_pattern, where_clause)
            result[table_name]['where'] = [col.lower() for col in columns if col.upper() not in ['AND', 'OR', 'NOT']]
        
        # 提取ORDER BY字段
        order_match = re.search(r'ORDER BY\s+([\w\s,]+)', query)
        if order_match:
            order_fields = [field.strip().lower() for field in order_match.group(1).split(',')]
            result[table_name]['order_by'] = [field.split()[0] for field in order_fields]  # 去除ASC/DESC
        
        # 提取GROUP BY字段
        group_match = re.search(r'GROUP BY\s+([\w\s,]+)', query)
        if group_match:
            group_fields = [field.strip().lower() for field in group_match.group(1).split(',')]
            result[table_name]['group_by'] = group_fields
        
        return result
    
    def _estimate_index_size(self, table_info: Dict[str, Any], columns: List[str]) -> float:
        """估算索引大小"""
        row_count = table_info['row_count']
        
        # 简化的索引大小估算
        # 假设每个索引项平均20字节，加上B树开销
        estimated_size_bytes = row_count * len(columns) * 25
        
        return estimated_size_bytes / 1024 / 1024  # 转换为MB
    
    def _deduplicate_recommendations(self, recommendations: List[IndexRecommendation]) -> List[IndexRecommendation]:
        """去重索引推荐"""
        unique_recommendations = {}
        
        for rec in recommendations:
            # 使用表名和字段组合作为键
            key = f"{rec.table_name}:{':'.join(sorted(rec.column_names))}"
            
            if key not in unique_recommendations or rec.priority > unique_recommendations[key].priority:
                unique_recommendations[key] = rec
        
        # 按优先级排序
        return sorted(unique_recommendations.values(), key=lambda x: x.priority, reverse=True)
    
    def create_recommended_indexes(self, recommendations: List[IndexRecommendation] = None, 
                                 apply: bool = False) -> Dict[str, Any]:
        """创建推荐的索引"""
        
        if recommendations is None:
            recommendations = self.index_recommendations
        
        results = {
            'created_indexes': [],
            'failed_indexes': [],
            'total_time_seconds': 0
        }
        
        start_time = time.time()
        
        with self.perf_optimizer.connection_pool.get_connection() as conn:
            
            for rec in recommendations:
                
                # 生成索引名
                index_name = f"idx_{rec.table_name}_{'_'.join(rec.column_names)}"
                
                # 生成CREATE INDEX语句
                if rec.index_type == 'btree':
                    columns_sql = ', '.join(rec.column_names)
                    create_sql = f"CREATE INDEX IF NOT EXISTS {index_name} ON {rec.table_name} ({columns_sql})"
                elif rec.index_type == 'fts':
                    # FTS索引需要特殊处理
                    continue  # 暂时跳过FTS索引创建
                else:
                    continue
                
                try:
                    if apply:
                        self.logger.info(f"创建索引: {index_name}")
                        conn.execute(create_sql)
                        conn.commit()
                        results['created_indexes'].append({
                            'name': index_name,
                            'table': rec.table_name,
                            'columns': rec.column_names,
                            'sql': create_sql
                        })
                    else:
                        self.logger.info(f"建议创建索引: {create_sql}")
                        results['created_indexes'].append({
                            'name': index_name,
                            'table': rec.table_name,
                            'columns': rec.column_names,
                            'sql': create_sql,
                            'dry_run': True
                        })
                
                except Exception as e:
                    self.logger.error(f"创建索引失败 {index_name}: {e}")
                    results['failed_indexes'].append({
                        'name': index_name,
                        'error': str(e),
                        'sql': create_sql
                    })
        
        results['total_time_seconds'] = time.time() - start_time
        
        return results
    
    def optimize_fts_search(self) -> Dict[str, Any]:
        """优化全文搜索"""
        self.logger.info("优化全文搜索...")
        
        results = {
            'fts_tables_optimized': [],
            'new_fts_indexes': [],
            'optimization_time_seconds': 0
        }
        
        start_time = time.time()
        
        with self.perf_optimizer.connection_pool.get_connection() as conn:
            
            # 查找现有的FTS表
            fts_tables = conn.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND (name LIKE '%fts%' OR sql LIKE '%FTS%')
            """).fetchall()
            
            for table_row in fts_tables:
                table_name = table_row[0]
                
                try:
                    # 优化FTS表
                    self.logger.info(f"优化FTS表: {table_name}")
                    
                    # 重建FTS索引
                    conn.execute(f"INSERT INTO {table_name}({table_name}) VALUES('rebuild')")
                    
                    # 优化FTS表
                    conn.execute(f"INSERT INTO {table_name}({table_name}) VALUES('optimize')")
                    
                    results['fts_tables_optimized'].append(table_name)
                    
                except Exception as e:
                    self.logger.error(f"优化FTS表失败 {table_name}: {e}")
            
            # 分析可能需要FTS的文本字段
            tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
            
            for table_row in tables:
                table_name = table_row[0]
                
                if table_name.startswith('sqlite_') or 'fts' in table_name.lower():
                    continue
                
                # 获取表结构
                columns = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
                
                text_columns = []
                for col in columns:
                    col_name, col_type = col[1], col[2]
                    if col_type.upper() in ['TEXT', 'VARCHAR', 'CHAR'] and 'content' in col_name.lower():
                        text_columns.append(col_name)
                
                # 如果有文本内容字段，建议创建FTS索引
                if text_columns:
                    fts_table_name = f"fts_{table_name}"
                    
                    # 检查是否已存在
                    existing = conn.execute("""
                        SELECT name FROM sqlite_master 
                        WHERE type='table' AND name=?
                    """, (fts_table_name,)).fetchone()
                    
                    if not existing:
                        results['new_fts_indexes'].append({
                            'original_table': table_name,
                            'fts_table': fts_table_name,
                            'columns': text_columns,
                            'recommended': True
                        })
        
        results['optimization_time_seconds'] = time.time() - start_time
        
        return results
    
    def generate_optimization_report(self) -> Dict[str, Any]:
        """生成优化报告"""
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'total_queries_analyzed': len(self.analyzed_queries),
                'slow_queries_found': len(self.slow_queries),
                'index_recommendations': len(self.index_recommendations)
            },
            'query_analysis': [asdict(qa) for qa in self.analyzed_queries],
            'slow_queries': [asdict(sq) for sq in self.slow_queries],
            'index_recommendations': [asdict(ir) for ir in self.index_recommendations],
            'performance_insights': self._generate_performance_insights()
        }
        
        return report
    
    def _generate_performance_insights(self) -> List[str]:
        """生成性能洞察"""
        insights = []
        
        if not self.analyzed_queries:
            return ["没有分析的查询数据"]
        
        # 平均查询时间
        avg_time = statistics.mean([qa.execution_time_ms for qa in self.analyzed_queries])
        if avg_time > 10:
            insights.append(f"平均查询时间 {avg_time:.1f}ms，超过10ms目标，需要优化")
        else:
            insights.append(f"平均查询时间 {avg_time:.1f}ms，性能良好")
        
        # 慢查询比例
        slow_query_rate = len(self.slow_queries) / len(self.analyzed_queries)
        if slow_query_rate > 0.2:
            insights.append(f"慢查询比例 {slow_query_rate:.1%}，建议重点优化")
        
        # 索引使用情况
        queries_with_index = [qa for qa in self.analyzed_queries if qa.uses_index]
        index_usage_rate = len(queries_with_index) / len(self.analyzed_queries)
        
        if index_usage_rate < 0.5:
            insights.append(f"索引使用率 {index_usage_rate:.1%}，建议创建更多索引")
        
        # 常见瓶颈
        all_bottlenecks = []
        for qa in self.analyzed_queries:
            all_bottlenecks.extend(qa.bottlenecks)
        
        if all_bottlenecks:
            from collections import Counter
            common_bottlenecks = Counter(all_bottlenecks).most_common(3)
            for bottleneck, count in common_bottlenecks:
                insights.append(f"常见瓶颈: {bottleneck} (出现 {count} 次)")
        
        return insights
    
    def close(self):
        """关闭优化器"""
        if self.perf_optimizer:
            self.perf_optimizer.close()


# 使用示例
def run_query_optimization(db_path: str, test_queries: List[str] = None) -> Dict[str, Any]:
    """运行查询优化流程"""
    
    print("🔍 开始数据库查询优化分析")
    
    optimizer = QueryOptimizer(db_path)
    
    try:
        # 1. 分析数据库模式
        print("1. 分析数据库模式...")
        schema_info = optimizer.analyze_database_schema()
        
        print(f"   发现 {len(schema_info['tables'])} 个表")
        print(f"   发现 {len(schema_info['indexes'])} 个索引")
        print(f"   发现 {len(schema_info['fts_tables'])} 个FTS表")
        
        # 2. 分析测试查询
        if test_queries is None:
            # 默认测试查询
            test_queries = [
                "SELECT * FROM yixue_data WHERE category = 'hexagram'",
                "SELECT * FROM yixue_data WHERE content LIKE '%易经%'",
                "SELECT COUNT(*) FROM yixue_data GROUP BY category",
                "SELECT * FROM yixue_data ORDER BY created_at DESC LIMIT 10",
                "SELECT * FROM yixue_data WHERE category = 'hexagram' AND confidence > 0.8"
            ]
        
        print(f"\n2. 分析 {len(test_queries)} 个测试查询...")
        for i, query in enumerate(test_queries, 1):
            try:
                analysis = optimizer.analyze_query_performance(query)
                print(f"   查询 {i}: {analysis.execution_time_ms:.2f}ms ({'✓' if analysis.execution_time_ms < 10 else '⚠️'})")
                
                if analysis.bottlenecks:
                    for bottleneck in analysis.bottlenecks[:2]:  # 显示前2个瓶颈
                        print(f"     瓶颈: {bottleneck}")
                        
            except Exception as e:
                print(f"   查询 {i}: 分析失败 - {e}")
        
        # 3. 生成索引推荐
        print(f"\n3. 生成索引优化建议...")
        recommendations = optimizer.generate_index_recommendations(schema_info)
        
        print(f"   生成 {len(recommendations)} 个索引建议")
        for i, rec in enumerate(recommendations[:5], 1):  # 显示前5个
            print(f"   建议 {i}: {rec.table_name}.{','.join(rec.column_names)} "
                  f"(优先级: {rec.priority}, 预期改进: {rec.estimated_improvement:.1%})")
        
        # 4. 优化FTS搜索
        print(f"\n4. 优化全文搜索...")
        fts_results = optimizer.optimize_fts_search()
        
        if fts_results['fts_tables_optimized']:
            print(f"   优化了 {len(fts_results['fts_tables_optimized'])} 个FTS表")
        
        if fts_results['new_fts_indexes']:
            print(f"   建议创建 {len(fts_results['new_fts_indexes'])} 个新FTS索引")
        
        # 5. 创建推荐索引（试运行）
        print(f"\n5. 生成索引创建脚本...")
        index_results = optimizer.create_recommended_indexes(apply=False)
        
        print(f"   准备创建 {len(index_results['created_indexes'])} 个索引")
        
        # 6. 生成报告
        print(f"\n6. 生成优化报告...")
        report = optimizer.generate_optimization_report()
        
        # 保存报告
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = f"query_optimization_report_{timestamp}.json"
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"   报告已保存: {report_file}")
        
        # 显示总结
        print(f"\n📊 优化总结:")
        print(f"   分析查询数: {report['summary']['total_queries_analyzed']}")
        print(f"   慢查询数: {report['summary']['slow_queries_found']}")
        print(f"   索引建议数: {report['summary']['index_recommendations']}")
        
        for insight in report['performance_insights'][:3]:
            print(f"   💡 {insight}")
        
        return report
        
    finally:
        optimizer.close()


if __name__ == "__main__":
    # 测试查询优化
    import sys
    
    if len(sys.argv) > 1:
        db_path = sys.argv[1]
    else:
        db_path = "database/yijing_knowledge.db"
    
    if Path(db_path).exists():
        run_query_optimization(db_path)
    else:
        print(f"数据库文件不存在: {db_path}")
        print("使用测试数据库进行演示...")
        
        # 创建测试数据库
        test_db = "test_optimization.db"
        conn = sqlite3.connect(test_db)
        
        # 创建测试表和数据
        conn.execute("""
            CREATE TABLE yixue_data (
                id INTEGER PRIMARY KEY,
                category TEXT,
                content TEXT,
                confidence REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 插入测试数据
        for i in range(1000):
            conn.execute("""
                INSERT INTO yixue_data (category, content, confidence)
                VALUES (?, ?, ?)
            """, (
                f"category_{i % 10}",
                f"测试内容 {i} 包含易经知识",
                0.5 + (i % 50) / 100
            ))
        
        conn.commit()
        conn.close()
        
        print(f"创建测试数据库: {test_db}")
        run_query_optimization(test_db)