# 易学知识库 SQLite 数据库设计

## 概述

这是一个专为易学（I-Ching）知识存储和查询优化的高效SQLite数据库解决方案。系统采用分层数据架构，支持从5MB核心包到完整云端数据库的灵活部署。

## 🎯 设计目标

- **核心数据包 < 10MB** (实际目标 5MB)
- **查询性能优化** (核心查询 < 10ms)
- **全文搜索支持** (FTS5)
- **数据分层存储** (core/extended/cloud)
- **知识图谱关系** 支持

## 📁 文件结构

```
database/
├── schema.sql              # 完整数据库架构
├── indexes.sql             # 优化索引策略
├── data_import.py          # 数据导入脚本
├── query_optimization.sql  # 查询性能优化
├── compression_strategies.md # 数据压缩策略
└── README.md              # 本文档
```

## 🗄️ 核心表结构

### 主要数据表

1. **hexagrams** - 64卦主表
   - 基础信息：id, name, chinese_name, symbol
   - 结构信息：upper_trigram, lower_trigram, palace
   - 内容：judgment (卦辞), image (象辞)
   - 质量控制：data_tier, quality_score

2. **lines** - 384爻表 (64×6)
   - 爻位信息：hexagram_id, position, type
   - 内容：text (爻辞), image (小象辞)
   - 特殊标记：is_changing, strength

3. **interpretations** - 解释注解表
   - 目标关联：target_type, target_id
   - 分类：category (传统注解/现代解释/占断要诀)
   - 内容：title, content, author, source_book
   - 质量评估：quality_score, readability_score

4. **divination_cases** - 占卜案例表
   - 基础信息：title, question, method
   - 卦象信息：original_hexagram, changed_hexagram, changing_lines
   - 分析：analysis_process, judgment, result_verification
   - 元数据：difficulty_level, case_category, accuracy_rating

### 辅助表

5. **trigrams** - 八卦基础表
6. **tags** / **content_tags** - 标签系统
7. **knowledge_relationships** - 知识图谱关系
8. **source_documents** - 数据源管理
9. **learning_progress** - 学习进度跟踪

## 🔍 全文搜索 (FTS5)

### 搜索表设计

- **hexagrams_fts** - 卦象全文搜索
- **lines_fts** - 爻辞全文搜索  
- **interpretations_fts** - 解释全文搜索
- **cases_fts** - 案例全文搜索

### 搜索示例

```sql
-- 基础全文搜索
SELECT h.name, h.judgment 
FROM hexagrams h
JOIN hexagrams_fts ON h.id = hexagrams_fts.rowid
WHERE hexagrams_fts MATCH '天 AND 龙'
ORDER BY bm25(hexagrams_fts) DESC;

-- 多表联合搜索
SELECT 'hexagram' as type, h.name as title,
       snippet(hexagrams_fts, -1, '<mark>', '</mark>') as snippet
FROM hexagrams h
JOIN hexagrams_fts ON h.id = hexagrams_fts.rowid
WHERE hexagrams_fts MATCH '乾坤' AND h.data_tier <= 2

UNION ALL

SELECT 'interpretation' as type, i.title,
       snippet(interpretations_fts, -1, '<mark>', '</mark>') as snippet  
FROM interpretations i
JOIN interpretations_fts ON i.id = interpretations_fts.rowid
WHERE interpretations_fts MATCH '乾坤' AND i.data_tier <= 2
ORDER BY bm25() DESC;
```

## 📊 数据分层策略

### 三层架构

1. **Core Layer (data_tier = 1)**
   - 64卦基础数据 + 384爻辞
   - 高质量解释 (quality_score ≥ 0.9)
   - 精选案例 (accuracy_rating ≥ 0.8)
   - 目标大小: 5MB

2. **Extended Layer (data_tier = 2)** 
   - 包含core所有内容
   - 更多解释和注释
   - 完整案例库
   - 知识图谱关系
   - 目标大小: 50MB

3. **Cloud Layer (data_tier = 3)**
   - 完整历史文献
   - 所有提取数据
   - 用户生成内容
   - 无大小限制

### 分层查询视图

```sql
-- 核心数据视图
CREATE VIEW core_content AS
SELECT 'hexagram' as type, id, name as title FROM hexagrams WHERE data_tier = 1
UNION ALL  
SELECT 'interpretation' as type, id, title FROM interpretations WHERE data_tier = 1
UNION ALL
SELECT 'case' as type, id, title FROM divination_cases WHERE data_tier = 1;

-- 数据分布统计
SELECT * FROM data_statistics;
```

## ⚡ 性能优化

### 关键索引

```sql
-- 高频查询索引
CREATE INDEX idx_hexagrams_name ON hexagrams(name);
CREATE INDEX idx_hexagrams_tier_quality ON hexagrams(data_tier, quality_score DESC);
CREATE INDEX idx_lines_hexagram_position ON lines(hexagram_id, position);
CREATE INDEX idx_interpretations_target ON interpretations(target_type, target_id);

-- 复合查询索引
CREATE INDEX idx_case_method_difficulty ON divination_cases(method, difficulty_level, accuracy_rating DESC);

-- 部分索引 (节省空间)
CREATE INDEX idx_high_quality_interpretations ON interpretations(target_type, target_id, quality_score DESC) 
WHERE quality_score >= 0.8;
```

