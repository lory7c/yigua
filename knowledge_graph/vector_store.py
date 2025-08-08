"""
向量化存储模块
使用sentence-transformers和Qdrant进行语义检索
"""

import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
import json
from pathlib import Path
import logging
from datetime import datetime
import hashlib

from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct,
    Filter, FieldCondition, MatchValue,
    SearchRequest, SearchParams
)
from qdrant_client.http import models
import faiss
import pickle

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class Document:
    """文档对象"""
    id: str
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[np.ndarray] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'content': self.content,
            'metadata': self.metadata
        }


@dataclass
class SearchResult:
    """搜索结果"""
    document: Document
    score: float
    highlights: List[str] = field(default_factory=list)


class VectorStore:
    """向量存储基类"""
    
    def __init__(self, embedding_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"):
        """初始化向量存储
        
        Args:
            embedding_model: 嵌入模型名称，支持中文的模型
        """
        self.model = SentenceTransformer(embedding_model)
        self.embedding_dim = self.model.get_sentence_embedding_dimension()
        logger.info(f"加载嵌入模型: {embedding_model}, 维度: {self.embedding_dim}")
    
    def encode_texts(self, texts: List[str], batch_size: int = 32) -> np.ndarray:
        """批量编码文本"""
        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=True,
            convert_to_numpy=True
        )
        return embeddings
    
    def encode_text(self, text: str) -> np.ndarray:
        """编码单个文本"""
        return self.model.encode(text, convert_to_numpy=True)


class QdrantVectorStore(VectorStore):
    """Qdrant向量数据库存储"""
    
    def __init__(self, 
                 collection_name: str = "yijing_knowledge",
                 embedding_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
                 host: str = "localhost",
                 port: int = 6333,
                 memory: bool = True):
        """初始化Qdrant存储
        
        Args:
            collection_name: 集合名称
            embedding_model: 嵌入模型
            host: Qdrant服务器地址
            port: Qdrant服务器端口
            memory: 是否使用内存模式（用于测试）
        """
        super().__init__(embedding_model)
        
        self.collection_name = collection_name
        
        if memory:
            # 内存模式，用于测试
            self.client = QdrantClient(":memory:")
        else:
            # 连接到Qdrant服务器
            self.client = QdrantClient(host=host, port=port)
        
        self._init_collection()
    
    def _init_collection(self):
        """初始化集合"""
        collections = self.client.get_collections().collections
        collection_names = [c.name for c in collections]
        
        if self.collection_name not in collection_names:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=self.embedding_dim,
                    distance=Distance.COSINE
                )
            )
            logger.info(f"创建集合: {self.collection_name}")
        else:
            logger.info(f"使用已存在的集合: {self.collection_name}")
    
    def add_documents(self, documents: List[Document], batch_size: int = 100) -> None:
        """批量添加文档"""
        logger.info(f"开始添加 {len(documents)} 个文档")
        
        for i in range(0, len(documents), batch_size):
            batch = documents[i:i + batch_size]
            
            # 编码文本
            texts = [doc.content for doc in batch]
            embeddings = self.encode_texts(texts)
            
            # 创建点
            points = []
            for j, (doc, embedding) in enumerate(zip(batch, embeddings)):
                point = PointStruct(
                    id=hashlib.md5(doc.id.encode()).hexdigest()[:16],
                    vector=embedding.tolist(),
                    payload={
                        'doc_id': doc.id,
                        'content': doc.content,
                        **doc.metadata
                    }
                )
                points.append(point)
            
            # 上传到Qdrant
            self.client.upsert(
                collection_name=self.collection_name,
                points=points
            )
            
            logger.info(f"已添加批次 {i//batch_size + 1}: {len(batch)} 个文档")
    
    def search(self, 
               query: str,
               top_k: int = 5,
               filter_dict: Optional[Dict[str, Any]] = None) -> List[SearchResult]:
        """语义搜索
        
        Args:
            query: 查询文本
            top_k: 返回结果数量
            filter_dict: 过滤条件
        
        Returns:
            搜索结果列表
        """
        # 编码查询
        query_embedding = self.encode_text(query)
        
        # 构建过滤器
        filter_obj = None
        if filter_dict:
            conditions = []
            for key, value in filter_dict.items():
                conditions.append(
                    FieldCondition(
                        key=key,
                        match=MatchValue(value=value)
                    )
                )
            filter_obj = Filter(must=conditions)
        
        # 执行搜索
        search_result = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_embedding.tolist(),
            limit=top_k,
            query_filter=filter_obj
        )
        
        # 构建结果
        results = []
        for hit in search_result:
            doc = Document(
                id=hit.payload['doc_id'],
                content=hit.payload['content'],
                metadata={k: v for k, v in hit.payload.items() 
                         if k not in ['doc_id', 'content']}
            )
            results.append(SearchResult(
                document=doc,
                score=hit.score
            ))
        
        return results
    
    def delete_collection(self):
        """删除集合"""
        self.client.delete_collection(self.collection_name)
        logger.info(f"已删除集合: {self.collection_name}")


