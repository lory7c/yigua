"""
FastAPI主应用
提供易学知识图谱和RAG系统的REST API接口
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks, UploadFile, File, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime
import uvicorn
import asyncio
from pathlib import Path
import json
import hashlib
import logging

# 导入系统模块
import sys
sys.path.append(str(Path(__file__).parent.parent))

from knowledge_graph.graph_builder import YixueKnowledgeGraphBuilder, Entity, Relation
from knowledge_graph.vector_store import FaissVectorStore, HybridVectorStore, Document
from rag_system.rag_framework import RAGPipeline, RAGResponse, Context
from local_models.local_llm import LocalLLM, ModelManager, InferenceConfig

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 创建FastAPI应用
app = FastAPI(
    title="易学知识图谱与RAG系统API",
    description="提供易学知识查询、占卜解析、智能问答等服务",
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

# 全局变量存储系统组件
kg: Optional[YixueKnowledgeGraphBuilder] = None
vs: Optional[FaissVectorStore] = None
rag_pipeline: Optional[RAGPipeline] = None
model_manager: ModelManager = ModelManager()


# ========== 请求/响应模型 ==========

class QueryRequest(BaseModel):
    """查询请求"""
    question: str = Field(..., description="用户问题")
    top_k: int = Field(5, description="返回结果数量")
    strategy: str = Field("hybrid", description="检索策略")
    template_type: str = Field("qa", description="模板类型")
    use_llm: bool = Field(False, description="是否使用LLM")


class QueryResponse(BaseModel):
    """查询响应"""
    answer: str
    confidence: float
    sources: List[str]
    context_docs: int
    context_entities: int
    processing_time: float


class EntityRequest(BaseModel):
    """实体请求"""
    name: str
    entity_type: str
    properties: Dict[str, Any] = {}


class RelationRequest(BaseModel):
    """关系请求"""
    source_name: str
    target_name: str
    relation_type: str
    properties: Dict[str, Any] = {}
    bidirectional: bool = False


class DocumentRequest(BaseModel):
    """文档请求"""
    content: str
    metadata: Dict[str, Any] = {}


class DivinationRequest(BaseModel):
    """占卜请求"""
    question: str = Field(..., description="占问事项")
    method: str = Field("liuyao", description="占卜方法")
    hexagram_number: Optional[int] = Field(None, description="卦序号")
    changing_lines: List[int] = Field([], description="变爻")


class SearchRequest(BaseModel):
    """搜索请求"""
    query: str
    search_type: str = Field("semantic", description="搜索类型: semantic/keyword/hybrid")
    filters: Dict[str, Any] = {}
    top_k: int = 10


class ModelLoadRequest(BaseModel):
    """模型加载请求"""
    model_name: str
    model_path: str
    load_in_8bit: bool = False
    load_in_4bit: bool = False
    use_flash_attention: bool = False


class GenerateRequest(BaseModel):
    """生成请求"""
    prompt: str
    max_new_tokens: int = 512
    temperature: float = 0.7
    top_p: float = 0.9
    stream: bool = False


# ========== 系统初始化 ==========

@app.on_event("startup")
async def startup_event():
    """启动时初始化系统"""
    global kg, vs, rag_pipeline
    
    try:
        # 初始化知识图谱
        kg_path = Path("data/knowledge_graph.pkl")
        if kg_path.exists():
            kg = YixueKnowledgeGraphBuilder.load(kg_path)
        else:
            kg = YixueKnowledgeGraphBuilder()
        logger.info(f"知识图谱已加载: {len(kg.entities)} 个实体")
        
        # 初始化向量存储
        vs_path = Path("data/vector_index")
        vs = HybridVectorStore(vs_path)
        logger.info("向量存储已初始化")
        
        # 初始化RAG管道
        rag_config = Path("config/rag_config.json")
        rag_pipeline = RAGPipeline(rag_config if rag_config.exists() else None)
        logger.info("RAG管道已初始化")
        
    except Exception as e:
        logger.error(f"系统初始化失败: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    """关闭时清理资源"""
    global kg, vs, rag_pipeline
    
    # 保存知识图谱
    if kg:
        kg.save()
    
    # 保存向量索引
    if vs and hasattr(vs, 'save'):
        vs.save()
    
    # 清理模型
    model_manager.get_current_model()
    
    logger.info("系统资源已清理")


# ========== 健康检查 ==========

@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "components": {
            "knowledge_graph": kg is not None,
            "vector_store": vs is not None,
            "rag_pipeline": rag_pipeline is not None,
            "models_loaded": len(model_manager.list_models())
        }
    }


# ========== RAG问答接口 ==========

@app.post("/api/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    """智能问答接口"""
    if not rag_pipeline:
        raise HTTPException(status_code=503, detail="RAG系统未初始化")
    
    start_time = datetime.now()
    
    try:
        # 执行查询
        response = await rag_pipeline.query(
            request.question,
            top_k=request.top_k,
            template_type=request.template_type
        )
        
        # 计算处理时间
        processing_time = (datetime.now() - start_time).total_seconds()
        
        return QueryResponse(
            answer=response.answer,
            confidence=response.confidence,
            sources=response.sources,
            context_docs=len(response.context.retrieved_documents),
            context_entities=len(response.context.graph_entities),
            processing_time=processing_time
        )
        
    except Exception as e:
        logger.error(f"查询失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/query/stream")
async def query_stream(request: QueryRequest):
    """流式问答接口"""
    if not rag_pipeline:
        raise HTTPException(status_code=503, detail="RAG系统未初始化")
    
    async def generate():
        try:
            # 获取当前模型
            model = model_manager.get_current_model()
            if not model:
                yield json.dumps({"error": "没有加载的模型"})
                return
            
            # 获取上下文
            response = await rag_pipeline.query(request.question, top_k=request.top_k)
            context = response.context.to_prompt_context()
            
            # 构建提示词
            prompt = f"背景信息:\n{context}\n\n问题: {request.question}\n\n回答:"
            
            # 流式生成
            for chunk in model.stream_generate(prompt):
                yield json.dumps({"chunk": chunk})
                
        except Exception as e:
            yield json.dumps({"error": str(e)})
    
    return StreamingResponse(generate(), media_type="application/json")


# ========== 知识图谱接口 ==========

@app.post("/api/kg/entity")
async def add_entity(request: EntityRequest):
    """添加实体"""
    if not kg:
        raise HTTPException(status_code=503, detail="知识图谱未初始化")
    
    entity = Entity(
        id=hashlib.md5(f"{request.name}_{request.entity_type}".encode()).hexdigest()[:16],
        name=request.name,
        entity_type=request.entity_type,
        properties=request.properties
    )
    
    success = kg.add_entity(entity)
    
    if success:
        return {"status": "success", "entity_id": entity.id}
    else:
        raise HTTPException(status_code=400, detail="实体已存在")


@app.post("/api/kg/relation")
async def add_relation(request: RelationRequest):
    """添加关系"""
    if not kg:
        raise HTTPException(status_code=503, detail="知识图谱未初始化")
    
    # 查找实体
    source = kg.query_by_name(request.source_name)
    target = kg.query_by_name(request.target_name)
    
    if not source or not target:
        raise HTTPException(status_code=404, detail="实体不存在")
    
    relation = Relation(
        source_id=source.id,
        target_id=target.id,
        relation_type=request.relation_type,
        properties=request.properties,
        bidirectional=request.bidirectional
    )
    
    success = kg.add_relation(relation)
    
    if success:
        return {"status": "success"}
    else:
        raise HTTPException(status_code=400, detail="关系添加失败")


@app.get("/api/kg/entity/{name}")
async def get_entity(name: str):
    """获取实体信息"""
    if not kg:
        raise HTTPException(status_code=503, detail="知识图谱未初始化")
    
    entity = kg.query_by_name(name)
    
    if entity:
        neighbors = kg.get_neighbors(entity.id)
        return {
            "entity": entity.to_dict(),
            "neighbors": [
                {
                    "entity": n[0].to_dict(),
                    "relation": n[1].to_dict()
                }
                for n in neighbors
            ]
        }
    else:
        raise HTTPException(status_code=404, detail="实体不存在")


@app.get("/api/kg/path")
async def find_path(source: str, target: str, max_length: int = 5):
    """查找实体间路径"""
    if not kg:
        raise HTTPException(status_code=503, detail="知识图谱未初始化")
    
    source_entity = kg.query_by_name(source)
    target_entity = kg.query_by_name(target)
    
    if not source_entity or not target_entity:
        raise HTTPException(status_code=404, detail="实体不存在")
    
    path = kg.find_path(source_entity.id, target_entity.id, max_length)
    
    if path:
        return {
            "path": [kg.entities[node_id].name for node_id in path]
        }
    else:
        return {"path": None, "message": "未找到路径"}


@app.get("/api/kg/stats")
async def get_kg_stats():
    """获取知识图谱统计信息"""
    if not kg:
        raise HTTPException(status_code=503, detail="知识图谱未初始化")
    
    return {
        "total_entities": len(kg.entities),
        "total_relations": len(kg.relations),
        "entity_types": {
            entity_type: len(entities)
            for entity_type, entities in kg.type_index.items()
        },
        "graph_density": kg.graph.number_of_edges() / (kg.graph.number_of_nodes() * (kg.graph.number_of_nodes() - 1))
        if kg.graph.number_of_nodes() > 1 else 0
    }


# ========== 向量存储接口 ==========

@app.post("/api/vector/add")
async def add_documents(documents: List[DocumentRequest]):
    """添加文档到向量存储"""
    if not vs:
        raise HTTPException(status_code=503, detail="向量存储未初始化")
    
    doc_objects = []
    for doc in documents:
        doc_obj = Document(
            id=hashlib.md5(doc.content.encode()).hexdigest(),
            content=doc.content,
            metadata=doc.metadata
        )
        doc_objects.append(doc_obj)
    
    vs.add_documents(doc_objects)
    
    return {
        "status": "success",
        "documents_added": len(doc_objects)
    }


@app.post("/api/vector/search")
async def vector_search(request: SearchRequest):
    """向量搜索"""
    if not vs:
        raise HTTPException(status_code=503, detail="向量存储未初始化")
    
    results = vs.search(
        request.query,
        top_k=request.top_k,
        filter_dict=request.filters if request.filters else None
    )
    
    return {
        "results": [
            {
                "content": r.document.content[:200],
                "score": r.score,
                "metadata": r.document.metadata
            }
            for r in results
        ]
    }


# ========== 占卜接口 ==========

@app.post("/api/divination")
async def divination(request: DivinationRequest):
    """占卜解析"""
    if not rag_pipeline:
        raise HTTPException(status_code=503, detail="系统未初始化")
    
    # 构建占卜查询
    query = f"请为我解析占问：{request.question}"
    
    if request.hexagram_number:
        hexagram = kg.query_entity(f"hexagram_{request.hexagram_number}")
        if hexagram:
            query += f"\n得到{hexagram.name}卦"
    
    if request.changing_lines:
        query += f"\n变爻：{', '.join(map(str, request.changing_lines))}"
    
    # 执行查询
    response = await rag_pipeline.query(
        query,
        template_type="divination"
    )
    
    return {
        "interpretation": response.answer,
        "confidence": response.confidence,
        "references": response.sources
    }


# ========== 模型管理接口 ==========

@app.post("/api/model/load")
async def load_model(request: ModelLoadRequest):
    """加载模型"""
    try:
        model = model_manager.load_model(
            request.model_name,
            request.model_path,
            load_in_8bit=request.load_in_8bit,
            load_in_4bit=request.load_in_4bit,
            use_flash_attention=request.use_flash_attention
        )
        
        return {
            "status": "success",
            "model_name": request.model_name,
            "parameters": f"{model._count_parameters():.1f}M"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/model/{model_name}")
async def unload_model(model_name: str):
    """卸载模型"""
    model_manager.unload_model(model_name)
    return {"status": "success", "message": f"模型 {model_name} 已卸载"}


@app.get("/api/model/list")
async def list_models():
    """列出已加载的模型"""
    models = []
    for name in model_manager.list_models():
        info = model_manager.get_model_info(name)
        models.append(info)
    
    return {
        "models": models,
        "current": model_manager.current_model
    }


@app.post("/api/model/switch/{model_name}")
async def switch_model(model_name: str):
    """切换当前模型"""
    model = model_manager.switch_model(model_name)
    if model:
        return {"status": "success", "current_model": model_name}
    else:
        raise HTTPException(status_code=404, detail="模型未找到")


@app.post("/api/model/generate")
async def generate_text(request: GenerateRequest):
    """文本生成"""
    model = model_manager.get_current_model()
    if not model:
        raise HTTPException(status_code=503, detail="没有加载的模型")
    
    if request.stream:
        async def stream_generate():
            for chunk in model.stream_generate(request.prompt):
                yield json.dumps({"chunk": chunk}) + "\n"
        
        return StreamingResponse(stream_generate(), media_type="application/json")
    else:
        config = InferenceConfig(
            max_new_tokens=request.max_new_tokens,
            temperature=request.temperature,
            top_p=request.top_p
        )
        
        response = model.generate(request.prompt, config)
        return {"response": response}


# ========== 文件上传接口 ==========

@app.post("/api/upload/pdf")
async def upload_pdf(file: UploadFile = File(...)):
    """上传PDF文件进行处理"""
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="只支持PDF文件")
    
    # 保存文件
    upload_dir = Path("uploads")
    upload_dir.mkdir(exist_ok=True)
    
    file_path = upload_dir / file.filename
    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)
    
    # TODO: 调用PDF提取模块处理文件
    
    return {
        "status": "success",
        "filename": file.filename,
        "size": len(content),
        "path": str(file_path)
    }


# ========== 导出接口 ==========

@app.get("/api/export/knowledge_graph")
async def export_knowledge_graph():
    """导出知识图谱"""
    if not kg:
        raise HTTPException(status_code=503, detail="知识图谱未初始化")
    
    export_path = Path("exports/knowledge_graph.json")
    export_path.parent.mkdir(exist_ok=True)
    
    kg.export_to_json(export_path)
    
    return {
        "status": "success",
        "path": str(export_path),
        "entities": len(kg.entities),
        "relations": len(kg.relations)
    }


# ========== WebSocket接口（实时对话） ==========

from fastapi import WebSocket, WebSocketDisconnect

@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    """WebSocket实时对话"""
    await websocket.accept()
    
    try:
        while True:
            # 接收消息
            data = await websocket.receive_json()
            question = data.get("question", "")
            
            if not question:
                await websocket.send_json({"error": "问题不能为空"})
                continue
            
            # 处理查询
            if rag_pipeline:
                response = await rag_pipeline.query(question)
                
                # 发送响应
                await websocket.send_json({
                    "answer": response.answer,
                    "confidence": response.confidence,
                    "sources": response.sources
                })
            else:
                await websocket.send_json({"error": "系统未初始化"})
                
    except WebSocketDisconnect:
        logger.info("WebSocket连接断开")
    except Exception as e:
        logger.error(f"WebSocket错误: {e}")
        await websocket.close()


# ========== 主函数 ==========

if __name__ == "__main__":
    # 运行服务器
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )