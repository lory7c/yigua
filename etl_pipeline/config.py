"""
ETL Pipeline Configuration
易学知识库构建配置文件
"""

import os
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List, Any

@dataclass
class ETLConfig:
    """ETL管道配置类"""
    
    # 数据路径配置
    SOURCE_DATA_DIR = Path("/mnt/d/desktop/appp/data")
    OUTPUT_DIR = Path("/mnt/d/desktop/appp/processed_data")
    
    # 数据包配置
    CORE_DATA_SIZE_MB = 8  # 核心数据包目标大小
    EXTENDED_DATA_SIZE_MB = 80  # 扩展数据包目标大小
    
    # PDF处理配置 - 优化后的高性能配置
    BATCH_SIZE = 15  # 批处理大小（从10增加到15）
    MAX_WORKERS = 6  # 并发处理线程数（从4增加到6）
    PDF_TIMEOUT = 300  # PDF处理超时时间（秒）
    
    # 性能优化配置
    ENABLE_MULTIPROCESSING = True  # 启用多进程处理
    ENABLE_ASYNC_PROCESSING = True  # 启用异步处理
    MAX_MEMORY_MB = 2048  # 最大内存使用限制
    MEMORY_CHECK_INTERVAL = 10  # 内存检查间隔（秒）
    FORCE_GC_INTERVAL = 100  # 强制垃圾回收间隔（处理文件数）
    
    # 缓存配置
    ENABLE_RESULT_CACHE = True
    CACHE_SIZE_MB = 256  # 结果缓存大小
    CACHE_TTL_SECONDS = 1800  # 缓存过期时间（30分钟）
    
    # 数据分类配置
    CATEGORIES = {
        'hexagram': {  # 64卦相关
            'keywords': ['卦', '乾', '坤', '震', '巽', '坎', '离', '艮', '兑'],
            'priority': 1,
            'target_size_mb': 3
        },
        'yao': {  # 384爻辞
            'keywords': ['爻', '初六', '九二', '六三', '九四', '六五', '上九'],
            'priority': 2,
            'target_size_mb': 2
        },
        'annotation': {  # 历代注解
            'keywords': ['注', '解', '释', '疏', '传'],
            'priority': 3,
            'target_size_mb': 20
        },
        'divination': {  # 占卜案例
            'keywords': ['占', '卜', '筮', '测', '断'],
            'priority': 4,
            'target_size_mb': 15
        },
        'judgment': {  # 断语集合
            'keywords': ['断语', '口诀', '诀', '法'],
            'priority': 5,
            'target_size_mb': 10
        },
        'liuyao': {  # 六爻专题
            'keywords': ['六爻', '八卦', '世爻', '应爻'],
            'priority': 6,
            'target_size_mb': 25
        },
        'other': {  # 其他内容
            'keywords': [],
            'priority': 99,
            'target_size_mb': 5
        }
    }
    
    # 数据质量配置
    MIN_TEXT_LENGTH = 50  # 最小文本长度
    MAX_TEXT_LENGTH = 100000  # 最大文本长度
    MIN_CONFIDENCE_SCORE = 0.7  # 最小置信度分数
    
    # 输出格式配置
    OUTPUT_FORMATS = {
        'json': True,
        'sqlite': True,
        'parquet': True,
        'csv': False
    }
    
    # 数据库配置
    DATABASE_PATH = OUTPUT_DIR / "yijing_knowledge.db"
    
    # 日志配置
    LOG_LEVEL = "INFO"
    LOG_FILE = OUTPUT_DIR / "etl_pipeline.log"
    
    @classmethod
    def create_directories(cls):
        """创建必要的目录结构"""
        directories = [
            cls.OUTPUT_DIR,
            cls.OUTPUT_DIR / "core_data",
            cls.OUTPUT_DIR / "extended_data",
            cls.OUTPUT_DIR / "cloud_data",
            cls.OUTPUT_DIR / "logs",
            cls.OUTPUT_DIR / "temp",
            cls.OUTPUT_DIR / "quality_reports"
        ]
        
        for dir_path in directories:
            dir_path.mkdir(parents=True, exist_ok=True)
        
        return directories

# 64卦基础信息配置
HEXAGRAM_INFO = {
    1: {"name": "乾", "symbol": "☰", "nature": "天", "element": "金"},
    2: {"name": "坤", "symbol": "☷", "nature": "地", "element": "土"},
    3: {"name": "屯", "symbol": "☵", "nature": "水雷", "element": "水"},
    4: {"name": "蒙", "symbol": "☶", "nature": "山水", "element": "水"},
    5: {"name": "需", "symbol": "☰", "nature": "水天", "element": "水"},
    6: {"name": "讼", "symbol": "☰", "nature": "天水", "element": "水"},
    # ... 继续添加其他62卦
}

# 文本分类模型配置
TEXT_CLASSIFICATION_CONFIG = {
    'model_type': 'rule_based',  # 规则基础分类
    'use_ml': False,  # 是否使用机器学习
    'confidence_threshold': 0.6,
    'keyword_weights': {
        'exact_match': 1.0,
        'partial_match': 0.7,
        'context_match': 0.5
    }
}

# 数据去重配置
DEDUPLICATION_CONFIG = {
    'similarity_threshold': 0.85,
    'hash_algorithm': 'sha256',
    'content_comparison': True,
    'fuzzy_matching': True
}