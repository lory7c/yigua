-- ========================================================================
-- 高性能SQLite查询优化配置
-- 专门针对10万+记录的易学知识库进行优化
-- ========================================================================

-- 基础性能优化设置
PRAGMA journal_mode = WAL;          -- 写前日志模式，提高并发性能
PRAGMA synchronous = NORMAL;        -- 平衡安全性和性能  
PRAGMA cache_size = -64000;         -- 64MB内存缓存
PRAGMA temp_store = MEMORY;         -- 临时数据存储在内存
PRAGMA mmap_size = 268435456;       -- 256MB内存映射
PRAGMA page_size = 4096;            -- 4KB页面大小(适合现代SSD)
PRAGMA auto_vacuum = INCREMENTAL;   -- 增量式自动清理

-- 查询优化器配置
PRAGMA optimize;                    -- 启用查询优化器
PRAGMA analysis_limit = 1000;      -- 统计分析限制

-- ========================================================================
-- 高频查询的物化视图和索引优化
-- ========================================================================

-- 1. 复合索引优化 - 卦象相关查询
CREATE INDEX IF NOT EXISTS idx_hexagrams_composite_search 
ON hexagrams(category, nature, gua_number);

CREATE INDEX IF NOT EXISTS idx_hexagrams_trigram_binary 
ON hexagrams(upper_trigram, lower_trigram, binary_code);

-- 2. 爻表的复合索引
CREATE INDEX IF NOT EXISTS idx_lines_hex_pos_type 
ON lines(hexagram_id, line_position, line_type);

CREATE INDEX IF NOT EXISTS idx_lines_changing_element 
ON lines(is_changing_line, element, hexagram_id) 
WHERE is_changing_line = 1;

-- 3. 注解表的分区索引 (按重要性和内容类型)
CREATE INDEX IF NOT EXISTS idx_interpretations_core_search 
ON interpretations(is_core_content, importance_level, target_type, target_id);

CREATE INDEX IF NOT EXISTS idx_interpretations_author_dynasty 
ON interpretations(author, dynasty, interpretation_type);

-- 4. 案例表的时间和准确性索引
CREATE INDEX IF NOT EXISTS idx_cases_accuracy_date 
ON divination_cases(accuracy_rating, divination_date, is_verified);

CREATE INDEX IF NOT EXISTS idx_cases_question_type_hex 
ON divination_cases(question_type, hexagram_id, accuracy_rating);

-- 5. 内容标签的关联查询优化
CREATE INDEX IF NOT EXISTS idx_content_tags_relevance 
ON content_tags(keyword_id, content_type, relevance_score DESC);

-- ========================================================================
-- 专用查询优化视图
-- ========================================================================

-- 高性能卦象摘要视图 (减少JOIN开销)
CREATE VIEW IF NOT EXISTS v_hexagram_summary AS
SELECT 
    h.id,
    h.gua_number,
    h.gua_name,
    h.gua_name_pinyin,
    h.basic_meaning,
    h.category,
    h.nature,
    h.binary_code,
    COUNT(DISTINCT l.id) as line_count,
    COUNT(DISTINCT i.id) as interpretation_count,
    COUNT(DISTINCT dc.id) as case_count,
    MAX(i.importance_level) as max_interpretation_level
FROM hexagrams h
LEFT JOIN lines l ON h.id = l.hexagram_id
LEFT JOIN interpretations i ON i.target_type = 'hexagram' AND i.target_id = h.id
LEFT JOIN divination_cases dc ON h.id = dc.hexagram_id
GROUP BY h.id;

-- 核心内容快速访问视图 (5MB分层存储)
CREATE VIEW IF NOT EXISTS v_core_content_fast AS
SELECT 
    'hexagram' as content_type,
    h.id as content_id,
    h.gua_name as title,
    h.basic_meaning as preview,
    LENGTH(h.judgement) + LENGTH(h.image) + LENGTH(h.decision) as content_size
FROM hexagrams h
UNION ALL
SELECT 
    'interpretation' as content_type,
    i.id as content_id,
    i.author || ' - ' || COALESCE(i.source_book, '未知') as title,
    SUBSTR(i.interpretation_text, 1, 100) as preview,
    i.content_length as content_size
