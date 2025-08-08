"""
增量更新机制和变化检测
实现智能的增量处理，避免重复处理，提升效率
"""

import hashlib
import json
import sqlite3
import time
import logging
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path
import os
from collections import defaultdict
import threading

from .config import ETLConfig
from .models import SourceDocument, ProcessedContent


@dataclass
class FileChecksum:
    """文件校验和信息"""
    file_path: str
    file_size: int
    modification_time: datetime
    checksum: str
    checksum_type: str = "sha256"
    last_checked: datetime = field(default_factory=datetime.now)


@dataclass
class ChangeDetectionResult:
    """变化检测结果"""
    new_files: List[Path] = field(default_factory=list)
    modified_files: List[Path] = field(default_factory=list)
    deleted_files: List[Path] = field(default_factory=list)
    unchanged_files: List[Path] = field(default_factory=list)
    
    @property
    def has_changes(self) -> bool:
        """是否有变化"""
        return bool(self.new_files or self.modified_files or self.deleted_files)
    
    @property
    def total_changed(self) -> int:
        """总变化数量"""
        return len(self.new_files) + len(self.modified_files) + len(self.deleted_files)


@dataclass
class ProcessingCache:
    """处理缓存记录"""
    file_path: str
    file_checksum: str
    processing_result_id: str
    processing_time: datetime
    processing_version: str = "1.0"
    metadata: Dict[str, Any] = field(default_factory=dict)


class ChecksumCalculator:
    """校验和计算器"""
    
    def __init__(self, checksum_type: str = "sha256"):
        self.checksum_type = checksum_type
        self.logger = logging.getLogger(__name__)
    
    def calculate_file_checksum(self, file_path: Path, chunk_size: int = 8192) -> str:
        """计算文件校验和"""
        if not file_path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        if self.checksum_type == "sha256":
            hasher = hashlib.sha256()
        elif self.checksum_type == "md5":
            hasher = hashlib.md5()
        else:
            raise ValueError(f"不支持的校验和类型: {self.checksum_type}")
        
        try:
            with open(file_path, 'rb') as f:
                while chunk := f.read(chunk_size):
                    hasher.update(chunk)
            
            return hasher.hexdigest()
            
        except Exception as e:
            self.logger.error(f"计算文件校验和失败 {file_path}: {e}")
            raise
    
    def calculate_fast_checksum(self, file_path: Path) -> str:
        """快速校验和计算（基于文件大小和修改时间）"""
        try:
            stat = file_path.stat()
            fast_hash = hashlib.md5(
                f"{file_path}:{stat.st_size}:{stat.st_mtime}".encode()
            ).hexdigest()
            
            return fast_hash
            
        except Exception as e:
            self.logger.error(f"计算快速校验和失败 {file_path}: {e}")
            raise


