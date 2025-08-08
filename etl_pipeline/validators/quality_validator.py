"""
数据质量验证器
实现全面的数据质量检查和验证规则
"""

import re
import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime
import hashlib
import statistics
from collections import Counter, defaultdict

from ..models import ProcessedContent, QualityLevel, QualityReport, ContentType
from ..config import ETLConfig


@dataclass
class ValidationRule:
    """验证规则定义"""
    name: str
    description: str
    rule_type: str  # 'content', 'structure', 'format', 'business'
    severity: str   # 'critical', 'major', 'minor', 'info'
    check_function: str
    threshold: Optional[float] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True


@dataclass
class ValidationResult:
    """验证结果"""
    rule_name: str
    passed: bool
    score: float
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    severity: str = 'info'


class DataQualityValidator:
    """数据质量验证器"""
    
    def __init__(self, config: ETLConfig = None):
        self.config = config or ETLConfig()
        self.logger = logging.getLogger(__name__)
        
        # 初始化验证规则
        self.validation_rules = self._initialize_validation_rules()
        
        # 质量评分权重
        self.quality_weights = {
            'content_completeness': 0.25,
            'text_quality': 0.20,
            'classification_accuracy': 0.20,
            'structure_integrity': 0.15,
            'encoding_quality': 0.10,
            'business_rules': 0.10
        }
    
    def _initialize_validation_rules(self) -> Dict[str, ValidationRule]:
        """初始化验证规则"""
        rules = {
            # 内容完整性规则
            'min_text_length': ValidationRule(
                name='最小文本长度',
                description='检查文本内容是否达到最小长度要求',
                rule_type='content',
                severity='critical',
                check_function='_check_min_text_length',
                threshold=self.config.MIN_TEXT_LENGTH
            ),
            
            'max_text_length': ValidationRule(
                name='最大文本长度',
                description='检查文本内容是否超过最大长度限制',
                rule_type='content',
                severity='major',
                check_function='_check_max_text_length',
                threshold=self.config.MAX_TEXT_LENGTH
            ),
            
            'chinese_content_ratio': ValidationRule(
                name='中文内容比例',
                description='检查中文字符占比是否合理',
                rule_type='content',
                severity='major',
                check_function='_check_chinese_content_ratio',
                threshold=0.3,  # 至少30%中文字符
                parameters={'min_ratio': 0.3}
            ),
            
            'encoding_quality': ValidationRule(
                name='编码质量',
                description='检查文本编码质量，识别乱码',
                rule_type='format',
                severity='critical',
                check_function='_check_encoding_quality',
                threshold=0.95  # 95%的字符应该是有效的
            ),
            
            # 结构完整性规则
            'required_fields': ValidationRule(
                name='必填字段检查',
                description='检查必要字段是否完整',
                rule_type='structure',
                severity='critical',
                check_function='_check_required_fields',
                parameters={
                    'required_fields': ['id', 'title', 'content', 'content_type', 'category']
                }
            ),
            
            'field_format': ValidationRule(
                name='字段格式验证',
                description='检查字段格式是否符合要求',
                rule_type='structure',
                severity='major',
                check_function='_check_field_format'
            ),
            
            # 分类准确性规则
            'classification_confidence': ValidationRule(
                name='分类置信度',
                description='检查内容分类的置信度',
                rule_type='business',
                severity='major',
                check_function='_check_classification_confidence',
                threshold=self.config.MIN_CONFIDENCE_SCORE
            ),
            
            'category_consistency': ValidationRule(
                name='分类一致性',
                description='检查分类结果的一致性',
                rule_type='business',
                severity='minor',
                check_function='_check_category_consistency'
            ),
            
            # 业务规则验证
            'hexagram_structure': ValidationRule(
                name='卦象结构验证',
                description='验证64卦相关内容的结构完整性',
                rule_type='business',
                severity='major',
                check_function='_check_hexagram_structure',
                enabled=True
            ),
            
            'yao_structure': ValidationRule(
                name='爻辞结构验证', 
                description='验证384爻辞内容的结构',
                rule_type='business',
                severity='major',
                check_function='_check_yao_structure',
                enabled=True
            ),
            
            # 内容去重规则
            'duplicate_content': ValidationRule(
                name='重复内容检测',
                description='检测重复或高度相似的内容',
                rule_type='content',
                severity='minor',
                check_function='_check_duplicate_content',
                threshold=0.85  # 85%相似度阈值
            ),
            
            # 数据新鲜度规则
            'data_freshness': ValidationRule(
                name='数据新鲜度',
                description='检查数据的时效性',
                rule_type='content',
                severity='info',
                check_function='_check_data_freshness',
                parameters={'max_age_days': 30}
            )
        }
        
        return rules
    
    def validate_single_item(self, content: ProcessedContent) -> List[ValidationResult]:
        """验证单个内容项"""
        results = []
        
        for rule_name, rule in self.validation_rules.items():
            if not rule.enabled:
                continue
                
            try:
                # 获取检查函数
                check_func = getattr(self, rule.check_function)
                
                # 执行验证
                result = check_func(content, rule)
                results.append(result)
                
            except Exception as e:
                self.logger.error(f"验证规则 {rule_name} 执行失败: {e}")
                results.append(ValidationResult(
                    rule_name=rule_name,
                    passed=False,
                    score=0.0,
                    message=f"验证规则执行失败: {e}",
                    severity='critical'
                ))
        
        return results
    
    def validate_batch(self, content_list: List[ProcessedContent]) -> Dict[str, Any]:
        """批量验证内容"""
        batch_results = {
            'total_items': len(content_list),
            'individual_results': [],
            'summary': {},
            'quality_distribution': {},
            'failed_items': [],
            'warnings': []
        }
        
        all_validation_results = []
        
        # 逐项验证
        for i, content in enumerate(content_list):
            try:
                item_results = self.validate_single_item(content)
                
                # 计算单项质量分数
                item_score = self._calculate_item_quality_score(item_results)
                
                item_summary = {
                    'item_id': content.id,
                    'item_index': i,
                    'quality_score': item_score,
                    'validation_results': item_results,
                    'quality_level': self._determine_quality_level(item_score)
                }
                
                batch_results['individual_results'].append(item_summary)
                all_validation_results.extend(item_results)
                
                # 收集失败项
                critical_failures = [r for r in item_results if not r.passed and r.severity == 'critical']
                if critical_failures:
                    batch_results['failed_items'].append({
                        'item_id': content.id,
                        'failures': critical_failures
                    })
                
            except Exception as e:
                self.logger.error(f"验证第 {i} 项失败: {e}")
                batch_results['warnings'].append(f"Item {i} validation failed: {e}")
        
        # 生成批次汇总
        batch_results['summary'] = self._generate_batch_summary(
            batch_results['individual_results'],
            all_validation_results
        )
        
        # 质量分布统计
        batch_results['quality_distribution'] = self._calculate_quality_distribution(
            batch_results['individual_results']
        )
        
        return batch_results
    
    def validate_processed_data(self, processed_data_file: str) -> QualityReport:
        """验证处理后的数据文件"""
        try:
            # 加载处理后的数据
            with open(processed_data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 转换为ProcessedContent对象
            content_list = []
            for item_data in data:
                try:
                    content = ProcessedContent.from_dict(item_data)
                    content_list.append(content)
                except Exception as e:
                    self.logger.warning(f"跳过无效数据项: {e}")
            
            # 执行批量验证
            validation_results = self.validate_batch(content_list)
            
            # 生成质量报告
            quality_report = self._create_quality_report(
                processed_data_file,
                validation_results
            )
            
            return quality_report
            
        except Exception as e:
            self.logger.error(f"数据验证失败: {e}")
            raise
    
    # =============================================================================
    # 具体验证规则实现
    # =============================================================================
    
    def _check_min_text_length(self, content: ProcessedContent, rule: ValidationRule) -> ValidationResult:
        """检查最小文本长度"""
        text_length = len(content.content.strip())
        threshold = rule.threshold
        
        passed = text_length >= threshold
        score = min(1.0, text_length / threshold) if threshold > 0 else 1.0
        
        message = f"文本长度: {text_length}, 要求最小: {threshold}"
        if not passed:
            message += f" (不达标)"
        
        return ValidationResult(
            rule_name=rule.name,
            passed=passed,
            score=score,
            message=message,
            details={'actual_length': text_length, 'required_length': threshold},
            severity=rule.severity
        )
    
    def _check_max_text_length(self, content: ProcessedContent, rule: ValidationRule) -> ValidationResult:
        """检查最大文本长度"""
        text_length = len(content.content.strip())
        threshold = rule.threshold
        
        passed = text_length <= threshold
        score = 1.0 if passed else threshold / text_length
        
        message = f"文本长度: {text_length}, 限制最大: {threshold}"
        if not passed:
            message += f" (超标)"
        
        return ValidationResult(
            rule_name=rule.name,
            passed=passed,
            score=score,
            message=message,
            details={'actual_length': text_length, 'max_length': threshold},
            severity=rule.severity
        )
    
    def _check_chinese_content_ratio(self, content: ProcessedContent, rule: ValidationRule) -> ValidationResult:
        """检查中文内容比例"""
        text = content.content
        if not text:
            return ValidationResult(
                rule_name=rule.name,
                passed=False,
                score=0.0,
                message="空文本内容",
                severity=rule.severity
            )
        
        # 计算中文字符比例
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
        total_chars = len(text)
        chinese_ratio = chinese_chars / total_chars if total_chars > 0 else 0
        
        min_ratio = rule.parameters.get('min_ratio', 0.3)
        passed = chinese_ratio >= min_ratio
        score = min(1.0, chinese_ratio / min_ratio) if min_ratio > 0 else 1.0
        
        message = f"中文字符比例: {chinese_ratio:.2%}, 要求最小: {min_ratio:.2%}"
        
        return ValidationResult(
            rule_name=rule.name,
            passed=passed,
            score=score,
            message=message,
            details={
                'chinese_chars': chinese_chars,
                'total_chars': total_chars,
                'chinese_ratio': chinese_ratio
            },
            severity=rule.severity
        )
    
    def _check_encoding_quality(self, content: ProcessedContent, rule: ValidationRule) -> ValidationResult:
        """检查编码质量"""
        text = content.content
        if not text:
            return ValidationResult(
                rule_name=rule.name,
                passed=False,
                score=0.0,
                message="空文本内容",
                severity=rule.severity
            )
        
        # 检查乱码字符
        invalid_chars = 0
        replacement_chars = text.count('�')  # 替换字符
        control_chars = len(re.findall(r'[\x00-\x1f\x7f-\x9f]', text))  # 控制字符
        
        invalid_chars = replacement_chars + control_chars
        total_chars = len(text)
        quality_ratio = 1.0 - (invalid_chars / total_chars) if total_chars > 0 else 0
        
        threshold = rule.threshold
        passed = quality_ratio >= threshold
        score = quality_ratio
        
        message = f"编码质量: {quality_ratio:.2%}, 要求: {threshold:.2%}"
        if invalid_chars > 0:
            message += f" (发现 {invalid_chars} 个无效字符)"
        
        return ValidationResult(
            rule_name=rule.name,
            passed=passed,
            score=score,
            message=message,
            details={
                'invalid_chars': invalid_chars,
                'replacement_chars': replacement_chars,
                'control_chars': control_chars,
                'quality_ratio': quality_ratio
            },
            severity=rule.severity
        )
    
    def _check_required_fields(self, content: ProcessedContent, rule: ValidationResult) -> ValidationResult:
        """检查必填字段"""
        required_fields = rule.parameters.get('required_fields', [])
        missing_fields = []
        
        for field in required_fields:
            value = getattr(content, field, None)
            if value is None or (isinstance(value, str) and not value.strip()):
                missing_fields.append(field)
        
        passed = len(missing_fields) == 0
        score = 1.0 - (len(missing_fields) / len(required_fields)) if required_fields else 1.0
        
        if missing_fields:
            message = f"缺少必填字段: {', '.join(missing_fields)}"
        else:
            message = "所有必填字段完整"
        
        return ValidationResult(
            rule_name=rule.name,
            passed=passed,
            score=score,
            message=message,
            details={'missing_fields': missing_fields},
            severity=rule.severity
        )
    
    def _check_field_format(self, content: ProcessedContent, rule: ValidationRule) -> ValidationResult:
        """检查字段格式"""
        format_issues = []
        
        # 检查ID格式
        if not re.match(r'^[a-zA-Z0-9_-]+$', content.id):
            format_issues.append('ID格式不正确')
        
        # 检查内容类型
        if content.content_type not in ContentType:
            format_issues.append('内容类型无效')
        
        # 检查质量等级
        if content.quality_level not in QualityLevel:
            format_issues.append('质量等级无效')
        
        # 检查置信度分数
        if not (0 <= content.confidence_score <= 1):
            format_issues.append('置信度分数超出范围')
        
        passed = len(format_issues) == 0
        score = 1.0 if passed else 0.5  # 格式问题给0.5分
        
        message = "字段格式正确" if passed else f"格式问题: {'; '.join(format_issues)}"
        
        return ValidationResult(
            rule_name=rule.name,
            passed=passed,
            score=score,
            message=message,
            details={'format_issues': format_issues},
            severity=rule.severity
        )
    
    def _check_classification_confidence(self, content: ProcessedContent, rule: ValidationRule) -> ValidationResult:
        """检查分类置信度"""
        confidence = content.confidence_score
        threshold = rule.threshold
        
        passed = confidence >= threshold
        score = confidence
        
        message = f"分类置信度: {confidence:.2f}, 要求最小: {threshold:.2f}"
        
        return ValidationResult(
            rule_name=rule.name,
            passed=passed,
            score=score,
            message=message,
            details={'confidence': confidence, 'threshold': threshold},
            severity=rule.severity
        )
    
    def _check_category_consistency(self, content: ProcessedContent, rule: ValidationRule) -> ValidationResult:
        """检查分类一致性"""
        # 检查类别和子类别是否匹配
        category_mapping = {
            'hexagram': ['basic_info', 'judgment', 'image'],
            'yao': ['line_text', 'interpretation'],
            'annotation': ['classical', 'modern', 'commentary'],
            'divination': ['case_study', 'example', 'practice'],
            'judgment': ['formula', 'technique', 'method']
        }
        
        category = content.category
        subcategory = content.subcategory
        
        if category in category_mapping:
            valid_subcategories = category_mapping[category]
            passed = subcategory in valid_subcategories if subcategory else True
        else:
            passed = True  # 未知类别暂时通过
        
        score = 1.0 if passed else 0.7
        message = "分类一致" if passed else f"子类别 '{subcategory}' 与主类别 '{category}' 不匹配"
        
        return ValidationResult(
            rule_name=rule.name,
            passed=passed,
            score=score,
            message=message,
            details={'category': category, 'subcategory': subcategory},
            severity=rule.severity
        )
    
    def _check_hexagram_structure(self, content: ProcessedContent, rule: ValidationRule) -> ValidationResult:
        """验证64卦结构"""
        if content.content_type != ContentType.HEXAGRAM:
            return ValidationResult(
                rule_name=rule.name,
                passed=True,
                score=1.0,
                message="非卦象内容，跳过验证",
                severity=rule.severity
            )
        
        text = content.content
        issues = []
        
        # 检查是否包含卦名
        hexagram_names = ['乾', '坤', '屯', '蒙', '需', '讼', '师', '比']  # 部分卦名示例
        has_hexagram_name = any(name in text for name in hexagram_names)
        if not has_hexagram_name:
            issues.append('未发现卦名')
        
        # 检查是否包含卦象符号
        has_symbols = bool(re.search(r'[☰☱☲☳☴☵☶☷]', text))
        if not has_symbols:
            issues.append('未发现卦象符号')
        
        # 检查是否包含卦辞或爻辞关键词
        divination_keywords = ['吉', '凶', '悔', '吝', '无咎', '利', '不利']
        has_keywords = any(keyword in text for keyword in divination_keywords)
        if not has_keywords:
            issues.append('未发现占卜关键词')
        
        passed = len(issues) == 0
        score = 1.0 - (len(issues) * 0.3)  # 每个问题扣0.3分
        score = max(0, score)
        
        message = "卦象结构完整" if passed else f"结构问题: {'; '.join(issues)}"
        
        return ValidationResult(
            rule_name=rule.name,
            passed=passed,
            score=score,
            message=message,
            details={'issues': issues},
            severity=rule.severity
        )
    
    def _check_yao_structure(self, content: ProcessedContent, rule: ValidationRule) -> ValidationResult:
        """验证爻辞结构"""
        if content.content_type != ContentType.YAO:
            return ValidationResult(
                rule_name=rule.name,
                passed=True,
                score=1.0,
                message="非爻辞内容，跳过验证",
                severity=rule.severity
            )
        
        text = content.content
        issues = []
        
        # 检查爻位表示
        yao_positions = ['初', '二', '三', '四', '五', '上']
        has_position = any(pos in text for pos in yao_positions)
        if not has_position:
            issues.append('未发现爻位')
        
        # 检查阴阳标识
        yin_yang = ['九', '六']
        has_yin_yang = any(yy in text for yy in yin_yang)
        if not has_yin_yang:
            issues.append('未发现阴阳标识')
        
        passed = len(issues) == 0
        score = 1.0 - (len(issues) * 0.4)  # 每个问题扣0.4分
        score = max(0, score)
        
        message = "爻辞结构完整" if passed else f"结构问题: {'; '.join(issues)}"
        
        return ValidationResult(
            rule_name=rule.name,
            passed=passed,
            score=score,
            message=message,
            details={'issues': issues},
            severity=rule.severity
        )
    
    def _check_duplicate_content(self, content: ProcessedContent, rule: ValidationRule) -> ValidationResult:
        """检查重复内容（简化版，完整版需要与其他内容比较）"""
        text = content.content
        
        # 检查内部重复（重复句子）
        sentences = re.split(r'[。！？；]', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        if len(sentences) == 0:
            return ValidationResult(
                rule_name=rule.name,
                passed=True,
                score=1.0,
                message="文本为空，无法检测重复",
                severity=rule.severity
            )
        
        unique_sentences = set(sentences)
        duplicate_ratio = 1.0 - (len(unique_sentences) / len(sentences))
        
        threshold = 0.3  # 30%重复率阈值
        passed = duplicate_ratio <= threshold
        score = 1.0 - duplicate_ratio
        
        message = f"重复内容比例: {duplicate_ratio:.2%}"
        if not passed:
            message += " (超出阈值)"
        
        return ValidationResult(
            rule_name=rule.name,
            passed=passed,
            score=score,
            message=message,
            details={'duplicate_ratio': duplicate_ratio, 'threshold': threshold},
            severity=rule.severity
        )
    
    def _check_data_freshness(self, content: ProcessedContent, rule: ValidationRule) -> ValidationResult:
        """检查数据新鲜度"""
        max_age_days = rule.parameters.get('max_age_days', 30)
        
        now = datetime.now()
        data_age = (now - content.processed_at).days
        
        passed = data_age <= max_age_days
        score = max(0, 1.0 - (data_age / max_age_days)) if max_age_days > 0 else 1.0
        
        message = f"数据处理于 {data_age} 天前"
        if not passed:
            message += f" (超过 {max_age_days} 天限制)"
        
        return ValidationResult(
            rule_name=rule.name,
            passed=passed,
            score=score,
            message=message,
            details={'data_age_days': data_age, 'max_age_days': max_age_days},
            severity=rule.severity
        )
    
    # =============================================================================
    # 辅助方法
    # =============================================================================
    
    def _calculate_item_quality_score(self, validation_results: List[ValidationResult]) -> float:
        """计算单项质量分数"""
        if not validation_results:
            return 0.0
        
        # 按严重程度加权
        severity_weights = {
            'critical': 1.0,
            'major': 0.8,
            'minor': 0.5,
            'info': 0.2
        }
        
        weighted_scores = []
        for result in validation_results:
            weight = severity_weights.get(result.severity, 0.5)
            weighted_scores.append(result.score * weight)
        
        return sum(weighted_scores) / len(weighted_scores) if weighted_scores else 0.0
    
    def _determine_quality_level(self, score: float) -> QualityLevel:
        """根据分数确定质量等级"""
        if score >= 0.9:
            return QualityLevel.HIGH
        elif score >= 0.7:
            return QualityLevel.MEDIUM
        elif score >= 0.5:
            return QualityLevel.LOW
        else:
            return QualityLevel.INVALID
    
    def _generate_batch_summary(self, individual_results: List[Dict], all_validation_results: List[ValidationResult]) -> Dict[str, Any]:
        """生成批次汇总"""
        if not individual_results:
            return {}
        
        scores = [item['quality_score'] for item in individual_results]
        
        # 按规则汇总
        rule_summary = defaultdict(list)
        for result in all_validation_results:
            rule_summary[result.rule_name].append(result.score)
        
        rule_averages = {
            rule_name: statistics.mean(scores) 
            for rule_name, scores in rule_summary.items()
        }
        
        return {
            'total_items': len(individual_results),
            'average_quality_score': statistics.mean(scores),
            'median_quality_score': statistics.median(scores),
            'min_quality_score': min(scores),
            'max_quality_score': max(scores),
            'std_quality_score': statistics.stdev(scores) if len(scores) > 1 else 0,
            'rule_averages': rule_averages,
            'pass_rate_by_rule': {
                rule_name: sum(1 for r in all_validation_results if r.rule_name == rule_name and r.passed) / len([r for r in all_validation_results if r.rule_name == rule_name])
                for rule_name in rule_summary.keys()
            }
        }
    
    def _calculate_quality_distribution(self, individual_results: List[Dict]) -> Dict[str, int]:
        """计算质量分布"""
        distribution = Counter()
        
        for item in individual_results:
            quality_level = item.get('quality_level', QualityLevel.INVALID)
            if isinstance(quality_level, QualityLevel):
                distribution[quality_level.value] += 1
            else:
                distribution[str(quality_level)] += 1
        
        return dict(distribution)
    
    def _create_quality_report(self, data_file: str, validation_results: Dict[str, Any]) -> QualityReport:
        """创建质量报告"""
        summary = validation_results.get('summary', {})
        
        report = QualityReport(
            document_path=data_file,
            total_extractions=validation_results['total_items'],
            successful_extractions=validation_results['total_items'] - len(validation_results['failed_items']),
            failed_extractions=len(validation_results['failed_items']),
            average_confidence=summary.get('average_quality_score', 0.0),
            quality_distribution=validation_results.get('quality_distribution', {}),
            errors=[item['failures'] for item in validation_results['failed_items']],
            warnings=validation_results.get('warnings', []),
            processing_time=0.0  # 需要外部设置
        )
        
        return report