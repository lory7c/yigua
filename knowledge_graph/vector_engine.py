#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
易学知识向量化系统
基于sentence-transformers实现文档向量化、相似度计算和语义检索
支持多种中文预训练模型和向量数据库存储
"""

import sqlite3
import numpy as np
import json
import pickle
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional, Union
import logging
from dataclasses import dataclass, asdict
import jieba
from collections import defaultdict
import time
import hashlib

try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False

try:
    from qdrant_client import QdrantClient
    from qdrant_client.http.models import Distance, VectorParams, PointStruct
    from qdrant_client.http.models import Filter, FieldCondition, MatchValue
    QDRANT_AVAILABLE = True
except ImportError:
    QDRANT_AVAILABLE = False

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    from sklearn.feature_extraction.text import TfidfVectorizer

# 确保总是导入cosine_similarity
from sklearn.metrics.pairwise import cosine_similarity

@dataclass
class Document:
    """文档类"""
    id: str
    content: str
    doc_type: str  # hexagram, line, interpretation, case
    metadata: Dict[str, Any]
    embedding: Optional[np.ndarray] = None
    keywords: List[str] = None

@dataclass
class SearchResult:
    """搜索结果类"""
    doc_id: str
    content: str
    score: float
    doc_type: str
    metadata: Dict[str, Any]
    matched_keywords: List[str] = None

class YixueVectorEngine:
    """易学知识向量化引擎"""
    
    def __init__(self, 
                 db_path: str, 
                 model_name: str = "shibing624/text2vec-base-chinese",
                 output_dir: str = "./knowledge_graph",
                 use_local_model: bool = True,
                 qdrant_host: str = "localhost",
                 qdrant_port: int = 6333,
                 qdrant_collection: str = "yixue_knowledge"):
        
        self.db_path = db_path
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # 文档和向量存储
        self.documents = {}
        self.embeddings = {}
        self.doc_index = {}  # 文档ID到索引的映射
        
        # 向量搜索配置
        self.embedding_dim = 512
        self.faiss_index = None
        self.tfidf_vectorizer = None
        self.tfidf_matrix = None
        
        # Qdrant配置
        self.qdrant_host = qdrant_host
        self.qdrant_port = qdrant_port
        self.qdrant_collection = qdrant_collection
        self.qdrant_client = None
        self.use_qdrant = False
        
        # 初始化向量模型
        self._init_vector_model(model_name, use_local_model)
        
        # 缓存配置
        self.cache_dir = self.output_dir / "cache"
        self.cache_dir.mkdir(exist_ok=True)
        
        # 易学关键词词典
        self.yixue_keywords = self._load_yixue_keywords()
        
        # 尝试连接Qdrant
        self._init_qdrant_client()

    def _init_vector_model(self, model_name: str, use_local_model: bool) -> None:
        """初始化向量模型"""
        if SENTENCE_TRANSFORMERS_AVAILABLE and use_local_model:
            try:
                # 尝试使用本地中文模型
                local_models = [
                    "shibing624/text2vec-base-chinese",
                    "GanymedeNil/text2vec-large-chinese", 
                    "sentence-transformers/distiluse-base-multilingual-cased"
                ]
                
                for model in local_models:
                    try:
                        logger.info(f"尝试加载模型: {model}")
                        self.model = SentenceTransformer(model)
                        self.embedding_dim = self.model.get_sentence_embedding_dimension()
                        logger.info(f"成功加载模型: {model}, 向量维度: {self.embedding_dim}")
                        self.use_transformer = True
                        return
                    except Exception as e:
                        logger.warning(f"模型 {model} 加载失败: {e}")
                        continue
                        
            except Exception as e:
                logger.warning(f"Sentence Transformers初始化失败: {e}")
        
        # 后备方案: 使用TF-IDF
        logger.info("使用TF-IDF向量化作为后备方案")
        self.use_transformer = False
        self.tfidf_vectorizer = TfidfVectorizer(
            max_features=1000,
            stop_words=None,  # 保留中文停用词
            ngram_range=(1, 2),
            min_df=2
        )
        self.embedding_dim = 1000

    def _load_yixue_keywords(self) -> Dict[str, List[str]]:
        """加载易学关键词词典"""
        return {
            '卦象': ['乾', '坤', '震', '艮', '坎', '离', '巽', '兑', '屯', '蒙', '需', '讼', '师', '比'],
            '爻位': ['初', '二', '三', '四', '五', '上', '九', '六'],
            '属性': ['阴', '阳', '刚', '柔', '中', '正', '应', '承'],
            '五行': ['金', '木', '水', '火', '土'],
            '方位': ['东', '南', '西', '北', '中央'],
            '人物': ['君子', '小人', '大人', '圣人', '王', '臣'],
            '动物': ['龙', '马', '牛', '羊', '鸟', '鱼', '虎', '豹'],
            '自然': ['天', '地', '山', '泽', '风', '雷', '水', '火'],
            '时间': ['春', '夏', '秋', '冬', '朝', '夕', '昼', '夜'],
            '状态': ['吉', '凶', '悔', '吝', '无咎', '有孚']
        }

    def connect_db(self) -> sqlite3.Connection:
        """连接数据库"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def extract_documents(self) -> None:
        """从数据库提取文档"""
        logger.info("开始提取文档...")
        
        with self.connect_db() as conn:
            # 1. 提取卦象文档
            cursor = conn.execute("""
                SELECT id, name, chinese_name, symbol, judgment, image, sequence_king_wen
                FROM hexagrams
                ORDER BY sequence_king_wen
            """)
            
            for row in cursor:
                doc_id = f"hexagram_{row['id']}"
                content = self._build_hexagram_content(row)
                
                doc = Document(
                    id=doc_id,
                    content=content,
                    doc_type='hexagram',
                    metadata={
                        'name': row['name'],
                        'chinese_name': row['chinese_name'],
                        'symbol': row['symbol'],
                        'sequence': row['sequence_king_wen'],
                        'db_id': row['id']
                    },
                    keywords=self.extract_keywords(content)
                )
                
                self.documents[doc_id] = doc
            
            # 2. 提取爻位文档
            cursor = conn.execute("""
                SELECT l.*, h.name as hexagram_name
                FROM lines l
                JOIN hexagrams h ON l.hexagram_id = h.id
                ORDER BY l.hexagram_id, l.position
            """)
            
            for row in cursor:
                doc_id = f"line_{row['id']}"
                content = self._build_line_content(row)
                
                doc = Document(
                    id=doc_id,
                    content=content,
                    doc_type='line',
                    metadata={
                        'hexagram_name': row['hexagram_name'],
                        'position': row['position'],
                        'line_type': '阳爻' if row['type'] == 1 else '阴爻',
                        'db_id': row['id']
                    },
                    keywords=self.extract_keywords(content)
                )
                
                self.documents[doc_id] = doc
            
            # 3. 提取注解文档
            cursor = conn.execute("""
                SELECT i.*, 
                       CASE WHEN i.target_type = 1 THEN h.name
                            WHEN i.target_type = 2 THEN h2.name || '第' || l.position || '爻'
                            ELSE '未知'
                       END as target_name
                FROM interpretations i
                LEFT JOIN hexagrams h ON i.target_type = 1 AND i.target_id = h.id
                LEFT JOIN lines l ON i.target_type = 2 AND i.target_id = l.id
                LEFT JOIN hexagrams h2 ON l.hexagram_id = h2.id
                WHERE i.content IS NOT NULL
                ORDER BY i.quality_score DESC
            """)
            
            for row in cursor:
                doc_id = f"interpretation_{row['id']}"
                content = self._build_interpretation_content(row)
                
                doc = Document(
                    id=doc_id,
                    content=content,
                    doc_type='interpretation',
                    metadata={
                        'author': row['author'],
                        'source_book': row['source_book'],
                        'target_name': row['target_name'],
                        'category': row['category'],
                        'quality_score': row['quality_score'],
                        'db_id': row['id']
                    },
                    keywords=self.extract_keywords(content)
                )
                
                self.documents[doc_id] = doc
            
            # 4. 提取占卜案例文档（如果存在该表）
            try:
                cursor = conn.execute("""
                    SELECT dc.*, h.name as main_hexagram_name
                    FROM divination_cases dc
                    JOIN hexagrams h ON dc.hexagram_id = h.id
                    WHERE dc.interpretation IS NOT NULL
                    ORDER BY dc.accuracy_rating DESC, dc.created_at DESC
                """)
            except sqlite3.OperationalError:
                # 表不存在，跳过
                pass
            else:
                for row in cursor:
                    doc_id = f"case_{row['id']}"
                    content = self._build_case_content(row)
                    
                    doc = Document(
                        id=doc_id,
                        content=content,
                        doc_type='case',
                        metadata={
                            'question_type': row.get('question_type', '未知'),
                            'main_hexagram': row['main_hexagram_name'],
                            'accuracy_rating': row.get('accuracy_rating', 0),
                            'db_id': row['id']
                        },
                        keywords=self.extract_keywords(content)
                    )
                    
                    self.documents[doc_id] = doc
        
        logger.info(f"成功提取 {len(self.documents)} 个文档")

    def _build_hexagram_content(self, row: sqlite3.Row) -> str:
        """构建卦象文档内容"""
        parts = [
            f"卦名: {row['name']}",
            f"中文名: {row['chinese_name']}" if row['chinese_name'] else "",
            f"符号: {row['symbol']}" if row['symbol'] else "",
            f"卦辞: {row['judgment']}" if row['judgment'] else "",
            f"象传: {row['image']}" if row['image'] else "",
            f"序号: {row['sequence_king_wen']}"
        ]
        return "\n".join([p for p in parts if p])

    def _build_line_content(self, row: sqlite3.Row) -> str:
        """构建爻位文档内容"""
        parts = [
            f"卦象: {row['hexagram_name']}",
            f"爻位: 第{row['position']}爻",
            f"爻性: {'阳爻' if row['type'] == 1 else '阴爻'}",
            f"爻辞: {row['text']}" if row['text'] else "",
            f"小象: {row['image']}" if row['image'] else ""
        ]
        return "\n".join([p for p in parts if p])

    def _build_interpretation_content(self, row: sqlite3.Row) -> str:
        """构建注解文档内容"""
        parts = [
            f"注解对象: {row['target_name']}" if row['target_name'] else "",
            f"标题: {row['title']}" if row['title'] else "",
            f"作者: {row['author']}" if row['author'] else "",
            f"出处: {row['source_book']}" if row['source_book'] else "",
            f"注解内容: {row['content']}" if row['content'] else ""
        ]
        return "\n".join([p for p in parts if p])

    def _build_case_content(self, row: sqlite3.Row) -> str:
        """构建案例文档内容"""
        parts = [
            f"案例标题: {row['case_title']}" if row['case_title'] else "",
            f"问题类型: {row['question_type']}" if row['question_type'] else "",
            f"具体问题: {row['question_detail']}" if row['question_detail'] else "",
            f"本卦: {row['main_hexagram_name']}" if row['main_hexagram_name'] else "",
            f"解卦过程: {row['interpretation']}" if row['interpretation'] else "",
            f"实际结果: {row['actual_result']}" if row['actual_result'] else "",
            f"准确度: {row['accuracy_rating']}/5" if row['accuracy_rating'] else ""
        ]
        return "\n".join([p for p in parts if p])

    def extract_keywords(self, text: str) -> List[str]:
        """提取关键词"""
        keywords = []
        
        # jieba分词
        words = jieba.lcut(text)
        
        # 匹配易学关键词
        for category, keyword_list in self.yixue_keywords.items():
            for keyword in keyword_list:
                if keyword in text:
                    keywords.append(keyword)
        
        # 提取高频词汇
        word_freq = defaultdict(int)
        for word in words:
            if len(word) > 1:  # 过滤单字符
                word_freq[word] += 1
        
        # 添加高频词
        high_freq_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:10]
        keywords.extend([word for word, freq in high_freq_words if freq > 1])
        
        return list(set(keywords))
    
    def _init_qdrant_client(self) -> None:
        """初始化Qdrant客户端"""
        if not QDRANT_AVAILABLE:
            logger.info("未安装Qdrant客户端，使用FAISS或sklearn作为备用")
            return
        
        try:
            # 尝试连接Qdrant
            self.qdrant_client = QdrantClient(host=self.qdrant_host, port=self.qdrant_port)
            
            # 检查连接
            collections = self.qdrant_client.get_collections()
            self.use_qdrant = True
            logger.info(f"成功连接到Qdrant: {self.qdrant_host}:{self.qdrant_port}")
            
        except Exception as e:
            logger.warning(f"Qdrant连接失败: {e}，使用备用方案")
            self.use_qdrant = False
            self.qdrant_client = None
    
    def _create_qdrant_collection(self) -> None:
        """创建Qdrant集合"""
        if not self.use_qdrant or not self.qdrant_client:
            return
        
        try:
            # 检查集合是否存在
            collections = self.qdrant_client.get_collections()
            collection_names = [col.name for col in collections.collections]
            
            if self.qdrant_collection not in collection_names:
                # 创建新集合
                self.qdrant_client.create_collection(
                    collection_name=self.qdrant_collection,
                    vectors_config=VectorParams(size=self.embedding_dim, distance=Distance.COSINE)
                )
                logger.info(f"创建了Qdrant集合: {self.qdrant_collection}")
            else:
                logger.info(f"Qdrant集合已存在: {self.qdrant_collection}")
                
        except Exception as e:
            logger.error(f"创建Qdrant集合失败: {e}")
            self.use_qdrant = False

    def vectorize_documents(self, batch_size: int = 32) -> None:
        """对文档进行向量化"""
        logger.info("开始文档向量化...")
        
        if not self.documents:
            logger.error("没有找到文档，请先调用extract_documents()")
            return
        
        doc_ids = list(self.documents.keys())
        contents = [self.documents[doc_id].content for doc_id in doc_ids]
        
        if self.use_transformer:
            # 使用Sentence Transformers
            embeddings = self._vectorize_with_transformer(contents, batch_size)
        else:
            # 使用TF-IDF
            embeddings = self._vectorize_with_tfidf(contents)
        
        # 存储向量
        for i, doc_id in enumerate(doc_ids):
            self.embeddings[doc_id] = embeddings[i]
            self.documents[doc_id].embedding = embeddings[i]
            self.doc_index[doc_id] = i
        
        logger.info(f"完成 {len(embeddings)} 个文档的向量化")

    def _vectorize_with_transformer(self, contents: List[str], batch_size: int) -> np.ndarray:
        """使用Transformer模型向量化"""
        logger.info("使用Sentence Transformers进行向量化...")
        
        embeddings = []
        for i in range(0, len(contents), batch_size):
            batch = contents[i:i+batch_size]
            batch_embeddings = self.model.encode(
                batch, 
                convert_to_numpy=True,
                show_progress_bar=True
            )
            embeddings.extend(batch_embeddings)
        
        return np.array(embeddings)

    def _vectorize_with_tfidf(self, contents: List[str]) -> np.ndarray:
        """使用TF-IDF向量化"""
        logger.info("使用TF-IDF进行向量化...")
        
        # 预处理文本
        processed_contents = []
        for content in contents:
            words = jieba.lcut(content)
            processed_contents.append(" ".join(words))
        
        # 训练TF-IDF
        self.tfidf_matrix = self.tfidf_vectorizer.fit_transform(processed_contents)
        
        return self.tfidf_matrix.toarray()

    def build_faiss_index(self) -> None:
        """构建FAISS索引"""
        if not self.embeddings:
            logger.error("没有向量数据，请先调用vectorize_documents()")
            return
        
        logger.info("构建向量索引...")
        
        embedding_matrix = np.array(list(self.embeddings.values())).astype('float32')
        actual_dim = embedding_matrix.shape[1]
        
        if FAISS_AVAILABLE:
            # 创建FAISS索引（使用实际向量维度）
            if self.use_transformer:
                # 对于transformer embeddings，使用内积索引
                self.faiss_index = faiss.IndexFlatIP(actual_dim)
                # 归一化向量以获得余弦相似度
                faiss.normalize_L2(embedding_matrix)
            else:
                # 对于TF-IDF，使用L2距离
                self.faiss_index = faiss.IndexFlatL2(actual_dim)
            
            self.faiss_index.add(embedding_matrix)
            logger.info(f"FAISS索引构建完成，包含 {self.faiss_index.ntotal} 个向量，维度: {actual_dim}")
        else:
            # 备用：使用numpy存储向量矩阵
            self.embedding_matrix = embedding_matrix
            logger.info(f"向量矩阵构建完成，包含 {len(embedding_matrix)} 个向量，维度: {actual_dim}")
            
        # 更新实际向量维度
        self.embedding_dim = actual_dim

    def semantic_search(self, 
                       query: str, 
                       top_k: int = 10, 
                       doc_type_filter: List[str] = None,
                       score_threshold: float = 0.3) -> List[SearchResult]:
        """语义搜索（优先Qdrant，后备FAISS）"""
        if self.use_qdrant and self.qdrant_client:
            return self._qdrant_search(query, top_k, doc_type_filter, score_threshold)
        elif hasattr(self, 'faiss_index') or hasattr(self, 'embedding_matrix'):
            return self._faiss_search(query, top_k, doc_type_filter, score_threshold)
        else:
            logger.error("向量索引未构建，请先调用build_vector_index()")
            return []
    
    def _qdrant_search(self, query: str, top_k: int, doc_type_filter: List[str], score_threshold: float) -> List[SearchResult]:
        """使用Qdrant进行语义搜索"""
        try:
            # 向量化查询
            if self.use_transformer:
                query_embedding = self.model.encode([query], convert_to_numpy=True)[0].tolist()
            else:
                query_words = jieba.lcut(query)
                query_text = " ".join(query_words)
                query_embedding = self.tfidf_vectorizer.transform([query_text]).toarray()[0].tolist()
            
            # 构建过滤器
            search_filter = None
            if doc_type_filter:
                search_filter = Filter(
                    must=[
                        FieldCondition(
                            key="doc_type",
                            match=MatchValue(value=doc_type) if len(doc_type_filter) == 1 
                            else MatchValue(any=doc_type_filter)
                        )
                    ]
                )
            
            # 搜索
            search_result = self.qdrant_client.search(
                collection_name=self.qdrant_collection,
                query_vector=query_embedding,
                query_filter=search_filter,
                limit=top_k,
                score_threshold=score_threshold
            )
            
            # 转换结果
            results = []
            for point in search_result:
                matched_keywords = self._find_matched_keywords(query, point.payload["content"])
                
                result = SearchResult(
                    doc_id=point.payload["doc_id"],
                    content=point.payload["content"],
                    score=float(point.score),
                    doc_type=point.payload["doc_type"],
                    metadata=point.payload["metadata"],
                    matched_keywords=matched_keywords
                )
                results.append(result)
            
            return results
            
        except Exception as e:
            logger.error(f"Qdrant搜索失败: {e}，使用后备方案")
            return self._faiss_search(query, top_k, doc_type_filter, score_threshold)
    
    def _faiss_search(self, query: str, top_k: int, doc_type_filter: List[str], score_threshold: float) -> List[SearchResult]:
        """使用FAISS进行语义搜索"""
        # 向量化查询
        if self.use_transformer:
            query_embedding = self.model.encode([query], convert_to_numpy=True)
            if FAISS_AVAILABLE and hasattr(self, 'faiss_index'):
                faiss.normalize_L2(query_embedding.astype('float32'))
        else:
            query_words = jieba.lcut(query)
            query_text = " ".join(query_words)
            query_embedding = self.tfidf_vectorizer.transform([query_text]).toarray()
        
        # 搜索
        if FAISS_AVAILABLE and hasattr(self, 'faiss_index'):
            # FAISS搜索
            scores, indices = self.faiss_index.search(
                query_embedding.astype('float32'), 
                min(top_k * 2, self.faiss_index.ntotal)  # 搜索更多结果用于过滤
            )
            scores, indices = scores[0], indices[0]
        else:
            # 备用：sklearn余弦相似度搜索
            if not hasattr(self, 'embedding_matrix'):
                logger.error("向量矩阵未构建")
                return []
            
            similarities = cosine_similarity(query_embedding, self.embedding_matrix).flatten()
            indices = np.argsort(similarities)[::-1][:top_k * 2]
            scores = similarities[indices]
        
        results = []
        doc_ids = list(self.documents.keys())
        
        # 确保scores和indices是数组格式
        if hasattr(scores, 'shape') and len(scores.shape) == 2:
            scores_list = scores[0]
            indices_list = indices[0]
        else:
            scores_list = scores
            indices_list = indices
        
        for i, (score, idx) in enumerate(zip(scores_list, indices_list)):
            if idx == -1:  # FAISS返回-1表示无效索引
                continue
                
            if idx >= len(doc_ids):  # 防止索引越界
                continue
                
            doc_id = doc_ids[idx]
            doc = self.documents[doc_id]
            
            # 应用过滤器
            if doc_type_filter and doc.doc_type not in doc_type_filter:
                continue
            
            # 评分转换（TF-IDF使用L2距离，需要转换为相似度）
            if self.use_transformer:
                similarity_score = float(score)
            else:
                similarity_score = 1.0 / (1.0 + float(score))  # 距离转相似度
            
            if similarity_score < score_threshold:
                continue
            
            # 提取匹配的关键词
            matched_keywords = self._find_matched_keywords(query, doc.content)
            
            result = SearchResult(
                doc_id=doc_id,
                content=doc.content,
                score=similarity_score,
                doc_type=doc.doc_type,
                metadata=doc.metadata,
                matched_keywords=matched_keywords
            )
            
            results.append(result)
        
        # 按相似度排序并返回top_k
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:top_k]

    def _find_matched_keywords(self, query: str, content: str) -> List[str]:
        """寻找匹配的关键词"""
        matched = []
        query_words = set(jieba.lcut(query))
        content_words = set(jieba.lcut(content))
        
        # 直接词汇匹配
        matched.extend(query_words.intersection(content_words))
        
        # 易学关键词匹配
        for category, keywords in self.yixue_keywords.items():
            for keyword in keywords:
                if keyword in query and keyword in content:
                    matched.append(keyword)
        
        return list(set(matched))

    def keyword_search(self, 
                      keywords: List[str], 
                      top_k: int = 10,
                      doc_type_filter: List[str] = None) -> List[SearchResult]:
        """关键词搜索"""
        results = []
        
        for doc_id, doc in self.documents.items():
            if doc_type_filter and doc.doc_type not in doc_type_filter:
                continue
            
            # 计算关键词匹配分数
            matched_keywords = []
            score = 0.0
            
            for keyword in keywords:
                if keyword in doc.content:
                    matched_keywords.append(keyword)
                    # 根据关键词重要性计算分数
                    if keyword in doc.keywords:
                        score += 2.0  # 如果是文档的关键词，加权更高
                    else:
                        score += 1.0
            
            if matched_keywords:
                # 归一化分数
                normalized_score = min(1.0, score / len(keywords))
                
                result = SearchResult(
                    doc_id=doc_id,
                    content=doc.content,
                    score=normalized_score,
                    doc_type=doc.doc_type,
                    metadata=doc.metadata,
                    matched_keywords=matched_keywords
                )
                
                results.append(result)
        
        # 按分数排序
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:top_k]

    def hybrid_search(self, 
                     query: str, 
                     top_k: int = 10,
                     semantic_weight: float = 0.7,
                     keyword_weight: float = 0.3,
                     doc_type_filter: List[str] = None) -> List[SearchResult]:
        """混合搜索（语义 + 关键词）"""
        # 提取查询关键词
        query_keywords = self.extract_keywords(query)
        
        # 语义搜索
        semantic_results = self.semantic_search(
            query, top_k=top_k*2, doc_type_filter=doc_type_filter
        )
        
        # 关键词搜索
        keyword_results = self.keyword_search(
            query_keywords, top_k=top_k*2, doc_type_filter=doc_type_filter
        )
        
        # 合并结果
        combined_scores = defaultdict(float)
        all_results = {}
        
        # 语义搜索结果
        for result in semantic_results:
            combined_scores[result.doc_id] += result.score * semantic_weight
            all_results[result.doc_id] = result
        
        # 关键词搜索结果
        for result in keyword_results:
            if result.doc_id in combined_scores:
                combined_scores[result.doc_id] += result.score * keyword_weight
            else:
                combined_scores[result.doc_id] = result.score * keyword_weight
                all_results[result.doc_id] = result
        
        # 按综合得分排序
        sorted_doc_ids = sorted(combined_scores.items(), 
                               key=lambda x: x[1], reverse=True)
        
        final_results = []
        for doc_id, score in sorted_doc_ids[:top_k]:
            result = all_results[doc_id]
            result.score = score  # 更新为综合得分
            final_results.append(result)
        
        return final_results

    def get_similar_documents(self, 
                             doc_id: str, 
                             top_k: int = 5,
                             doc_type_filter: List[str] = None) -> List[SearchResult]:
        """找到相似文档"""
        if doc_id not in self.documents:
            logger.error(f"文档 {doc_id} 不存在")
            return []
        
        doc = self.documents[doc_id]
        return self.semantic_search(
            doc.content, top_k=top_k+1, doc_type_filter=doc_type_filter
        )[1:]  # 排除自己

    def save_vectors(self, filename: str = "vectors.pkl") -> str:
        """保存向量数据"""
        vector_path = self.output_dir / filename
        
        vector_data = {
            'documents': {doc_id: asdict(doc) for doc_id, doc in self.documents.items()},
            'embeddings': {doc_id: emb.tolist() for doc_id, emb in self.embeddings.items()},
            'doc_index': self.doc_index,
            'embedding_dim': self.embedding_dim,
            'use_transformer': self.use_transformer
        }
        
        # 保存numpy数组需要特殊处理
        for doc_id, doc_data in vector_data['documents'].items():
            if doc_data['embedding'] is not None:
                doc_data['embedding'] = doc_data['embedding'].tolist()
        
        with open(vector_path, 'wb') as f:
            pickle.dump(vector_data, f)
        
        # 保存FAISS索引
        if FAISS_AVAILABLE and hasattr(self, 'faiss_index') and self.faiss_index:
            faiss_path = self.output_dir / "faiss.index"
            faiss.write_index(self.faiss_index, str(faiss_path))
        
        logger.info(f"向量数据保存到: {vector_path}")
        return str(vector_path)

    def load_vectors(self, filename: str = "vectors.pkl") -> None:
        """加载向量数据"""
        vector_path = self.output_dir / filename
        
        if not vector_path.exists():
            logger.error(f"向量文件不存在: {vector_path}")
            return
        
        with open(vector_path, 'rb') as f:
            vector_data = pickle.load(f)
        
        # 重建文档对象
        self.documents = {}
        for doc_id, doc_data in vector_data['documents'].items():
            doc_data['embedding'] = np.array(doc_data['embedding']) if doc_data['embedding'] else None
            self.documents[doc_id] = Document(**doc_data)
        
        # 重建向量
        self.embeddings = {
            doc_id: np.array(emb) for doc_id, emb in vector_data['embeddings'].items()
        }
        
        self.doc_index = vector_data['doc_index']
        self.embedding_dim = vector_data['embedding_dim']
        self.use_transformer = vector_data['use_transformer']
        
        # 加载FAISS索引
        if FAISS_AVAILABLE:
            faiss_path = self.output_dir / "faiss.index"
            if faiss_path.exists():
                self.faiss_index = faiss.read_index(str(faiss_path))
        
        logger.info(f"成功加载 {len(self.documents)} 个文档的向量数据")

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        if not self.documents:
            return {'error': '没有文档数据'}
        
        stats = {
            'total_documents': len(self.documents),
            'document_types': {},
            'embedding_dimension': self.embedding_dim,
            'use_transformer_model': self.use_transformer,
            'has_faiss_index': self.faiss_index is not None,
            'keywords_stats': {}
        }
        
        # 统计文档类型
        for doc in self.documents.values():
            doc_type = doc.doc_type
            stats['document_types'][doc_type] = stats['document_types'].get(doc_type, 0) + 1
        
        # 统计关键词
        all_keywords = []
        for doc in self.documents.values():
            if doc.keywords:
                all_keywords.extend(doc.keywords)
        
        keyword_freq = defaultdict(int)
        for keyword in all_keywords:
            keyword_freq[keyword] += 1
        
        stats['keywords_stats'] = {
            'total_unique_keywords': len(keyword_freq),
            'top_keywords': sorted(keyword_freq.items(), key=lambda x: x[1], reverse=True)[:20]
        }
        
        return stats

    def build_complete_vector_system(self) -> Dict[str, str]:
        """构建完整向量系统"""
        logger.info("开始构建易学知识向量系统...")
        
        # 1. 提取文档
        self.extract_documents()
        
        # 2. 向量化
        self.vectorize_documents()
        
        # 3. 构建索引
        self.build_vector_index()
        
        # 4. 保存系统
        vector_path = self.save_vectors()
        
        # 5. 保存统计信息
        stats = self.get_statistics()
        stats_path = self.output_dir / 'vector_statistics.json'
        with open(stats_path, 'w', encoding='utf-8') as f:
            json.dump(stats, f, ensure_ascii=False, indent=2, default=str)
        
        logger.info("向量系统构建完成!")
        return {
            'vectors': vector_path,
            'statistics': str(stats_path)
        }
    
    def build_vector_index(self) -> None:
        """构建向量索引（兼容性方法）"""
        if not self.embeddings:
            logger.error("没有向量数据，请先调用vectorize_documents()")
            return
        
        logger.info("构建向量索引...")
        
        embedding_matrix = np.array(list(self.embeddings.values())).astype('float32')
        actual_dim = embedding_matrix.shape[1]
        
        if FAISS_AVAILABLE:
            # 创建FAISS索引
            if self.use_transformer:
                self.faiss_index = faiss.IndexFlatIP(actual_dim)
                faiss.normalize_L2(embedding_matrix)
            else:
                self.faiss_index = faiss.IndexFlatL2(actual_dim)
            
            self.faiss_index.add(embedding_matrix)
            logger.info(f"FAISS索引构建完成，包含 {self.faiss_index.ntotal} 个向量，维度: {actual_dim}")
        else:
            # 备用：使用numpy存储向量矩阵
            self.embedding_matrix = embedding_matrix
            logger.info(f"向量矩阵构建完成，包含 {len(embedding_matrix)} 个向量，维度: {actual_dim}")
        
        # 更新实际向量维度
        self.embedding_dim = actual_dim

if __name__ == "__main__":
    # 示例用法
    db_path = "../database/yixue_knowledge_base.db"
    engine = YixueVectorEngine(db_path)
    
    # 构建向量系统
    saved_files = engine.build_complete_vector_system()
    
    print("向量系统构建完成!")
    print("保存的文件:")
    for file_type, path in saved_files.items():
        print(f"  {file_type}: {path}")
    
    # 示例搜索
    results = engine.hybrid_search("乾卦的含义是什么", top_k=5)
    print(f"\n搜索结果数量: {len(results)}")
    for i, result in enumerate(results, 1):
        print(f"{i}. 文档类型: {result.doc_type}, 分数: {result.score:.3f}")
        print(f"   内容: {result.content[:100]}...")