class IncrementalDatabase:
    """增量处理数据库"""
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
        self._lock = threading.RLock()
        
        # 初始化数据库
        self._init_database()
    
    def _init_database(self):
        """初始化数据库"""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            # 文件校验和表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS file_checksums (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_path TEXT UNIQUE NOT NULL,
                    file_size INTEGER NOT NULL,
                    modification_time TIMESTAMP NOT NULL,
                    checksum TEXT NOT NULL,
                    checksum_type TEXT DEFAULT 'sha256',
                    last_checked TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 处理缓存表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS processing_cache (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_path TEXT NOT NULL,
                    file_checksum TEXT NOT NULL,
                    processing_result_id TEXT NOT NULL,
                    processing_time TIMESTAMP NOT NULL,
                    processing_version TEXT DEFAULT '1.0',
                    metadata TEXT,  -- JSON格式
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(file_path, file_checksum)
                )
            """)
            
            # 创建索引
            conn.execute("CREATE INDEX IF NOT EXISTS idx_file_checksums_path ON file_checksums(file_path)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_file_checksums_checksum ON file_checksums(checksum)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_processing_cache_path ON processing_cache(file_path)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_processing_cache_checksum ON processing_cache(file_checksum)")
            
            conn.commit()
    
    def save_file_checksum(self, file_checksum: FileChecksum):
        """保存文件校验和"""
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO file_checksums 
                    (file_path, file_size, modification_time, checksum, checksum_type, last_checked, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (
                    file_checksum.file_path,
                    file_checksum.file_size,
                    file_checksum.modification_time,
                    file_checksum.checksum,
                    file_checksum.checksum_type,
                    file_checksum.last_checked
                ))
                conn.commit()
    
    def get_file_checksum(self, file_path: str) -> Optional[FileChecksum]:
        """获取文件校验和"""
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT file_path, file_size, modification_time, checksum, checksum_type, last_checked
                    FROM file_checksums WHERE file_path = ?
                """, (file_path,))
                
                row = cursor.fetchone()
                if row:
                    return FileChecksum(
                        file_path=row[0],
                        file_size=row[1],
                        modification_time=datetime.fromisoformat(row[2]),
                        checksum=row[3],
                        checksum_type=row[4],
                        last_checked=datetime.fromisoformat(row[5])
                    )
                return None
    
    def get_all_checksums(self) -> Dict[str, FileChecksum]:
        """获取所有文件校验和"""
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT file_path, file_size, modification_time, checksum, checksum_type, last_checked
                    FROM file_checksums
                """)
                
                checksums = {}
                for row in cursor:
                    checksum = FileChecksum(
                        file_path=row[0],
                        file_size=row[1],
                        modification_time=datetime.fromisoformat(row[2]),
                        checksum=row[3],
                        checksum_type=row[4],
                        last_checked=datetime.fromisoformat(row[5])
                    )
                    checksums[row[0]] = checksum
                
                return checksums
    
    def save_processing_cache(self, cache: ProcessingCache):
        """保存处理缓存"""
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO processing_cache 
                    (file_path, file_checksum, processing_result_id, processing_time, processing_version, metadata)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    cache.file_path,
                    cache.file_checksum,
                    cache.processing_result_id,
                    cache.processing_time,
                    cache.processing_version,
                    json.dumps(cache.metadata)
                ))
                conn.commit()
    
    def get_processing_cache(self, file_path: str, file_checksum: str) -> Optional[ProcessingCache]:
        """获取处理缓存"""
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT file_path, file_checksum, processing_result_id, processing_time, processing_version, metadata
                    FROM processing_cache WHERE file_path = ? AND file_checksum = ?
                """, (file_path, file_checksum))
                
                row = cursor.fetchone()
                if row:
                    return ProcessingCache(
                        file_path=row[0],
                        file_checksum=row[1],
                        processing_result_id=row[2],
                        processing_time=datetime.fromisoformat(row[3]),
                        processing_version=row[4],
                        metadata=json.loads(row[5]) if row[5] else {}
                    )
                return None
    
    def remove_file_records(self, file_path: str):
        """删除文件相关记录"""
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("DELETE FROM file_checksums WHERE file_path = ?", (file_path,))
                conn.execute("DELETE FROM processing_cache WHERE file_path = ?", (file_path,))
                conn.commit()
    
    def cleanup_old_records(self, days_threshold: int = 30):
        """清理旧记录"""
        cutoff_date = datetime.now() - timedelta(days=days_threshold)
        
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                # 删除旧的校验和记录（如果对应文件不存在）
                cursor = conn.execute("""
                    SELECT file_path FROM file_checksums 
                    WHERE last_checked < ? 
                """, (cutoff_date,))
                
                old_files = [row[0] for row in cursor]
                deleted_count = 0
                
                for file_path in old_files:
                    if not Path(file_path).exists():
                        self.remove_file_records(file_path)
                        deleted_count += 1
                
                self.logger.info(f"清理了 {deleted_count} 个过期记录")