class FaissVectorStore(VectorStore):
    """FAISS向量存储（本地版本）"""
    
    def __init__(self,
                 index_path: Optional[Path] = None,
                 embedding_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"):
        """初始化FAISS存储
        
        Args:
            index_path: 索引保存路径
            embedding_model: 嵌入模型
        """
        super().__init__(embedding_model)
        
        self.index_path = index_path
        self.index = None
        self.documents: Dict[int, Document] = {}
        self.id_to_idx: Dict[str, int] = {}
        self.current_idx = 0
        
        self._init_index()
    
    def _init_index(self):
        """初始化FAISS索引"""
        if self.index_path and self.index_path.exists():
            self.load()
        else:
            # 创建新索引
            self.index = faiss.IndexFlatCosine(self.embedding_dim)
            logger.info(f"创建新的FAISS索引，维度: {self.embedding_dim}")
    
    def add_documents(self, documents: List[Document], batch_size: int = 100) -> None:
        """批量添加文档"""
        logger.info(f"开始添加 {len(documents)} 个文档到FAISS索引")
        
        all_embeddings = []
        
        for i in range(0, len(documents), batch_size):
            batch = documents[i:i + batch_size]
            
            # 编码文本
            texts = [doc.content for doc in batch]
            embeddings = self.encode_texts(texts)
            
            # 保存文档和映射
            for doc, embedding in zip(batch, embeddings):
                self.documents[self.current_idx] = doc
                self.id_to_idx[doc.id] = self.current_idx
                doc.embedding = embedding
                self.current_idx += 1
            
            all_embeddings.append(embeddings)
            logger.info(f"已处理批次 {i//batch_size + 1}: {len(batch)} 个文档")
        
        # 添加到索引
        if all_embeddings:
            all_embeddings = np.vstack(all_embeddings)
            self.index.add(all_embeddings)
            logger.info(f"已添加 {len(all_embeddings)} 个向量到索引")
    
    def search(self,
               query: str,
               top_k: int = 5,
               filter_dict: Optional[Dict[str, Any]] = None) -> List[SearchResult]:
        """语义搜索
        
        Args:
            query: 查询文本
            top_k: 返回结果数量
            filter_dict: 过滤条件（需要后处理）
        
        Returns:
            搜索结果列表
        """
        if self.index.ntotal == 0:
            logger.warning("索引为空")
            return []
        
        # 编码查询
        query_embedding = self.encode_text(query).reshape(1, -1)
        
        # 搜索
        scores, indices = self.index.search(query_embedding, min(top_k * 3, self.index.ntotal))
        
        # 构建结果
        results = []
        for idx, score in zip(indices[0], scores[0]):
            if idx == -1:  # FAISS返回-1表示没有结果
                break
            
            doc = self.documents.get(idx)
            if not doc:
                continue
            
            # 应用过滤器
            if filter_dict:
                match = all(
                    doc.metadata.get(key) == value
                    for key, value in filter_dict.items()
                )
                if not match:
                    continue
            
            results.append(SearchResult(
                document=doc,
                score=float(score)
            ))
            
            if len(results) >= top_k:
                break
        
        return results
    
    def save(self, path: Optional[Path] = None) -> None:
        """保存索引和文档"""
        save_path = path or self.index_path
        if not save_path:
            raise ValueError("未指定保存路径")
        
        # 保存FAISS索引
        faiss.write_index(self.index, str(save_path.with_suffix('.faiss')))
        
        # 保存文档和映射
        with open(save_path.with_suffix('.pkl'), 'wb') as f:
            pickle.dump({
                'documents': self.documents,
                'id_to_idx': self.id_to_idx,
                'current_idx': self.current_idx
            }, f)
        
        logger.info(f"索引已保存到: {save_path}")
    
    def load(self, path: Optional[Path] = None) -> None:
        """加载索引和文档"""
        load_path = path or self.index_path
        if not load_path:
            raise ValueError("未指定加载路径")
        
        # 加载FAISS索引
        self.index = faiss.read_index(str(load_path.with_suffix('.faiss')))
        
        # 加载文档和映射
        with open(load_path.with_suffix('.pkl'), 'rb') as f:
            data = pickle.load(f)
            self.documents = data['documents']
            self.id_to_idx = data['id_to_idx']
            self.current_idx = data['current_idx']
        
        logger.info(f"索引已加载: {self.index.ntotal} 个向量")


class HybridVectorStore(VectorStore):
    """混合向量存储（结合关键词和语义搜索）"""
    
    def __init__(self,
                 index_path: Optional[Path] = None,
                 embedding_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"):
        """初始化混合存储"""
        super().__init__(embedding_model)
        
        self.faiss_store = FaissVectorStore(index_path, embedding_model)
        self.inverted_index: Dict[str, Set[str]] = {}  # 倒排索引
    
    def _tokenize(self, text: str) -> List[str]:
        """简单的中文分词"""
        import jieba
        return list(jieba.cut(text))
    
    def _build_inverted_index(self, documents: List[Document]) -> None:
        """构建倒排索引"""
        for doc in documents:
            tokens = self._tokenize(doc.content)
            for token in tokens:
                if token not in self.inverted_index:
                    self.inverted_index[token] = set()
                self.inverted_index[token].add(doc.id)
    
    def add_documents(self, documents: List[Document], batch_size: int = 100) -> None:
        """添加文档"""
        # 添加到FAISS
        self.faiss_store.add_documents(documents, batch_size)
        
        # 构建倒排索引
        self._build_inverted_index(documents)
        logger.info("倒排索引构建完成")
    
    def search(self,
               query: str,
               top_k: int = 5,
               alpha: float = 0.7,
               filter_dict: Optional[Dict[str, Any]] = None) -> List[SearchResult]:
        """混合搜索
        
        Args:
            query: 查询文本
            top_k: 返回结果数量
            alpha: 语义搜索权重 (0-1)
            filter_dict: 过滤条件
        
        Returns:
            搜索结果列表
        """
        # 语义搜索
        semantic_results = self.faiss_store.search(query, top_k * 2, filter_dict)
        semantic_scores = {r.document.id: r.score * alpha for r in semantic_results}
        
        # 关键词搜索
        query_tokens = self._tokenize(query)
        keyword_scores = {}
        
        for token in query_tokens:
            if token in self.inverted_index:
                for doc_id in self.inverted_index[token]:
                    if doc_id not in keyword_scores:
                        keyword_scores[doc_id] = 0
                    keyword_scores[doc_id] += (1 - alpha) / len(query_tokens)
        
        # 合并分数
        all_scores = {}
        all_docs = {}
        
        for result in semantic_results:
            doc_id = result.document.id
            all_scores[doc_id] = semantic_scores.get(doc_id, 0) + keyword_scores.get(doc_id, 0)
            all_docs[doc_id] = result.document
        
        for doc_id, score in keyword_scores.items():
            if doc_id not in all_scores:
                # 从FAISS获取文档
                if doc_id in self.faiss_store.id_to_idx:
                    idx = self.faiss_store.id_to_idx[doc_id]
                    doc = self.faiss_store.documents.get(idx)
                    if doc:
                        all_scores[doc_id] = score
                        all_docs[doc_id] = doc
        
        # 排序并返回
        sorted_results = sorted(all_scores.items(), key=lambda x: x[1], reverse=True)
        
        results = []
        for doc_id, score in sorted_results[:top_k]:
            if doc_id in all_docs:
                results.append(SearchResult(
                    document=all_docs[doc_id],
                    score=score
                ))
        
        return results


def create_yijing_vector_store(documents: List[Dict[str, Any]], 
                               store_type: str = "faiss") -> VectorStore:
    """创建易学向量存储
    
    Args:
        documents: 文档列表
        store_type: 存储类型 ("qdrant", "faiss", "hybrid")
    
    Returns:
        向量存储实例
    """
    # 转换文档格式
    doc_objects = []
    for doc in documents:
        doc_obj = Document(
            id=doc.get('id', hashlib.md5(doc['content'].encode()).hexdigest()),
            content=doc['content'],
            metadata=doc.get('metadata', {})
        )
        doc_objects.append(doc_obj)
    
    # 创建存储
    if store_type == "qdrant":
        store = QdrantVectorStore(memory=True)
    elif store_type == "faiss":
        store = FaissVectorStore(Path("yijing_index"))
    elif store_type == "hybrid":
        store = HybridVectorStore(Path("yijing_hybrid_index"))
    else:
        raise ValueError(f"不支持的存储类型: {store_type}")
    
    # 添加文档
    store.add_documents(doc_objects)
    
    # 保存索引
    if hasattr(store, 'save'):
        store.save()
    
    logger.info(f"向量存储创建完成: {store_type}")
    return store


if __name__ == "__main__":
    # 测试向量存储
    test_documents = [
        {
            'id': 'hex_1',
            'content': '乾卦，象征天，刚健中正，自强不息。乾为天，为君，为父。',
            'metadata': {'type': 'hexagram', 'number': 1}
        },
        {
            'id': 'hex_2',
            'content': '坤卦，象征地，柔顺谦逊，厚德载物。坤为地，为母，为臣。',
            'metadata': {'type': 'hexagram', 'number': 2}
        },
        {
            'id': 'wuxing_1',
            'content': '金生水，水生木，木生火，火生土，土生金，此为五行相生之理。',
            'metadata': {'type': 'wuxing', 'category': 'generation'}
        },
        {
            'id': 'wuxing_2',
            'content': '金克木，木克土，土克水，水克火，火克金，此为五行相克之理。',
            'metadata': {'type': 'wuxing', 'category': 'restraint'}
        }
    ]
    
    # 创建FAISS存储
    store = create_yijing_vector_store(test_documents, "faiss")
    
    # 测试搜索
    results = store.search("天地之道", top_k=2)
    print("\n搜索结果：天地之道")
    for result in results:
        print(f"  分数: {result.score:.3f}")
        print(f"  内容: {result.document.content[:50]}...")
        print(f"  元数据: {result.document.metadata}")
        print()
    
    # 测试过滤搜索
    results = store.search("相生相克", top_k=2, filter_dict={'type': 'wuxing'})
    print("\n搜索结果：相生相克 (仅五行)")
    for result in results:
        print(f"  分数: {result.score:.3f}")
        print(f"  内容: {result.document.content[:50]}...")
        print()