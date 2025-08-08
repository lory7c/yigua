#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
易学知识问答引擎 (Enhanced RAG Engine)
集成知识图谱、向量检索和智能推理的问答系统
支持多模态检索、动态重排序和答案生成
"""

import asyncio
import sqlite3
import json
import logging
import numpy as np
import os
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional, Union
from dataclasses import dataclass, field, asdict
from datetime import datetime
from collections import defaultdict, Counter
import re
import hashlib
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# LLM 相关导入
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    from transformers import AutoTokenizer, AutoModelForCausalLM
    import torch
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False

import jieba
import jieba.analyse
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import networkx as nx

# 导入本地模块
from graph_builder import YixueKnowledgeGraphBuilder, Entity, Relation
from vector_engine import YixueVectorEngine, Document, SearchResult

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class QueryContext:
    """查询上下文"""
    query: str
    intent: str = 'general'  # general, divination, explanation, relation, application
    entities: List[str] = field(default_factory=list)
    concepts: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    category: str = 'general'  # hexagram, wuxing, ganzhi, general
    confidence: float = 0.5
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass 
class RetrievalResult:
    """检索结果"""
    query: str
    vector_results: List[SearchResult] = field(default_factory=list)
    graph_entities: List[Entity] = field(default_factory=list)  
    graph_relations: List[Dict[str, Any]] = field(default_factory=list)
    combined_score: float = 0.0
    sources: List[str] = field(default_factory=list)


@dataclass
class QAResponse:
    """问答响应"""
    question: str
    answer: str
    confidence: float
    sources: List[str] = field(default_factory=list)
    reasoning_steps: List[str] = field(default_factory=list)
    related_concepts: List[str] = field(default_factory=list)
    context_used: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    llm_model: str = "template_based"
    tokens_used: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'question': self.question,
            'answer': self.answer,
            'confidence': self.confidence,
            'sources': self.sources,
            'reasoning_steps': self.reasoning_steps,
            'related_concepts': self.related_concepts,
            'context_used': {
                'vector_docs': self.context_used.get('vector_docs', 0),
                'graph_entities': self.context_used.get('graph_entities', 0),
                'graph_relations': self.context_used.get('graph_relations', 0)
            },
            'timestamp': self.timestamp.isoformat(),
            'llm_model': self.llm_model,
            'tokens_used': self.tokens_used
        }


class QueryAnalyzer:
    """高级查询分析器"""
    
    def __init__(self):
        # 意图识别模式
        self.intent_patterns = {
            'divination': [
                r'占卜|问卦|起卦|算命|预测|运势|吉凶',
                r'会.*?吗|能.*?吗|应该.*?吗',
                r'什么时候|何时|几时'
            ],
            'explanation': [
                r'什么是|含义|意思|定义|解释|表示',
                r'为什么|怎么理解|如何解释',
                r'象征|代表|寓意'
            ],
            'relation': [
                r'关系|区别|联系|对应|差异',
                r'相生|相克|相冲|相合',
                r'比较|对比|异同'
            ],
            'application': [
                r'如何|怎么|方法|运用|应用',
                r'实际|实践|操作|使用',
                r'指导|建议|原则'
            ]
        }
        
        # 分类识别模式
        self.category_patterns = {
            'hexagram': [
                r'[乾坤震巽坎离艮兑][卦]',
                r'六十四卦|八卦|本卦|变卦',
                r'爻[辞位]|初爻|上爻|[九六][爻]'
            ],
            'wuxing': [
                r'五行|金木水火土',
                r'生克|相生|相克',
                r'[金木水火土][生克]'
            ],
            'ganzhi': [
                r'天干地支|干支',
                r'[甲乙丙丁戊己庚辛壬癸]',
                r'[子丑寅卯辰巳午未申酉戌亥]'
            ],
            'calendar': [
                r'历法|节气|二十四节气',
                r'农历|阴历|阳历',
                r'立春|立夏|立秋|立冬'
            ]
        }
        
        # 易学实体词典
        self.yixue_entities = {
            '八卦': ['乾', '坤', '震', '艮', '坎', '离', '巽', '兑'],
            '五行': ['金', '木', '水', '火', '土'],
            '天干': ['甲', '乙', '丙', '丁', '戊', '己', '庚', '辛', '壬', '癸'],
            '地支': ['子', '丑', '寅', '卯', '辰', '巳', '午', '未', '申', '酉', '戌', '亥'],
            '卦位': ['初', '二', '三', '四', '五', '上'],
            '节气': ['立春', '雨水', '惊蛰', '春分', '清明', '谷雨', '立夏', '小满', 
                     '芒种', '夏至', '小暑', '大暑', '立秋', '处暑', '白露', '秋分', 
                     '寒露', '霜降', '立冬', '小雪', '大雪', '冬至', '小寒', '大寒']
        }
    
    def analyze(self, query: str) -> QueryContext:
        """全面分析查询"""
        context = QueryContext(query=query)
        
        # 意图识别
        context.intent = self._detect_intent(query)
        
        # 分类识别
        context.category = self._classify_query(query)
        
        # 实体抽取
        context.entities = self._extract_entities(query)
        
        # 概念提取
        context.concepts = self._extract_concepts(query)
        
        # 关键词提取
        context.keywords = self._extract_keywords(query)
        
        # 置信度评估
        context.confidence = self._calculate_confidence(context)
        
        # 元数据
        context.metadata = {
            'query_length': len(query),
            'entity_count': len(context.entities),
            'concept_count': len(context.concepts),
            'has_interrogative': any(word in query for word in ['什么', '如何', '为什么', '怎么', '哪个'])
        }
        
        return context
    
    def _detect_intent(self, query: str) -> str:
        """检测查询意图"""
        scores = defaultdict(float)
        
        for intent, patterns in self.intent_patterns.items():
            for pattern in patterns:
                if re.search(pattern, query):
                    scores[intent] += 1.0
        
        if not scores:
            return 'general'
        
        return max(scores.items(), key=lambda x: x[1])[0]
    
    def _classify_query(self, query: str) -> str:
        """分类查询"""
        scores = defaultdict(float)
        
        for category, patterns in self.category_patterns.items():
            for pattern in patterns:
                matches = len(re.findall(pattern, query))
                scores[category] += matches
        
        if not scores:
            return 'general'
        
        return max(scores.items(), key=lambda x: x[1])[0]
    
    def _extract_entities(self, query: str) -> List[str]:
        """抽取实体"""
        entities = []
        
        for category, entity_list in self.yixue_entities.items():
            for entity in entity_list:
                if entity in query:
                    entities.append(entity)
        
        # 提取卦名
        gua_pattern = r'([乾坤震巽坎离艮兑])[卦]?'
        gua_matches = re.findall(gua_pattern, query)
        entities.extend(gua_matches)
        
        return list(set(entities))
    
    def _extract_concepts(self, query: str) -> List[str]:
        """提取概念"""
        concepts = []
        
        # 易学核心概念
        core_concepts = [
            '阴阳', '太极', '五行', '八卦', '六十四卦', '爻', '卦象', '卦辞',
            '爻辞', '象传', '彖传', '文言传', '序卦传', '说卦传', '杂卦传',
            '天干地支', '五运六气', '纳音', '神煞', '十二长生', '三合', '六冲'
        ]
        
        for concept in core_concepts:
            if concept in query:
                concepts.append(concept)
        
        return concepts
    
    def _extract_keywords(self, query: str) -> List[str]:
        """提取关键词"""
        # 添加易学词汇到jieba词典
        yixue_words = [
            '六爻', '八卦', '五行', '天干地支', '阴阳', '太极',
            '乾卦', '坤卦', '震卦', '巽卦', '坎卦', '离卦', '艮卦', '兑卦',
            '相生', '相克', '生克', '冲合', '刑害'
        ]
        
        for word in yixue_words:
            jieba.add_word(word)
        
        # 使用TF-IDF提取关键词
        keywords = jieba.analyse.extract_tags(query, topK=10, withWeight=False)
        
        # 过滤停用词
        stop_words = {'的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '个'}
        keywords = [kw for kw in keywords if kw not in stop_words and len(kw) > 1]
        
        return keywords[:5]
    
    def _calculate_confidence(self, context: QueryContext) -> float:
        """计算查询理解置信度"""
        confidence = 0.3  # 基础置信度
        
        # 实体识别加分
        if context.entities:
            confidence += min(0.3, len(context.entities) * 0.1)
        
        # 概念识别加分
        if context.concepts:
            confidence += min(0.2, len(context.concepts) * 0.1)
        
        # 明确分类加分
        if context.category != 'general':
            confidence += 0.2
        
        # 明确意图加分
        if context.intent != 'general':
            confidence += 0.2
        
        return min(confidence, 1.0)


class SmartRetriever:
    """智能检索器"""
    
    def __init__(self, vector_engine: YixueVectorEngine, 
                 graph_builder: YixueKnowledgeGraphBuilder):
        self.vector_engine = vector_engine
        self.graph_builder = graph_builder
        
        # 检索策略权重
        self.weights = {
            'vector_semantic': 0.4,
            'vector_keyword': 0.2, 
            'graph_entity': 0.25,
            'graph_relation': 0.15
        }
    
    async def retrieve(self, context: QueryContext, top_k: int = 10) -> RetrievalResult:
        """智能多策略检索"""
        result = RetrievalResult(query=context.query)
        
        # 1. 向量语义检索
        if context.confidence > 0.5:
            vector_results = await self._vector_semantic_search(context, top_k)
            result.vector_results.extend(vector_results[:top_k//2])
        
        # 2. 向量关键词检索
        if context.keywords:
            keyword_results = await self._vector_keyword_search(context, top_k)
            result.vector_results.extend(keyword_results[:top_k//2])
        
        # 3. 图谱实体检索
        if context.entities:
            entities = await self._graph_entity_search(context, top_k)
            result.graph_entities.extend(entities)
        
        # 4. 图谱关系检索  
        if len(context.entities) >= 2:
            relations = await self._graph_relation_search(context, top_k)
            result.graph_relations.extend(relations)
        
        # 5. 去重和排序
        result = self._deduplicate_and_rank(result, context)
        
        # 6. 提取来源
        result.sources = self._extract_sources(result)
        
        return result
    
    async def _vector_semantic_search(self, context: QueryContext, top_k: int) -> List[SearchResult]:
        """向量语义检索"""
        # 构建增强查询
        enhanced_query = context.query
        if context.concepts:
            enhanced_query += " " + " ".join(context.concepts)
        if context.entities:
            enhanced_query += " " + " ".join(context.entities)
        
        # 根据类别过滤
        doc_filter = None
        if context.category != 'general':
            doc_filter = [context.category, 'general']
        
        results = self.vector_engine.hybrid_search(
            enhanced_query, 
            top_k=top_k,
            doc_type_filter=doc_filter
        )
        
        return results
    
    async def _vector_keyword_search(self, context: QueryContext, top_k: int) -> List[SearchResult]:
        """向量关键词检索"""
        results = self.vector_engine.keyword_search(
            context.keywords,
            top_k=top_k
        )
        
        return results
    
    async def _graph_entity_search(self, context: QueryContext, top_k: int) -> List[Any]:
        """图谱实体检索"""
        entities = []
        
        for entity_name in context.entities:
            # 精确匹配实体
            entity_candidates = []
            for entity_id, entity in self.graph_builder.entities.items():
                if entity.name == entity_name or entity_name in entity.name:
                    entity_candidates.append(entity)
            
            entities.extend(entity_candidates[:2])  # 每个实体最多2个候选
            
            # 获取邻居实体
            for entity in entity_candidates[:1]:  # 只对最匹配的实体获取邻居
                neighbors = self.graph_builder.query_neighbors(
                    entity.id, max_depth=1
                )
                
                neighbor_entities = []
                for neighbor_id, neighbor_data in neighbors.items():
                    if neighbor_id != entity.id:
                        neighbor_entity = self.graph_builder.entities.get(neighbor_id)
                        if neighbor_entity:
                            neighbor_entities.append(neighbor_entity)
                
                entities.extend(neighbor_entities[:3])
        
        return entities[:top_k]
    
    async def _graph_relation_search(self, context: QueryContext, top_k: int) -> List[Dict[str, Any]]:
        """图谱关系检索"""
        relations = []
        
        # 查找实体间的直接关系
        for i, entity1 in enumerate(context.entities):
            for j, entity2 in enumerate(context.entities[i+1:], i+1):
                # 查找两个实体间的关系
                entity1_candidates = [eid for eid, e in self.graph_builder.entities.items() 
                                    if e.name == entity1]
                entity2_candidates = [eid for eid, e in self.graph_builder.entities.items() 
                                    if e.name == entity2]
                
                for e1_id in entity1_candidates:
                    for e2_id in entity2_candidates:
                        # 检查图谱中的边
                        if self.graph_builder.graph.has_edge(e1_id, e2_id):
                            edge_data = self.graph_builder.graph[e1_id][e2_id]
                            for edge_id, attrs in edge_data.items():
                                relations.append({
                                    'source': entity1,
                                    'target': entity2,
                                    'relation': attrs.get('relation', 'related'),
                                    'weight': attrs.get('weight', 1.0)
                                })
                        
                        # 检查反向关系
                        if self.graph_builder.graph.has_edge(e2_id, e1_id):
                            edge_data = self.graph_builder.graph[e2_id][e1_id]
                            for edge_id, attrs in edge_data.items():
                                relations.append({
                                    'source': entity2,
                                    'target': entity1,
                                    'relation': attrs.get('relation', 'related'),
                                    'weight': attrs.get('weight', 1.0)
                                })
        
        return relations[:top_k]
    
    def _deduplicate_and_rank(self, result: RetrievalResult, context: QueryContext) -> RetrievalResult:
        """去重和重新排序"""
        # 向量结果去重
        seen_docs = set()
        unique_vector_results = []
        for doc_result in result.vector_results:
            if doc_result.doc_id not in seen_docs:
                seen_docs.add(doc_result.doc_id)
                unique_vector_results.append(doc_result)
        result.vector_results = unique_vector_results
        
        # 图谱实体去重
        seen_entities = set()
        unique_entities = []
        for entity in result.graph_entities:
            if entity.id not in seen_entities:
                seen_entities.add(entity.id)
                unique_entities.append(entity)
        result.graph_entities = unique_entities
        
        # 重新排序向量结果（考虑查询上下文）
        for doc_result in result.vector_results:
            # 基于实体匹配调整分数
            entity_boost = 0
            for entity in context.entities:
                if entity in doc_result.content:
                    entity_boost += 0.1
            
            # 基于概念匹配调整分数
            concept_boost = 0
            for concept in context.concepts:
                if concept in doc_result.content:
                    concept_boost += 0.1
            
            doc_result.score += entity_boost + concept_boost
        
        # 按分数排序
        result.vector_results.sort(key=lambda x: x.score, reverse=True)
        
        return result
    
    def _extract_sources(self, result: RetrievalResult) -> List[str]:
        """提取来源"""
        sources = []
        
        # 从向量结果提取
        for doc_result in result.vector_results[:3]:
            if 'source' in doc_result.metadata:
                sources.append(doc_result.metadata['source'])
            else:
                sources.append(f"文档{doc_result.doc_id[:8]}")
        
        # 从图谱实体提取
        for entity in result.graph_entities[:2]:
            if hasattr(entity, 'properties') and 'source' in entity.properties:
                sources.append(entity.properties['source'])
        
        return list(set(sources))


class LLMClient:
    """大语言模型客户端"""
    
    def __init__(self, 
                 model_type: str = "template",  # template, openai, local
                 model_name: str = "gpt-3.5-turbo",
                 api_key: str = None,
                 base_url: str = None,
                 local_model_path: str = None):
        
        self.model_type = model_type
        self.model_name = model_name
        self.tokens_used = 0
        
        if model_type == "openai" and OPENAI_AVAILABLE:
            self._init_openai_client(api_key, base_url)
        elif model_type == "local" and TRANSFORMERS_AVAILABLE:
            self._init_local_model(local_model_path or model_name)
        else:
            self.model_type = "template"
            logger.info("使用模板生成答案")
    
    def _init_openai_client(self, api_key: str = None, base_url: str = None):
        """OpenAI客户端初始化"""
        try:
            openai.api_key = api_key or os.getenv("OPENAI_API_KEY")
            if base_url:
                openai.api_base = base_url
            self.openai_client = openai
            logger.info(f"成功初始化OpenAI客户端: {self.model_name}")
        except Exception as e:
            logger.error(f"OpenAI客户端初始化失败: {e}")
            self.model_type = "template"
    
    def _init_local_model(self, model_path: str):
        """本地模型初始化"""
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(model_path)
            self.model = AutoModelForCausalLM.from_pretrained(
                model_path,
                torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
                device_map="auto" if torch.cuda.is_available() else None
            )
            logger.info(f"成功加载本地模型: {model_path}")
        except Exception as e:
            logger.error(f"本地模型加载失败: {e}")
            self.model_type = "template"
    
    async def generate_answer(self, prompt: str, max_tokens: int = 1000) -> Tuple[str, int]:
        """生成答案"""
        if self.model_type == "openai":
            return await self._openai_generate(prompt, max_tokens)
        elif self.model_type == "local":
            return await self._local_generate(prompt, max_tokens)
        else:
            return prompt, 0  # 模板模式直接返回
    
    async def _openai_generate(self, prompt: str, max_tokens: int) -> Tuple[str, int]:
        """使用OpenAI API生成答案"""
        try:
            response = await self.openai_client.ChatCompletion.acreate(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": "你是一个专业的易学知识问答专家，擅长古典易学、八卦、五行等中华传统文化。请给出准确、详细、易懂的回答。"},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_tokens,
                temperature=0.7
            )
            
            answer = response.choices[0].message.content.strip()
            tokens_used = response.usage.total_tokens
            self.tokens_used += tokens_used
            
            return answer, tokens_used
            
        except Exception as e:
            logger.error(f"OpenAI API调用失败: {e}")
            return f"抚歉，AI服务临时不可用。\n\n{prompt}", 0
    
    async def _local_generate(self, prompt: str, max_tokens: int) -> Tuple[str, int]:
        """使用本地模型生成答案"""
        try:
            inputs = self.tokenizer(prompt, return_tensors="pt", truncation=True, max_length=2048)
            
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=max_tokens,
                    temperature=0.7,
                    do_sample=True,
                    top_p=0.9,
                    pad_token_id=self.tokenizer.eos_token_id
                )
            
            # 提取新生成的文本
            generated_text = self.tokenizer.decode(outputs[0][inputs['input_ids'].shape[1]:], skip_special_tokens=True)
            tokens_used = len(outputs[0]) - len(inputs['input_ids'][0])
            self.tokens_used += tokens_used
            
            return generated_text.strip(), tokens_used
            
        except Exception as e:
            logger.error(f"本地模型生成失败: {e}")
            return f"抚歉，本地模型临时不可用。\n\n{prompt}", 0


class AnswerGenerator:
    """答案生成器（集成LLM和模板）"""
    
    def __init__(self, 
                 llm_client: LLMClient = None,
                 use_llm: bool = True):
        
        self.llm_client = llm_client or LLMClient(model_type="template")
        self.use_llm = use_llm and self.llm_client.model_type != "template"
        
        # 模板系统作为后备
        self.templates = {
            'general': self._general_template,
            'divination': self._divination_template,
            'explanation': self._explanation_template,
            'relation': self._relation_template,
            'application': self._application_template
        }
    
    async def generate(self, context: QueryContext, retrieval_result: RetrievalResult) -> QAResponse:
        """生成答案（优先LLM，后备模板）"""
        answer = ""
        tokens_used = 0
        model_used = self.llm_client.model_type
        
        try:
            if self.use_llm and self.llm_client.model_type != "template":
                # 使用LLM生成答案
                prompt = self._build_llm_prompt(context, retrieval_result)
                answer, tokens_used = await self.llm_client.generate_answer(prompt, max_tokens=800)
                model_used = self.llm_client.model_name
            else:
                # 使用模板生成
                template_func = self.templates.get(context.intent, self.templates['general'])
                answer = template_func(context, retrieval_result)
                model_used = "template_based"
        
        except Exception as e:
            logger.error(f"LLM生成失败: {e}，使用模板后备")
            template_func = self.templates.get(context.intent, self.templates['general'])
            answer = template_func(context, retrieval_result)
            model_used = "template_fallback"
        
        # 评估置信度
        confidence = self._calculate_confidence(context, retrieval_result, answer)
        
        # 提取推理步骤
        reasoning_steps = self._extract_reasoning(context, retrieval_result)
        
        # 提取相关概念
        related_concepts = self._extract_related_concepts(retrieval_result)
        
        # 构建响应
        response = QAResponse(
            question=context.query,
            answer=answer,
            confidence=confidence,
            sources=retrieval_result.sources,
            reasoning_steps=reasoning_steps,
            related_concepts=related_concepts,
            context_used={
                'vector_docs': len(retrieval_result.vector_results),
                'graph_entities': len(retrieval_result.graph_entities),
                'graph_relations': len(retrieval_result.graph_relations)
            },
            llm_model=model_used,
            tokens_used=tokens_used
        )
        
        return response
    
    def _build_llm_prompt(self, context: QueryContext, retrieval_result: RetrievalResult) -> str:
        """为LLM构建提示词"""
        prompt_parts = []
        
        # 系统指令
        prompt_parts.append("你是一个专业的易学知识问答专家，擅长古典易学、八卦、五行等中华传统文化。")
        prompt_parts.append("请基于下面提供的相关资料回答问题，答案要准确、详细、易懂。\n")
        
        # 查询信息
        prompt_parts.append(f"问题: {context.query}")
        prompt_parts.append(f"查询意图: {context.intent}")
        prompt_parts.append(f"相关实体: {', '.join(context.entities) if context.entities else '无'}")
        prompt_parts.append(f"相关概念: {', '.join(context.concepts) if context.concepts else '无'}\n")
        
        # 相关文档
        if retrieval_result.vector_results:
            prompt_parts.append("相关文献资料:")
            for i, result in enumerate(retrieval_result.vector_results[:5], 1):
                content = result.content[:300] + "..." if len(result.content) > 300 else result.content
                prompt_parts.append(f"{i}. [{result.doc_type}] {content}")
            prompt_parts.append("")
        
        # 知识图谱信息
        if retrieval_result.graph_entities:
            prompt_parts.append("相关概念实体:")
            for entity in retrieval_result.graph_entities[:5]:
                entity_desc = f"{entity.name}({entity.type})"
                if hasattr(entity, 'properties') and entity.properties:
                    if 'basic_meaning' in entity.properties:
                        entity_desc += f": {entity.properties['basic_meaning'][:100]}"
                prompt_parts.append(f"• {entity_desc}")
            prompt_parts.append("")
        
        # 概念关系
        if retrieval_result.graph_relations:
            prompt_parts.append("概念关系:")
            for rel in retrieval_result.graph_relations[:3]:
                prompt_parts.append(f"• {rel['source']} {rel['relation']} {rel['target']}")
            prompt_parts.append("")
        
        # 生成要求
        prompt_parts.append("请基于以上资料给出专业的回答，包括:")
        prompt_parts.append("1. 直接回答问题")
        prompt_parts.append("2. 相关的背景知识")
        prompt_parts.append("3. 实际应用或意义")
        prompt_parts.append("4. 如有必要，可提供延伸阅读建议")
        
        return "\n".join(prompt_parts)
    
    def _general_template(self, context: QueryContext, retrieval: RetrievalResult) -> str:
        """通用回答模板"""
        answer_parts = []
        
        answer_parts.append(f"关于您的问题：{context.query}\n")
        
        # 基于检索到的文档
        if retrieval.vector_results:
            answer_parts.append("根据相关资料：")
            for i, result in enumerate(retrieval.vector_results[:3], 1):
                content = result.content
                if len(content) > 150:
                    content = content[:150] + "..."
                answer_parts.append(f"{i}. {content}")
        
        # 基于图谱实体
        if retrieval.graph_entities:
            answer_parts.append("\n相关概念包括：")
            for entity in retrieval.graph_entities[:5]:
                entity_desc = self._format_entity_description(entity)
                answer_parts.append(f"• {entity_desc}")
        
        # 基于图谱关系
        if retrieval.graph_relations:
            answer_parts.append("\n概念关系：")
            for rel in retrieval.graph_relations[:3]:
                answer_parts.append(f"• {rel['source']} {rel['relation']} {rel['target']}")
        
        return "\n".join(answer_parts)
    
    def _divination_template(self, context: QueryContext, retrieval: RetrievalResult) -> str:
        """占卜回答模板"""
        answer_parts = []
        
        answer_parts.append(f"占卜问题：{context.query}\n")
        
        # 查找相关卦象
        hexagram_entities = [e for e in retrieval.graph_entities if e.type == 'hexagram']
        if hexagram_entities:
            main_hexagram = hexagram_entities[0]
            answer_parts.append(f"主卦：{main_hexagram.name}")
            
            if hasattr(main_hexagram, 'properties'):
                props = main_hexagram.properties
                if 'basic_meaning' in props:
                    answer_parts.append(f"卦意：{props['basic_meaning']}")
                if 'judgement' in props:
                    answer_parts.append(f"卦辞：{props['judgement']}")
                if 'image' in props:
                    answer_parts.append(f"象传：{props['image']}")
        
        # 查找占卜案例
        divination_docs = [r for r in retrieval.vector_results if r.doc_type == 'case']
        if divination_docs:
            answer_parts.append("\n参考案例：")
            for i, doc in enumerate(divination_docs[:2], 1):
                answer_parts.append(f"{i}. {doc.content[:100]}...")
        
        # 给出建议
        answer_parts.append("\n建议：")
        answer_parts.append("请结合具体情况，理性分析，易经主要用于启发思考，不应完全依赖占卜结果。")
        
        return "\n".join(answer_parts)
    
    def _explanation_template(self, context: QueryContext, retrieval: RetrievalResult) -> str:
        """解释说明模板"""
        answer_parts = []
        
        # 提取要解释的主要概念
        main_concepts = context.entities + context.concepts
        if main_concepts:
            main_concept = main_concepts[0]
            answer_parts.append(f"{main_concept}的含义：\n")
            
            # 查找对应的图谱实体
            related_entities = [e for e in retrieval.graph_entities 
                             if main_concept in e.name or e.name in main_concept]
            
            if related_entities:
                entity = related_entities[0]
                answer_parts.append(f"基本定义：{self._format_entity_description(entity)}")
                
                # 属性信息
                if hasattr(entity, 'properties') and entity.properties:
                    for key, value in list(entity.properties.items())[:3]:
                        if key not in ['name', 'id'] and value:
                            answer_parts.append(f"{key}：{value}")
        
        # 相关文献
        if retrieval.vector_results:
            answer_parts.append("\n详细说明：")
            for result in retrieval.vector_results[:2]:
                answer_parts.append(result.content[:200] + "...")
        
        # 相关概念
        if len(retrieval.graph_entities) > 1:
            answer_parts.append("\n相关概念：")
            for entity in retrieval.graph_entities[1:4]:
                answer_parts.append(f"• {entity.name}：{self._get_entity_brief(entity)}")
        
        return "\n".join(answer_parts)
    
    def _relation_template(self, context: QueryContext, retrieval: RetrievalResult) -> str:
        """关系分析模板"""
        answer_parts = []
        
        answer_parts.append(f"关系分析：{context.query}\n")
        
        # 直接关系
        if retrieval.graph_relations:
            answer_parts.append("概念关系：")
            for rel in retrieval.graph_relations:
                answer_parts.append(f"• {rel['source']} {rel['relation']} {rel['target']}")
        
        # 基于实体的关系分析
        if len(context.entities) >= 2:
            entity1, entity2 = context.entities[0], context.entities[1]
            answer_parts.append(f"\n{entity1}与{entity2}的关系：")
            
            # 查找五行生克关系
            if entity1 in ['金', '木', '水', '火', '土'] and entity2 in ['金', '木', '水', '火', '土']:
                wuxing_relation = self._get_wuxing_relation(entity1, entity2)
                answer_parts.append(f"五行关系：{wuxing_relation}")
        
        # 相关文献佐证
        if retrieval.vector_results:
            answer_parts.append("\n文献支持：")
            for result in retrieval.vector_results[:2]:
                answer_parts.append(f"• {result.content[:150]}...")
        
        return "\n".join(answer_parts)
    
    def _application_template(self, context: QueryContext, retrieval: RetrievalResult) -> str:
        """应用指导模板"""
        answer_parts = []
        
        answer_parts.append(f"实用指导：{context.query}\n")
        
        # 方法步骤
        answer_parts.append("基本方法：")
        
        # 从检索结果中提取方法
        method_docs = [r for r in retrieval.vector_results 
                      if any(keyword in r.content for keyword in ['方法', '步骤', '如何', '操作'])]
        
        if method_docs:
            for i, doc in enumerate(method_docs[:2], 1):
                answer_parts.append(f"{i}. {doc.content[:200]}...")
        else:
            # 基于图谱实体提供通用指导
            if retrieval.graph_entities:
                entity = retrieval.graph_entities[0]
                if hasattr(entity, 'properties') and 'practical_application' in entity.properties:
                    answer_parts.append(f"1. {entity.properties['practical_application']}")
        
        # 注意事项
        answer_parts.append("\n注意事项：")
        answer_parts.append("• 理论与实践相结合")
        answer_parts.append("• 因人因时因地制宜")
        answer_parts.append("• 保持客观理性态度")
        
        return "\n".join(answer_parts)
    
    def _format_entity_description(self, entity) -> str:
        """格式化实体描述"""
        if hasattr(entity, 'properties') and entity.properties:
            # 优先使用基本含义
            if 'basic_meaning' in entity.properties:
                return f"{entity.name}：{entity.properties['basic_meaning']}"
            elif 'description' in entity.properties:
                return f"{entity.name}：{entity.properties['description']}"
        
        return f"{entity.name}（{entity.type}）"
    
    def _get_entity_brief(self, entity) -> str:
        """获取实体简要描述"""
        if hasattr(entity, 'properties') and entity.properties:
            for key in ['basic_meaning', 'description', 'nature']:
                if key in entity.properties:
                    desc = entity.properties[key]
                    if len(desc) > 50:
                        return desc[:50] + "..."
                    return desc
        
        return f"{entity.type}概念"
    
    def _get_wuxing_relation(self, element1: str, element2: str) -> str:
        """获取五行关系"""
        sheng_relations = {
            '金': '水', '水': '木', '木': '火', '火': '土', '土': '金'
        }
        ke_relations = {
            '金': '木', '木': '土', '土': '水', '水': '火', '火': '金'
        }
        
        if sheng_relations.get(element1) == element2:
            return f"{element1}生{element2}"
        elif ke_relations.get(element1) == element2:
            return f"{element1}克{element2}"
        elif sheng_relations.get(element2) == element1:
            return f"{element2}生{element1}"
        elif ke_relations.get(element2) == element1:
            return f"{element2}克{element1}"
        else:
            return f"{element1}与{element2}无直接生克关系"
    
    def _calculate_confidence(self, context: QueryContext, retrieval: RetrievalResult, answer: str) -> float:
        """计算答案置信度"""
        confidence = 0.4  # 基础置信度
        
        # 查询理解置信度
        confidence += context.confidence * 0.3
        
        # 检索结果质量
        if retrieval.vector_results:
            avg_score = np.mean([r.score for r in retrieval.vector_results])
            confidence += avg_score * 0.2
        
        if retrieval.graph_entities:
            confidence += min(0.2, len(retrieval.graph_entities) * 0.05)
        
        if retrieval.graph_relations:
            confidence += min(0.1, len(retrieval.graph_relations) * 0.03)
        
        # 答案长度和结构
        if len(answer) > 100:
            confidence += 0.1
        
        # 实体匹配度
        entity_matches = sum(1 for entity in context.entities if entity in answer)
        if context.entities:
            confidence += (entity_matches / len(context.entities)) * 0.1
        
        return min(confidence, 1.0)
    
    def _extract_reasoning(self, context: QueryContext, retrieval: RetrievalResult) -> List[str]:
        """提取推理步骤"""
        steps = []
        
        steps.append(f"1. 分析查询：识别意图为{context.intent}，类别为{context.category}")
        
        if context.entities:
            steps.append(f"2. 实体识别：提取到{len(context.entities)}个相关实体")
        
        if retrieval.vector_results:
            steps.append(f"3. 文档检索：找到{len(retrieval.vector_results)}个相关文档")
        
        if retrieval.graph_entities:
            steps.append(f"4. 知识图谱：匹配到{len(retrieval.graph_entities)}个相关概念")
        
        if retrieval.graph_relations:
            steps.append(f"5. 关系分析：发现{len(retrieval.graph_relations)}个概念关系")
        
        steps.append("6. 综合分析：整合多源信息生成答案")
        
        return steps
    
    def _extract_related_concepts(self, retrieval: RetrievalResult) -> List[str]:
        """提取相关概念"""
        concepts = []
        
        # 从图谱实体提取
        for entity in retrieval.graph_entities[:5]:
            concepts.append(entity.name)
        
        # 从文档中提取（简单关键词提取）
        all_content = " ".join([r.content for r in retrieval.vector_results[:3]])
        keywords = jieba.analyse.extract_tags(all_content, topK=10)
        
        # 过滤易学相关概念
        yixue_keywords = []
        yixue_terms = ['卦', '爻', '五行', '天干', '地支', '阴阳', '太极', '八卦']
        for keyword in keywords:
            if any(term in keyword for term in yixue_terms) or len(keyword) <= 2:
                yixue_keywords.append(keyword)
        
        concepts.extend(yixue_keywords[:5])
        
        return list(set(concepts))


class YixueQAEngine:
    """易学问答引擎主类"""
    
    def __init__(self, 
                 db_path: str, 
                 knowledge_graph_dir: str = "./knowledge_graph",
                 llm_config: Dict[str, Any] = None):
        """初始化问答引擎"""
        self.db_path = db_path
        self.kg_dir = Path(knowledge_graph_dir)
        self.kg_dir.mkdir(exist_ok=True)
        
        # LLM配置
        self.llm_config = llm_config or {
            'model_type': 'template',  # template, openai, local
            'model_name': 'gpt-3.5-turbo',
            'api_key': os.getenv('OPENAI_API_KEY'),
            'base_url': os.getenv('OPENAI_BASE_URL'),
            'use_llm': True
        }
        
        # 初始化组件
        self._init_components()
        
        # 性能统计
        self.stats = {
            'total_queries': 0,
            'successful_queries': 0,
            'avg_response_time': 0.0,
            'avg_confidence': 0.0,
            'total_tokens_used': 0
        }
    
    def _init_components(self):
        """初始化各个组件"""
        logger.info("初始化易学问答引擎组件...")
        
        # 1. 初始化知识图谱构建器
        self.graph_builder = YixueKnowledgeGraphBuilder(
            self.db_path, str(self.kg_dir)
        )
        
        # 2. 初始化向量引擎
        self.vector_engine = YixueVectorEngine(
            self.db_path, output_dir=str(self.kg_dir)
        )
        
        # 3. 初始化查询分析器
        self.query_analyzer = QueryAnalyzer()
        
        # 4. 初始化检索器
        self.retriever = SmartRetriever(self.vector_engine, self.graph_builder)
        
        # 5. 初始化LLM客户端和答案生成器
        self.llm_client = LLMClient(
            model_type=self.llm_config.get('model_type', 'template'),
            model_name=self.llm_config.get('model_name', 'gpt-3.5-turbo'),
            api_key=self.llm_config.get('api_key'),
            base_url=self.llm_config.get('base_url'),
            local_model_path=self.llm_config.get('local_model_path')
        )
        self.generator = AnswerGenerator(
            llm_client=self.llm_client,
            use_llm=self.llm_config.get('use_llm', True)
        )
        
        logger.info("易学问答引擎初始化完成")
    
    async def build_system(self) -> Dict[str, str]:
        """构建完整的问答系统"""
        logger.info("开始构建完整问答系统...")
        
        # 1. 构建知识图谱
        logger.info("构建知识图谱...")
        graph_files = self.graph_builder.build_complete_graph()
        
        # 2. 构建向量系统
        logger.info("构建向量系统...")
        vector_files = self.vector_engine.build_complete_vector_system()
        
        # 3. 保存系统配置
        system_config = {
            'db_path': self.db_path,
            'kg_dir': str(self.kg_dir),
            'graph_files': graph_files,
            'vector_files': vector_files,
            'build_timestamp': datetime.now().isoformat()
        }
        
        config_path = self.kg_dir / 'qa_system_config.json'
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(system_config, f, ensure_ascii=False, indent=2)
        
        all_files = {**graph_files, **vector_files, 'config': str(config_path)}
        
        logger.info("问答系统构建完成！")
        return all_files
    
    async def query(self, question: str, **kwargs) -> QAResponse:
        """处理问答查询"""
        start_time = datetime.now()
        
        try:
            # 1. 查询分析
            context = self.query_analyzer.analyze(question)
            
            # 2. 智能检索
            retrieval_result = await self.retriever.retrieve(
                context, 
                top_k=kwargs.get('top_k', 10)
            )
            
            # 3. 答案生成
            response = await self.generator.generate(context, retrieval_result)
            
            # 4. 更新统计
            response_time = (datetime.now() - start_time).total_seconds()
            self._update_stats(response, response_time)
            
            return response
            
        except Exception as e:
            logger.error(f"查询处理失败: {e}")
            return QAResponse(
                question=question,
                answer=f"抱歉，处理您的问题时出现了错误：{str(e)}",
                confidence=0.0,
                sources=[],
                reasoning_steps=["查询处理失败"],
                related_concepts=[]
            )
    
    def batch_query(self, questions: List[str], **kwargs) -> List[QAResponse]:
        """批量查询"""
        responses = []
        
        for question in questions:
            try:
                response = asyncio.run(self.query(question, **kwargs))
                responses.append(response)
            except Exception as e:
                logger.error(f"批量查询失败 {question}: {e}")
                responses.append(QAResponse(
                    question=question,
                    answer=f"查询失败: {str(e)}",
                    confidence=0.0
                ))
        
        return responses
    
    def _update_stats(self, response: QAResponse, response_time: float):
        """更新性能统计"""
        self.stats['total_queries'] += 1
        if response.confidence > 0.3:
            self.stats['successful_queries'] += 1
        
        # 更新平均响应时间
        total_time = self.stats['avg_response_time'] * (self.stats['total_queries'] - 1)
        self.stats['avg_response_time'] = (total_time + response_time) / self.stats['total_queries']
        
        # 更新平均置信度
        total_conf = self.stats['avg_confidence'] * (self.stats['total_queries'] - 1)
        self.stats['avg_confidence'] = (total_conf + response.confidence) / self.stats['total_queries']
        
        # 更新Token使用统计
        self.stats['total_tokens_used'] += response.tokens_used
    
    def get_stats(self) -> Dict[str, Any]:
        """获取系统统计信息"""
        return {
            **self.stats,
            'success_rate': self.stats['successful_queries'] / max(1, self.stats['total_queries']),
            'avg_tokens_per_query': self.stats['total_tokens_used'] / max(1, self.stats['total_queries']),
            'graph_nodes': self.graph_builder.graph.number_of_nodes(),
            'graph_edges': self.graph_builder.graph.number_of_edges(),
            'vector_documents': len(self.vector_engine.documents),
            'llm_model': self.llm_client.model_name if hasattr(self, 'llm_client') else 'template',
            'vector_engine_type': 'qdrant' if self.vector_engine.use_qdrant else 'faiss'
        }
    
    def save_system(self):
        """保存完整系统"""
        # 保存知识图谱
        graph_files = self.graph_builder.save_graph('all')
        
        # 保存向量数据
        vector_file = self.vector_engine.save_vectors()
        
        # 保存统计数据
        stats_path = self.kg_dir / 'qa_stats.json'
        with open(stats_path, 'w', encoding='utf-8') as f:
            json.dump(self.get_stats(), f, ensure_ascii=False, indent=2)
        
        logger.info("问答系统已保存")
        return {**graph_files, 'vectors': vector_file, 'stats': str(stats_path)}


if __name__ == "__main__":
    # 使用示例
    async def main():
        # 初始化问答引擎
        db_path = "../database/yixue_knowledge_base.db"
        qa_engine = YixueQAEngine(db_path)
        
        # 构建系统
        print("构建问答系统...")
        system_files = await qa_engine.build_system()
        
        print("系统构建完成！文件：")
        for file_type, path in system_files.items():
            print(f"  {file_type}: {path}")
        
        # 测试问答
        test_questions = [
            "乾卦的含义是什么？",
            "五行相生的顺序是怎样的？",
            "天干地支如何与五行对应？",
            "坤卦和乾卦有什么关系？",
            "如何使用易经进行占卜？"
        ]
        
        print("\n测试问答：")
        for question in test_questions:
            print(f"\n问题: {question}")
            response = await qa_engine.query(question)
            
            print(f"答案: {response.answer[:200]}...")
            print(f"置信度: {response.confidence:.3f}")
            print(f"来源: {', '.join(response.sources[:2])}")
            print(f"相关概念: {', '.join(response.related_concepts[:3])}")
        
        # 显示统计信息
        print(f"\n系统统计:")
        stats = qa_engine.get_stats()
        for key, value in stats.items():
            print(f"  {key}: {value}")
    
    # 运行测试
    asyncio.run(main())