#!/usr/bin/env python3
"""
性能基准测试套件
Performance Benchmark Test Suite
测试PDF处理、SQLite查询、数据压缩等性能指标
"""

import time
import sqlite3
import multiprocessing as mp
import concurrent.futures
import random
import string
import hashlib
import json
import os
import sys
import tempfile
import shutil
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass, asdict
from contextlib import contextmanager
import statistics
import psutil
import traceback

# 尝试导入可选依赖
try:
    import lz4.frame
    HAS_LZ4 = True
except ImportError:
    HAS_LZ4 = False
    
try:
    import zstandard as zstd
    HAS_ZSTD = True
except ImportError:
    HAS_ZSTD = False

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

# ============================================================================
# 基准测试结果数据类
# ============================================================================

@dataclass
class BenchmarkResult:
    """基准测试结果"""
    test_name: str
    duration_ms: float
    throughput: float
    memory_mb: float
    cpu_percent: float
    success: bool
    error: Optional[str] = None
    details: Dict = None
    
    def __post_init__(self):
        if self.details is None:
            self.details = {}
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    def print_summary(self):
        """打印测试结果摘要"""
        status = "✓ 成功" if self.success else "✗ 失败"
        print(f"\n{status} {self.test_name}")
        print(f"  耗时: {self.duration_ms:.2f}ms")
        print(f"  吞吐量: {self.throughput:.2f}/s")
        print(f"  内存: {self.memory_mb:.2f}MB")
        print(f"  CPU: {self.cpu_percent:.1f}%")
        if self.error:
            print(f"  错误: {self.error}")
        if self.details:
            for key, value in self.details.items():
                print(f"  {key}: {value}")


# ============================================================================
# 性能监控工具
# ============================================================================

class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self):
        self.process = psutil.Process()
        self.start_time = None
        self.start_memory = None
        self.start_cpu_time = None
    
    def start(self):
        """开始监控"""
        self.start_time = time.time()
        self.start_memory = self.process.memory_info().rss / 1024 / 1024
        self.start_cpu_time = sum(self.process.cpu_times()[:2])
    
    def stop(self) -> Tuple[float, float, float]:
        """停止监控并返回(duration_ms, memory_mb, cpu_percent)"""
        duration = (time.time() - self.start_time) * 1000
        memory = (self.process.memory_info().rss / 1024 / 1024) - self.start_memory
        cpu_time = sum(self.process.cpu_times()[:2]) - self.start_cpu_time
        cpu_percent = (cpu_time / (time.time() - self.start_time)) * 100
        return duration, abs(memory), cpu_percent

@contextmanager
def performance_monitor():
    """性能监控上下文管理器"""
    monitor = PerformanceMonitor()
    monitor.start()
    try:
        yield monitor
    finally:
        pass  # stop在外部调用


# ============================================================================
# PDF批处理基准测试
# ============================================================================

class PDFBenchmark:
    """PDF批处理性能测试"""
    
    @staticmethod
    def simulate_pdf_processing(file_path: str) -> Dict:
        """模拟PDF处理(实际应用中使用PyPDF2等)"""
        # 模拟文本提取
        time.sleep(random.uniform(0.1, 0.3))  # 模拟处理时间
        
        # 生成模拟数据
        text_length = random.randint(1000, 10000)
        text = ''.join(random.choices(string.ascii_letters + string.digits, k=text_length))
        
        return {
            "file": file_path,
            "pages": random.randint(1, 100),
            "text_length": text_length,
            "hash": hashlib.md5(text.encode()).hexdigest()
        }
    
    @staticmethod
    def worker_process(file_paths: List[str]) -> List[Dict]:
        """工作进程"""
        results = []
        for path in file_paths:
            try:
                result = PDFBenchmark.simulate_pdf_processing(path)
                results.append(result)
            except Exception as e:
                results.append({"file": path, "error": str(e)})
        return results
    
    @classmethod
    def run_benchmark(cls, num_files: int = 200, num_workers: int = None) -> BenchmarkResult:
        """运行PDF批处理基准测试"""
        if num_workers is None:
            num_workers = mp.cpu_count() * 2
        
        print(f"\n开始PDF批处理测试: {num_files}个文件, {num_workers}个进程")
        
        # 生成模拟文件路径
        file_paths = [f"file_{i}.pdf" for i in range(num_files)]
        
        # 分配任务
        chunk_size = len(file_paths) // num_workers + 1
        chunks = [file_paths[i:i+chunk_size] for i in range(0, len(file_paths), chunk_size)]
        
        with performance_monitor() as monitor:
            try:
                # 多进程处理
                with mp.Pool(processes=num_workers) as pool:
                    results = pool.map(cls.worker_process, chunks)
                
                duration, memory, cpu = monitor.stop()
                
                # 展平结果
                all_results = [item for sublist in results for item in sublist]
                successful = sum(1 for r in all_results if "error" not in r)
                
                # 计算吞吐量(文件/小时)
                throughput_per_hour = (successful / duration) * 1000 * 3600
                
                return BenchmarkResult(
                    test_name="PDF批处理",
                    duration_ms=duration,
                    throughput=throughput_per_hour,
                    memory_mb=memory,
                    cpu_percent=cpu,
                    success=successful == num_files,
                    details={
                        "总文件数": num_files,
                        "成功处理": successful,
                        "工作进程": num_workers,
                        "文件/小时": f"{throughput_per_hour:.0f}",
                        "目标达成": "是" if throughput_per_hour >= 200 else "否"
                    }
                )
            except Exception as e:
                duration, memory, cpu = monitor.stop()
                return BenchmarkResult(
                    test_name="PDF批处理",
                    duration_ms=duration,
                    throughput=0,
                    memory_mb=memory,
                    cpu_percent=cpu,
                    success=False,
                    error=str(e)
                )