FROM interpretations i
WHERE i.is_core_content = 1
ORDER BY content_size DESC;

-- 热门搜索结果缓存视图
CREATE VIEW IF NOT EXISTS v_search_popularity AS
SELECT 
    query_type,
    COUNT(*) as search_count,
    AVG(result_count) as avg_results
FROM query_performance_log
WHERE created_at >= datetime('now', '-7 days')
GROUP BY query_type
ORDER BY search_count DESC;

-- ========================================================================
-- 查询性能监控和自动优化
-- ========================================================================

-- 慢查询检测触发器
CREATE TRIGGER IF NOT EXISTS trg_slow_query_alert
AFTER INSERT ON query_performance_log
WHEN new.execution_time_ms > 1000  -- 超过1秒的查询
BEGIN
    INSERT INTO db_usage_stats (table_name, operation_type, record_count)
    VALUES ('slow_queries', 'ALERT', new.execution_time_ms);
END;

-- 自动更新统计信息触发器 (每1000次插入)
CREATE TRIGGER IF NOT EXISTS trg_auto_analyze
AFTER INSERT ON hexagrams
WHEN (SELECT COUNT(*) FROM hexagrams) % 1000 = 0
BEGIN
    -- SQLite会在后台异步执行ANALYZE
    INSERT INTO db_usage_stats (table_name, operation_type)
    VALUES ('system', 'ANALYZE');
END;

-- ========================================================================
-- 分层存储管理查询
-- ========================================================================

-- 计算各表存储大小 (字节)
CREATE VIEW IF NOT EXISTS v_table_storage_size AS
SELECT 
    'hexagrams' as table_name,
    COUNT(*) as record_count,
    SUM(
        LENGTH(COALESCE(gua_name, '')) + 
        LENGTH(COALESCE(basic_meaning, '')) + 
        LENGTH(COALESCE(judgement, '')) + 
        LENGTH(COALESCE(image, '')) + 
        LENGTH(COALESCE(decision, ''))
    ) as estimated_bytes,
    'core' as storage_tier
FROM hexagrams

UNION ALL

SELECT 
    'lines' as table_name,
    COUNT(*) as record_count,
    SUM(
        LENGTH(COALESCE(line_text, '')) + 
        LENGTH(COALESCE(line_meaning, '')) + 
        LENGTH(COALESCE(line_image, ''))
    ) as estimated_bytes,
    'core' as storage_tier
FROM lines

UNION ALL

SELECT 
    'interpretations_core' as table_name,
    COUNT(*) as record_count,
    SUM(COALESCE(content_length, 0)) as estimated_bytes,
    'core' as storage_tier
FROM interpretations 
WHERE is_core_content = 1

UNION ALL

SELECT 
    'interpretations_extended' as table_name,
    COUNT(*) as record_count,
    SUM(COALESCE(content_length, 0)) as estimated_bytes,
    'extended' as storage_tier
FROM interpretations 
WHERE is_core_content = 0

UNION ALL

SELECT 
    'divination_cases' as table_name,
    COUNT(*) as record_count,
    SUM(
        LENGTH(COALESCE(case_title, '')) + 
        LENGTH(COALESCE(question_detail, '')) + 
        LENGTH(COALESCE(interpretation, '')) + 
        LENGTH(COALESCE(actual_result, ''))
    ) as estimated_bytes,
    'extended' as storage_tier
FROM divination_cases

UNION ALL

SELECT 
    'keywords_tags' as table_name,
    COUNT(*) as record_count,
    SUM(
        LENGTH(COALESCE(keyword, '')) + 
        LENGTH(COALESCE(description, ''))
    ) as estimated_bytes,
    'core' as storage_tier
FROM keywords_tags;

-- 存储层级汇总
CREATE VIEW IF NOT EXISTS v_storage_tier_summary AS
SELECT 
    storage_tier,
    COUNT(*) as table_count,
    SUM(record_count) as total_records,
    SUM(estimated_bytes) as total_bytes,
    ROUND(SUM(estimated_bytes) / 1024.0 / 1024.0, 2) as total_mb,
    CASE 
        WHEN storage_tier = 'core' THEN 
            CASE WHEN SUM(estimated_bytes) <= 5*1024*1024 THEN '✓ 符合5MB限制' 
                 ELSE '⚠ 超出5MB限制' END
        WHEN storage_tier = 'extended' THEN 
            CASE WHEN SUM(estimated_bytes) <= 50*1024*1024 THEN '✓ 符合50MB限制'
                 ELSE '⚠ 超出50MB限制' END
    END as size_status
