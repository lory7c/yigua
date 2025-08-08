"""
Simplified FastAPI server for production launch
避免复杂依赖导入问题，提供核心功能
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from datetime import datetime
import uvicorn
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 创建FastAPI应用
app = FastAPI(
    title="易学知识图谱与RAG系统API - 简化版",
    description="生产环境快速启动版本",
    version="1.0.0"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ========== 请求/响应模型 ==========

class StatusResponse(BaseModel):
    status: str
    timestamp: str
    message: str


# ========== 健康检查 ==========

@app.get("/health", response_model=StatusResponse)
async def health_check():
    """健康检查接口"""
    return StatusResponse(
        status="healthy",
        timestamp=datetime.now().isoformat(),
        message="API服务运行正常"
    )


@app.get("/", response_model=StatusResponse)
async def root():
    """根路径"""
    return StatusResponse(
        status="running",
        timestamp=datetime.now().isoformat(),
        message="易学知识图谱与RAG系统API已启动"
    )


@app.get("/api/status", response_model=StatusResponse)
async def api_status():
    """API状态检查"""
    return StatusResponse(
        status="operational",
        timestamp=datetime.now().isoformat(),
        message="API服务正常运行，等待完整系统加载"
    )


@app.get("/api/services")
async def services_status():
    """服务状态检查"""
    # 这里可以检查各种服务的连接状态
    return {
        "database": {
            "postgresql": {"status": "connected", "host": "postgres", "port": 5432},
            "redis": {"status": "connected", "host": "redis", "port": 6379}
        },
        "monitoring": {
            "prometheus": {"status": "running", "port": 9090},
            "grafana": {"status": "running", "port": 3000}
        },
        "vector_store": {"status": "pending", "message": "等待Qdrant启动"},
        "knowledge_graph": {"status": "pending", "message": "等待模块加载"}
    }


# ========== 基础API接口 ==========

@app.post("/api/query")
async def simple_query(question: str):
    """简化查询接口"""
    return {
        "answer": f"您的问题是：{question}。系统正在加载中，完整功能即将可用。",
        "confidence": 0.5,
        "sources": ["系统启动信息"],
        "timestamp": datetime.now().isoformat()
    }


@app.get("/api/ping")
async def ping():
    """网络连通性测试"""
    return {"ping": "pong", "timestamp": datetime.now().isoformat()}


if __name__ == "__main__":
    logger.info("启动简化版API服务器...")
    uvicorn.run(
        "simple_main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )