-- SQLite索引优化策略
-- 针对易学知识库的高频查询模式优化
-- 执行计划分析和性能基准测试

-- ==========================================
-- 核心性能索引 (Core Performance Indexes)
-- ==========================================

-- 1. 主键和外键索引 (自动创建，但显式声明便于管理)
-- hexagrams表主键索引 (SQLite自动创建)
-- CREATE UNIQUE INDEX idx_hexagrams_pk ON hexagrams(id);

-- 2. 高频查询索引

-- 2.1 卦象快速查找 (按名称、符号、序号)
CREATE UNIQUE INDEX idx_hexagrams_name ON hexagrams(name);
CREATE INDEX idx_hexagrams_symbol ON hexagrams(symbol);
CREATE INDEX idx_hexagrams_sequence_kingwen ON hexagrams(sequence_king_wen);
CREATE INDEX idx_hexagrams_binary ON hexagrams(binary_value);

-- 2.2 卦宫分组查询优化
CREATE INDEX idx_hexagrams_palace ON hexagrams(palace);
CREATE INDEX idx_hexagrams_trigrams ON hexagrams(upper_trigram, lower_trigram);

-- 2.3 数据层级过滤 (核心优化)
CREATE INDEX idx_hexagrams_tier_quality ON hexagrams(data_tier, quality_score DESC);
CREATE INDEX idx_lines_tier ON lines(data_tier);
CREATE INDEX idx_interpretations_tier ON interpretations(data_tier, quality_score DESC);
CREATE INDEX idx_cases_tier ON divination_cases(data_tier, accuracy_rating DESC);

-- ==========================================
-- 关系型查询索引
-- ==========================================

-- 3. 爻辞查询优化
CREATE INDEX idx_lines_hexagram_position ON lines(hexagram_id, position);
CREATE INDEX idx_lines_type ON lines(type); -- 阴爻/阳爻筛选
CREATE INDEX idx_lines_changing ON lines(is_changing) WHERE is_changing = 1; -- 部分索引，仅变爻

-- 4. 解释注解查询
CREATE INDEX idx_interpretations_target ON interpretations(target_type, target_id);
CREATE INDEX idx_interpretations_category ON interpretations(category);
CREATE INDEX idx_interpretations_author ON interpretations(author) WHERE author IS NOT NULL;
CREATE INDEX idx_interpretations_content_length ON interpretations(content_length DESC); -- 按内容长度排序

-- 5. 占卜案例查询优化
CREATE INDEX idx_cases_hexagram ON divination_cases(original_hexagram, changed_hexagram);
CREATE INDEX idx_cases_method ON divination_cases(method);
CREATE INDEX idx_cases_category ON divination_cases(case_category);
CREATE INDEX idx_cases_difficulty ON divination_cases(difficulty_level);
CREATE INDEX idx_cases_time ON divination_cases(divination_time DESC); -- 时间序列查询

-- 6. 标签系统索引
CREATE INDEX idx_tags_category ON tags(category, usage_count DESC);
CREATE INDEX idx_content_tags_lookup ON content_tags(content_type, content_id);
CREATE INDEX idx_content_tags_reverse ON content_tags(tag_id, content_type);

-- ==========================================
-- 知识图谱和关系查询索引
-- ==========================================

-- 7. 知识图谱关系索引
CREATE INDEX idx_relationships_from ON knowledge_relationships(from_type, from_id);
CREATE INDEX idx_relationships_to ON knowledge_relationships(to_type, to_id);
CREATE INDEX idx_relationships_type_strength ON knowledge_relationships(relationship_type, strength DESC);

-- 8. 复合查询索引
-- 基于实际查询模式优化的组合索引
CREATE INDEX idx_hexagram_palace_tier ON hexagrams(palace, data_tier, quality_score DESC);
CREATE INDEX idx_case_method_difficulty ON divination_cases(method, difficulty_level, accuracy_rating DESC);

-- ==========================================
-- 时间序列和统计索引
-- ==========================================

-- 9. 时间戳索引 (用于数据同步和增量更新)
CREATE INDEX idx_hexagrams_updated ON hexagrams(updated_at DESC);
CREATE INDEX idx_interpretations_created ON interpretations(created_at DESC);
CREATE INDEX idx_cases_created ON divination_cases(created_at DESC);

-- 10. 学习进度跟踪索引
CREATE INDEX idx_progress_content ON learning_progress(content_type, content_id);
CREATE INDEX idx_progress_reviewed ON learning_progress(last_reviewed DESC) WHERE last_reviewed IS NOT NULL;
CREATE INDEX idx_progress_mastery ON learning_progress(mastery_level DESC, review_count DESC);

