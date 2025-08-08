"""
批处理优化器
实现并行处理、内存管理、性能优化等策略
目标：在3小时内处理3.7GB数据（200+PDF文档）
"""

import asyncio
import concurrent.futures
import multiprocessing
import threading
import psutil
import gc
import time
import logging
from typing import List, Dict, Any, Optional, Callable, Iterator, Tuple
from dataclasses import dataclass, field
from pathlib import Path
from queue import Queue, PriorityQueue
import heapq
from collections import deque
import resource
import os
import math

from .config import ETLConfig
from .error_handling import ErrorHandler, safe_operation, RetryConfig, RetryStrategy
from .models import TextExtraction, ProcessedContent


@dataclass
class ProcessingMetrics:
    """处理指标"""
    start_time: float = 0.0
    end_time: float = 0.0
    total_files: int = 0
    processed_files: int = 0
    failed_files: int = 0
    total_size_mb: float = 0.0
    processed_size_mb: float = 0.0
    memory_peak_mb: float = 0.0
    cpu_usage_avg: float = 0.0
    throughput_mb_per_sec: float = 0.0
    throughput_files_per_sec: float = 0.0
    
    @property
    def processing_time(self) -> float:
        return self.end_time - self.start_time if self.end_time > self.start_time else 0.0
    
    @property
    def success_rate(self) -> float:
        return (self.processed_files / self.total_files * 100) if self.total_files > 0 else 0.0


@dataclass
class BatchConfig:
    """批处理配置"""
    # 基础配置
    batch_size: int = 10
    max_workers: int = 4
    max_memory_mb: int = 2048
    max_processing_time_hours: float = 3.0
    
    # 并行策略
    use_multiprocessing: bool = True
    use_async_processing: bool = True
    use_thread_pool: bool = True
    
    # 内存管理
    memory_check_interval: int = 5  # 秒
    memory_warning_threshold: float = 0.8  # 80%
    memory_critical_threshold: float = 0.95  # 95%
    force_gc_interval: int = 100  # 处理100个文件后强制GC
    
    # 动态调整
    adaptive_batch_size: bool = True
    performance_monitoring: bool = True
    auto_scaling: bool = True
    
    # 优先级处理
    use_priority_queue: bool = True
    priority_by_size: bool = True  # True: 小文件优先, False: 大文件优先


class MemoryMonitor:
    """内存监控器"""
    
    def __init__(self, config: BatchConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.monitoring = False
        self.memory_history = deque(maxlen=60)  # 保存最近60个检查点
        self._monitor_thread = None
    
    def start_monitoring(self):
        """开始内存监控"""
        if self.monitoring:
            return
        
        self.monitoring = True
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
        self.logger.info("内存监控已启动")
    
    def stop_monitoring(self):
        """停止内存监控"""
        self.monitoring = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=1)
        self.logger.info("内存监控已停止")
    
    def _monitor_loop(self):
        """监控循环"""
        while self.monitoring:
            try:
                memory_info = self.get_memory_info()
                self.memory_history.append({
                    'timestamp': time.time(),
                    'memory_percent': memory_info['memory_percent'],
                    'memory_used_mb': memory_info['memory_used_mb'],
                    'memory_available_mb': memory_info['memory_available_mb']
                })
                
                # 检查内存阈值
                if memory_info['memory_percent'] > self.config.memory_critical_threshold * 100:
                    self.logger.critical(f"内存使用超过临界阈值: {memory_info['memory_percent']:.1f}%")
                    self._trigger_emergency_gc()
                elif memory_info['memory_percent'] > self.config.memory_warning_threshold * 100:
                    self.logger.warning(f"内存使用超过警告阈值: {memory_info['memory_percent']:.1f}%")
                
                time.sleep(self.config.memory_check_interval)
                
            except Exception as e:
                self.logger.error(f"内存监控异常: {e}")
                time.sleep(self.config.memory_check_interval)
    
    def get_memory_info(self) -> Dict[str, float]:
        """获取内存信息"""
        memory = psutil.virtual_memory()
        
        return {
            'memory_total_mb': memory.total / 1024 / 1024,
            'memory_used_mb': memory.used / 1024 / 1024,
            'memory_available_mb': memory.available / 1024 / 1024,
            'memory_percent': memory.percent
        }
    
    def _trigger_emergency_gc(self):
        """触发紧急垃圾回收"""
        self.logger.info("执行紧急垃圾回收")
        gc.collect()
        
        # 如果可能，建议减少批处理大小
        return "reduce_batch_size"
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """获取内存统计"""
        if not self.memory_history:
            return {}
        
        memory_values = [h['memory_percent'] for h in self.memory_history]
        
        return {
            'current_memory_percent': memory_values[-1] if memory_values else 0,
            'avg_memory_percent': sum(memory_values) / len(memory_values),
            'peak_memory_percent': max(memory_values),
            'memory_trend': 'increasing' if len(memory_values) > 1 and memory_values[-1] > memory_values[0] else 'stable'
        }


