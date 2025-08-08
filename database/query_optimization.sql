-- SQLite查询性能优化指南
-- 针对易学知识库的高频查询模式优化
-- 包含执行计划分析和性能基准测试

-- ==========================================
-- 查询性能分析工具
-- ==========================================

-- 1. 查询执行计划分析函数
-- 使用方法: .mode column 然后执行 EXPLAIN QUERY PLAN

-- 示例查询执行计划分析
.mode column
.headers on
.width 10 60 10 10

-- ==========================================
-- 高频查询优化模式
-- ==========================================

-- 2. 卦象快速查询优化
-- 场景1: 按卦名查找 (最高频)
-- 优化前查询
SELECT h.*, l.position, l.text, l.image 
FROM hexagrams h 
LEFT JOIN lines l ON h.id = l.hexagram_id 
WHERE h.name = '乾';

-- 执行计划分析
EXPLAIN QUERY PLAN 
SELECT h.*, l.position, l.text, l.image 
FROM hexagrams h 
LEFT JOIN lines l ON h.id = l.hexagram_id 
WHERE h.name = '乾';

-- 优化后查询 (使用索引提示)
SELECT /*+ INDEX(h, idx_hexagrams_name) */ 
       h.*, l.position, l.text, l.image 
FROM hexagrams h 
LEFT JOIN lines l ON h.id = l.hexagram_id 
WHERE h.name = '乾'
ORDER BY l.position;

-- 场景2: 全文搜索 + 数据层级过滤
-- 优化前 (效率低)
SELECT h.* FROM hexagrams h 
WHERE (h.judgment LIKE '%天%' OR h.image LIKE '%天%') 
AND h.data_tier <= 2;

-- 优化后 (使用FTS5)
SELECT h.* 
FROM hexagrams h 
JOIN hexagrams_fts fts ON h.id = fts.rowid 
WHERE hexagrams_fts MATCH '天*' 
AND h.data_tier <= 2;

EXPLAIN QUERY PLAN 
SELECT h.* 
FROM hexagrams h 
JOIN hexagrams_fts fts ON h.id = fts.rowid 
WHERE hexagrams_fts MATCH '天*' 
AND h.data_tier <= 2;

-- ==========================================
-- 复杂查询优化
-- ==========================================

-- 3. 多表关联查询优化
-- 场景: 案例分析 + 卦象解释
-- 优化前 (子查询效率低)
SELECT c.title, c.question, c.judgment,
       h.name, h.judgment as hex_judgment,
       (SELECT content FROM interpretations i 
        WHERE i.target_type = 1 AND i.target_id = h.id 
        AND i.quality_score >= 0.8 LIMIT 1) as interpretation
FROM divination_cases c
JOIN hexagrams h ON c.original_hexagram = h.id
WHERE c.data_tier <= 2
ORDER BY c.created_at DESC
LIMIT 20;

-- 优化后 (LEFT JOIN + 窗口函数)
WITH ranked_interpretations AS (
    SELECT target_id, content, quality_score,
           ROW_NUMBER() OVER (PARTITION BY target_id ORDER BY quality_score DESC) as rn
    FROM interpretations 
    WHERE target_type = 1 AND quality_score >= 0.8
)
SELECT c.title, c.question, c.judgment,
       h.name, h.judgment as hex_judgment,
       ri.content as interpretation
FROM divination_cases c
JOIN hexagrams h ON c.original_hexagram = h.id
LEFT JOIN ranked_interpretations ri ON h.id = ri.target_id AND ri.rn = 1
WHERE c.data_tier <= 2
ORDER BY c.created_at DESC
LIMIT 20;

-- 执行计划对比
EXPLAIN QUERY PLAN 
WITH ranked_interpretations AS (
    SELECT target_id, content, quality_score,
           ROW_NUMBER() OVER (PARTITION BY target_id ORDER BY quality_score DESC) as rn
    FROM interpretations 
    WHERE target_type = 1 AND quality_score >= 0.8
)
SELECT c.title, h.name, ri.content
FROM divination_cases c
JOIN hexagrams h ON c.original_hexagram = h.id
LEFT JOIN ranked_interpretations ri ON h.id = ri.target_id AND ri.rn = 1
WHERE c.data_tier <= 2
LIMIT 20;

-- ==========================================
-- 聚合查询优化
-- ==========================================

-- 4. 统计查询优化
-- 场景: 数据包大小统计
-- 优化前 (多次扫描)
SELECT 
    (SELECT COUNT(*) FROM hexagrams WHERE data_tier = 1) as core_hexagrams,
    (SELECT COUNT(*) FROM hexagrams WHERE data_tier = 2) as extended_hexagrams,
    (SELECT COUNT(*) FROM lines WHERE data_tier = 1) as core_lines,
    (SELECT COUNT(*) FROM interpretations WHERE data_tier = 1) as core_interpretations;