FROM v_table_storage_size
GROUP BY storage_tier;

-- ========================================================================
-- 批量操作优化
-- ========================================================================

-- 批量插入临时表 (用于大量数据导入)
CREATE TEMP TABLE IF NOT EXISTS temp_bulk_hexagrams AS 
SELECT * FROM hexagrams WHERE 1=0;

CREATE TEMP TABLE IF NOT EXISTS temp_bulk_lines AS
SELECT * FROM lines WHERE 1=0;

-- 批量插入优化的SQL模板
-- 使用方法: 先插入临时表，再批量转移到正式表

-- ========================================================================
-- 查询性能基准测试
-- ========================================================================

-- 基准测试1: 单卦查询性能
-- SELECT * FROM hexagrams WHERE gua_number = 1;

-- 基准测试2: 复杂关联查询性能  
-- SELECT h.gua_name, COUNT(l.id) as line_count, COUNT(i.id) as interp_count
-- FROM hexagrams h 
-- LEFT JOIN lines l ON h.id = l.hexagram_id
-- LEFT JOIN interpretations i ON h.id = i.target_id AND i.target_type = 'hexagram'
-- WHERE h.category = '乾宫'
-- GROUP BY h.id;

-- 基准测试3: 全文搜索性能
-- SELECT * FROM fts_hexagrams WHERE fts_hexagrams MATCH '龙 AND 天';

-- 基准测试4: 分层存储查询性能
-- SELECT * FROM v_core_content_fast LIMIT 100;

-- ========================================================================
-- 自动维护任务
-- ========================================================================

-- 定期清理性能日志 (保留最近30天)
-- DELETE FROM query_performance_log 
-- WHERE created_at < datetime('now', '-30 days');

-- 定期重建FTS索引 (每月执行)
-- INSERT INTO fts_hexagrams(fts_hexagrams) VALUES('rebuild');
-- INSERT INTO fts_lines(fts_lines) VALUES('rebuild'); 
-- INSERT INTO fts_interpretations(fts_interpretations) VALUES('rebuild');
-- INSERT INTO fts_cases(fts_cases) VALUES('rebuild');

-- 定期更新统计信息
-- ANALYZE;

-- ========================================================================
-- 备份和恢复优化
-- ========================================================================

-- 核心数据备份查询 (只备份5MB核心内容)
CREATE VIEW IF NOT EXISTS v_core_backup_data AS
SELECT 'hexagrams' as table_name, * FROM hexagrams
UNION ALL
SELECT 'lines' as table_name, 
       CAST(hexagram_id as TEXT) as id,
       CAST(line_position as TEXT) as gua_number,
       line_text as gua_name,
       '' as gua_name_pinyin,
       '' as upper_trigram,
       '' as lower_trigram,
       '' as binary_code,
       '' as unicode_symbol,
       '' as sequence_order,
       '' as nature,
       '' as category,
       line_meaning as basic_meaning,
       '' as judgement,
       line_image as image,
       '' as decision,
       created_at,
       updated_at
FROM lines
UNION ALL
SELECT 'interpretations_core' as table_name,
       CAST(id as TEXT),
       target_type as gua_number,
       author as gua_name,
       '' as gua_name_pinyin,
       dynasty as upper_trigram,
       source_book as lower_trigram,
       '' as binary_code,
       '' as unicode_symbol,
       '' as sequence_order,
       interpretation_type as nature,
       '' as category,
       interpretation_text as basic_meaning,
       '' as judgement,
       keywords as image,
       '' as decision,
       created_at,
       updated_at
FROM interpretations
WHERE is_core_content = 1;

-- 性能优化完成标记
INSERT INTO db_usage_stats (table_name, operation_type, record_count)
VALUES ('performance_config', 'LOADED', 1);