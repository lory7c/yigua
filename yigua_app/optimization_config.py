#!/usr/bin/env python3
"""
性能优化配置中心
Performance Optimization Configuration Center
目标: PDF批处理200文件/小时, SQLite查询<5ms, Flutter 60fps, 数据压缩3.7GB→100MB
"""

import os
import psutil
import sqlite3
import multiprocessing as mp
from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from enum import Enum
import json

# ============================================================================
# 系统资源配置
# ============================================================================

@dataclass
class SystemResources:
    """系统资源自动检测与配置"""
    cpu_cores: int = psutil.cpu_count(logical=False)
    cpu_threads: int = psutil.cpu_count(logical=True)
    memory_gb: float = psutil.virtual_memory().total / (1024**3)
    available_memory_gb: float = psutil.virtual_memory().available / (1024**3)
    
    @property
    def optimal_workers(self) -> int:
        """计算最优工作进程数: CPU核心数 × 2"""
        return min(self.cpu_cores * 2, 32)  # 限制最大32个进程
    
    @property
    def memory_per_worker(self) -> float:
        """每个工作进程分配的内存(GB)"""
        return (self.available_memory_gb * 0.8) / self.optimal_workers


# ============================================================================
# PDF批处理优化配置
# ============================================================================

class PDFProcessingConfig:
    """PDF批处理性能优化配置"""
    
    def __init__(self):
        self.resources = SystemResources()
        
    @property
    def config(self) -> Dict:
        return {
            # 多进程配置
            "multiprocessing": {
                "worker_processes": self.resources.optimal_workers,
                "chunk_size": 10,  # 每个进程批量处理文件数
                "queue_size": 100,  # 任务队列大小
                "timeout": 30,  # 单文件处理超时(秒)
            },
            
            # 内存优化
            "memory": {
                "max_file_size_mb": 100,  # 最大单文件大小
                "cache_size_mb": 500,  # PDF渲染缓存
                "gc_threshold": 100,  # 垃圾回收阈值(处理文件数)
            },
            
            # I/O优化
            "io": {
                "buffer_size": 8192 * 1024,  # 8MB缓冲区
                "prefetch_count": 5,  # 预读取文件数
                "use_mmap": True,  # 使用内存映射
            },
            
            # 批处理策略
            "batch": {
                "batch_size": 50,  # 批量处理大小
                "parallel_extraction": True,  # 并行文本提取
                "compression": "lz4",  # 中间结果压缩
            },
            
            # 性能目标
            "targets": {
                "files_per_hour": 200,
                "max_memory_usage_gb": self.resources.available_memory_gb * 0.6,
                "cpu_usage_percent": 80,
            }
        }


# ============================================================================
# SQLite查询优化配置
# ============================================================================

