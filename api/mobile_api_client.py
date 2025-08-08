#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
移动端API客户端
支持离线优先、缓存策略、数据同步的移动端API客户端

核心功能:
1. HTTP客户端封装
2. 离线数据缓存和同步
3. 请求重试和容错
4. 数据一致性保证
5. 网络状态监控
6. 批量操作优化

作者: Claude
版本: 2.0.0
"""

import asyncio
import json
import sqlite3
import hashlib
import logging
import time
import gzip
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union, Callable
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum
import uuid
import threading
from contextlib import asynccontextmanager

import aiohttp
import aiofiles
from pydantic import BaseModel, Field

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NetworkStatus(Enum):
    """网络状态"""
    ONLINE = "online"
    OFFLINE = "offline"
    LIMITED = "limited"  # 网络受限

class SyncStatus(Enum):
    """同步状态"""
    IDLE = "idle"
    SYNCING = "syncing"
    COMPLETED = "completed"
    ERROR = "error"

class CachePolicy(Enum):
    """缓存策略"""
    CACHE_FIRST = "cache_first"      # 优先使用缓存
    NETWORK_FIRST = "network_first"  # 优先网络请求
    CACHE_ONLY = "cache_only"        # 仅使用缓存
    NETWORK_ONLY = "network_only"    # 仅使用网络

@dataclass
class APIConfig:
    """API配置"""
    base_url: str = "https://api.yixue.local"
    timeout: int = 30
    retry_times: int = 3
    retry_delay: float = 1.0
    cache_ttl: int = 3600  # 1小时
    offline_retention_days: int = 30
    batch_size: int = 50
    compression_enabled: bool = True

@dataclass
class CacheEntry:
    """缓存条目"""
    key: str
    data: Any
    timestamp: datetime
    ttl: int
    etag: Optional[str] = None
    compressed: bool = False

class MobileAPIClient:
    """移动端API客户端"""
    
    def __init__(self, 
                 config: APIConfig = None,
                 cache_db_path: str = "mobile_cache.db",
                 auth_token: Optional[str] = None):
        """
        初始化移动端API客户端
        
        Args:
            config: API配置
            cache_db_path: 缓存数据库路径
            auth_token: 认证令牌
        """
        self.config = config or APIConfig()
        self.cache_db_path = cache_db_path
        self.auth_token = auth_token
        
        # 状态管理
        self.network_status = NetworkStatus.ONLINE
        self.sync_status = SyncStatus.IDLE
        self.last_sync_time: Optional[datetime] = None
        
        # 缓存和队列
        self._cache_lock = threading.Lock()
        self._offline_queue: List[Dict[str, Any]] = []
        self._sync_callbacks: List[Callable] = []
        
        # HTTP会话
        self._session: Optional[aiohttp.ClientSession] = None
        
        # 初始化缓存数据库
        self._init_cache_db()
        
        # 启动后台任务
        asyncio.create_task(self._background_sync())
        asyncio.create_task(self._network_monitor())
    
    def _init_cache_db(self):
        """初始化缓存数据库"""
        try:
            with sqlite3.connect(self.cache_db_path) as conn:
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS cache (
                        key TEXT PRIMARY KEY,
                        data TEXT NOT NULL,
                        timestamp REAL NOT NULL,
                        ttl INTEGER NOT NULL,
                        etag TEXT,
                        compressed INTEGER DEFAULT 0
                    )
                ''')
                
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS offline_queue (
                        id TEXT PRIMARY KEY,
                        method TEXT NOT NULL,
                        url TEXT NOT NULL,
                        data TEXT,
                        headers TEXT,
                        timestamp REAL NOT NULL,
                        retry_count INTEGER DEFAULT 0
                    )
                ''')
                
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS sync_log (
                        id TEXT PRIMARY KEY,
                        operation TEXT NOT NULL,
                        status TEXT NOT NULL,
                        data TEXT,
                        timestamp REAL NOT NULL,
                        error_message TEXT
                    )
                ''')
                
                # 创建索引
                conn.execute('CREATE INDEX IF NOT EXISTS idx_cache_timestamp ON cache(timestamp)')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_queue_timestamp ON offline_queue(timestamp)')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_sync_timestamp ON sync_log(timestamp)')
                
                conn.commit()
                logger.info("缓存数据库初始化完成")
                
        except Exception as e:
            logger.error(f"缓存数据库初始化失败: {e}")
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """获取HTTP会话"""
        if self._session is None or self._session.closed:
            headers = {
                'Content-Type': 'application/json',
                'User-Agent': 'YiXue-Mobile-Client/2.0.0'
            }
            
            if self.auth_token:
                headers['Authorization'] = f'Bearer {self.auth_token}'
            
            timeout = aiohttp.ClientTimeout(total=self.config.timeout)
            self._session = aiohttp.ClientSession(
                headers=headers,
                timeout=timeout
            )
        
        return self._session
    
    async def close(self):
        """关闭客户端"""
        if self._session and not self._session.closed:
            await self._session.close()
    
    def set_auth_token(self, token: str):
        """设置认证令牌"""
        self.auth_token = token
        # 重新创建会话以更新认证头
        if self._session:
            asyncio.create_task(self._session.close())
            self._session = None
    
    def add_sync_callback(self, callback: Callable):
        """添加同步回调函数"""
        self._sync_callbacks.append(callback)
    
    def remove_sync_callback(self, callback: Callable):
        """移除同步回调函数"""
        if callback in self._sync_callbacks:
            self._sync_callbacks.remove(callback)
    
    async def _network_monitor(self):
        """网络状态监控"""
        while True:
            try:
                # 简单的网络检测 - 尝试访问健康检查端点
                async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
                    async with session.get(f"{self.config.base_url}/health") as response:
                        if response.status == 200:
                            old_status = self.network_status
                            self.network_status = NetworkStatus.ONLINE
                            
                            # 如果网络从离线变为在线，触发同步
                            if old_status == NetworkStatus.OFFLINE:
                                logger.info("网络连接已恢复，开始同步...")
                                asyncio.create_task(self._sync_offline_queue())
                        else:
                            self.network_status = NetworkStatus.LIMITED
            
            except Exception:
                self.network_status = NetworkStatus.OFFLINE
            
            # 每30秒检查一次网络状态
            await asyncio.sleep(30)
    
    async def _background_sync(self):
        """后台同步任务"""
        while True:
            try:
                if (self.network_status == NetworkStatus.ONLINE and 
                    self.sync_status == SyncStatus.IDLE and
                    len(self._offline_queue) > 0):
                    
                    await self._sync_offline_queue()
                
                # 清理过期缓存
                await self._cleanup_expired_cache()
                
                # 定期全量同步（每小时）
                if (self.last_sync_time is None or 
                    datetime.now() - self.last_sync_time > timedelta(hours=1)):
                    await self._full_sync()
                
            except Exception as e:
                logger.error(f"后台同步任务失败: {e}")
            
            # 每分钟执行一次
            await asyncio.sleep(60)
    
    async def get(self, 
                  endpoint: str, 
                  params: Dict[str, Any] = None,
                  cache_policy: CachePolicy = CachePolicy.CACHE_FIRST) -> Dict[str, Any]:
        """GET请求"""
        return await self._request('GET', endpoint, params=params, cache_policy=cache_policy)
    
    async def post(self, 
                   endpoint: str, 
                   data: Dict[str, Any] = None,
                   cache_policy: CachePolicy = CachePolicy.NETWORK_FIRST) -> Dict[str, Any]:
        """POST请求"""
        return await self._request('POST', endpoint, json_data=data, cache_policy=cache_policy)
    
    async def put(self, 
                  endpoint: str, 
                  data: Dict[str, Any] = None,
                  cache_policy: CachePolicy = CachePolicy.NETWORK_FIRST) -> Dict[str, Any]:
        """PUT请求"""
        return await self._request('PUT', endpoint, json_data=data, cache_policy=cache_policy)
    
    async def delete(self, 
                     endpoint: str,
                     cache_policy: CachePolicy = CachePolicy.NETWORK_ONLY) -> Dict[str, Any]:
        """DELETE请求"""
        return await self._request('DELETE', endpoint, cache_policy=cache_policy)
    
    async def _request(self, 
                      method: str, 
                      endpoint: str, 
                      params: Dict[str, Any] = None,
                      json_data: Dict[str, Any] = None,
                      cache_policy: CachePolicy = CachePolicy.CACHE_FIRST) -> Dict[str, Any]:
        """通用请求方法"""
        
        url = f"{self.config.base_url}{endpoint}"
        cache_key = self._generate_cache_key(method, url, params, json_data)
        
        # 根据缓存策略处理请求
        if cache_policy in [CachePolicy.CACHE_FIRST, CachePolicy.CACHE_ONLY]:
            cached_result = await self._get_from_cache(cache_key)
            if cached_result:
                logger.info(f"使用缓存数据: {endpoint}")
                return cached_result
            
            if cache_policy == CachePolicy.CACHE_ONLY:
                raise Exception("缓存中没有数据且仅允许使用缓存")
        
        # 如果是离线状态且允许使用缓存，返回缓存数据
        if self.network_status == NetworkStatus.OFFLINE:
            if cache_policy != CachePolicy.NETWORK_ONLY:
                cached_result = await self._get_from_cache(cache_key, ignore_ttl=True)
                if cached_result:
                    logger.warning(f"离线模式，使用过期缓存: {endpoint}")
                    return cached_result
            
            # 将请求加入离线队列
            if method in ['POST', 'PUT', 'DELETE']:
                await self._add_to_offline_queue(method, url, json_data)
            
            raise Exception("网络不可用且缓存中没有数据")
        
        # 执行网络请求
        try:
            result = await self._execute_request(method, url, params, json_data)
            
            # 缓存GET请求结果
            if method == 'GET':
                await self._save_to_cache(cache_key, result)
            
            return result
            
        except Exception as e:
            logger.error(f"网络请求失败 {method} {endpoint}: {e}")
            
            # 如果网络请求失败，尝试使用缓存
            if cache_policy != CachePolicy.NETWORK_ONLY:
                cached_result = await self._get_from_cache(cache_key, ignore_ttl=True)
                if cached_result:
                    logger.warning(f"网络请求失败，使用缓存: {endpoint}")
                    return cached_result
            
            # 将修改操作加入离线队列
            if method in ['POST', 'PUT', 'DELETE']:
                await self._add_to_offline_queue(method, url, json_data)
            
            raise
    
    async def _execute_request(self, 
                             method: str, 
                             url: str, 
                             params: Dict[str, Any] = None,
                             json_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """执行网络请求"""
        session = await self._get_session()
        
        for attempt in range(self.config.retry_times):
            try:
                async with session.request(
                    method=method,
                    url=url,
                    params=params,
                    json=json_data
                ) as response:
                    
                    if response.status == 401:
                        # 认证失败，可能需要刷新token
                        await self._handle_auth_error()
                        raise Exception("认证失败")
                    
                    response.raise_for_status()
                    
                    # 处理压缩响应
                    if response.headers.get('Content-Encoding') == 'gzip':
                        content = await response.read()
                        content = gzip.decompress(content)
                        result = json.loads(content.decode('utf-8'))
                    else:
                        result = await response.json()
                    
                    return result
            
            except Exception as e:
                if attempt == self.config.retry_times - 1:
                    raise
                
                logger.warning(f"请求失败，重试 {attempt + 1}/{self.config.retry_times}: {e}")
                await asyncio.sleep(self.config.retry_delay * (2 ** attempt))  # 指数退避
    
    def _generate_cache_key(self, 
                           method: str, 
                           url: str, 
                           params: Dict[str, Any] = None, 
                           json_data: Dict[str, Any] = None) -> str:
        """生成缓存键"""
        key_data = {
            'method': method,
            'url': url,
            'params': params or {},
            'data': json_data or {}
        }
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(key_str.encode()).hexdigest()
    
    async def _get_from_cache(self, key: str, ignore_ttl: bool = False) -> Optional[Dict[str, Any]]:
        """从缓存获取数据"""
        try:
            with sqlite3.connect(self.cache_db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    'SELECT data, timestamp, ttl, compressed FROM cache WHERE key = ?', 
                    (key,)
                )
                result = cursor.fetchone()
                
                if result:
                    data_str, timestamp, ttl, compressed = result
                    cached_time = datetime.fromtimestamp(timestamp)
                    
                    # 检查缓存是否过期
                    if not ignore_ttl and datetime.now() - cached_time > timedelta(seconds=ttl):
                        return None
                    
                    # 解压数据
                    if compressed:
                        data_str = gzip.decompress(data_str.encode()).decode()
                    
                    return json.loads(data_str)
        
        except Exception as e:
            logger.error(f"读取缓存失败: {e}")
        
        return None
    
    async def _save_to_cache(self, key: str, data: Dict[str, Any]):
        """保存数据到缓存"""
        try:
            data_str = json.dumps(data, ensure_ascii=False)
            compressed = 0
            
            # 压缩大数据
            if self.config.compression_enabled and len(data_str) > 1024:
                data_str = gzip.compress(data_str.encode()).decode('latin1')
                compressed = 1
            
            with sqlite3.connect(self.cache_db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO cache 
                    (key, data, timestamp, ttl, compressed) 
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    key,
                    data_str,
                    time.time(),
                    self.config.cache_ttl,
                    compressed
                ))
                conn.commit()
                
        except Exception as e:
            logger.error(f"保存缓存失败: {e}")
    
    async def _add_to_offline_queue(self, method: str, url: str, data: Dict[str, Any] = None):
        """添加请求到离线队列"""
        try:
            request_id = str(uuid.uuid4())
            
            with sqlite3.connect(self.cache_db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO offline_queue 
                    (id, method, url, data, headers, timestamp) 
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    request_id,
                    method,
                    url,
                    json.dumps(data) if data else None,
                    json.dumps({'Authorization': f'Bearer {self.auth_token}'} if self.auth_token else {}),
                    time.time()
                ))
                conn.commit()
                
                self._offline_queue.append({
                    'id': request_id,
                    'method': method,
                    'url': url,
                    'data': data
                })
                
                logger.info(f"已添加到离线队列: {method} {url}")
                
        except Exception as e:
            logger.error(f"添加到离线队列失败: {e}")
    
    async def _sync_offline_queue(self):
        """同步离线队列"""
        if self.sync_status == SyncStatus.SYNCING:
            return
        
        self.sync_status = SyncStatus.SYNCING
        
        try:
            with sqlite3.connect(self.cache_db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, method, url, data, headers, retry_count 
                    FROM offline_queue 
                    ORDER BY timestamp
                ''')
                
                pending_requests = cursor.fetchall()
                
                successful_ids = []
                
                for request_data in pending_requests:
                    request_id, method, url, data_str, headers_str, retry_count = request_data
                    
                    try:
                        data = json.loads(data_str) if data_str else None
                        headers = json.loads(headers_str) if headers_str else {}
                        
                        # 执行请求
                        result = await self._execute_request(method, url, json_data=data)
                        
                        successful_ids.append(request_id)
                        logger.info(f"离线请求同步成功: {method} {url}")
                        
                        # 记录同步日志
                        await self._log_sync_operation(request_id, "sync_success", data, None)
                        
                    except Exception as e:
                        # 增加重试次数
                        new_retry_count = retry_count + 1
                        
                        if new_retry_count >= self.config.retry_times:
                            # 超过重试次数，记录错误并移除
                            successful_ids.append(request_id)
                            await self._log_sync_operation(request_id, "sync_failed", data, str(e))
                            logger.error(f"离线请求同步失败（超过重试次数）: {method} {url} - {e}")
                        else:
                            # 更新重试次数
                            cursor.execute('''
                                UPDATE offline_queue 
                                SET retry_count = ? 
                                WHERE id = ?
                            ''', (new_retry_count, request_id))
                            logger.warning(f"离线请求同步失败，将重试: {method} {url} - {e}")
                
                # 移除成功同步的请求
                if successful_ids:
                    placeholders = ','.join('?' * len(successful_ids))
                    cursor.execute(f'''
                        DELETE FROM offline_queue 
                        WHERE id IN ({placeholders})
                    ''', successful_ids)
                    
                    conn.commit()
                
                # 更新内存中的离线队列
                self._offline_queue = [
                    req for req in self._offline_queue 
                    if req['id'] not in successful_ids
                ]
                
                # 通知同步完成
                for callback in self._sync_callbacks:
                    try:
                        if asyncio.iscoroutinefunction(callback):
                            await callback(len(successful_ids), len(pending_requests))
                        else:
                            callback(len(successful_ids), len(pending_requests))
                    except Exception as e:
                        logger.error(f"同步回调执行失败: {e}")
                
                self.sync_status = SyncStatus.COMPLETED
                self.last_sync_time = datetime.now()
                
        except Exception as e:
            logger.error(f"同步离线队列失败: {e}")
            self.sync_status = SyncStatus.ERROR
        
        finally:
            self.sync_status = SyncStatus.IDLE
    
    async def _log_sync_operation(self, 
                                 operation_id: str, 
                                 status: str, 
                                 data: Dict[str, Any] = None, 
                                 error_message: str = None):
        """记录同步操作"""
        try:
            with sqlite3.connect(self.cache_db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO sync_log 
                    (id, operation, status, data, timestamp, error_message) 
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    str(uuid.uuid4()),
                    operation_id,
                    status,
                    json.dumps(data) if data else None,
                    time.time(),
                    error_message
                ))
                conn.commit()
                
        except Exception as e:
            logger.error(f"记录同步日志失败: {e}")
    
    async def _cleanup_expired_cache(self):
        """清理过期缓存"""
        try:
            cutoff_time = time.time() - (self.config.offline_retention_days * 24 * 3600)
            
            with sqlite3.connect(self.cache_db_path) as conn:
                cursor = conn.cursor()
                
                # 清理过期缓存
                cursor.execute('DELETE FROM cache WHERE timestamp < ?', (cutoff_time,))
                
                # 清理旧的同步日志
                cursor.execute('DELETE FROM sync_log WHERE timestamp < ?', (cutoff_time,))
                
                deleted_cache = cursor.rowcount
                conn.commit()
                
                if deleted_cache > 0:
                    logger.info(f"清理了 {deleted_cache} 条过期缓存")
                
        except Exception as e:
            logger.error(f"清理过期缓存失败: {e}")
    
    async def _full_sync(self):
        """执行全量同步"""
        try:
            logger.info("开始全量同步...")
            
            # 同步用户数据
            await self.sync_user_data()
            
            # 同步占卜历史
            await self.sync_divination_history()
            
            # 同步知识库更新
            await self.sync_knowledge_updates()
            
            logger.info("全量同步完成")
            
        except Exception as e:
            logger.error(f"全量同步失败: {e}")
    
    async def _handle_auth_error(self):
        """处理认证错误"""
        # 这里可以实现自动刷新token的逻辑
        logger.warning("认证失败，需要重新登录")
        
        # 通知应用层处理认证失败
        for callback in self._sync_callbacks:
            try:
                if hasattr(callback, '__name__') and callback.__name__ == 'auth_error_handler':
                    if asyncio.iscoroutinefunction(callback):
                        await callback()
                    else:
                        callback()
            except Exception as e:
                logger.error(f"认证错误回调失败: {e}")
    
    # ========== 具体业务API方法 ==========
    
    async def login(self, username: str, password: str) -> Dict[str, Any]:
        """用户登录"""
        data = {
            'username': username,
            'password': password
        }
        
        result = await self.post('/api/auth/login', data, CachePolicy.NETWORK_ONLY)
        
        if result.get('success') and result.get('data', {}).get('access_token'):
            self.set_auth_token(result['data']['access_token'])
            logger.info("登录成功")
        
        return result
    
    async def get_hexagram(self, gua_number: int) -> Dict[str, Any]:
        """获取卦象信息"""
        return await self.get(f'/api/hexagram/{gua_number}')
    
    async def search_hexagrams(self, 
                             query: str, 
                             category: str = None, 
                             limit: int = 20) -> Dict[str, Any]:
        """搜索卦象"""
        params = {
            'query': query,
            'limit': limit
        }
        if category:
            params['category'] = category
        
        return await self.get('/api/hexagram/search', params)
    
    async def create_divination(self, 
                              question: str, 
                              method: str = 'liuyao',
                              hexagram_number: int = None,
                              changing_lines: List[int] = None) -> Dict[str, Any]:
        """创建占卜"""
        data = {
            'question': question,
            'method': method
        }
        
        if hexagram_number:
            data['hexagram_number'] = hexagram_number
        
        if changing_lines:
            data['changing_lines'] = changing_lines
        
        return await self.post('/api/divination', data)
    
    async def search_knowledge(self, 
                             query: str, 
                             search_type: str = 'hybrid',
                             top_k: int = 10) -> Dict[str, Any]:
        """搜索知识"""
        data = {
            'query': query,
            'search_type': search_type,
            'top_k': top_k
        }
        
        return await self.post('/api/search/knowledge', data)
    
    async def ask_question(self, question: str) -> Dict[str, Any]:
        """智能问答"""
        data = {
            'question': question,
            'use_history': True
        }
        
        return await self.post('/api/qa', data)
    
    async def get_user_profile(self) -> Dict[str, Any]:
        """获取用户档案"""
        return await self.get('/api/user/profile')
    
    async def get_user_history(self, limit: int = 50, offset: int = 0) -> Dict[str, Any]:
        """获取用户历史"""
        params = {
            'limit': limit,
            'offset': offset
        }
        
        return await self.get('/api/user/history', params)
    
    # ========== 同步相关方法 ==========
    
    async def sync_user_data(self):
        """同步用户数据"""
        try:
            user_data = await self.get_user_profile()
            # 这里可以保存用户数据到本地数据库
            logger.info("用户数据同步完成")
        except Exception as e:
            logger.error(f"同步用户数据失败: {e}")
    
    async def sync_divination_history(self):
        """同步占卜历史"""
        try:
            history = await self.get_user_history()
            # 这里可以保存历史记录到本地数据库
            logger.info("占卜历史同步完成")
        except Exception as e:
            logger.error(f"同步占卜历史失败: {e}")
    
    async def sync_knowledge_updates(self):
        """同步知识库更新"""
        try:
            # 获取知识库版本信息
            version_info = await self.get('/api/version')
            # 根据版本信息决定是否需要更新
            logger.info("知识库同步完成")
        except Exception as e:
            logger.error(f"同步知识库失败: {e}")
    
    def get_offline_queue_size(self) -> int:
        """获取离线队列大小"""
        return len(self._offline_queue)
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        try:
            with sqlite3.connect(self.cache_db_path) as conn:
                cursor = conn.cursor()
                
                # 缓存条目数
                cursor.execute('SELECT COUNT(*) FROM cache')
                cache_count = cursor.fetchone()[0]
                
                # 离线队列大小
                cursor.execute('SELECT COUNT(*) FROM offline_queue')
                queue_size = cursor.fetchone()[0]
                
                # 同步日志数
                cursor.execute('SELECT COUNT(*) FROM sync_log')
                sync_log_count = cursor.fetchone()[0]
                
                return {
                    'cache_entries': cache_count,
                    'offline_queue_size': queue_size,
                    'sync_log_entries': sync_log_count,
                    'network_status': self.network_status.value,
                    'sync_status': self.sync_status.value,
                    'last_sync_time': self.last_sync_time.isoformat() if self.last_sync_time else None
                }
        
        except Exception as e:
            logger.error(f"获取缓存统计失败: {e}")
            return {}
    
    def clear_cache(self):
        """清除所有缓存"""
        try:
            with sqlite3.connect(self.cache_db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM cache')
                cursor.execute('DELETE FROM offline_queue')
                cursor.execute('DELETE FROM sync_log')
                conn.commit()
                
                self._offline_queue.clear()
                logger.info("缓存已清除")
        
        except Exception as e:
            logger.error(f"清除缓存失败: {e}")

# 工厂方法
def create_mobile_client(base_url: str = "https://api.yixue.local", 
                        auth_token: str = None) -> MobileAPIClient:
    """创建移动端API客户端"""
    config = APIConfig(base_url=base_url)
    return MobileAPIClient(config, auth_token=auth_token)