# ============================================================================
# SQLite查询基准测试
# ============================================================================

class SQLiteBenchmark:
    """SQLite查询性能测试"""
    
    @staticmethod
    def setup_test_database(db_path: str, num_records: int = 10000):
        """创建测试数据库"""
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 应用优化PRAGMA设置
        pragmas = [
            "PRAGMA journal_mode = WAL",
            "PRAGMA synchronous = NORMAL",
            "PRAGMA cache_size = -64000",
            "PRAGMA temp_store = MEMORY",
            "PRAGMA mmap_size = 268435456",
        ]
        for pragma in pragmas:
            cursor.execute(pragma)
        
        # 创建测试表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS hexagrams (
                id INTEGER PRIMARY KEY,
                number INTEGER,
                name TEXT,
                description TEXT,
                category TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS dreams (
                id INTEGER PRIMARY KEY,
                keyword TEXT,
                interpretation TEXT,
                category TEXT,
                relevance REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 插入测试数据
        hexagram_data = [
            (i, i % 64 + 1, f"卦{i}", f"描述{i}", f"类别{i % 8}")
            for i in range(num_records)
        ]
        cursor.executemany(
            "INSERT INTO hexagrams (id, number, name, description, category) VALUES (?, ?, ?, ?, ?)",
            hexagram_data
        )
        
        dream_data = [
            (i, f"梦{i}", f"解释{i}", f"类别{i % 10}", random.random())
            for i in range(num_records)
        ]
        cursor.executemany(
            "INSERT INTO dreams (id, keyword, interpretation, category, relevance) VALUES (?, ?, ?, ?, ?)",
            dream_data
        )
        
        # 创建索引
        indexes = [
            "CREATE INDEX idx_hexagram_number ON hexagrams(number)",
            "CREATE INDEX idx_hexagram_category ON hexagrams(category)",
            "CREATE INDEX idx_dream_keyword ON dreams(keyword)",
            "CREATE INDEX idx_dream_category ON dreams(category)",
            "CREATE INDEX idx_dream_relevance ON dreams(relevance)",
        ]
        for index in indexes:
            cursor.execute(index)
        
        conn.commit()
        conn.close()
    
    @classmethod
    def run_benchmark(cls, num_queries: int = 1000) -> BenchmarkResult:
        """运行SQLite查询基准测试"""
        print(f"\n开始SQLite查询测试: {num_queries}次查询")
        
        # 创建临时数据库
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name
        
        try:
            # 设置测试数据库
            cls.setup_test_database(db_path)
            
            with performance_monitor() as monitor:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                
                query_times = []
                queries = [
                    ("SELECT * FROM hexagrams WHERE number = ?", (random.randint(1, 64),)),
                    ("SELECT * FROM dreams WHERE category = ? LIMIT 10", (f"类别{random.randint(0, 9)}",)),
                    ("SELECT * FROM hexagrams WHERE category = ? ORDER BY created_at DESC LIMIT 20", 
                     (f"类别{random.randint(0, 7)}",)),
                    ("SELECT d.*, h.name FROM dreams d JOIN hexagrams h ON d.id = h.id WHERE d.relevance > ?", 
                     (0.5,)),
                    ("SELECT COUNT(*) FROM hexagrams WHERE number IN (?, ?, ?, ?)", 
                     (1, 8, 15, 22)),
                ]
                
                for _ in range(num_queries):
                    query, params = random.choice(queries)
                    
                    start = time.perf_counter()
                    cursor.execute(query, params)
                    cursor.fetchall()
                    end = time.perf_counter()
                    
                    query_times.append((end - start) * 1000)  # 转换为毫秒
                
                conn.close()
                duration, memory, cpu = monitor.stop()
                
                # 计算统计信息
                avg_time = statistics.mean(query_times)
                p50 = statistics.median(query_times)
                p95 = sorted(query_times)[int(len(query_times) * 0.95)]
                p99 = sorted(query_times)[int(len(query_times) * 0.99)]
                
                return BenchmarkResult(
                    test_name="SQLite查询",
                    duration_ms=duration,
                    throughput=num_queries / (duration / 1000),
                    memory_mb=memory,
                    cpu_percent=cpu,
                    success=p95 < 5,  # P95 < 5ms为成功
                    details={
                        "查询次数": num_queries,
                        "平均耗时": f"{avg_time:.2f}ms",
                        "P50": f"{p50:.2f}ms",
                        "P95": f"{p95:.2f}ms",
                        "P99": f"{p99:.2f}ms",
                        "目标达成": "是" if p95 < 5 else "否"
                    }
                )
                
        except Exception as e:
            return BenchmarkResult(
                test_name="SQLite查询",
                duration_ms=0,
                throughput=0,
                memory_mb=0,
                cpu_percent=0,
                success=False,
                error=str(e)
            )
        finally:
            # 清理临时文件
            if os.path.exists(db_path):
                os.unlink(db_path)


# ============================================================================
# 数据压缩基准测试
# ============================================================================

class CompressionBenchmark:
    """数据压缩性能测试"""
    
    @staticmethod
    def generate_test_data(size_mb: int) -> bytes:
        """生成测试数据"""
        # 生成具有一定重复性的数据以模拟真实场景
        data_parts = []
        total_size = size_mb * 1024 * 1024
        chunk_size = 1024 * 1024  # 1MB chunks
        
        patterns = [
            b"Lorem ipsum dolor sit amet, " * 100,
            bytes(range(256)) * 100,
            b"0123456789" * 1000,
            b"ABCDEFGHIJKLMNOPQRSTUVWXYZ" * 500,
        ]
        
        while sum(len(p) for p in data_parts) < total_size:
            pattern = random.choice(patterns)
            noise = bytes(random.getrandbits(8) for _ in range(100))
            data_parts.append(pattern + noise)
        
        return b''.join(data_parts)[:total_size]
    
    @staticmethod
    def compress_lz4(data: bytes) -> Tuple[bytes, float, float]:
        """LZ4压缩"""
        if not HAS_LZ4:
            return b'', 0, 0
        
        start = time.perf_counter()
        compressed = lz4.frame.compress(data, compression_level=9)
        compress_time = time.perf_counter() - start
        
        start = time.perf_counter()
        decompressed = lz4.frame.decompress(compressed)
        decompress_time = time.perf_counter() - start
        
        return compressed, compress_time, decompress_time
    
    @staticmethod
    def compress_zstd(data: bytes, level: int = 3) -> Tuple[bytes, float, float]:
        """ZSTD压缩"""
        if not HAS_ZSTD:
            return b'', 0, 0
        
        cctx = zstd.ZstdCompressor(level=level, threads=-1)
        dctx = zstd.ZstdDecompressor()
        
        start = time.perf_counter()
        compressed = cctx.compress(data)
        compress_time = time.perf_counter() - start
        
        start = time.perf_counter()
        decompressed = dctx.decompress(compressed)
        decompress_time = time.perf_counter() - start
        
        return compressed, compress_time, decompress_time
    
    @classmethod
    def run_benchmark(cls, data_size_mb: int = 100) -> BenchmarkResult:
        """运行压缩基准测试"""
        print(f"\n开始数据压缩测试: {data_size_mb}MB数据")
        
        with performance_monitor() as monitor:
            try:
                # 生成测试数据
                print("  生成测试数据...")
                test_data = cls.generate_test_data(data_size_mb)
                original_size = len(test_data)
                
                results = {}
                
                # 测试LZ4
                if HAS_LZ4:
                    print("  测试LZ4压缩...")
                    compressed, c_time, d_time = cls.compress_lz4(test_data)
                    if compressed:
                        results["LZ4"] = {
                            "压缩率": original_size / len(compressed),
                            "压缩速度": f"{(original_size / 1024 / 1024) / c_time:.1f}MB/s",
                            "解压速度": f"{(original_size / 1024 / 1024) / d_time:.1f}MB/s",
                            "压缩后大小": f"{len(compressed) / 1024 / 1024:.1f}MB"
                        }
                
                # 测试ZSTD (标准级别)
                if HAS_ZSTD:
                    print("  测试ZSTD压缩(级别3)...")
                    compressed, c_time, d_time = cls.compress_zstd(test_data, level=3)
                    if compressed:
                        results["ZSTD-3"] = {
                            "压缩率": original_size / len(compressed),
                            "压缩速度": f"{(original_size / 1024 / 1024) / c_time:.1f}MB/s",
                            "解压速度": f"{(original_size / 1024 / 1024) / d_time:.1f}MB/s",
                            "压缩后大小": f"{len(compressed) / 1024 / 1024:.1f}MB"
                        }
                
                # 测试ZSTD (高压缩级别)
                if HAS_ZSTD:
                    print("  测试ZSTD压缩(级别19)...")
                    compressed, c_time, d_time = cls.compress_zstd(test_data, level=19)
                    if compressed:
                        results["ZSTD-19"] = {
                            "压缩率": original_size / len(compressed),
                            "压缩速度": f"{(original_size / 1024 / 1024) / c_time:.1f}MB/s",
                            "解压速度": f"{(original_size / 1024 / 1024) / d_time:.1f}MB/s",
                            "压缩后大小": f"{len(compressed) / 1024 / 1024:.1f}MB"
                        }
                
                duration, memory, cpu = monitor.stop()
                
                # 计算3.7GB->100MB所需的压缩率
                required_ratio = (3.7 * 1024) / 100
                
                return BenchmarkResult(
                    test_name="数据压缩",
                    duration_ms=duration,
                    throughput=data_size_mb / (duration / 1000),
                    memory_mb=memory,
                    cpu_percent=cpu,
                    success=True,
                    details={
                        "原始大小": f"{data_size_mb}MB",
                        "所需压缩率": f"{required_ratio:.1f}x",
                        **{f"{algo}_{key}": value 
                           for algo, metrics in results.items() 
                           for key, value in metrics.items()}
                    }
                )
                
            except Exception as e:
                duration, memory, cpu = monitor.stop()
                return BenchmarkResult(
                    test_name="数据压缩",
                    duration_ms=duration,
                    throughput=0,
                    memory_mb=memory,
                    cpu_percent=cpu,
                    success=False,
                    error=str(e)
                )


# ============================================================================
# Flutter性能模拟测试
# ============================================================================

class FlutterBenchmark:
    """Flutter应用性能模拟测试"""
    
    @staticmethod
    def simulate_frame_rendering(num_frames: int = 600) -> List[float]:
        """模拟帧渲染"""
        frame_times = []
        target_frame_time = 16.67  # 60fps = 16.67ms per frame
        
        for i in range(num_frames):
            # 模拟不同的渲染负载
            if i % 100 == 0:  # 每100帧一次重负载
                frame_time = random.uniform(20, 30)
            elif i % 10 == 0:  # 每10帧一次中等负载
                frame_time = random.uniform(15, 20)
            else:  # 正常负载
                frame_time = random.uniform(10, 17)
            
            frame_times.append(frame_time)
            time.sleep(frame_time / 1000)  # 转换为秒
        
        return frame_times
    
    @classmethod
    def run_benchmark(cls, duration_seconds: int = 10) -> BenchmarkResult:
        """运行Flutter性能模拟测试"""
        print(f"\n开始Flutter渲染测试: {duration_seconds}秒")
        
        with performance_monitor() as monitor:
            try:
                num_frames = duration_seconds * 60  # 目标60fps
                frame_times = cls.simulate_frame_rendering(num_frames)
                
                duration, memory, cpu = monitor.stop()
                
                # 计算性能指标
                avg_frame_time = statistics.mean(frame_times)
                actual_fps = 1000 / avg_frame_time
                
                # 计算卡顿(jank) - 超过16.67ms的帧
                jank_frames = sum(1 for t in frame_times if t > 16.67)
                jank_ratio = (jank_frames / len(frame_times)) * 100
                
                # 计算丢帧
                dropped_frames = sum(1 for t in frame_times if t > 33.34)  # 超过2帧时间
                
                return BenchmarkResult(
                    test_name="Flutter渲染",
                    duration_ms=duration,
                    throughput=actual_fps,
                    memory_mb=memory,
                    cpu_percent=cpu,
                    success=actual_fps >= 55,  # 至少55fps
                    details={
                        "平均FPS": f"{actual_fps:.1f}",
                        "平均帧时间": f"{avg_frame_time:.2f}ms",
                        "卡顿比例": f"{jank_ratio:.1f}%",
                        "卡顿帧数": jank_frames,
                        "丢帧数": dropped_frames,
                        "总帧数": len(frame_times),
                        "目标达成": "是" if actual_fps >= 60 else "否"
                    }
                )
                
            except Exception as e:
                duration, memory, cpu = monitor.stop()
                return BenchmarkResult(
                    test_name="Flutter渲染",
                    duration_ms=duration,
                    throughput=0,
                    memory_mb=memory,
                    cpu_percent=cpu,
                    success=False,
                    error=str(e)
                )


# ============================================================================
# 缓存性能测试
# ============================================================================

class CacheBenchmark:
    """缓存性能测试"""
    
    @staticmethod
    def simulate_cache_operations(num_operations: int = 10000) -> Dict:
        """模拟缓存操作"""
        cache = {}
        cache_hits = 0
        cache_misses = 0
        
        # 生成测试键
        keys = [f"key_{i}" for i in range(num_operations // 10)]
        
        operation_times = []
        
        for _ in range(num_operations):
            key = random.choice(keys)
            operation = random.choice(['get', 'set'])
            
            start = time.perf_counter()
            
            if operation == 'get':
                if key in cache:
                    _ = cache[key]
                    cache_hits += 1
                else:
                    cache_misses += 1
                    # 模拟从数据库获取
                    time.sleep(0.001)
                    cache[key] = f"value_{key}"
            else:
                cache[key] = f"value_{random.randint(0, 1000)}"
            
            operation_times.append((time.perf_counter() - start) * 1000)
        
        return {
            "hits": cache_hits,
            "misses": cache_misses,
            "hit_rate": cache_hits / (cache_hits + cache_misses) * 100,
            "operation_times": operation_times
        }
    
    @classmethod
    def run_benchmark(cls, num_operations: int = 10000) -> BenchmarkResult:
        """运行缓存基准测试"""
        print(f"\n开始缓存性能测试: {num_operations}次操作")
        
        with performance_monitor() as monitor:
            try:
                results = cls.simulate_cache_operations(num_operations)
                duration, memory, cpu = monitor.stop()
                
                avg_time = statistics.mean(results["operation_times"])
                p95_time = sorted(results["operation_times"])[int(len(results["operation_times"]) * 0.95)]
                
                return BenchmarkResult(
                    test_name="缓存性能",
                    duration_ms=duration,
                    throughput=num_operations / (duration / 1000),
                    memory_mb=memory,
                    cpu_percent=cpu,
                    success=results["hit_rate"] > 80,
                    details={
                        "操作次数": num_operations,
                        "缓存命中": results["hits"],
                        "缓存未命中": results["misses"],
                        "命中率": f"{results['hit_rate']:.1f}%",
                        "平均操作时间": f"{avg_time:.3f}ms",
                        "P95操作时间": f"{p95_time:.3f}ms"
                    }
                )
                
            except Exception as e:
                duration, memory, cpu = monitor.stop()
                return BenchmarkResult(
                    test_name="缓存性能",
                    duration_ms=duration,
                    throughput=0,
                    memory_mb=memory,
                    cpu_percent=cpu,
                    success=False,
                    error=str(e)
                )


# ============================================================================
# 综合基准测试套件
# ============================================================================

class BenchmarkSuite:
    """综合基准测试套件"""
    
    def __init__(self):
        self.results = []
    
    def run_all_tests(self, quick_mode: bool = False):
        """运行所有测试"""
        print("="*60)
        print("性能基准测试套件")
        print("="*60)
        print(f"系统信息:")
        print(f"  CPU核心: {mp.cpu_count()}")
        print(f"  内存: {psutil.virtual_memory().total / (1024**3):.1f}GB")
        print(f"  Python版本: {sys.version.split()[0]}")
        print("="*60)
        
        # 测试配置
        if quick_mode:
            pdf_files = 20
            sqlite_queries = 100
            compression_size = 10
            flutter_duration = 2
            cache_operations = 1000
        else:
            pdf_files = 200
            sqlite_queries = 1000
            compression_size = 100
            flutter_duration = 10
            cache_operations = 10000
        
        # 运行测试
        tests = [
            ("PDF批处理", PDFBenchmark.run_benchmark, (pdf_files,)),
            ("SQLite查询", SQLiteBenchmark.run_benchmark, (sqlite_queries,)),
            ("数据压缩", CompressionBenchmark.run_benchmark, (compression_size,)),
            ("Flutter渲染", FlutterBenchmark.run_benchmark, (flutter_duration,)),
            ("缓存性能", CacheBenchmark.run_benchmark, (cache_operations,)),
        ]
        
        for test_name, test_func, args in tests:
            try:
                result = test_func(*args)
                self.results.append(result)
                result.print_summary()
            except Exception as e:
                print(f"\n✗ {test_name} 测试失败: {str(e)}")
                self.results.append(BenchmarkResult(
                    test_name=test_name,
                    duration_ms=0,
                    throughput=0,
                    memory_mb=0,
                    cpu_percent=0,
                    success=False,
                    error=str(e)
                ))
    
    def generate_report(self, output_file: str = "benchmark_report.json"):
        """生成测试报告"""
        print("\n" + "="*60)
        print("测试结果汇总")
        print("="*60)
        
        passed = sum(1 for r in self.results if r.success)
        total = len(self.results)
        
        print(f"通过测试: {passed}/{total}")
        print("\n性能目标达成情况:")
        
        for result in self.results:
            if result.test_name == "PDF批处理":
                target_met = result.throughput >= 200
                print(f"  PDF处理: {'✓' if target_met else '✗'} {result.throughput:.0f}文件/小时 (目标: 200)")
            elif result.test_name == "SQLite查询":
                p95 = result.details.get("P95", "N/A")
                target_met = result.success
                print(f"  SQLite查询: {'✓' if target_met else '✗'} P95={p95} (目标: <5ms)")
            elif result.test_name == "Flutter渲染":
                fps = result.details.get("平均FPS", "N/A")
                target_met = result.throughput >= 60
                print(f"  Flutter渲染: {'✓' if target_met else '✗'} {fps}fps (目标: 60fps)")
            elif result.test_name == "数据压缩":
                if HAS_ZSTD and "ZSTD-19_压缩率" in result.details:
                    ratio = result.details["ZSTD-19_压缩率"]
                    target_met = ratio >= 37
                    print(f"  数据压缩: {'✓' if target_met else '✗'} {ratio:.1f}x压缩率 (目标: 37x)")
        
        # 保存JSON报告
        report = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "system": {
                "cpu_cores": mp.cpu_count(),
                "memory_gb": psutil.virtual_memory().total / (1024**3),
                "python_version": sys.version.split()[0]
            },
            "results": [r.to_dict() for r in self.results],
            "summary": {
                "total_tests": total,
                "passed_tests": passed,
                "success_rate": f"{(passed/total)*100:.1f}%"
            }
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"\n报告已保存到: {output_file}")
        print("="*60)


# ============================================================================
# 主程序
# ============================================================================

def main():
    """主程序入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description="性能基准测试套件")
    parser.add_argument("--quick", action="store_true", help="快速模式(减少测试数据量)")
    parser.add_argument("--test", choices=["pdf", "sqlite", "compression", "flutter", "cache", "all"], 
                       default="all", help="选择测试类型")
    parser.add_argument("--output", default="benchmark_report.json", help="输出报告文件名")
    
    args = parser.parse_args()
    
    if args.test == "all":
        suite = BenchmarkSuite()
        suite.run_all_tests(quick_mode=args.quick)
        suite.generate_report(args.output)
    else:
        # 运行单个测试
        if args.test == "pdf":
            result = PDFBenchmark.run_benchmark(20 if args.quick else 200)
        elif args.test == "sqlite":
            result = SQLiteBenchmark.run_benchmark(100 if args.quick else 1000)
        elif args.test == "compression":
            result = CompressionBenchmark.run_benchmark(10 if args.quick else 100)
        elif args.test == "flutter":
            result = FlutterBenchmark.run_benchmark(2 if args.quick else 10)
        elif args.test == "cache":
            result = CacheBenchmark.run_benchmark(1000 if args.quick else 10000)
        
        result.print_summary()
        
        # 保存单个测试结果
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(result.to_dict(), f, indent=2, ensure_ascii=False)
        print(f"\n结果已保存到: {args.output}")


if __name__ == "__main__":
    main()