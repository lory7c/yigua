#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多层缓存策略配置
实现Redis、内存缓存、数据库查询缓存的统一管理
目标：缓存命中率>80%，响应时间<5ms
"""

import redis
import json
import time
import logging
import hashlib
import pickle
from typing import Dict, List, Any, Optional, Union, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from threading import Lock
import asyncio
from enum import Enum
from collections import OrderedDict
import gzip
import lz4.frame


class CacheLevel(Enum):
    """缓存级别"""
    L1_MEMORY = "l1_memory"      # 内存缓存 (最快)
    L2_REDIS = "l2_redis"        # Redis缓存 (中等速度)
    L3_DATABASE = "l3_database"  # 数据库缓存 (最慢，但持久)


class CacheStrategy(Enum):
    """缓存策略"""
    LRU = "lru"                  # 最近最少使用
    LFU = "lfu"                  # 最不经常使用
    TTL = "ttl"                  # 基于时间过期
    SIZE_BASED = "size_based"    # 基于大小限制


@dataclass
class CacheConfig:
    """缓存配置"""
    # L1 内存缓存
    l1_max_size: int = 10000      # 最大条目数
    l1_max_memory_mb: int = 256   # 最大内存使用
    l1_ttl_seconds: int = 300     # 5分钟过期
    
    # L2 Redis缓存
    l2_enabled: bool = True
    l2_host: str = "localhost"
    l2_port: int = 6379
    l2_db: int = 0
    l2_max_memory: str = "512mb"
    l2_ttl_seconds: int = 1800    # 30分钟过期
    
    # L3 数据库缓存
    l3_enabled: bool = True
    l3_table_name: str = "cache_storage"
    l3_cleanup_interval: int = 3600  # 1小时清理一次
    
    # 压缩配置
    enable_compression: bool = True
    compression_threshold: int = 1024  # 大于1KB的数据进行压缩
    compression_method: str = "lz4"    # lz4 或 gzip
    
    # 性能配置
    enable_async: bool = True
    batch_size: int = 100
    prefetch_enabled: bool = True


class CompressionManager:
    """压缩管理器"""
    
    @staticmethod
    def compress(data: bytes, method: str = "lz4") -> bytes:
        """压缩数据"""
        if method == "lz4":
            return lz4.frame.compress(data)
        elif method == "gzip":
            return gzip.compress(data)
        else:
            return data
    
    @staticmethod
    def decompress(data: bytes, method: str = "lz4") -> bytes:
        """解压数据"""
        try:
            if method == "lz4":
                return lz4.frame.decompress(data)
            elif method == "gzip":
                return gzip.decompress(data)
            else:
                return data
        except Exception:
            return data  # 如果解压失败，返回原数据


class L1MemoryCache:
    """L1内存缓存 - 最快响应"""
    
    def __init__(self, config: CacheConfig):
        self.config = config
        self.cache = OrderedDict()
        self.access_counts = {}
        self.access_times = {}
        self.lock = Lock()
        self.current_size = 0
        
    def _generate_key(self, key: str) -> str:
        """生成缓存键"""
        return hashlib.md5(key.encode()).hexdigest()
    
    def _estimate_size(self, value: Any) -> int:
        """估算值的大小"""
        try:
            return len(pickle.dumps(value))
        except:
            return len(str(value).encode())
    
    def _evict_if_needed(self, new_size: int):
        """根据需要驱逐缓存"""
        max_size_bytes = self.config.l1_max_memory_mb * 1024 * 1024
        
        while (len(self.cache) >= self.config.l1_max_size or 
               self.current_size + new_size > max_size_bytes):
            if not self.cache:
                break
                
            # LRU策略：移除最久未访问的项
            oldest_key = next(iter(self.cache))
            oldest_value = self.cache.pop(oldest_key)
            
            # 更新大小统计
            self.current_size -= self._estimate_size(oldest_value)
            
            # 清理相关统计
            self.access_counts.pop(oldest_key, None)
            self.access_times.pop(oldest_key, None)
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        with self.lock:
            cache_key = self._generate_key(key)
            
            if cache_key not in self.cache:
                return None
            
            # 检查TTL
            if cache_key in self.access_times:
                if time.time() - self.access_times[cache_key] > self.config.l1_ttl_seconds:
                    self.delete(key)
                    return None
            
            # 更新访问统计
            self.access_counts[cache_key] = self.access_counts.get(cache_key, 0) + 1
            self.access_times[cache_key] = time.time()
            
            # 移到最后（LRU）
            value = self.cache.pop(cache_key)
            self.cache[cache_key] = value
            
            return value
    
    def set(self, key: str, value: Any) -> bool:
        """设置缓存值"""
        with self.lock:
            cache_key = self._generate_key(key)
            value_size = self._estimate_size(value)
            
            # 检查是否需要驱逐
            self._evict_if_needed(value_size)
            
            # 如果键已存在，更新大小
            if cache_key in self.cache:
                old_size = self._estimate_size(self.cache[cache_key])
                self.current_size -= old_size
            
            # 设置新值
            self.cache[cache_key] = value
            self.current_size += value_size
            self.access_times[cache_key] = time.time()
            self.access_counts[cache_key] = self.access_counts.get(cache_key, 0) + 1
            
            return True
    
    def delete(self, key: str) -> bool:
        """删除缓存值"""
        with self.lock:
            cache_key = self._generate_key(key)
            
            if cache_key in self.cache:
                value = self.cache.pop(cache_key)
                self.current_size -= self._estimate_size(value)
                self.access_counts.pop(cache_key, None)
                self.access_times.pop(cache_key, None)
                return True
            
            return False
    
    def clear(self):
        """清空缓存"""
        with self.lock:
            self.cache.clear()
            self.access_counts.clear()
            self.access_times.clear()
            self.current_size = 0
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        with self.lock:
            return {
                'total_items': len(self.cache),
                'current_size_mb': self.current_size / 1024 / 1024,
                'max_size_items': self.config.l1_max_size,
                'max_size_mb': self.config.l1_max_memory_mb,
                'hit_rate': getattr(self, '_hit_count', 0) / max(getattr(self, '_request_count', 1), 1)
            }


class L2RedisCache:
    """L2 Redis缓存 - 中等速度，支持分布式"""
    
    def __init__(self, config: CacheConfig):
        self.config = config
        self.compression = CompressionManager()
        self.redis_client = None
        self._connect()
        
    def _connect(self):
        """连接Redis"""
        try:
            if self.config.l2_enabled:
                self.redis_client = redis.Redis(
                    host=self.config.l2_host,
                    port=self.config.l2_port,
                    db=self.config.l2_db,
                    decode_responses=False,  # 处理二进制数据
                    socket_connect_timeout=5,
                    socket_timeout=5,
                    retry_on_timeout=True,
                    health_check_interval=30
                )
                
                # 测试连接
                self.redis_client.ping()
                
                # 配置内存策略
                try:
                    self.redis_client.config_set('maxmemory', self.config.l2_max_memory)
                    self.redis_client.config_set('maxmemory-policy', 'allkeys-lru')
                except:
                    pass  # 如果没有权限修改配置，继续使用默认设置
                
        except Exception as e:
            logging.warning(f"Redis连接失败，禁用L2缓存: {e}")
            self.redis_client = None
    
    def _serialize(self, value: Any) -> bytes:
        """序列化值"""
        data = pickle.dumps(value)
        
        if (self.config.enable_compression and 
            len(data) > self.config.compression_threshold):
            data = self.compression.compress(data, self.config.compression_method)
            return b'COMPRESSED:' + data
        
        return data
    
    def _deserialize(self, data: bytes) -> Any:
        """反序列化值"""
        if data.startswith(b'COMPRESSED:'):
            compressed_data = data[11:]  # 移除前缀
            data = self.compression.decompress(compressed_data, self.config.compression_method)
        
        return pickle.loads(data)
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        if not self.redis_client:
            return None
        
        try:
            data = self.redis_client.get(key)
            if data is None:
                return None
            
            return self._deserialize(data)
        
        except Exception as e:
            logging.warning(f"Redis获取失败: {e}")
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """设置缓存值"""
        if not self.redis_client:
            return False
        
        try:
            data = self._serialize(value)
            ttl = ttl or self.config.l2_ttl_seconds
            
            return self.redis_client.setex(key, ttl, data)
        
        except Exception as e:
            logging.warning(f"Redis设置失败: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """删除缓存值"""
        if not self.redis_client:
            return False
        
        try:
            return bool(self.redis_client.delete(key))
        
        except Exception as e:
            logging.warning(f"Redis删除失败: {e}")
            return False
    
    def get_batch(self, keys: List[str]) -> Dict[str, Any]:
        """批量获取"""
        if not self.redis_client or not keys:
            return {}
        
        try:
            values = self.redis_client.mget(keys)
            result = {}
            
            for key, data in zip(keys, values):
                if data is not None:
                    try:
                        result[key] = self._deserialize(data)
                    except:
                        continue
            
            return result
        
        except Exception as e:
            logging.warning(f"Redis批量获取失败: {e}")
            return {}
    
    def set_batch(self, items: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """批量设置"""
        if not self.redis_client or not items:
            return False
        
        try:
            pipe = self.redis_client.pipeline()
            ttl = ttl or self.config.l2_ttl_seconds
            
            for key, value in items.items():
                data = self._serialize(value)
                pipe.setex(key, ttl, data)
            
            pipe.execute()
            return True
        
        except Exception as e:
            logging.warning(f"Redis批量设置失败: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """获取Redis统计"""
        if not self.redis_client:
            return {'status': 'disabled'}
        
        try:
            info = self.redis_client.info()
            memory_info = self.redis_client.memory_stats()
            
            return {
                'status': 'connected',
                'used_memory_mb': info.get('used_memory', 0) / 1024 / 1024,
                'connected_clients': info.get('connected_clients', 0),
                'keyspace_hits': info.get('keyspace_hits', 0),
                'keyspace_misses': info.get('keyspace_misses', 0),
                'hit_rate': info.get('keyspace_hits', 0) / max(
                    info.get('keyspace_hits', 0) + info.get('keyspace_misses', 0), 1
                ),
                'total_keys': sum(info.get(f'db{i}', {}).get('keys', 0) for i in range(16))
            }
        
        except Exception as e:
            logging.warning(f"获取Redis统计失败: {e}")
            return {'status': 'error', 'error': str(e)}


class MultiLevelCacheManager:
    """多层缓存管理器"""
    
    def __init__(self, config: CacheConfig = None):
        self.config = config or CacheConfig()
        self.logger = logging.getLogger(__name__)
        
        # 初始化各层缓存
        self.l1_cache = L1MemoryCache(self.config)
        self.l2_cache = L2RedisCache(self.config) if self.config.l2_enabled else None
        
        # 统计信息
        self.stats = {
            'l1_hits': 0, 'l1_misses': 0,
            'l2_hits': 0, 'l2_misses': 0,
            'l3_hits': 0, 'l3_misses': 0,
            'total_requests': 0
        }
    
    def _update_stats(self, level: str, hit: bool):
        """更新统计信息"""
        self.stats['total_requests'] += 1
        if hit:
            self.stats[f'{level}_hits'] += 1
        else:
            self.stats[f'{level}_misses'] += 1
    
    async def get(self, key: str, default: Any = None) -> Any:
        """多层缓存获取"""
        
        # L1 内存缓存
        value = self.l1_cache.get(key)
        if value is not None:
            self._update_stats('l1', True)
            return value
        self._update_stats('l1', False)
        
        # L2 Redis缓存
        if self.l2_cache:
            value = self.l2_cache.get(key)
            if value is not None:
                self._update_stats('l2', True)
                # 回写到L1
                self.l1_cache.set(key, value)
                return value
            self._update_stats('l2', False)
        
        return default
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """多层缓存设置"""
        success = True
        
        # 设置到L1
        if not self.l1_cache.set(key, value):
            success = False
        
        # 设置到L2
        if self.l2_cache and not self.l2_cache.set(key, value, ttl):
            success = False
        
        return success
    
    async def delete(self, key: str) -> bool:
        """多层缓存删除"""
        results = []
        
        # 从所有层删除
        results.append(self.l1_cache.delete(key))
        
        if self.l2_cache:
            results.append(self.l2_cache.delete(key))
        
        return any(results)
    
    async def get_batch(self, keys: List[str]) -> Dict[str, Any]:
        """批量获取"""
        results = {}
        remaining_keys = list(keys)
        
        # L1 批量获取
        for key in list(remaining_keys):
            value = self.l1_cache.get(key)
            if value is not None:
                results[key] = value
                remaining_keys.remove(key)
                self._update_stats('l1', True)
            else:
                self._update_stats('l1', False)
        
        # L2 批量获取剩余键
        if self.l2_cache and remaining_keys:
            l2_results = self.l2_cache.get_batch(remaining_keys)
            
            for key, value in l2_results.items():
                results[key] = value
                self.l1_cache.set(key, value)  # 回写到L1
                self._update_stats('l2', True)
            
            # 统计L2未命中
            for key in remaining_keys:
                if key not in l2_results:
                    self._update_stats('l2', False)
        
        return results
    
    async def set_batch(self, items: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """批量设置"""
        success = True
        
        # L1批量设置
        for key, value in items.items():
            if not self.l1_cache.set(key, value):
                success = False
        
        # L2批量设置
        if self.l2_cache and not self.l2_cache.set_batch(items, ttl):
            success = False
        
        return success
    
    def invalidate_pattern(self, pattern: str) -> int:
        """根据模式批量失效缓存"""
        count = 0
        
        # 暂时只支持简单的前缀匹配
        if pattern.endswith('*'):
            prefix = pattern[:-1]
            
            # L1缓存失效
            keys_to_delete = []
            for key in self.l1_cache.cache.keys():
                if key.startswith(prefix):
                    keys_to_delete.append(key)
            
            for key in keys_to_delete:
                if self.l1_cache.delete(key):
                    count += 1
            
            # L2缓存失效
            if self.l2_cache and self.l2_cache.redis_client:
                try:
                    keys = self.l2_cache.redis_client.keys(pattern)
                    if keys:
                        deleted = self.l2_cache.redis_client.delete(*keys)
                        count += deleted
                except Exception as e:
                    self.logger.warning(f"Redis模式删除失败: {e}")
        
        return count
    
    def clear_all(self):
        """清空所有缓存"""
        self.l1_cache.clear()
        
        if self.l2_cache and self.l2_cache.redis_client:
            try:
                self.l2_cache.redis_client.flushdb()
            except Exception as e:
                self.logger.warning(f"清空Redis失败: {e}")
    
    def get_comprehensive_stats(self) -> Dict[str, Any]:
        """获取综合统计信息"""
        total_requests = max(self.stats['total_requests'], 1)
        
        stats = {
            'timestamp': datetime.now().isoformat(),
            'total_requests': total_requests,
            
            # 各层统计
            'l1_stats': {
                'hits': self.stats['l1_hits'],
                'misses': self.stats['l1_misses'],
                'hit_rate': self.stats['l1_hits'] / total_requests,
                'cache_info': self.l1_cache.get_stats()
            },
            
            'l2_stats': {
                'hits': self.stats['l2_hits'],
                'misses': self.stats['l2_misses'],
                'hit_rate': self.stats['l2_hits'] / total_requests,
                'cache_info': self.l2_cache.get_stats() if self.l2_cache else {'status': 'disabled'}
            },
            
            # 综合指标
            'overall_hit_rate': (self.stats['l1_hits'] + self.stats['l2_hits']) / total_requests,
            'cache_efficiency': self._calculate_cache_efficiency(),
            'performance_score': self._calculate_performance_score()
        }
        
        return stats
    
    def _calculate_cache_efficiency(self) -> float:
        """计算缓存效率"""
        total_hits = self.stats['l1_hits'] + self.stats['l2_hits'] 
        total_requests = max(self.stats['total_requests'], 1)
        
        hit_rate = total_hits / total_requests
        
        # L1命中更有价值（更快）
        l1_weight = 1.0
        l2_weight = 0.8
        
        weighted_score = (
            (self.stats['l1_hits'] * l1_weight + self.stats['l2_hits'] * l2_weight) /
            (total_requests * l1_weight)
        )
        
        return min(1.0, weighted_score)
    
    def _calculate_performance_score(self) -> float:
        """计算性能评分（0-100）"""
        efficiency = self._calculate_cache_efficiency()
        
        # 基于效率的评分
        base_score = efficiency * 80
        
        # L1缓存利用率加分
        l1_stats = self.l1_cache.get_stats()
        if l1_stats['total_items'] > 0:
            l1_utilization = min(1.0, l1_stats['current_size_mb'] / l1_stats['max_size_mb'])
            base_score += l1_utilization * 10
        
        # L2连接状态加分
        if self.l2_cache:
            l2_stats = self.l2_cache.get_stats()
            if l2_stats.get('status') == 'connected':
                base_score += 10
        
        return min(100, base_score)


# =============================================================================
# 使用示例和测试
# =============================================================================

async def test_cache_performance():
    """测试缓存性能"""
    print("🚀 开始多层缓存性能测试")
    
    # 配置缓存
    config = CacheConfig(
        l1_max_size=5000,
        l1_max_memory_mb=128,
        l2_enabled=True,  # 启用Redis（如果可用）
        enable_compression=True
    )
    
    cache_manager = MultiLevelCacheManager(config)
    
    # 测试数据
    test_data = {
        f"key_{i}": {
            "id": i,
            "name": f"test_item_{i}",
            "data": "x" * (100 + i % 500),  # 不同大小的数据
            "timestamp": datetime.now().isoformat()
        }
        for i in range(1000)
    }
    
    print(f"准备测试数据: {len(test_data)} 项")
    
    # 写入性能测试
    print("\n=== 写入性能测试 ===")
    start_time = time.time()
    
    await cache_manager.set_batch(test_data)
    
    write_time = time.time() - start_time
    write_rate = len(test_data) / write_time
    
    print(f"批量写入完成: {len(test_data)} 项，耗时 {write_time:.2f}s ({write_rate:.0f} ops/sec)")
    
    # 读取性能测试
    print("\n=== 读取性能测试 ===")
    
    # 随机读取测试
    import random
    test_keys = random.sample(list(test_data.keys()), 500)
    
    start_time = time.time()
    results = await cache_manager.get_batch(test_keys)
    read_time = time.time() - start_time
    
    hit_count = len(results)
    hit_rate = hit_count / len(test_keys)
    read_rate = len(test_keys) / read_time
    
    print(f"批量读取测试: {len(test_keys)} 项")
    print(f"命中数: {hit_count}, 命中率: {hit_rate:.1%}")
    print(f"耗时: {read_time:.2f}s ({read_rate:.0f} ops/sec)")
    
    # 缓存层级测试
    print("\n=== 缓存层级效果测试 ===")
    
    # 清空L1，测试L2->L1回写
    cache_manager.l1_cache.clear()
    
    single_key = test_keys[0]
    value = await cache_manager.get(single_key)
    
    if value:
        print(f"L2->L1回写成功: {single_key}")
        
        # 再次获取，应该从L1命中
        start_time = time.time()
        value2 = await cache_manager.get(single_key)
        l1_time = time.time() - start_time
        
        print(f"L1缓存响应时间: {l1_time*1000:.2f}ms")
    
    # 获取综合统计
    print("\n=== 综合性能统计 ===")
    stats = cache_manager.get_comprehensive_stats()
    
    print(f"总请求数: {stats['total_requests']}")
    print(f"L1命中率: {stats['l1_stats']['hit_rate']:.1%}")
    print(f"L2命中率: {stats['l2_stats']['hit_rate']:.1%}")
    print(f"总体命中率: {stats['overall_hit_rate']:.1%}")
    print(f"缓存效率: {stats['cache_efficiency']:.1%}")
    print(f"性能评分: {stats['performance_score']:.1f}/100")
    
    # L1内存使用
    l1_info = stats['l1_stats']['cache_info']
    print(f"L1内存使用: {l1_info['current_size_mb']:.1f}MB/{l1_info['max_size_mb']}MB")
    print(f"L1缓存项: {l1_info['total_items']}/{l1_info['max_size_items']}")
    
    # L2状态
    l2_info = stats['l2_stats']['cache_info']
    if l2_info['status'] == 'connected':
        print(f"L2内存使用: {l2_info['used_memory_mb']:.1f}MB")
        print(f"L2键数量: {l2_info['total_keys']}")
        print(f"L2命中率: {l2_info['hit_rate']:.1%}")
    else:
        print(f"L2状态: {l2_info['status']}")
    
    return stats


if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(level=logging.INFO)
    
    # 运行性能测试
    asyncio.run(test_cache_performance())