-- 优化后 (单次扫描 + CASE WHEN)
SELECT 
    SUM(CASE WHEN table_name = 'hexagrams' AND data_tier = 1 THEN cnt ELSE 0 END) as core_hexagrams,
    SUM(CASE WHEN table_name = 'hexagrams' AND data_tier = 2 THEN cnt ELSE 0 END) as extended_hexagrams,
    SUM(CASE WHEN table_name = 'lines' AND data_tier = 1 THEN cnt ELSE 0 END) as core_lines,
    SUM(CASE WHEN table_name = 'interpretations' AND data_tier = 1 THEN cnt ELSE 0 END) as core_interpretations
FROM (
    SELECT 'hexagrams' as table_name, data_tier, COUNT(*) as cnt FROM hexagrams GROUP BY data_tier
    UNION ALL
    SELECT 'lines' as table_name, data_tier, COUNT(*) as cnt FROM lines GROUP BY data_tier  
    UNION ALL
    SELECT 'interpretations' as table_name, data_tier, COUNT(*) as cnt FROM interpretations GROUP BY data_tier
) stats;

-- ==========================================
-- 范围查询优化
-- ==========================================

-- 5. 时间范围查询
-- 场景: 最近添加的内容
-- 优化前 (全表扫描)
SELECT * FROM divination_cases 
WHERE created_at > strftime('%s', 'now', '-7 days')
ORDER BY created_at DESC;

-- 优化后 (使用时间戳索引)
SELECT * FROM divination_cases 
WHERE created_at > (strftime('%s', 'now') - 7*24*3600)
ORDER BY created_at DESC
LIMIT 50;

-- 执行计划分析
EXPLAIN QUERY PLAN 
SELECT * FROM divination_cases 
WHERE created_at > (strftime('%s', 'now') - 7*24*3600)
ORDER BY created_at DESC
LIMIT 50;

-- ==========================================
-- 分页查询优化
-- ==========================================

-- 6. 高效分页实现
-- 场景: 解释内容分页浏览
-- 避免 OFFSET (效率低)
-- SELECT * FROM interpretations ORDER BY id LIMIT 20 OFFSET 1000;

-- 优化: 使用游标分页
-- 第一页
SELECT * FROM interpretations 
WHERE data_tier <= 2 
ORDER BY id 
LIMIT 21; -- 多取1条用于判断是否有下一页

-- 后续页 (假设上一页最后一条记录的id是100)
SELECT * FROM interpretations 
WHERE data_tier <= 2 AND id > 100
ORDER BY id 
LIMIT 21;

-- ==========================================
-- 知识图谱查询优化  
-- ==========================================

-- 7. 关系查询优化
-- 场景: 查找相关卦象 (2度关系)
-- 优化前 (递归CTE，可能很慢)
WITH RECURSIVE related_hexagrams(hexagram_id, level) AS (
    SELECT 1 as hexagram_id, 0 as level
    UNION ALL
    SELECT kr.to_id, rh.level + 1
    FROM knowledge_relationships kr
    JOIN related_hexagrams rh ON kr.from_id = rh.hexagram_id
    WHERE kr.from_type = 1 AND kr.to_type = 1 AND rh.level < 2
)
SELECT DISTINCT h.name, rh.level
FROM related_hexagrams rh
JOIN hexagrams h ON rh.hexagram_id = h.id
ORDER BY rh.level, h.name;

-- 优化后 (限制递归深度，添加循环检测)
WITH RECURSIVE related_hexagrams(hexagram_id, level, path) AS (
    SELECT 1 as hexagram_id, 0 as level, '1' as path
    UNION ALL
    SELECT kr.to_id, rh.level + 1, rh.path || ',' || kr.to_id
    FROM knowledge_relationships kr
    JOIN related_hexagrams rh ON kr.from_id = rh.hexagram_id
    WHERE kr.from_type = 1 AND kr.to_type = 1 
    AND rh.level < 2
    AND instr(rh.path, ',' || kr.to_id || ',') = 0  -- 避免循环
    AND kr.strength >= 0.5  -- 只考虑强关系
)
SELECT DISTINCT h.name, rh.level, kr.relationship_type
FROM related_hexagrams rh
JOIN hexagrams h ON rh.hexagram_id = h.id
LEFT JOIN knowledge_relationships kr ON kr.to_id = rh.hexagram_id
WHERE rh.hexagram_id != 1  -- 排除起始节点
ORDER BY rh.level, kr.strength DESC, h.name
LIMIT 20;

-- ==========================================
-- 批量操作优化
-- ==========================================

-- 8. 批量插入优化
-- 使用事务包装批量操作
BEGIN TRANSACTION;

-- 准备语句 (在Python中使用executemany)
INSERT INTO interpretations (target_type, target_id, title, content, data_tier, quality_score)
VALUES (?, ?, ?, ?, ?, ?);

COMMIT;

-- 9. 批量更新优化
-- 场景: 质量评分重新计算
-- 使用临时表进行批量更新
CREATE TEMP TABLE quality_updates (
    id INTEGER PRIMARY KEY,
    new_score REAL
);

