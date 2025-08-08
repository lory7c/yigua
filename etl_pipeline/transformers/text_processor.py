"""
文本处理器 - 专门处理易学文献的文本清洗和结构化
包含去除乱码、标准化、实体识别等功能
"""

import re
import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, field
from datetime import datetime
import unicodedata
from collections import defaultdict, Counter
import time

# 易学专业术语和实体
@dataclass
class YijingEntity:
    """易学实体"""
    text: str
    entity_type: str  # 'hexagram', 'yao', 'element', 'star', 'direction', 'time'
    confidence: float
    start_pos: int
    end_pos: int
    context: str = ""
    attributes: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProcessedText:
    """处理后的文本结构"""
    original_text: str
    cleaned_text: str
    structured_content: Dict[str, Any]
    entities: List[YijingEntity]
    categories: List[str]
    quality_score: float
    processing_time: float
    metadata: Dict[str, Any] = field(default_factory=dict)


class YijingTextProcessor:
    """易学文本专业处理器"""
    
    def __init__(self, config=None):
        self.logger = logging.getLogger(__name__)
        self.config = config
        
        # 初始化易学知识库
        self._initialize_knowledge_base()
        
        # 文本清洗规则
        self._initialize_cleaning_rules()
        
        # 实体识别模式
        self._initialize_entity_patterns()
        
        # 统计信息
        self.stats = {
            'processed_texts': 0,
            'entities_found': 0,
            'categories_assigned': 0,
            'processing_time_total': 0
        }
    
    def _initialize_knowledge_base(self):
        """初始化易学知识库"""
        
        # 64卦名称
        self.hexagram_names = {
            '乾', '坤', '屯', '蒙', '需', '讼', '师', '比',
            '小畜', '履', '泰', '否', '同人', '大有', '谦', '豫',
            '随', '蛊', '临', '观', '噬嗑', '贲', '剥', '复',
            '无妄', '大畜', '颐', '大过', '坎', '离', '咸', '恒',
            '遁', '大壮', '晋', '明夷', '家人', '睽', '蹇', '解',
            '损', '益', '夬', '姤', '萃', '升', '困', '井',
            '革', '鼎', '震', '艮', '渐', '归妹', '丰', '旅',
            '巽', '兑', '涣', '节', '中孚', '小过', '既济', '未济'
        }
        
        # 八宫卦名
        self.palace_names = {
            '乾宫': ['乾', '姤', '遁', '否', '观', '剥', '晋', '大有'],
            '坤宫': ['坤', '复', '临', '泰', '大壮', '夬', '需', '比'],
            '震宫': ['震', '豫', '解', '恒', '升', '井', '大过', '随'],
            '巽宫': ['巽', '小畜', '家人', '益', '无妄', '噬嗑', '颐', '蛊'],
            '坎宫': ['坎', '节', '屯', '既济', '革', '丰', '明夷', '师'],
            '离宫': ['离', '旅', '鼎', '未济', '蒙', '涣', '讼', '同人'],
            '艮宫': ['艮', '谦', '蹇', '渐', '小过', '旅', '咸', '损'],
            '兑宫': ['兑', '困', '萃', '咸', '蹇', '谦', '履', '小畜']
        }
        
        # 爻位名称
        self.yao_positions = {
            '初六', '初九', '六二', '九二', '六三', '九三',
            '六四', '九四', '六五', '九五', '上六', '上九'
        }
        
        # 五行
        self.elements = {'金', '木', '水', '火', '土'}
        
        # 十天干
        self.heavenly_stems = {'甲', '乙', '丙', '丁', '戊', '己', '庚', '辛', '壬', '癸'}
        
        # 十二地支
        self.earthly_branches = {
            '子', '丑', '寅', '卯', '辰', '巳', 
            '午', '未', '申', '酉', '戌', '亥'
        }
        
        # 八神（六爻中的六神）
        self.six_spirits = {'青龙', '朱雀', '勾陈', '螣蛇', '白虎', '玄武'}
        
        # 方位
        self.directions = {'东', '南', '西', '北', '东南', '西南', '西北', '东北', '中央'}
        
        # 时辰
        self.time_periods = {
            '子时', '丑时', '寅时', '卯时', '辰时', '巳时',
            '午时', '未时', '申时', '酉时', '戌时', '亥时'
        }
        
        # 卦象描述词汇
        self.hexagram_attributes = {
            '吉', '凶', '悔', '吝', '无咎', '有悔', '元吉', '大吉', 
            '中吉', '小吉', '大凶', '中凶', '小凶'
        }
        
        # 专业术语
        self.professional_terms = {
            '世爻', '应爻', '用神', '原神', '忌神', '仇神', '动爻', '变爻',
            '月建', '日辰', '空亡', '墓库', '长生', '帝旺', '死绝',
            '进神', '退神', '反吟', '伏吟', '游魂', '归魂',
            '飞神', '伏神', '出现', '暗动', '化回头', '化进神', '化退神'
        }
        
        self.logger.info("易学知识库初始化完成")
    
    def _initialize_cleaning_rules(self):
        """初始化文本清洗规则"""
        
        # 乱码字符模式
        self.garbage_patterns = [
            r'[^\u4e00-\u9fff\u3400-\u4dbf\w\s\.,;:!?\-\(\)\[\]{}""''《》。，、；：！？（）【】]',  # 非中文和基本标点
            r'(\n\s*){3,}',  # 多余空行
            r'[ \t]{2,}',    # 多余空格
            r'[■□●○◎△▲※◆◇]',  # 特殊符号
            r'[①②③④⑤⑥⑦⑧⑨⑩]',  # 圆圈数字
        ]
        
        # 页眉页脚模式
        self.header_footer_patterns = [
            r'第\s*\d+\s*页',
            r'Page\s*\d+',
            r'^\d+\s*$',  # 单独的页码
            r'版权所有.*',
            r'本书由.*制作',
            r'更多资源.*',
            r'微信.*群',
            r'QQ.*群',
            r'http[s]?://\S+',
            r'www\.\S+',
        ]
        
        # 标准化替换规则
        self.normalization_rules = [
            (r'（', '('),
            (r'）', ')'),
            (r'，', ','),
            (r'。', '.'),
            (r'？', '?'),
            (r'！', '!'),
            (r'：', ':'),
            (r'；', ';'),
            (r'［', '['),
            (r'］', ']'),
            (r'「', '"'),
            (r'」', '"'),
            (r'【', '['),
            (r'】', ']'),
        ]
        
        self.logger.info("文本清洗规则初始化完成")
    
    def _initialize_entity_patterns(self):
        """初始化实体识别模式"""
        
        # 卦名模式
        hexagram_pattern = '|'.join(self.hexagram_names)
        self.entity_patterns = {
            'hexagram': [
                rf'({hexagram_pattern})卦',
                rf'({hexagram_pattern})',
                rf'第({hexagram_pattern})',
            ],
            
            'yao': [
                rf'(初[六九]|[六九][二三四五]|上[六九])',
                rf'爻[曰云]?：?(.{{0,100}})',
                rf'([初二三四五上])爻',
            ],
            
            'element': [
                rf'({"|".join(self.elements)})[行元]',
                rf'五行.*?({"|".join(self.elements)})',
            ],
            
            'time_stem_branch': [
                rf'({"|".join(self.heavenly_stems)})({"|".join(self.earthly_branches)})',
                rf'({"|".join(self.time_periods)})',
            ],
            
            'direction': [
                rf'({"|".join(self.directions)})方',
                rf'朝({"|".join(self.directions)})',
            ],
            
            'six_spirits': [
                rf'({"|".join(self.six_spirits)})',
                rf'临({"|".join(self.six_spirits)})',
            ],
            
            'professional_term': [
                rf'({"|".join(self.professional_terms)})',
            ],
            
            'hexagram_attribute': [
                rf'({"|".join(self.hexagram_attributes)})',
                rf'得({"|".join(self.hexagram_attributes)})',
            ]
        }
        
        # 编译正则表达式以提高性能
        self.compiled_patterns = {}
        for entity_type, patterns in self.entity_patterns.items():
            self.compiled_patterns[entity_type] = [
                re.compile(pattern, re.IGNORECASE) for pattern in patterns
            ]
        
        self.logger.info(f"实体识别模式初始化完成，共 {len(self.entity_patterns)} 类实体")
    
    def process_text(self, raw_text: str, metadata: Dict[str, Any] = None) -> ProcessedText:
        """处理单个文本"""
        
        start_time = time.time()
        
        try:
            # 1. 文本清洗
            cleaned_text = self.clean_text(raw_text)
            
            # 2. 实体识别
            entities = self.extract_entities(cleaned_text)
            
            # 3. 内容分类
            categories = self.categorize_content(cleaned_text, entities)
            
            # 4. 结构化处理
            structured_content = self.structure_content(cleaned_text, entities, categories)
            
            # 5. 质量评估
            quality_score = self.assess_text_quality(cleaned_text, entities)
            
            processing_time = time.time() - start_time
            
            # 更新统计
            self.stats['processed_texts'] += 1
            self.stats['entities_found'] += len(entities)
            self.stats['categories_assigned'] += len(categories)
            self.stats['processing_time_total'] += processing_time
            
            result = ProcessedText(
                original_text=raw_text,
                cleaned_text=cleaned_text,
                structured_content=structured_content,
                entities=entities,
                categories=categories,
                quality_score=quality_score,
                processing_time=processing_time,
                metadata={
                    'original_length': len(raw_text),
                    'cleaned_length': len(cleaned_text),
                    'compression_ratio': len(cleaned_text) / max(len(raw_text), 1),
                    'entities_count': len(entities),
                    'categories_count': len(categories),
                    **(metadata or {})
                }
            )
            
            self.logger.debug(f"文本处理完成: {len(entities)} 个实体, {len(categories)} 个分类, "
                            f"质量分数: {quality_score:.2f}, 耗时: {processing_time:.3f}s")
            
            return result
            
        except Exception as e:
            self.logger.error(f"文本处理失败: {e}")
            return ProcessedText(
                original_text=raw_text,
                cleaned_text="",
                structured_content={},
                entities=[],
                categories=[],
                quality_score=0.0,
                processing_time=time.time() - start_time,
                metadata={'error': str(e)}
            )
    
    def clean_text(self, text: str) -> str:
        """文本清洗"""
        
        if not text:
            return ""
        
        cleaned = text
        
        # 1. Unicode标准化
        cleaned = unicodedata.normalize('NFKC', cleaned)
        
        # 2. 移除页眉页脚
        for pattern in self.header_footer_patterns:
            cleaned = re.sub(pattern, '', cleaned, flags=re.MULTILINE)
        
        # 3. 移除乱码
        for pattern in self.garbage_patterns:
            if pattern == r'(\n\s*){3,}':
                cleaned = re.sub(pattern, '\n\n', cleaned)
            elif pattern == r'[ \t]{2,}':
                cleaned = re.sub(pattern, ' ', cleaned)
            else:
                cleaned = re.sub(pattern, '', cleaned)
        
        # 4. 标点符号标准化
        for old, new in self.normalization_rules:
            cleaned = cleaned.replace(old, new)
        
        # 5. 清理多余空白
        cleaned = re.sub(r'\n\s*\n', '\n\n', cleaned)  # 多余换行
        cleaned = re.sub(r'[ \t]+', ' ', cleaned)       # 多余空格
        
        # 6. 首尾空白清理
        cleaned = cleaned.strip()
        
        # 7. 特殊清理：移除OCR常见错误
        ocr_error_patterns = [
            r'[lI1]{3,}',      # 连续的1或l或I
            r'[oO0]{3,}',      # 连续的0或o或O
            r'[。]{2,}',        # 连续句号
            r'[，]{2,}',        # 连续逗号
        ]
        
        for pattern in ocr_error_patterns:
            cleaned = re.sub(pattern, '', cleaned)
        
        return cleaned
    
    def extract_entities(self, text: str) -> List[YijingEntity]:
        """提取易学实体"""
        
        entities = []
        
        for entity_type, patterns in self.compiled_patterns.items():
            for pattern in patterns:
                matches = pattern.finditer(text)
                
                for match in matches:
                    entity_text = match.group(1) if match.groups() else match.group(0)
                    start_pos = match.start()
                    end_pos = match.end()
                    
                    # 提取上下文
                    context_start = max(0, start_pos - 50)
                    context_end = min(len(text), end_pos + 50)
                    context = text[context_start:context_end]
                    
                    # 计算置信度
                    confidence = self._calculate_entity_confidence(
                        entity_text, entity_type, context
                    )
                    
                    # 提取属性
                    attributes = self._extract_entity_attributes(
                        entity_text, entity_type, context
                    )
                    
                    entity = YijingEntity(
                        text=entity_text,
                        entity_type=entity_type,
                        confidence=confidence,
                        start_pos=start_pos,
                        end_pos=end_pos,
                        context=context,
                        attributes=attributes
                    )
                    
                    entities.append(entity)
        
        # 去重和合并重叠实体
        entities = self._deduplicate_entities(entities)
        
        # 按位置排序
        entities.sort(key=lambda e: e.start_pos)
        
        return entities
    
    def _calculate_entity_confidence(self, entity_text: str, entity_type: str, context: str) -> float:
        """计算实体识别置信度"""
        
        base_confidence = 0.7
        
        # 基于实体类型的基础置信度
        type_confidence = {
            'hexagram': 0.9,
            'yao': 0.85,
            'professional_term': 0.8,
            'element': 0.75,
            'six_spirits': 0.8,
            'time_stem_branch': 0.7,
            'direction': 0.7,
            'hexagram_attribute': 0.6
        }.get(entity_type, base_confidence)
        
        # 上下文相关性加成
        context_bonus = 0.0
        relevant_keywords = {
            'hexagram': ['卦', '占', '筮', '易'],
            'yao': ['爻', '动', '变', '之'],
            'professional_term': ['用神', '世应', '六亲'],
            'element': ['五行', '生克', '旺相'],
        }
        
        if entity_type in relevant_keywords:
            for keyword in relevant_keywords[entity_type]:
                if keyword in context:
                    context_bonus += 0.05
        
        # 实体长度因子
        length_factor = min(1.0, len(entity_text) / 10)
        
        final_confidence = min(1.0, type_confidence + context_bonus + length_factor * 0.1)
        
        return final_confidence
    
    def _extract_entity_attributes(self, entity_text: str, entity_type: str, context: str) -> Dict[str, Any]:
        """提取实体属性"""
        
        attributes = {}
        
        if entity_type == 'hexagram':
            # 查找卦的宫位
            for palace, hexagrams in self.palace_names.items():
                if entity_text in hexagrams:
                    attributes['palace'] = palace
                    attributes['position_in_palace'] = hexagrams.index(entity_text)
                    break
        
        elif entity_type == 'yao':
            # 分析爻的阴阳和位置
            if '六' in entity_text:
                attributes['yin_yang'] = '阴'
                attributes['nature'] = '柔'
            elif '九' in entity_text:
                attributes['yin_yang'] = '阳'
                attributes['nature'] = '刚'
            
            # 提取位置
            position_map = {'初': 1, '二': 2, '三': 3, '四': 4, '五': 5, '上': 6}
            for pos_char, pos_num in position_map.items():
                if pos_char in entity_text:
                    attributes['position'] = pos_num
                    break
        
        elif entity_type == 'element':
            # 五行生克关系
            element_relations = {
                '金': {'generates': '水', 'destroys': '木', 'generated_by': '土', 'destroyed_by': '火'},
                '木': {'generates': '火', 'destroys': '土', 'generated_by': '水', 'destroyed_by': '金'},
                '水': {'generates': '木', 'destroys': '火', 'generated_by': '金', 'destroyed_by': '土'},
                '火': {'generates': '土', 'destroys': '金', 'generated_by': '木', 'destroyed_by': '水'},
                '土': {'generates': '金', 'destroys': '水', 'generated_by': '火', 'destroyed_by': '木'}
            }
            
            if entity_text in element_relations:
                attributes.update(element_relations[entity_text])
        
        elif entity_type == 'time_stem_branch':
            # 天干地支属性
            if len(entity_text) == 2:
                stem, branch = entity_text[0], entity_text[1]
                if stem in self.heavenly_stems:
                    attributes['heavenly_stem'] = stem
                if branch in self.earthly_branches:
                    attributes['earthly_branch'] = branch
        
        return attributes
    
    def _deduplicate_entities(self, entities: List[YijingEntity]) -> List[YijingEntity]:
        """去重和合并重叠实体"""
        
        if not entities:
            return entities
        
        # 按位置排序
        entities.sort(key=lambda e: (e.start_pos, e.end_pos))
        
        deduplicated = []
        
        for entity in entities:
            # 检查是否与已有实体重叠
            should_add = True
            
            for existing in deduplicated:
                # 检查重叠
                if (entity.start_pos < existing.end_pos and 
                    entity.end_pos > existing.start_pos):
                    
                    # 如果置信度更高，替换
                    if entity.confidence > existing.confidence:
                        deduplicated.remove(existing)
                        deduplicated.append(entity)
                        should_add = False
                        break
                    else:
                        should_add = False
                        break
                        
                # 检查完全重复
                if (entity.text == existing.text and 
                    entity.entity_type == existing.entity_type):
                    should_add = False
                    break
            
            if should_add:
                deduplicated.append(entity)
        
        return deduplicated
    
    def categorize_content(self, text: str, entities: List[YijingEntity]) -> List[str]:
        """内容分类"""
        
        categories = []
        entity_types = [e.entity_type for e in entities]
        entity_texts = [e.text for e in entities]
        
        # 基于实体类型的分类
        if 'hexagram' in entity_types:
            categories.append('hexagram')
        
        if 'yao' in entity_types:
            categories.append('yao')
        
        if 'professional_term' in entity_types:
            categories.append('divination')
        
        # 基于关键词的分类
        annotation_keywords = ['注', '解', '释', '疏', '传', '说', '论', '辨']
        if any(keyword in text for keyword in annotation_keywords):
            categories.append('annotation')
        
        judgment_keywords = ['断语', '口诀', '诀', '法', '应', '验', '准']
        if any(keyword in text for keyword in judgment_keywords):
            categories.append('judgment')
        
        liuyao_keywords = ['六爻', '世爻', '应爻', '用神', '原神', '忌神']
        if any(keyword in text for keyword in liuyao_keywords):
            categories.append('liuyao')
        
        qimen_keywords = ['奇门', '遁甲', '九宫', '八门', '天盘', '地盘']
        if any(keyword in text for keyword in qimen_keywords):
            categories.append('qimen')
        
        ziwei_keywords = ['紫微', '斗数', '命宫', '财帛宫', '夫妻宫']
        if any(keyword in text for keyword in ziwei_keywords):
            categories.append('ziwei')
        
        # 如果没有明确分类，归为其他
        if not categories:
            categories.append('other')
        
        return list(set(categories))  # 去重
    
    def structure_content(self, text: str, entities: List[YijingEntity], categories: List[str]) -> Dict[str, Any]:
        """结构化内容"""
        
        structure = {
            'text_length': len(text),
            'entities_summary': self._summarize_entities(entities),
            'categories': categories,
            'sections': self._identify_sections(text),
            'key_concepts': self._extract_key_concepts(text, entities),
            'relationships': self._extract_relationships(entities),
            'quality_indicators': self._extract_quality_indicators(text)
        }
        
        # 特定类别的结构化
        if 'hexagram' in categories:
            structure['hexagram_analysis'] = self._analyze_hexagrams(text, entities)
        
        if 'yao' in categories:
            structure['yao_analysis'] = self._analyze_yaos(text, entities)
        
        if 'divination' in categories:
            structure['divination_elements'] = self._extract_divination_elements(text, entities)
        
        return structure
    
    def _summarize_entities(self, entities: List[YijingEntity]) -> Dict[str, Any]:
        """实体摘要"""
        
        summary = defaultdict(list)
        
        for entity in entities:
            summary[entity.entity_type].append({
                'text': entity.text,
                'confidence': entity.confidence,
                'attributes': entity.attributes
            })
        
        return dict(summary)
    
    def _identify_sections(self, text: str) -> List[Dict[str, Any]]:
        """识别文本章节结构"""
        
        sections = []
        
        # 常见的章节标记模式
        section_patterns = [
            r'第[一二三四五六七八九十\d]+章',
            r'第[一二三四五六七八九十\d]+节',
            r'[一二三四五六七八九十]、',
            r'\d+\.',
            r'[\d]+、',
        ]
        
        current_pos = 0
        
        for pattern in section_patterns:
            matches = re.finditer(pattern, text)
            
            for match in matches:
                sections.append({
                    'title': match.group(0),
                    'start_pos': match.start(),
                    'end_pos': match.end(),
                    'content_start': match.end()
                })
        
        # 按位置排序
        sections.sort(key=lambda s: s['start_pos'])
        
        # 计算每个章节的内容长度
        for i, section in enumerate(sections):
            if i < len(sections) - 1:
                section['content_length'] = sections[i + 1]['start_pos'] - section['content_start']
            else:
                section['content_length'] = len(text) - section['content_start']
        
        return sections
    
    def _extract_key_concepts(self, text: str, entities: List[YijingEntity]) -> List[str]:
        """提取关键概念"""
        
        key_concepts = set()
        
        # 从实体中提取
        for entity in entities:
            if entity.confidence > 0.8:
                key_concepts.add(entity.text)
        
        # 基于频率的关键词提取
        words = re.findall(r'[\u4e00-\u9fff]{2,}', text)
        word_freq = Counter(words)
        
        # 提取高频专业术语
        for word, freq in word_freq.most_common(20):
            if freq > 2 and len(word) >= 2:
                # 检查是否为专业术语
                if (word in self.professional_terms or
                    word in self.hexagram_names or
                    any(word in terms for terms in [self.elements, self.six_spirits])):
                    key_concepts.add(word)
        
        return list(key_concepts)
    
    def _extract_relationships(self, entities: List[YijingEntity]) -> List[Dict[str, Any]]:
        """提取实体间关系"""
        
        relationships = []
        
        # 分析相邻实体的关系
        for i in range(len(entities) - 1):
            entity1 = entities[i]
            entity2 = entities[i + 1]
            
            # 位置距离
            distance = entity2.start_pos - entity1.end_pos
            
            if distance < 50:  # 50字符以内认为可能存在关系
                relationship_type = self._determine_relationship_type(entity1, entity2)
                
                if relationship_type:
                    relationships.append({
                        'entity1': entity1.text,
                        'entity2': entity2.text,
                        'relationship_type': relationship_type,
                        'confidence': min(entity1.confidence, entity2.confidence),
                        'distance': distance
                    })
        
        return relationships
    
    def _determine_relationship_type(self, entity1: YijingEntity, entity2: YijingEntity) -> Optional[str]:
        """确定两个实体之间的关系类型"""
        
        # 卦与爻的关系
        if entity1.entity_type == 'hexagram' and entity2.entity_type == 'yao':
            return 'hexagram_yao'
        
        # 爻与属性的关系
        if entity1.entity_type == 'yao' and entity2.entity_type == 'hexagram_attribute':
            return 'yao_attribute'
        
        # 五行关系
        if entity1.entity_type == 'element' and entity2.entity_type == 'element':
            return 'element_relationship'
        
        # 时间关系
        if entity1.entity_type == 'time_stem_branch' and entity2.entity_type in ['hexagram', 'yao']:
            return 'time_association'
        
        return None
    
    def _extract_quality_indicators(self, text: str) -> Dict[str, Any]:
        """提取文本质量指标"""
        
        indicators = {}
        
        # 完整性指标
        indicators['has_title'] = bool(re.search(r'第.*[章节]|[一二三四五六七八九十]、', text))
        indicators['has_conclusion'] = bool(re.search(r'[总结论]|综上|因此|总之', text))
        
        # 专业性指标
        professional_term_count = sum(1 for term in self.professional_terms if term in text)
        indicators['professional_density'] = professional_term_count / max(len(text.split()), 1)
        
        # 结构性指标
        indicators['paragraph_count'] = len(text.split('\n\n'))
        indicators['average_paragraph_length'] = len(text) / max(indicators['paragraph_count'], 1)
        
        # 可读性指标
        sentence_count = len(re.findall(r'[。！？]', text))
        indicators['sentence_count'] = sentence_count
        indicators['average_sentence_length'] = len(text) / max(sentence_count, 1)
        
        return indicators
    
    def _analyze_hexagrams(self, text: str, entities: List[YijingEntity]) -> Dict[str, Any]:
        """分析卦象内容"""
        
        hexagram_entities = [e for e in entities if e.entity_type == 'hexagram']
        
        analysis = {
            'hexagram_count': len(hexagram_entities),
            'hexagrams': [],
            'palace_distribution': defaultdict(int)
        }
        
        for entity in hexagram_entities:
            hexagram_info = {
                'name': entity.text,
                'confidence': entity.confidence,
                'context': entity.context[:100],
                'attributes': entity.attributes
            }
            
            # 统计宫位分布
            if 'palace' in entity.attributes:
                analysis['palace_distribution'][entity.attributes['palace']] += 1
            
            analysis['hexagrams'].append(hexagram_info)
        
        return analysis
    
    def _analyze_yaos(self, text: str, entities: List[YijingEntity]) -> Dict[str, Any]:
        """分析爻象内容"""
        
        yao_entities = [e for e in entities if e.entity_type == 'yao']
        
        analysis = {
            'yao_count': len(yao_entities),
            'yaos': [],
            'position_distribution': defaultdict(int),
            'yin_yang_distribution': defaultdict(int)
        }
        
        for entity in yao_entities:
            yao_info = {
                'text': entity.text,
                'confidence': entity.confidence,
                'context': entity.context[:100],
                'attributes': entity.attributes
            }
            
            # 统计位置分布
            if 'position' in entity.attributes:
                analysis['position_distribution'][entity.attributes['position']] += 1
            
            # 统计阴阳分布
            if 'yin_yang' in entity.attributes:
                analysis['yin_yang_distribution'][entity.attributes['yin_yang']] += 1
            
            analysis['yaos'].append(yao_info)
        
        return analysis
    
    def _extract_divination_elements(self, text: str, entities: List[YijingEntity]) -> Dict[str, Any]:
        """提取占卜要素"""
        
        elements = {
            'method_mentioned': [],
            'time_factors': [],
            'question_types': [],
            'judgment_keywords': []
        }
        
        # 占卜方法
        divination_methods = ['六爻', '梅花易数', '奇门遁甲', '大六壬', '太乙神数']
        for method in divination_methods:
            if method in text:
                elements['method_mentioned'].append(method)
        
        # 时间因素
        time_entities = [e for e in entities if e.entity_type == 'time_stem_branch']
        elements['time_factors'] = [e.text for e in time_entities]
        
        # 问题类型关键词
        question_keywords = ['求财', '求官', '婚姻', '疾病', '出行', '失物', '天气']
        for keyword in question_keywords:
            if keyword in text:
                elements['question_types'].append(keyword)
        
        # 判断关键词
        judgment_keywords = ['吉', '凶', '宜', '忌', '应', '验', '成', '败']
        for keyword in judgment_keywords:
            if keyword in text:
                elements['judgment_keywords'].append(keyword)
        
        return elements
    
    def assess_text_quality(self, text: str, entities: List[YijingEntity]) -> float:
        """评估文本质量"""
        
        if not text:
            return 0.0
        
        score = 0.0
        factors = []
        
        # 1. 长度因子 (20%)
        length_score = min(1.0, len(text) / 1000)  # 1000字符为满分
        factors.append(('length', length_score, 0.2))
        
        # 2. 实体密度因子 (25%)
        entity_density = len(entities) / max(len(text.split()), 1)
        entity_score = min(1.0, entity_density * 100)  # 调整比例
        factors.append(('entity_density', entity_score, 0.25))
        
        # 3. 实体质量因子 (20%)
        if entities:
            avg_entity_confidence = sum(e.confidence for e in entities) / len(entities)
            factors.append(('entity_quality', avg_entity_confidence, 0.2))
        else:
            factors.append(('entity_quality', 0.0, 0.2))
        
        # 4. 专业术语因子 (15%)
        professional_terms_found = sum(1 for term in self.professional_terms if term in text)
        professional_score = min(1.0, professional_terms_found / 10)
        factors.append(('professional_terms', professional_score, 0.15))
        
        # 5. 结构完整性因子 (10%)
        structure_score = 0.0
        if re.search(r'第.*[章节]|[一二三四五六七八九十]、', text):
            structure_score += 0.3
        if re.search(r'[。！？]', text):
            structure_score += 0.4
        if len(text.split('\n\n')) > 1:
            structure_score += 0.3
        factors.append(('structure', structure_score, 0.1))
        
        # 6. 可读性因子 (10%)
        sentence_count = len(re.findall(r'[。！？]', text))
        if sentence_count > 0:
            avg_sentence_length = len(text) / sentence_count
            readability_score = 1.0 if 10 <= avg_sentence_length <= 100 else 0.5
        else:
            readability_score = 0.2
        factors.append(('readability', readability_score, 0.1))
        
        # 计算加权总分
        for factor_name, factor_score, weight in factors:
            score += factor_score * weight
        
        return min(1.0, max(0.0, score))
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """获取处理统计信息"""
        
        avg_processing_time = (self.stats['processing_time_total'] / 
                             max(self.stats['processed_texts'], 1))
        
        return {
            'processed_texts': self.stats['processed_texts'],
            'entities_found': self.stats['entities_found'],
            'categories_assigned': self.stats['categories_assigned'],
            'average_processing_time': avg_processing_time,
            'average_entities_per_text': (self.stats['entities_found'] / 
                                        max(self.stats['processed_texts'], 1)),
            'total_processing_time': self.stats['processing_time_total']
        }
    
    def reset_stats(self):
        """重置统计信息"""
        self.stats = {
            'processed_texts': 0,
            'entities_found': 0,
            'categories_assigned': 0,
            'processing_time_total': 0
        }