class SQLiteOptimizationConfig:
    """SQLite数据库性能优化配置"""
    
    @staticmethod
    def get_pragma_settings() -> List[str]:
        """获取SQLite PRAGMA优化设置"""
        return [
            # 性能优化
            "PRAGMA journal_mode = WAL",  # Write-Ahead Logging
            "PRAGMA synchronous = NORMAL",  # 平衡性能与安全
            "PRAGMA cache_size = -64000",  # 64MB缓存
            "PRAGMA temp_store = MEMORY",  # 临时表在内存
            "PRAGMA mmap_size = 268435456",  # 256MB内存映射
            
            # 查询优化
            "PRAGMA optimize",  # 自动优化
            "PRAGMA analysis_limit = 1000",  # 分析限制
            "PRAGMA automatic_index = ON",  # 自动索引
            
            # 并发优化
            "PRAGMA busy_timeout = 5000",  # 5秒超时
            "PRAGMA wal_autocheckpoint = 1000",  # WAL检查点
        ]
    
    @staticmethod
    def get_index_recommendations() -> Dict[str, List[str]]:
        """索引优化建议"""
        return {
            "hexagrams": [
                "CREATE INDEX idx_hexagram_number ON hexagrams(number)",
                "CREATE INDEX idx_hexagram_name ON hexagrams(name)",
                "CREATE INDEX idx_hexagram_category ON hexagrams(category)",
            ],
            "dreams": [
                "CREATE INDEX idx_dream_keyword ON dreams(keyword)",
                "CREATE INDEX idx_dream_category ON dreams(category)",
                "CREATE INDEX idx_dream_date ON dreams(created_date)",
            ],
            "calendar": [
                "CREATE INDEX idx_calendar_date ON calendar(date)",
                "CREATE INDEX idx_calendar_lunar ON calendar(lunar_date)",
                "CREATE INDEX idx_calendar_solar_term ON calendar(solar_term)",
            ],
            "history": [
                "CREATE INDEX idx_history_user ON history(user_id, created_at)",
                "CREATE INDEX idx_history_type ON history(query_type, created_at)",
            ],
            # 复合索引
            "composite": [
                "CREATE INDEX idx_search_composite ON search_data(category, keyword, relevance)",
            ]
        }
    
    @staticmethod
    def get_query_optimizations() -> Dict[str, str]:
        """查询优化模板"""
        return {
            # 使用覆盖索引
            "covering_index": """
                -- 原查询
                SELECT * FROM hexagrams WHERE number = ?
                
                -- 优化后(仅选择需要的列)
                SELECT number, name, description FROM hexagrams WHERE number = ?
            """,
            
            # 批量查询优化
            "batch_query": """
                -- 原查询(多次单独查询)
                SELECT * FROM dreams WHERE id = ?
                
                -- 优化后(批量IN查询)
                SELECT * FROM dreams WHERE id IN (?, ?, ?, ...)
            """,
            
            # 分页优化
            "pagination": """
                -- 原查询
                SELECT * FROM history ORDER BY created_at DESC LIMIT 20 OFFSET 1000
                
                -- 优化后(使用游标)
                SELECT * FROM history 
                WHERE created_at < ? 
                ORDER BY created_at DESC 
                LIMIT 20
            """,
            
            # 连接优化
            "join_optimization": """
                -- 使用INNER JOIN替代子查询
                SELECT h.*, u.name 
                FROM history h
                INNER JOIN users u ON h.user_id = u.id
                WHERE h.created_at > ?
            """
        }


# ============================================================================
# Flutter应用性能优化配置
# ============================================================================

class FlutterPerformanceConfig:
    """Flutter应用性能优化配置"""
    
    @staticmethod
    def get_optimization_settings() -> Dict:
        return {
            # 渲染优化
            "rendering": {
                "target_fps": 60,
                "enable_performance_overlay": False,  # 生产环境关闭
                "use_hardware_acceleration": True,
                "repaint_rainbow": False,  # 调试时开启
            },
            
            # 懒加载配置
            "lazy_loading": {
                "list_view": {
                    "cache_extent": 500,  # 缓存范围(像素)
                    "item_extent": None,  # 固定高度项优化
                    "add_automatic_keep_alives": False,  # 避免过度缓存
                    "add_repaint_boundaries": True,  # 重绘边界
                },
                "images": {
                    "cache_width": 800,  # 图片缓存宽度
                    "cache_height": 800,  # 图片缓存高度
                    "memory_cache_size": 100,  # 内存缓存图片数
                    "use_cdn": True,  # 使用CDN加速
                },
            },
            
            # 虚拟滚动配置
            "virtual_scrolling": {
                "sliver_grid": {
                    "cross_axis_count": 2,
                    "main_axis_spacing": 10,
                    "cross_axis_spacing": 10,
                    "child_aspect_ratio": 1.0,
                },
                "sliver_list": {
                    "item_builder_cache": True,
                    "find_child_index_callback": True,
                },
            },
            
            # 状态管理优化
            "state_management": {
                "use_const_widgets": True,  # 使用const widget
                "selective_rebuilding": True,  # 选择性重建
                "immutable_data": True,  # 不可变数据
            },
            
            # 动画优化
            "animations": {
                "use_animated_builder": True,
                "cache_animations": True,
                "prefer_gpu_animations": True,
                "animation_duration_ms": 300,
            }
        }
    
    @staticmethod
    def get_widget_optimizations() -> Dict[str, str]:
        """Widget优化代码示例"""
        return {
            "lazy_list": '''
// 优化的ListView.builder
ListView.builder(
  itemCount: items.length,
  cacheExtent: 500,
  itemBuilder: (context, index) {
    return RepaintBoundary(
      child: ItemWidget(
        key: ValueKey(items[index].id),
        item: items[index],
      ),
    );
  },
)
            ''',
            
            "virtual_scroll": '''
// 使用CustomScrollView和Slivers
CustomScrollView(
  slivers: [
    SliverGrid(
      delegate: SliverChildBuilderDelegate(
        (context, index) => ItemCard(items[index]),
        childCount: items.length,
      ),
      gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
        crossAxisCount: 2,
        mainAxisSpacing: 10,
        crossAxisSpacing: 10,
      ),
    ),
  ],
)
            ''',
            
            "image_optimization": '''
// 优化的图片加载
CachedNetworkImage(
  imageUrl: url,
  memCacheWidth: 800,
  memCacheHeight: 800,
  placeholder: (context, url) => ShimmerLoading(),
  errorWidget: (context, url, error) => Icon(Icons.error),
  fadeInDuration: Duration(milliseconds: 200),
)
            '''
        }