class AdaptiveBatchSizer:
    """自适应批大小调整器"""
    
    def __init__(self, initial_batch_size: int = 10):
        self.current_batch_size = initial_batch_size
        self.performance_history = deque(maxlen=10)
        self.min_batch_size = 1
        self.max_batch_size = 50
        self.logger = logging.getLogger(__name__)
    
    def update_performance(self, processing_time: float, memory_usage: float, success_rate: float):
        """更新性能指标"""
        performance_score = self._calculate_performance_score(processing_time, memory_usage, success_rate)
        
        self.performance_history.append({
            'batch_size': self.current_batch_size,
            'processing_time': processing_time,
            'memory_usage': memory_usage,
            'success_rate': success_rate,
            'performance_score': performance_score,
            'timestamp': time.time()
        })
        
        # 调整批大小
        self._adjust_batch_size()
    
    def _calculate_performance_score(self, processing_time: float, memory_usage: float, success_rate: float) -> float:
        """计算性能分数"""
        # 处理时间分数 (越快越好)
        time_score = max(0, 1.0 - processing_time / 300)  # 假设300秒是基准
        
        # 内存使用分数 (使用率50-70%最理想)
        if memory_usage < 0.5:
            memory_score = memory_usage * 2  # 使用率太低，鼓励提高
        elif memory_usage <= 0.7:
            memory_score = 1.0  # 理想区间
        else:
            memory_score = max(0, 1.0 - (memory_usage - 0.7) * 3)  # 惩罚过高使用率
        
        # 成功率分数
        success_score = success_rate
        
        # 综合分数
        return (time_score * 0.4 + memory_score * 0.3 + success_score * 0.3)
    
    def _adjust_batch_size(self):
        """调整批大小"""
        if len(self.performance_history) < 3:
            return  # 需要足够的历史数据
        
        recent_performances = list(self.performance_history)[-3:]
        current_score = recent_performances[-1]['performance_score']
        
        # 计算趋势
        scores = [p['performance_score'] for p in recent_performances]
        is_improving = scores[-1] > scores[0]
        
        if is_improving:
            # 性能在改善，可以尝试增加批大小
            if current_score > 0.8 and self.current_batch_size < self.max_batch_size:
                self.current_batch_size = min(self.max_batch_size, self.current_batch_size + 2)
                self.logger.info(f"性能良好，增加批大小至 {self.current_batch_size}")
        else:
            # 性能在下降，减少批大小
            if current_score < 0.6 and self.current_batch_size > self.min_batch_size:
                self.current_batch_size = max(self.min_batch_size, self.current_batch_size - 1)
                self.logger.info(f"性能下降，减少批大小至 {self.current_batch_size}")
    
    def get_batch_size(self) -> int:
        """获取当前推荐的批大小"""
        return self.current_batch_size


class PriorityQueue:
    """优先级队列"""
    
    def __init__(self, priority_by_size: bool = True):
        self.queue = []
        self.priority_by_size = priority_by_size
        self.counter = 0  # 用于处理相同优先级的项目
    
    def add_item(self, item: Path, priority: Optional[float] = None):
        """添加项目到队列"""
        if priority is None:
            # 根据文件大小自动计算优先级
            file_size = item.stat().st_size if item.exists() else 0
            if self.priority_by_size:
                priority = -file_size  # 小文件优先（负数，因为heapq是最小堆）
            else:
                priority = file_size   # 大文件优先
        
        heapq.heappush(self.queue, (priority, self.counter, item))
        self.counter += 1
    
    def get_item(self) -> Optional[Path]:
        """获取下一个项目"""
        if not self.queue:
            return None
        
        priority, counter, item = heapq.heappop(self.queue)
        return item
    
    def get_batch(self, batch_size: int) -> List[Path]:
        """获取一批项目"""
        batch = []
        for _ in range(min(batch_size, len(self.queue))):
            item = self.get_item()
            if item is not None:
                batch.append(item)
        return batch
    
    def size(self) -> int:
        """队列大小"""
        return len(self.queue)
    
    def is_empty(self) -> bool:
        """队列是否为空"""
        return len(self.queue) == 0


