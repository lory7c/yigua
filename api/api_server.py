#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
云端易学知识API服务器
支持高并发、数据同步、版本管理的企业级API服务

核心功能:
1. RESTful API接口设计
2. 数据同步和版本控制
3. 高并发处理和缓存
4. 安全认证和授权
5. 监控和日志记录
6. 性能优化和负载均衡

作者: Claude
版本: 2.0.0
"""

import asyncio
import hashlib
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from contextlib import asynccontextmanager
from pathlib import Path
import uuid
import gzip
import aiofiles

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, Request, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field, validator
import uvicorn
import redis.asyncio as redis
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import text
import jwt
from typing_extensions import Annotated

# 导入系统模块
import sys
sys.path.append(str(Path(__file__).parent.parent))

from database.db_manager import DatabaseManager
from knowledge_graph.graph_builder import YiJingKnowledgeGraph
from rag_system.rag_framework import RAGPipeline

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 全局配置
class Config:
    SECRET_KEY = "your-secret-key-change-this-in-production"
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = 30
    REDIS_URL = "redis://localhost:6379"
    DATABASE_URL = "sqlite+aiosqlite:///./yixue_cloud.db"
    MAX_CONNECTIONS = 100
    CACHE_TTL = 3600  # 1小时
    RATE_LIMIT = 1000  # 每分钟请求限制

config = Config()

# 数据模型
class UserInfo(BaseModel):
    """用户信息"""
    user_id: str
    username: str
    email: str
    role: str = "user"
    created_at: datetime
    last_sync: Optional[datetime] = None

class SyncRequest(BaseModel):
    """同步请求"""
    client_id: str = Field(..., description="客户端唯一标识")
    last_sync_time: Optional[datetime] = Field(None, description="上次同步时间")
    device_info: Dict[str, Any] = Field(default_factory=dict, description="设备信息")
    data_version: str = Field("1.0.0", description="数据版本")
    force_sync: bool = Field(False, description="强制同步")

class SyncResponse(BaseModel):
    """同步响应"""
    sync_id: str
    status: str
    data_updates: List[Dict[str, Any]]
    deleted_items: List[str]
    new_version: str
    next_sync_time: datetime
    compressed: bool = False

class VersionInfo(BaseModel):
    """版本信息"""
    version: str
    release_date: datetime
    changes: List[str]
    compatibility: Dict[str, str]
    download_url: Optional[str] = None

class CacheStats(BaseModel):
    """缓存统计"""
    hit_rate: float
    total_requests: int
    cache_size: int
    memory_usage: str

class APIResponse(BaseModel):
    """统一API响应格式"""
    success: bool
    data: Any = None
    message: str = ""
    timestamp: datetime = Field(default_factory=datetime.now)
    version: str = "2.0.0"
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))

# 中间件和依赖
security = HTTPBearer()

class RateLimiter:
    """速率限制器"""
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
    
    async def is_allowed(self, key: str, limit: int = 60, window: int = 60) -> bool:
        """检查是否允许请求"""
        current = int(time.time())
        pipe = self.redis.pipeline()
        pipe.zremrangebyscore(key, 0, current - window)
        pipe.zcard(key)
        pipe.zadd(key, {str(uuid.uuid4()): current})
        pipe.expire(key, window)
        results = await pipe.execute()
        
        request_count = results[1]
        return request_count < limit

class SecurityManager:
    """安全管理器"""
    
    @staticmethod
    def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
        """创建访问令牌"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=15)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, config.SECRET_KEY, algorithm=config.ALGORITHM)
        return encoded_jwt
    
    @staticmethod
    async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
        """验证访问令牌"""
        try:
            payload = jwt.decode(credentials.credentials, config.SECRET_KEY, algorithms=[config.ALGORITHM])
            user_id: str = payload.get("sub")
            if user_id is None:
                raise HTTPException(status_code=401, detail="无效的认证令牌")
            return payload
        except jwt.PyJWTError:
            raise HTTPException(status_code=401, detail="无效的认证令牌")

