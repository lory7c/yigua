#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
云端数据同步服务
支持增量更新、冲突解决、压缩传输的企业级数据同步方案

核心功能:
1. 增量数据同步
2. 版本控制和冲突解决
3. 数据压缩和传输优化
4. 离线数据缓存
5. 同步状态监控
6. 多设备数据一致性

作者: Claude
版本: 2.0.0
"""

import asyncio
import gzip
import json
import hashlib
import logging
import time
import zlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Set
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum
import uuid

import redis.asyncio as redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
import aiofiles

# 导入系统模块
import sys
sys.path.append(str(Path(__file__).parent.parent))

from database.db_manager import DatabaseManager

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SyncStatus(Enum):
    """同步状态枚举"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CONFLICT = "conflict"

class ConflictResolution(Enum):
    """冲突解决策略"""
    CLIENT_WINS = "client_wins"
    SERVER_WINS = "server_wins"
    MERGE = "merge"
    MANUAL = "manual"

@dataclass
class DataChange:
    """数据变更记录"""
    id: str
    table_name: str
    operation: str  # INSERT, UPDATE, DELETE
    data: Dict[str, Any]
    timestamp: datetime
    version: str
    checksum: str
    user_id: str
    device_id: str

@dataclass
class SyncSession:
    """同步会话"""
    session_id: str
    client_id: str
    user_id: str
    start_time: datetime
    last_sync_time: Optional[datetime]
    device_info: Dict[str, Any]
    data_version: str
    status: SyncStatus
    total_changes: int = 0
    processed_changes: int = 0
    conflicts: List[str] = None
    
    def __post_init__(self):
        if self.conflicts is None:
            self.conflicts = []

@dataclass
class ConflictRecord:
    """冲突记录"""
    conflict_id: str
    session_id: str
    table_name: str
    record_id: str
    client_data: Dict[str, Any]
    server_data: Dict[str, Any]
    client_version: str
    server_version: str
    timestamp: datetime
    resolution: Optional[ConflictResolution] = None
    resolved_data: Optional[Dict[str, Any]] = None

