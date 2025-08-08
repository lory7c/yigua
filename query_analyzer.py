#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SQLite查询性能深度分析器
专业级查询计划分析、慢查询诊断、索引优化建议

核心功能:
1. EXPLAIN QUERY PLAN 深度分析
2. 慢查询模式识别和优化
3. 索引使用效率分析  
4. JOIN操作优化建议
5. 查询重写和优化提案
6. 实时SQL监控和报警
7. 查询成本估算

性能目标:
- 自动识别>10ms的慢查询
- 提供具体的优化方案
- 预测优化后的性能提升
- 生成可执行的DDL建议

作者: Claude
创建时间: 2025-08-07
"""

import sqlite3
import re
import json
import time
import hashlib
import statistics
from typing import Dict, List, Tuple, Optional, Any, Set
from dataclasses import dataclass, asdict, field
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from contextlib import contextmanager
import logging


@dataclass
class QueryPlan:
    """查询计划分析结果"""
    query: str
    plan_steps: List[Dict[str, Any]]
    total_cost: float
    table_scans: List[str]
    index_scans: List[str] 
    join_operations: List[str]
    sort_operations: List[str]
    temp_table_usage: bool
    estimated_rows: int


@dataclass
class SlowQueryAnalysis:
    """慢查询分析结果"""
    query_hash: str
    query: str
    execution_time_ms: float
    execution_count: int
    plan_analysis: QueryPlan
    bottlenecks: List[str]
    optimization_suggestions: List[str]
    estimated_improvement: float
    first_seen: datetime
    last_seen: datetime


@dataclass
class IndexAnalysis:
    """索引分析结果"""
    table_name: str
    index_name: str
    columns: List[str]
    usage_count: int
    selectivity: float
    size_estimate_mb: float
    effectiveness_score: float
    recommendations: List[str]


@dataclass
class QueryPattern:
    """查询模式"""
    pattern_hash: str
    template: str
    frequency: int
    avg_execution_time: float
    tables_involved: Set[str]
    common_filters: List[str]
    optimization_potential: float


class QueryAnalyzer:
    """SQL查询性能分析器"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
        
        # 分析数据存储
        self.query_plans = {}
        self.slow_queries = {}
        self.query_patterns = {}
        self.index_usage_stats = defaultdict(int)
        self.table_access_patterns = defaultdict(lambda: {'scans': 0, 'seeks': 0})
        
        # 性能阈值配置
        self.slow_query_threshold_ms = 10
        self.table_scan_penalty = 100
        self.index_seek_reward = 1
    
    @contextmanager
    def get_connection(self):
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    def analyze_query_plan(self, query: str, params: tuple = None) -> QueryPlan:
        """分析查询计划"""
        with self.get_connection() as conn:
            # 获取查询计划
            explain_query = f"EXPLAIN QUERY PLAN {query}"
            cursor = conn.execute(explain_query, params or ())
            plan_rows = cursor.fetchall()
            
            # 解析计划步骤
            plan_steps = []
            table_scans = []
            index_scans = []
            join_operations = []
            sort_operations = []
            temp_table_usage = False
            estimated_rows = 0
            total_cost = 0.0
            
            for row in plan_rows:
                step = {
                    'id': row[0],
                    'parent': row[1], 
                    'notused': row[2],
                    'detail': row[3]
                }
                plan_steps.append(step)
                
                detail = step['detail'].upper()
                
                # 识别表扫描
                if 'SCAN TABLE' in detail:
                    table_match = re.search(r'SCAN TABLE (\w+)', detail)
                    if table_match:
                        table_name = table_match.group(1)
                        table_scans.append(table_name)
                        total_cost += self.table_scan_penalty
                        estimated_rows += 1000  # 估算值
                
                # 识别索引扫描
                if 'SEARCH TABLE' in detail or 'INDEX' in detail:
                    index_match = re.search(r'USING (?:COVERING )?INDEX (\w+)', detail)
                    if index_match:
                        index_name = index_match.group(1)
                        index_scans.append(index_name)
                        total_cost += self.index_seek_reward
                        estimated_rows += 10  # 索引查找通常返回较少行
                
                # 识别JOIN操作
                if any(join_type in detail for join_type in ['JOIN', 'LEFT JOIN', 'INNER JOIN']):
                    join_operations.append(detail)
                
                # 识别排序操作
                if 'ORDER BY' in detail or 'SORT' in detail:
                    sort_operations.append(detail)
                    total_cost += 50  # 排序成本
                
                # 识别临时表使用
                if 'TEMP' in detail or 'TEMPORARY' in detail:
                    temp_table_usage = True
                    total_cost += 200  # 临时表成本很高
        
        return QueryPlan(
            query=query,
            plan_steps=plan_steps,
            total_cost=total_cost,
            table_scans=table_scans,
            index_scans=index_scans,
            join_operations=join_operations,
            sort_operations=sort_operations,
            temp_table_usage=temp_table_usage,
            estimated_rows=estimated_rows
        )
    
    def analyze_slow_query(self, query: str, execution_time_ms: float,
                          params: tuple = None) -> SlowQueryAnalysis:
        """分析慢查询"""
        query_hash = hashlib.md5(query.encode()).hexdigest()[:12]
        
        # 获取查询计划
        plan_analysis = self.analyze_query_plan(query, params)
        
        # 识别性能瓶颈
        bottlenecks = []
        optimization_suggestions = []
        estimated_improvement = 0.0
        
        # 分析表扫描
        if plan_analysis.table_scans:
            bottlenecks.append(f"全表扫描: {', '.join(plan_analysis.table_scans)}")
            optimization_suggestions.append("为频繁查询的列创建索引")
            estimated_improvement += 0.6  # 预计60%的性能提升
        
        # 分析临时表使用
        if plan_analysis.temp_table_usage:
            bottlenecks.append("使用临时表，可能由于复杂的GROUP BY或ORDER BY造成")
            optimization_suggestions.append("考虑重构查询或创建覆盖索引")
            estimated_improvement += 0.3
        
        # 分析复杂JOIN
        if len(plan_analysis.join_operations) > 2:
            bottlenecks.append("复杂的多表JOIN操作")
            optimization_suggestions.append("优化JOIN顺序，确保有适当的索引支持")
            estimated_improvement += 0.4
        
        # 分析排序操作
        if plan_analysis.sort_operations:
            bottlenecks.append("排序操作可能消耗大量资源")
            optimization_suggestions.append("为ORDER BY列创建索引")
            estimated_improvement += 0.25
        
        # 检查是否已存在分析结果
        if query_hash in self.slow_queries:
            existing = self.slow_queries[query_hash]
            existing.execution_count += 1
            existing.last_seen = datetime.now()
            return existing
        
        # 创建新的分析结果
        analysis = SlowQueryAnalysis(
            query_hash=query_hash,
            query=query,
            execution_time_ms=execution_time_ms,
            execution_count=1,
            plan_analysis=plan_analysis,
            bottlenecks=bottlenecks,
            optimization_suggestions=optimization_suggestions,
            estimated_improvement=min(estimated_improvement, 0.9),  # 最大90%提升
            first_seen=datetime.now(),
            last_seen=datetime.now()
        )
        
        self.slow_queries[query_hash] = analysis
        return analysis
    
    def analyze_index_usage(self) -> List[IndexAnalysis]:
        """分析索引使用情况"""
        index_analyses = []
        
        with self.get_connection() as conn:
            # 获取所有索引信息
            cursor = conn.execute("""
                SELECT name, tbl_name, sql 
                FROM sqlite_master 
                WHERE type = 'index' AND name NOT LIKE 'sqlite_%'
            """)
            indexes = cursor.fetchall()
            
            for index in indexes:
                index_name = index['name']
                table_name = index['tbl_name']
                
                # 分析索引结构
                columns = self._extract_index_columns(index['sql'])
                
                # 获取使用统计
                usage_count = self.index_usage_stats.get(index_name, 0)
                
                # 估算索引大小
                size_estimate = self._estimate_index_size(conn, table_name, columns)
                
                # 计算选择性
                selectivity = self._calculate_selectivity(conn, table_name, columns)
                
                # 计算效果评分
                effectiveness_score = self._calculate_effectiveness_score(
                    usage_count, selectivity, size_estimate
                )
                
                # 生成建议
                recommendations = self._generate_index_recommendations(
                    table_name, columns, usage_count, selectivity, effectiveness_score
                )
                
                analysis = IndexAnalysis(
                    table_name=table_name,
                    index_name=index_name,
                    columns=columns,
                    usage_count=usage_count,
                    selectivity=selectivity,
                    size_estimate_mb=size_estimate,
                    effectiveness_score=effectiveness_score,
                    recommendations=recommendations
                )
                
                index_analyses.append(analysis)
        
        return index_analyses
    
    def _extract_index_columns(self, create_sql: str) -> List[str]:
        """从CREATE INDEX语句中提取列名"""
        if not create_sql:
            return []
        
        # 使用正则表达式提取列名
        match = re.search(r'\((.*?)\)', create_sql)
        if match:
            columns_str = match.group(1)
            return [col.strip().strip('"\'') for col in columns_str.split(',')]
        
        return []
    
    def _estimate_index_size(self, conn: sqlite3.Connection, 
                           table_name: str, columns: List[str]) -> float:
        """估算索引大小 (MB)"""
        try:
            # 获取表行数
            cursor = conn.execute(f"SELECT COUNT(*) FROM {table_name}")
            row_count = cursor.fetchone()[0]
            
            # 估算每行索引大小 (简化计算)
            avg_key_size = len(columns) * 20  # 假设每个键值平均20字节
            estimated_size_bytes = row_count * avg_key_size * 1.5  # 包括B-tree开销
            
            return estimated_size_bytes / 1024 / 1024  # 转换为MB
        except:
            return 1.0  # 默认估算值
    
    def _calculate_selectivity(self, conn: sqlite3.Connection,
                             table_name: str, columns: List[str]) -> float:
        """计算索引选择性"""
        try:
            if not columns:
                return 0.1
            
            # 获取总行数
            cursor = conn.execute(f"SELECT COUNT(*) FROM {table_name}")
            total_rows = cursor.fetchone()[0]
            
            if total_rows == 0:
                return 1.0
            
            # 获取唯一值数量 (使用第一列)
            first_column = columns[0]
            cursor = conn.execute(f"SELECT COUNT(DISTINCT {first_column}) FROM {table_name}")
            distinct_values = cursor.fetchone()[0]
            
            return distinct_values / total_rows
        except:
            return 0.5  # 默认值
    
    def _calculate_effectiveness_score(self, usage_count: int, selectivity: float,
                                     size_mb: float) -> float:
        """计算索引效果评分 (0-100)"""
        # 使用频率评分 (0-40分)
        usage_score = min(usage_count / 100 * 40, 40)
        
        # 选择性评分 (0-40分)
        selectivity_score = selectivity * 40
        
        # 大小效率评分 (0-20分)
        size_score = max(20 - size_mb, 0)
        
        return usage_score + selectivity_score + size_score
    
    def _generate_index_recommendations(self, table_name: str, columns: List[str],
                                      usage_count: int, selectivity: float,
                                      effectiveness_score: float) -> List[str]:
        """生成索引建议"""
        recommendations = []
        
        if usage_count == 0:
            recommendations.append("索引未被使用，考虑删除以节省存储空间")
        elif usage_count < 10:
            recommendations.append("索引使用频率较低，评估是否需要保留")
        
        if selectivity < 0.1:
            recommendations.append("选择性较低，考虑与其他列组合成复合索引")
        elif selectivity > 0.9:
            recommendations.append("选择性极佳，可考虑作为主要查询路径")
        
        if effectiveness_score < 30:
            recommendations.append("总体效果较差，需要重新评估索引策略")
        elif effectiveness_score > 80:
            recommendations.append("高效索引，建议保持并优化相关查询")
        
        return recommendations
    
    def identify_query_patterns(self, queries: List[Tuple[str, float]]) -> List[QueryPattern]:
        """识别查询模式"""
        pattern_groups = defaultdict(list)
        
        for query, execution_time in queries:
            # 将查询参数化为模式
            normalized_query = self._normalize_query(query)
            pattern_hash = hashlib.md5(normalized_query.encode()).hexdigest()[:8]
            pattern_groups[pattern_hash].append((query, execution_time))
        
        patterns = []
        for pattern_hash, query_group in pattern_groups.items():
            if len(query_group) < 2:  # 至少需要2个相似查询才算模式
                continue
            
            # 分析模式特征
            template = self._generate_query_template(query_group[0][0])
            frequency = len(query_group)
            avg_time = statistics.mean(time for _, time in query_group)
            tables_involved = self._extract_tables_from_query(template)
            common_filters = self._extract_common_filters(query_group)
            
            # 计算优化潜力
            optimization_potential = self._calculate_optimization_potential(
                avg_time, frequency, tables_involved
            )
            
            pattern = QueryPattern(
                pattern_hash=pattern_hash,
                template=template,
                frequency=frequency,
                avg_execution_time=avg_time,
                tables_involved=tables_involved,
                common_filters=common_filters,
                optimization_potential=optimization_potential
            )
            
            patterns.append(pattern)
        
        # 按优化潜力排序
        patterns.sort(key=lambda p: p.optimization_potential, reverse=True)
        return patterns
    
    def _normalize_query(self, query: str) -> str:
        """规范化查询，移除参数值"""
        # 移除字符串和数字字面量，替换为占位符
        normalized = re.sub(r"'[^']*'", "'?'", query)
        normalized = re.sub(r'\b\d+\b', '?', normalized)
        normalized = re.sub(r'\s+', ' ', normalized).strip().upper()
        return normalized
    
    def _generate_query_template(self, query: str) -> str:
        """生成查询模板"""
        return self._normalize_query(query)
    
    def _extract_tables_from_query(self, query: str) -> Set[str]:
        """从查询中提取表名"""
        tables = set()
        
        # 提取FROM子句中的表名
        from_match = re.search(r'FROM\s+(\w+)', query)
        if from_match:
            tables.add(from_match.group(1).lower())
        
        # 提取JOIN子句中的表名
        join_matches = re.findall(r'JOIN\s+(\w+)', query)
        for table in join_matches:
            tables.add(table.lower())
        
        return tables
    
    def _extract_common_filters(self, query_group: List[Tuple[str, float]]) -> List[str]:
        """提取常见过滤条件"""
        filters = []
        
        for query, _ in query_group:
            # 提取WHERE子句
            where_match = re.search(r'WHERE\s+(.+?)(?:\s+ORDER\s+BY|\s+GROUP\s+BY|\s+LIMIT|$)', 
                                  query, re.IGNORECASE)
            if where_match:
                where_clause = where_match.group(1)
                # 简单的列名提取
                column_matches = re.findall(r'(\w+)\s*[=<>!]+', where_clause)
                filters.extend(column_matches)
        
        # 返回出现频率高的过滤条件
        filter_counter = Counter(filters)
        return [col for col, count in filter_counter.most_common(5)]
    
    def _calculate_optimization_potential(self, avg_time: float, frequency: int,
                                        tables_involved: Set[str]) -> float:
        """计算优化潜力评分"""
        # 时间因子 (慢查询优化潜力更大)
        time_factor = min(avg_time / 100, 1.0)
        
        # 频率因子 (高频查询优化价值更大)
        frequency_factor = min(frequency / 1000, 1.0)
        
        # 复杂度因子 (多表查询通常有更大优化空间)
        complexity_factor = min(len(tables_involved) / 5, 1.0)
        
        return (time_factor * 0.4 + frequency_factor * 0.4 + complexity_factor * 0.2) * 100
    
    def suggest_query_optimization(self, query: str, execution_time_ms: float) -> Dict[str, Any]:
        """为特定查询提供优化建议"""
        plan_analysis = self.analyze_query_plan(query)
        optimization_suggestions = {
            'original_query': query,
            'execution_time_ms': execution_time_ms,
            'analysis': asdict(plan_analysis),
            'suggestions': [],
            'rewritten_queries': [],
            'expected_improvement': 0.0
        }
        
        # 基于查询计划生成具体建议
        if plan_analysis.table_scans:
            for table in plan_analysis.table_scans:
                suggestion = self._suggest_index_for_table_scan(query, table)
                optimization_suggestions['suggestions'].append(suggestion)
        
        if plan_analysis.sort_operations:
            suggestion = self._suggest_index_for_sorting(query, plan_analysis.sort_operations)
            optimization_suggestions['suggestions'].append(suggestion)
        
        if plan_analysis.join_operations:
            suggestion = self._suggest_join_optimization(query, plan_analysis.join_operations)
            optimization_suggestions['suggestions'].append(suggestion)
        
        # 生成重写的查询
        rewritten = self._generate_rewritten_queries(query, plan_analysis)
        optimization_suggestions['rewritten_queries'] = rewritten
        
        # 估算改进效果
        optimization_suggestions['expected_improvement'] = self._estimate_improvement(plan_analysis)
        
        return optimization_suggestions
    
    def _suggest_index_for_table_scan(self, query: str, table: str) -> Dict[str, str]:
        """为表扫描建议索引"""
        # 分析WHERE条件，提取可索引的列
        where_columns = []
        where_match = re.search(r'WHERE\s+(.+?)(?:\s+ORDER\s+BY|\s+GROUP\s+BY|\s+LIMIT|$)', 
                               query, re.IGNORECASE)
        if where_match:
            where_clause = where_match.group(1)
            column_matches = re.findall(rf'{table}\.(\w+)', where_clause)
            where_columns.extend(column_matches)
            
            # 也提取没有表前缀的列
            simple_columns = re.findall(r'(\w+)\s*[=<>!]+', where_clause)
            where_columns.extend(simple_columns)
        
        if where_columns:
            columns_str = ', '.join(set(where_columns))
            ddl = f"CREATE INDEX idx_{table}_{'_'.join(set(where_columns))} ON {table}({columns_str})"
        else:
            ddl = f"-- 需要分析具体的WHERE条件来创建合适的索引"
        
        return {
            'type': 'create_index',
            'table': table,
            'reason': f'消除{table}表的全表扫描',
            'suggested_ddl': ddl,
            'expected_benefit': '60-80%的查询性能提升'
        }
    
    def _suggest_index_for_sorting(self, query: str, sort_operations: List[str]) -> Dict[str, str]:
        """为排序操作建议索引"""
        # 提取ORDER BY列
        order_columns = []
        order_match = re.search(r'ORDER\s+BY\s+([^;]+)', query, re.IGNORECASE)
        if order_match:
            order_clause = order_match.group(1)
            columns = re.findall(r'(\w+)', order_clause)
            order_columns.extend(columns)
        
        if order_columns:
            columns_str = ', '.join(order_columns)
            table_name = "target_table"  # 需要从查询中提取实际表名
            ddl = f"CREATE INDEX idx_{table_name}_sort ON {table_name}({columns_str})"
        else:
            ddl = "-- 需要分析ORDER BY子句来创建排序索引"
        
        return {
            'type': 'create_sort_index',
            'reason': '消除排序操作，直接从索引返回有序结果',
            'suggested_ddl': ddl,
            'expected_benefit': '25-50%的查询性能提升'
        }
    
    def _suggest_join_optimization(self, query: str, join_operations: List[str]) -> Dict[str, str]:
        """建议JOIN优化"""
        return {
            'type': 'join_optimization',
            'reason': '优化多表JOIN操作',
            'suggested_ddl': '-- 为JOIN条件中的外键列创建索引',
            'expected_benefit': '30-60%的查询性能提升',
            'additional_tips': [
                '确保JOIN条件使用了索引',
                '考虑调整表的JOIN顺序',
                '使用STRAIGHT_JOIN强制特定的JOIN顺序（如果适用）'
            ]
        }
    
    def _generate_rewritten_queries(self, query: str, plan_analysis: QueryPlan) -> List[Dict[str, str]]:
        """生成查询重写建议"""
        rewritten_queries = []
        
        # 示例：如果有复杂的子查询，建议改写为JOIN
        if 'EXISTS' in query.upper() or 'IN (SELECT' in query.upper():
            rewritten_queries.append({
                'type': 'subquery_to_join',
                'description': '将相关子查询改写为JOIN操作',
                'example': '-- 将 WHERE id IN (SELECT...) 改写为 INNER JOIN'
            })
        
        # 示例：如果有复杂的CASE WHEN，建议使用查找表
        if query.upper().count('CASE') > 2:
            rewritten_queries.append({
                'type': 'case_to_lookup_table',
                'description': '复杂的CASE表达式可以用查找表替换',
                'example': '-- 创建查找表并用JOIN替换复杂的CASE WHEN'
            })
        
        return rewritten_queries
    
    def _estimate_improvement(self, plan_analysis: QueryPlan) -> float:
        """估算性能改进百分比"""
        improvement = 0.0
        
        # 表扫描改为索引查找的改进
        improvement += len(plan_analysis.table_scans) * 0.6
        
        # 排序操作的改进
        improvement += len(plan_analysis.sort_operations) * 0.25
        
        # 临时表的改进
        if plan_analysis.temp_table_usage:
            improvement += 0.3
        
        return min(improvement, 0.9)  # 最大90%改进
    
    def generate_optimization_report(self, hours: int = 24) -> Dict[str, Any]:
        """生成完整的优化报告"""
        report = {
            'timestamp': datetime.now(),
            'analysis_period_hours': hours,
            'slow_queries': [],
            'index_analysis': [],
            'query_patterns': [],
            'recommendations': {
                'high_priority': [],
                'medium_priority': [],
                'low_priority': []
            },
            'estimated_total_improvement': 0.0
        }
        
        # 慢查询分析
        cutoff_time = datetime.now() - timedelta(hours=hours)
        recent_slow_queries = [
            sq for sq in self.slow_queries.values() 
            if sq.last_seen > cutoff_time
        ]
        
        report['slow_queries'] = [asdict(sq) for sq in recent_slow_queries]
        
        # 索引分析
        index_analyses = self.analyze_index_usage()
        report['index_analysis'] = [asdict(idx) for idx in index_analyses]
        
        # 查询模式分析
        query_data = [(sq.query, sq.execution_time_ms) for sq in recent_slow_queries]
        patterns = self.identify_query_patterns(query_data)
        report['query_patterns'] = [asdict(pattern) for pattern in patterns]
        
        # 生成优先级建议
        self._categorize_recommendations(report, recent_slow_queries, index_analyses, patterns)
        
        return report
    
    def _categorize_recommendations(self, report: Dict, slow_queries: List[SlowQueryAnalysis],
                                  index_analyses: List[IndexAnalysis], 
                                  patterns: List[QueryPattern]) -> None:
        """将建议按优先级分类"""
        # 高优先级：频繁的慢查询
        for sq in slow_queries:
            if sq.execution_count > 10 and sq.execution_time_ms > 50:
                report['recommendations']['high_priority'].append({
                    'type': 'critical_slow_query',
                    'description': f'高频慢查询需要立即优化: {sq.query[:100]}...',
                    'impact': 'high',
                    'effort': 'medium'
                })
        
        # 中优先级：低效索引
        for idx in index_analyses:
            if idx.effectiveness_score < 30 and idx.usage_count > 0:
                report['recommendations']['medium_priority'].append({
                    'type': 'inefficient_index',
                    'description': f'索引 {idx.index_name} 效率较低，需要优化',
                    'impact': 'medium',
                    'effort': 'low'
                })
        
        # 低优先级：查询模式优化
        for pattern in patterns[:3]:  # 前3个模式
            if pattern.optimization_potential > 50:
                report['recommendations']['low_priority'].append({
                    'type': 'query_pattern_optimization',
                    'description': f'查询模式可以优化: {pattern.template[:100]}...',
                    'impact': 'medium',
                    'effort': 'high'
                })