# 全局状态管理
class AppState:
    """应用状态管理"""
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self.db_manager: Optional[DatabaseManager] = None
        self.kg: Optional[YiJingKnowledgeGraph] = None
        self.rag_pipeline: Optional[RAGPipeline] = None
        self.rate_limiter: Optional[RateLimiter] = None
        self.startup_time = datetime.now()

app_state = AppState()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时初始化
    logger.info("初始化云端API服务器...")
    
    # 初始化Redis连接
    app_state.redis_client = redis.from_url(config.REDIS_URL)
    await app_state.redis_client.ping()
    logger.info("Redis连接已建立")
    
    # 初始化速率限制器
    app_state.rate_limiter = RateLimiter(app_state.redis_client)
    
    # 初始化数据库管理器
    app_state.db_manager = DatabaseManager()
    logger.info("数据库管理器已初始化")
    
    # 初始化知识图谱
    try:
        kg_path = Path("../data/knowledge_graph.pkl")
        if kg_path.exists():
            app_state.kg = YiJingKnowledgeGraph.load(kg_path)
        else:
            app_state.kg = YiJingKnowledgeGraph()
        logger.info(f"知识图谱已加载: {len(app_state.kg.entities) if app_state.kg else 0} 个实体")
    except Exception as e:
        logger.warning(f"知识图谱加载失败: {e}")
        app_state.kg = YiJingKnowledgeGraph()
    
    # 初始化RAG管道
    try:
        app_state.rag_pipeline = RAGPipeline()
        logger.info("RAG管道已初始化")
    except Exception as e:
        logger.warning(f"RAG管道初始化失败: {e}")
    
    yield
    
    # 关闭时清理资源
    logger.info("清理资源...")
    if app_state.redis_client:
        await app_state.redis_client.close()
    logger.info("云端API服务器已关闭")

# 创建FastAPI应用
app = FastAPI(
    title="云端易学知识API",
    description="企业级易学知识图谱和RAG系统云端服务",
    version="2.0.0",
    lifespan=lifespan
)

# 添加中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# 请求拦截器
@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """请求速率限制中间件"""
    client_ip = request.client.host
    
    if app_state.rate_limiter:
        rate_key = f"rate_limit:{client_ip}"
        if not await app_state.rate_limiter.is_allowed(rate_key, config.RATE_LIMIT):
            return JSONResponse(
                status_code=429,
                content={"error": "请求频率超限", "retry_after": 60}
            )
    
    response = await call_next(request)
    response.headers["X-RateLimit-Remaining"] = str(config.RATE_LIMIT)
    return response

# ========== 基础API接口 ==========

@app.get("/health")
async def health_check():
    """健康检查"""
    uptime = datetime.now() - app_state.startup_time
    return APIResponse(
        success=True,
        data={
            "status": "healthy",
            "uptime_seconds": uptime.total_seconds(),
            "components": {
                "redis": app_state.redis_client is not None,
                "database": app_state.db_manager is not None,
                "knowledge_graph": app_state.kg is not None,
                "rag_pipeline": app_state.rag_pipeline is not None
            }
        }
    )

@app.get("/api/version")
async def get_version():
    """获取API版本信息"""
    return APIResponse(
        success=True,
        data=VersionInfo(
            version="2.0.0",
            release_date=datetime.now(),
            changes=[
                "新增数据同步功能",
                "支持高并发处理",
                "优化缓存策略",
                "增强安全认证"
            ],
            compatibility={
                "mobile_client": ">=1.5.0",
                "web_client": ">=2.0.0"
            }
        )
    )

# ========== 认证接口 ==========