class DataSyncService:
    """数据同步服务"""
    
    def __init__(self, 
                 db_manager: DatabaseManager,
                 redis_client: redis.Redis,
                 compression_level: int = 6):
        """
        初始化数据同步服务
        
        Args:
            db_manager: 数据库管理器
            redis_client: Redis客户端
            compression_level: 压缩级别 (1-9)
        """
        self.db_manager = db_manager
        self.redis = redis_client
        self.compression_level = compression_level
        self.active_sessions: Dict[str, SyncSession] = {}
        
        # 同步配置
        self.sync_config = {
            "batch_size": 1000,
            "max_session_time": 3600,  # 1小时
            "conflict_retention_days": 30,
            "compression_threshold": 1024,  # 1KB以上压缩
            "max_retries": 3,
            "retry_delay": 5.0
        }
    
    async def start_sync_session(self, 
                                client_id: str, 
                                user_id: str,
                                last_sync_time: Optional[datetime] = None,
                                device_info: Dict[str, Any] = None,
                                data_version: str = "1.0.0") -> SyncSession:
        """
        开始同步会话
        
        Args:
            client_id: 客户端唯一标识
            user_id: 用户ID
            last_sync_time: 上次同步时间
            device_info: 设备信息
            data_version: 数据版本
            
        Returns:
            同步会话对象
        """
        session_id = str(uuid.uuid4())
        
        session = SyncSession(
            session_id=session_id,
            client_id=client_id,
            user_id=user_id,
            start_time=datetime.now(),
            last_sync_time=last_sync_time,
            device_info=device_info or {},
            data_version=data_version,
            status=SyncStatus.PENDING
        )
        
        self.active_sessions[session_id] = session
        
        # 保存会话到Redis
        await self.redis.hset(
            f"sync_session:{session_id}",
            mapping={
                "session_data": json.dumps(asdict(session), default=str),
                "created_at": datetime.now().isoformat()
            }
        )
        await self.redis.expire(f"sync_session:{session_id}", self.sync_config["max_session_time"])
        
        logger.info(f"同步会话已创建: {session_id} for user: {user_id}")
        return session
    
    async def get_incremental_changes(self, 
                                    session: SyncSession,
                                    tables: List[str] = None) -> List[DataChange]:
        """
        获取增量数据变更
        
        Args:
            session: 同步会话
            tables: 要同步的表名列表，None表示所有表
            
        Returns:
            数据变更列表
        """
        changes = []
        
        try:
            with self.db_manager.get_connection() as conn:
                # 如果没有指定表，获取所有需要同步的表
                if tables is None:
                    tables = ['hexagrams', 'yao_lines', 'interpretations', 'divination_records']
                
                for table_name in tables:
                    # 查询变更日志
                    cursor = conn.cursor()
                    
                    if session.last_sync_time:
                        cursor.execute(f"""
                            SELECT * FROM {table_name}_changelog 
                            WHERE timestamp > ? AND user_id = ?
                            ORDER BY timestamp ASC
                        """, (session.last_sync_time, session.user_id))
                    else:
                        # 首次同步，获取所有数据
                        cursor.execute(f"""
                            SELECT id, 'INSERT' as operation, * FROM {table_name}
                            WHERE user_id = ? OR user_id IS NULL
                            ORDER BY id
                        """, (session.user_id,))
                    
                    for row in cursor.fetchall():
                        data_dict = dict(zip([col[0] for col in cursor.description], row))
                        
                        # 计算数据校验和
                        checksum = self._calculate_checksum(data_dict)
                        
                        change = DataChange(
                            id=str(uuid.uuid4()),
                            table_name=table_name,
                            operation=data_dict.get('operation', 'INSERT'),
                            data=data_dict,
                            timestamp=datetime.now(),
                            version=session.data_version,
                            checksum=checksum,
                            user_id=session.user_id,
                            device_id=session.client_id
                        )
                        
                        changes.append(change)
                
                session.total_changes = len(changes)
                logger.info(f"获取到 {len(changes)} 个增量变更")
                
        except Exception as e:
            logger.error(f"获取增量变更失败: {e}")
            raise
        
        return changes
    
    async def apply_client_changes(self, 
                                 session: SyncSession,
                                 client_changes: List[Dict[str, Any]]) -> Tuple[List[str], List[ConflictRecord]]:
        """
        应用客户端变更
        
        Args:
            session: 同步会话
            client_changes: 客户端变更列表
            
        Returns:
            (成功应用的变更ID列表, 冲突记录列表)
        """
        applied_changes = []
        conflicts = []
        
        session.status = SyncStatus.IN_PROGRESS
        
        try:
            with self.db_manager.get_connection() as conn:
                conn.execute("BEGIN TRANSACTION")
                
                for change_data in client_changes:
                    change_id = change_data.get('id', str(uuid.uuid4()))
                    table_name = change_data['table_name']
                    operation = change_data['operation']
                    data = change_data['data']
                    client_version = change_data.get('version', '1.0.0')
                    
                    try:
                        # 检查是否存在冲突
                        conflict = await self._detect_conflict(
                            conn, table_name, data, client_version, session
                        )
                        
                        if conflict:
                            conflicts.append(conflict)
                            logger.warning(f"检测到冲突: {change_id}")
                            continue
                        
                        # 应用变更
                        success = await self._apply_change(conn, table_name, operation, data, session)
                        
                        if success:
                            applied_changes.append(change_id)
                            session.processed_changes += 1
                            
                            # 记录变更日志
                            await self._log_change(conn, table_name, operation, data, session)
                        
                    except Exception as e:
                        logger.error(f"应用变更失败 {change_id}: {e}")
                        continue
                
                conn.commit()
                logger.info(f"成功应用 {len(applied_changes)} 个变更，{len(conflicts)} 个冲突")
                
        except Exception as e:
            conn.rollback()
            logger.error(f"应用客户端变更失败: {e}")
            session.status = SyncStatus.FAILED
            raise
        
        return applied_changes, conflicts
    
    async def _detect_conflict(self, 
                             conn, 
                             table_name: str, 
                             client_data: Dict[str, Any],
                             client_version: str,
                             session: SyncSession) -> Optional[ConflictRecord]:
        """检测数据冲突"""
        record_id = client_data.get('id')
        if not record_id:
            return None
        
        try:
            # 查询服务器端当前数据
            cursor = conn.cursor()
            cursor.execute(f"SELECT * FROM {table_name} WHERE id = ?", (record_id,))
            server_row = cursor.fetchone()
            
            if server_row:
                server_data = dict(zip([col[0] for col in cursor.description], server_row))
                
                # 查询服务器端版本信息
                cursor.execute(f"""
                    SELECT version, timestamp FROM {table_name}_changelog 
                    WHERE record_id = ? ORDER BY timestamp DESC LIMIT 1
                """, (record_id,))
                version_row = cursor.fetchone()
                
                server_version = version_row[0] if version_row else "1.0.0"
                
                # 检查版本冲突
                if client_version != server_version:
                    # 检查数据内容是否实际不同
                    client_checksum = self._calculate_checksum(client_data)
                    server_checksum = self._calculate_checksum(server_data)
                    
                    if client_checksum != server_checksum:
                        conflict = ConflictRecord(
                            conflict_id=str(uuid.uuid4()),
                            session_id=session.session_id,
                            table_name=table_name,
                            record_id=record_id,
                            client_data=client_data,
                            server_data=server_data,
                            client_version=client_version,
                            server_version=server_version,
                            timestamp=datetime.now()
                        )
                        
                        # 保存冲突记录
                        await self._save_conflict_record(conn, conflict)
                        
                        return conflict
        
        except Exception as e:
            logger.error(f"冲突检测失败: {e}")
        
        return None
    
    async def _apply_change(self, 
                          conn, 
                          table_name: str, 
                          operation: str, 
                          data: Dict[str, Any],
                          session: SyncSession) -> bool:
        """应用单个数据变更"""
        try:
            cursor = conn.cursor()
            
            if operation == "INSERT":
                # 构建INSERT语句
                columns = list(data.keys())
                placeholders = ["?" * len(columns)]
                values = list(data.values())
                
                sql = f"INSERT OR REPLACE INTO {table_name} ({', '.join(columns)}) VALUES ({', '.join(placeholders)})"
                cursor.execute(sql, values)
                
            elif operation == "UPDATE":
                # 构建UPDATE语句
                record_id = data.pop('id')
                set_clause = ", ".join([f"{k} = ?" for k in data.keys()])
                values = list(data.values()) + [record_id]
                
                sql = f"UPDATE {table_name} SET {set_clause} WHERE id = ?"
                cursor.execute(sql, values)
                
            elif operation == "DELETE":
                # DELETE操作
                record_id = data.get('id')
                sql = f"DELETE FROM {table_name} WHERE id = ?"
                cursor.execute(sql, (record_id,))
            
            return True
            
        except Exception as e:
            logger.error(f"应用变更失败 {operation} on {table_name}: {e}")
            return False
    
    async def _log_change(self, 
                        conn, 
                        table_name: str, 
                        operation: str, 
                        data: Dict[str, Any],
                        session: SyncSession):
        """记录数据变更日志"""
        try:
            changelog_table = f"{table_name}_changelog"
            
            cursor = conn.cursor()
            cursor.execute(f"""
                INSERT INTO {changelog_table} 
                (record_id, operation, data, timestamp, version, user_id, device_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                data.get('id'),
                operation,
                json.dumps(data),
                datetime.now(),
                session.data_version,
                session.user_id,
                session.client_id
            ))
            
        except Exception as e:
            logger.error(f"记录变更日志失败: {e}")
    
    async def _save_conflict_record(self, conn, conflict: ConflictRecord):
        """保存冲突记录"""
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO sync_conflicts 
                (conflict_id, session_id, table_name, record_id, client_data, server_data, 
                 client_version, server_version, timestamp, resolution)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                conflict.conflict_id,
                conflict.session_id,
                conflict.table_name,
                conflict.record_id,
                json.dumps(conflict.client_data),
                json.dumps(conflict.server_data),
                conflict.client_version,
                conflict.server_version,
                conflict.timestamp,
                conflict.resolution.value if conflict.resolution else None
            ))
            
        except Exception as e:
            logger.error(f"保存冲突记录失败: {e}")
    
    def _calculate_checksum(self, data: Dict[str, Any]) -> str:
        """计算数据校验和"""
        # 排序键以确保一致性
        sorted_data = json.dumps(data, sort_keys=True, default=str)
        return hashlib.md5(sorted_data.encode()).hexdigest()
    
    async def compress_data(self, data: Any) -> Tuple[bytes, bool]:
        """
        压缩数据
        
        Args:
            data: 要压缩的数据
            
        Returns:
            (压缩后的字节数据, 是否已压缩)
        """
        json_data = json.dumps(data, default=str)
        raw_bytes = json_data.encode('utf-8')
        
        # 如果数据小于阈值，不压缩
        if len(raw_bytes) < self.sync_config["compression_threshold"]:
            return raw_bytes, False
        
        # 使用gzip压缩
        compressed_bytes = gzip.compress(raw_bytes, compresslevel=self.compression_level)
        
        # 如果压缩后反而更大，返回原始数据
        if len(compressed_bytes) >= len(raw_bytes):
            return raw_bytes, False
        
        return compressed_bytes, True
    
    async def decompress_data(self, data: bytes, is_compressed: bool) -> Any:
        """
        解压数据
        
        Args:
            data: 字节数据
            is_compressed: 是否已压缩
            
        Returns:
            解压后的数据
        """
        if is_compressed:
            json_str = gzip.decompress(data).decode('utf-8')
        else:
            json_str = data.decode('utf-8')
        
        return json.loads(json_str)
    
    async def resolve_conflicts(self, 
                              conflict_ids: List[str], 
                              resolution_strategy: ConflictResolution,
                              custom_data: Dict[str, Any] = None) -> List[str]:
        """
        解决冲突
        
        Args:
            conflict_ids: 冲突ID列表
            resolution_strategy: 解决策略
            custom_data: 自定义解决数据
            
        Returns:
            已解决的冲突ID列表
        """
        resolved_conflicts = []
        
        try:
            with self.db_manager.get_connection() as conn:
                conn.execute("BEGIN TRANSACTION")
                
                for conflict_id in conflict_ids:
                    # 获取冲突记录
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT * FROM sync_conflicts WHERE conflict_id = ?
                    """, (conflict_id,))
                    
                    conflict_row = cursor.fetchone()
                    if not conflict_row:
                        continue
                    
                    # 解析冲突数据
                    conflict_data = dict(zip([col[0] for col in cursor.description], conflict_row))
                    client_data = json.loads(conflict_data['client_data'])
                    server_data = json.loads(conflict_data['server_data'])
                    
                    # 根据策略解决冲突
                    resolved_data = None
                    
                    if resolution_strategy == ConflictResolution.CLIENT_WINS:
                        resolved_data = client_data
                    elif resolution_strategy == ConflictResolution.SERVER_WINS:
                        resolved_data = server_data
                    elif resolution_strategy == ConflictResolution.MERGE:
                        resolved_data = self._merge_data(client_data, server_data)
                    elif resolution_strategy == ConflictResolution.MANUAL and custom_data:
                        resolved_data = custom_data.get(conflict_id)
                    
                    if resolved_data:
                        # 应用解决方案
                        table_name = conflict_data['table_name']
                        record_id = conflict_data['record_id']
                        
                        # 更新数据
                        set_clause = ", ".join([f"{k} = ?" for k in resolved_data.keys() if k != 'id'])
                        values = [v for k, v in resolved_data.items() if k != 'id'] + [record_id]
                        
                        cursor.execute(f"""
                            UPDATE {table_name} SET {set_clause} WHERE id = ?
                        """, values)
                        
                        # 更新冲突状态
                        cursor.execute("""
                            UPDATE sync_conflicts 
                            SET resolution = ?, resolved_data = ?, resolved_at = ?
                            WHERE conflict_id = ?
                        """, (
                            resolution_strategy.value,
                            json.dumps(resolved_data),
                            datetime.now(),
                            conflict_id
                        ))
                        
                        resolved_conflicts.append(conflict_id)
                
                conn.commit()
                logger.info(f"已解决 {len(resolved_conflicts)} 个冲突")
                
        except Exception as e:
            conn.rollback()
            logger.error(f"解决冲突失败: {e}")
            raise
        
        return resolved_conflicts
    
    def _merge_data(self, client_data: Dict[str, Any], server_data: Dict[str, Any]) -> Dict[str, Any]:
        """合并客户端和服务器数据"""
        merged = server_data.copy()
        
        # 简单合并策略：客户端数据优先，但保留服务器端的时间戳
        for key, value in client_data.items():
            if key not in ['created_at', 'updated_at']:
                merged[key] = value
        
        # 更新时间戳
        merged['updated_at'] = datetime.now()
        
        return merged
    
    async def get_sync_status(self, session_id: str) -> Optional[SyncSession]:
        """获取同步状态"""
        if session_id in self.active_sessions:
            return self.active_sessions[session_id]
        
        # 从Redis获取
        session_data = await self.redis.hget(f"sync_session:{session_id}", "session_data")
        if session_data:
            data = json.loads(session_data)
            return SyncSession(**data)
        
        return None
    
    async def finalize_sync_session(self, session_id: str) -> bool:
        """完成同步会话"""
        session = await self.get_sync_status(session_id)
        if not session:
            return False
        
        try:
            # 更新会话状态
            if session.processed_changes == session.total_changes and not session.conflicts:
                session.status = SyncStatus.COMPLETED
            elif session.conflicts:
                session.status = SyncStatus.CONFLICT
            else:
                session.status = SyncStatus.FAILED
            
            # 更新Redis
            await self.redis.hset(
                f"sync_session:{session_id}",
                "session_data", json.dumps(asdict(session), default=str)
            )
            
            # 从活动会话中移除
            if session_id in self.active_sessions:
                del self.active_sessions[session_id]
            
            logger.info(f"同步会话已完成: {session_id}, 状态: {session.status}")
            return True
            
        except Exception as e:
            logger.error(f"完成同步会话失败: {e}")
            return False
    
    async def cleanup_old_conflicts(self, days: int = None):
        """清理旧冲突记录"""
        if days is None:
            days = self.sync_config["conflict_retention_days"]
        
        cutoff_date = datetime.now() - timedelta(days=days)
        
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    DELETE FROM sync_conflicts 
                    WHERE timestamp < ? AND resolution IS NOT NULL
                """, (cutoff_date,))
                
                deleted_count = cursor.rowcount
                conn.commit()
                
                logger.info(f"清理了 {deleted_count} 条旧冲突记录")
                return deleted_count
                
        except Exception as e:
            logger.error(f"清理旧冲突记录失败: {e}")
            return 0
    
    async def get_sync_statistics(self, user_id: str = None) -> Dict[str, Any]:
        """获取同步统计信息"""
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                stats = {}
                
                # 总同步会话数
                if user_id:
                    cursor.execute("""
                        SELECT COUNT(*) FROM sync_sessions WHERE user_id = ?
                    """, (user_id,))
                else:
                    cursor.execute("SELECT COUNT(*) FROM sync_sessions")
                stats['total_sessions'] = cursor.fetchone()[0]
                
                # 成功同步数
                if user_id:
                    cursor.execute("""
                        SELECT COUNT(*) FROM sync_sessions 
                        WHERE user_id = ? AND status = 'completed'
                    """, (user_id,))
                else:
                    cursor.execute("""
                        SELECT COUNT(*) FROM sync_sessions WHERE status = 'completed'
                    """)
                stats['successful_syncs'] = cursor.fetchone()[0]
                
                # 冲突数量
                if user_id:
                    cursor.execute("""
                        SELECT COUNT(*) FROM sync_conflicts sc
                        JOIN sync_sessions ss ON sc.session_id = ss.session_id
                        WHERE ss.user_id = ?
                    """, (user_id,))
                else:
                    cursor.execute("SELECT COUNT(*) FROM sync_conflicts")
                stats['total_conflicts'] = cursor.fetchone()[0]
                
                # 未解决冲突数
                cursor.execute("""
                    SELECT COUNT(*) FROM sync_conflicts WHERE resolution IS NULL
                """)
                stats['unresolved_conflicts'] = cursor.fetchone()[0]
                
                # 最近同步时间
                if user_id:
                    cursor.execute("""
                        SELECT MAX(start_time) FROM sync_sessions WHERE user_id = ?
                    """, (user_id,))
                else:
                    cursor.execute("SELECT MAX(start_time) FROM sync_sessions")
                last_sync = cursor.fetchone()[0]
                stats['last_sync_time'] = last_sync
                
                return stats
                
        except Exception as e:
            logger.error(f"获取同步统计失败: {e}")
            return {}

# 同步服务工厂
class SyncServiceFactory:
    """同步服务工厂"""
    
    @staticmethod
    def create_sync_service(db_manager: DatabaseManager, 
                          redis_client: redis.Redis) -> DataSyncService:
        """创建同步服务实例"""
        return DataSyncService(db_manager, redis_client)