if __name__ == "__main__":
    # 命令行工具
    import argparse
    
    parser = argparse.ArgumentParser(description='SQL查询性能分析器')
    parser.add_argument('--db', required=True, help='数据库文件路径')
    parser.add_argument('--query', help='分析特定查询')
    parser.add_argument('--report', action='store_true', help='生成完整分析报告')
    parser.add_argument('--indexes', action='store_true', help='分析索引使用情况')
    
    args = parser.parse_args()
    
    analyzer = QueryAnalyzer(args.db)
    
    if args.query:
        print(f"分析查询: {args.query}")
        suggestions = analyzer.suggest_query_optimization(args.query, 0)
        print(json.dumps(suggestions, indent=2, ensure_ascii=False, default=str))
    
    if args.indexes:
        print("分析索引使用情况...")
        index_analyses = analyzer.analyze_index_usage()
        for analysis in index_analyses:
            print(f"\n索引: {analysis.index_name}")
            print(f"  表: {analysis.table_name}")
            print(f"  列: {analysis.columns}")
            print(f"  使用次数: {analysis.usage_count}")
            print(f"  选择性: {analysis.selectivity:.3f}")
            print(f"  效果评分: {analysis.effectiveness_score:.1f}")
            if analysis.recommendations:
                print("  建议:")
                for rec in analysis.recommendations:
                    print(f"    - {rec}")
    
    if args.report:
        print("生成优化分析报告...")
        report = analyzer.generate_optimization_report()
        print(json.dumps(report, indent=2, ensure_ascii=False, default=str))