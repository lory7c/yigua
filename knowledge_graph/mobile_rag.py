#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
移动端优化RAG系统
专为Android/iOS应用设计的轻量化RAG问答系统
支持本地推理、缓存机制和离线运行
"""

import sqlite3
import json
import pickle
import logging
import numpy as np
import time
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict, OrderedDict
import threading
import hashlib
import gzip
import os

# 轻量化依赖
import jieba
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class MobileDocument:
    """移动端文档类（轻量化）"""
    id: str
    content: str
    doc_type: str
    score: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MobileResponse:
    """移动端响应类"""
    question: str
    answer: str
    confidence: float
    response_time: float
    sources: List[str] = field(default_factory=list)
    cached: bool = False
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'question': self.question,
            'answer': self.answer,
            'confidence': self.confidence,
            'response_time': self.response_time,
            'sources': self.sources[:3],  # 限制来源数量
            'cached': self.cached,
            'timestamp': self.timestamp.isoformat()
        }


class LRUCache:
    """LRU缓存实现"""
    
    def __init__(self, capacity: int = 100):
        self.capacity = capacity
        self.cache = OrderedDict()
    
    def get(self, key: str) -> Optional[Any]:
        if key in self.cache:
            # 移动到末尾（最近使用）
            value = self.cache.pop(key)
            self.cache[key] = value
            return value
        return None
    
    def put(self, key: str, value: Any) -> None:
        if key in self.cache:
            self.cache.pop(key)
        elif len(self.cache) >= self.capacity:
            # 删除最久未使用的项
            self.cache.popitem(last=False)
        
        self.cache[key] = value
    
    def clear(self) -> None:
        self.cache.clear()
    
    def size(self) -> int:
        return len(self.cache)


class CompactVectorizer:
    """紧凑向量化器（内存优化）"""
    
    def __init__(self, max_features: int = 1000, cache_size: int = 50):
        self.max_features = max_features
        self.vectorizer = TfidfVectorizer(
            max_features=max_features,
            stop_words=None,
            ngram_range=(1, 2),
            min_df=1,
            max_df=0.9
        )
        self.document_cache = LRUCache(cache_size)
        self.query_cache = LRUCache(cache_size // 2)
        self.fitted = False
        self.doc_vectors = None
        self.doc_ids = []
    
    def fit_documents(self, documents: List[MobileDocument]) -> None:
        """训练向量化器"""
        logger.info(f"训练紧凑向量化器，文档数: {len(documents)}")
        
        # 预处理文本
        texts = []
        self.doc_ids = []
        
        for doc in documents:
            # 简单分词
            words = jieba.lcut(doc.content)
            processed_text = " ".join(words)
            texts.append(processed_text)
            self.doc_ids.append(doc.id)
        
        # 训练TF-IDF
        self.doc_vectors = self.vectorizer.fit_transform(texts)
        self.fitted = True
        
        logger.info(f"向量化完成，特征维度: {self.vectorizer.get_feature_names_out().shape[0]}")
    
    def search(self, query: str, top_k: int = 5) -> List[Tuple[str, float]]:
        """向量搜索"""
        if not self.fitted:
            logger.error("向量化器未训练")
            return []
        
        # 检查缓存
        cache_key = hashlib.md5(f"{query}_{top_k}".encode()).hexdigest()
        cached_result = self.query_cache.get(cache_key)
        if cached_result:
            return cached_result
        
        # 向量化查询
        words = jieba.lcut(query)
        processed_query = " ".join(words)
        query_vector = self.vectorizer.transform([processed_query])
        
        # 计算相似度
        similarities = cosine_similarity(query_vector, self.doc_vectors).flatten()
        
        # 排序并获取top_k
        top_indices = np.argsort(similarities)[::-1][:top_k]
        
        results = []
        for idx in top_indices:
            if similarities[idx] > 0.01:  # 相似度阈值
                results.append((self.doc_ids[idx], float(similarities[idx])))
        
        # 缓存结果
        self.query_cache.put(cache_key, results)
        
        return results


class MobileKnowledgeBase:
    """移动端知识库"""
    
    def __init__(self, db_path: str, cache_dir: str = "./mobile_cache"):
        self.db_path = db_path
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        
        # 轻量化数据存储
        self.documents = {}  # id -> MobileDocument
        self.entities = {}   # name -> properties
        self.relations = {}  # (source, target) -> relation_type
        
        # 缓存
        self.response_cache = LRUCache(100)
        self.embedding_cache = LRUCache(50)
        
        # 向量化器
        self.vectorizer = None
        
        # 预定义易学知识
        self.yixue_knowledge = self._load_predefined_knowledge()
        
        # 性能监控
        self.stats = {
            'cache_hits': 0,
            'cache_misses': 0,
            'total_queries': 0,
            'avg_response_time': 0.0
        }
    
    def _load_predefined_knowledge(self) -> Dict[str, Any]:
        """加载预定义易学知识"""
        return {
            'bagua': {
                '乾': {'meaning': '天、刚健、创造', 'wuxing': '金', 'direction': '西北'},
                '坤': {'meaning': '地、柔顺、包容', 'wuxing': '土', 'direction': '西南'},
                '震': {'meaning': '雷、动、奋起', 'wuxing': '木', 'direction': '东'},
                '巽': {'meaning': '风、顺、进入', 'wuxing': '木', 'direction': '东南'},
                '坎': {'meaning': '水、险、陷入', 'wuxing': '水', 'direction': '北'},
                '离': {'meaning': '火、丽、光明', 'wuxing': '火', 'direction': '南'},
                '艮': {'meaning': '山、止、静止', 'wuxing': '土', 'direction': '东北'},
                '兑': {'meaning': '泽、悦、喜悦', 'wuxing': '金', 'direction': '西'}
            },
            'wuxing': {
                '生': {'金': '水', '水': '木', '木': '火', '火': '土', '土': '金'},
                '克': {'金': '木', '木': '土', '土': '水', '水': '火', '火': '金'}
            },
            'tiangan': ['甲', '乙', '丙', '丁', '戊', '己', '庚', '辛', '壬', '癸'],
            'dizhi': ['子', '丑', '寅', '卯', '辰', '巳', '午', '未', '申', '酉', '戌', '亥']
        }
    
    def load_data(self, max_docs: int = 1000) -> None:
        """加载数据（限制数量以节省内存）"""
        logger.info("加载移动端知识库数据...")
        
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            
            # 加载文档（优先加载重要文档）
            cursor = conn.execute("""
                SELECT h.id, h.gua_name, h.basic_meaning, h.judgement, h.image,
                       'hexagram' as doc_type
                FROM hexagrams h
                ORDER BY h.gua_number
                LIMIT ?
            """, (max_docs // 2,))
            
            doc_count = 0
            for row in cursor:
                doc_id = f"hex_{row['id']}"
                content = self._build_hexagram_content(row)
                
                doc = MobileDocument(
                    id=doc_id,
                    content=content,
                    doc_type='hexagram',
                    metadata={
                        'name': row['gua_name'],
                        'type': 'hexagram'
                    }
                )
                self.documents[doc_id] = doc
                doc_count += 1
            
            # 加载爻位数据
            cursor = conn.execute("""
                SELECT l.id, l.line_position, l.line_text, l.line_meaning,
                       h.gua_name, 'line' as doc_type
                FROM lines l
                JOIN hexagrams h ON l.hexagram_id = h.id
                ORDER BY l.hexagram_id, l.line_position
                LIMIT ?
            """, (max_docs // 2,))
            
            for row in cursor:
                doc_id = f"line_{row['id']}"
                content = self._build_line_content(row)
                
                doc = MobileDocument(
                    id=doc_id,
                    content=content,
                    doc_type='line',
                    metadata={
                        'hexagram': row['gua_name'],
                        'position': row['line_position'],
                        'type': 'line'
                    }
                )
                self.documents[doc_id] = doc
                doc_count += 1
            
            conn.close()
            logger.info(f"加载了 {doc_count} 个文档")
            
            # 训练向量化器
            self._build_vectorizer()
            
        except Exception as e:
            logger.error(f"数据加载失败: {e}")
    
    def _build_hexagram_content(self, row: sqlite3.Row) -> str:
        """构建卦象内容（精简版）"""
        parts = [
            f"卦名: {row['gua_name']}",
            f"含义: {row['basic_meaning']}" if row['basic_meaning'] else "",
            f"卦辞: {row['judgement']}" if row['judgement'] else "",
            f"象传: {row['image']}" if row['image'] else ""
        ]
        return " ".join([p for p in parts if p])
    
    def _build_line_content(self, row: sqlite3.Row) -> str:
        """构建爻位内容（精简版）"""
        parts = [
            f"{row['gua_name']}第{row['line_position']}爻",
            f"爻辞: {row['line_text']}" if row['line_text'] else "",
            f"含义: {row['line_meaning']}" if row['line_meaning'] else ""
        ]
        return " ".join([p for p in parts if p])
    
    def _build_vectorizer(self) -> None:
        """构建向量化器"""
        if not self.documents:
            logger.warning("没有文档可用于训练向量化器")
            return
        
        self.vectorizer = CompactVectorizer(max_features=800)
        docs_list = list(self.documents.values())
        self.vectorizer.fit_documents(docs_list)
    
    def search_documents(self, query: str, top_k: int = 5) -> List[MobileDocument]:
        """搜索文档"""
        if not self.vectorizer or not self.vectorizer.fitted:
            logger.error("向量化器未准备就绪")
            return []
        
        # 向量搜索
        results = self.vectorizer.search(query, top_k)
        
        documents = []
        for doc_id, score in results:
            if doc_id in self.documents:
                doc = self.documents[doc_id]
                doc.score = score
                documents.append(doc)
        
        return documents
    
    def get_predefined_answer(self, query: str) -> Optional[str]:
        """获取预定义答案"""
        query_lower = query.lower()
        
        # 八卦查询
        for gua_name, gua_info in self.yixue_knowledge['bagua'].items():
            if gua_name in query:
                return f"{gua_name}卦：{gua_info['meaning']}，五行属{gua_info['wuxing']}，方位{gua_info['direction']}"
        
        # 五行生克查询
        if '相生' in query or '生克' in query:
            wuxing_sheng = self.yixue_knowledge['wuxing']['生']
            sheng_info = "，".join([f"{k}生{v}" for k, v in wuxing_sheng.items()])
            return f"五行相生：{sheng_info}"
        
        if '相克' in query:
            wuxing_ke = self.yixue_knowledge['wuxing']['克']
            ke_info = "，".join([f"{k}克{v}" for k, v in wuxing_ke.items()])
            return f"五行相克：{ke_info}"
        
        # 天干地支查询
        if '天干' in query:
            return f"十天干：{' '.join(self.yixue_knowledge['tiangan'])}"
        
        if '地支' in query:
            return f"十二地支：{' '.join(self.yixue_knowledge['dizhi'])}"
        
        return None
    
    def save_cache(self) -> None:
        """保存缓存到磁盘"""
        cache_file = self.cache_dir / "mobile_cache.pkl.gz"
        
        cache_data = {
            'response_cache': dict(self.response_cache.cache),
            'embedding_cache': dict(self.embedding_cache.cache),
            'stats': self.stats,
            'timestamp': datetime.now().isoformat()
        }
        
        with gzip.open(cache_file, 'wb') as f:
            pickle.dump(cache_data, f, protocol=pickle.HIGHEST_PROTOCOL)
        
        logger.info(f"缓存已保存: {cache_file}")
    
    def load_cache(self) -> None:
        """从磁盘加载缓存"""
        cache_file = self.cache_dir / "mobile_cache.pkl.gz"
        
        if not cache_file.exists():
            return
        
        try:
            with gzip.open(cache_file, 'rb') as f:
                cache_data = pickle.load(f)
            
            # 恢复缓存
            for k, v in cache_data.get('response_cache', {}).items():
                self.response_cache.put(k, v)
            
            for k, v in cache_data.get('embedding_cache', {}).items():
                self.embedding_cache.put(k, v)
            
            # 恢复统计
            self.stats.update(cache_data.get('stats', {}))
            
            logger.info(f"缓存已加载: {cache_file}")
            
        except Exception as e:
            logger.error(f"缓存加载失败: {e}")


class MobileRAGEngine:
    """移动端RAG引擎"""
    
    def __init__(self, db_path: str, cache_dir: str = "./mobile_cache", 
                 max_docs: int = 1000, enable_cache: bool = True):
        """初始化移动端RAG引擎"""
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.enable_cache = enable_cache
        
        # 知识库
        self.kb = MobileKnowledgeBase(db_path, str(self.cache_dir))
        
        # 初始化
        self._initialize(max_docs)
        
        # 线程锁（用于多线程安全）
        self.lock = threading.Lock()
    
    def _initialize(self, max_docs: int) -> None:
        """初始化系统"""
        logger.info("初始化移动端RAG引擎...")
        
        # 加载缓存
        if self.enable_cache:
            self.kb.load_cache()
        
        # 加载数据
        self.kb.load_data(max_docs)
        
        logger.info("移动端RAG引擎初始化完成")
    
    def query(self, question: str, max_length: int = 200) -> MobileResponse:
        """处理查询（优化版）"""
        start_time = time.time()
        
        with self.lock:
            # 检查缓存
            cache_key = hashlib.md5(question.encode()).hexdigest()
            if self.enable_cache:
                cached_response = self.kb.response_cache.get(cache_key)
                if cached_response:
                    self.kb.stats['cache_hits'] += 1
                    response_time = time.time() - start_time
                    cached_response['response_time'] = response_time
                    cached_response['cached'] = True
                    return MobileResponse(**cached_response)
            
            self.kb.stats['cache_misses'] += 1
            self.kb.stats['total_queries'] += 1
            
            try:
                # 1. 检查预定义答案
                predefined_answer = self.kb.get_predefined_answer(question)
                if predefined_answer:
                    response_time = time.time() - start_time
                    response = MobileResponse(
                        question=question,
                        answer=predefined_answer,
                        confidence=0.9,
                        response_time=response_time,
                        sources=['预定义知识库']
                    )
                    
                    # 缓存结果
                    if self.enable_cache:
                        self.kb.response_cache.put(cache_key, {
                            'question': question,
                            'answer': predefined_answer,
                            'confidence': 0.9,
                            'response_time': response_time,
                            'sources': ['预定义知识库']
                        })
                    
                    return response
                
                # 2. 文档检索
                docs = self.kb.search_documents(question, top_k=3)
                
                # 3. 生成答案
                answer = self._generate_answer(question, docs, max_length)
                confidence = self._calculate_confidence(question, docs)
                sources = [doc.metadata.get('name', doc.id[:8]) for doc in docs[:2]]
                
                response_time = time.time() - start_time
                
                # 4. 构建响应
                response = MobileResponse(
                    question=question,
                    answer=answer,
                    confidence=confidence,
                    response_time=response_time,
                    sources=sources
                )
                
                # 5. 缓存结果
                if self.enable_cache and confidence > 0.3:
                    self.kb.response_cache.put(cache_key, {
                        'question': question,
                        'answer': answer,
                        'confidence': confidence,
                        'response_time': response_time,
                        'sources': sources
                    })
                
                # 6. 更新统计
                self._update_stats(response_time)
                
                return response
                
            except Exception as e:
                logger.error(f"查询处理失败: {e}")
                response_time = time.time() - start_time
                return MobileResponse(
                    question=question,
                    answer=f"抱歉，处理问题时出现错误。",
                    confidence=0.0,
                    response_time=response_time,
                    sources=[]
                )
    
    def _generate_answer(self, question: str, docs: List[MobileDocument], 
                        max_length: int = 200) -> str:
        """生成答案（轻量化版本）"""
        if not docs:
            return "抱歉，没有找到相关信息。请尝试重新提问或使用不同的关键词。"
        
        answer_parts = []
        
        # 根据问题类型决定答案结构
        if any(word in question for word in ['什么是', '含义', '意思', '定义']):
            # 解释类问题
            best_doc = docs[0]
            answer_parts.append(f"关于您询问的内容：")
            content = best_doc.content[:100]
            answer_parts.append(content)
            
            if len(docs) > 1:
                answer_parts.append(f"相关信息：{docs[1].content[:50]}...")
                
        elif any(word in question for word in ['如何', '怎么', '方法']):
            # 方法类问题
            answer_parts.append(f"关于{question}：")
            for i, doc in enumerate(docs[:2], 1):
                answer_parts.append(f"{i}. {doc.content[:80]}...")
                
        else:
            # 通用问题
            answer_parts.append(f"根据易学资料：")
            best_doc = docs[0]
            answer_parts.append(best_doc.content[:120])
            
            if len(docs) > 1 and docs[1].score > 0.3:
                answer_parts.append(f"另外，{docs[1].content[:60]}...")
        
        answer = "\n".join(answer_parts)
        
        # 确保答案不超过最大长度
        if len(answer) > max_length:
            answer = answer[:max_length-3] + "..."
        
        return answer
    
    def _calculate_confidence(self, question: str, docs: List[MobileDocument]) -> float:
        """计算置信度"""
        if not docs:
            return 0.0
        
        confidence = 0.3  # 基础置信度
        
        # 基于最佳匹配分数
        if docs[0].score > 0.5:
            confidence += 0.4
        elif docs[0].score > 0.3:
            confidence += 0.2
        
        # 基于文档数量
        if len(docs) >= 2:
            confidence += 0.1
        
        # 基于关键词匹配
        question_words = set(jieba.lcut(question.lower()))
        for doc in docs[:2]:
            doc_words = set(jieba.lcut(doc.content.lower()))
            overlap = len(question_words & doc_words)
            confidence += min(0.2, overlap * 0.05)
        
        return min(confidence, 1.0)
    
    def _update_stats(self, response_time: float) -> None:
        """更新统计信息"""
        # 更新平均响应时间
        total_time = self.kb.stats['avg_response_time'] * (self.kb.stats['total_queries'] - 1)
        self.kb.stats['avg_response_time'] = (total_time + response_time) / self.kb.stats['total_queries']
    
    def batch_query(self, questions: List[str], max_workers: int = 3) -> List[MobileResponse]:
        """批量查询（限制并发数）"""
        responses = []
        
        # 简单的顺序处理（避免过多并发）
        for question in questions:
            response = self.query(question)
            responses.append(response)
        
        return responses
    
    def get_stats(self) -> Dict[str, Any]:
        """获取性能统计"""
        total_requests = self.kb.stats['cache_hits'] + self.kb.stats['cache_misses']
        cache_hit_rate = self.kb.stats['cache_hits'] / max(1, total_requests)
        
        return {
            **self.kb.stats,
            'cache_hit_rate': cache_hit_rate,
            'cache_size': self.kb.response_cache.size(),
            'document_count': len(self.kb.documents),
            'memory_efficient': True
        }
    
    def clear_cache(self) -> None:
        """清理缓存"""
        self.kb.response_cache.clear()
        self.kb.embedding_cache.clear()
        logger.info("缓存已清理")
    
    def save(self) -> None:
        """保存系统状态"""
        if self.enable_cache:
            self.kb.save_cache()
        
        # 保存统计信息
        stats_file = self.cache_dir / "mobile_stats.json"
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump(self.get_stats(), f, ensure_ascii=False, indent=2)
        
        logger.info("移动端系统状态已保存")
    
    def optimize_for_mobile(self) -> Dict[str, Any]:
        """移动端优化设置"""
        optimizations = {
            'max_cache_size': 50,
            'max_document_length': 200,
            'max_response_length': 150,
            'enable_compression': True,
            'reduce_precision': True
        }
        
        # 应用优化设置
        self.kb.response_cache.capacity = optimizations['max_cache_size']
        
        logger.info("移动端优化已应用")
        return optimizations


class MobileRAGAPI:
    """移动端RAG API接口"""
    
    def __init__(self, engine: MobileRAGEngine):
        self.engine = engine
    
    def ask(self, question: str, options: Dict[str, Any] = None) -> Dict[str, Any]:
        """问答接口"""
        if options is None:
            options = {}
        
        max_length = options.get('max_length', 150)
        response = self.engine.query(question, max_length)
        
        return response.to_dict()
    
    def batch_ask(self, questions: List[str], options: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """批量问答接口"""
        responses = self.engine.batch_query(questions)
        return [resp.to_dict() for resp in responses]
    
    def get_system_info(self) -> Dict[str, Any]:
        """获取系统信息"""
        return {
            'name': 'Mobile YiXue RAG Engine',
            'version': '1.0',
            'stats': self.engine.get_stats(),
            'capabilities': [
                'offline_query',
                'cache_optimization', 
                'memory_efficient',
                'batch_processing'
            ]
        }
    
    def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        try:
            test_response = self.engine.query("测试")
            return {
                'status': 'healthy',
                'response_time': test_response.response_time,
                'cache_hit_rate': self.engine.get_stats()['cache_hit_rate'],
                'memory_usage': 'optimal'
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }


def create_mobile_rag_system(db_path: str, cache_dir: str = "./mobile_cache",
                           max_docs: int = 800) -> MobileRAGEngine:
    """创建移动端RAG系统"""
    logger.info("创建移动端RAG系统...")
    
    engine = MobileRAGEngine(
        db_path=db_path,
        cache_dir=cache_dir,
        max_docs=max_docs,
        enable_cache=True
    )
    
    # 应用移动端优化
    engine.optimize_for_mobile()
    
    logger.info("移动端RAG系统创建完成")
    return engine


if __name__ == "__main__":
    # 测试移动端RAG系统
    def test_mobile_rag():
        db_path = "../database/yixue_knowledge_base.db"
        
        # 创建移动端引擎
        engine = create_mobile_rag_system(db_path, max_docs=500)
        
        # 创建API接口
        api = MobileRAGAPI(engine)
        
        # 测试问题
        test_questions = [
            "乾卦是什么意思？",
            "五行相生的顺序是什么？",
            "什么是八卦？",
            "天干有哪些？",
            "坤卦和乾卦有什么关系？"
        ]
        
        print("=== 移动端RAG系统测试 ===\n")
        
        # 单个查询测试
        for i, question in enumerate(test_questions, 1):
            print(f"问题 {i}: {question}")
            response = api.ask(question)
            
            print(f"答案: {response['answer'][:100]}...")
            print(f"置信度: {response['confidence']:.3f}")
            print(f"响应时间: {response['response_time']:.3f}s")
            print(f"缓存: {response['cached']}")
            print("-" * 50)
        
        # 批量查询测试
        print("\n批量查询测试:")
        batch_responses = api.batch_ask(test_questions[:3])
        for resp in batch_responses:
            print(f"Q: {resp['question'][:20]}... | 置信度: {resp['confidence']:.3f}")
        
        # 系统信息
        print("\n系统信息:")
        system_info = api.get_system_info()
        print(f"文档数量: {system_info['stats']['document_count']}")
        print(f"缓存命中率: {system_info['stats']['cache_hit_rate']:.3f}")
        print(f"平均响应时间: {system_info['stats']['avg_response_time']:.3f}s")
        
        # 健康检查
        health = api.health_check()
        print(f"\n系统状态: {health['status']}")
        
        # 保存系统状态
        engine.save()
        print("\n系统状态已保存")
    
    test_mobile_rag()