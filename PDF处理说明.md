# 📚 易学PDF批量处理工具

高效处理200+易学PDF文件，支持自动分类、内容提取和数据结构化。

## 🚀 快速开始

### 方式1: 一键启动 (推荐)
```bash
# Windows用户
双击运行 "一键提取PDF.bat"

# Linux/Mac用户
python quick_extract.py
```

### 方式2: 直接运行
```bash
# 安装依赖
python install_dependencies.py

# 运行处理(标准版)
python extract_pdfs.py

# 运行处理(进度条版)
python extract_pdfs_with_progress.py
```

## 📂 目录结构

```
/mnt/d/desktop/appp/
├── data/                          # 放置PDF文件的目录 (191个PDF)
├── structured_data/               # 输出目录
│   ├── structured_data/          # 主要结果文件
│   ├── categories/               # 按类别分组的结果
│   ├── raw_texts/               # 提取的原始文本
│   ├── cache/                   # 处理缓存(支持断点续传)
│   └── reports/                 # HTML报告
├── extract_pdfs.py              # 标准处理脚本
├── extract_pdfs_with_progress.py # 带进度条的处理脚本
├── analyze_results.py           # 结果分析脚本
└── 一键提取PDF.bat              # Windows一键启动
```

## 📊 功能特性

### 🔍 自动分类识别
- **六爻**: 六爻预测、卜易、增删卜易、火珠林等
- **梅花易数**: 梅花易数、观梅数、先后天数理
- **大六壬**: 六壬占卜、课传、神将、四课三传
- **紫微斗数**: 紫微命盘、宫位星曜、化忌化禄
- **奇门遁甲**: 奇门遁甲、九宫八门、三奇六仪
- **八字命理**: 四柱八字、十神、纳音、喜用神
- **其他类别**: 金口诀、太乙神数、河洛理数等

### 📖 内容提取
- **64卦信息**: 卦名、卦象、卦辞描述
- **384爻辞**: 初六、九二等爻位爻辞
- **注解内容**: 注、解、释、按、曰等各类注解
- **实战案例**: 例、案例、实例、占例、测例
- **关键词**: 易学术语、书名、人名自动提取
- **作者朝代**: 从文件名和内容自动识别

### ⚡ 高性能处理
- **多进程并行**: 默认4进程同时处理
- **断点续传**: 支持中断后继续处理
- **智能缓存**: 避免重复处理相同文件
- **进度显示**: 实时显示处理进度和状态
- **错误处理**: 完善的异常处理和日志记录

### 📈 结果分析
- **可视化报告**: 自动生成HTML统计报告
- **分类统计**: 按类别、优先级详细统计
- **内容统计**: 卦象、爻辞、注解、案例数量
- **交互式查询**: 支持类别搜索、关键词搜索
- **数据导出**: 支持JSON、Markdown格式导出

## 🎯 使用流程

### 1. 准备PDF文件
将易学PDF文件放入 `data/` 目录中

### 2. 运行处理
```bash
# 快速启动
python quick_extract.py

# 或者直接运行
python extract_pdfs_with_progress.py
```

### 3. 查看结果
处理完成后会生成：
- `structured_data/complete_results_YYYYMMDD_HHMMSS.json` - 完整结果
- `structured_data/statistics_YYYYMMDD_HHMMSS.json` - 统计信息  
- `reports/report_YYYYMMDD_HHMMSS.html` - 可视化报告
- `categories/` - 按类别保存的文件
- `processing_report_YYYYMMDD_HHMMSS.md` - 文本报告

### 4. 分析结果
```bash
python analyze_results.py
```

## 📋 输出格式示例

### JSON结果格式
```json
{
  "pdf_info": {
    "file_name": "王虎应-六爻预测宝典.pdf",
    "category": "六爻",
    "confidence": 0.85,
    "priority": 1,
    "pages": 156,
    "text_length": 125000
  },
  "content": {
    "hexagrams": [
      {
        "number": 1,
        "name": "乾",
        "description": "天行健，君子以自强不息"
      }
    ],
    "yao_ci": [
      {
        "position": "初",
        "type": "六",
        "full_name": "初六",
        "text": "潜龙勿用"
      }
    ],
    "annotations": [...],
    "cases": [...],
    "keywords": ["六爻", "卦象", "世应"],
    "author": "王虎应",
    "dynasty": null
  },
  "statistics": {
    "hexagram_count": 12,
    "yao_ci_count": 45,
    "annotation_count": 78,
    "case_count": 23
  }
}
```

## 🔧 高级配置

### 修改处理参数
编辑 `extract_pdfs_with_progress.py`:
```python
# 并发进程数 (根据CPU核心数调整)
results = processor.process_all_pdfs(max_workers=4)

# 最大处理页数 (避免超大文件)
max_pages = min(page_count, 200)
```

### 添加新的分类
在 `category_patterns` 中添加新类别:
```python
"新类别": {
    "keywords": ["关键词1", "关键词2"],
    "priority": 2,
    "patterns": [r"正则表达式1", r"正则表达式2"]
}
```

## 📊 处理统计

基于191个PDF文件的处理结果:
- **六爻类**: 约60-70个文件，优先级最高
- **周易基础**: 约30-40个文件，经典文献
- **大六壬**: 约15-25个文件，术数精品
- **紫微斗数**: 约15-20个文件
- **八字命理**: 约10-15个文件
- **其他类别**: 奇门遁甲、梅花易数等

## ⚠️ 注意事项

1. **内存使用**: 大文件可能占用较多内存
2. **处理时间**: 191个文件预计需要10-30分钟
3. **文件格式**: 仅支持PDF格式，不支持扫描版
4. **中文支持**: 完全支持中文内容提取和分析
5. **断点续传**: 中途中断可重新运行继续处理

## 🆘 故障排除

### 常见问题
1. **依赖安装失败**
   ```bash
   pip install --upgrade pip
   pip install pdfplumber tqdm pillow
   ```

2. **PDF文件无法读取**
   - 检查是否为扫描版PDF
   - 尝试其他PDF处理工具转换

3. **内存不足**
   - 减少 `max_workers` 参数
   - 限制 `max_pages` 处理页数

4. **中文乱码**
   - 确保系统支持UTF-8编码
   - 使用支持中文的文本编辑器查看结果

### 获取帮助
- 查看日志文件: `pdf_processing.log`
- 检查错误详情和处理进度
- 根据错误信息调整配置参数

## 🎉 处理完成后

1. **查看HTML报告** - 可视化统计和分析
2. **按类别研究** - 重点关注高优先级类别
3. **内容验证** - 抽查提取内容的准确性
4. **数据应用** - 用于知识库构建、搜索系统等

---

🔮 **易学PDF批量处理工具** - 让古籍数字化更简单高效！