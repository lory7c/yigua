-- SQLite数据库架构设计 for 易学知识库
-- 优化目标: <10MB核心包, 高性能查询, 分层数据存储
-- 作者: Database Optimization Expert
-- 版本: v1.0

-- 启用外键约束和性能优化
PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA cache_size = -128000; -- 128MB cache for better performance
PRAGMA temp_store = memory;
PRAGMA mmap_size = 268435456; -- 256MB memory mapping
PRAGMA page_size = 4096; -- 4KB pages for optimal SSD performance
PRAGMA auto_vacuum = INCREMENTAL;
PRAGMA secure_delete = OFF; -- Faster deletes
PRAGMA locking_mode = NORMAL; -- Allow concurrent readers

-- ==========================================
-- 核心表结构 (Core Tables)
-- ==========================================

-- 1. 六十四卦主表 (64 hexagrams)
CREATE TABLE hexagrams (
    id INTEGER PRIMARY KEY, -- 1-64
    name TEXT NOT NULL, -- 卦名 (乾、坤等)
    chinese_name TEXT NOT NULL, -- 中文全称
    symbol TEXT NOT NULL, -- 卦象符号 (☰☷)
    upper_trigram INTEGER NOT NULL, -- 上卦 (1-8)
    lower_trigram INTEGER NOT NULL, -- 下卦 (1-8)
    judgment TEXT NOT NULL, -- 卦辞
    image TEXT NOT NULL, -- 象辞
    sequence_king_wen INTEGER NOT NULL, -- 文王卦序
    sequence_fuxi INTEGER NOT NULL, -- 伏羲卦序
    binary_value TEXT NOT NULL, -- 二进制表示 (111111)
    palace INTEGER NOT NULL, -- 宫位 (1-8)
    
    -- 分层标记和性能指标
    data_tier INTEGER NOT NULL DEFAULT 1, -- 1=core(5MB), 2=extended(50MB), 3=cloud(unlimited)
    quality_score REAL DEFAULT 1.0, -- 质量评分 0.0-1.0
    access_frequency INTEGER DEFAULT 0, -- 访问频次
    content_size INTEGER DEFAULT 0, -- 内容字节大小
    last_accessed INTEGER, -- 最后访问时间
    
    -- 时间戳
    created_at INTEGER DEFAULT (strftime('%s', 'now')),
    updated_at INTEGER DEFAULT (strftime('%s', 'now'))
);

-- 2. 三百八十四爻表 (384 lines: 64*6)
CREATE TABLE lines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    hexagram_id INTEGER NOT NULL,
    position INTEGER NOT NULL, -- 爻位 1-6
    type INTEGER NOT NULL, -- 0=阴爻, 1=阳爻
    text TEXT NOT NULL, -- 爻辞
    image TEXT, -- 小象辞
    
    -- 结构化数据
    is_changing BOOLEAN DEFAULT 0, -- 是否变爻
    strength INTEGER, -- 爻力强度 1-5
    
    data_tier INTEGER NOT NULL DEFAULT 1,
    content_size INTEGER DEFAULT 0,
    access_frequency INTEGER DEFAULT 0,
    created_at INTEGER DEFAULT (strftime('%s', 'now')),
    
    FOREIGN KEY (hexagram_id) REFERENCES hexagrams(id) ON DELETE CASCADE,
    UNIQUE(hexagram_id, position)
);

-- 3. 解释注解表 (多版本解释)
CREATE TABLE interpretations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    target_type INTEGER NOT NULL, -- 1=hexagram, 2=line
    target_id INTEGER NOT NULL, -- 对应的卦或爻ID
    category INTEGER NOT NULL, -- 1=传统注解, 2=现代解释, 3=占断要诀
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    author TEXT,
    source_book TEXT,
    
    -- 内容特征
    content_length INTEGER, -- 文本长度
    readability_score REAL, -- 可读性评分
    
    data_tier INTEGER NOT NULL DEFAULT 2,
    quality_score REAL DEFAULT 0.8,
    access_frequency INTEGER DEFAULT 0,
    content_size INTEGER DEFAULT 0,
    last_accessed INTEGER,
    created_at INTEGER DEFAULT (strftime('%s', 'now'))
);

