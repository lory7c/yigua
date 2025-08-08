"""
性能优化和基准测试模块
目标：在3小时内处理3.7GB数据（200+ PDF文档）
提供自动性能调优、基准测试和瓶颈分析
"""

import time
import psutil
import asyncio
import concurrent.futures
import multiprocessing
import threading
import logging
import json
import statistics
from typing import Dict, List, Any, Optional, Callable, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
import resource
import gc
import platform
import sys
from collections import defaultdict, deque

from .config import ETLConfig
from .models import ProcessingMetrics
from .monitoring import MetricsCollector


@dataclass
class BenchmarkResult:
    """基准测试结果"""
    test_name: str
    duration_seconds: float
    throughput_files_per_sec: float
    throughput_mb_per_sec: float
    memory_peak_mb: float
    cpu_usage_avg: float
    success_rate: float
    error_count: int = 0
    configuration: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def performance_score(self) -> float:
        """性能评分（0-100）"""
        # 综合评分算法
        throughput_score = min(100, (self.throughput_files_per_sec / 2.0) * 100)  # 2 files/sec为满分
        success_score = self.success_rate * 100
        efficiency_score = min(100, (1.0 / max(0.1, self.cpu_usage_avg / 100)) * 50)
        
        return (throughput_score * 0.5 + success_score * 0.3 + efficiency_score * 0.2)


@dataclass
class SystemProfile:
    """系统性能画像"""
    cpu_count: int
    memory_total_gb: float
    disk_type: str  # SSD/HDD
    python_version: str
    platform_info: str
    available_memory_gb: float
    cpu_frequency_ghz: float
    
    # 性能基线
    cpu_baseline_score: float = 0.0
    memory_baseline_score: float = 0.0
    disk_baseline_score: float = 0.0
    
    @classmethod
    def create_current_profile(cls) -> 'SystemProfile':
        """创建当前系统性能画像"""
        memory = psutil.virtual_memory()
        cpu_freq = psutil.cpu_freq()
        
        return cls(
            cpu_count=multiprocessing.cpu_count(),
            memory_total_gb=memory.total / 1024**3,
            disk_type=cls._detect_disk_type(),
            python_version=sys.version,
            platform_info=platform.platform(),
            available_memory_gb=memory.available / 1024**3,
            cpu_frequency_ghz=cpu_freq.current / 1000 if cpu_freq else 0.0
        )
    
    @staticmethod
    def _detect_disk_type() -> str:
        """检测磁盘类型"""
        try:
            # 简化的磁盘类型检测
            disk_usage = psutil.disk_usage('/')
            # 在实际环境中可以通过更复杂的方法检测SSD/HDD
            return "SSD"  # 默认假设为SSD
        except:
            return "Unknown"


