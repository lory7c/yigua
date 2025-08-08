# 智能文本处理引擎

专门用于处理易经、六爻、大六壬等古籍文档的智能文本处理系统。支持文本清洗、内容分类、信息抽取、质量检查等核心功能。

## 🚀 核心功能

### 1. 文本清洗引擎 (`text_cleaner.py`)
- **编码统一**：自动检测文件编码，统一转换为UTF-8
- **格式标准化**：清理OCR噪声，标准化标点符号和空格
- **繁简转换**：支持繁体字转简体字
- **多文本类型**：针对易经、六爻等不同文本类型优化
- **批量处理**：支持多进程并发处理
- **增量处理**：只处理修改过的文件

### 2. 智能分类器 (`content_classifier.py`)
- **内容识别**：自动识别卦象、爻辞、注解、案例等内容类型
- **上下文分析**：考虑位置和上下文进行智能分类
- **置信度评估**：为每个分类结果提供置信度分数
- **文档结构分析**：分析整个文档的结构组成
- **段落合并**：合并相邻的同类型内容段

### 3. 关键信息抽取 (`info_extractor.py`)
- **卦名识别**：抽取64卦名和八卦名
- **爻位分析**：识别爻名、爻辞、爻位信息
- **术语提取**：抽取易经术语、六爻术语、时间信息
- **结构化输出**：将抽取的信息组织成结构化数据
- **多种格式支持**：支持易经、六爻、一般文本等格式

### 4. 质量检查器 (`quality_checker.py`)
- **格式检查**：标点符号、空格、括号匹配等格式问题
- **内容逻辑**：检查内容的逻辑一致性和完整性
- **术语规范**：验证卦名、爻名等术语的正确性
- **编码质量**：检查字符编码和无效字符
- **质量评分**：提供综合质量分数和改进建议

## 📁 文件结构

```
/mnt/d/desktop/appp/data/
├── text_cleaner.py           # 文本清洗引擎
├── content_classifier.py     # 智能分类器
├── info_extractor.py        # 信息抽取模块
├── quality_checker.py       # 质量检查模块
├── main_processor.py        # 主处理器（CLI工具）
├── test_processing_engine.py # 集成测试脚本
├── structured_data/         # 结构化数据输出目录
└── README.md               # 使用说明
```

## 🛠️ 安装依赖

```bash
pip install chardet numpy
```

## 💻 使用方法

### 1. 命令行使用

#### 处理单个文件
```bash
python main_processor.py -i input_file.txt -o output_dir -t yijing
```

#### 批量处理
```bash
python main_processor.py -i input_dir -o output_dir -b --patterns "*.txt" "*.md"
```

#### 增量处理
```bash
python main_processor.py -i input_dir -o output_dir --incremental
```

#### 跳过质量检查
```bash
python main_processor.py -i input_file.txt -o output_dir --no-quality-check
```

### 2. 程序化使用

```python
from text_cleaner import TextCleaner
from content_classifier import ContentClassifier
from info_extractor import InfoExtractor
from quality_checker import QualityChecker

# 初始化模块
cleaner = TextCleaner()
classifier = ContentClassifier()
extractor = InfoExtractor()
checker = QualityChecker()

# 处理文本
text = "乾：元亨利贞。"

# 清洗文本
cleaned_text = cleaner.clean_yijing_text(text)

# 分类内容
results = classifier.classify_document(cleaned_text)

# 抽取信息
info = extractor.extract_structured_info(cleaned_text, 'yijing')

# 质量检查
quality_report = checker.check_quality(cleaned_text, 'yijing')
```

## 📊 性能指标

基于测试结果的性能指标：

- **文本清洗**: ~19M 字符/秒
- **内容分类**: ~1.3M 字符/秒  
- **信息抽取**: ~3.8M 字符/秒
- **质量检查**: ~0.9M 字符/秒
- **总体平均**: ~1.8M 字符/秒

## 🎯 支持的文本类型

### 易经文本 (yijing)
- 卦名、卦辞
- 彖辞、象辞、文言
- 爻名、爻辞
- 注释和疏解

### 六爻文本 (liuyao)
- 卦象排列
- 世应爻位
- 六亲关系
- 动爻变化
- 占断分析

### 一般文本 (general)
- 基础文本清洗
- 通用内容分类
- 基本信息抽取

## 📈 输出格式

### 处理结果JSON
```json
{
  "file_info": {
    "input_path": "文件路径",
    "file_name": "文件名",
    "text_type": "文本类型"
  },
  "processing_results": {
    "cleaned_text": "清洗后文本",
    "classification": {
      "segments": "分类段落",
      "structure_analysis": "结构分析"
    },
    "extracted_info": {
      "type": "信息类型",
      "data": "抽取数据"
    },
    "quality_report": {
      "overall_score": "质量分数",
      "issues": "问题列表",
      "recommendations": "改进建议"
    }
  }
}
```

## 🔧 配置选项

### TextCleaner 配置
- `max_workers`: 最大工作进程数
- `text_type`: 文本类型 ('yijing', 'liuyao', 'general')

### ContentClassifier 配置
- `segment_size`: 分段大小 (默认200字符)
- `overlap`: 重叠大小 (默认50字符)
- `min_confidence`: 最小置信度 (默认0.3)

### QualityChecker 配置
- `severity_weights`: 问题严重程度权重
- `check_categories`: 检查类别 (格式/内容/编码/逻辑)

## 🐛 常见问题

### 1. 编码问题
如果遇到中文乱码：
```python
# 手动指定编码
with open(file_path, 'r', encoding='gbk') as f:
    text = f.read()
```

### 2. 性能优化
对于大文件批量处理：
```bash
python main_processor.py -i input_dir -o output_dir -b -w 8  # 使用8个进程
```

### 3. 内存使用
处理大文件时可以调整段落大小：
```python
classifier.classify_document(text, segment_size=100, overlap=25)
```

## 📝 开发计划

- [x] 文本清洗引擎
- [x] 智能内容分类
- [x] 关键信息抽取
- [x] 质量评估验证
- [x] 命令行工具
- [x] 批量处理支持
- [ ] Web界面
- [ ] API服务
- [ ] 机器学习优化
- [ ] 更多文本类型支持

## 🤝 贡献

欢迎提交Issue和Pull Request来改进这个项目。

## 📄 许可证

本项目采用MIT许可证。