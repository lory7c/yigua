"""
RAG (Retrieval-Augmented Generation) 框架
检索增强生成系统，结合知识图谱和向量检索
"""

import asyncio
from typing import List, Dict, Any, Optional, Tuple, Union
from dataclasses import dataclass, field
from datetime import datetime
import json
import logging
from pathlib import Path
from enum import Enum
import hashlib
import re

import numpy as np
from transformers import pipeline, AutoTokenizer, AutoModelForCausalLM
import torch

# 导入知识图谱和向量存储
import sys
sys.path.append(str(Path(__file__).parent.parent))
from knowledge_graph.graph_builder import YiJingKnowledgeGraph, Entity
from knowledge_graph.vector_store import VectorStore, Document, SearchResult, FaissVectorStore, HybridVectorStore

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RetrievalStrategy(Enum):
    """检索策略"""
    VECTOR_ONLY = "vector_only"           # 仅向量检索
    GRAPH_ONLY = "graph_only"             # 仅图谱检索
    HYBRID = "hybrid"                     # 混合检索
    CHAIN = "chain"                       # 链式检索
    ENSEMBLE = "ensemble"                 # 集成检索


@dataclass
class Context:
    """上下文信息"""
    question: str
    retrieved_documents: List[Document] = field(default_factory=list)
    graph_entities: List[Entity] = field(default_factory=list)
    graph_relations: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_prompt_context(self) -> str:
        """转换为提示词上下文"""
        context_parts = []
        
        # 添加检索到的文档
        if self.retrieved_documents:
            context_parts.append("【相关文献】")
            for i, doc in enumerate(self.retrieved_documents[:5], 1):
                context_parts.append(f"{i}. {doc.content[:200]}...")
        
        # 添加图谱实体
        if self.graph_entities:
            context_parts.append("\n【相关概念】")
            for entity in self.graph_entities[:5]:
                props = ', '.join([f"{k}:{v}" for k, v in entity.properties.items()][:3])
                context_parts.append(f"- {entity.name} ({entity.entity_type}): {props}")
        
        # 添加关系
        if self.graph_relations:
            context_parts.append("\n【概念关系】")
            for rel in self.graph_relations[:5]:
                context_parts.append(f"- {rel['source']} {rel['relation']} {rel['target']}")
        
        return '\n'.join(context_parts)


@dataclass
class RAGResponse:
    """RAG响应"""
    answer: str
    context: Context
    confidence: float
    sources: List[str] = field(default_factory=list)
    reasoning_path: List[str] = field(default_factory=list)
    generated_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'answer': self.answer,
            'question': self.context.question,
            'confidence': self.confidence,
            'sources': self.sources,
            'reasoning_path': self.reasoning_path,
            'retrieved_docs': len(self.context.retrieved_documents),
            'graph_entities': len(self.context.graph_entities),
            'generated_at': self.generated_at.isoformat()
        }


class PromptTemplate:
    """提示词模板"""
    
    # 易学问答模板
    YIJING_QA = """你是一位精通易经的专家。请根据以下背景信息回答用户的问题。

{context}

用户问题：{question}

请提供准确、详细的回答，如果涉及卦象或爻辞，请引用原文。如果信息不足，请诚实说明。

回答："""

    # 占卜解释模板
    DIVINATION = """你是一位经验丰富的易经占卜师。请根据以下信息为用户解卦。

{context}

占问事项：{question}

请从以下方面解释：
1. 卦象含义
2. 爻辞解释
3. 变化趋势
4. 实际建议

解卦："""

    # 概念解释模板
    CONCEPT_EXPLANATION = """你是易学知识专家。请解释以下概念。

{context}

需要解释的概念：{question}

请提供：
1. 基本定义
2. 在易学中的意义
3. 相关概念
4. 实际应用

解释："""

    # 关系分析模板
    RELATION_ANALYSIS = """你是易学关系分析专家。请分析以下概念之间的关系。

{context}

分析主题：{question}

请说明：
1. 概念之间的联系
2. 相生相克关系
3. 转化条件
4. 应用场景

分析："""

    @classmethod
    def get_template(cls, template_type: str) -> str:
        """获取模板"""
        templates = {
            'qa': cls.YIJING_QA,
            'divination': cls.DIVINATION,
            'concept': cls.CONCEPT_EXPLANATION,
            'relation': cls.RELATION_ANALYSIS
        }
        return templates.get(template_type, cls.YIJING_QA)