class PerformanceProfiler:
    """性能分析器"""
    
    def __init__(self, sampling_interval: float = 0.1):
        self.sampling_interval = sampling_interval
        self.logger = logging.getLogger(__name__)
        
        # 性能数据收集
        self.cpu_samples = deque(maxlen=1000)
        self.memory_samples = deque(maxlen=1000)
        self.io_samples = deque(maxlen=1000)
        
        # 监控状态
        self._monitoring = False
        self._monitor_thread = None
        self._start_time = None
        
    def start_profiling(self):
        """开始性能分析"""
        if self._monitoring:
            return
        
        self._monitoring = True
        self._start_time = time.time()
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
        
        self.logger.info("性能分析已启动")
    
    def stop_profiling(self) -> Dict[str, Any]:
        """停止性能分析并返回结果"""
        if not self._monitoring:
            return {}
        
        self._monitoring = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=1)
        
        # 分析收集的数据
        results = self._analyze_performance_data()
        
        self.logger.info("性能分析已停止")
        return results
    
    def _monitor_loop(self):
        """监控循环"""
        while self._monitoring:
            try:
                # 采集CPU使用率
                cpu_percent = psutil.cpu_percent(interval=None)
                self.cpu_samples.append({
                    'timestamp': time.time(),
                    'value': cpu_percent
                })
                
                # 采集内存使用
                memory = psutil.virtual_memory()
                self.memory_samples.append({
                    'timestamp': time.time(),
                    'used_mb': memory.used / 1024**2,
                    'percent': memory.percent
                })
                
                # 采集IO统计
                try:
                    io_stats = psutil.disk_io_counters()
                    self.io_samples.append({
                        'timestamp': time.time(),
                        'read_bytes': io_stats.read_bytes,
                        'write_bytes': io_stats.write_bytes
                    })
                except:
                    pass
                
                time.sleep(self.sampling_interval)
                
            except Exception as e:
                self.logger.error(f"性能监控异常: {e}")
                time.sleep(1)
    
    def _analyze_performance_data(self) -> Dict[str, Any]:
        """分析性能数据"""
        if not self.cpu_samples:
            return {}
        
        # CPU分析
        cpu_values = [sample['value'] for sample in self.cpu_samples]
        cpu_analysis = {
            'average': statistics.mean(cpu_values),
            'peak': max(cpu_values),
            'min': min(cpu_values),
            'std_dev': statistics.stdev(cpu_values) if len(cpu_values) > 1 else 0
        }
        
        # 内存分析
        memory_values = [sample['percent'] for sample in self.memory_samples]
        memory_mb_values = [sample['used_mb'] for sample in self.memory_samples]
        memory_analysis = {
            'average_percent': statistics.mean(memory_values),
            'peak_percent': max(memory_values),
            'average_mb': statistics.mean(memory_mb_values),
            'peak_mb': max(memory_mb_values)
        }
        
        # IO分析
        io_analysis = {}
        if len(self.io_samples) > 1:
            first_sample = self.io_samples[0]
            last_sample = self.io_samples[-1]
            duration = last_sample['timestamp'] - first_sample['timestamp']
            
            if duration > 0:
                read_rate = (last_sample['read_bytes'] - first_sample['read_bytes']) / duration
                write_rate = (last_sample['write_bytes'] - first_sample['write_bytes']) / duration
                
                io_analysis = {
                    'read_mb_per_sec': read_rate / 1024**2,
                    'write_mb_per_sec': write_rate / 1024**2,
                    'total_io_mb_per_sec': (read_rate + write_rate) / 1024**2
                }
        
        return {
            'duration_seconds': time.time() - self._start_time if self._start_time else 0,
            'cpu_analysis': cpu_analysis,
            'memory_analysis': memory_analysis,
            'io_analysis': io_analysis,
            'sample_counts': {
                'cpu_samples': len(self.cpu_samples),
                'memory_samples': len(self.memory_samples),
                'io_samples': len(self.io_samples)
            }
        }