-- ==========================================
-- 数据源文档索引
-- ==========================================

-- 11. 文档处理状态索引
CREATE INDEX idx_documents_status ON source_documents(processing_status, quality_score DESC);
CREATE INDEX idx_documents_hash ON source_documents(file_hash); -- 去重检查
CREATE INDEX idx_documents_size ON source_documents(file_size DESC); -- 文件大小排序

-- ==========================================
-- 性能监控和统计索引
-- ==========================================

-- 12. 统计查询优化索引
-- 用于数据包大小估算和质量评估的快速聚合
CREATE INDEX idx_hexagrams_stats ON hexagrams(data_tier, quality_score);
CREATE INDEX idx_interpretations_stats ON interpretations(data_tier, quality_score, content_length);

-- ==========================================
-- 部分索引 (Partial Indexes) - 节省空间
-- ==========================================

-- 13. 条件索引 - 仅为高质量内容建立索引
CREATE INDEX idx_high_quality_interpretations ON interpretations(target_type, target_id, quality_score DESC) 
    WHERE quality_score >= 0.8;

CREATE INDEX idx_verified_cases ON divination_cases(original_hexagram, method, accuracy_rating DESC)
    WHERE result_verification IS NOT NULL AND accuracy_rating >= 0.7;

-- 14. 错误和异常数据索引
CREATE INDEX idx_low_quality_content ON interpretations(id, quality_score) 
    WHERE quality_score < 0.5; -- 用于数据清理

-- ==========================================
-- 查询性能分析视图
-- ==========================================

-- 索引使用情况统计视图
CREATE VIEW index_usage_stats AS
SELECT 
    name,
    tbl,
    rootpage,
    sql
FROM sqlite_master 
WHERE type = 'index' 
AND name NOT LIKE 'sqlite_%'
ORDER BY tbl, name;

-- ==========================================
-- 索引维护和优化建议
-- ==========================================

-- 性能测试查询 (用于EXPLAIN QUERY PLAN分析)
-- 测试1: 按卦名查找及其爻辞
-- SELECT h.*, l.* FROM hexagrams h LEFT JOIN lines l ON h.id = l.hexagram_id WHERE h.name = '乾';

-- 测试2: 全文搜索 + 数据层级过滤
-- SELECT * FROM hexagrams WHERE id IN (SELECT rowid FROM hexagrams_fts WHERE hexagrams_fts MATCH '天*') AND data_tier <= 2;

-- 测试3: 复杂关联查询 (案例 + 卦象 + 解释)
-- SELECT c.title, h.name, i.content FROM divination_cases c 
-- JOIN hexagrams h ON c.original_hexagram = h.id 
-- LEFT JOIN interpretations i ON i.target_type = 1 AND i.target_id = h.id 
-- WHERE c.method = 1 AND c.data_tier <= 2;

-- 索引大小估算查询
-- SELECT name, pgsize * pgno as size_bytes FROM dbstat WHERE name LIKE 'idx_%' ORDER BY size_bytes DESC;

-- ANALYZE命令 - 更新索引统计信息 (应定期执行)
ANALYZE;

-- 索引重建建议 (数据大量变更后)
-- REINDEX;

-- ==========================================
-- 性能优化建议和最佳实践
-- ==========================================

/*
索引优化原则:
1. 高选择性字段优先建索引 (name, symbol, binary_value等)
2. 复合索引字段顺序: 等值查询 > 范围查询 > 排序字段
3. 部分索引用于节省空间，仅为常用数据建索引
4. 避免过多索引，影响写入性能
5. 定期ANALYZE更新统计信息
6. 监控查询执行计划，识别missing indexes

查询优化最佳实践:
1. 使用EXPLAIN QUERY PLAN分析查询执行计划
2. 避免SELECT * ，明确指定需要的列
3. 合理使用LIMIT限制结果集大小
4. WHERE条件中使用索引字段
5. JOIN操作优先使用有索引的字段
6. 批量操作使用事务包装

存储优化策略:
1. 使用INTEGER主键 (ROWID别名)
2. TEXT字段设置合理长度限制
3. 使用BLOB存储二进制数据
4. 定期VACUUM回收空间
5. 启用压缩 (application level)

内存和缓存优化:
- PRAGMA cache_size = -64000 (64MB)
- PRAGMA temp_store = memory
- PRAGMA mmap_size = 268435456 (256MB)
*/