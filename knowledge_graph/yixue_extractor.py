#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
易学知识抽取器
专门从文本中抽取易学相关的实体、关系和概念
支持实体识别、关系抽取、概念聚类和知识验证
"""

import re
import json
import logging
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional, Set
from dataclasses import dataclass, field
from collections import defaultdict, Counter
from datetime import datetime
import hashlib

import jieba
import jieba.analyse
import jieba.posseg as pseg
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
from sklearn.metrics.pairwise import cosine_similarity

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class ExtractedEntity:
    """抽取的实体"""
    name: str
    entity_type: str  # hexagram, line, concept, person, book, dynasty
    confidence: float
    positions: List[Tuple[int, int]] = field(default_factory=list)  # 文本位置
    attributes: Dict[str, Any] = field(default_factory=dict)
    context: str = ""
    source_text: str = ""


@dataclass
class ExtractedRelation:
    """抽取的关系"""
    source: str
    target: str
    relation_type: str
    confidence: float
    evidence: str = ""
    positions: List[int] = field(default_factory=list)
    attributes: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExtractedConcept:
    """抽取的概念"""
    concept: str
    category: str
    description: str
    confidence: float
    related_entities: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    examples: List[str] = field(default_factory=list)


class YixuePatterns:
    """易学模式库"""
    
    def __init__(self):
        # 实体识别模式
        self.entity_patterns = {
            'hexagram': [
                r'([乾坤震巽坎离艮兑])[卦]',
                r'(屯|蒙|需|讼|师|比|小畜|履|泰|否|同人|大有|谦|豫|随|蛊|临|观|噬嗑|贲|剥|复|无妄|大畜|颐|大过|坎|离|咸|恒|遁|大壮|晋|明夷|家人|睽|蹇|解|损|益|夬|姤|萃|升|困|井|革|鼎|震|艮|渐|归妹|丰|旅|巽|兑|涣|节|中孚|小过|既济|未济)[卦]?',
                r'六十四卦|八卦|本卦|变卦|互卦|错卦|综卦'
            ],
            'line': [
                r'(初|二|三|四|五|上)[爻]',
                r'[九六][一二三四五]',
                r'爻[辞位变]',
                r'变爻|动爻|静爻'
            ],
            'wuxing': [
                r'[金木水火土][行性]?',
                r'五行',
                r'相生|相克|生克|克制'
            ],
            'ganzhi': [
                r'[甲乙丙丁戊己庚辛壬癸]',
                r'[子丑寅卯辰巳午未申酉戌亥]',
                r'天干|地支|干支|甲子'
            ],
            'person': [
                r'([王李张刘陈杨赵黄周吴徐孙胡朱高林何郭马罗梁宋郑谢韩唐冯于董萧程曹袁邓许傅沈曾彭吕苏卢蒋蔡贾丁魏薛叶阎余潘杜戴夏钟汪田任姜范方石姚谭廖邹熊金陆郝孔白崔康毛邱秦江史顾侯邵孟龙万段雷钱汤尹黎易常武乔贺赖龚文][一-龯]{1,3})',
                r'孔子|老子|庄子|荀子|墨子|韩非子|朱熹|王阳明|程颐|程颢'
            ],
            'dynasty': [
                r'[夏商周秦汉晋隋唐宋元明清][朝代]?',
                r'春秋|战国|三国|南北朝|五代十国'
            ],
            'book': [
                r'《([^》]+)》',
                r'易经|周易|易传|十翼|彖传|象传|文言传|系辞传|说卦传|序卦传|杂卦传'
            ]
        }
        
        # 关系抽取模式
        self.relation_patterns = {
            'belongs_to': [
                r'(.+)属于(.+)',
                r'(.+)是(.+)的一种',
                r'(.+)包含(.+)',
                r'(.+)中的(.+)'
            ],
            'transforms_to': [
                r'(.+)变为(.+)',
                r'(.+)化为(.+)',
                r'(.+)转化为(.+)',
                r'由(.+)变成(.+)'
            ],
            'generates': [
                r'(.+)生(.+)',
                r'(.+)产生(.+)',
                r'(.+)生成(.+)'
            ],
            'restrains': [
                r'(.+)克(.+)',
                r'(.+)制(.+)',
                r'(.+)抑制(.+)'
            ],
            'interprets': [
                r'(.+)解释(.+)',
                r'(.+)注解(.+)',
                r'(.+)阐释(.+)'
            ],
            'corresponds_to': [
                r'(.+)对应(.+)',
                r'(.+)相当于(.+)',
                r'(.+)等同于(.+)'
            ]
        }
        
        # 概念模式
        self.concept_patterns = {
            'yinyang': [
                r'阴阳|太极|两仪',
                r'阴[性质气]|阳[性质气]',
                r'太阴|太阳|少阴|少阳'
            ],
            'wuxing': [
                r'五行|金木水火土',
                r'[金木水火土][行属性质气]',
                r'五行生克|相生相克'
            ],
            'bagua': [
                r'八卦|[乾坤震巽坎离艮兑]{2,}',
                r'先天八卦|后天八卦|文王八卦|伏羲八卦'
            ],
            'liuyao': [
                r'六爻|[初二三四五上]爻',
                r'爻[辞象义变动静]',
                r'变爻|动爻|主卦|变卦'
            ]
        }
        
        # 添加专业词汇到jieba
        self._add_yixue_words()
    
    def _add_yixue_words(self):
        """添加易学专业词汇到jieba词典"""
        yixue_words = [
            # 卦名
            '乾卦', '坤卦', '震卦', '巽卦', '坎卦', '离卦', '艮卦', '兑卦',
            '屯卦', '蒙卦', '需卦', '讼卦', '师卦', '比卦', '小畜', '履卦',
            '泰卦', '否卦', '同人', '大有', '谦卦', '豫卦', '随卦', '蛊卦',
            # 概念
            '六爻', '八卦', '五行', '天干地支', '阴阳', '太极', '两仪', '四象',
            '相生', '相克', '生克', '制化', '纳甲', '世应', '用神', '原神',
            '忌神', '飞神', '伏神', '月建', '日建', '旬空', '破碎', '暗动',
            # 术语
            '卦辞', '爻辞', '象传', '彖传', '文言传', '系辞传', '说卦传',
            '序卦传', '杂卦传', '十翼', '易传', '周易', '易经', '连山', '归藏'
        ]
        
        for word in yixue_words:
            jieba.add_word(word)


class EntityExtractor:
    """实体抽取器"""
    
    def __init__(self):
        self.patterns = YixuePatterns()
        
        # 实体验证词典
        self.entity_dict = self._build_entity_dict()
        
        # 上下文窗口大小
        self.context_window = 50
    
    def _build_entity_dict(self) -> Dict[str, Set[str]]:
        """构建实体验证词典"""
        entity_dict = {
            'hexagram': {
                '乾', '坤', '震', '巽', '坎', '离', '艮', '兑',  # 八卦
                '屯', '蒙', '需', '讼', '师', '比', '小畜', '履', '泰', '否',  # 1-10
                '同人', '大有', '谦', '豫', '随', '蛊', '临', '观', '噬嗑', '贲',  # 11-20
                '剥', '复', '无妄', '大畜', '颐', '大过', '坎', '离', '咸', '恒',  # 21-30
                '遁', '大壮', '晋', '明夷', '家人', '睽', '蹇', '解', '损', '益',  # 31-40
                '夬', '姤', '萃', '升', '困', '井', '革', '鼎', '震', '艮',  # 41-50
                '渐', '归妹', '丰', '旅', '巽', '兑', '涣', '节', '中孚', '小过',  # 51-60
                '既济', '未济'  # 61-64
            },
            'wuxing': {'金', '木', '水', '火', '土'},
            'tiangan': {'甲', '乙', '丙', '丁', '戊', '己', '庚', '辛', '壬', '癸'},
            'dizhi': {'子', '丑', '寅', '卯', '辰', '巳', '午', '未', '申', '酉', '戌', '亥'},
            'dynasty': {
                '夏', '商', '周', '秦', '汉', '晋', '隋', '唐', '宋', '元', '明', '清',
                '春秋', '战国', '三国', '南北朝', '五代十国'
            }
        }
        return entity_dict
    
    def extract_entities(self, text: str) -> List[ExtractedEntity]:
        """抽取实体"""
        entities = []
        
        for entity_type, patterns in self.patterns.entity_patterns.items():
            for pattern in patterns:
                matches = re.finditer(pattern, text)
                
                for match in matches:
                    entity_name = match.group(1) if match.groups() else match.group(0)
                    
                    # 验证实体
                    if self._validate_entity(entity_name, entity_type):
                        confidence = self._calculate_entity_confidence(
                            entity_name, entity_type, text, match.span()
                        )
                        
                        context = self._extract_context(text, match.span())
                        
                        entity = ExtractedEntity(
                            name=entity_name,
                            entity_type=entity_type,
                            confidence=confidence,
                            positions=[match.span()],
                            context=context,
                            source_text=match.group(0)
                        )
                        
                        # 提取属性
                        entity.attributes = self._extract_entity_attributes(
                            entity_name, entity_type, context
                        )
                        
                        entities.append(entity)
        
        # 去重并合并
        entities = self._merge_duplicate_entities(entities)
        
        return entities
    
    def _validate_entity(self, entity_name: str, entity_type: str) -> bool:
        """验证实体有效性"""
        # 长度检查
        if len(entity_name) > 10 or len(entity_name) < 1:
            return False
        
        # 字典验证
        if entity_type in self.entity_dict:
            if entity_name not in self.entity_dict[entity_type]:
                # 部分匹配检查
                for valid_entity in self.entity_dict[entity_type]:
                    if entity_name in valid_entity or valid_entity in entity_name:
                        return True
                return False
        
        # 其他类型的基本验证
        if entity_type == 'person':
            # 人名通常2-4个字
            return 2 <= len(entity_name) <= 4
        
        if entity_type == 'book':
            # 书名通常不为空且有意义
            return len(entity_name) > 1
        
        return True
    
    def _calculate_entity_confidence(self, entity_name: str, entity_type: str,
                                   text: str, position: Tuple[int, int]) -> float:
        """计算实体置信度"""
        confidence = 0.5  # 基础置信度
        
        # 字典匹配加分
        if entity_type in self.entity_dict:
            if entity_name in self.entity_dict[entity_type]:
                confidence += 0.3
        
        # 上下文相关性
        context = self._extract_context(text, position)
        context_words = jieba.lcut(context)
        
        # 易学相关词汇加分
        yixue_words = {'易经', '周易', '卦', '爻', '五行', '八卦', '阴阳', '太极'}
        related_count = sum(1 for word in context_words if word in yixue_words)
        confidence += min(0.2, related_count * 0.05)
        
        # 重复出现加分
        entity_count = text.count(entity_name)
        if entity_count > 1:
            confidence += min(0.1, (entity_count - 1) * 0.02)
        
        return min(confidence, 1.0)
    
    def _extract_context(self, text: str, position: Tuple[int, int]) -> str:
        """提取上下文"""
        start_pos = max(0, position[0] - self.context_window)
        end_pos = min(len(text), position[1] + self.context_window)
        return text[start_pos:end_pos]
    
    def _extract_entity_attributes(self, entity_name: str, entity_type: str,
                                 context: str) -> Dict[str, Any]:
        """抽取实体属性"""
        attributes = {}
        
        if entity_type == 'hexagram':
            # 卦象属性
            if '上卦' in context or '外卦' in context:
                attributes['position'] = 'upper'
            if '下卦' in context or '内卦' in context:
                attributes['position'] = 'lower'
            
            # 五行属性
            for wuxing in ['金', '木', '水', '火', '土']:
                if wuxing in context:
                    attributes['wuxing'] = wuxing
                    break
        
        elif entity_type == 'line':
            # 爻位属性
            if '阳爻' in context or '九' in context:
                attributes['line_type'] = 'yang'
            elif '阴爻' in context or '六' in context:
                attributes['line_type'] = 'yin'
        
        elif entity_type == 'person':
            # 朝代属性
            for dynasty in self.entity_dict.get('dynasty', set()):
                if dynasty in context:
                    attributes['dynasty'] = dynasty
                    break
        
        return attributes
    
    def _merge_duplicate_entities(self, entities: List[ExtractedEntity]) -> List[ExtractedEntity]:
        """合并重复实体"""
        merged = {}
        
        for entity in entities:
            key = f"{entity.name}_{entity.entity_type}"
            
            if key in merged:
                # 合并位置
                merged[key].positions.extend(entity.positions)
                # 更新置信度（取最高值）
                merged[key].confidence = max(merged[key].confidence, entity.confidence)
                # 合并属性
                merged[key].attributes.update(entity.attributes)
            else:
                merged[key] = entity
        
        return list(merged.values())


class RelationExtractor:
    """关系抽取器"""
    
    def __init__(self):
        self.patterns = YixuePatterns()
        
        # 关系词典
        self.relation_indicators = {
            'belongs_to': ['属于', '是', '包含', '中的'],
            'transforms_to': ['变为', '化为', '转化为', '变成'],
            'generates': ['生', '产生', '生成', '生出'],
            'restrains': ['克', '制', '抑制', '克制'],
            'interprets': ['解释', '注解', '阐释', '说明'],
            'corresponds_to': ['对应', '相当于', '等同于', '即是']
        }
    
    def extract_relations(self, text: str, entities: List[ExtractedEntity]) -> List[ExtractedRelation]:
        """抽取关系"""
        relations = []
        
        # 1. 基于模式的关系抽取
        pattern_relations = self._extract_pattern_relations(text)
        relations.extend(pattern_relations)
        
        # 2. 基于实体的关系抽取
        entity_relations = self._extract_entity_relations(text, entities)
        relations.extend(entity_relations)
        
        # 3. 基于易学规则的关系抽取
        rule_relations = self._extract_rule_based_relations(entities)
        relations.extend(rule_relations)
        
        # 去重
        relations = self._deduplicate_relations(relations)
        
        return relations
    
    def _extract_pattern_relations(self, text: str) -> List[ExtractedRelation]:
        """基于模式抽取关系"""
        relations = []
        
        for relation_type, patterns in self.patterns.relation_patterns.items():
            for pattern in patterns:
                matches = re.finditer(pattern, text)
                
                for match in matches:
                    if len(match.groups()) >= 2:
                        source = match.group(1).strip()
                        target = match.group(2).strip()
                        
                        confidence = self._calculate_relation_confidence(
                            source, target, relation_type, text, match.span()
                        )
                        
                        if confidence > 0.3:
                            relation = ExtractedRelation(
                                source=source,
                                target=target,
                                relation_type=relation_type,
                                confidence=confidence,
                                evidence=match.group(0),
                                positions=[match.start()]
                            )
                            relations.append(relation)
        
        return relations
    
    def _extract_entity_relations(self, text: str, entities: List[ExtractedEntity]) -> List[ExtractedRelation]:
        """基于实体抽取关系"""
        relations = []
        entity_positions = [(e.name, e.positions) for e in entities]
        
        # 寻找实体间的关系
        for i, (entity1, pos1) in enumerate(entity_positions):
            for j, (entity2, pos2) in enumerate(entity_positions):
                if i >= j:
                    continue
                
                # 检查实体间的文本距离
                min_distance = float('inf')
                for p1 in pos1:
                    for p2 in pos2:
                        distance = min(abs(p1[0] - p2[1]), abs(p2[0] - p1[1]))
                        min_distance = min(min_distance, distance)
                
                if min_distance < 100:  # 实体距离阈值
                    # 提取中间文本寻找关系指示词
                    relation_text = self._extract_relation_context(text, entity1, entity2)
                    relation_type = self._identify_relation_type(relation_text)
                    
                    if relation_type:
                        confidence = self._calculate_entity_relation_confidence(
                            entity1, entity2, relation_type, relation_text
                        )
                        
                        if confidence > 0.2:
                            relation = ExtractedRelation(
                                source=entity1,
                                target=entity2,
                                relation_type=relation_type,
                                confidence=confidence,
                                evidence=relation_text
                            )
                            relations.append(relation)
        
        return relations
    
    def _extract_rule_based_relations(self, entities: List[ExtractedEntity]) -> List[ExtractedRelation]:
        """基于易学规则抽取关系"""
        relations = []
        
        # 五行生克关系
        wuxing_sheng = {'金': '水', '水': '木', '木': '火', '火': '土', '土': '金'}
        wuxing_ke = {'金': '木', '木': '土', '土': '水', '水': '火', '火': '金'}
        
        wuxing_entities = [e for e in entities if e.entity_type == 'wuxing']
        
        for i, entity1 in enumerate(wuxing_entities):
            for j, entity2 in enumerate(wuxing_entities):
                if i >= j:
                    continue
                
                if wuxing_sheng.get(entity1.name) == entity2.name:
                    relation = ExtractedRelation(
                        source=entity1.name,
                        target=entity2.name,
                        relation_type='generates',
                        confidence=0.9,
                        evidence=f"{entity1.name}生{entity2.name}（五行相生）"
                    )
                    relations.append(relation)
                
                elif wuxing_ke.get(entity1.name) == entity2.name:
                    relation = ExtractedRelation(
                        source=entity1.name,
                        target=entity2.name,
                        relation_type='restrains',
                        confidence=0.9,
                        evidence=f"{entity1.name}克{entity2.name}（五行相克）"
                    )
                    relations.append(relation)
        
        return relations
    
    def _extract_relation_context(self, text: str, entity1: str, entity2: str) -> str:
        """提取关系上下文"""
        # 简单实现：寻找两个实体间的文本
        entity1_pos = text.find(entity1)
        entity2_pos = text.find(entity2)
        
        if entity1_pos == -1 or entity2_pos == -1:
            return ""
        
        start = min(entity1_pos, entity2_pos)
        end = max(entity1_pos + len(entity1), entity2_pos + len(entity2))
        
        # 扩展上下文
        context_start = max(0, start - 20)
        context_end = min(len(text), end + 20)
        
        return text[context_start:context_end]
    
    def _identify_relation_type(self, relation_text: str) -> Optional[str]:
        """识别关系类型"""
        for relation_type, indicators in self.relation_indicators.items():
            for indicator in indicators:
                if indicator in relation_text:
                    return relation_type
        return None
    
    def _calculate_relation_confidence(self, source: str, target: str, 
                                     relation_type: str, text: str, 
                                     position: Tuple[int, int]) -> float:
        """计算关系置信度"""
        confidence = 0.4  # 基础置信度
        
        # 关系指示词强度
        if relation_type in ['generates', 'restrains']:
            confidence += 0.3  # 五行生克关系置信度较高
        
        # 实体有效性
        if len(source) <= 2 and len(target) <= 2:
            confidence += 0.2  # 简短实体通常更准确
        
        return min(confidence, 1.0)
    
    def _calculate_entity_relation_confidence(self, entity1: str, entity2: str,
                                            relation_type: str, evidence: str) -> float:
        """计算基于实体的关系置信度"""
        confidence = 0.3
        
        # 关系词出现加分
        if relation_type in self.relation_indicators:
            indicators = self.relation_indicators[relation_type]
            found_indicators = sum(1 for ind in indicators if ind in evidence)
            confidence += found_indicators * 0.1
        
        return min(confidence, 1.0)
    
    def _deduplicate_relations(self, relations: List[ExtractedRelation]) -> List[ExtractedRelation]:
        """关系去重"""
        unique_relations = {}
        
        for relation in relations:
            key = f"{relation.source}_{relation.target}_{relation.relation_type}"
            
            if key not in unique_relations or relation.confidence > unique_relations[key].confidence:
                unique_relations[key] = relation
        
        return list(unique_relations.values())


class ConceptExtractor:
    """概念抽取器"""
    
    def __init__(self):
        self.patterns = YixuePatterns()
        self.vectorizer = TfidfVectorizer(
            max_features=500,
            ngram_range=(1, 3),
            min_df=2
        )
        
        # 预定义概念类别
        self.concept_categories = {
            'philosophical': ['道', '德', '理', '气', '心', '性', '命', '运'],
            'technical': ['占卜', '预测', '算命', '风水', '择吉', '命理'],
            'symbolic': ['象征', '寓意', '比喻', '隐喻', '象', '意'],
            'temporal': ['时间', '时机', '节气', '历法', '纪年', '周期'],
            'spatial': ['方位', '方向', '空间', '位置', '地理', '环境']
        }
    
    def extract_concepts(self, text: str, entities: List[ExtractedEntity]) -> List[ExtractedConcept]:
        """抽取概念"""
        concepts = []
        
        # 1. 基于模式的概念抽取
        pattern_concepts = self._extract_pattern_concepts(text)
        concepts.extend(pattern_concepts)
        
        # 2. 基于关键词聚类的概念抽取
        cluster_concepts = self._extract_cluster_concepts(text)
        concepts.extend(cluster_concepts)
        
        # 3. 基于实体的概念推导
        entity_concepts = self._extract_entity_concepts(entities)
        concepts.extend(entity_concepts)
        
        # 去重和验证
        concepts = self._validate_and_merge_concepts(concepts)
        
        return concepts
    
    def _extract_pattern_concepts(self, text: str) -> List[ExtractedConcept]:
        """基于模式抽取概念"""
        concepts = []
        
        for category, patterns in self.patterns.concept_patterns.items():
            for pattern in patterns:
                matches = re.finditer(pattern, text)
                
                for match in matches:
                    concept_text = match.group(0)
                    
                    # 提取描述
                    description = self._extract_concept_description(text, match.span())
                    
                    # 计算置信度
                    confidence = self._calculate_concept_confidence(concept_text, category, text)
                    
                    if confidence > 0.3:
                        concept = ExtractedConcept(
                            concept=concept_text,
                            category=category,
                            description=description,
                            confidence=confidence
                        )
                        concepts.append(concept)
        
        return concepts
    
    def _extract_cluster_concepts(self, text: str) -> List[ExtractedConcept]:
        """基于聚类抽取概念"""
        concepts = []
        
        # 分句并提取关键词
        sentences = re.split(r'[。！？；]', text)
        if len(sentences) < 3:
            return concepts
        
        try:
            # TF-IDF向量化
            tfidf_matrix = self.vectorizer.fit_transform(sentences)
            
            # K-means聚类
            n_clusters = min(5, len(sentences) // 2)
            if n_clusters < 2:
                return concepts
            
            kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
            clusters = kmeans.fit_predict(tfidf_matrix)
            
            # 提取每个聚类的代表性词汇
            feature_names = self.vectorizer.get_feature_names_out()
            
            for cluster_id in range(n_clusters):
                cluster_center = kmeans.cluster_centers_[cluster_id]
                top_indices = cluster_center.argsort()[-5:][::-1]
                top_words = [feature_names[i] for i in top_indices if cluster_center[i] > 0.1]
                
                if top_words:
                    # 构建概念
                    concept_name = " ".join(top_words[:2])
                    category = self._classify_concept_category(top_words)
                    
                    concept = ExtractedConcept(
                        concept=concept_name,
                        category=category,
                        description=f"通过文本聚类发现的概念集合",
                        confidence=0.6,
                        keywords=top_words
                    )
                    concepts.append(concept)
        
        except Exception as e:
            logger.warning(f"概念聚类失败: {e}")
        
        return concepts
    
    def _extract_entity_concepts(self, entities: List[ExtractedEntity]) -> List[ExtractedConcept]:
        """基于实体推导概念"""
        concepts = []
        
        # 按类型分组实体
        entity_groups = defaultdict(list)
        for entity in entities:
            entity_groups[entity.entity_type].append(entity)
        
        # 为每个实体类型创建概念
        for entity_type, type_entities in entity_groups.items():
            if len(type_entities) >= 2:
                concept_name = f"{entity_type}_concept"
                entity_names = [e.name for e in type_entities]
                
                concept = ExtractedConcept(
                    concept=concept_name,
                    category='entity_based',
                    description=f"基于{entity_type}实体推导的概念",
                    confidence=0.5,
                    related_entities=entity_names
                )
                concepts.append(concept)
        
        return concepts
    
    def _extract_concept_description(self, text: str, position: Tuple[int, int]) -> str:
        """提取概念描述"""
        # 扩展上下文
        start = max(0, position[0] - 50)
        end = min(len(text), position[1] + 50)
        context = text[start:end]
        
        # 寻找描述性句子
        sentences = re.split(r'[。！？]', context)
        
        # 选择包含概念的句子作为描述
        concept_text = text[position[0]:position[1]]
        for sentence in sentences:
            if concept_text in sentence and len(sentence.strip()) > 10:
                return sentence.strip()
        
        return context[:50] + "..." if len(context) > 50 else context
    
    def _calculate_concept_confidence(self, concept: str, category: str, text: str) -> float:
        """计算概念置信度"""
        confidence = 0.4
        
        # 模式匹配加分
        if category in ['yinyang', 'wuxing', 'bagua']:
            confidence += 0.3
        
        # 出现频率加分
        count = text.count(concept)
        confidence += min(0.2, count * 0.05)
        
        # 长度合理性
        if 2 <= len(concept) <= 6:
            confidence += 0.1
        
        return min(confidence, 1.0)
    
    def _classify_concept_category(self, keywords: List[str]) -> str:
        """分类概念类别"""
        for category, category_words in self.concept_categories.items():
            overlap = set(keywords) & set(category_words)
            if overlap:
                return category
        
        return 'general'
    
    def _validate_and_merge_concepts(self, concepts: List[ExtractedConcept]) -> List[ExtractedConcept]:
        """验证和合并概念"""
        # 简单去重
        unique_concepts = {}
        
        for concept in concepts:
            key = f"{concept.concept}_{concept.category}"
            
            if key not in unique_concepts or concept.confidence > unique_concepts[key].confidence:
                unique_concepts[key] = concept
        
        # 过滤低置信度概念
        filtered_concepts = [c for c in unique_concepts.values() if c.confidence > 0.3]
        
        return filtered_concepts


class YixueKnowledgeExtractor:
    """易学知识抽取器主类"""
    
    def __init__(self):
        self.entity_extractor = EntityExtractor()
        self.relation_extractor = RelationExtractor()
        self.concept_extractor = ConceptExtractor()
        
        # 抽取统计
        self.stats = {
            'texts_processed': 0,
            'entities_extracted': 0,
            'relations_extracted': 0,
            'concepts_extracted': 0
        }
    
    def extract_knowledge(self, text: str, text_id: str = None) -> Dict[str, Any]:
        """完整知识抽取"""
        if not text or len(text.strip()) < 10:
            return {'entities': [], 'relations': [], 'concepts': [], 'stats': {}}
        
        logger.info(f"开始抽取知识，文本长度: {len(text)}")
        
        # 1. 实体抽取
        entities = self.entity_extractor.extract_entities(text)
        
        # 2. 关系抽取
        relations = self.relation_extractor.extract_relations(text, entities)
        
        # 3. 概念抽取
        concepts = self.concept_extractor.extract_concepts(text, entities)
        
        # 4. 更新统计
        self.stats['texts_processed'] += 1
        self.stats['entities_extracted'] += len(entities)
        self.stats['relations_extracted'] += len(relations)
        self.stats['concepts_extracted'] += len(concepts)
        
        # 5. 构建结果
        result = {
            'text_id': text_id or hashlib.md5(text[:100].encode()).hexdigest(),
            'text_length': len(text),
            'entities': [
                {
                    'name': e.name,
                    'type': e.entity_type,
                    'confidence': e.confidence,
                    'attributes': e.attributes,
                    'context': e.context[:50] + '...' if len(e.context) > 50 else e.context
                }
                for e in entities
            ],
            'relations': [
                {
                    'source': r.source,
                    'target': r.target,
                    'type': r.relation_type,
                    'confidence': r.confidence,
                    'evidence': r.evidence
                }
                for r in relations
            ],
            'concepts': [
                {
                    'concept': c.concept,
                    'category': c.category,
                    'confidence': c.confidence,
                    'description': c.description,
                    'keywords': c.keywords,
                    'related_entities': c.related_entities
                }
                for c in concepts
            ],
            'extraction_stats': {
                'entity_count': len(entities),
                'relation_count': len(relations),
                'concept_count': len(concepts)
            },
            'timestamp': datetime.now().isoformat()
        }
        
        logger.info(f"知识抽取完成: {len(entities)}个实体, {len(relations)}个关系, {len(concepts)}个概念")
        
        return result
    
    def batch_extract(self, texts: List[str], text_ids: List[str] = None) -> List[Dict[str, Any]]:
        """批量知识抽取"""
        if text_ids is None:
            text_ids = [None] * len(texts)
        
        results = []
        for text, text_id in zip(texts, text_ids):
            try:
                result = self.extract_knowledge(text, text_id)
                results.append(result)
            except Exception as e:
                logger.error(f"批量抽取失败 {text_id}: {e}")
                results.append({
                    'text_id': text_id,
                    'error': str(e),
                    'entities': [],
                    'relations': [],
                    'concepts': []
                })
        
        return results
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取抽取统计"""
        return {
            **self.stats,
            'avg_entities_per_text': self.stats['entities_extracted'] / max(1, self.stats['texts_processed']),
            'avg_relations_per_text': self.stats['relations_extracted'] / max(1, self.stats['texts_processed']),
            'avg_concepts_per_text': self.stats['concepts_extracted'] / max(1, self.stats['texts_processed'])
        }
    
    def save_results(self, results: List[Dict[str, Any]], output_path: str) -> None:
        """保存抽取结果"""
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                'extraction_results': results,
                'statistics': self.get_statistics(),
                'timestamp': datetime.now().isoformat()
            }, f, ensure_ascii=False, indent=2)
        
        logger.info(f"抽取结果已保存: {output_file}")