class BenchmarkSuite:
    """基准测试套件"""
    
    def __init__(self, config: ETLConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # 系统信息
        self.system_profile = SystemProfile.create_current_profile()
        
        # 测试配置
        self.test_data_dir = self.config.OUTPUT_DIR / "benchmark_data"
        self.results_dir = self.config.OUTPUT_DIR / "benchmark_results"
        
        # 确保目录存在
        self.test_data_dir.mkdir(parents=True, exist_ok=True)
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
        # 基准测试结果
        self.benchmark_results: List[BenchmarkResult] = []
    
    def run_full_benchmark_suite(self, test_files: List[Path] = None) -> Dict[str, Any]:
        """运行完整基准测试套件"""
        self.logger.info("开始完整基准测试套件")
        
        if test_files is None:
            test_files = self._create_test_data()
        
        # 测试配置矩阵
        test_configurations = [
            {"batch_size": 5, "workers": 2, "strategy": "sequential"},
            {"batch_size": 10, "workers": 4, "strategy": "threading"},
            {"batch_size": 15, "workers": 4, "strategy": "multiprocessing"},
            {"batch_size": 20, "workers": 6, "strategy": "async"},
            {"batch_size": 25, "workers": 8, "strategy": "hybrid"},
        ]
        
        best_result = None
        best_score = 0.0
        
        for config in test_configurations:
            try:
                self.logger.info(f"测试配置: {config}")
                
                result = self._run_single_benchmark(
                    test_name=f"config_{len(self.benchmark_results)}",
                    test_files=test_files,
                    configuration=config
                )
                
                self.benchmark_results.append(result)
                
                if result.performance_score > best_score:
                    best_score = result.performance_score
                    best_result = result
                
                self.logger.info(f"测试完成，性能评分: {result.performance_score:.2f}")
                
                # 强制垃圾回收
                gc.collect()
                time.sleep(2)  # 冷却时间
                
            except Exception as e:
                self.logger.error(f"基准测试失败 {config}: {e}")
        
        # 生成测试报告
        report = self._generate_benchmark_report(best_result)
        
        # 保存结果
        self._save_benchmark_results(report)
        
        return report
    
    def _create_test_data(self) -> List[Path]:
        """创建测试数据"""
        test_files = []
        
        # 创建不同大小的测试文件
        test_sizes = [
            (10, "small"),    # 10KB 小文件
            (100, "medium"),  # 100KB 中文件  
            (500, "large"),   # 500KB 大文件
            (1000, "xlarge") # 1MB 超大文件
        ]
        
        for size_kb, size_label in test_sizes:
            for i in range(5):  # 每种大小创建5个文件
                filename = f"test_{size_label}_{i+1}.pdf"
                file_path = self.test_data_dir / filename
                
                # 创建模拟PDF内容
                content = self._generate_test_content(size_kb * 1024)
                file_path.write_bytes(content)
                
                test_files.append(file_path)
        
        self.logger.info(f"创建了 {len(test_files)} 个测试文件")
        return test_files
    
    def _generate_test_content(self, size_bytes: int) -> bytes:
        """生成测试内容"""
        # 简单的重复内容生成
        base_content = b"This is test content for PDF processing benchmark. " * 100
        
        # 重复内容直到达到目标大小
        content = base_content
        while len(content) < size_bytes:
            content += base_content
        
        return content[:size_bytes]
    
    def _run_single_benchmark(self, test_name: str, test_files: List[Path], configuration: Dict[str, Any]) -> BenchmarkResult:
        """运行单个基准测试"""
        
        # 启动性能分析
        profiler = PerformanceProfiler(sampling_interval=0.1)
        profiler.start_profiling()
        
        start_time = time.time()
        successful_files = 0
        error_count = 0
        total_size_mb = 0
        
        try:
            # 计算总文件大小
            for file_path in test_files:
                try:
                    total_size_mb += file_path.stat().st_size / 1024**2
                except:
                    pass
            
            # 根据配置选择处理策略
            strategy = configuration.get("strategy", "sequential")
            
            if strategy == "sequential":
                successful_files, error_count = self._benchmark_sequential(test_files, configuration)
            elif strategy == "threading":
                successful_files, error_count = self._benchmark_threading(test_files, configuration)
            elif strategy == "multiprocessing":
                successful_files, error_count = self._benchmark_multiprocessing(test_files, configuration)
            elif strategy == "async":
                successful_files, error_count = self._benchmark_async(test_files, configuration)
            elif strategy == "hybrid":
                successful_files, error_count = self._benchmark_hybrid(test_files, configuration)
            else:
                raise ValueError(f"未知的处理策略: {strategy}")
            
        except Exception as e:
            self.logger.error(f"基准测试执行失败: {e}")
            error_count = len(test_files)
            successful_files = 0
        
        # 停止性能分析
        performance_data = profiler.stop_profiling()
        
        end_time = time.time()
        duration = end_time - start_time
        
        # 计算指标
        throughput_files_per_sec = successful_files / duration if duration > 0 else 0
        throughput_mb_per_sec = total_size_mb / duration if duration > 0 else 0
        success_rate = successful_files / len(test_files) if test_files else 0
        
        # 从性能数据中提取指标
        memory_peak_mb = performance_data.get('memory_analysis', {}).get('peak_mb', 0)
        cpu_usage_avg = performance_data.get('cpu_analysis', {}).get('average', 0)
        
        return BenchmarkResult(
            test_name=test_name,
            duration_seconds=duration,
            throughput_files_per_sec=throughput_files_per_sec,
            throughput_mb_per_sec=throughput_mb_per_sec,
            memory_peak_mb=memory_peak_mb,
            cpu_usage_avg=cpu_usage_avg,
            success_rate=success_rate,
            error_count=error_count,
            configuration=configuration,
            metadata={
                'total_files': len(test_files),
                'total_size_mb': total_size_mb,
                'performance_data': performance_data
            }
        )
    
    def _benchmark_sequential(self, test_files: List[Path], config: Dict[str, Any]) -> Tuple[int, int]:
        """顺序处理基准测试"""
        successful = 0
        errors = 0
        
        for file_path in test_files:
            try:
                self._mock_process_file(file_path)
                successful += 1
            except Exception as e:
                errors += 1
                self.logger.debug(f"处理文件失败 {file_path}: {e}")
        
        return successful, errors
    
    def _benchmark_threading(self, test_files: List[Path], config: Dict[str, Any]) -> Tuple[int, int]:
        """多线程处理基准测试"""
        successful = 0
        errors = 0
        max_workers = config.get("workers", 4)
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_file = {
                executor.submit(self._mock_process_file, file_path): file_path
                for file_path in test_files
            }
            
            for future in concurrent.futures.as_completed(future_to_file):
                try:
                    future.result()
                    successful += 1
                except Exception as e:
                    errors += 1
                    file_path = future_to_file[future]
                    self.logger.debug(f"处理文件失败 {file_path}: {e}")
        
        return successful, errors
    
    def _benchmark_multiprocessing(self, test_files: List[Path], config: Dict[str, Any]) -> Tuple[int, int]:
        """多进程处理基准测试"""
        successful = 0
        errors = 0
        max_workers = config.get("workers", 4)
        
        with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
            future_to_file = {
                executor.submit(self._mock_process_file_static, file_path): file_path
                for file_path in test_files
            }
            
            for future in concurrent.futures.as_completed(future_to_file):
                try:
                    future.result()
                    successful += 1
                except Exception as e:
                    errors += 1
                    file_path = future_to_file[future]
                    self.logger.debug(f"处理文件失败 {file_path}: {e}")
        
        return successful, errors
    
    async def _benchmark_async(self, test_files: List[Path], config: Dict[str, Any]) -> Tuple[int, int]:
        """异步处理基准测试"""
        successful = 0
        errors = 0
        max_workers = config.get("workers", 4)
        semaphore = asyncio.Semaphore(max_workers)
        
        async def process_with_semaphore(file_path):
            async with semaphore:
                return await self._mock_process_file_async(file_path)
        
        tasks = [process_with_semaphore(file_path) for file_path in test_files]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, Exception):
                errors += 1
            else:
                successful += 1
        
        return successful, errors
    
    def _benchmark_hybrid(self, test_files: List[Path], config: Dict[str, Any]) -> Tuple[int, int]:
        """混合策略基准测试"""
        # 结合异步和线程池的混合策略
        return asyncio.run(self._benchmark_async(test_files, config))
    
    def _mock_process_file(self, file_path: Path):
        """模拟文件处理"""
        # 模拟PDF处理的CPU和IO操作
        file_size = file_path.stat().st_size
        
        # 模拟CPU密集操作
        processing_time = (file_size / 1024**2) * 0.01  # 每MB处理10ms
        time.sleep(processing_time)
        
        # 模拟内存使用
        temp_data = b'x' * min(file_size, 1024*1024)  # 最多1MB临时数据
        del temp_data
        
        # 随机失败模拟（5%失败率）
        import random
        if random.random() < 0.05:
            raise Exception("模拟处理失败")
        
        return f"Processed: {file_path.name}"
    
    @staticmethod
    def _mock_process_file_static(file_path: Path):
        """静态方法版本的模拟文件处理（用于多进程）"""
        file_size = file_path.stat().st_size
        processing_time = (file_size / 1024**2) * 0.01
        time.sleep(processing_time)
        
        import random
        if random.random() < 0.05:
            raise Exception("模拟处理失败")
        
        return f"Processed: {file_path.name}"
    
    async def _mock_process_file_async(self, file_path: Path):
        """异步版本的模拟文件处理"""
        file_size = file_path.stat().st_size
        processing_time = (file_size / 1024**2) * 0.01
        await asyncio.sleep(processing_time)
        
        import random
        if random.random() < 0.05:
            raise Exception("模拟处理失败")
        
        return f"Processed: {file_path.name}"
    
    def _generate_benchmark_report(self, best_result: Optional[BenchmarkResult]) -> Dict[str, Any]:
        """生成基准测试报告"""
        if not self.benchmark_results:
            return {"error": "没有基准测试结果"}
        
        # 排序结果（按性能评分）
        sorted_results = sorted(self.benchmark_results, key=lambda r: r.performance_score, reverse=True)
        
        # 计算统计信息
        scores = [r.performance_score for r in self.benchmark_results]
        throughputs = [r.throughput_files_per_sec for r in self.benchmark_results]
        
        report = {
            "test_summary": {
                "total_tests": len(self.benchmark_results),
                "best_performance_score": max(scores),
                "average_performance_score": statistics.mean(scores),
                "performance_score_std": statistics.stdev(scores) if len(scores) > 1 else 0,
                "best_throughput": max(throughputs),
                "average_throughput": statistics.mean(throughputs)
            },
            
            "system_profile": {
                "cpu_count": self.system_profile.cpu_count,
                "memory_total_gb": self.system_profile.memory_total_gb,
                "disk_type": self.system_profile.disk_type,
                "python_version": self.system_profile.python_version.split()[0],
                "platform": self.system_profile.platform_info
            },
            
            "best_configuration": best_result.configuration if best_result else None,
            "best_result": {
                "performance_score": best_result.performance_score,
                "throughput_files_per_sec": best_result.throughput_files_per_sec,
                "throughput_mb_per_sec": best_result.throughput_mb_per_sec,
                "memory_peak_mb": best_result.memory_peak_mb,
                "cpu_usage_avg": best_result.cpu_usage_avg,
                "success_rate": best_result.success_rate
            } if best_result else None,
            
            "all_results": [
                {
                    "test_name": r.test_name,
                    "performance_score": r.performance_score,
                    "throughput_files_per_sec": r.throughput_files_per_sec,
                    "configuration": r.configuration
                }
                for r in sorted_results
            ],
            
            "recommendations": self._generate_recommendations(best_result),
            "target_analysis": self._analyze_target_achievement(best_result)
        }
        
        return report
    
    def _generate_recommendations(self, best_result: Optional[BenchmarkResult]) -> List[str]:
        """生成优化建议"""
        recommendations = []
        
        if not best_result:
            return ["无法生成建议：没有有效的测试结果"]
        
        # 基于最佳结果的建议
        best_config = best_result.configuration
        
        if best_result.performance_score < 60:
            recommendations.append("整体性能较低，建议检查系统资源和处理算法")
        
        if best_result.cpu_usage_avg < 50:
            recommendations.append("CPU使用率较低，可以增加并发度")
        elif best_result.cpu_usage_avg > 90:
            recommendations.append("CPU使用率过高，建议减少并发度或优化算法")
        
        if best_result.memory_peak_mb > self.system_profile.memory_total_gb * 1024 * 0.8:
            recommendations.append("内存使用接近系统限制，建议减少批处理大小")
        
        if best_result.success_rate < 0.95:
            recommendations.append("成功率较低，建议加强错误处理和重试机制")
        
        # 策略建议
        strategy = best_config.get("strategy", "unknown")
        recommendations.append(f"推荐使用 {strategy} 处理策略，批大小: {best_config.get('batch_size', 'N/A')}")
        
        return recommendations
    
    def _analyze_target_achievement(self, best_result: Optional[BenchmarkResult]) -> Dict[str, Any]:
        """分析目标达成情况"""
        target_time_hours = 3.0
        target_size_gb = 3.7
        target_files = 200
        
        if not best_result:
            return {"status": "无法分析", "reason": "没有测试结果"}
        
        # 预测实际性能
        predicted_time_hours = target_files / (best_result.throughput_files_per_sec * 3600)
        predicted_size_processing = target_size_gb / (best_result.throughput_mb_per_sec * 3600) if best_result.throughput_mb_per_sec > 0 else float('inf')
        
        analysis = {
            "target_time_hours": target_time_hours,
            "predicted_time_hours": predicted_time_hours,
            "time_target_achievable": predicted_time_hours <= target_time_hours,
            
            "target_throughput_files_per_sec": target_files / (target_time_hours * 3600),
            "actual_throughput_files_per_sec": best_result.throughput_files_per_sec,
            "throughput_gap": best_result.throughput_files_per_sec - (target_files / (target_time_hours * 3600)),
            
            "performance_multiplier_needed": (target_files / (target_time_hours * 3600)) / best_result.throughput_files_per_sec if best_result.throughput_files_per_sec > 0 else float('inf'),
            
            "recommendations_for_target": []
        }
        
        if not analysis["time_target_achievable"]:
            needed_improvement = analysis["performance_multiplier_needed"]
            analysis["recommendations_for_target"].append(f"需要提升 {needed_improvement:.2f}x 的处理性能才能达到目标")
            
            if needed_improvement < 2:
                analysis["recommendations_for_target"].append("可通过增加并发度和优化算法达到目标")
            elif needed_improvement < 5:
                analysis["recommendations_for_target"].append("需要显著优化处理流程或增加硬件资源")
            else:
                analysis["recommendations_for_target"].append("目标可能不现实，需要重新评估或大幅改进架构")
        else:
            analysis["recommendations_for_target"].append("当前性能可以达到目标要求")
        
        return analysis
    
    def _save_benchmark_results(self, report: Dict[str, Any]):
        """保存基准测试结果"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = self.results_dir / f"benchmark_report_{timestamp}.json"
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False, default=str)
        
        self.logger.info(f"基准测试报告已保存: {report_file}")


class AutoPerformanceTuner:
    """自动性能调优器"""
    
    def __init__(self, config: ETLConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # 调优历史
        self.tuning_history = []
        
        # 当前最佳配置
        self.best_configuration = None
        self.best_score = 0.0
    
    def auto_tune_performance(self, test_files: List[Path] = None, iterations: int = 10) -> Dict[str, Any]:
        """自动性能调优"""
        self.logger.info(f"开始自动性能调优，迭代次数: {iterations}")
        
        # 如果没有测试文件，创建小规模测试数据
        if test_files is None:
            benchmark_suite = BenchmarkSuite(self.config)
            test_files = benchmark_suite._create_test_data()[:10]  # 使用少量文件进行调优
        
        # 初始化搜索空间
        search_space = self._define_search_space()
        
        # 使用网格搜索进行调优
        best_config, best_score = self._grid_search_optimization(test_files, search_space, iterations)
        
        # 保存最佳配置
        self.best_configuration = best_config
        self.best_score = best_score
        
        tuning_result = {
            "status": "completed",
            "best_configuration": best_config,
            "best_performance_score": best_score,
            "iterations_completed": len(self.tuning_history),
            "tuning_history": self.tuning_history,
            "recommendations": self._generate_tuning_recommendations(best_config)
        }
        
        self.logger.info(f"自动调优完成，最佳性能评分: {best_score:.2f}")
        
        return tuning_result
    
    def _define_search_space(self) -> Dict[str, List[Any]]:
        """定义搜索空间"""
        return {
            "batch_size": [5, 10, 15, 20, 25],
            "workers": [2, 4, 6, 8],
            "strategy": ["threading", "multiprocessing", "async"],
            # 可以添加更多参数
            "memory_limit_mb": [512, 1024, 2048],
            "use_cache": [True, False]
        }
    
    def _grid_search_optimization(self, test_files: List[Path], search_space: Dict[str, List[Any]], max_iterations: int) -> Tuple[Dict[str, Any], float]:
        """网格搜索优化"""
        import itertools
        
        # 生成参数组合
        param_names = list(search_space.keys())
        param_values = list(search_space.values())
        
        all_combinations = list(itertools.product(*param_values))
        
        # 限制搜索次数
        if len(all_combinations) > max_iterations:
            import random
            combinations_to_test = random.sample(all_combinations, max_iterations)
        else:
            combinations_to_test = all_combinations
        
        best_config = None
        best_score = 0.0
        
        for i, combination in enumerate(combinations_to_test):
            config = dict(zip(param_names, combination))
            
            self.logger.info(f"测试配置 {i+1}/{len(combinations_to_test)}: {config}")
            
            try:
                # 运行基准测试
                benchmark_suite = BenchmarkSuite(self.config)
                result = benchmark_suite._run_single_benchmark(
                    test_name=f"auto_tune_{i}",
                    test_files=test_files,
                    configuration=config
                )
                
                score = result.performance_score
                
                # 记录调优历史
                self.tuning_history.append({
                    "iteration": i,
                    "configuration": config,
                    "performance_score": score,
                    "throughput": result.throughput_files_per_sec,
                    "memory_peak": result.memory_peak_mb,
                    "success_rate": result.success_rate
                })
                
                # 更新最佳配置
                if score > best_score:
                    best_score = score
                    best_config = config
                    self.logger.info(f"发现更佳配置，性能评分: {score:.2f}")
                
            except Exception as e:
                self.logger.error(f"配置测试失败 {config}: {e}")
        
        return best_config, best_score
    
    def _generate_tuning_recommendations(self, best_config: Dict[str, Any]) -> List[str]:
        """生成调优建议"""
        recommendations = []
        
        if not best_config:
            return ["无法生成建议：没有找到最佳配置"]
        
        # 基于最佳配置的建议
        recommendations.append(f"推荐批处理大小: {best_config.get('batch_size', 'N/A')}")
        recommendations.append(f"推荐工作进程数: {best_config.get('workers', 'N/A')}")
        recommendations.append(f"推荐处理策略: {best_config.get('strategy', 'N/A')}")
        
        # 基于调优历史的分析
        if len(self.tuning_history) > 3:
            scores = [h["performance_score"] for h in self.tuning_history]
            score_variance = statistics.stdev(scores) if len(scores) > 1 else 0
            
            if score_variance < 5:
                recommendations.append("性能评分变化较小，当前配置已接近最优")
            else:
                recommendations.append("性能评分变化较大，可能还有进一步优化空间")
        
        return recommendations


# =============================================================================
# 使用示例和主函数
# =============================================================================

def run_performance_analysis(config: ETLConfig = None) -> Dict[str, Any]:
    """运行完整的性能分析"""
    if config is None:
        config = ETLConfig()
    
    logger = logging.getLogger(__name__)
    
    # 1. 运行基准测试套件
    logger.info("=" * 60)
    logger.info("开始基准测试套件")
    logger.info("=" * 60)
    
    benchmark_suite = BenchmarkSuite(config)
    benchmark_report = benchmark_suite.run_full_benchmark_suite()
    
    # 2. 运行自动调优
    logger.info("=" * 60)
    logger.info("开始自动性能调优")
    logger.info("=" * 60)
    
    auto_tuner = AutoPerformanceTuner(config)
    tuning_report = auto_tuner.auto_tune_performance(iterations=5)
    
    # 3. 综合分析报告
    comprehensive_report = {
        "timestamp": datetime.now().isoformat(),
        "benchmark_results": benchmark_report,
        "auto_tuning_results": tuning_report,
        
        "final_recommendations": [
            "基于基准测试和自动调优的综合建议:",
            f"最佳处理策略: {tuning_report.get('best_configuration', {}).get('strategy', 'N/A')}",
            f"推荐批大小: {tuning_report.get('best_configuration', {}).get('batch_size', 'N/A')}",
            f"推荐工作进程数: {tuning_report.get('best_configuration', {}).get('workers', 'N/A')}",
            f"预期性能评分: {tuning_report.get('best_performance_score', 0):.2f}",
            
            "要达到3小时处理3.7GB目标，需要:",
            "- 持续监控和优化处理流程",
            "- 考虑硬件升级或分布式处理",
            "- 实施缓存和增量处理策略"
        ]
    }
    
    logger.info("=" * 60)
    logger.info("性能分析完成")
    logger.info(f"最佳性能评分: {tuning_report.get('best_performance_score', 0):.2f}")
    logger.info("=" * 60)
    
    return comprehensive_report


if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 运行性能分析
    config = ETLConfig()
    
    try:
        report = run_performance_analysis(config)
        
        # 保存综合报告
        report_file = config.OUTPUT_DIR / "performance_analysis_report.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"\n性能分析报告已保存: {report_file}")
        
        # 打印关键指标
        best_score = report["auto_tuning_results"].get("best_performance_score", 0)
        print(f"最佳性能评分: {best_score:.2f}/100")
        
        target_analysis = report["benchmark_results"].get("target_analysis", {})
        if target_analysis.get("time_target_achievable"):
            print("✅ 能够达到3小时处理目标")
        else:
            print("❌ 无法达到3小时处理目标")
            needed = target_analysis.get("performance_multiplier_needed", 0)
            print(f"需要 {needed:.2f}x 性能提升")
        
    except Exception as e:
        print(f"性能分析失败: {e}")
        import traceback
        traceback.print_exc()