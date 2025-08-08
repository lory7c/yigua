#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能内容分类器
专门用于识别和分类易经、六爻、大六壬等古籍文档中的不同内容类型
支持卦象、爻辞、注解、案例等多种内容的智能识别
"""

import re
import logging
from typing import Dict, List, Optional, Tuple, Set, NamedTuple
from dataclasses import dataclass
from pathlib import Path
import json
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
import numpy as np
from functools import lru_cache
import time

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class ClassificationResult:
    """分类结果数据类"""
    content_type: str
    confidence: float
    features: Dict[str, float]
    text_segment: str
    start_position: int
    end_position: int
    metadata: Dict = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class ContentClassifier:
    """智能内容分类器"""
    
    def __init__(self):
        """初始化分类器"""
        self.content_types = {
            'gua_name': '卦名',
            'gua_ci': '卦辞', 
            'yao_ci': '爻辞',
            'tuan_ci': '彖辞',
            'xiang_ci': '象辞',
            'wen_yan': '文言',
            'annotation': '注解',
            'case_study': '案例',
            'theory': '理论',
            'formula': '公式口诀',
            'date_time': '时间日期',
            'divination_method': '起卦方法',
            'interpretation': '断卦解释',
            'prediction': '预测结果',
            'other': '其他'
        }
        
        # 编译正则模式
        self._compile_patterns()
        
        # 初始化特征词典
        self._init_feature_dictionaries()
        
        # 初始化权重
        self._init_weights()
        
        logger.info("内容分类器初始化完成")
    
    def _compile_patterns(self):
        """编译正则表达式模式"""
        self.patterns = {
            # 卦名模式
            'gua_name': [
                re.compile(r'\b(乾|坤|屯|蒙|需|讼|师|比|小畜|履|泰|否|同人|大有|谦|豫|随|蛊|临|观|噬嗑|贲|剥|复|无妄|大畜|颐|大过|坎|离|咸|恒|遁|大壮|晋|明夷|家人|睽|蹇|解|损|益|夬|姤|萃|升|困|井|革|鼎|震|艮|渐|归妹|丰|旅|巽|兑|涣|节|中孚|小过|既济|未济)\s*卦?\b'),
                re.compile(r'([乾坤震巽坎离艮兑])\s*为\s*([乾坤震巽坎离艮兑])'),
                re.compile(r'([乾坤震巽坎离艮兑])\s*([乾坤震巽坎离艮兑])\s*卦')
            ],
            
            # 卦辞模式
            'gua_ci': [
                re.compile(r'(乾|坤|屯|蒙|需|讼|师|比|小畜|履|泰|否|同人|大有|谦|豫|随|蛊|临|观|噬嗑|贲|剥|复|无妄|大畜|颐|大过|坎|离|咸|恒|遁|大壮|晋|明夷|家人|睽|蹇|解|损|益|夬|姤|萃|升|困|井|革|鼎|震|艮|渐|归妹|丰|旅|巽|兑|涣|节|中孚|小过|既济|未济)\s*[:：]\s*(.{5,50})'),
                re.compile(r'卦辞\s*[:：]\s*(.+)')
            ],
            
            # 爻辞模式
            'yao_ci': [
                re.compile(r'(初|二|三|四|五|上)\s*(六|九)\s*[:：]\s*(.+)'),
                re.compile(r'(初九|九二|九三|九四|九五|上九|初六|六二|六三|六四|六五|上六)\s*[:：]\s*(.+)'),
                re.compile(r'爻辞\s*[:：]\s*(.+)')
            ],
            
            # 彖辞模式
            'tuan_ci': [
                re.compile(r'彖曰?\s*[:：]\s*(.+)'),
                re.compile(r'彖辞\s*[:：]\s*(.+)')
            ],
            
            # 象辞模式
            'xiang_ci': [
                re.compile(r'象曰?\s*[:：]\s*(.+)'),
                re.compile(r'大象\s*[:：]\s*(.+)'),
                re.compile(r'小象\s*[:：]\s*(.+)')
            ],
            
            # 文言模式
            'wen_yan': [
                re.compile(r'文言曰?\s*[:：]\s*(.+)'),
                re.compile(r'文言\s*[:：]\s*(.+)')
            ],
            
            # 注解模式
            'annotation': [
                re.compile(r'注\s*[:：]\s*(.+)'),
                re.compile(r'释\s*[:：]\s*(.+)'),
                re.compile(r'疏\s*[:：]\s*(.+)'),
                re.compile(r'按\s*[:：]\s*(.+)'),
                re.compile(r'案\s*[:：]\s*(.+)'),
                re.compile(r'解\s*[:：]\s*(.+)')
            ],
            
            # 案例模式
            'case_study': [
                re.compile(r'例\s*\d*\s*[:：]\s*(.+)'),
                re.compile(r'案例\s*\d*\s*[:：]\s*(.+)'),
                re.compile(r'实例\s*\d*\s*[:：]\s*(.+)'),
                re.compile(r'卦例\s*\d*\s*[:：]\s*(.+)')
            ],
            
            # 时间日期模式
            'date_time': [
                re.compile(r'(甲|乙|丙|丁|戊|己|庚|辛|壬|癸)(子|丑|寅|卯|辰|巳|午|未|申|酉|戌|亥)年'),
                re.compile(r'(正|二|三|四|五|六|七|八|九|十|冬|腊)月'),
                re.compile(r'\d{4}年\d{1,2}月\d{1,2}日'),
                re.compile(r'(子|丑|寅|卯|辰|巳|午|未|申|酉|戌|亥)时')
            ]
        }
    
    def _init_feature_dictionaries(self):
        """初始化特征词典"""
        self.feature_words = {
            'gua_name': {
                '卦', '乾', '坤', '震', '巽', '坎', '离', '艮', '兑',
                '上卦', '下卦', '本卦', '变卦', '互卦', '错卦', '综卦'
            },
            
            'gua_ci': {
                '元亨', '利贞', '无咎', '有孚', '大吉', '小吉', '凶', 
                '厉', '悔', '吝', '亨', '利', '贞'
            },
            
            'yao_ci': {
                '初', '二', '三', '四', '五', '上', '九', '六',
                '勿用', '见龙', '飞龙', '亢龙', '潜龙', '群龙'
            },
            
            'tuan_ci': {
                '彖曰', '彖辞', '大哉', '刚健', '柔顺', '时行', '天道', '地道'
            },
            
            'xiang_ci': {
                '象曰', '大象', '小象', '君子以', '先王以', '后以',
                '天行健', '地势坤', '云雷屯', '山下出泉'
            },
            
            'annotation': {
                '注', '释', '疏', '按', '案', '解', '曰', '谓', '者',
                '所以', '故', '是以', '盖', '夫'
            },
            
            'case_study': {
                '例', '案例', '实例', '卦例', '占', '问', '测', '断',
                '验证', '应验', '准确', '不准'
            },
            
            'theory': {
                '理论', '原理', '法则', '规律', '定律', '学说', '思想',
                '观念', '概念', '体系', '架构'
            },
            
            'formula': {
                '口诀', '歌诀', '赋', '诀', '法', '术', '式', '秘',
                '要诀', '心法', '真诀', '妙诀'
            },
            
            'divination_method': {
                '起卦', '摇卦', '装卦', '排卦', '成卦', '变卦',
                '铜钱', '蓍草', '时间', '方位', '数字'
            },
            
            'interpretation': {
                '断卦', '解卦', '释卦', '判断', '分析', '推理',
                '吉凶', '休咎', '得失', '成败', '进退'
            },
            
            'prediction': {
                '预测', '预言', '占卜', '卜筮', '推算', '测算',
                '应期', '应验', '结果', '未来', '将来'
            }
        }
    
    def _init_weights(self):
        """初始化分类权重"""
        self.weights = {
            'pattern_match': 0.4,    # 正则模式匹配权重
            'feature_words': 0.3,    # 特征词权重
            'position': 0.1,         # 位置权重
            'context': 0.2           # 上下文权重
        }
    
    @lru_cache(maxsize=1000)
    def _calculate_pattern_score(self, text: str, content_type: str) -> float:
        """计算正则模式匹配分数"""
        if content_type not in self.patterns:
            return 0.0
        
        patterns = self.patterns[content_type]
        max_score = 0.0
        
        for pattern in patterns:
            matches = pattern.findall(text)
            if matches:
                # 匹配数量和匹配长度影响分数
                match_count = len(matches)
                avg_match_length = sum(len(str(match)) for match in matches) / match_count
                score = min(1.0, (match_count * 0.3 + avg_match_length * 0.01))
                max_score = max(max_score, score)
        
        return max_score
    
    def _calculate_feature_score(self, text: str, content_type: str) -> float:
        """计算特征词匹配分数"""
        if content_type not in self.feature_words:
            return 0.0
        
        feature_words = self.feature_words[content_type]
        text_words = set(re.findall(r'\w+', text))
        
        matched_words = feature_words.intersection(text_words)
        if not feature_words:
            return 0.0
        
        score = len(matched_words) / len(feature_words)
        return min(1.0, score * 2)  # 放大分数，最大为1
    
    def _calculate_position_score(self, position: float, text_length: int, content_type: str) -> float:
        """计算位置权重分数"""
        relative_position = position / text_length if text_length > 0 else 0
        
        # 不同内容类型在文档中的典型位置权重
        position_preferences = {
            'gua_name': [0.0, 0.2],      # 通常在开头
            'gua_ci': [0.0, 0.3],        # 通常在前部
            'yao_ci': [0.2, 0.8],        # 通常在中间
            'tuan_ci': [0.1, 0.5],       # 通常在前中部
            'xiang_ci': [0.3, 0.9],      # 可能在各个位置
            'annotation': [0.2, 1.0],     # 可能在各个位置
            'case_study': [0.5, 1.0],    # 通常在后部
        }
        
        if content_type in position_preferences:
            start, end = position_preferences[content_type]
            if start <= relative_position <= end:
                return 1.0
            elif relative_position < start:
                return max(0.1, 1.0 - (start - relative_position) * 2)
            else:
                return max(0.1, 1.0 - (relative_position - end) * 2)
        
        return 0.5  # 默认中等权重
    
    def _calculate_context_score(self, text: str, surrounding_text: str, content_type: str) -> float:
        """计算上下文相关性分数"""
        # 简化版上下文分析
        context_indicators = {
            'gua_name': ['卦', '乾坤', '八卦', '六十四卦'],
            'yao_ci': ['爻', '初二三四五上', '九六'],
            'annotation': ['注', '释', '解', '按', '疏'],
            'case_study': ['例', '实占', '验证', '应验']
        }
        
        if content_type in context_indicators:
            indicators = context_indicators[content_type]
            combined_text = text + ' ' + surrounding_text
            
            score = 0.0
            for indicator in indicators:
                if indicator in combined_text:
                    score += 0.25
            
            return min(1.0, score)
        
        return 0.5
    
    def classify_segment(self, text: str, position: int = 0, 
                        text_length: int = None, surrounding_text: str = "") -> ClassificationResult:
        """
        分类单个文本片段
        
        Args:
            text: 要分类的文本片段
            position: 文本在原文档中的位置
            text_length: 原文档总长度
            surrounding_text: 周围上下文文本
            
        Returns:
            分类结果
        """
        if not text.strip():
            return ClassificationResult(
                content_type='other',
                confidence=0.0,
                features={},
                text_segment=text,
                start_position=position,
                end_position=position + len(text)
            )
        
        text_length = text_length or len(text)
        scores = {}
        features = {}
        
        # 计算各种内容类型的分数
        for content_type in self.content_types.keys():
            pattern_score = self._calculate_pattern_score(text, content_type)
            feature_score = self._calculate_feature_score(text, content_type)
            position_score = self._calculate_position_score(position, text_length, content_type)
            context_score = self._calculate_context_score(text, surrounding_text, content_type)
            
            # 加权计算总分
            total_score = (
                pattern_score * self.weights['pattern_match'] +
                feature_score * self.weights['feature_words'] +
                position_score * self.weights['position'] +
                context_score * self.weights['context']
            )
            
            scores[content_type] = total_score
            features[content_type] = {
                'pattern': pattern_score,
                'feature': feature_score,
                'position': position_score,
                'context': context_score
            }
        
        # 找到最高分的分类
        best_type = max(scores.keys(), key=lambda k: scores[k])
        best_score = scores[best_type]
        
        # 如果分数太低，归类为其他
        if best_score < 0.2:
            best_type = 'other'
            best_score = scores['other']
        
        return ClassificationResult(
            content_type=best_type,
            confidence=best_score,
            features=features[best_type],
            text_segment=text,
            start_position=position,
            end_position=position + len(text),
            metadata={
                'all_scores': scores,
                'text_length': len(text)
            }
        )
    
    def classify_document(self, text: str, segment_size: int = 200, 
                         overlap: int = 50) -> List[ClassificationResult]:
        """
        分类整个文档
        
        Args:
            text: 文档文本
            segment_size: 分段大小
            overlap: 重叠大小
            
        Returns:
            分类结果列表
        """
        if not text:
            return []
        
        results = []
        text_length = len(text)
        position = 0
        
        while position < text_length:
            # 计算当前片段的结束位置
            end_pos = min(position + segment_size, text_length)
            segment = text[position:end_pos]
            
            # 获取上下文
            context_start = max(0, position - overlap)
            context_end = min(text_length, end_pos + overlap)
            surrounding_text = text[context_start:context_end]
            
            # 分类当前片段
            result = self.classify_segment(segment, position, text_length, surrounding_text)
            results.append(result)
            
            # 移动到下一个位置
            position += segment_size - overlap
            
            if position >= text_length:
                break
        
        return results
    
    def merge_adjacent_segments(self, results: List[ClassificationResult], 
                               min_confidence: float = 0.3) -> List[ClassificationResult]:
        """
        合并相邻的相同类型片段
        
        Args:
            results: 分类结果列表
            min_confidence: 最小置信度阈值
            
        Returns:
            合并后的结果列表
        """
        if not results:
            return []
        
        merged = []
        current_group = [results[0]]
        
        for i in range(1, len(results)):
            current = results[i]
            previous = current_group[-1]
            
            # 如果类型相同且置信度足够，合并
            if (current.content_type == previous.content_type and 
                current.confidence >= min_confidence and 
                previous.confidence >= min_confidence):
                current_group.append(current)
            else:
                # 创建合并的结果
                if len(current_group) > 1:
                    merged_result = self._merge_group(current_group)
                    merged.append(merged_result)
                else:
                    merged.append(current_group[0])
                
                current_group = [current]
        
        # 处理最后一组
        if current_group:
            if len(current_group) > 1:
                merged_result = self._merge_group(current_group)
                merged.append(merged_result)
            else:
                merged.append(current_group[0])
        
        return merged
    
    def _merge_group(self, group: List[ClassificationResult]) -> ClassificationResult:
        """合并一组相同类型的结果"""
        if not group:
            return None
        
        if len(group) == 1:
            return group[0]
        
        # 合并文本
        combined_text = ''.join(result.text_segment for result in group)
        
        # 计算平均置信度
        avg_confidence = sum(result.confidence for result in group) / len(group)
        
        # 合并特征
        merged_features = {}
        for key in group[0].features.keys():
            merged_features[key] = sum(result.features[key] for result in group) / len(group)
        
        return ClassificationResult(
            content_type=group[0].content_type,
            confidence=avg_confidence,
            features=merged_features,
            text_segment=combined_text,
            start_position=group[0].start_position,
            end_position=group[-1].end_position,
            metadata={
                'merged_count': len(group),
                'original_segments': len(group)
            }
        )
    
    def analyze_document_structure(self, results: List[ClassificationResult]) -> Dict:
        """
        分析文档结构
        
        Args:
            results: 分类结果列表
            
        Returns:
            文档结构分析
        """
        if not results:
            return {}
        
        # 统计各类型的数量和分布
        type_counts = Counter(result.content_type for result in results)
        type_positions = defaultdict(list)
        type_confidences = defaultdict(list)
        
        for result in results:
            type_positions[result.content_type].append(result.start_position)
            type_confidences[result.content_type].append(result.confidence)
        
        # 计算统计信息
        structure = {
            'total_segments': len(results),
            'content_types': dict(type_counts),
            'type_distribution': {},
            'document_flow': [result.content_type for result in results],
            'high_confidence_types': [],
            'low_confidence_types': []
        }
        
        for content_type, count in type_counts.items():
            confidences = type_confidences[content_type]
            positions = type_positions[content_type]
            
            structure['type_distribution'][content_type] = {
                'count': count,
                'percentage': count / len(results) * 100,
                'avg_confidence': sum(confidences) / len(confidences),
                'avg_position': sum(positions) / len(positions),
                'position_spread': max(positions) - min(positions) if len(positions) > 1 else 0
            }
            
            avg_conf = structure['type_distribution'][content_type]['avg_confidence']
            if avg_conf >= 0.7:
                structure['high_confidence_types'].append(content_type)
            elif avg_conf < 0.3:
                structure['low_confidence_types'].append(content_type)
        
        return structure
    
    def classify_file(self, file_path: str, output_path: str = None) -> Dict:
        """
        分类文件并保存结果
        
        Args:
            file_path: 输入文件路径
            output_path: 输出文件路径
            
        Returns:
            分类结果统计
        """
        start_time = time.time()
        
        try:
            # 读取文件
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
            
            # 执行分类
            results = self.classify_document(text)
            merged_results = self.merge_adjacent_segments(results)
            structure = self.analyze_document_structure(merged_results)
            
            # 准备输出数据
            output_data = {
                'file_path': file_path,
                'processing_time': time.time() - start_time,
                'document_structure': structure,
                'classification_results': [
                    {
                        'content_type': result.content_type,
                        'confidence': result.confidence,
                        'text_preview': result.text_segment[:100],
                        'start_position': result.start_position,
                        'end_position': result.end_position,
                        'features': result.features
                    }
                    for result in merged_results
                ]
            }
            
            # 保存结果
            if output_path:
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(output_data, f, ensure_ascii=False, indent=2)
                logger.info(f"分类结果已保存到: {output_path}")
            
            logger.info(f"文件分类完成: {Path(file_path).name}, "
                       f"共 {len(merged_results)} 个片段, "
                       f"耗时: {output_data['processing_time']:.2f}s")
            
            return output_data
            
        except Exception as e:
            logger.error(f"文件分类失败 {file_path}: {e}")
            return {'error': str(e), 'file_path': file_path}


def main():
    """主函数示例"""
    classifier = ContentClassifier()
    
    # 示例文本
    sample_text = """
    乾卦
    
    乾：元亨利贞。
    
    彖曰：大哉乾元，万物资始，乃统天。云行雨施，品物流形。
    
    象曰：天行健，君子以自强不息。
    
    初九：潜龙勿用。
    象曰：潜龙勿用，阳在下也。
    
    注：此乾卦为六十四卦之首，代表天之德性。
    
    例1：某人问事业，得乾卦，断其必有大发展。
    """
    
    # 执行分类
    results = classifier.classify_document(sample_text)
    merged_results = classifier.merge_adjacent_segments(results)
    
    print("分类结果：")
    for result in merged_results:
        print(f"类型: {result.content_type}")
        print(f"置信度: {result.confidence:.2f}")
        print(f"文本: {result.text_segment[:50]}...")
        print("---")


if __name__ == "__main__":
    main()