class ChunkingStrategy:
    """文本分块策略"""
    
    @staticmethod
    def sliding_window(text: str, window_size: int = 512, overlap: int = 128) -> List[str]:
        """滑动窗口分块"""
        chunks = []
        start = 0
        
        while start < len(text):
            end = min(start + window_size, len(text))
            chunk = text[start:end]
            chunks.append(chunk)
            
            if end >= len(text):
                break
            
            start += (window_size - overlap)
        
        return chunks
    
    @staticmethod
    def semantic_chunking(text: str, max_chunk_size: int = 512) -> List[str]:
        """语义分块（按段落和句子）"""
        chunks = []
        current_chunk = []
        current_size = 0
        
        # 按段落分割
        paragraphs = text.split('\n\n')
        
        for para in paragraphs:
            para_size = len(para)
            
            if current_size + para_size > max_chunk_size:
                if current_chunk:
                    chunks.append('\n\n'.join(current_chunk))
                current_chunk = [para]
                current_size = para_size
            else:
                current_chunk.append(para)
                current_size += para_size
        
        if current_chunk:
            chunks.append('\n\n'.join(current_chunk))
        
        return chunks
    
    @staticmethod
    def hierarchical_chunking(text: str, levels: List[int] = [128, 256, 512]) -> Dict[str, List[str]]:
        """层次化分块"""
        results = {}
        
        for level in levels:
            chunks = ChunkingStrategy.sliding_window(text, level, level // 4)
            results[f"level_{level}"] = chunks
        
        return results


class RAGOrchestrator:
    """RAG编排器"""
    
    def __init__(self,
                 knowledge_graph: YiJingKnowledgeGraph,
                 vector_store: VectorStore,
                 llm_model: Optional[Any] = None,
                 retrieval_strategy: RetrievalStrategy = RetrievalStrategy.HYBRID):
        """初始化RAG编排器
        
        Args:
            knowledge_graph: 知识图谱
            vector_store: 向量存储
            llm_model: 语言模型
            retrieval_strategy: 检索策略
        """
        self.kg = knowledge_graph
        self.vs = vector_store
        self.llm = llm_model
        self.strategy = retrieval_strategy
        
        # 查询分析器
        self.query_analyzer = QueryAnalyzer()
        
        # 重排序器
        self.reranker = Reranker()
        
        logger.info(f"RAG编排器初始化完成，策略: {retrieval_strategy.value}")
    
    async def process_query(self,
                          query: str,
                          top_k: int = 5,
                          template_type: str = 'qa') -> RAGResponse:
        """处理查询
        
        Args:
            query: 用户查询
            top_k: 检索数量
            template_type: 模板类型
        
        Returns:
            RAG响应
        """
        # 1. 分析查询
        query_info = self.query_analyzer.analyze(query)
        
        # 2. 执行检索
        context = await self._retrieve(query, query_info, top_k)
        context.question = query
        
        # 3. 生成回答
        if self.llm:
            answer = await self._generate(context, template_type)
        else:
            answer = self._rule_based_answer(context)
        
        # 4. 评估置信度
        confidence = self._evaluate_confidence(context, answer)
        
        # 5. 提取来源
        sources = self._extract_sources(context)
        
        # 6. 构建响应
        response = RAGResponse(
            answer=answer,
            context=context,
            confidence=confidence,
            sources=sources,
            reasoning_path=query_info.get('reasoning_path', [])
        )
        
        return response
    
    async def _retrieve(self,
                       query: str,
                       query_info: Dict[str, Any],
                       top_k: int) -> Context:
        """执行检索"""
        context = Context(question=query)
        
        if self.strategy == RetrievalStrategy.VECTOR_ONLY:
            # 仅向量检索
            docs = await self._vector_retrieve(query, top_k)
            context.retrieved_documents = docs
            
        elif self.strategy == RetrievalStrategy.GRAPH_ONLY:
            # 仅图谱检索
            entities, relations = await self._graph_retrieve(query, query_info, top_k)
            context.graph_entities = entities
            context.graph_relations = relations
            
        elif self.strategy == RetrievalStrategy.HYBRID:
            # 混合检索
            docs_task = self._vector_retrieve(query, top_k)
            graph_task = self._graph_retrieve(query, query_info, top_k)
            
            docs, (entities, relations) = await asyncio.gather(docs_task, graph_task)
            
            context.retrieved_documents = docs
            context.graph_entities = entities
            context.graph_relations = relations
            
        elif self.strategy == RetrievalStrategy.CHAIN:
            # 链式检索
            docs = await self._vector_retrieve(query, top_k // 2)
            
            # 从文档中提取实体
            entity_names = self._extract_entities_from_docs(docs)
            
            # 基于实体检索图谱
            entities, relations = await self._graph_retrieve_by_entities(entity_names, top_k // 2)
            
            context.retrieved_documents = docs
            context.graph_entities = entities
            context.graph_relations = relations
            
        elif self.strategy == RetrievalStrategy.ENSEMBLE:
            # 集成检索
            strategies = [
                self._vector_retrieve(query, top_k),
                self._graph_retrieve(query, query_info, top_k),
                self._hybrid_retrieve(query, top_k)
            ]
            
            results = await asyncio.gather(*strategies)
            
            # 合并结果
            context = self._merge_contexts(results)
        
        # 重排序
        context = self.reranker.rerank(context, query)
        
        return context
    
    async def _vector_retrieve(self, query: str, top_k: int) -> List[Document]:
        """向量检索"""
        results = self.vs.search(query, top_k)
        return [r.document for r in results]
    
    async def _graph_retrieve(self,
                            query: str,
                            query_info: Dict[str, Any],
                            top_k: int) -> Tuple[List[Entity], List[Dict[str, Any]]]:
        """图谱检索"""
        entities = []
        relations = []
        
        # 提取查询中的实体
        entity_names = query_info.get('entities', [])
        
        for name in entity_names:
            entity = self.kg.query_by_name(name)
            if entity:
                entities.append(entity)
                
                # 获取相关实体
                neighbors = self.kg.get_neighbors(entity.id)
                for neighbor, relation in neighbors[:top_k // len(entity_names) if entity_names else top_k]:
                    entities.append(neighbor)
                    relations.append({
                        'source': entity.name,
                        'target': neighbor.name,
                        'relation': relation.relation_type
                    })
        
        # 按类型检索
        if not entities:
            for entity_type in ['hexagram', 'wuxing', 'trigram']:
                type_entities = self.kg.query_by_type(entity_type)
                if type_entities:
                    entities.extend(type_entities[:top_k // 3])
        
        return entities[:top_k], relations[:top_k]
    
    async def _graph_retrieve_by_entities(self,
                                         entity_names: List[str],
                                         top_k: int) -> Tuple[List[Entity], List[Dict[str, Any]]]:
        """基于实体名称的图谱检索"""
        entities = []
        relations = []
        
        for name in entity_names[:5]:
            entity = self.kg.query_by_name(name)
            if entity:
                entities.append(entity)
                
                neighbors = self.kg.get_neighbors(entity.id)
                for neighbor, relation in neighbors[:2]:
                    entities.append(neighbor)
                    relations.append({
                        'source': entity.name,
                        'target': neighbor.name,
                        'relation': relation.relation_type
                    })
        
        return entities[:top_k], relations[:top_k]
    
    async def _hybrid_retrieve(self, query: str, top_k: int) -> Context:
        """混合检索（向量+关键词）"""
        if isinstance(self.vs, HybridVectorStore):
            results = self.vs.search(query, top_k, alpha=0.7)
            docs = [r.document for r in results]
        else:
            docs = await self._vector_retrieve(query, top_k)
        
        context = Context(question=query)
        context.retrieved_documents = docs
        return context
    
    def _extract_entities_from_docs(self, docs: List[Document]) -> List[str]:
        """从文档中提取实体名称"""
        entities = set()
        
        # 简单的实体提取（可以用NER模型替换）
        patterns = [
            r'[乾坤震巽坎离艮兑]卦',
            r'[金木水火土]',
            r'[甲乙丙丁戊己庚辛壬癸]',
            r'[子丑寅卯辰巳午未申酉戌亥]'
        ]
        
        for doc in docs:
            for pattern in patterns:
                matches = re.findall(pattern, doc.content)
                entities.update(matches)
        
        return list(entities)
    
    def _merge_contexts(self, contexts: List[Any]) -> Context:
        """合并多个上下文"""
        merged = Context(question="")
        
        for ctx in contexts:
            if isinstance(ctx, list):
                # 文档列表
                merged.retrieved_documents.extend(ctx)
            elif isinstance(ctx, tuple):
                # 实体和关系
                entities, relations = ctx
                merged.graph_entities.extend(entities)
                merged.graph_relations.extend(relations)
            elif isinstance(ctx, Context):
                # 完整上下文
                merged.retrieved_documents.extend(ctx.retrieved_documents)
                merged.graph_entities.extend(ctx.graph_entities)
                merged.graph_relations.extend(ctx.graph_relations)
        
        # 去重
        seen_docs = set()
        unique_docs = []
        for doc in merged.retrieved_documents:
            if doc.id not in seen_docs:
                seen_docs.add(doc.id)
                unique_docs.append(doc)
        merged.retrieved_documents = unique_docs
        
        seen_entities = set()
        unique_entities = []
        for entity in merged.graph_entities:
            if entity.id not in seen_entities:
                seen_entities.add(entity.id)
                unique_entities.append(entity)
        merged.graph_entities = unique_entities
        
        return merged
    
    async def _generate(self, context: Context, template_type: str) -> str:
        """使用LLM生成回答"""
        # 构建提示词
        template = PromptTemplate.get_template(template_type)
        prompt = template.format(
            context=context.to_prompt_context(),
            question=context.question
        )
        
        # 生成回答
        if hasattr(self.llm, 'generate'):
            response = await self.llm.generate(prompt)
        else:
            # 同步调用
            response = self.llm(prompt)
        
        return response
    
    def _rule_based_answer(self, context: Context) -> str:
        """基于规则的回答（无LLM时使用）"""
        answer_parts = []
        
        answer_parts.append(f"关于您的问题：{context.question}\n")
        
        if context.retrieved_documents:
            answer_parts.append("根据相关文献：")
            for i, doc in enumerate(context.retrieved_documents[:3], 1):
                answer_parts.append(f"{i}. {doc.content[:150]}...")
        
        if context.graph_entities:
            answer_parts.append("\n相关概念包括：")
            for entity in context.graph_entities[:5]:
                if entity.entity_type == 'hexagram':
                    answer_parts.append(f"- {entity.name}卦：{entity.properties.get('judgment', '')[:100]}")
                elif entity.entity_type == 'wuxing':
                    answer_parts.append(f"- {entity.name}：{entity.properties.get('nature', '')}")
                else:
                    answer_parts.append(f"- {entity.name} ({entity.entity_type})")
        
        if context.graph_relations:
            answer_parts.append("\n概念关系：")
            for rel in context.graph_relations[:3]:
                answer_parts.append(f"- {rel['source']} {rel['relation']} {rel['target']}")
        
        return '\n'.join(answer_parts)
    
    def _evaluate_confidence(self, context: Context, answer: str) -> float:
        """评估回答置信度"""
        confidence = 0.5
        
        # 基于检索结果数量
        if len(context.retrieved_documents) > 3:
            confidence += 0.2
        elif len(context.retrieved_documents) > 0:
            confidence += 0.1
        
        # 基于图谱实体
        if len(context.graph_entities) > 3:
            confidence += 0.2
        elif len(context.graph_entities) > 0:
            confidence += 0.1
        
        # 基于回答长度
        if len(answer) > 200:
            confidence += 0.1
        
        return min(confidence, 1.0)
    
    def _extract_sources(self, context: Context) -> List[str]:
        """提取来源信息"""
        sources = []
        
        for doc in context.retrieved_documents[:3]:
            if 'source' in doc.metadata:
                sources.append(doc.metadata['source'])
            else:
                sources.append(f"文档_{doc.id[:8]}")
        
        for entity in context.graph_entities[:3]:
            if entity.source_refs:
                sources.extend(entity.source_refs[:1])
        
        return list(set(sources))


class QueryAnalyzer:
    """查询分析器"""
    
    def analyze(self, query: str) -> Dict[str, Any]:
        """分析查询意图和实体"""
        analysis = {
            'query': query,
            'intent': self._detect_intent(query),
            'entities': self._extract_entities(query),
            'keywords': self._extract_keywords(query),
            'query_type': self._classify_query(query),
            'reasoning_path': []
        }
        
        return analysis
    
    def _detect_intent(self, query: str) -> str:
        """检测查询意图"""
        intents = {
            'divination': ['占卜', '预测', '问卦', '算卦', '起卦'],
            'explanation': ['什么是', '解释', '含义', '意思', '定义'],
            'relation': ['关系', '区别', '联系', '对应', '相生', '相克'],
            'application': ['如何', '怎么', '方法', '应用', '使用']
        }
        
        for intent, keywords in intents.items():
            for keyword in keywords:
                if keyword in query:
                    return intent
        
        return 'general'
    
    def _extract_entities(self, query: str) -> List[str]:
        """提取实体"""
        entities = []
        
        # 卦名
        gua_names = ['乾', '坤', '震', '巽', '坎', '离', '艮', '兑']
        for name in gua_names:
            if name in query:
                entities.append(name)
        
        # 五行
        wuxing = ['金', '木', '水', '火', '土']
        for wx in wuxing:
            if wx in query and wx + '属性' not in query:  # 避免误判
                entities.append(wx)
        
        # 天干地支
        tiangan = ['甲', '乙', '丙', '丁', '戊', '己', '庚', '辛', '壬', '癸']
        dizhi = ['子', '丑', '寅', '卯', '辰', '巳', '午', '未', '申', '酉', '戌', '亥']
        
        for tg in tiangan:
            if tg in query:
                entities.append(tg)
        
        for dz in dizhi:
            if dz in query:
                entities.append(dz)
        
        return entities
    
    def _extract_keywords(self, query: str) -> List[str]:
        """提取关键词"""
        import jieba
        import jieba.analyse
        
        # 添加易学专有词汇
        jieba.add_word('六爻')
        jieba.add_word('八卦')
        jieba.add_word('五行')
        jieba.add_word('天干地支')
        
        keywords = jieba.analyse.extract_tags(query, topK=5)
        return keywords
    
    def _classify_query(self, query: str) -> str:
        """分类查询类型"""
        if '卦' in query or '爻' in query:
            return 'hexagram'
        elif '五行' in query or '生克' in query:
            return 'wuxing'
        elif '天干' in query or '地支' in query:
            return 'ganzhi'
        else:
            return 'general'


class Reranker:
    """重排序器"""
    
    def rerank(self, context: Context, query: str) -> Context:
        """重排序检索结果"""
        # 计算相关性分数
        if context.retrieved_documents:
            doc_scores = []
            for doc in context.retrieved_documents:
                score = self._calculate_relevance(doc.content, query)
                doc_scores.append((doc, score))
            
            # 排序
            doc_scores.sort(key=lambda x: x[1], reverse=True)
            context.retrieved_documents = [doc for doc, _ in doc_scores]
        
        return context
    
    def _calculate_relevance(self, text: str, query: str) -> float:
        """计算相关性分数（简单版本）"""
        score = 0.0
        
        # 关键词匹配
        query_terms = set(query)
        text_terms = set(text)
        
        overlap = len(query_terms & text_terms)
        score += overlap / len(query_terms) if query_terms else 0
        
        # 完全匹配加分
        if query in text:
            score += 0.5
        
        return score


class RAGPipeline:
    """完整的RAG管道"""
    
    def __init__(self, config_path: Optional[Path] = None):
        """初始化RAG管道"""
        self.config = self._load_config(config_path)
        self.kg = None
        self.vs = None
        self.orchestrator = None
        
        self._initialize_components()
    
    def _load_config(self, config_path: Optional[Path]) -> Dict[str, Any]:
        """加载配置"""
        default_config = {
            'knowledge_graph': {
                'path': 'knowledge_graph.pkl'
            },
            'vector_store': {
                'type': 'faiss',
                'index_path': 'vector_index',
                'embedding_model': 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2'
            },
            'retrieval': {
                'strategy': 'hybrid',
                'top_k': 5
            },
            'generation': {
                'use_llm': False,
                'model_name': None
            }
        }
        
        if config_path and config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                user_config = json.load(f)
                default_config.update(user_config)
        
        return default_config
    
    def _initialize_components(self):
        """初始化组件"""
        # 加载知识图谱
        kg_path = Path(self.config['knowledge_graph']['path'])
        if kg_path.exists():
            self.kg = YiJingKnowledgeGraph.load(kg_path)
        else:
            self.kg = YiJingKnowledgeGraph()
            logger.warning("知识图谱文件不存在，使用默认图谱")
        
        # 初始化向量存储
        vs_config = self.config['vector_store']
        if vs_config['type'] == 'faiss':
            self.vs = FaissVectorStore(
                Path(vs_config['index_path']),
                vs_config['embedding_model']
            )
        elif vs_config['type'] == 'hybrid':
            self.vs = HybridVectorStore(
                Path(vs_config['index_path']),
                vs_config['embedding_model']
            )
        
        # 初始化LLM（如果配置）
        llm = None
        if self.config['generation']['use_llm']:
            llm = self._initialize_llm()
        
        # 初始化编排器
        strategy = RetrievalStrategy[self.config['retrieval']['strategy'].upper()]
        self.orchestrator = RAGOrchestrator(self.kg, self.vs, llm, strategy)
    
    def _initialize_llm(self):
        """初始化语言模型"""
        model_name = self.config['generation'].get('model_name')
        if not model_name:
            return None
        
        # 这里可以初始化具体的模型
        # 例如：return LocalLLM(model_name)
        return None
    
    async def query(self, question: str, **kwargs) -> RAGResponse:
        """执行查询"""
        top_k = kwargs.get('top_k', self.config['retrieval']['top_k'])
        template_type = kwargs.get('template_type', 'qa')
        
        response = await self.orchestrator.process_query(
            question,
            top_k=top_k,
            template_type=template_type
        )
        
        return response
    
    def add_documents(self, documents: List[Dict[str, Any]]):
        """添加文档到向量存储"""
        doc_objects = []
        for doc in documents:
            doc_obj = Document(
                id=doc.get('id', hashlib.md5(doc['content'].encode()).hexdigest()),
                content=doc['content'],
                metadata=doc.get('metadata', {})
            )
            doc_objects.append(doc_obj)
        
        self.vs.add_documents(doc_objects)
        logger.info(f"添加了 {len(doc_objects)} 个文档")
    
    def save(self):
        """保存所有组件"""
        # 保存知识图谱
        self.kg.save()
        
        # 保存向量索引
        if hasattr(self.vs, 'save'):
            self.vs.save()
        
        logger.info("RAG管道组件已保存")


if __name__ == "__main__":
    # 测试RAG系统
    import asyncio
    
    async def test_rag():
        # 初始化管道
        pipeline = RAGPipeline()
        
        # 添加测试文档
        test_docs = [
            {
                'content': '乾卦是易经六十四卦之首，象征天、刚健、自强不息。乾为纯阳之卦，代表创造力和领导力。',
                'metadata': {'type': 'hexagram', 'source': 'yijing'}
            },
            {
                'content': '五行相生：木生火，火生土，土生金，金生水，水生木。这是自然界的基本规律。',
                'metadata': {'type': 'wuxing', 'source': 'theory'}
            }
        ]
        pipeline.add_documents(test_docs)
        
        # 测试查询
        questions = [
            "乾卦的含义是什么？",
            "五行相生的顺序是什么？",
            "天干地支如何对应五行？"
        ]
        
        for question in questions:
            print(f"\n问题: {question}")
            response = await pipeline.query(question)
            print(f"回答: {response.answer[:200]}...")
            print(f"置信度: {response.confidence:.2f}")
            print(f"来源: {', '.join(response.sources[:3])}")
    
    # 运行测试
    asyncio.run(test_rag())