-- 插入计算结果到临时表
INSERT INTO quality_updates (id, new_score)
SELECT id, 
       CASE 
           WHEN length(content) > 500 THEN 0.9
           WHEN length(content) > 200 THEN 0.7
           ELSE 0.5
       END as new_score
FROM interpretations;

-- 批量更新主表
UPDATE interpretations 
SET quality_score = (SELECT new_score FROM quality_updates WHERE quality_updates.id = interpretations.id),
    updated_at = strftime('%s', 'now')
WHERE id IN (SELECT id FROM quality_updates);

DROP TABLE quality_updates;

-- ==========================================
-- 全文搜索优化
-- ==========================================

-- 10. FTS5高级搜索优化
-- 基础全文搜索
SELECT h.name, h.judgment,
       snippet(hexagrams_fts, 1, '<mark>', '</mark>', '...', 32) as highlighted
FROM hexagrams h
JOIN hexagrams_fts ON h.id = hexagrams_fts.rowid
WHERE hexagrams_fts MATCH '天 AND 龙'
ORDER BY bm25(hexagrams_fts) DESC
LIMIT 10;

-- 多表联合搜索
SELECT 
    'hexagram' as type, h.id, h.name as title,
    snippet(hexagrams_fts, -1, '<mark>', '</mark>', '...', 32) as snippet,
    bm25(hexagrams_fts) as relevance
FROM hexagrams h
JOIN hexagrams_fts ON h.id = hexagrams_fts.rowid
WHERE hexagrams_fts MATCH '乾坤' AND h.data_tier <= 2

UNION ALL

SELECT 
    'interpretation' as type, i.id, i.title,
    snippet(interpretations_fts, -1, '<mark>', '</mark>', '...', 32) as snippet,
    bm25(interpretations_fts) as relevance
FROM interpretations i
JOIN interpretations_fts ON i.id = interpretations_fts.rowid
WHERE interpretations_fts MATCH '乾坤' AND i.data_tier <= 2

ORDER BY relevance DESC
LIMIT 20;

-- ==========================================
-- 性能监控查询
-- ==========================================

-- 11. 索引使用情况分析
-- 检查未使用的索引
SELECT name, tbl, sql 
FROM sqlite_master 
WHERE type = 'index' 
AND name NOT IN (
    SELECT DISTINCT index_name 
    FROM sqlite_stat1 
    WHERE index_name IS NOT NULL
)
AND name NOT LIKE 'sqlite_%';

-- 检查表和索引大小
SELECT name, 
       SUM(pgsize) as size_bytes,
       COUNT(*) as page_count
FROM dbstat 
WHERE aggregate = true
GROUP BY name
ORDER BY size_bytes DESC;

-- 12. 查询性能基准测试
-- 创建性能测试视图
CREATE VIEW performance_benchmark AS
SELECT 
    'hexagram_name_lookup' as test_name,
    (SELECT COUNT(*) FROM hexagrams WHERE name = '乾') as result_count,
    0 as exec_time_ms; -- 需要在应用层测量

-- 13. 慢查询识别
-- 在应用中启用查询日志，识别执行时间>100ms的查询
-- PRAGMA compile_options; -- 检查是否启用了SQLITE_ENABLE_STMT_SCANSTATUS

-- ==========================================
-- 查询优化最佳实践总结
-- ==========================================

/*
1. 索引优化策略:
   - 高选择性字段建单列索引 (name, symbol等)
   - 常用组合查询建复合索引 (data_tier + quality_score)
   - WHERE条件中的字段优先建索引
   - 避免函数调用在WHERE条件中 (使用预计算字段)

2. JOIN优化:
   - 小表驱动大表
   - 使用EXISTS替代IN (当子查询返回大量结果时)
   - 避免笛卡尔积 (确保JOIN条件完整)
   - 考虑使用LEFT JOIN替代子查询

3. 全文搜索优化:
   - 使用FTS5而非LIKE匹配
   - 合理使用搜索运算符 (*, AND, OR, NEAR)
   - 利用BM25评分排序
   - 考虑使用snippet()函数高亮显示

4. 分页优化:
   - 使用游标分页替代OFFSET
   - LIMIT配合ORDER BY使用索引
   - 避免COUNT(*)用于分页计算

5. 聚合查询优化:
   - 尽量在单次扫描中完成多个统计
   - 使用GROUP BY替代多个子查询
   - 考虑使用物化视图存储预计算结果

6. 数据层级查询优化:
   - data_tier字段建索引
   - 使用视图简化常用查询
   - 批量操作考虑分层处理

7. 内存和缓存优化:
   - 合理设置cache_size
   - 使用TEMP表存储中间结果
   - 启用WAL模式提高并发性能

8. 监控和维护:
   - 定期ANALYZE更新统计信息
   - 监控慢查询日志
   - 定期VACUUM回收空间
   - 检查索引使用情况
*/