-- 4. 占卜案例表
CREATE TABLE divination_cases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    question TEXT NOT NULL, -- 所问事项
    method INTEGER NOT NULL, -- 1=六爻, 2=梅花易数, 3=大六壬等
    
    -- 起卦信息
    original_hexagram INTEGER NOT NULL, -- 本卦
    changed_hexagram INTEGER, -- 变卦
    changing_lines TEXT, -- 变爻位置 JSON数组 [2,4,6]
    divination_time INTEGER, -- 起卦时间
    
    -- 分析过程
    analysis_process TEXT NOT NULL, -- 分析过程
    judgment TEXT NOT NULL, -- 断语
    result_verification TEXT, -- 应验情况
    
    -- 元数据
    author TEXT,
    source_document TEXT,
    difficulty_level INTEGER DEFAULT 2, -- 1-5难度
    case_category TEXT, -- 事业/婚姻/健康等
    
    data_tier INTEGER NOT NULL DEFAULT 2,
    accuracy_rating REAL, -- 准确度评分
    access_frequency INTEGER DEFAULT 0,
    content_size INTEGER DEFAULT 0,
    last_accessed INTEGER,
    created_at INTEGER DEFAULT (strftime('%s', 'now')),
    
    FOREIGN KEY (original_hexagram) REFERENCES hexagrams(id),
    FOREIGN KEY (changed_hexagram) REFERENCES hexagrams(id)
);

-- ==========================================
-- 辅助数据表
-- ==========================================

-- 5. 八卦基础表
CREATE TABLE trigrams (
    id INTEGER PRIMARY KEY, -- 1-8
    name TEXT NOT NULL, -- 乾、兑、离、震、巽、坎、艮、坤
    symbol TEXT NOT NULL, -- ☰☱☲☳☴☵☶☷
    binary TEXT NOT NULL, -- 111, 110, 101等
    nature TEXT NOT NULL, -- 天、泽、火、雷、风、水、山、地
    attribute TEXT, -- 刚健、喜悦等属性
    direction TEXT, -- 方位
    season TEXT, -- 季节
    family_role TEXT, -- 家庭角色
    
    data_tier INTEGER NOT NULL DEFAULT 1
);

-- 6. 标签分类表
CREATE TABLE tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    category TEXT NOT NULL, -- 分类: method/topic/difficulty/quality
    description TEXT,
    color TEXT, -- UI显示颜色
    usage_count INTEGER DEFAULT 0 -- 使用次数统计
);

-- 7. 内容标签关联表
CREATE TABLE content_tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content_type INTEGER NOT NULL, -- 1=hexagram, 2=line, 3=interpretation, 4=case
    content_id INTEGER NOT NULL,
    tag_id INTEGER NOT NULL,
    
    FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE,
    UNIQUE(content_type, content_id, tag_id)
);

-- 8. 知识图谱关系表
CREATE TABLE knowledge_relationships (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    from_type INTEGER NOT NULL, -- 源节点类型
    from_id INTEGER NOT NULL, -- 源节点ID
    to_type INTEGER NOT NULL, -- 目标节点类型
    to_id INTEGER NOT NULL, -- 目标节点ID
    relationship_type INTEGER NOT NULL, -- 关系类型: 1=相似, 2=对比, 3=演变, 4=引用
    strength REAL DEFAULT 1.0, -- 关系强度 0-1
    description TEXT, -- 关系描述
    
    created_at INTEGER DEFAULT (strftime('%s', 'now')),
    UNIQUE(from_type, from_id, to_type, to_id, relationship_type)
);

-- 9. 数据源文档表
CREATE TABLE source_documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_path TEXT NOT NULL,
    file_name TEXT NOT NULL,
    file_size INTEGER,
    file_hash TEXT UNIQUE,
    mime_type TEXT,
    
    -- 处理状态
    processing_status INTEGER DEFAULT 0, -- 0=未处理, 1=处理中, 2=已完成, 3=失败
    extraction_method TEXT,
    page_count INTEGER,
    
    -- 质量评估
    quality_score REAL DEFAULT 0.0,
    confidence_score REAL DEFAULT 0.0,
    
    created_at INTEGER DEFAULT (strftime('%s', 'now')),
    processed_at INTEGER
);

-- 10. 用户学习进度表 (轻量级)
CREATE TABLE learning_progress (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content_type INTEGER NOT NULL,
    content_id INTEGER NOT NULL,
    progress_percent INTEGER DEFAULT 0, -- 0-100
    mastery_level INTEGER DEFAULT 1, -- 1-5掌握程度
    last_reviewed INTEGER, -- 最后复习时间
    review_count INTEGER DEFAULT 0,
    time_spent INTEGER DEFAULT 0, -- 学习时长(秒)
    
    created_at INTEGER DEFAULT (strftime('%s', 'now')),
    updated_at INTEGER DEFAULT (strftime('%s', 'now'))
);

