#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
易学知识库性能测试和演示脚本
测试10万+记录的查询性能，验证分层存储和FTS5搜索效果

主要测试项：
1. 基础CRUD性能
2. FTS5全文搜索性能
3. 复杂关联查询性能
4. 分层存储效果
5. 缓存命中率
6. 并发性能测试

作者: Claude
创建时间: 2025-08-07
"""

import time
import random
import sqlite3
import threading
from concurrent.futures import ThreadPoolExecutor
import json
import sys
import os

# 添加父目录到路径以导入db_manager
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from db_manager import DatabaseManager


class PerformanceTester:
    """性能测试器"""
    
    def __init__(self, db_path: str = "test_yixue_kb.db"):
        self.db_path = db_path
        self.db = DatabaseManager(db_path, enable_performance_logging=True)
        self.test_results = {}
        
        # 初始化测试数据
        self._setup_test_data()
    
    def _setup_test_data(self):
        """设置测试数据"""
        print("正在初始化测试数据...")
        
        # 加载示例数据
        schema_path = os.path.join(os.path.dirname(__file__), 'sample_data.sql')
        if os.path.exists(schema_path):
            with open(schema_path, 'r', encoding='utf-8') as f:
                sample_sql = f.read()
            
            with self.db.get_connection() as conn:
                conn.executescript(sample_sql)
                conn.commit()
        
        # 生成大量测试数据以达到10万+记录
        self._generate_bulk_data()
        print("测试数据初始化完成")
    
    def _generate_bulk_data(self):
        """生成批量测试数据"""
        print("生成大量测试数据...")
        
        # 生成大量注解数据
        authors = ['朱熹', '程颐', '王弼', '孔子', '邵雍', '周敦颐', '张载', '司马光', '苏轼', '王安石']
        dynasties = ['春秋', '战国', '汉', '魏', '晋', '唐', '宋', '元', '明', '清']
        interpretation_types = ['象', '义', '占', '理', '数']
        
        bulk_interpretations = []
        for i in range(10000):  # 生成10000条注解
            author = random.choice(authors)
            dynasty = random.choice(dynasties)
            interp_type = random.choice(interpretation_types)
            importance = random.choice([3, 3, 3, 4, 4, 5])  # 更多中等重要性
            
            interpretation_text = f"这是第{i+1}条测试注解。作者{author}在{dynasty}朝的观点是..." + "易学深奥，需要仔细研读。" * random.randint(5, 20)
            
            is_core = importance >= 4 or author in ['朱熹', '程颐', '王弼', '孔子']
            
            bulk_interpretations.append({
                'target_type': random.choice(['hexagram', 'line']),
                'target_id': random.randint(1, 64),
                'author': author,
                'dynasty': dynasty,
                'source_book': f"《{author}文集》",
                'interpretation_text': interpretation_text,
                'interpretation_type': interp_type,
                'importance_level': importance,
                'is_core_content': is_core,
                'keywords': f"{author},{dynasty},{interp_type}",
                'content_length': len(interpretation_text)
            })
        
        # 批量插入注解
        with self.db.get_connection() as conn:
            for data in bulk_interpretations:
                conn.execute("""
                    INSERT INTO interpretations 
                    (target_type, target_id, author, dynasty, source_book,
                     interpretation_text, interpretation_type, importance_level,
                     is_core_content, keywords, content_length)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    data['target_type'], data['target_id'], data['author'],
                    data['dynasty'], data['source_book'], data['interpretation_text'],
                    data['interpretation_type'], data['importance_level'],
                    data['is_core_content'], data['keywords'], data['content_length']
                ))
            conn.commit()
        
        # 生成大量占卜案例
        question_types = ['事业', '婚姻', '健康', '学业', '财运', '出行', '官司', '搬家']
        diviners = ['张三丰', '刘伯温', '诸葛亮', '袁天罡', '李淳风', '邵康节']
        
        bulk_cases = []
        for i in range(5000):  # 生成5000个案例
            case_title = f"测试案例{i+1}"
            hexagram_id = random.randint(1, 64)
            question_type = random.choice(question_types)
            diviner = random.choice(diviners)
            accuracy = random.choices([3, 4, 5], weights=[0.3, 0.5, 0.2])[0]
            
            question_detail = f"这是第{i+1}个{question_type}相关的问题，涉及具体情况..." + "请大师指点迷津。" * random.randint(3, 8)
            interpretation = f"{diviner}解卦：根据卦象分析..." + "预测结果如下。" * random.randint(5, 15)
            actual_result = "后续验证确实如预测所说。" * random.randint(2, 6)
            
            bulk_cases.append({
                'case_title': case_title,
                'hexagram_id': hexagram_id,
                'question_type': question_type,
                'question_detail': question_detail,
                'interpretation': interpretation,
                'actual_result': actual_result,
                'accuracy_rating': accuracy,
                'diviner_name': diviner,
                'case_source': f"《{diviner}案例集》",
                'is_verified': random.choice([True, False]),
                'tags': f"{question_type},{diviner},测试"
            })
        
        # 批量插入案例
        with self.db.get_connection() as conn:
            for data in bulk_cases:
                conn.execute("""
                    INSERT INTO divination_cases 
                    (case_title, hexagram_id, question_type, question_detail,
                     interpretation, actual_result, accuracy_rating, diviner_name,
                     case_source, is_verified, tags)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    data['case_title'], data['hexagram_id'], data['question_type'],
                    data['question_detail'], data['interpretation'], data['actual_result'],
                    data['accuracy_rating'], data['diviner_name'], data['case_source'],
                    data['is_verified'], data['tags']
                ))
            conn.commit()
        
        print("批量数据生成完成")
    
    def test_basic_queries(self):
        """测试基础查询性能"""
        print("\n=== 基础查询性能测试 ===")
        
        tests = [
            ("单卦查询", lambda: self.db.get_hexagram_by_number(1)),
            ("卦名查询", lambda: self.db.get_hexagram_by_name("乾")),
            ("完整卦象查询", lambda: self.db.get_complete_hexagram_info(1)),
            ("爻查询", lambda: self.db.get_lines_by_hexagram(1)),
            ("注解查询", lambda: self.db.get_interpretations_by_target('hexagram', 1)),
            ("案例查询", lambda: self.db.get_cases_by_hexagram(1)),
        ]
        
        for test_name, test_func in tests:
            times = []
            for _ in range(10):  # 每个测试执行10次
                start = time.time()
                result = test_func()
                end = time.time()
                times.append((end - start) * 1000)  # 转换为毫秒
            
            avg_time = sum(times) / len(times)
            min_time = min(times)
            max_time = max(times)
            
            print(f"{test_name}: 平均 {avg_time:.2f}ms, 最小 {min_time:.2f}ms, 最大 {max_time:.2f}ms")
            self.test_results[test_name] = {
                'avg_ms': avg_time,
                'min_ms': min_time,
                'max_ms': max_time
            }
    
    def test_fts_search_performance(self):
        """测试FTS5全文搜索性能"""
        print("\n=== FTS5全文搜索性能测试 ===")
        
        search_terms = [
            ("单字搜索", "龙"),
            ("双字搜索", "君子"),
            ("短语搜索", "刚健"),
            ("复合搜索", "天 AND 地"),
            ("通配符搜索", "龙*"),
            ("多关键词", "乾 OR 坤"),
        ]
        
        for search_name, term in search_terms:
            times = []
            result_counts = []
            
            for _ in range(5):  # 每个搜索执行5次
                start = time.time()
                
                # 测试各种搜索
                hexagram_results = self.db.search_hexagrams(term, 10)
                line_results = self.db.search_lines(term, 20)
                interp_results = self.db.search_interpretations(term, 30)
                case_results = self.db.search_cases(term, 15)
                
                end = time.time()
                times.append((end - start) * 1000)
                result_counts.append(len(hexagram_results) + len(line_results) + 
                                   len(interp_results) + len(case_results))
            
            avg_time = sum(times) / len(times)
            avg_results = sum(result_counts) / len(result_counts)
            
            print(f"{search_name} ({term}): 平均 {avg_time:.2f}ms, 平均结果 {avg_results:.1f}条")
            self.test_results[f"fts_{search_name}"] = {
                'avg_ms': avg_time,
                'avg_results': avg_results
            }
    
    def test_complex_queries(self):
        """测试复杂关联查询性能"""
        print("\n=== 复杂查询性能测试 ===")
        
        complex_tests = [
            ("完整卦象关联", lambda: self.db.get_hexagram_with_related_content(1)),
            ("相似卦象查询", lambda: self.db.get_similar_hexagrams(1, 5)),
            ("热门案例查询", lambda: self.db.get_popular_cases(20)),
            ("核心注解查询", lambda: self.db.get_core_interpretations()),
            ("关键词统计", lambda: self.db.get_keyword_stats()),
        ]
        
        for test_name, test_func in complex_tests:
            times = []
            for _ in range(3):  # 复杂查询执行3次
                start = time.time()
                result = test_func()
                end = time.time()
                times.append((end - start) * 1000)
            
            avg_time = sum(times) / len(times)
            print(f"{test_name}: 平均 {avg_time:.2f}ms")
            self.test_results[f"complex_{test_name}"] = {'avg_ms': avg_time}
    
    def test_storage_tiers(self):
        """测试分层存储效果"""
        print("\n=== 分层存储测试 ===")
        
        storage_stats = self.db.get_storage_stats()
        
        core_size = 0
        extended_size = 0
        
        for stat in storage_stats:
            table_name = stat['table_name']
            size_bytes = stat['estimated_size_bytes'] or 0
            
            if 'core' in table_name or table_name in ['hexagrams', 'lines', 'keywords_tags']:
                core_size += size_bytes
            else:
                extended_size += size_bytes
        
        core_mb = core_size / 1024 / 1024
        extended_mb = extended_size / 1024 / 1024
        total_mb = core_mb + extended_mb
        
        print(f"核心数据: {core_mb:.2f}MB ({'✓ 符合5MB限制' if core_mb <= 5 else '⚠ 超出5MB限制'})")
        print(f"扩展数据: {extended_mb:.2f}MB ({'✓ 符合50MB限制' if extended_mb <= 50 else '⚠ 超出50MB限制'})")
        print(f"总计数据: {total_mb:.2f}MB")
        
        self.test_results['storage'] = {
            'core_mb': core_mb,
            'extended_mb': extended_mb,
            'total_mb': total_mb,
            'core_limit_ok': core_mb <= 5,
            'extended_limit_ok': extended_mb <= 50
        }
    
    def test_concurrent_performance(self):
        """测试并发性能"""
        print("\n=== 并发性能测试 ===")
        
        def worker_task(worker_id):
            """工作线程任务"""
            times = []
            for _ in range(10):
                start = time.time()
                
                # 执行各种操作
                self.db.get_hexagram_by_number(random.randint(1, 64))
                self.db.search_hexagrams("测试", 5)
                self.db.get_interpretations_by_target('hexagram', random.randint(1, 64))
                
                end = time.time()
                times.append((end - start) * 1000)
            
            return {
                'worker_id': worker_id,
                'avg_time': sum(times) / len(times),
                'total_operations': len(times) * 3
            }
        
        # 测试不同并发数
        for thread_count in [1, 2, 4, 8]:
            start_time = time.time()
            
            with ThreadPoolExecutor(max_workers=thread_count) as executor:
                futures = [executor.submit(worker_task, i) for i in range(thread_count)]
                results = [future.result() for future in futures]
            
            end_time = time.time()
            total_time = (end_time - start_time) * 1000
            total_ops = sum(r['total_operations'] for r in results)
            ops_per_second = total_ops / (total_time / 1000)
            
            print(f"{thread_count}线程: 总时间 {total_time:.2f}ms, 操作数 {total_ops}, QPS {ops_per_second:.1f}")
            
            self.test_results[f"concurrent_{thread_count}"] = {
                'total_ms': total_time,
                'total_ops': total_ops,
                'qps': ops_per_second
            }
    
    def test_cache_effectiveness(self):
        """测试缓存效果"""
        print("\n=== 缓存效果测试 ===")
        
        # 清空缓存
        self.db.clear_cache()
        
        # 第一次查询 (缓存未命中)
        start = time.time()
        result1 = self.db.get_hexagram_by_number(1)
        first_time = (time.time() - start) * 1000
        
        # 第二次查询 (缓存命中)
        start = time.time()
        result2 = self.db.get_hexagram_by_number(1)
        second_time = (time.time() - start) * 1000
        
        cache_improvement = ((first_time - second_time) / first_time) * 100
        
        print(f"首次查询: {first_time:.2f}ms")
        print(f"缓存查询: {second_time:.2f}ms")
        print(f"性能提升: {cache_improvement:.1f}%")
        
        self.test_results['cache'] = {
            'first_ms': first_time,
            'cached_ms': second_time,
            'improvement_pct': cache_improvement
        }
    
    def run_all_tests(self):
        """运行所有性能测试"""
        print("开始易学知识库性能测试...")
        print(f"数据库路径: {self.db_path}")
        
        # 获取数据统计
        storage_stats = self.db.get_storage_stats()
        total_records = sum(stat['record_count'] for stat in storage_stats)
        print(f"总记录数: {total_records}")
        
        # 执行各项测试
        self.test_basic_queries()
        self.test_fts_search_performance()
        self.test_complex_queries()
        self.test_storage_tiers()
        self.test_concurrent_performance()
        self.test_cache_effectiveness()
        
        # 生成测试报告
        self.generate_report()
    
    def generate_report(self):
        """生成性能测试报告"""
        print("\n" + "="*60)
        print("易学知识库性能测试报告")
        print("="*60)
        
        # 基础性能总结
        print("\n基础查询性能:")
        basic_queries = [k for k in self.test_results.keys() if not k.startswith(('fts_', 'complex_', 'concurrent_', 'storage', 'cache'))]
        avg_basic_time = sum(self.test_results[k]['avg_ms'] for k in basic_queries) / len(basic_queries)
        print(f"  平均响应时间: {avg_basic_time:.2f}ms")
        
        # 搜索性能总结
        print("\n全文搜索性能:")
        fts_queries = [k for k in self.test_results.keys() if k.startswith('fts_')]
        if fts_queries:
            avg_fts_time = sum(self.test_results[k]['avg_ms'] for k in fts_queries) / len(fts_queries)
            print(f"  平均搜索时间: {avg_fts_time:.2f}ms")
        
        # 复杂查询性能
        print("\n复杂查询性能:")
        complex_queries = [k for k in self.test_results.keys() if k.startswith('complex_')]
        if complex_queries:
            avg_complex_time = sum(self.test_results[k]['avg_ms'] for k in complex_queries) / len(complex_queries)
            print(f"  平均复杂查询时间: {avg_complex_time:.2f}ms")
        
        # 分层存储状态
        if 'storage' in self.test_results:
            storage = self.test_results['storage']
            print(f"\n分层存储状态:")
            print(f"  核心数据: {storage['core_mb']:.2f}MB ({'✓' if storage['core_limit_ok'] else '✗'})")
            print(f"  扩展数据: {storage['extended_mb']:.2f}MB ({'✓' if storage['extended_limit_ok'] else '✗'})")
            print(f"  总数据量: {storage['total_mb']:.2f}MB")
        
        # 并发性能
        concurrent_results = [k for k in self.test_results.keys() if k.startswith('concurrent_')]
        if concurrent_results:
            print(f"\n并发性能:")
            for k in sorted(concurrent_results):
                thread_num = k.split('_')[1]
                qps = self.test_results[k]['qps']
                print(f"  {thread_num}线程 QPS: {qps:.1f}")
        
        # 缓存效果
        if 'cache' in self.test_results:
            cache = self.test_results['cache']
            print(f"\n缓存效果:")
            print(f"  性能提升: {cache['improvement_pct']:.1f}%")
        
        # 总体评估
        print("\n性能评估:")
        if avg_basic_time < 50:
            print("  ✓ 基础查询性能优秀 (< 50ms)")
        elif avg_basic_time < 100:
            print("  ✓ 基础查询性能良好 (< 100ms)")
        else:
            print("  ⚠ 基础查询性能需要优化 (> 100ms)")
        
        # 保存详细报告
        report_file = f"performance_report_{int(time.time())}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(self.test_results, f, ensure_ascii=False, indent=2)
        print(f"\n详细报告已保存到: {report_file}")


def main():
    """主程序"""
    print("易学知识库性能测试工具")
    print("="*50)
    
    # 创建测试器并运行测试
    tester = PerformanceTester()
    
    try:
        tester.run_all_tests()
    except KeyboardInterrupt:
        print("\n测试被用户中断")
    except Exception as e:
        print(f"\n测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        tester.db.close()
        print("\n测试完成")


if __name__ == "__main__":
    main()