# ============================================================================
# 数据压缩优化配置
# ============================================================================

class CompressionConfig:
    """数据压缩策略配置"""
    
    class Algorithm(Enum):
        ZSTD = "zstd"  # Facebook Zstandard
        LZ4 = "lz4"    # 极速压缩
        GZIP = "gzip"  # 标准压缩
        BROTLI = "brotli"  # Google Brotli
        LZMA = "lzma"  # 7-Zip算法
    
    @staticmethod
    def get_algorithm_comparison() -> Dict:
        """压缩算法对比"""
        return {
            Algorithm.ZSTD: {
                "compression_ratio": 3.5,  # 压缩比
                "speed_mb_per_sec": 500,  # 压缩速度
                "decompression_speed": 1500,  # 解压速度
                "cpu_usage": "medium",
                "best_for": "平衡速度与压缩率",
                "config": {
                    "level": 3,  # 1-22
                    "threads": 4,
                    "dict_size": 110 * 1024,  # 110KB字典
                }
            },
            Algorithm.LZ4: {
                "compression_ratio": 2.1,
                "speed_mb_per_sec": 750,
                "decompression_speed": 3700,
                "cpu_usage": "low",
                "best_for": "实时压缩,低延迟",
                "config": {
                    "level": 1,  # 1-12
                    "block_size": 4 * 1024 * 1024,  # 4MB
                    "favor_dec_speed": True,
                }
            },
            Algorithm.GZIP: {
                "compression_ratio": 3.0,
                "speed_mb_per_sec": 50,
                "decompression_speed": 250,
                "cpu_usage": "medium",
                "best_for": "通用兼容性",
                "config": {
                    "level": 6,  # 1-9
                    "strategy": "default",
                }
            },
            Algorithm.BROTLI: {
                "compression_ratio": 4.0,
                "speed_mb_per_sec": 25,
                "decompression_speed": 350,
                "cpu_usage": "high",
                "best_for": "静态资源,Web传输",
                "config": {
                    "quality": 4,  # 0-11
                    "window": 22,
                    "mode": "generic",
                }
            },
            Algorithm.LZMA: {
                "compression_ratio": 4.5,
                "speed_mb_per_sec": 10,
                "decompression_speed": 50,
                "cpu_usage": "very_high",
                "best_for": "最高压缩率,归档",
                "config": {
                    "preset": 6,  # 0-9
                    "dict_size": 64 * 1024 * 1024,  # 64MB
                }
            }
        }
    
    @staticmethod
    def get_compression_strategy(data_size_gb: float, target_size_mb: float) -> Dict:
        """根据数据大小选择压缩策略"""
        required_ratio = (data_size_gb * 1024) / target_size_mb
        
        if required_ratio >= 30:  # 需要极高压缩率 (3.7GB -> 100MB = 37倍)
            return {
                "primary": Algorithm.ZSTD,
                "settings": {
                    "level": 19,  # 高压缩级别
                    "threads": mp.cpu_count(),
                    "long_mode": 27,  # 长距离匹配
                    "strategy": "btultra2",
                },
                "preprocessing": {
                    "deduplication": True,  # 去重
                    "delta_encoding": True,  # 增量编码
                    "dictionary_training": True,  # 训练字典
                },
                "chunking": {
                    "chunk_size_mb": 16,
                    "parallel_chunks": 8,
                },
                "expected_ratio": 35,
                "estimated_time_minutes": 15,
            }
        elif required_ratio >= 10:
            return {
                "primary": Algorithm.ZSTD,
                "settings": {
                    "level": 12,
                    "threads": mp.cpu_count() // 2,
                },
                "preprocessing": {
                    "deduplication": True,
                    "delta_encoding": False,
                    "dictionary_training": False,
                },
                "expected_ratio": 15,
                "estimated_time_minutes": 5,
            }
        else:
            return {
                "primary": Algorithm.LZ4,
                "settings": {
                    "level": 9,
                    "block_size": 4 * 1024 * 1024,
                },
                "preprocessing": {
                    "deduplication": False,
                    "delta_encoding": False,
                    "dictionary_training": False,
                },
                "expected_ratio": 5,
                "estimated_time_minutes": 1,
            }