-- 11. 数据层级管理表
CREATE TABLE tier_management (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tier_level INTEGER NOT NULL, -- 1=core, 2=extended, 3=cloud
    max_size_bytes INTEGER NOT NULL, -- 层级最大容量
    current_size_bytes INTEGER DEFAULT 0, -- 当前使用容量
    target_quality_threshold REAL DEFAULT 0.8, -- 质量门槛
    auto_cleanup BOOLEAN DEFAULT 1, -- 是否自动清理
    
    created_at INTEGER DEFAULT (strftime('%s', 'now')),
    updated_at INTEGER DEFAULT (strftime('%s', 'now'))
);

-- 12. 查询性能统计表
CREATE TABLE query_performance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query_pattern TEXT NOT NULL, -- 查询模式标识
    execution_time_ms INTEGER NOT NULL, -- 执行时间(毫秒)
    result_count INTEGER DEFAULT 0, -- 结果数量
    index_used TEXT, -- 使用的索引
    optimization_suggestion TEXT, -- 优化建议
    
    created_at INTEGER DEFAULT (strftime('%s', 'now'))
);

-- 13. 缓存管理表
CREATE TABLE cache_management (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cache_key TEXT NOT NULL UNIQUE,
    content_hash TEXT NOT NULL, -- 内容哈希
    hit_count INTEGER DEFAULT 0, -- 命中次数
    last_hit INTEGER, -- 最后命中时间
    ttl_seconds INTEGER DEFAULT 3600, -- TTL秒数
    
    created_at INTEGER DEFAULT (strftime('%s', 'now')),
    expires_at INTEGER DEFAULT (strftime('%s', 'now', '+1 hour'))
);

-- ==========================================
-- 全文搜索表 (FTS5)
-- ==========================================

-- FTS5虚拟表: 全文搜索索引
CREATE VIRTUAL TABLE hexagrams_fts USING fts5(
    name, chinese_name, judgment, image, 
    content='hexagrams', 
    content_rowid='id',
    tokenize='porter ascii'
);

CREATE VIRTUAL TABLE lines_fts USING fts5(
    text, image,
    content='lines',
    content_rowid='id',
    tokenize='porter ascii'
);

CREATE VIRTUAL TABLE interpretations_fts USING fts5(
    title, content, author,
    content='interpretations',
    content_rowid='id',
    tokenize='porter ascii'
);

CREATE VIRTUAL TABLE cases_fts USING fts5(
    title, question, analysis_process, judgment,
    content='divination_cases',
    content_rowid='id',
    tokenize='porter ascii'
);

-- FTS5同步触发器
CREATE TRIGGER hexagrams_fts_insert AFTER INSERT ON hexagrams 
BEGIN
    INSERT INTO hexagrams_fts(rowid, name, chinese_name, judgment, image)
    VALUES (new.id, new.name, new.chinese_name, new.judgment, new.image);
END;

CREATE TRIGGER hexagrams_fts_delete AFTER DELETE ON hexagrams 
BEGIN
    INSERT INTO hexagrams_fts(hexagrams_fts, rowid, name, chinese_name, judgment, image)
    VALUES ('delete', old.id, old.name, old.chinese_name, old.judgment, old.image);
END;

CREATE TRIGGER hexagrams_fts_update AFTER UPDATE ON hexagrams 
BEGIN
    INSERT INTO hexagrams_fts(hexagrams_fts, rowid, name, chinese_name, judgment, image)
    VALUES ('delete', old.id, old.name, old.chinese_name, old.judgment, old.image);
    INSERT INTO hexagrams_fts(rowid, name, chinese_name, judgment, image)
    VALUES (new.id, new.name, new.chinese_name, new.judgment, new.image);
END;

-- 类似地为其他表创建FTS5同步触发器
CREATE TRIGGER lines_fts_insert AFTER INSERT ON lines 
BEGIN
    INSERT INTO lines_fts(rowid, text, image) VALUES (new.id, new.text, new.image);
END;

CREATE TRIGGER interpretations_fts_insert AFTER INSERT ON interpretations 
BEGIN
    INSERT INTO interpretations_fts(rowid, title, content, author) 
    VALUES (new.id, new.title, new.content, new.author);
END;

CREATE TRIGGER cases_fts_insert AFTER INSERT ON divination_cases 
BEGIN
    INSERT INTO cases_fts(rowid, title, question, analysis_process, judgment)
    VALUES (new.id, new.title, new.question, new.analysis_process, new.judgment);