class BatchProcessor:
    """批处理器"""
    
    def __init__(self, config: BatchConfig = None, error_handler: ErrorHandler = None):
        self.config = config or BatchConfig()
        self.error_handler = error_handler or ErrorHandler()
        self.logger = logging.getLogger(__name__)
        
        # 组件初始化
        self.memory_monitor = MemoryMonitor(self.config)
        self.batch_sizer = AdaptiveBatchSizer(self.config.batch_size)
        self.priority_queue = PriorityQueue(self.config.priority_by_size)
        
        # 处理指标
        self.metrics = ProcessingMetrics()
        
        # 处理器状态
        self.is_processing = False
        self.should_stop = False
    
    async def process_files_batch(self, 
                                 file_paths: List[Path],
                                 processor_func: Callable,
                                 **kwargs) -> List[Any]:
        """批量处理文件"""
        
        self.logger.info(f"开始批量处理 {len(file_paths)} 个文件")
        
        # 初始化指标
        self._initialize_metrics(file_paths)
        
        # 启动监控
        self.memory_monitor.start_monitoring()
        
        try:
            # 填充优先级队列
            self._fill_priority_queue(file_paths)
            
            # 执行批处理
            results = await self._execute_batch_processing(processor_func, **kwargs)
            
            return results
            
        finally:
            # 清理
            self.memory_monitor.stop_monitoring()
            self._finalize_metrics()
            self._log_final_metrics()
    
    def _initialize_metrics(self, file_paths: List[Path]):
        """初始化处理指标"""
        self.metrics = ProcessingMetrics()
        self.metrics.start_time = time.time()
        self.metrics.total_files = len(file_paths)
        
        # 计算总文件大小
        total_size = 0
        for path in file_paths:
            try:
                total_size += path.stat().st_size
            except OSError:
                pass
        
        self.metrics.total_size_mb = total_size / 1024 / 1024
        self.logger.info(f"总文件大小: {self.metrics.total_size_mb:.2f} MB")
    
    def _fill_priority_queue(self, file_paths: List[Path]):
        """填充优先级队列"""
        self.logger.info("初始化优先级队列...")
        
        for path in file_paths:
            self.priority_queue.add_item(path)
        
        self.logger.info(f"队列已填充，共 {self.priority_queue.size()} 个文件")
    
    async def _execute_batch_processing(self, processor_func: Callable, **kwargs) -> List[Any]:
        """执行批处理"""
        
        all_results = []
        processed_count = 0
        
        while not self.priority_queue.is_empty() and not self.should_stop:
            # 获取当前批大小
            current_batch_size = self.batch_sizer.get_batch_size()
            
            # 内存检查
            memory_info = self.memory_monitor.get_memory_info()
            if memory_info['memory_percent'] > self.config.memory_critical_threshold * 100:
                self.logger.warning("内存使用过高，减少批大小")
                current_batch_size = max(1, current_batch_size // 2)
            
            # 获取当前批次
            batch_files = self.priority_queue.get_batch(current_batch_size)
            if not batch_files:
                break
            
            self.logger.info(f"处理批次: {len(batch_files)} 个文件，当前批大小: {current_batch_size}")
            
            # 处理当前批次
            batch_start_time = time.time()
            batch_results = await self._process_single_batch(batch_files, processor_func, **kwargs)
            batch_end_time = time.time()
            
            # 更新结果
            all_results.extend([r for r in batch_results if r is not None])
            processed_count += len(batch_files)
            
            # 更新指标
            batch_processing_time = batch_end_time - batch_start_time
            self.metrics.processed_files = processed_count
            
            # 计算处理的文件大小
            batch_size_mb = sum(f.stat().st_size for f in batch_files if f.exists()) / 1024 / 1024
            self.metrics.processed_size_mb += batch_size_mb
            
            # 更新自适应批大小
            memory_usage = memory_info['memory_percent'] / 100
            success_rate = len([r for r in batch_results if r is not None]) / len(batch_files)
            self.batch_sizer.update_performance(batch_processing_time, memory_usage, success_rate)
            
            # 强制垃圾回收（定期）
            if processed_count % self.config.force_gc_interval == 0:
                self.logger.info("执行垃圾回收")
                gc.collect()
            
            # 检查时间限制
            elapsed_hours = (time.time() - self.metrics.start_time) / 3600
            if elapsed_hours >= self.config.max_processing_time_hours:
                self.logger.warning(f"达到最大处理时间 {self.config.max_processing_time_hours} 小时，停止处理")
                break
            
            # 进度报告
            progress = (processed_count / self.metrics.total_files) * 100
            self.logger.info(f"处理进度: {progress:.1f}% ({processed_count}/{self.metrics.total_files})")
        
        return all_results
    
    async def _process_single_batch(self, batch_files: List[Path], processor_func: Callable, **kwargs) -> List[Any]:
        """处理单个批次"""
        
        if self.config.use_async_processing:
            return await self._async_process_batch(batch_files, processor_func, **kwargs)
        elif self.config.use_multiprocessing:
            return await self._multiprocess_batch(batch_files, processor_func, **kwargs)
        elif self.config.use_thread_pool:
            return await self._thread_pool_batch(batch_files, processor_func, **kwargs)
        else:
            return await self._sequential_process_batch(batch_files, processor_func, **kwargs)
    
    async def _async_process_batch(self, batch_files: List[Path], processor_func: Callable, **kwargs) -> List[Any]:
        """异步处理批次"""
        
        tasks = []
        semaphore = asyncio.Semaphore(self.config.max_workers)
        
        async def process_with_semaphore(file_path):
            async with semaphore:
                try:
                    if asyncio.iscoroutinefunction(processor_func):
                        return await processor_func(file_path, **kwargs)
                    else:
                        # 在线程池中运行同步函数
                        loop = asyncio.get_event_loop()
                        return await loop.run_in_executor(None, processor_func, file_path)
                except Exception as e:
                    self.error_handler.handle_error(e, {'file_path': str(file_path)})
                    return None
        
        tasks = [process_with_semaphore(file_path) for file_path in batch_files]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理异常结果
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                self.logger.error(f"文件 {batch_files[i]} 处理失败: {result}")
                self.metrics.failed_files += 1
                processed_results.append(None)
            else:
                processed_results.append(result)
        
        return processed_results
    
    async def _multiprocess_batch(self, batch_files: List[Path], processor_func: Callable, **kwargs) -> List[Any]:
        """多进程处理批次"""
        
        loop = asyncio.get_event_loop()
        
        with concurrent.futures.ProcessPoolExecutor(max_workers=self.config.max_workers) as executor:
            # 创建任务
            futures = []
            for file_path in batch_files:
                future = loop.run_in_executor(executor, processor_func, file_path)
                futures.append(future)
            
            # 等待完成
            results = await asyncio.gather(*futures, return_exceptions=True)
            
            # 处理结果
            processed_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    self.logger.error(f"文件 {batch_files[i]} 处理失败: {result}")
                    self.metrics.failed_files += 1
                    processed_results.append(None)
                else:
                    processed_results.append(result)
            
            return processed_results
    
    async def _thread_pool_batch(self, batch_files: List[Path], processor_func: Callable, **kwargs) -> List[Any]:
        """线程池处理批次"""
        
        loop = asyncio.get_event_loop()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
            futures = []
            for file_path in batch_files:
                future = loop.run_in_executor(executor, processor_func, file_path)
                futures.append(future)
            
            results = await asyncio.gather(*futures, return_exceptions=True)
            
            processed_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    self.logger.error(f"文件 {batch_files[i]} 处理失败: {result}")
                    self.metrics.failed_files += 1
                    processed_results.append(None)
                else:
                    processed_results.append(result)
            
            return processed_results
    
    async def _sequential_process_batch(self, batch_files: List[Path], processor_func: Callable, **kwargs) -> List[Any]:
        """顺序处理批次"""
        
        results = []
        
        for file_path in batch_files:
            try:
                if asyncio.iscoroutinefunction(processor_func):
                    result = await processor_func(file_path, **kwargs)
                else:
                    result = processor_func(file_path, **kwargs)
                results.append(result)
            except Exception as e:
                self.error_handler.handle_error(e, {'file_path': str(file_path)})
                self.metrics.failed_files += 1
                results.append(None)
        
        return results
    
    def _finalize_metrics(self):
        """完成指标计算"""
        self.metrics.end_time = time.time()
        
        if self.metrics.processing_time > 0:
            self.metrics.throughput_mb_per_sec = self.metrics.processed_size_mb / self.metrics.processing_time
            self.metrics.throughput_files_per_sec = self.metrics.processed_files / self.metrics.processing_time
        
        # 获取内存峰值
        memory_stats = self.memory_monitor.get_memory_stats()
        if memory_stats:
            self.metrics.memory_peak_mb = memory_stats.get('peak_memory_percent', 0) / 100 * psutil.virtual_memory().total / 1024 / 1024
    
    def _log_final_metrics(self):
        """记录最终指标"""
        self.logger.info("=" * 60)
        self.logger.info("批处理完成 - 性能指标:")
        self.logger.info(f"总处理时间: {self.metrics.processing_time:.2f} 秒 ({self.metrics.processing_time/3600:.2f} 小时)")
        self.logger.info(f"处理文件数: {self.metrics.processed_files}/{self.metrics.total_files}")
        self.logger.info(f"成功率: {self.metrics.success_rate:.1f}%")
        self.logger.info(f"处理数据量: {self.metrics.processed_size_mb:.2f}/{self.metrics.total_size_mb:.2f} MB")
        self.logger.info(f"吞吐量: {self.metrics.throughput_mb_per_sec:.2f} MB/s, {self.metrics.throughput_files_per_sec:.2f} 文件/s")
        self.logger.info(f"内存峰值: {self.metrics.memory_peak_mb:.2f} MB")
        
        # 评估是否达到目标
        target_time_hours = 3.0
        target_size_gb = 3.7
        
        if self.metrics.processing_time <= target_time_hours * 3600:
            self.logger.info("✅ 达到时间目标!")
        else:
            self.logger.warning(f"⚠️  超过时间目标 {target_time_hours} 小时")
        
        if self.metrics.processed_size_mb >= target_size_gb * 1024 * 0.95:  # 95%容错
            self.logger.info("✅ 达到数据量目标!")
        else:
            self.logger.warning(f"⚠️  未达到数据量目标 {target_size_gb} GB")
        
        self.logger.info("=" * 60)
    
    def get_metrics(self) -> ProcessingMetrics:
        """获取处理指标"""
        return self.metrics
    
    def stop_processing(self):
        """停止处理"""
        self.should_stop = True
        self.logger.info("收到停止信号，正在安全停止处理...")


# =============================================================================
# 工厂函数
# =============================================================================

def create_optimized_processor(target_time_hours: float = 3.0,
                             target_size_gb: float = 3.7,
                             max_memory_mb: int = 2048) -> BatchProcessor:
    """创建优化的批处理器"""
    
    # 根据目标估算配置
    estimated_files = 200
    avg_file_size_mb = target_size_gb * 1024 / estimated_files
    
    # 动态计算最佳配置
    available_cores = multiprocessing.cpu_count()
    max_workers = min(available_cores, 8)  # 限制最大工作进程数
    
    # 根据文件大小和内存限制计算批大小
    target_batch_memory_mb = max_memory_mb * 0.6  # 60%的内存用于批处理
    estimated_batch_size = max(1, int(target_batch_memory_mb / avg_file_size_mb))
    estimated_batch_size = min(estimated_batch_size, 20)  # 限制最大批大小
    
    config = BatchConfig(
        batch_size=estimated_batch_size,
        max_workers=max_workers,
        max_memory_mb=max_memory_mb,
        max_processing_time_hours=target_time_hours,
        
        # 启用所有优化
        use_multiprocessing=True,
        use_async_processing=True,
        use_thread_pool=True,
        
        # 内存管理
        memory_warning_threshold=0.75,
        memory_critical_threshold=0.90,
        force_gc_interval=50,
        
        # 自适应优化
        adaptive_batch_size=True,
        performance_monitoring=True,
        auto_scaling=True,
        
        # 小文件优先策略
        use_priority_queue=True,
        priority_by_size=True
    )
    
    return BatchProcessor(config)


# =============================================================================
# 使用示例
# =============================================================================

if __name__ == "__main__":
    import asyncio
    from pathlib import Path
    
    async def sample_processor(file_path: Path) -> str:
        """示例处理函数"""
        # 模拟处理时间
        await asyncio.sleep(0.1)
        return f"处理完成: {file_path.name}"
    
    async def main():
        # 创建优化的处理器
        processor = create_optimized_processor(
            target_time_hours=3.0,
            target_size_gb=3.7,
            max_memory_mb=2048
        )
        
        # 模拟文件列表
        sample_files = [Path(f"sample_{i}.pdf") for i in range(50)]
        
        # 执行批处理
        results = await processor.process_files_batch(
            file_paths=sample_files,
            processor_func=sample_processor
        )
        
        print(f"处理完成，结果数量: {len(results)}")
        
        # 获取性能指标
        metrics = processor.get_metrics()
        print(f"处理性能: {metrics.throughput_files_per_sec:.2f} 文件/秒")
    
    # 运行示例
    # asyncio.run(main())