# ============================================================================
# 缓存策略配置
# ============================================================================

class CacheStrategyConfig:
    """多层缓存策略配置"""
    
    @staticmethod
    def get_cache_layers() -> Dict:
        return {
            # L1: 内存缓存
            "memory": {
                "type": "LRU",
                "size_mb": 512,
                "ttl_seconds": 3600,
                "max_items": 10000,
                "eviction_policy": "least_recently_used",
                "implementation": {
                    "python": "functools.lru_cache",
                    "dart": "flutter_cache_manager",
                }
            },
            
            # L2: Redis缓存
            "redis": {
                "enabled": True,
                "host": "localhost",
                "port": 6379,
                "db": 0,
                "password": None,
                "pool_size": 10,
                "socket_timeout": 5,
                "ttl_seconds": 7200,
                "serialization": "msgpack",  # 比JSON快
                "compression": "lz4",
                "key_patterns": {
                    "hexagram": "hexagram:{id}",
                    "dream": "dream:{keyword}",
                    "calendar": "calendar:{date}",
                    "search": "search:{query_hash}",
                },
                "config_commands": [
                    "CONFIG SET maxmemory 2gb",
                    "CONFIG SET maxmemory-policy allkeys-lru",
                    "CONFIG SET save ''",  # 禁用持久化提升性能
                ]
            },
            
            # L3: 磁盘缓存
            "disk": {
                "type": "sqlite",
                "path": "./cache/cache.db",
                "size_limit_gb": 5,
                "ttl_days": 7,
                "compression": "zstd",
                "vacuum_interval_hours": 24,
            },
            
            # CDN缓存(静态资源)
            "cdn": {
                "enabled": True,
                "provider": "cloudflare",
                "ttl_static": 86400 * 30,  # 30天
                "ttl_dynamic": 3600,  # 1小时
                "purge_on_update": True,
            }
        }
    
    @staticmethod
    def get_cache_warming_strategy() -> Dict:
        """缓存预热策略"""
        return {
            "startup_preload": [
                "hexagrams_all",  # 所有卦象
                "common_dreams",  # 常见梦境
                "current_month_calendar",  # 当月日历
            ],
            "scheduled_refresh": {
                "interval_minutes": 30,
                "items": ["hot_queries", "trending_topics"],
            },
            "predictive_loading": {
                "enabled": True,
                "algorithm": "time_series",  # 基于时间序列预测
                "look_ahead_hours": 2,
            }
        }


# ============================================================================
# 性能监控配置
# ============================================================================

