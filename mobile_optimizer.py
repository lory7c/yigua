#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
移动端高性能数据优化器
针对移动设备的内存限制、网络延迟、电池续航进行专门优化

核心功能:
1. 分页加载策略和预加载机制
2. 智能缓存管理和内存优化
3. 数据压缩和增量同步
4. 离线模式和后台同步
5. 电池友好的查询调度
6. 网络状态自适应优化
7. 移动端存储空间管理

性能目标:
- 首屏加载 < 500ms
- 滑动加载延迟 < 100ms  
- 内存使用 < 50MB
- 离线响应 < 50ms
- 后台同步低功耗

作者: Claude
创建时间: 2025-08-07
"""

import sqlite3
import json
import time
import threading
import gzip
import base64
import hashlib
from typing import Dict, List, Tuple, Optional, Any, Callable
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from collections import defaultdict, deque
from contextlib import contextmanager
from enum import Enum
import logging
import weakref


class NetworkStatus(Enum):
    """网络状态"""
    OFFLINE = "offline"
    WIFI = "wifi"
    MOBILE = "mobile"
    SLOW_MOBILE = "slow_mobile"


class CacheStrategy(Enum):
    """缓存策略"""
    AGGRESSIVE = "aggressive"  # 激进缓存，快速响应
    BALANCED = "balanced"      # 平衡模式
    CONSERVATIVE = "conservative"  # 保守模式，节省内存


@dataclass
class PaginationConfig:
    """分页配置"""
    page_size: int = 20
    preload_pages: int = 2
    max_cached_pages: int = 10
    lazy_load_threshold: int = 5  # 剩余多少项时开始预加载


@dataclass
class MobileQuery:
    """移动端查询配置"""
    query: str
    params: tuple
    cache_key: str
    priority: int  # 1-5, 5最高
    expires_at: datetime
    compressed: bool = True
    offline_available: bool = False


@dataclass
class SyncTask:
    """同步任务"""
    task_id: str
    task_type: str  # 'upload', 'download', 'delete'
    data: Dict[str, Any]
    priority: int
    created_at: datetime
    retry_count: int = 0
    max_retries: int = 3


@dataclass
class PerformanceMetrics:
    """移动端性能指标"""
    query_time_ms: float
    cache_hit: bool
    data_size_bytes: int
    compression_ratio: float
    battery_impact: float  # 0-1, 1为高耗电
    network_bytes: int = 0


class MemoryManager:
    """移动端内存管理器"""
    
    def __init__(self, max_memory_mb: int = 50):
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        self.current_usage = 0
        self.cached_objects = {}  # 使用弱引用存储缓存对象
        self._lock = threading.Lock()
    
    def allocate(self, key: str, obj: Any, size_bytes: int) -> bool:
        """分配内存给对象"""
        with self._lock:
            if self.current_usage + size_bytes > self.max_memory_bytes:
                # 尝试清理内存
                self._cleanup_memory()
                
                if self.current_usage + size_bytes > self.max_memory_bytes:
                    return False  # 内存不足
            
            self.cached_objects[key] = weakref.ref(obj)
            self.current_usage += size_bytes
            return True
    
    def deallocate(self, key: str, size_bytes: int) -> None:
        """释放内存"""
        with self._lock:
            if key in self.cached_objects:
                del self.cached_objects[key]
                self.current_usage = max(0, self.current_usage - size_bytes)
    
    def _cleanup_memory(self) -> None:
        """清理无效的弱引用"""
        dead_keys = []
        for key, weak_ref in self.cached_objects.items():
            if weak_ref() is None:
                dead_keys.append(key)
        
        for key in dead_keys:
            del self.cached_objects[key]
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """获取内存使用统计"""
        with self._lock:
            return {
                'current_usage_mb': self.current_usage / 1024 / 1024,
                'max_memory_mb': self.max_memory_bytes / 1024 / 1024,
                'usage_ratio': self.current_usage / self.max_memory_bytes,
                'cached_objects': len(self.cached_objects)
            }


class DataCompressor:
    """数据压缩器"""
    
    @staticmethod
    def compress_json(data: Any) -> str:
        """压缩JSON数据"""
        json_str = json.dumps(data, separators=(',', ':'), ensure_ascii=False)
        compressed = gzip.compress(json_str.encode('utf-8'))
        return base64.b64encode(compressed).decode('ascii')
    
    @staticmethod
    def decompress_json(compressed_data: str) -> Any:
        """解压JSON数据"""
        compressed = base64.b64decode(compressed_data.encode('ascii'))
        json_str = gzip.decompress(compressed).decode('utf-8')
        return json.loads(json_str)
    
    @staticmethod
    def calculate_compression_ratio(original_size: int, compressed_size: int) -> float:
        """计算压缩比"""
        if original_size == 0:
            return 1.0
        return compressed_size / original_size


class PaginatedResultSet:
    """分页结果集"""
    
    def __init__(self, query: str, params: tuple, page_size: int = 20,
                 preload_pages: int = 2):
        self.query = query
        self.params = params
        self.page_size = page_size
        self.preload_pages = preload_pages
        
        self.pages = {}  # page_num -> data
        self.total_count = None
        self.current_page = 0
        self.is_loading = set()  # 正在加载的页码
        
        self._lock = threading.Lock()
    
    def get_page(self, page_num: int) -> List[Any]:
        """获取指定页数据"""
        with self._lock:
            if page_num in self.pages:
                return self.pages[page_num]
            return []
    
    def set_page(self, page_num: int, data: List[Any]) -> None:
        """设置页数据"""
        with self._lock:
            self.pages[page_num] = data
            if page_num in self.is_loading:
                self.is_loading.remove(page_num)
    
    def mark_loading(self, page_num: int) -> None:
        """标记页面正在加载"""
        with self._lock:
            self.is_loading.add(page_num)
    
    def get_loaded_range(self) -> Tuple[int, int]:
        """获取已加载页面范围"""
        with self._lock:
            if not self.pages:
                return (0, 0)
            return (min(self.pages.keys()), max(self.pages.keys()))


class MobileOptimizer:
    """移动端性能优化器"""
    
    def __init__(self, db_path: str, cache_strategy: CacheStrategy = CacheStrategy.BALANCED):
        self.db_path = db_path
        self.cache_strategy = cache_strategy
        
        # 核心组件
        self.memory_manager = MemoryManager()
        self.data_compressor = DataCompressor()
        
        # 缓存和状态管理
        self.query_cache = {}
        self.paginated_results = {}
        self.sync_queue = deque()
        self.pending_queries = {}
        
        # 网络和性能监控
        self.network_status = NetworkStatus.WIFI
        self.performance_metrics = deque(maxlen=1000)
        self.battery_saver_mode = False
        
        # 线程管理
        self.background_sync_thread = None
        self.preload_thread = None
        self._shutdown = False
        
        # 日志设置
        self.logger = logging.getLogger(__name__)
        
        # 启动后台服务
        self._start_background_services()
    
    def _start_background_services(self):
        """启动后台服务"""
        self.background_sync_thread = threading.Thread(
            target=self._background_sync_worker, daemon=True
        )
        self.background_sync_thread.start()
        
        self.preload_thread = threading.Thread(
            target=self._preload_worker, daemon=True
        )
        self.preload_thread.start()
    
    @contextmanager
    def get_connection(self):
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        
        # 移动端优化设置
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA synchronous = NORMAL")
        conn.execute("PRAGMA cache_size = -8000")  # 8MB缓存，适合移动端
        conn.execute("PRAGMA temp_store = MEMORY")
        conn.execute("PRAGMA mmap_size = 67108864")  # 64MB内存映射
        
        try:
            yield conn
        finally:
            conn.close()
    
    def execute_query_paginated(self, query: str, params: tuple = None,
                               pagination_config: PaginationConfig = None) -> str:
        """执行分页查询并返回结果集ID"""
        if pagination_config is None:
            pagination_config = PaginationConfig()
        
        params = params or ()
        result_id = hashlib.md5(f"{query}:{params}".encode()).hexdigest()
        
        # 创建分页结果集
        paginated_result = PaginatedResultSet(
            query=query,
            params=params,
            page_size=pagination_config.page_size,
            preload_pages=pagination_config.preload_pages
        )
        
        self.paginated_results[result_id] = paginated_result
        
        # 异步加载第一页
        self._load_page_async(result_id, 0, high_priority=True)
        
        return result_id
    
    def get_page_data(self, result_id: str, page_num: int) -> Dict[str, Any]:
        """获取分页数据"""
        if result_id not in self.paginated_results:
            return {'error': 'Result set not found'}
        
        paginated_result = self.paginated_results[result_id]
        
        # 检查是否已缓存
        page_data = paginated_result.get_page(page_num)
        if page_data:
            # 触发预加载
            self._trigger_preload(result_id, page_num)
            return {
                'page_num': page_num,
                'data': page_data,
                'cached': True,
                'total_count': paginated_result.total_count
            }
        
        # 如果正在加载，返回加载状态
        if page_num in paginated_result.is_loading:
            return {
                'page_num': page_num,
                'loading': True,
                'cached': False
            }
        
        # 同步加载页面
        self._load_page_sync(result_id, page_num)
        page_data = paginated_result.get_page(page_num)
        
        return {
            'page_num': page_num,
            'data': page_data,
            'cached': False,
            'total_count': paginated_result.total_count
        }
    
    def _load_page_sync(self, result_id: str, page_num: int) -> None:
        """同步加载页面数据"""
        paginated_result = self.paginated_results[result_id]
        paginated_result.mark_loading(page_num)
        
        offset = page_num * paginated_result.page_size
        limit = paginated_result.page_size
        
        # 修改查询添加LIMIT和OFFSET
        paginated_query = f"{paginated_result.query} LIMIT {limit} OFFSET {offset}"
        
        start_time = time.time()
        
        try:
            with self.get_connection() as conn:
                cursor = conn.execute(paginated_query, paginated_result.params)
                results = [dict(row) for row in cursor.fetchall()]
                
                # 如果是第一页，获取总数
                if page_num == 0:
                    count_query = f"SELECT COUNT(*) FROM ({paginated_result.query})"
                    count_cursor = conn.execute(count_query, paginated_result.params)
                    paginated_result.total_count = count_cursor.fetchone()[0]
            
            # 缓存结果
            paginated_result.set_page(page_num, results)
            
            # 记录性能指标
            execution_time_ms = (time.time() - start_time) * 1000
            self._record_performance_metrics(
                execution_time_ms, False, len(json.dumps(results)), 
                self._calculate_battery_impact(execution_time_ms)
            )
            
        except Exception as e:
            self.logger.error(f"加载页面失败 {result_id}:{page_num}: {e}")
            paginated_result.set_page(page_num, [])
    
    def _load_page_async(self, result_id: str, page_num: int, 
                        high_priority: bool = False) -> None:
        """异步加载页面数据"""
        def load_task():
            self._load_page_sync(result_id, page_num)
        
        # 根据优先级和电池模式决定是否立即执行
        if high_priority or not self.battery_saver_mode:
            threading.Thread(target=load_task, daemon=True).start()
        else:
            # 低优先级任务加入队列
            self.sync_queue.append(SyncTask(
                task_id=f"load_{result_id}_{page_num}",
                task_type="load_page",
                data={"result_id": result_id, "page_num": page_num},
                priority=1,
                created_at=datetime.now()
            ))
    
    def _trigger_preload(self, result_id: str, current_page: int) -> None:
        """触发预加载"""
        paginated_result = self.paginated_results[result_id]
        
        # 预加载后续页面
        for i in range(1, paginated_result.preload_pages + 1):
            next_page = current_page + i
            if next_page not in paginated_result.pages and next_page not in paginated_result.is_loading:
                self._load_page_async(result_id, next_page, high_priority=False)
    
    def execute_cached_query(self, query: str, params: tuple = None,
                           cache_ttl_seconds: int = 300) -> Dict[str, Any]:
        """执行带缓存的查询"""
        params = params or ()
        cache_key = hashlib.md5(f"{query}:{params}".encode()).hexdigest()
        
        # 检查缓存
        if cache_key in self.query_cache:
            cached_item = self.query_cache[cache_key]
            if datetime.now() < cached_item['expires_at']:
                # 缓存命中
                self._record_performance_metrics(0, True, cached_item['size'], 0)
                return {
                    'data': cached_item['data'],
                    'cached': True,
                    'cache_key': cache_key
                }
        
        # 执行查询
        start_time = time.time()
        
        try:
            with self.get_connection() as conn:
                cursor = conn.execute(query, params)
                results = [dict(row) for row in cursor.fetchall()]
            
            execution_time_ms = (time.time() - start_time) * 1000
            
            # 数据压缩（可选）
            if self.cache_strategy == CacheStrategy.AGGRESSIVE:
                compressed_data = self.data_compressor.compress_json(results)
                data_size = len(compressed_data)
                cache_data = compressed_data
                is_compressed = True
            else:
                cache_data = results
                data_size = len(json.dumps(results))
                is_compressed = False
            
            # 缓存结果
            cache_item = {
                'data': cache_data,
                'expires_at': datetime.now() + timedelta(seconds=cache_ttl_seconds),
                'size': data_size,
                'compressed': is_compressed,
                'created_at': datetime.now()
            }
            
            # 检查内存限制
            if self.memory_manager.allocate(cache_key, cache_item, data_size):
                self.query_cache[cache_key] = cache_item
            
            # 如果数据被压缩，需要解压返回
            if is_compressed:
                results = self.data_compressor.decompress_json(cache_data)
            
            # 记录性能指标
            self._record_performance_metrics(
                execution_time_ms, False, data_size,
                self._calculate_battery_impact(execution_time_ms)
            )
            
            return {
                'data': results,
                'cached': False,
                'cache_key': cache_key,
                'execution_time_ms': execution_time_ms
            }
            
        except Exception as e:
            self.logger.error(f"查询执行失败: {e}")
            return {'error': str(e)}
    
    def _record_performance_metrics(self, execution_time_ms: float, cache_hit: bool,
                                  data_size: int, battery_impact: float,
                                  network_bytes: int = 0) -> None:
        """记录性能指标"""
        metrics = PerformanceMetrics(
            query_time_ms=execution_time_ms,
            cache_hit=cache_hit,
            data_size_bytes=data_size,
            compression_ratio=1.0,  # 简化
            battery_impact=battery_impact,
            network_bytes=network_bytes
        )
        
        self.performance_metrics.append(metrics)
    
    def _calculate_battery_impact(self, execution_time_ms: float) -> float:
        """计算电池影响评分 (0-1)"""
        # 简化的电池影响计算
        # 执行时间越长，CPU使用越多，电池影响越大
        base_impact = min(execution_time_ms / 1000, 1.0)  # 基于执行时间
        
        # 网络状态影响
        if self.network_status == NetworkStatus.MOBILE:
            base_impact *= 1.5
        elif self.network_status == NetworkStatus.SLOW_MOBILE:
            base_impact *= 2.0
        
        return min(base_impact, 1.0)
    
    def set_network_status(self, status: NetworkStatus) -> None:
        """设置网络状态"""
        self.network_status = status
        self.logger.info(f"网络状态变更为: {status.value}")
        
        # 根据网络状态调整策略
        if status == NetworkStatus.OFFLINE:
            self.battery_saver_mode = True
        elif status == NetworkStatus.SLOW_MOBILE:
            self.cache_strategy = CacheStrategy.AGGRESSIVE
        elif status == NetworkStatus.WIFI:
            self.cache_strategy = CacheStrategy.BALANCED
            self.battery_saver_mode = False
    
    def set_battery_saver_mode(self, enabled: bool) -> None:
        """设置省电模式"""
        self.battery_saver_mode = enabled
        self.logger.info(f"省电模式: {'启用' if enabled else '禁用'}")
        
        if enabled:
            self.cache_strategy = CacheStrategy.CONSERVATIVE
            # 清理低优先级缓存
            self._cleanup_low_priority_cache()
    
    def _cleanup_low_priority_cache(self) -> None:
        """清理低优先级缓存"""
        current_time = datetime.now()
        keys_to_remove = []
        
        for key, item in self.query_cache.items():
            # 移除即将过期的缓存
            if current_time + timedelta(seconds=60) > item['expires_at']:
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            cache_item = self.query_cache.pop(key)
            self.memory_manager.deallocate(key, cache_item['size'])
    
    def add_sync_task(self, task_type: str, data: Dict[str, Any], 
                     priority: int = 3) -> str:
        """添加同步任务"""
        task_id = hashlib.md5(f"{task_type}:{time.time()}".encode()).hexdigest()[:8]
        
        task = SyncTask(
            task_id=task_id,
            task_type=task_type,
            data=data,
            priority=priority,
            created_at=datetime.now()
        )
        
        self.sync_queue.append(task)
        return task_id
    
    def _background_sync_worker(self) -> None:
        """后台同步工作线程"""
        while not self._shutdown:
            try:
                if not self.sync_queue:
                    time.sleep(1)
                    continue
                
                # 按优先级排序
                sorted_tasks = sorted(self.sync_queue, key=lambda t: t.priority, reverse=True)
                self.sync_queue.clear()
                
                for task in sorted_tasks:
                    if self._shutdown:
                        break
                    
                    # 在省电模式下，只处理高优先级任务
                    if self.battery_saver_mode and task.priority < 4:
                        continue
                    
                    self._execute_sync_task(task)
                
            except Exception as e:
                self.logger.error(f"后台同步错误: {e}")
                time.sleep(5)
    
    def _preload_worker(self) -> None:
        """预加载工作线程"""
        while not self._shutdown:
            try:
                # 在省电模式下暂停预加载
                if self.battery_saver_mode:
                    time.sleep(10)
                    continue
                
                # 检查是否有需要预加载的数据
                # 这里可以实现智能预加载逻辑
                time.sleep(2)
                
            except Exception as e:
                self.logger.error(f"预加载错误: {e}")
                time.sleep(5)
    
    def _execute_sync_task(self, task: SyncTask) -> None:
        """执行同步任务"""
        try:
            if task.task_type == "load_page":
                result_id = task.data['result_id']
                page_num = task.data['page_num']
                self._load_page_sync(result_id, page_num)
            
            elif task.task_type == "upload":
                # 实现数据上传逻辑
                self._upload_data(task.data)
            
            elif task.task_type == "download":
                # 实现数据下载逻辑
                self._download_data(task.data)
            
            self.logger.info(f"同步任务完成: {task.task_id}")
            
        except Exception as e:
            task.retry_count += 1
            if task.retry_count < task.max_retries:
                self.sync_queue.append(task)
                self.logger.warning(f"同步任务重试 {task.task_id}: {e}")
            else:
                self.logger.error(f"同步任务失败 {task.task_id}: {e}")
    
    def _upload_data(self, data: Dict[str, Any]) -> None:
        """上传数据到服务器"""
        # 实现具体的上传逻辑
        pass
    
    def _download_data(self, data: Dict[str, Any]) -> None:
        """从服务器下载数据"""
        # 实现具体的下载逻辑
        pass
    
    def get_performance_dashboard(self) -> Dict[str, Any]:
        """获取移动端性能仪表板数据"""
        if not self.performance_metrics:
            return {'error': '没有性能数据'}
        
        metrics_list = list(self.performance_metrics)
        
        # 计算统计数据
        total_queries = len(metrics_list)
        cache_hits = sum(1 for m in metrics_list if m.cache_hit)
        avg_query_time = sum(m.query_time_ms for m in metrics_list) / total_queries
        total_data_size = sum(m.data_size_bytes for m in metrics_list)
        avg_battery_impact = sum(m.battery_impact for m in metrics_list) / total_queries
        
        return {
            'summary': {
                'total_queries': total_queries,
                'cache_hit_rate': cache_hits / total_queries,
                'avg_query_time_ms': avg_query_time,
                'total_data_size_mb': total_data_size / 1024 / 1024,
                'avg_battery_impact': avg_battery_impact
            },
            'memory_stats': self.memory_manager.get_usage_stats(),
            'cache_stats': {
                'cached_queries': len(self.query_cache),
                'paginated_results': len(self.paginated_results)
            },
            'network_status': self.network_status.value,
            'battery_saver_mode': self.battery_saver_mode,
            'sync_queue_size': len(self.sync_queue),
            'recent_performance': [
                {
                    'query_time_ms': m.query_time_ms,
                    'cache_hit': m.cache_hit,
                    'data_size_kb': m.data_size_bytes / 1024,
                    'battery_impact': m.battery_impact
                }
                for m in metrics_list[-20:]  # 最近20次查询
            ]
        }
    
    def optimize_for_mobile_constraints(self) -> Dict[str, Any]:
        """针对移动端约束进行优化"""
        optimization_results = {
            'timestamp': datetime.now(),
            'optimizations_applied': [],
            'memory_freed_mb': 0,
            'cache_efficiency_improved': False
        }
        
        # 1. 内存优化
        initial_memory = self.memory_manager.current_usage
        self._optimize_memory_usage()
        memory_freed = initial_memory - self.memory_manager.current_usage
        optimization_results['memory_freed_mb'] = memory_freed / 1024 / 1024
        optimization_results['optimizations_applied'].append("内存缓存优化")
        
        # 2. 缓存策略优化
        self._optimize_cache_strategy()
        optimization_results['optimizations_applied'].append("缓存策略调整")
        
        # 3. 预加载策略优化
        if not self.battery_saver_mode:
            self._optimize_preloading()
            optimization_results['optimizations_applied'].append("预加载策略优化")
        
        return optimization_results
    
    def _optimize_memory_usage(self) -> None:
        """优化内存使用"""
        # 清理过期缓存
        current_time = datetime.now()
        expired_keys = []
        
        for key, item in self.query_cache.items():
            if current_time > item['expires_at']:
                expired_keys.append(key)
        
        for key in expired_keys:
            item = self.query_cache.pop(key)
            self.memory_manager.deallocate(key, item['size'])
        
        # 清理长时间未使用的分页结果
        inactive_results = []
        for result_id, paginated_result in self.paginated_results.items():
            # 如果结果超过10分钟未访问，清理
            # 这里简化实现，实际应该跟踪访问时间
            if len(paginated_result.pages) > 10:  # 缓存页面过多
                inactive_results.append(result_id)
        
        for result_id in inactive_results:
            del self.paginated_results[result_id]
    
    def _optimize_cache_strategy(self) -> None:
        """优化缓存策略"""
        # 根据网络状态和内存使用情况动态调整
        memory_ratio = self.memory_manager.current_usage / self.memory_manager.max_memory_bytes
        
        if memory_ratio > 0.8:  # 内存使用超过80%
            self.cache_strategy = CacheStrategy.CONSERVATIVE
        elif memory_ratio < 0.3 and self.network_status == NetworkStatus.WIFI:
            self.cache_strategy = CacheStrategy.AGGRESSIVE
        else:
            self.cache_strategy = CacheStrategy.BALANCED
    
    def _optimize_preloading(self) -> None:
        """优化预加载策略"""
        # 根据网络状态调整预加载配置
        for paginated_result in self.paginated_results.values():
            if self.network_status == NetworkStatus.WIFI:
                paginated_result.preload_pages = 3
            elif self.network_status == NetworkStatus.MOBILE:
                paginated_result.preload_pages = 2
            else:  # SLOW_MOBILE or OFFLINE
                paginated_result.preload_pages = 1
    
    def close(self) -> None:
        """关闭优化器"""
        self._shutdown = True
        
        # 等待线程结束
        if self.background_sync_thread and self.background_sync_thread.is_alive():
            self.background_sync_thread.join(timeout=5)
        
        if self.preload_thread and self.preload_thread.is_alive():
            self.preload_thread.join(timeout=5)
        
        # 清理资源
        self.query_cache.clear()
        self.paginated_results.clear()


# 使用示例和工具函数
def create_mobile_test_environment():
    """创建移动端测试环境"""
    optimizer = MobileOptimizer("mobile_test.db", CacheStrategy.BALANCED)
    
    # 模拟网络状态变化
    optimizer.set_network_status(NetworkStatus.WIFI)
    
    # 创建测试数据
    with optimizer.get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS mobile_test_data (
                id INTEGER PRIMARY KEY,
                title TEXT,
                content TEXT,
                category TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 插入测试数据
        for i in range(1000):
            conn.execute("""
                INSERT INTO mobile_test_data (title, content, category)
                VALUES (?, ?, ?)
            """, (f"Title {i}", f"Content for item {i}", f"Category {i % 10}"))
        
        conn.commit()
    
    return optimizer


if __name__ == "__main__":
    # 命令行工具
    import argparse
    
    parser = argparse.ArgumentParser(description='移动端性能优化器')
    parser.add_argument('--db', required=True, help='数据库文件路径')
    parser.add_argument('--dashboard', action='store_true', help='显示性能仪表板')
    parser.add_argument('--optimize', action='store_true', help='执行移动端优化')
    parser.add_argument('--test', action='store_true', help='运行移动端性能测试')
    parser.add_argument('--network', choices=['wifi', 'mobile', 'slow_mobile', 'offline'],
                       help='设置网络状态')
    parser.add_argument('--battery-saver', action='store_true', help='启用省电模式')
    
    args = parser.parse_args()
    
    optimizer = MobileOptimizer(args.db)
    
    try:
        if args.network:
            status_map = {
                'wifi': NetworkStatus.WIFI,
                'mobile': NetworkStatus.MOBILE,
                'slow_mobile': NetworkStatus.SLOW_MOBILE,
                'offline': NetworkStatus.OFFLINE
            }
            optimizer.set_network_status(status_map[args.network])
            print(f"网络状态设置为: {args.network}")
        
        if args.battery_saver:
            optimizer.set_battery_saver_mode(True)
            print("省电模式已启用")
        
        if args.optimize:
            print("执行移动端优化...")
            results = optimizer.optimize_for_mobile_constraints()
            print("优化完成:")
            for opt in results['optimizations_applied']:
                print(f"  - {opt}")
            print(f"释放内存: {results['memory_freed_mb']:.2f}MB")
        
        if args.dashboard:
            print("生成移动端性能仪表板...")
            dashboard_data = optimizer.get_performance_dashboard()
            print(json.dumps(dashboard_data, indent=2, ensure_ascii=False, default=str))
        
        if args.test:
            print("运行移动端性能测试...")
            
            # 测试分页查询
            result_id = optimizer.execute_query_paginated(
                "SELECT * FROM hexagrams ORDER BY gua_number",
                pagination_config=PaginationConfig(page_size=10, preload_pages=2)
            )
            
            print(f"分页结果ID: {result_id}")
            
            # 获取第一页
            page_data = optimizer.get_page_data(result_id, 0)
            print(f"第一页数据: {len(page_data.get('data', []))} 条记录")
            
            # 测试缓存查询
            cached_result = optimizer.execute_cached_query(
                "SELECT COUNT(*) as total FROM hexagrams"
            )
            print(f"缓存查询结果: {cached_result}")
            
            time.sleep(2)  # 等待后台任务
            
            # 显示性能统计
            dashboard = optimizer.get_performance_dashboard()
            summary = dashboard.get('summary', {})
            print(f"\n性能统计:")
            print(f"  总查询数: {summary.get('total_queries', 0)}")
            print(f"  缓存命中率: {summary.get('cache_hit_rate', 0):.1%}")
            print(f"  平均查询时间: {summary.get('avg_query_time_ms', 0):.2f}ms")
            print(f"  内存使用: {dashboard.get('memory_stats', {}).get('current_usage_mb', 0):.2f}MB")
    
    finally:
        optimizer.close()