class BatchTextProcessor:
    """批量文本处理器"""
    
    def __init__(self, config=None):
        self.processor = YijingTextProcessor(config)
        self.logger = logging.getLogger(__name__)
    
    def process_batch(self, text_extractions: List[Any]) -> List[ProcessedText]:
        """批量处理文本"""
        
        self.logger.info(f"开始批量处理 {len(text_extractions)} 个文本")
        start_time = time.time()
        
        results = []
        
        for i, extraction in enumerate(text_extractions):
            try:
                # 获取原始文本
                raw_text = extraction.raw_text if hasattr(extraction, 'raw_text') else str(extraction)
                
                # 准备元数据
                metadata = {
                    'source_file': getattr(extraction, 'source_doc', {}).get('file_name', f'item_{i}'),
                    'extraction_method': getattr(extraction, 'extraction_method', 'unknown'),
                    'extraction_confidence': getattr(extraction, 'confidence_score', 0.0),
                    'page_count': getattr(extraction, 'page_count', 0),
                }
                
                # 处理文本
                processed = self.processor.process_text(raw_text, metadata)
                results.append(processed)
                
                # 进度报告
                if (i + 1) % 10 == 0:
                    elapsed = time.time() - start_time
                    avg_time = elapsed / (i + 1)
                    estimated_remaining = avg_time * (len(text_extractions) - i - 1)
                    
                    self.logger.info(f"处理进度: {i+1}/{len(text_extractions)}, "
                                   f"预计剩余时间: {estimated_remaining/60:.1f}分钟")
                
            except Exception as e:
                self.logger.error(f"处理第 {i} 个文本时失败: {e}")
                # 创建错误结果
                error_result = ProcessedText(
                    original_text="",
                    cleaned_text="",
                    structured_content={},
                    entities=[],
                    categories=[],
                    quality_score=0.0,
                    processing_time=0.0,
                    metadata={'error': str(e), 'index': i}
                )
                results.append(error_result)
        
        total_time = time.time() - start_time
        successful_count = sum(1 for r in results if r.quality_score > 0)
        
        self.logger.info(f"批量处理完成: {successful_count}/{len(text_extractions)} 成功, "
                        f"总耗时: {total_time/60:.2f}分钟, "
                        f"平均速度: {len(text_extractions)/total_time:.2f}文本/秒")
        
        return results
    
    def save_results(self, results: List[ProcessedText], output_path: Path):
        """保存处理结果"""
        
        # 准备保存数据
        save_data = []
        
        for result in results:
            data = {
                'original_text': result.original_text,
                'cleaned_text': result.cleaned_text,
                'structured_content': result.structured_content,
                'entities': [
                    {
                        'text': e.text,
                        'type': e.entity_type,
                        'confidence': e.confidence,
                        'start_pos': e.start_pos,
                        'end_pos': e.end_pos,
                        'context': e.context,
                        'attributes': e.attributes
                    }
                    for e in result.entities
                ],
                'categories': result.categories,
                'quality_score': result.quality_score,
                'processing_time': result.processing_time,
                'metadata': result.metadata
            }
            save_data.append(data)
        
        # 保存为JSON
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(save_data, f, ensure_ascii=False, indent=2)
        
        self.logger.info(f"处理结果已保存到: {output_path}")
        
        return str(output_path)
    
    def get_summary_report(self, results: List[ProcessedText]) -> Dict[str, Any]:
        """生成处理总结报告"""
        
        if not results:
            return {}
        
        # 基础统计
        total_texts = len(results)
        successful_results = [r for r in results if r.quality_score > 0]
        successful_count = len(successful_results)
        
        # 质量统计
        quality_scores = [r.quality_score for r in successful_results]
        avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0
        
        # 实体统计
        all_entities = []
        for result in successful_results:
            all_entities.extend(result.entities)
        
        entity_type_counts = Counter(e.entity_type for e in all_entities)
        
        # 分类统计
        all_categories = []
        for result in successful_results:
            all_categories.extend(result.categories)
        
        category_counts = Counter(all_categories)
        
        # 处理时间统计
        processing_times = [r.processing_time for r in results]
        total_processing_time = sum(processing_times)
        avg_processing_time = total_processing_time / len(processing_times) if processing_times else 0
        
        report = {
            'summary': {
                'total_texts': total_texts,
                'successful_texts': successful_count,
                'success_rate': (successful_count / total_texts * 100) if total_texts > 0 else 0,
                'average_quality_score': avg_quality,
                'total_processing_time': total_processing_time,
                'average_processing_time': avg_processing_time
            },
            'entity_statistics': dict(entity_type_counts),
            'category_statistics': dict(category_counts),
            'quality_distribution': {
                'high_quality': len([s for s in quality_scores if s >= 0.8]),
                'medium_quality': len([s for s in quality_scores if 0.5 <= s < 0.8]),
                'low_quality': len([s for s in quality_scores if s < 0.5])
            },
            'processor_stats': self.processor.get_processing_stats()
        }
        
        return report