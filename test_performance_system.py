#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
性能优化系统综合测试
验证查询<10ms，支持10万+记录的性能目标

测试项目:
1. 基础查询性能测试
2. 大数据量插入和查询测试
3. 索引优化效果验证
4. 移动端分页性能测试
5. 缓存系统效果测试
6. 并发查询性能测试
7. 慢查询分析和优化验证

作者: Claude
创建时间: 2025-08-07
"""

import os
import sys
import time
import json
import random
import threading
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from performance_optimizer import PerformanceOptimizer
from query_analyzer import QueryAnalyzer
from mobile_optimizer import MobileOptimizer, NetworkStatus, CacheStrategy, PaginationConfig


class PerformanceTestSuite:
    """性能测试套件"""
    
    def __init__(self, db_path: str = "performance_test.db"):
        self.db_path = db_path
        self.test_results = {}
        
        # 初始化优化器组件
        self.perf_optimizer = PerformanceOptimizer(db_path)
        self.query_analyzer = QueryAnalyzer(db_path)
        self.mobile_optimizer = MobileOptimizer(db_path)
        
        # 测试数据规模
        self.test_data_sizes = [1000, 10000, 50000, 100000]
        
        print(f"性能测试初始化完成，数据库: {db_path}")
    
    def setup_test_data(self, record_count: int = 100000):
        """创建测试数据"""
        print(f"创建 {record_count:,} 条测试数据...")
        
        # 生成测试数据
        test_data = []
        categories = ['易学', '六爻', '奇门', '紫微', '八字', '风水', '姓名学', '手相', '面相', '择日']
        authors = ['朱熹', '程颐', '王弼', '孔子', '刘伯温', '邵雍', '朱震亨', '李虚中', '徐子平', '袁天罡']
        
        for i in range(record_count):
            test_data.append({
                'title': f'测试标题_{i:06d}',
                'content': f'这是第{i}条测试内容，包含易学相关信息。' + '内容' * random.randint(10, 50),
                'category': random.choice(categories),
                'author': random.choice(authors),
                'importance_level': random.randint(1, 5),
                'view_count': random.randint(1, 10000),
                'created_year': random.randint(1000, 2024)
            })
        
        # 创建测试表
        with self.perf_optimizer.connection_pool.get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS performance_test_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    category TEXT,
                    author TEXT,
                    importance_level INTEGER,
                    view_count INTEGER,
                    created_year INTEGER,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 创建索引
            conn.execute("CREATE INDEX IF NOT EXISTS idx_category ON performance_test_data(category)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_author ON performance_test_data(author)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_importance ON performance_test_data(importance_level)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_year ON performance_test_data(created_year)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_compound ON performance_test_data(category, author)")
            
            conn.commit()
        
        # 批量插入数据
        start_time = time.time()
        inserted_count = self.perf_optimizer.bulk_insert('performance_test_data', test_data)
        insert_time = time.time() - start_time
        
        insert_rate = inserted_count / insert_time
        print(f"数据插入完成: {inserted_count:,} 条记录，耗时 {insert_time:.2f}s，速率 {insert_rate:,.0f} records/sec")
        
        return {
            'record_count': inserted_count,
            'insert_time_seconds': insert_time,
            'insert_rate_per_second': insert_rate
        }
    
    def test_basic_query_performance(self) -> Dict[str, Any]:
        """测试基础查询性能"""
        print("\n=== 基础查询性能测试 ===")
        
        test_queries = [
            # 简单查询
            ("SELECT COUNT(*) FROM performance_test_data", (), "count_all"),
            ("SELECT * FROM performance_test_data WHERE id = ?", (12345,), "select_by_id"),
            ("SELECT * FROM performance_test_data WHERE category = ?", ("易学",), "select_by_category"),
            
            # 复杂查询
            ("SELECT category, COUNT(*) FROM performance_test_data GROUP BY category", (), "group_by_category"),
            ("SELECT * FROM performance_test_data WHERE importance_level >= ? ORDER BY view_count DESC LIMIT 100", (4,), "complex_filter_sort"),
            
            # JOIN查询（自联接）
            ("SELECT a.title, b.title FROM performance_test_data a JOIN performance_test_data b ON a.category = b.category WHERE a.id != b.id LIMIT 50", (), "self_join"),
            
            # 全文搜索模拟
            ("SELECT * FROM performance_test_data WHERE content LIKE ? LIMIT 20", ("%易学%",), "text_search"),
        ]
        
        results = []
        
        for query, params, query_type in test_queries:
            print(f"测试查询: {query_type}")
            
            # 预热查询（避免冷启动影响）
            self.perf_optimizer.execute_query(query, params, query_type)
            
            # 执行多次测量
            times = []
            for _ in range(10):
                start_time = time.time()
                result = self.perf_optimizer.execute_query(query, params, query_type)
                execution_time_ms = (time.time() - start_time) * 1000
                times.append(execution_time_ms)
            
            avg_time = statistics.mean(times)
            min_time = min(times)
            max_time = max(times)
            
            result_info = {
                'query_type': query_type,
                'avg_time_ms': avg_time,
                'min_time_ms': min_time,
                'max_time_ms': max_time,
                'result_count': len(result),
                'under_10ms': avg_time < 10,
                'performance_grade': 'A' if avg_time < 5 else 'B' if avg_time < 10 else 'C'
            }
            
            results.append(result_info)
            print(f"  平均时间: {avg_time:.2f}ms, 结果数: {len(result)}, 等级: {result_info['performance_grade']}")
        
        # 统计结果
        fast_queries = sum(1 for r in results if r['under_10ms'])
        overall_avg = statistics.mean(r['avg_time_ms'] for r in results)
        
        summary = {
            'total_queries_tested': len(results),
            'queries_under_10ms': fast_queries,
            'success_rate': fast_queries / len(results),
            'overall_avg_time_ms': overall_avg,
            'detailed_results': results
        }
        
        print(f"基础查询测试完成: {fast_queries}/{len(results)} 个查询 < 10ms，成功率 {summary['success_rate']:.1%}")
        return summary
    
    def test_large_dataset_performance(self) -> Dict[str, Any]:
        """测试大数据集性能"""
        print("\n=== 大数据集性能测试 ===")
        
        results = {}
        
        for record_count in self.test_data_sizes:
            print(f"\n测试 {record_count:,} 记录规模...")
            
            # 创建指定大小的数据集
            setup_result = self.setup_test_data(record_count)
            
            # 测试各种查询在大数据集上的性能
            test_queries = [
                ("SELECT COUNT(*) FROM performance_test_data", (), "count"),
                ("SELECT * FROM performance_test_data WHERE category = ? LIMIT 100", ("易学",), "indexed_filter"),
                ("SELECT * FROM performance_test_data WHERE view_count > ? ORDER BY view_count DESC LIMIT 50", (5000,), "range_query"),
                ("SELECT category, AVG(view_count) FROM performance_test_data GROUP BY category", (), "aggregation"),
            ]
            
            query_results = []
            for query, params, query_type in test_queries:
                times = []
                for _ in range(5):  # 减少重复次数以节省时间
                    start_time = time.time()
                    result = self.perf_optimizer.execute_query(query, params, query_type)
                    execution_time_ms = (time.time() - start_time) * 1000
                    times.append(execution_time_ms)
                
                avg_time = statistics.mean(times)
                query_results.append({
                    'query_type': query_type,
                    'avg_time_ms': avg_time,
                    'under_10ms': avg_time < 10
                })
            
            success_rate = sum(1 for r in query_results if r['under_10ms']) / len(query_results)
            
            results[record_count] = {
                'setup': setup_result,
                'query_performance': query_results,
                'success_rate': success_rate
            }
            
            print(f"  {record_count:,} 记录性能: {success_rate:.1%} 查询 < 10ms")
        
        return results
    
    def test_mobile_pagination_performance(self) -> Dict[str, Any]:
        """测试移动端分页性能"""
        print("\n=== 移动端分页性能测试 ===")
        
        # 设置不同网络状态测试
        network_scenarios = [
            (NetworkStatus.WIFI, "WiFi环境"),
            (NetworkStatus.MOBILE, "移动网络"),
            (NetworkStatus.SLOW_MOBILE, "慢速移动网络")
        ]
        
        results = {}
        
        for network_status, scenario_name in network_scenarios:
            print(f"\n测试场景: {scenario_name}")
            
            # 设置网络状态
            self.mobile_optimizer.set_network_status(network_status)
            
            # 测试分页查询
            query = "SELECT * FROM performance_test_data ORDER BY created_at DESC"
            pagination_config = PaginationConfig(page_size=20, preload_pages=2)
            
            # 执行分页查询
            start_time = time.time()
            result_id = self.mobile_optimizer.execute_query_paginated(query, (), pagination_config)
            initial_time_ms = (time.time() - start_time) * 1000
            
            # 获取多页数据，模拟用户滑动
            page_times = []
            for page_num in range(5):  # 测试前5页
                start_time = time.time()
                page_data = self.mobile_optimizer.get_page_data(result_id, page_num)
                page_time_ms = (time.time() - start_time) * 1000
                page_times.append(page_time_ms)
                
                print(f"  第{page_num+1}页加载时间: {page_time_ms:.2f}ms, 缓存: {page_data.get('cached', False)}")
            
            avg_page_time = statistics.mean(page_times)
            
            results[network_status.value] = {
                'scenario': scenario_name,
                'initial_load_time_ms': initial_time_ms,
                'avg_page_load_time_ms': avg_page_time,
                'page_load_times_ms': page_times,
                'under_100ms_rate': sum(1 for t in page_times if t < 100) / len(page_times)
            }
            
            print(f"  平均页面加载时间: {avg_page_time:.2f}ms")
        
        return results
    
    def test_cache_effectiveness(self) -> Dict[str, Any]:
        """测试缓存效果"""
        print("\n=== 缓存效果测试 ===")
        
        # 测试查询
        test_query = "SELECT * FROM performance_test_data WHERE category = ? AND importance_level >= ?"
        test_params = ("易学", 3)
        
        results = {
            'cold_query_times': [],
            'cached_query_times': [],
            'cache_hit_improvement': 0
        }
        
        # 清空缓存
        self.perf_optimizer.cache.clear()
        
        # 冷查询测试（无缓存）
        print("执行冷查询测试...")
        for _ in range(10):
            start_time = time.time()
            self.perf_optimizer.execute_query(test_query, test_params, "cache_test")
            execution_time_ms = (time.time() - start_time) * 1000
            results['cold_query_times'].append(execution_time_ms)
        
        # 缓存查询测试
        print("执行缓存查询测试...")
        for _ in range(10):
            start_time = time.time()
            self.perf_optimizer.execute_query(test_query, test_params, "cache_test")
            execution_time_ms = (time.time() - start_time) * 1000
            results['cached_query_times'].append(execution_time_ms)
        
        # 计算改进效果
        avg_cold_time = statistics.mean(results['cold_query_times'])
        avg_cached_time = statistics.mean(results['cached_query_times'])
        
        if avg_cold_time > 0:
            improvement = (avg_cold_time - avg_cached_time) / avg_cold_time
            results['cache_hit_improvement'] = improvement
        
        results['avg_cold_time_ms'] = avg_cold_time
        results['avg_cached_time_ms'] = avg_cached_time
        
        print(f"冷查询平均时间: {avg_cold_time:.2f}ms")
        print(f"缓存查询平均时间: {avg_cached_time:.2f}ms")
        print(f"缓存改进效果: {improvement:.1%}")
        
        return results
    
    def test_concurrent_query_performance(self) -> Dict[str, Any]:
        """测试并发查询性能"""
        print("\n=== 并发查询性能测试 ===")
        
        # 不同并发级别测试
        concurrency_levels = [1, 5, 10, 20]
        results = {}
        
        def execute_query_batch(query_count: int) -> List[float]:
            """执行一批查询"""
            times = []
            queries = [
                ("SELECT COUNT(*) FROM performance_test_data WHERE category = ?", ("易学",)),
                ("SELECT * FROM performance_test_data WHERE importance_level = ? LIMIT 10", (4,)),
                ("SELECT category, COUNT(*) FROM performance_test_data GROUP BY category", ()),
                ("SELECT * FROM performance_test_data WHERE view_count > ? LIMIT 20", (5000,)),
            ]
            
            for i in range(query_count):
                query, params = random.choice(queries)
                start_time = time.time()
                self.perf_optimizer.execute_query(query, params, "concurrent_test")
                execution_time_ms = (time.time() - start_time) * 1000
                times.append(execution_time_ms)
            
            return times
        
        for concurrency in concurrency_levels:
            print(f"\n测试并发级别: {concurrency}")
            
            queries_per_thread = 20
            
            start_time = time.time()
            
            with ThreadPoolExecutor(max_workers=concurrency) as executor:
                futures = [
                    executor.submit(execute_query_batch, queries_per_thread)
                    for _ in range(concurrency)
                ]
                
                all_times = []
                for future in as_completed(futures):
                    times = future.result()
                    all_times.extend(times)
            
            total_time = time.time() - start_time
            total_queries = len(all_times)
            
            avg_time = statistics.mean(all_times)
            throughput = total_queries / total_time
            under_10ms_rate = sum(1 for t in all_times if t < 10) / total_queries
            
            results[concurrency] = {
                'concurrency_level': concurrency,
                'total_queries': total_queries,
                'total_time_seconds': total_time,
                'avg_query_time_ms': avg_time,
                'queries_per_second': throughput,
                'under_10ms_rate': under_10ms_rate
            }
            
            print(f"  平均查询时间: {avg_time:.2f}ms")
            print(f"  吞吐量: {throughput:.1f} queries/sec")
            print(f"  <10ms查询率: {under_10ms_rate:.1%}")
        
        return results
    
    def test_slow_query_analysis(self) -> Dict[str, Any]:
        """测试慢查询分析"""
        print("\n=== 慢查询分析测试 ===")
        
        # 故意创建慢查询
        slow_queries = [
            # 无索引的复杂查询
            ("SELECT * FROM performance_test_data WHERE content LIKE '%测试%' AND title LIKE '%标题%'", (), 25.0),
            
            # 复杂的子查询
            ("SELECT * FROM performance_test_data WHERE id IN (SELECT id FROM performance_test_data WHERE view_count > 8000)", (), 30.0),
            
            # 大范围扫描
            ("SELECT * FROM performance_test_data WHERE created_year BETWEEN 1500 AND 2000 ORDER BY content", (), 40.0),
        ]
        
        analysis_results = []
        
        for query, params, expected_time in slow_queries:
            print(f"\n分析慢查询 (预期 >{expected_time}ms)...")
            
            # 执行查询并测量时间
            start_time = time.time()
            try:
                result = self.perf_optimizer.execute_query(query, params, "slow_query_test")
                execution_time_ms = (time.time() - start_time) * 1000
            except Exception as e:
                print(f"  查询执行失败: {e}")
                continue
            
            print(f"  实际执行时间: {execution_time_ms:.2f}ms")
            
            # 分析慢查询
            if execution_time_ms > 10:
                analysis = self.query_analyzer.analyze_slow_query(query, execution_time_ms, params)
                
                optimization_suggestion = self.query_analyzer.suggest_query_optimization(query, execution_time_ms)
                
                analysis_result = {
                    'query': query[:100] + '...' if len(query) > 100 else query,
                    'execution_time_ms': execution_time_ms,
                    'bottlenecks': analysis.bottlenecks,
                    'optimization_suggestions': analysis.optimization_suggestions,
                    'estimated_improvement': analysis.estimated_improvement,
                    'detailed_suggestions': optimization_suggestion
                }
                
                analysis_results.append(analysis_result)
                
                print(f"  识别的瓶颈: {', '.join(analysis.bottlenecks)}")
                print(f"  预期改进: {analysis.estimated_improvement:.1%}")
        
        return {
            'analyzed_queries': len(analysis_results),
            'analysis_results': analysis_results
        }
    
    def run_full_test_suite(self) -> Dict[str, Any]:
        """运行完整测试套件"""
        print("开始性能优化系统全面测试...")
        print("=" * 60)
        
        # 设置测试数据
        setup_result = self.setup_test_data(50000)  # 5万条数据用于测试
        
        # 执行各项测试
        test_results = {
            'test_timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'setup_result': setup_result,
            'basic_query_performance': self.test_basic_query_performance(),
            'cache_effectiveness': self.test_cache_effectiveness(),
            'mobile_pagination_performance': self.test_mobile_pagination_performance(),
            'concurrent_query_performance': self.test_concurrent_query_performance(),
            'slow_query_analysis': self.test_slow_query_analysis()
        }
        
        # 生成综合报告
        self.generate_test_report(test_results)
        
        return test_results
    
    def generate_test_report(self, test_results: Dict[str, Any]):
        """生成测试报告"""
        print("\n" + "=" * 60)
        print("性能测试综合报告")
        print("=" * 60)
        
        # 基础性能统计
        basic_perf = test_results['basic_query_performance']
        print(f"\n【基础查询性能】")
        print(f"  测试查询数: {basic_perf['total_queries_tested']}")
        print(f"  <10ms查询数: {basic_perf['queries_under_10ms']}")
        print(f"  成功率: {basic_perf['success_rate']:.1%}")
        print(f"  平均查询时间: {basic_perf['overall_avg_time_ms']:.2f}ms")
        
        # 缓存效果
        cache_perf = test_results['cache_effectiveness']
        print(f"\n【缓存系统效果】")
        print(f"  冷查询时间: {cache_perf['avg_cold_time_ms']:.2f}ms")
        print(f"  缓存查询时间: {cache_perf['avg_cached_time_ms']:.2f}ms")
        print(f"  性能改进: {cache_perf['cache_hit_improvement']:.1%}")
        
        # 移动端性能
        mobile_perf = test_results['mobile_pagination_performance']
        print(f"\n【移动端分页性能】")
        for network, data in mobile_perf.items():
            print(f"  {data['scenario']}: {data['avg_page_load_time_ms']:.2f}ms")
            print(f"    <100ms页面率: {data['under_100ms_rate']:.1%}")
        
        # 并发性能
        concurrent_perf = test_results['concurrent_query_performance']
        print(f"\n【并发查询性能】")
        for level, data in concurrent_perf.items():
            print(f"  并发级别 {level}: {data['queries_per_second']:.1f} qps, {data['under_10ms_rate']:.1%} <10ms")
        
        # 慢查询分析
        slow_query = test_results['slow_query_analysis']
        print(f"\n【慢查询分析】")
        print(f"  分析查询数: {slow_query['analyzed_queries']}")
        
        # 总体评估
        print(f"\n【总体评估】")
        basic_success = basic_perf['success_rate'] > 0.8
        cache_effective = cache_perf['cache_hit_improvement'] > 0.5
        mobile_good = all(data['under_100ms_rate'] > 0.8 for data in mobile_perf.values())
        
        print(f"  基础性能: {'✓' if basic_success else '✗'} ({'优秀' if basic_success else '需改进'})")
        print(f"  缓存效果: {'✓' if cache_effective else '✗'} ({'优秀' if cache_effective else '需改进'})")
        print(f"  移动端性能: {'✓' if mobile_good else '✗'} ({'优秀' if mobile_good else '需改进'})")
        
        overall_score = sum([basic_success, cache_effective, mobile_good]) / 3
        grade = 'A' if overall_score > 0.8 else 'B' if overall_score > 0.6 else 'C'
        print(f"  综合评级: {grade} ({overall_score:.1%})")
        
        # 保存详细报告
        report_file = f"performance_test_report_{int(time.time())}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(test_results, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"\n详细报告已保存到: {report_file}")
    
    def cleanup(self):
        """清理测试资源"""
        try:
            self.perf_optimizer.close()
            self.mobile_optimizer.close()
        except:
            pass


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='性能优化系统综合测试')
    parser.add_argument('--db', default='performance_test.db', help='测试数据库文件')
    parser.add_argument('--quick', action='store_true', help='快速测试模式')
    parser.add_argument('--test', choices=[
        'basic', 'cache', 'mobile', 'concurrent', 'slow_query', 'full'
    ], default='full', help='指定测试项目')
    
    args = parser.parse_args()
    
    # 清理旧的测试数据库
    if os.path.exists(args.db):
        os.remove(args.db)
    
    test_suite = PerformanceTestSuite(args.db)
    
    try:
        if args.quick:
            # 快速测试模式，使用较小数据量
            test_suite.test_data_sizes = [1000, 5000]
        
        if args.test == 'full':
            results = test_suite.run_full_test_suite()
        elif args.test == 'basic':
            test_suite.setup_test_data(10000)
            results = test_suite.test_basic_query_performance()
        elif args.test == 'cache':
            test_suite.setup_test_data(10000)
            results = test_suite.test_cache_effectiveness()
        elif args.test == 'mobile':
            test_suite.setup_test_data(10000)
            results = test_suite.test_mobile_pagination_performance()
        elif args.test == 'concurrent':
            test_suite.setup_test_data(10000)
            results = test_suite.test_concurrent_query_performance()
        elif args.test == 'slow_query':
            test_suite.setup_test_data(10000)
            results = test_suite.test_slow_query_analysis()
        
        if args.test != 'full':
            print("\n测试结果:")
            print(json.dumps(results, indent=2, ensure_ascii=False, default=str))
    
    finally:
        test_suite.cleanup()


if __name__ == "__main__":
    main()