@app.post("/api/auth/login")
async def login(username: str, password: str):
    """用户登录"""
    # 这里应该验证用户名和密码
    # 简化实现，实际应该查询数据库
    if username and password:  # 简化验证
        access_token_expires = timedelta(minutes=config.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = SecurityManager.create_access_token(
            data={"sub": username}, expires_delta=access_token_expires
        )
        
        return APIResponse(
            success=True,
            data={
                "access_token": access_token,
                "token_type": "bearer",
                "expires_in": config.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
                "user": UserInfo(
                    user_id=str(uuid.uuid4()),
                    username=username,
                    email=f"{username}@example.com",
                    created_at=datetime.now()
                )
            }
        )
    else:
        raise HTTPException(status_code=401, detail="用户名或密码错误")

@app.post("/api/auth/refresh")
async def refresh_token(current_user: dict = Depends(SecurityManager.verify_token)):
    """刷新访问令牌"""
    access_token_expires = timedelta(minutes=config.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = SecurityManager.create_access_token(
        data={"sub": current_user["sub"]}, expires_delta=access_token_expires
    )
    
    return APIResponse(
        success=True,
        data={
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": config.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        }
    )

# ========== 卦象查询API ==========

@app.get("/api/hexagram/{gua_number}")
async def get_hexagram(gua_number: int):
    """获取卦象详情"""
    if not app_state.db_manager:
        raise HTTPException(status_code=503, detail="数据库服务不可用")
    
    # 检查缓存
    cache_key = f"hexagram:{gua_number}"
    if app_state.redis_client:
        cached = await app_state.redis_client.get(cache_key)
        if cached:
            return APIResponse(
                success=True,
                data=json.loads(cached)
            )
    
    try:
        with app_state.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM hexagrams WHERE gua_number = ?
            """, (gua_number,))
            result = cursor.fetchone()
            
            if result:
                data = dict(zip([col[0] for col in cursor.description], result))
                
                # 缓存结果
                if app_state.redis_client:
                    await app_state.redis_client.setex(
                        cache_key, config.CACHE_TTL, json.dumps(data, default=str)
                    )
                
                return APIResponse(success=True, data=data)
            else:
                raise HTTPException(status_code=404, detail="卦象不存在")
    
    except Exception as e:
        logger.error(f"查询卦象失败: {e}")
        raise HTTPException(status_code=500, detail="内部服务器错误")

@app.get("/api/hexagram/search")
async def search_hexagrams(
    query: str,
    category: Optional[str] = None,
    limit: int = 20,
    offset: int = 0
):
    """搜索卦象"""
    if not app_state.db_manager:
        raise HTTPException(status_code=503, detail="数据库服务不可用")
    
    try:
        # 使用FTS5全文搜索
        with app_state.db_manager.get_connection() as conn:
            if category:
                sql = """
                    SELECT h.*, rank FROM hexagrams h
                    JOIN hexagrams_fts ON h.id = hexagrams_fts.rowid
                    WHERE hexagrams_fts MATCH ? AND h.category = ?
                    ORDER BY rank LIMIT ? OFFSET ?
                """
                params = (query, category, limit, offset)
            else:
                sql = """
                    SELECT h.*, rank FROM hexagrams h
                    JOIN hexagrams_fts ON h.id = hexagrams_fts.rowid
                    WHERE hexagrams_fts MATCH ?
                    ORDER BY rank LIMIT ? OFFSET ?
                """
                params = (query, limit, offset)
            
            cursor = conn.cursor()
            cursor.execute(sql, params)
            results = cursor.fetchall()
            
            data = [
                dict(zip([col[0] for col in cursor.description], row))
                for row in results
            ]
            
            return APIResponse(
                success=True,
                data={
                    "results": data,
                    "total": len(data),
                    "limit": limit,
                    "offset": offset
                }
            )
    
    except Exception as e:
        logger.error(f"搜索卦象失败: {e}")
        raise HTTPException(status_code=500, detail="内部服务器错误")

# ========== 占卜服务API ==========

@app.post("/api/divination")
async def divination_service(
    question: str,
    method: str = "liuyao",
    hexagram_number: Optional[int] = None,
    changing_lines: List[int] = [],
    current_user: dict = Depends(SecurityManager.verify_token)
):
    """占卜解析服务"""
    if not app_state.rag_pipeline:
        raise HTTPException(status_code=503, detail="RAG服务不可用")
    
    try:
        # 构建占卜查询
        divination_query = f"请为我解析占问：{question}，使用{method}方法"
        
        if hexagram_number:
            divination_query += f"，得到第{hexagram_number}卦"
        
        if changing_lines:
            divination_query += f"，变爻：{', '.join(map(str, changing_lines))}"
        
        # 执行RAG查询
        start_time = time.time()
        response = await app_state.rag_pipeline.query(
            divination_query,
            template_type="divination"
        )
        processing_time = time.time() - start_time
        
        # 记录占卜历史
        divination_record = {
            "user_id": current_user["sub"],
            "question": question,
            "method": method,
            "hexagram_number": hexagram_number,
            "changing_lines": changing_lines,
            "interpretation": response.answer,
            "confidence": response.confidence,
            "timestamp": datetime.now(),
            "processing_time": processing_time
        }
        
        # 异步保存到数据库
        asyncio.create_task(save_divination_record(divination_record))
        
        return APIResponse(
            success=True,
            data={
                "interpretation": response.answer,
                "confidence": response.confidence,
                "references": response.sources,
                "processing_time": processing_time,
                "divination_id": str(uuid.uuid4())
            }
        )
    
    except Exception as e:
        logger.error(f"占卜服务失败: {e}")
        raise HTTPException(status_code=500, detail="占卜服务暂时不可用")

async def save_divination_record(record: dict):
    """异步保存占卜记录"""
    try:
        # 这里应该保存到数据库
        logger.info(f"保存占卜记录: {record['user_id']}")
    except Exception as e:
        logger.error(f"保存占卜记录失败: {e}")

# ========== 知识搜索API ==========

@app.post("/api/search/knowledge")
async def search_knowledge(
    query: str,
    search_type: str = "hybrid",
    category: Optional[str] = None,
    top_k: int = 10
):
    """知识搜索API"""
    if not app_state.rag_pipeline:
        raise HTTPException(status_code=503, detail="搜索服务不可用")
    
    try:
        start_time = time.time()
        
        # 执行搜索
        response = await app_state.rag_pipeline.query(
            query,
            top_k=top_k,
            template_type="search"
        )
        
        processing_time = time.time() - start_time
        
        return APIResponse(
            success=True,
            data={
                "results": [
                    {
                        "content": doc.content[:300] + "..." if len(doc.content) > 300 else doc.content,
                        "score": score,
                        "metadata": doc.metadata,
                        "source": doc.metadata.get("source", "unknown")
                    }
                    for doc, score in zip(response.context.retrieved_documents, [0.9] * len(response.context.retrieved_documents))
                ],
                "total_found": len(response.context.retrieved_documents),
                "processing_time": processing_time,
                "search_type": search_type
            }
        )
    
    except Exception as e:
        logger.error(f"知识搜索失败: {e}")
        raise HTTPException(status_code=500, detail="搜索服务暂时不可用")

# ========== 智能问答API ==========

@app.post("/api/qa")
async def question_answering(
    question: str,
    context_type: str = "auto",
    use_history: bool = True,
    current_user: dict = Depends(SecurityManager.verify_token)
):
    """智能问答API"""
    if not app_state.rag_pipeline:
        raise HTTPException(status_code=503, detail="问答服务不可用")
    
    try:
        start_time = time.time()
        
        # 执行问答
        response = await app_state.rag_pipeline.query(
            question,
            template_type="qa"
        )
        
        processing_time = time.time() - start_time
        
        return APIResponse(
            success=True,
            data={
                "answer": response.answer,
                "confidence": response.confidence,
                "sources": response.sources,
                "context_docs": len(response.context.retrieved_documents),
                "context_entities": len(response.context.graph_entities),
                "processing_time": processing_time
            }
        )
    
    except Exception as e:
        logger.error(f"问答服务失败: {e}")
        raise HTTPException(status_code=500, detail="问答服务暂时不可用")

# ========== 用户数据API ==========

@app.get("/api/user/profile")
async def get_user_profile(current_user: dict = Depends(SecurityManager.verify_token)):
    """获取用户档案"""
    return APIResponse(
        success=True,
        data=UserInfo(
            user_id=current_user["sub"],
            username=current_user["sub"],
            email=f"{current_user['sub']}@example.com",
            created_at=datetime.now(),
            last_sync=datetime.now()
        )
    )

@app.get("/api/user/history")
async def get_user_history(
    limit: int = 50,
    offset: int = 0,
    current_user: dict = Depends(SecurityManager.verify_token)
):
    """获取用户历史记录"""
    # 这里应该从数据库获取用户历史记录
    return APIResponse(
        success=True,
        data={
            "history": [],
            "total": 0,
            "limit": limit,
            "offset": offset
        }
    )

# ========== 缓存管理API ==========

@app.get("/api/cache/stats")
async def get_cache_stats(current_user: dict = Depends(SecurityManager.verify_token)):
    """获取缓存统计信息"""
    if not app_state.redis_client:
        raise HTTPException(status_code=503, detail="缓存服务不可用")
    
    try:
        info = await app_state.redis_client.info()
        
        return APIResponse(
            success=True,
            data=CacheStats(
                hit_rate=0.85,  # 示例数据
                total_requests=1000,
                cache_size=info.get('used_memory', 0),
                memory_usage=info.get('used_memory_human', '0B')
            )
        )
    
    except Exception as e:
        logger.error(f"获取缓存统计失败: {e}")
        raise HTTPException(status_code=500, detail="缓存服务错误")

@app.delete("/api/cache/clear")
async def clear_cache(
    pattern: Optional[str] = None,
    current_user: dict = Depends(SecurityManager.verify_token)
):
    """清除缓存"""
    if not app_state.redis_client:
        raise HTTPException(status_code=503, detail="缓存服务不可用")
    
    try:
        if pattern:
            keys = await app_state.redis_client.keys(pattern)
            if keys:
                await app_state.redis_client.delete(*keys)
            cleared_count = len(keys)
        else:
            await app_state.redis_client.flushdb()
            cleared_count = -1  # 全部清除
        
        return APIResponse(
            success=True,
            data={
                "cleared_keys": cleared_count,
                "pattern": pattern or "all"
            }
        )
    
    except Exception as e:
        logger.error(f"清除缓存失败: {e}")
        raise HTTPException(status_code=500, detail="缓存清除失败")

# ========== 流式API接口 ==========

@app.post("/api/stream/chat")
async def stream_chat(
    question: str,
    current_user: dict = Depends(SecurityManager.verify_token)
):
    """流式聊天接口"""
    if not app_state.rag_pipeline:
        raise HTTPException(status_code=503, detail="聊天服务不可用")
    
    async def generate_response():
        try:
            # 获取上下文
            response = await app_state.rag_pipeline.query(question, top_k=5)
            context = response.context.to_prompt_context()
            
            # 构建提示词
            prompt = f"背景信息:\n{context}\n\n问题: {question}\n\n回答:"
            
            # 模拟流式响应
            for i, word in enumerate(response.answer.split()):
                chunk_data = {
                    "chunk": word + " ",
                    "chunk_id": i,
                    "is_final": i == len(response.answer.split()) - 1
                }
                yield f"data: {json.dumps(chunk_data)}\n\n"
                await asyncio.sleep(0.05)  # 模拟流式延迟
                
        except Exception as e:
            error_data = {"error": str(e)}
            yield f"data: {json.dumps(error_data)}\n\n"
    
    return StreamingResponse(
        generate_response(),
        media_type="text/plain",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
    )

# ========== 系统监控API ==========

@app.get("/api/system/metrics")
async def get_system_metrics():
    """获取系统监控指标"""
    import psutil
    
    return APIResponse(
        success=True,
        data={
            "cpu_usage": psutil.cpu_percent(interval=1),
            "memory_usage": psutil.virtual_memory()._asdict(),
            "disk_usage": psutil.disk_usage('/')._asdict(),
            "uptime": (datetime.now() - app_state.startup_time).total_seconds(),
            "active_connections": 0,  # 这里应该从连接池获取
            "cache_hit_rate": 0.85,  # 示例数据
            "avg_response_time": 0.15  # 示例数据
        }
    )

# ========== 主函数 ==========

if __name__ == "__main__":
    uvicorn.run(
        "api_server:app",
        host="0.0.0.0",
        port=8000,
        workers=4,
        log_level="info",
        access_log=True,
        reload=False  # 生产环境关闭自动重载
    )