END;

-- ==========================================  
-- 分层数据初始化
-- ==========================================

-- 初始化数据层级管理配置
INSERT OR IGNORE INTO tier_management (tier_level, max_size_bytes, target_quality_threshold) VALUES
(1, 5242880, 0.9),    -- Core: 5MB, 高质量数据
(2, 52428800, 0.7),   -- Extended: 50MB, 中等质量数据  
(3, 1073741824, 0.5); -- Cloud: 1GB, 一般质量数据

-- 内容大小更新触发器
CREATE TRIGGER update_content_size_hexagrams AFTER INSERT ON hexagrams
BEGIN
    UPDATE hexagrams SET content_size = length(name) + length(chinese_name) + length(judgment) + length(image)
    WHERE id = new.id;
END;

CREATE TRIGGER update_content_size_interpretations AFTER INSERT ON interpretations  
BEGIN
    UPDATE interpretations SET content_size = length(title) + length(content)
    WHERE id = new.id;
END;

-- 访问频次更新触发器
CREATE TRIGGER update_access_hexagrams AFTER UPDATE OF last_accessed ON hexagrams
BEGIN
    UPDATE hexagrams SET access_frequency = access_frequency + 1 
    WHERE id = new.id;
END;

-- 数据层级自动调整触发器
CREATE TRIGGER auto_tier_adjustment AFTER UPDATE OF quality_score, access_frequency ON interpretations
BEGIN
    UPDATE interpretations 
    SET data_tier = CASE 
        WHEN quality_score >= 0.9 AND access_frequency > 100 THEN 1
        WHEN quality_score >= 0.7 AND access_frequency > 10 THEN 2
        ELSE 3
    END,
    updated_at = strftime('%s', 'now')
    WHERE id = new.id;
END;

-- 缓存清理触发器
CREATE TRIGGER cache_cleanup AFTER INSERT ON cache_management
WHEN (SELECT COUNT(*) FROM cache_management) > 10000
BEGIN
    DELETE FROM cache_management 
    WHERE expires_at < strftime('%s', 'now') 
    OR id IN (
        SELECT id FROM cache_management 
        ORDER BY last_hit ASC NULLS FIRST, created_at ASC 
        LIMIT 1000
    );
END;

-- ==========================================
-- 数据分层视图
-- ==========================================

-- 核心数据视图 (data_tier = 1)
CREATE VIEW core_hexagrams AS 
SELECT * FROM hexagrams WHERE data_tier = 1;

CREATE VIEW core_lines AS 
SELECT l.* FROM lines l 
JOIN hexagrams h ON l.hexagram_id = h.id 
WHERE l.data_tier = 1 AND h.data_tier = 1;

-- 扩展数据视图 (data_tier <= 2)
CREATE VIEW extended_content AS
SELECT 'hexagram' as type, id, name as title, judgment as content, data_tier, quality_score 
FROM hexagrams WHERE data_tier <= 2
UNION ALL
SELECT 'interpretation' as type, id, title, content, data_tier, quality_score 
FROM interpretations WHERE data_tier <= 2
UNION ALL
SELECT 'case' as type, id, title, question as content, data_tier, accuracy_rating as quality_score 
FROM divination_cases WHERE data_tier <= 2
UNION ALL
SELECT 'tag' as type, id, name as title, description as content, 1 as data_tier, (usage_count/100.0) as quality_score
FROM tags WHERE usage_count > 0;

-- 统计视图
CREATE VIEW data_statistics AS
SELECT 
    'hexagrams' as table_name,
    COUNT(*) as total_count,
    SUM(CASE WHEN data_tier = 1 THEN 1 ELSE 0 END) as core_count,
    SUM(CASE WHEN data_tier = 2 THEN 1 ELSE 0 END) as extended_count,
    SUM(CASE WHEN data_tier = 3 THEN 1 ELSE 0 END) as cloud_count,
    AVG(quality_score) as avg_quality
FROM hexagrams
UNION ALL
SELECT 
    'lines' as table_name,
    COUNT(*) as total_count,
    SUM(CASE WHEN data_tier = 1 THEN 1 ELSE 0 END) as core_count,
    SUM(CASE WHEN data_tier = 2 THEN 1 ELSE 0 END) as extended_count,
    SUM(CASE WHEN data_tier = 3 THEN 1 ELSE 0 END) as cloud_count,
    0.0 as avg_quality