class PerformanceMonitoringConfig:
    """性能监控配置"""
    
    @staticmethod
    def get_metrics() -> Dict:
        return {
            "pdf_processing": {
                "throughput": "files_per_minute",
                "latency_p50": "ms",
                "latency_p95": "ms",
                "latency_p99": "ms",
                "error_rate": "percentage",
                "memory_usage": "mb",
                "cpu_usage": "percentage",
            },
            "sqlite_queries": {
                "query_time_p50": "ms",
                "query_time_p95": "ms",
                "query_time_p99": "ms",
                "cache_hit_rate": "percentage",
                "slow_queries": "count",
                "connections": "count",
            },
            "flutter_app": {
                "fps": "frames_per_second",
                "jank_ratio": "percentage",
                "memory_usage": "mb",
                "startup_time": "ms",
                "api_response_time": "ms",
            },
            "compression": {
                "compression_ratio": "ratio",
                "compression_speed": "mb_per_sec",
                "decompression_speed": "mb_per_sec",
                "cpu_usage": "percentage",
            }
        }
    
    @staticmethod
    def get_alerts() -> List[Dict]:
        return [
            {
                "metric": "pdf_processing.throughput",
                "condition": "< 3",  # 低于3文件/分钟
                "severity": "warning",
                "action": "scale_workers",
            },
            {
                "metric": "sqlite_queries.query_time_p95",
                "condition": "> 5",  # 超过5ms
                "severity": "critical",
                "action": "optimize_query",
            },
            {
                "metric": "flutter_app.fps",
                "condition": "< 55",  # 低于55fps
                "severity": "warning",
                "action": "profile_rendering",
            },
            {
                "metric": "memory_usage",
                "condition": "> 80%",
                "severity": "critical",
                "action": "trigger_gc",
            }
        ]


# ============================================================================
# 主配置导出
# ============================================================================

class OptimizationConfig:
    """统一优化配置管理"""
    
    def __init__(self):
        self.pdf = PDFProcessingConfig()
        self.sqlite = SQLiteOptimizationConfig()
        self.flutter = FlutterPerformanceConfig()
        self.compression = CompressionConfig()
        self.cache = CacheStrategyConfig()
        self.monitoring = PerformanceMonitoringConfig()
    
    def export_config(self, filepath: str = "optimization_settings.json"):
        """导出所有配置为JSON"""
        config = {
            "pdf_processing": self.pdf.config,
            "sqlite": {
                "pragma": self.sqlite.get_pragma_settings(),
                "indexes": self.sqlite.get_index_recommendations(),
            },
            "flutter": self.flutter.get_optimization_settings(),
            "compression": {
                "algorithms": {
                    algo.value: specs 
                    for algo, specs in self.compression.get_algorithm_comparison().items()
                },
                "strategy": self.compression.get_compression_strategy(3.7, 100),
            },
            "cache": self.cache.get_cache_layers(),
            "monitoring": {
                "metrics": self.monitoring.get_metrics(),
                "alerts": self.monitoring.get_alerts(),
            }
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False, default=str)
        
        return config
    
    def print_summary(self):
        """打印优化配置摘要"""
        resources = SystemResources()
        print("="*60)
        print("性能优化配置摘要")
        print("="*60)
        print(f"系统资源:")
        print(f"  - CPU核心: {resources.cpu_cores} 物理核心, {resources.cpu_threads} 线程")
        print(f"  - 内存: {resources.memory_gb:.1f}GB 总计, {resources.available_memory_gb:.1f}GB 可用")
        print(f"  - 优化工作进程数: {resources.optimal_workers}")
        print()
        print(f"优化目标:")
        print(f"  - PDF处理: 200文件/小时 (使用{resources.optimal_workers}个进程)")
        print(f"  - SQLite查询: <5ms (WAL模式 + 索引优化)")
        print(f"  - Flutter渲染: 60fps (虚拟滚动 + 懒加载)")
        print(f"  - 数据压缩: 3.7GB → 100MB (ZSTD高压缩模式)")
        print()
        print(f"推荐压缩方案:")
        strategy = self.compression.get_compression_strategy(3.7, 100)
        print(f"  - 算法: {strategy['primary'].value}")
        print(f"  - 预期压缩率: {strategy['expected_ratio']}x")
        print(f"  - 预计时间: {strategy['estimated_time_minutes']}分钟")
        print("="*60)


if __name__ == "__main__":
    # 创建并导出配置
    config = OptimizationConfig()
    config.print_summary()
    config.export_config()
    print("\n配置已导出到 optimization_settings.json")