### 查询优化最佳实践

1. **使用索引字段**: WHERE条件优先使用有索引的字段
2. **避免SELECT \***: 明确指定需要的列
3. **JOIN优化**: 小表驱动大表，使用有索引的字段
4. **分页优化**: 使用游标分页替代OFFSET
5. **批量操作**: 使用事务包装，executemany()批量插入

## 🗜️ 数据压缩策略

### 数据库层面

```sql
-- 页面和存储优化
PRAGMA page_size = 4096;
PRAGMA auto_vacuum = INCREMENTAL;
VACUUM;
REINDEX;
```

### 应用层压缩

1. **文本去重**: 内容哈希去重，引用表存储
2. **内容归一化**: 统一标点、去除多余空白
3. **智能分层**: 基于质量评分自动分层
4. **延迟加载**: 按需加载详细内容
5. **GZIP压缩**: 大型文本字段压缩存储

## 🚀 快速开始

### 1. 创建数据库

```bash
# 执行数据库架构
sqlite3 yigua_knowledge.db < schema.sql

# 创建优化索引
sqlite3 yigua_knowledge.db < indexes.sql
```

### 2. 导入数据

```bash
# 使用Python导入脚本
python data_import.py

# 或者手动导入
sqlite3 yigua_knowledge.db
.mode csv
.import hexagrams.csv hexagrams
.import lines.csv lines
```

### 3. 性能测试

```sql
-- 查询执行计划分析
EXPLAIN QUERY PLAN 
SELECT h.name, l.text 
FROM hexagrams h 
LEFT JOIN lines l ON h.id = l.hexagram_id 
WHERE h.name = '乾';

-- 索引使用情况
SELECT name, tbl FROM sqlite_master WHERE type = 'index';

-- 数据库大小统计
SELECT page_count * page_size / (1024.0 * 1024.0) as size_mb 
FROM pragma_page_count(), pragma_page_size();
```

## 📈 性能基准

### 目标性能指标

- **卦名查找**: < 5ms
- **全文搜索**: < 50ms  
- **复杂关联查询**: < 100ms
- **批量导入**: 1000条/秒

### 实际测试结果

```sql
-- 性能测试查询
SELECT 'hexagram_lookup' as test,
       COUNT(*) as records,
       CAST((strftime('%s','now') - start_time) * 1000 as INTEGER) as ms
FROM (SELECT strftime('%s','now') as start_time), hexagrams 
WHERE name = '乾';
```

## 🔧 运维和维护

### 定期维护任务

```sql
-- 更新查询统计信息 (每周)
ANALYZE;

-- 清理数据库碎片 (每月)
VACUUM;

-- 重建索引 (数据大量变更后)
REINDEX;

-- 检查数据库完整性
PRAGMA integrity_check;
```

### 监控查询

```sql
-- 数据包大小监控
SELECT * FROM compression_stats;

-- 慢查询识别 (需要应用层配合)
SELECT query, avg_exec_time FROM query_log 
WHERE avg_exec_time > 100 
ORDER BY avg_exec_time DESC;
```

## 🌟 高级特性

### 知识图谱查询

```sql
-- 查找相关卦象 (2度关系)
WITH RECURSIVE related_hexagrams(hexagram_id, level, path) AS (
    SELECT 1 as hexagram_id, 0 as level, '1' as path
    UNION ALL
    SELECT kr.to_id, rh.level + 1, rh.path || ',' || kr.to_id
    FROM knowledge_relationships kr
    JOIN related_hexagrams rh ON kr.from_id = rh.hexagram_id
    WHERE kr.from_type = 1 AND kr.to_type = 1 
    AND rh.level < 2
    AND instr(rh.path, ',' || kr.to_id || ',') = 0
    AND kr.strength >= 0.5
)
SELECT h.name, rh.level
FROM related_hexagrams rh
JOIN hexagrams h ON rh.hexagram_id = h.id
WHERE rh.hexagram_id != 1
ORDER BY rh.level, h.name;
```

### 智能推荐

```sql
-- 基于学习进度的内容推荐
SELECT h.name, i.title, lp.mastery_level
FROM learning_progress lp
JOIN hexagrams h ON lp.content_id = h.id AND lp.content_type = 1
LEFT JOIN interpretations i ON i.target_id = h.id AND i.target_type = 1
WHERE lp.mastery_level < 3
ORDER BY lp.last_reviewed ASC, h.id ASC
LIMIT 10;
```

## 📄 许可和贡献

本项目专为易学知识库优化设计，遵循数据库最佳实践。

### 贡献指南

1. 性能优化建议
2. 新增查询模式
3. 数据压缩改进
4. 索引策略优化

## 📞 技术支持

对于数据库设计问题、性能调优建议或新功能需求，请参考：

- `query_optimization.sql` - 查询优化指南
- `compression_strategies.md` - 压缩策略详解
- SQLite官方文档和最佳实践

---

**数据库专家提醒**: 生产环境部署前，请务必进行充分的性能测试和数据备份。定期执行ANALYZE和VACUUM以维持最佳性能。