FROM lines
UNION ALL
SELECT 
    'interpretations' as table_name,
    COUNT(*) as total_count,
    SUM(CASE WHEN data_tier = 1 THEN 1 ELSE 0 END) as core_count,
    SUM(CASE WHEN data_tier = 2 THEN 1 ELSE 0 END) as extended_count,
    SUM(CASE WHEN data_tier = 3 THEN 1 ELSE 0 END) as cloud_count,
    AVG(quality_score) as avg_quality
FROM interpretations
UNION ALL
SELECT 
    'divination_cases' as table_name,
    COUNT(*) as total_count,
    SUM(CASE WHEN data_tier = 1 THEN 1 ELSE 0 END) as core_count,
    SUM(CASE WHEN data_tier = 2 THEN 1 ELSE 0 END) as extended_count,
    SUM(CASE WHEN data_tier = 3 THEN 1 ELSE 0 END) as cloud_count,
    AVG(accuracy_rating) as avg_quality
FROM divination_cases
UNION ALL
SELECT 
    'tags' as table_name,
    COUNT(*) as total_count,
    COUNT(*) as core_count, -- 所有标签都是核心数据
    0 as extended_count,
    0 as cloud_count,
    AVG(usage_count/100.0) as avg_quality
FROM tags
UNION ALL
SELECT 
    'source_documents' as table_name,
    COUNT(*) as total_count,
    SUM(CASE WHEN processing_status = 2 THEN 1 ELSE 0 END) as core_count,
    SUM(CASE WHEN processing_status = 1 THEN 1 ELSE 0 END) as extended_count,
    SUM(CASE WHEN processing_status = 0 OR processing_status = 3 THEN 1 ELSE 0 END) as cloud_count,
    AVG(quality_score) as avg_quality
FROM source_documents;

-- 数据层级大小监控视图
CREATE VIEW tier_size_monitor AS
SELECT 
    tm.tier_level,
    tm.max_size_bytes,
    tm.current_size_bytes,
    ROUND(tm.current_size_bytes * 100.0 / tm.max_size_bytes, 2) as usage_percent,
    CASE 
        WHEN tm.current_size_bytes > tm.max_size_bytes THEN 'OVER_LIMIT'
        WHEN tm.current_size_bytes > tm.max_size_bytes * 0.9 THEN 'WARNING'  
        WHEN tm.current_size_bytes > tm.max_size_bytes * 0.8 THEN 'HIGH'
        ELSE 'NORMAL'
    END as status,
    tm.target_quality_threshold,
    tm.auto_cleanup
FROM tier_management tm;

-- 高频访问内容视图
CREATE VIEW popular_content AS
SELECT 
    'hexagram' as content_type, 
    id,
    name as title,
    access_frequency,
    quality_score,
    data_tier,
    last_accessed
FROM hexagrams 
WHERE access_frequency > 50
UNION ALL
SELECT 
    'interpretation' as content_type,
    id, 
    title,
    access_frequency,
    quality_score, 
    data_tier,
    last_accessed
FROM interpretations
WHERE access_frequency > 20
ORDER BY access_frequency DESC, quality_score DESC;

-- 内容质量分布视图
CREATE VIEW quality_distribution AS 
SELECT 
    data_tier,
    CASE 
        WHEN quality_score >= 0.9 THEN 'EXCELLENT'
        WHEN quality_score >= 0.8 THEN 'GOOD' 
        WHEN quality_score >= 0.7 THEN 'FAIR'
        WHEN quality_score >= 0.6 THEN 'POOR'
        ELSE 'VERY_POOR'
    END as quality_level,
    COUNT(*) as count,
    AVG(access_frequency) as avg_access_freq
FROM (
    SELECT data_tier, quality_score, access_frequency FROM hexagrams
    UNION ALL  
    SELECT data_tier, quality_score, access_frequency FROM interpretations
    UNION ALL
    SELECT data_tier, accuracy_rating as quality_score, access_frequency FROM divination_cases
) combined
GROUP BY data_tier, quality_level
ORDER BY data_tier, quality_score DESC;

-- 查询性能监控视图  
CREATE VIEW slow_queries AS
SELECT 
    query_pattern,
    AVG(execution_time_ms) as avg_time_ms,
    MAX(execution_time_ms) as max_time_ms,
    COUNT(*) as execution_count,
    SUM(result_count) as total_results,
    MAX(created_at) as last_execution
FROM query_performance
WHERE execution_time_ms > 100  -- 慢查询阈值100ms
GROUP BY query_pattern
ORDER BY avg_time_ms DESC;