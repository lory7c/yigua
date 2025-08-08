"""
数据模型定义
易学知识库数据结构
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum
import json
import hashlib


class ContentType(Enum):
    """内容类型枚举"""
    HEXAGRAM = "hexagram"          # 卦象
    YAO = "yao"                   # 爻辞
    ANNOTATION = "annotation"      # 注解
    DIVINATION = "divination"      # 占卜案例
    JUDGMENT = "judgment"          # 断语
    LIUYAO = "liuyao"             # 六爻
    OTHER = "other"               # 其他


class DataTier(Enum):
    """数据层级枚举"""
    CORE = "core"                 # 核心数据包
    EXTENDED = "extended"         # 扩展数据包
    CLOUD = "cloud"              # 云端数据


class QualityLevel(Enum):
    """数据质量等级"""
    HIGH = "high"                # 高质量
    MEDIUM = "medium"            # 中等质量
    LOW = "low"                  # 低质量
    INVALID = "invalid"          # 无效数据


@dataclass
class SourceDocument:
    """源文档信息"""
    file_path: str
    file_name: str
    file_size: int
    file_hash: str
    created_at: datetime
    modified_at: datetime
    mime_type: str = "application/pdf"
    
    def __post_init__(self):
        if isinstance(self.created_at, str):
            self.created_at = datetime.fromisoformat(self.created_at)
        if isinstance(self.modified_at, str):
            self.modified_at = datetime.fromisoformat(self.modified_at)


@dataclass
class TextExtraction:
    """文本提取结果"""
    source_doc: SourceDocument
    raw_text: str
    page_count: int
    extraction_method: str
    extraction_time: datetime
    confidence_score: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def text_length(self) -> int:
        return len(self.raw_text)
    
    @property
    def words_count(self) -> int:
        return len(self.raw_text.split())
    
    def get_text_hash(self) -> str:
        """获取文本内容哈希"""
        return hashlib.sha256(self.raw_text.encode()).hexdigest()


@dataclass
class ProcessedContent:
    """处理后的内容"""
    id: str
    title: str
    content: str
    content_type: ContentType
    source_document: str  # 源文档路径
    category: str
    quality_level: QualityLevel
    confidence_score: float
    validation_status: str
    
    # 可选字段
    page_number: Optional[int] = None
    subcategory: Optional[str] = None
    
    # 默认值字段
    tags: List[str] = field(default_factory=list)
    structured_data: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    processed_at: datetime = field(default_factory=datetime.now)
    data_tier: DataTier = DataTier.EXTENDED
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'id': self.id,
            'title': self.title,
            'content': self.content,
            'content_type': self.content_type.value,
            'source_document': self.source_document,
            'page_number': self.page_number,
            'category': self.category,
            'subcategory': self.subcategory,
            'tags': self.tags,
            'quality_level': self.quality_level.value,
            'confidence_score': self.confidence_score,
            'validation_status': self.validation_status,
            'structured_data': self.structured_data,
            'created_at': self.created_at.isoformat(),
            'processed_at': self.processed_at.isoformat(),
            'data_tier': self.data_tier.value
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ProcessedContent':
        """从字典创建实例"""
        return cls(
            id=data['id'],
            title=data['title'],
            content=data['content'],
            content_type=ContentType(data['content_type']),
            source_document=data['source_document'],
            page_number=data.get('page_number'),
            category=data['category'],
            subcategory=data.get('subcategory'),
            tags=data.get('tags', []),
            quality_level=QualityLevel(data['quality_level']),
            confidence_score=data['confidence_score'],
            validation_status=data['validation_status'],
            structured_data=data.get('structured_data', {}),
            created_at=datetime.fromisoformat(data['created_at']),
            processed_at=datetime.fromisoformat(data['processed_at']),
            data_tier=DataTier(data['data_tier'])
        )


@dataclass
class HexagramData:
    """64卦数据结构"""
    number: int                    # 卦序号 (1-64)
    name: str                     # 卦名
    chinese_name: str             # 中文卦名
    trigrams: Dict[str, str]      # 上下卦
    symbol: str                   # 卦象符号
    judgment: str                 # 卦辞
    image: str                    # 象辞
    
    # 爻辞数据
    lines: List[Dict[str, str]] = field(default_factory=list)
    
    # 注解数据
    annotations: List[str] = field(default_factory=list)
    
    # 占卜相关
    divination_meanings: List[str] = field(default_factory=list)
    
    # 元数据
    source_references: List[str] = field(default_factory=list)
    quality_score: float = 0.0


@dataclass
class YaoData:
    """爻辞数据结构"""
    hexagram_number: int          # 所属卦序号
    line_number: int              # 爻位 (1-6)
    line_type: str               # 爻性 (阴/阳)
    text: str                    # 爻辞内容
    interpretation: str          # 释义
    
    # 象义
    image_text: Optional[str] = None
    
    # 占断
    divination_meaning: Optional[str] = None
    
    # 来源信息
    source_document: Optional[str] = None
    confidence_score: float = 0.0


@dataclass
class DivinationCase:
    """占卜案例数据结构"""
    id: str
    title: str
    question: str                 # 所问事项
    hexagram_original: int        # 本卦
    analysis_process: str         # 解析过程
    judgment: str                 # 断语
    method: str                   # 占法 (六爻/梅花易数等)
    
    # 可选字段
    hexagram_changed: Optional[int] = None  # 变卦
    result: Optional[str] = None  # 结果验证
    author: Optional[str] = None  # 作者
    source: Optional[str] = None  # 来源
    case_date: Optional[datetime] = None
    
    # 默认值字段
    changing_lines: List[int] = field(default_factory=list)  # 变爻
    recorded_date: datetime = field(default_factory=datetime.now)


@dataclass
class KnowledgeGraph:
    """知识图谱节点"""
    id: str
    name: str
    type: str                     # 节点类型
    properties: Dict[str, Any] = field(default_factory=dict)
    relationships: List[Dict[str, Any]] = field(default_factory=list)
    
    def add_relationship(self, target_id: str, relation_type: str, properties: Dict[str, Any] = None):
        """添加关系"""
        relationship = {
            'target_id': target_id,
            'type': relation_type,
            'properties': properties or {}
        }
        self.relationships.append(relationship)


@dataclass
class QualityReport:
    """数据质量报告"""
    document_path: str
    total_extractions: int
    successful_extractions: int
    failed_extractions: int
    average_confidence: float
    quality_distribution: Dict[str, int]  # 各质量等级的数量
    processing_time: float
    
    # 默认值字段
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    generated_at: datetime = field(default_factory=datetime.now)
    
    @property
    def success_rate(self) -> float:
        """成功率计算"""
        if self.total_extractions == 0:
            return 0.0
        return self.successful_extractions / self.total_extractions * 100


@dataclass
class DataPackage:
    """数据包结构"""
    name: str
    version: str
    tier: DataTier
    size_mb: float
    content_count: int
    
    # 内容分布
    content_distribution: Dict[str, int] = field(default_factory=dict)
    
    # 质量统计
    quality_stats: Dict[str, int] = field(default_factory=dict)
    
    # 元数据
    created_at: datetime = field(default_factory=datetime.now)
    description: str = ""
    checksum: str = ""
    
    def calculate_checksum(self, content: bytes) -> str:
        """计算数据包校验和"""
        self.checksum = hashlib.sha256(content).hexdigest()
        return self.checksum