class ChangeDetector:
    """变化检测器"""
    
    def __init__(self, config: ETLConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # 初始化组件
        self.checksum_calculator = ChecksumCalculator()
        self.database = IncrementalDatabase(config.OUTPUT_DIR / "incremental" / "incremental.db")
        
        # 检测配置
        self.use_fast_checksum = True  # 优先使用快速校验和
        self.parallel_processing = True
        self.batch_size = 20
    
    def detect_changes(self, source_directory: Path, file_patterns: List[str] = None) -> ChangeDetectionResult:
        """检测文件变化"""
        self.logger.info(f"开始检测变化: {source_directory}")
        
        # 默认文件模式
        if file_patterns is None:
            file_patterns = ["*.pdf", "*.doc", "*.docx", "*.txt"]
        
        # 扫描当前文件
        current_files = self._scan_directory(source_directory, file_patterns)
        self.logger.info(f"发现 {len(current_files)} 个文件")
        
        # 获取历史校验和
        historical_checksums = self.database.get_all_checksums()
        self.logger.info(f"历史记录中有 {len(historical_checksums)} 个文件")
        
        # 检测变化
        result = self._compare_files(current_files, historical_checksums)
        
        # 更新数据库
        self._update_database(result, current_files)
        
        # 清理旧记录
        self.database.cleanup_old_records()
        
        self.logger.info(f"变化检测完成: 新增 {len(result.new_files)}, "
                        f"修改 {len(result.modified_files)}, "
                        f"删除 {len(result.deleted_files)}")
        
        return result
    
    def _scan_directory(self, directory: Path, patterns: List[str]) -> Dict[str, Path]:
        """扫描目录获取文件列表"""
        files = {}
        
        for pattern in patterns:
            for file_path in directory.glob(f"**/{pattern}"):
                if file_path.is_file():
                    files[str(file_path)] = file_path
        
        return files
    
    def _compare_files(self, current_files: Dict[str, Path], 
                      historical_checksums: Dict[str, FileChecksum]) -> ChangeDetectionResult:
        """比较文件变化"""
        result = ChangeDetectionResult()
        
        current_paths = set(current_files.keys())
        historical_paths = set(historical_checksums.keys())
        
        # 新文件
        new_paths = current_paths - historical_paths
        result.new_files = [current_files[path] for path in new_paths]
        
        # 删除的文件
        deleted_paths = historical_paths - current_paths
        result.deleted_files = [Path(path) for path in deleted_paths]
        
        # 检查可能修改的文件
        common_paths = current_paths & historical_paths
        
        for file_path_str in common_paths:
            file_path = current_files[file_path_str]
            historical_checksum = historical_checksums[file_path_str]
            
            # 检查文件是否修改
            if self._is_file_modified(file_path, historical_checksum):
                result.modified_files.append(file_path)
            else:
                result.unchanged_files.append(file_path)
        
        return result
    
    def _is_file_modified(self, file_path: Path, historical_checksum: FileChecksum) -> bool:
        """检查文件是否被修改"""
        try:
            stat = file_path.stat()
            current_modification_time = datetime.fromtimestamp(stat.st_mtime)
            
            # 快速检查：大小和修改时间
            if (stat.st_size != historical_checksum.file_size or 
                abs((current_modification_time - historical_checksum.modification_time).total_seconds()) > 1):
                return True
            
            # 如果启用了精确校验和检查
            if not self.use_fast_checksum:
                current_checksum = self.checksum_calculator.calculate_file_checksum(file_path)
                return current_checksum != historical_checksum.checksum
            
            return False
            
        except Exception as e:
            self.logger.warning(f"检查文件修改状态失败 {file_path}: {e}")
            return True  # 保守处理，认为文件已修改
    
    def _update_database(self, result: ChangeDetectionResult, current_files: Dict[str, Path]):
        """更新数据库记录"""
        
        # 为新文件和修改文件生成校验和
        files_to_update = result.new_files + result.modified_files
        
        self.logger.info(f"更新 {len(files_to_update)} 个文件的校验和")
        
        for file_path in files_to_update:
            try:
                stat = file_path.stat()
                
                # 计算校验和
                if self.use_fast_checksum:
                    checksum = self.checksum_calculator.calculate_fast_checksum(file_path)
                    checksum_type = "fast"
                else:
                    checksum = self.checksum_calculator.calculate_file_checksum(file_path)
                    checksum_type = "sha256"
                
                # 创建校验和记录
                file_checksum = FileChecksum(
                    file_path=str(file_path),
                    file_size=stat.st_size,
                    modification_time=datetime.fromtimestamp(stat.st_mtime),
                    checksum=checksum,
                    checksum_type=checksum_type
                )
                
                # 保存到数据库
                self.database.save_file_checksum(file_checksum)
                
            except Exception as e:
                self.logger.error(f"更新文件校验和失败 {file_path}: {e}")
        
        # 删除已删除文件的记录
        for file_path in result.deleted_files:
            self.database.remove_file_records(str(file_path))


class IncrementalProcessor:
    """增量处理器"""
    
    def __init__(self, config: ETLConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # 初始化组件
        self.change_detector = ChangeDetector(config)
        self.database = IncrementalDatabase(config.OUTPUT_DIR / "incremental" / "incremental.db")
        
        # 处理版本（用于兼容性检查）
        self.processing_version = "1.0"
    
    def should_process_file(self, file_path: Path) -> Tuple[bool, Optional[str]]:
        """判断是否需要处理文件"""
        try:
            # 计算当前文件校验和
            if self.change_detector.use_fast_checksum:
                current_checksum = self.change_detector.checksum_calculator.calculate_fast_checksum(file_path)
            else:
                current_checksum = self.change_detector.checksum_calculator.calculate_file_checksum(file_path)
            
            # 检查处理缓存
            cache = self.database.get_processing_cache(str(file_path), current_checksum)
            
            if cache and cache.processing_version == self.processing_version:
                self.logger.debug(f"文件已处理，跳过: {file_path}")
                return False, cache.processing_result_id
            
            self.logger.debug(f"文件需要处理: {file_path}")
            return True, None
            
        except Exception as e:
            self.logger.error(f"检查文件处理状态失败 {file_path}: {e}")
            return True, None  # 出错时保守处理
    
    def mark_file_processed(self, file_path: Path, processing_result_id: str, metadata: Dict[str, Any] = None):
        """标记文件已处理"""
        try:
            # 计算文件校验和
            if self.change_detector.use_fast_checksum:
                checksum = self.change_detector.checksum_calculator.calculate_fast_checksum(file_path)
            else:
                checksum = self.change_detector.checksum_calculator.calculate_file_checksum(file_path)
            
            # 创建处理缓存记录
            cache = ProcessingCache(
                file_path=str(file_path),
                file_checksum=checksum,
                processing_result_id=processing_result_id,
                processing_time=datetime.now(),
                processing_version=self.processing_version,
                metadata=metadata or {}
            )
            
            # 保存到数据库
            self.database.save_processing_cache(cache)
            
            self.logger.debug(f"文件处理完成标记: {file_path}")
            
        except Exception as e:
            self.logger.error(f"标记文件处理完成失败 {file_path}: {e}")
    
    def get_cached_result(self, file_path: Path) -> Optional[str]:
        """获取缓存的处理结果"""
        needs_processing, cached_id = self.should_process_file(file_path)
        
        if not needs_processing and cached_id:
            return cached_id
        
        return None
    
    def invalidate_cache(self, file_path: Path = None):
        """使缓存失效"""
        if file_path:
            # 删除特定文件的缓存
            self.database.remove_file_records(str(file_path))
            self.logger.info(f"清除文件缓存: {file_path}")
        else:
            # 清除所有缓存（通过升级版本号）
            self.processing_version = f"1.{int(time.time())}"
            self.logger.info(f"升级处理版本: {self.processing_version}")
    
    def get_processing_statistics(self) -> Dict[str, Any]:
        """获取处理统计"""
        with sqlite3.connect(self.database.db_path) as conn:
            # 总文件数
            cursor = conn.execute("SELECT COUNT(*) FROM file_checksums")
            total_files = cursor.fetchone()[0]
            
            # 已处理文件数
            cursor = conn.execute("""
                SELECT COUNT(DISTINCT file_path) FROM processing_cache 
                WHERE processing_version = ?
            """, (self.processing_version,))
            processed_files = cursor.fetchone()[0]
            
            # 最近处理的文件
            cursor = conn.execute("""
                SELECT COUNT(*) FROM processing_cache 
                WHERE processing_time > datetime('now', '-1 day')
            """)
            recent_processed = cursor.fetchone()[0]
            
            return {
                "total_files": total_files,
                "processed_files": processed_files,
                "recent_processed": recent_processed,
                "processing_version": self.processing_version,
                "cache_hit_rate": (processed_files / total_files * 100) if total_files > 0 else 0
            }


class SmartIncrementalETL:
    """智能增量ETL处理器"""
    
    def __init__(self, config: ETLConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # 初始化组件
        self.change_detector = ChangeDetector(config)
        self.incremental_processor = IncrementalProcessor(config)
        
        # 处理策略配置
        self.max_batch_size = 50
        self.force_full_scan_interval_hours = 24  # 24小时强制全量扫描一次
        self.last_full_scan: Optional[datetime] = None
    
    def process_incremental_updates(self, source_directory: Path, 
                                   processor_func, 
                                   **processor_kwargs) -> Dict[str, Any]:
        """处理增量更新"""
        
        start_time = datetime.now()
        self.logger.info("开始增量ETL处理")
        
        # 检查是否需要全量扫描
        force_full_scan = self._should_force_full_scan()
        
        if force_full_scan:
            self.logger.info("执行强制全量扫描")
            self.incremental_processor.invalidate_cache()
        
        # 检测变化
        changes = self.change_detector.detect_changes(source_directory)
        
        if not changes.has_changes and not force_full_scan:
            self.logger.info("未检测到文件变化，跳过处理")
            return {
                "status": "skipped",
                "reason": "no_changes",
                "processing_time": 0,
                "files_processed": 0
            }
        
        # 确定需要处理的文件
        files_to_process = self._determine_files_to_process(changes, force_full_scan, source_directory)
        
        if not files_to_process:
            self.logger.info("没有需要处理的文件")
            return {
                "status": "completed",
                "files_processed": 0,
                "processing_time": (datetime.now() - start_time).total_seconds()
            }
        
        self.logger.info(f"需要处理 {len(files_to_process)} 个文件")
        
        # 批量处理文件
        processing_results = self._batch_process_files(files_to_process, processor_func, **processor_kwargs)
        
        # 更新处理记录
        self._update_processing_records(processing_results)
        
        # 更新最后全量扫描时间
        if force_full_scan:
            self.last_full_scan = start_time
        
        # 生成处理报告
        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()
        
        report = {
            "status": "completed",
            "processing_time": processing_time,
            "files_processed": len(processing_results),
            "successful_files": len([r for r in processing_results if r['success']]),
            "failed_files": len([r for r in processing_results if not r['success']]),
            "changes_detected": {
                "new_files": len(changes.new_files),
                "modified_files": len(changes.modified_files),
                "deleted_files": len(changes.deleted_files)
            },
            "force_full_scan": force_full_scan,
            "processing_statistics": self.incremental_processor.get_processing_statistics()
        }
        
        self.logger.info(f"增量处理完成: {report}")
        
        return report
    
    def _should_force_full_scan(self) -> bool:
        """判断是否需要强制全量扫描"""
        if self.last_full_scan is None:
            return True
        
        hours_since_last_scan = (datetime.now() - self.last_full_scan).total_seconds() / 3600
        return hours_since_last_scan >= self.force_full_scan_interval_hours
    
    def _determine_files_to_process(self, changes: ChangeDetectionResult, 
                                  force_full_scan: bool, 
                                  source_directory: Path) -> List[Path]:
        """确定需要处理的文件"""
        files_to_process = []
        
        if force_full_scan:
            # 全量扫描：处理所有文件
            all_files = self.change_detector._scan_directory(source_directory, ["*.pdf"])
            
            for file_path in all_files.values():
                needs_processing, _ = self.incremental_processor.should_process_file(file_path)
                if needs_processing:
                    files_to_process.append(file_path)
        else:
            # 增量扫描：只处理变化的文件
            for file_path in changes.new_files + changes.modified_files:
                needs_processing, _ = self.incremental_processor.should_process_file(file_path)
                if needs_processing:
                    files_to_process.append(file_path)
        
        return files_to_process
    
    def _batch_process_files(self, files: List[Path], processor_func, **kwargs) -> List[Dict[str, Any]]:
        """批量处理文件"""
        results = []
        
        # 分批处理
        for i in range(0, len(files), self.max_batch_size):
            batch = files[i:i + self.max_batch_size]
            self.logger.info(f"处理批次 {i // self.max_batch_size + 1}: {len(batch)} 个文件")
            
            batch_results = self._process_file_batch(batch, processor_func, **kwargs)
            results.extend(batch_results)
        
        return results
    
    def _process_file_batch(self, batch: List[Path], processor_func, **kwargs) -> List[Dict[str, Any]]:
        """处理文件批次"""
        results = []
        
        for file_path in batch:
            try:
                # 检查缓存
                cached_result = self.incremental_processor.get_cached_result(file_path)
                
                if cached_result:
                    self.logger.debug(f"使用缓存结果: {file_path}")
                    results.append({
                        "file_path": str(file_path),
                        "success": True,
                        "cached": True,
                        "result_id": cached_result,
                        "processing_time": 0
                    })
                    continue
                
                # 处理文件
                start_time = time.time()
                
                try:
                    result = processor_func(file_path, **kwargs)
                    processing_time = time.time() - start_time
                    
                    # 生成结果ID
                    result_id = hashlib.md5(f"{file_path}:{time.time()}".encode()).hexdigest()
                    
                    results.append({
                        "file_path": str(file_path),
                        "success": True,
                        "cached": False,
                        "result_id": result_id,
                        "result": result,
                        "processing_time": processing_time
                    })
                    
                    self.logger.info(f"文件处理成功: {file_path}")
                    
                except Exception as e:
                    processing_time = time.time() - start_time
                    
                    results.append({
                        "file_path": str(file_path),
                        "success": False,
                        "cached": False,
                        "error": str(e),
                        "processing_time": processing_time
                    })
                    
                    self.logger.error(f"文件处理失败 {file_path}: {e}")
                    
            except Exception as e:
                self.logger.error(f"批次处理异常 {file_path}: {e}")
                results.append({
                    "file_path": str(file_path),
                    "success": False,
                    "cached": False,
                    "error": str(e),
                    "processing_time": 0
                })
        
        return results
    
    def _update_processing_records(self, results: List[Dict[str, Any]]):
        """更新处理记录"""
        for result in results:
            if result["success"] and not result["cached"]:
                file_path = Path(result["file_path"])
                result_id = result["result_id"]
                
                metadata = {
                    "processing_time": result["processing_time"],
                    "timestamp": datetime.now().isoformat()
                }
                
                self.incremental_processor.mark_file_processed(file_path, result_id, metadata)


# =============================================================================
# 使用示例
# =============================================================================

if __name__ == "__main__":
    from pathlib import Path
    import time
    
    # 示例处理函数
    def sample_processor(file_path: Path) -> str:
        """示例处理函数"""
        time.sleep(0.1)  # 模拟处理时间
        return f"处理完成: {file_path.name}"
    
    # 创建配置和智能增量处理器
    config = ETLConfig()
    smart_etl = SmartIncrementalETL(config)
    
    # 执行增量处理
    source_dir = Path("/mnt/d/desktop/appp/data")
    
    if source_dir.exists():
        result = smart_etl.process_incremental_updates(
            source_directory=source_dir,
            processor_func=sample_processor
        )
        
        print("处理结果:")
        print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    else:
        print(f"源目录不存在: {source_dir}")
        
        # 创建模拟数据进行测试
        test_dir = Path("/tmp/test_incremental")
        test_dir.mkdir(exist_ok=True)
        
        # 创建测试文件
        for i in range(5):
            test_file = test_dir / f"test_{i}.pdf"
            test_file.write_text(f"Test content {i}")
        
        print("使用测试目录进行演示...")
        result = smart_etl.process_incremental_updates(
            source_directory=test_dir,
            processor_func=sample_processor
        )
        
        print("处理结果:")
        print(json.dumps(result, indent=2, ensure_ascii=False, default=str))