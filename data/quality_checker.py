#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
质量评估和验证模块
用于评估文本处理质量、数据完整性和准确性
包括语义一致性检查、格式规范性验证、内容逻辑性检查等
"""

import re
import logging
from typing import Dict, List, Optional, Tuple, Set, Union
from dataclasses import dataclass, field
from pathlib import Path
import json
import time
from collections import defaultdict, Counter
import math
import statistics
from concurrent.futures import ThreadPoolExecutor
import difflib

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class QualityIssue:
    """质量问题数据结构"""
    issue_type: str
    severity: str  # 'critical', 'major', 'minor', 'warning'
    description: str
    position: int
    line_number: int
    context: str
    suggestion: str = ""
    confidence: float = 1.0


@dataclass
class QualityReport:
    """质量报告数据结构"""
    overall_score: float
    total_issues: int
    critical_issues: int
    major_issues: int
    minor_issues: int
    warnings: int
    issues: List[QualityIssue] = field(default_factory=list)
    metrics: Dict = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)
    processing_time: float = 0.0


class QualityChecker:
    """质量检查器"""
    
    def __init__(self):
        """初始化质量检查器"""
        self.gua_names = self._load_standard_gua_names()
        self.yao_names = self._load_standard_yao_names()
        self.standard_phrases = self._load_standard_phrases()
        
        # 编译检查规则
        self._compile_check_patterns()
        
        # 初始化权重
        self._init_weights()
        
        logger.info("质量检查器初始化完成")
    
    def _load_standard_gua_names(self) -> Set[str]:
        """加载标准卦名"""
        eight_gua = {'乾', '坤', '震', '巽', '坎', '离', '艮', '兑'}
        sixty_four_gua = {
            '乾', '坤', '屯', '蒙', '需', '讼', '师', '比', '小畜', '履',
            '泰', '否', '同人', '大有', '谦', '豫', '随', '蛊', '临', '观',
            '噬嗑', '贲', '剥', '复', '无妄', '大畜', '颐', '大过', '坎', '离',
            '咸', '恒', '遁', '大壮', '晋', '明夷', '家人', '睽', '蹇', '解',
            '损', '益', '夬', '姤', '萃', '升', '困', '井', '革', '鼎',
            '震', '艮', '渐', '归妹', '丰', '旅', '巽', '兑', '涣', '节',
            '中孚', '小过', '既济', '未济'
        }
        return eight_gua.union(sixty_four_gua)
    
    def _load_standard_yao_names(self) -> Set[str]:
        """加载标准爻名"""
        return {
            '初九', '九二', '九三', '九四', '九五', '上九',
            '初六', '六二', '六三', '六四', '六五', '上六'
        }
    
    def _load_standard_phrases(self) -> Dict[str, List[str]]:
        """加载标准术语和短语"""
        return {
            'divination_terms': [
                '彖曰', '象曰', '文言曰', '系辞', '说卦', '序卦', '杂卦',
                '元亨利贞', '无咎', '有孚', '吉', '凶', '厉', '悔', '吝'
            ],
            'liuyao_terms': [
                '世爻', '应爻', '动爻', '变爻', '空亡', '月破', '日冲',
                '父母', '兄弟', '子孙', '妻财', '官鬼', '青龙', '朱雀',
                '勾陈', '螣蛇', '白虎', '玄武'
            ],
            'time_terms': [
                '甲乙丙丁戊己庚辛壬癸', '子丑寅卯辰巳午未申酉戌亥',
                '正月', '二月', '三月', '四月', '五月', '六月',
                '七月', '八月', '九月', '十月', '冬月', '腊月'
            ]
        }
    
    def _compile_check_patterns(self):
        """编译检查模式"""
        self.check_patterns = {
            # 格式规范检查
            'invalid_punctuation': re.compile(r'[，。！？：；、]{2,}|[，。！？：；、]\s+[，。！？：；、]'),
            'extra_spaces': re.compile(r'\s{3,}'),
            'mixed_punctuation': re.compile(r'[，。！？：；、][,\.!?:;]|[,\.!?:;][，。！？：；、]'),
            'incomplete_brackets': re.compile(r'[（【《〈][^）】》〉]*$|^[^（【《〈]*[）】》〉]'),
            
            # 内容逻辑检查
            'invalid_yao_sequence': re.compile(r'(初九|九二|九三|九四|九五|上九|初六|六二|六三|六四|六五|上六)(?!.*[:：])'),
            'incomplete_gua_ci': re.compile(r'([乾坤屯蒙需讼师比小畜履泰否同人大有谦豫随蛊临观噬嗑贲剥复无妄大畜颐大过坎离咸恒遁大壮晋明夷家人睽蹇解损益夬姤萃升困井革鼎震艮渐归妹丰旅巽兑涣节中孚小过既济未济])\s*[:：]\s*$'),
            'orphan_annotation': re.compile(r'^(注|释|疏|按|案)\s*[:：]'),
            
            # 编码和字符检查
            'invalid_chars': re.compile(r'[^\u4e00-\u9fff\u3400-\u4dbf\ua700-\ua71fa-zA-Z0-9\s，。！？：；、（）【】《》〈〉〔〕…—""''·\-\+=\*\/\\&%\$#@\[\]\{\}\|`~\^]'),
            'mixed_encodings': re.compile(r'[\uff00-\uffef]'),  # 全角字符
            
            # 语义一致性检查
            'contradictory_statements': re.compile(r'吉.*凶|凶.*吉|利.*不利|不利.*利'),
            'temporal_inconsistency': re.compile(r'(\d{4})年.*(\d{4})年'),
        }
    
    def _init_weights(self):
        """初始化检查权重"""
        self.severity_weights = {
            'critical': 10.0,
            'major': 5.0, 
            'minor': 2.0,
            'warning': 1.0
        }
        
        self.issue_categories = {
            'format': ['invalid_punctuation', 'extra_spaces', 'mixed_punctuation', 'incomplete_brackets'],
            'content': ['invalid_yao_sequence', 'incomplete_gua_ci', 'orphan_annotation'],
            'encoding': ['invalid_chars', 'mixed_encodings'],
            'logic': ['contradictory_statements', 'temporal_inconsistency']
        }
    
    def _get_line_number(self, text: str, position: int) -> int:
        """根据位置获取行号"""
        return text[:position].count('\n') + 1
    
    def _get_context(self, text: str, position: int, window: int = 50) -> str:
        """获取上下文文本"""
        start = max(0, position - window)
        end = min(len(text), position + window)
        context = text[start:end]
        
        # 如果截取的文本不是从开头开始，添加省略号
        if start > 0:
            context = '...' + context
        if end < len(text):
            context = context + '...'
            
        return context
    
    def check_format_quality(self, text: str) -> List[QualityIssue]:
        """检查格式质量"""
        issues = []
        
        # 检查标点符号问题
        for match in self.check_patterns['invalid_punctuation'].finditer(text):
            issue = QualityIssue(
                issue_type='invalid_punctuation',
                severity='minor',
                description='重复或错误的标点符号使用',
                position=match.start(),
                line_number=self._get_line_number(text, match.start()),
                context=self._get_context(text, match.start()),
                suggestion='删除多余的标点符号或修正标点符号间距'
            )
            issues.append(issue)
        
        # 检查多余空格
        for match in self.check_patterns['extra_spaces'].finditer(text):
            issue = QualityIssue(
                issue_type='extra_spaces',
                severity='minor',
                description='存在多余的空格',
                position=match.start(),
                line_number=self._get_line_number(text, match.start()),
                context=self._get_context(text, match.start()),
                suggestion='删除多余的空格，保持适当的间距'
            )
            issues.append(issue)
        
        # 检查混合标点
        for match in self.check_patterns['mixed_punctuation'].finditer(text):
            issue = QualityIssue(
                issue_type='mixed_punctuation',
                severity='major',
                description='混合使用中英文标点符号',
                position=match.start(),
                line_number=self._get_line_number(text, match.start()),
                context=self._get_context(text, match.start()),
                suggestion='统一使用中文标点符号'
            )
            issues.append(issue)
        
        # 检查不匹配的括号
        for match in self.check_patterns['incomplete_brackets'].finditer(text):
            issue = QualityIssue(
                issue_type='incomplete_brackets',
                severity='major',
                description='不匹配的括号或引号',
                position=match.start(),
                line_number=self._get_line_number(text, match.start()),
                context=self._get_context(text, match.start()),
                suggestion='补全缺失的括号或引号'
            )
            issues.append(issue)
        
        return issues
    
    def check_content_quality(self, text: str) -> List[QualityIssue]:
        """检查内容质量"""
        issues = []
        
        # 检查无效的爻序列
        for match in self.check_patterns['invalid_yao_sequence'].finditer(text):
            yao_name = match.group(1)
            if yao_name in self.yao_names:
                issue = QualityIssue(
                    issue_type='invalid_yao_sequence',
                    severity='major',
                    description=f'爻名 "{yao_name}" 后缺少冒号或内容',
                    position=match.start(),
                    line_number=self._get_line_number(text, match.start()),
                    context=self._get_context(text, match.start()),
                    suggestion=f'在 "{yao_name}" 后添加冒号和相应的爻辞内容'
                )
                issues.append(issue)
        
        # 检查不完整的卦辞
        for match in self.check_patterns['incomplete_gua_ci'].finditer(text):
            gua_name = match.group(1)
            issue = QualityIssue(
                issue_type='incomplete_gua_ci',
                severity='major',
                description=f'卦名 "{gua_name}" 后缺少卦辞内容',
                position=match.start(),
                line_number=self._get_line_number(text, match.start()),
                context=self._get_context(text, match.start()),
                suggestion=f'在 "{gua_name}:" 后添加相应的卦辞内容'
            )
            issues.append(issue)
        
        # 检查孤立的注释
        lines = text.split('\n')
        for i, line in enumerate(lines):
            if self.check_patterns['orphan_annotation'].match(line.strip()):
                # 检查前后是否有相关内容
                has_context = False
                for j in range(max(0, i-2), min(len(lines), i+3)):
                    if j != i and lines[j].strip():
                        has_context = True
                        break
                
                if not has_context:
                    position = sum(len(lines[k]) + 1 for k in range(i))
                    issue = QualityIssue(
                        issue_type='orphan_annotation',
                        severity='warning',
                        description='孤立的注释，缺少相关内容上下文',
                        position=position,
                        line_number=i + 1,
                        context=line,
                        suggestion='确保注释有相应的正文内容'
                    )
                    issues.append(issue)
        
        return issues
    
    def check_encoding_quality(self, text: str) -> List[QualityIssue]:
        """检查编码质量"""
        issues = []
        
        # 检查无效字符
        for match in self.check_patterns['invalid_chars'].finditer(text):
            issue = QualityIssue(
                issue_type='invalid_chars',
                severity='major',
                description=f'发现无效字符: {match.group(0)}',
                position=match.start(),
                line_number=self._get_line_number(text, match.start()),
                context=self._get_context(text, match.start()),
                suggestion='删除或替换无效字符'
            )
            issues.append(issue)
        
        # 检查混合编码
        for match in self.check_patterns['mixed_encodings'].finditer(text):
            issue = QualityIssue(
                issue_type='mixed_encodings',
                severity='minor',
                description=f'发现全角字符: {match.group(0)}',
                position=match.start(),
                line_number=self._get_line_number(text, match.start()),
                context=self._get_context(text, match.start()),
                suggestion='将全角字符转换为对应的半角字符'
            )
            issues.append(issue)
        
        return issues
    
    def check_logical_consistency(self, text: str) -> List[QualityIssue]:
        """检查逻辑一致性"""
        issues = []
        
        # 检查矛盾陈述
        for match in self.check_patterns['contradictory_statements'].finditer(text):
            issue = QualityIssue(
                issue_type='contradictory_statements',
                severity='major',
                description='发现矛盾的表述',
                position=match.start(),
                line_number=self._get_line_number(text, match.start()),
                context=self._get_context(text, match.start()),
                suggestion='检查并修正矛盾的表述',
                confidence=0.7  # 语义分析置信度较低
            )
            issues.append(issue)
        
        # 检查时间不一致
        time_matches = list(self.check_patterns['temporal_inconsistency'].finditer(text))
        for match in time_matches:
            years = [int(year) for year in match.groups()]
            if len(years) > 1 and abs(years[0] - years[1]) > 100:  # 时间跨度过大
                issue = QualityIssue(
                    issue_type='temporal_inconsistency',
                    severity='warning',
                    description=f'时间跨度异常: {years[0]}年 到 {years[1]}年',
                    position=match.start(),
                    line_number=self._get_line_number(text, match.start()),
                    context=self._get_context(text, match.start()),
                    suggestion='检查时间信息是否正确',
                    confidence=0.8
                )
                issues.append(issue)
        
        return issues
    
    def check_terminology_consistency(self, text: str) -> List[QualityIssue]:
        """检查术语一致性"""
        issues = []
        
        # 检查卦名的正确性
        gua_mentions = re.finditer(r'([乾坤屯蒙需讼师比小畜履泰否同人大有谦豫随蛊临观噬嗑贲剥复无妄大畜颐大过坎离咸恒遁大壮晋明夷家人睽蹇解损益夬姤萃升困井革鼎震艮渐归妹丰旅巽兑涣节中孚小过既济未济])', text)
        
        for match in gua_mentions:
            gua_name = match.group(1)
            if gua_name not in self.gua_names:
                issue = QualityIssue(
                    issue_type='invalid_gua_name',
                    severity='major',
                    description=f'可能存在错误的卦名: {gua_name}',
                    position=match.start(),
                    line_number=self._get_line_number(text, match.start()),
                    context=self._get_context(text, match.start()),
                    suggestion='检查卦名是否正确',
                    confidence=0.9
                )
                issues.append(issue)
        
        # 检查爻名的正确性
        yao_mentions = re.finditer(r'(初九|九二|九三|九四|九五|上九|初六|六二|六三|六四|六五|上六)', text)
        
        for match in yao_mentions:
            yao_name = match.group(1)
            if yao_name not in self.yao_names:
                issue = QualityIssue(
                    issue_type='invalid_yao_name',
                    severity='major',
                    description=f'可能存在错误的爻名: {yao_name}',
                    position=match.start(),
                    line_number=self._get_line_number(text, match.start()),
                    context=self._get_context(text, match.start()),
                    suggestion='检查爻名是否正确',
                    confidence=0.9
                )
                issues.append(issue)
        
        return issues
    
    def calculate_readability_score(self, text: str) -> float:
        """计算可读性分数"""
        if not text:
            return 0.0
        
        # 基本统计
        sentences = re.split(r'[。！？]', text)
        words = re.findall(r'\S+', text)
        chars = len(text)
        
        # 避免除零错误
        if not sentences or not words:
            return 0.0
        
        # 计算各种指标
        avg_sentence_length = chars / len([s for s in sentences if s.strip()])
        avg_word_length = chars / len(words)
        punctuation_ratio = len(re.findall(r'[，。！？：；、]', text)) / chars
        
        # 简化的中文可读性评分
        readability_score = max(0, min(100, 
            100 - (avg_sentence_length - 20) * 2 - 
            (avg_word_length - 2) * 10 + 
            punctuation_ratio * 50
        ))
        
        return readability_score
    
    def calculate_completeness_score(self, text: str, text_type: str = 'general') -> float:
        """计算完整性分数"""
        if not text:
            return 0.0
        
        completeness_score = 100.0
        
        if text_type == 'yijing':
            # 易经文本的完整性检查
            required_elements = ['gua_name', 'gua_ci', 'tuan_ci', 'xiang_ci', 'yao_ci']
            found_elements = []
            
            if re.search(r'[乾坤屯蒙需讼师比小畜履泰否同人大有谦豫随蛊临观噬嗑贲剥复无妄大畜颐大过坎离咸恒遁大壮晋明夷家人睽蹇解损益夬姤萃升困井革鼎震艮渐归妹丰旅巽兑涣节中孚小过既济未济]', text):
                found_elements.append('gua_name')
            if re.search(r'[乾坤屯蒙需讼师比小畜履泰否同人大有谦豫随蛊临观噬嗑贲剥复无妄大畜颐大过坎离咸恒遁大壮晋明夷家人睽蹇解损益夬姤萃升困井革鼎震艮渐归妹丰旅巽兑涣节中孚小过既济未济]\s*[:：]', text):
                found_elements.append('gua_ci')
            if re.search(r'彖曰', text):
                found_elements.append('tuan_ci')
            if re.search(r'象曰', text):
                found_elements.append('xiang_ci')
            if re.search(r'(初九|九二|九三|九四|九五|上九|初六|六二|六三|六四|六五|上六)', text):
                found_elements.append('yao_ci')
            
            completeness_score = (len(found_elements) / len(required_elements)) * 100
        
        elif text_type == 'liuyao':
            # 六爻文本的完整性检查
            required_elements = ['gua_name', 'yao_positions', 'world_response']
            found_elements = []
            
            if re.search(r'[乾坤震巽坎离艮兑]', text):
                found_elements.append('gua_name')
            if re.search(r'[子丑寅卯辰巳午未申酉戌亥]', text):
                found_elements.append('yao_positions')
            if re.search(r'[世应]', text):
                found_elements.append('world_response')
            
            completeness_score = (len(found_elements) / len(required_elements)) * 100
        
        return completeness_score
    
    def generate_quality_metrics(self, text: str, issues: List[QualityIssue]) -> Dict:
        """生成质量指标"""
        if not text:
            return {}
        
        # 基本统计
        char_count = len(text)
        word_count = len(re.findall(r'\S+', text))
        line_count = text.count('\n') + 1
        
        # 问题统计
        issue_counts = Counter(issue.severity for issue in issues)
        issue_types = Counter(issue.issue_type for issue in issues)
        
        # 质量分数计算
        penalty = sum(self.severity_weights.get(issue.severity, 1) for issue in issues)
        base_score = 100.0
        quality_score = max(0, base_score - penalty)
        
        # 可读性和完整性
        readability_score = self.calculate_readability_score(text)
        completeness_score = self.calculate_completeness_score(text)
        
        return {
            'basic_stats': {
                'char_count': char_count,
                'word_count': word_count,
                'line_count': line_count,
                'avg_line_length': char_count / line_count if line_count > 0 else 0
            },
            'issue_stats': {
                'total_issues': len(issues),
                'by_severity': dict(issue_counts),
                'by_type': dict(issue_types),
                'issue_density': len(issues) / char_count * 1000 if char_count > 0 else 0  # issues per 1000 chars
            },
            'quality_scores': {
                'overall_quality': quality_score,
                'readability': readability_score,
                'completeness': completeness_score,
                'consistency': max(0, 100 - len([i for i in issues if 'consistency' in i.issue_type]) * 10)
            }
        }
    
    def check_quality(self, text: str, text_type: str = 'general') -> QualityReport:
        """执行完整的质量检查"""
        start_time = time.time()
        
        if not text:
            return QualityReport(
                overall_score=0.0,
                total_issues=0,
                critical_issues=0,
                major_issues=0,
                minor_issues=0,
                warnings=0,
                processing_time=0.0
            )
        
        all_issues = []
        
        # 执行各种质量检查
        try:
            all_issues.extend(self.check_format_quality(text))
            all_issues.extend(self.check_content_quality(text))
            all_issues.extend(self.check_encoding_quality(text))
            all_issues.extend(self.check_logical_consistency(text))
            all_issues.extend(self.check_terminology_consistency(text))
        except Exception as e:
            logger.warning(f"质量检查过程中出现错误: {e}")
        
        # 统计问题数量
        issue_counts = Counter(issue.severity for issue in all_issues)
        
        # 计算整体质量分数
        penalty = sum(self.severity_weights.get(issue.severity, 1) for issue in all_issues)
        overall_score = max(0, min(100, 100 - penalty))
        
        # 生成质量指标
        metrics = self.generate_quality_metrics(text, all_issues)
        
        # 生成改进建议
        recommendations = self._generate_recommendations(all_issues, text_type)
        
        return QualityReport(
            overall_score=overall_score,
            total_issues=len(all_issues),
            critical_issues=issue_counts.get('critical', 0),
            major_issues=issue_counts.get('major', 0),
            minor_issues=issue_counts.get('minor', 0),
            warnings=issue_counts.get('warning', 0),
            issues=all_issues,
            metrics=metrics,
            recommendations=recommendations,
            processing_time=time.time() - start_time
        )
    
    def _generate_recommendations(self, issues: List[QualityIssue], text_type: str) -> List[str]:
        """生成改进建议"""
        recommendations = []
        
        # 按问题类型分组
        issue_types = defaultdict(list)
        for issue in issues:
            issue_types[issue.issue_type].append(issue)
        
        # 生成针对性建议
        if 'invalid_punctuation' in issue_types:
            recommendations.append("统一标点符号使用规范，删除重复标点")
        
        if 'mixed_punctuation' in issue_types:
            recommendations.append("统一使用中文标点符号，避免中英文标点混用")
        
        if 'invalid_chars' in issue_types:
            recommendations.append("清理无效字符，确保文本编码统一")
        
        if 'incomplete_gua_ci' in issue_types:
            recommendations.append("补全缺失的卦辞内容")
        
        if 'invalid_yao_sequence' in issue_types:
            recommendations.append("检查爻辞格式，确保格式完整")
        
        if text_type == 'yijing':
            recommendations.append("确保易经文本包含卦名、卦辞、彖辞、象辞等基本要素")
        elif text_type == 'liuyao':
            recommendations.append("确保六爻文本包含卦象、爻位、世应等关键信息")
        
        return recommendations[:10]  # 限制建议数量
    
    def check_file(self, file_path: str, text_type: str = 'general', 
                  output_path: str = None) -> QualityReport:
        """检查文件质量"""
        try:
            # 读取文件
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
            
            # 执行质量检查
            report = self.check_quality(text, text_type)
            
            # 添加文件信息
            report.metrics['file_info'] = {
                'file_path': file_path,
                'file_size': len(text),
                'text_type': text_type
            }
            
            # 保存报告
            if output_path:
                self.save_report(report, output_path)
            
            logger.info(f"质量检查完成: {Path(file_path).name}, "
                       f"得分: {report.overall_score:.1f}, "
                       f"问题数: {report.total_issues}, "
                       f"耗时: {report.processing_time:.2f}s")
            
            return report
            
        except Exception as e:
            logger.error(f"文件质量检查失败 {file_path}: {e}")
            return QualityReport(
                overall_score=0.0,
                total_issues=1,
                critical_issues=1,
                major_issues=0,
                minor_issues=0,
                warnings=0,
                issues=[QualityIssue(
                    issue_type='file_error',
                    severity='critical',
                    description=f'文件读取错误: {e}',
                    position=0,
                    line_number=0,
                    context='',
                    suggestion='检查文件路径和编码'
                )]
            )
    
    def save_report(self, report: QualityReport, output_path: str):
        """保存质量报告"""
        try:
            report_data = {
                'overall_score': report.overall_score,
                'total_issues': report.total_issues,
                'issue_summary': {
                    'critical': report.critical_issues,
                    'major': report.major_issues,
                    'minor': report.minor_issues,
                    'warnings': report.warnings
                },
                'issues': [
                    {
                        'type': issue.issue_type,
                        'severity': issue.severity,
                        'description': issue.description,
                        'line': issue.line_number,
                        'position': issue.position,
                        'context': issue.context,
                        'suggestion': issue.suggestion,
                        'confidence': issue.confidence
                    }
                    for issue in report.issues
                ],
                'metrics': report.metrics,
                'recommendations': report.recommendations,
                'processing_time': report.processing_time,
                'timestamp': time.time()
            }
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, ensure_ascii=False, indent=2)
                
            logger.info(f"质量报告已保存到: {output_path}")
            
        except Exception as e:
            logger.error(f"保存质量报告失败: {e}")
    
    def batch_check(self, file_paths: List[str], output_dir: str = None, 
                   text_type: str = 'general') -> List[QualityReport]:
        """批量质量检查"""
        reports = []
        
        for file_path in file_paths:
            output_path = None
            if output_dir:
                output_dir_path = Path(output_dir)
                output_dir_path.mkdir(parents=True, exist_ok=True)
                filename = Path(file_path).stem + '_quality_report.json'
                output_path = output_dir_path / filename
            
            report = self.check_file(file_path, text_type, output_path)
            reports.append(report)
        
        return reports


def main():
    """主函数示例"""
    checker = QualityChecker()
    
    # 示例文本（包含一些质量问题）
    sample_text = """
    乾卦
    
    乾：：元亨利贞。。
    
    彖曰：大哉乾元，万物资始    ，乃统天。
    
    象曰：天行健，君子以自强不息.
    
    初九
    象曰：潜龙勿用，阳在下也。
    
    注：这个卦很吉利又很凶险。
    """
    
    # 执行质量检查
    report = checker.check_quality(sample_text, 'yijing')
    
    print("质量检查报告：")
    print(f"整体分数: {report.overall_score:.1f}")
    print(f"总问题数: {report.total_issues}")
    print(f"严重问题: {report.critical_issues}")
    print(f"主要问题: {report.major_issues}")
    print(f"次要问题: {report.minor_issues}")
    print(f"警告: {report.warnings}")
    
    print("\n主要问题：")
    for issue in report.issues[:5]:  # 显示前5个问题
        print(f"- {issue.issue_type}: {issue.description}")
        print(f"  位置: 第{issue.line_number}行")
        print(f"  建议: {issue.suggestion}")


if __name__ == "__main__":
    main()