if __name__ == "__main__":
    # 测试易学知识抽取器
    def test_extractor():
        extractor = YixueKnowledgeExtractor()
        
        # 测试文本
        test_texts = [
            """
            乾卦是易经六十四卦之首，象征天、刚健、自强不息。乾为纯阳之卦，代表创造力和领导力。
            乾卦的卦辞是："乾，元亨利贞"。象传说："天行健，君子以自强不息"。
            乾卦属于金，对应西北方位。在五行中，金生水，因此乾卦与坎卦有相生关系。
            """,
            """
            五行相生：木生火，火生土，土生金，金生水，水生木。这是自然界的基本规律。
            五行相克：金克木，木克土，土克水，水克火，火克金。相生相克维持着自然的平衡。
            在易学理论中，五行学说是重要的基础理论之一。
            """,
            """
            孔子对易经的研究很深，他说"五十以学易，可以无大过矣"。
            朱熹是宋代著名的易学家，他注解了周易，对后世影响很大。
            《周易》、《易传》、《十翼》都是易学的重要典籍。
            """
        ]
        
        print("=== 易学知识抽取器测试 ===\n")
        
        # 批量抽取
        results = extractor.batch_extract(test_texts, ['text1', 'text2', 'text3'])
        
        # 显示结果
        for i, result in enumerate(results, 1):
            print(f"文本 {i} 抽取结果:")
            print(f"实体数量: {result['extraction_stats']['entity_count']}")
            print(f"关系数量: {result['extraction_stats']['relation_count']}")
            print(f"概念数量: {result['extraction_stats']['concept_count']}")
            
            print("\n实体:")
            for entity in result['entities']:
                print(f"  - {entity['name']} ({entity['type']}) 置信度: {entity['confidence']:.3f}")
            
            print("\n关系:")
            for relation in result['relations']:
                print(f"  - {relation['source']} {relation['type']} {relation['target']} 置信度: {relation['confidence']:.3f}")
            
            print("\n概念:")
            for concept in result['concepts']:
                print(f"  - {concept['concept']} ({concept['category']}) 置信度: {concept['confidence']:.3f}")
            
            print("-" * 60)
        
        # 显示统计信息
        print("总体统计:")
        stats = extractor.get_statistics()
        for key, value in stats.items():
            print(f"  {key}: {value}")
        
        # 保存结果
        extractor.save_results(results, "./knowledge_extraction_results.json")
        print("\n结果已保存到 knowledge_extraction_results.json")
    
    test_extractor()