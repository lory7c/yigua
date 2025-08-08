-- Complete database rebuild script
-- SQLite I-Ching Knowledge Base

-- Performance settings
PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA cache_size = -64000;
PRAGMA temp_store = MEMORY;
PRAGMA mmap_size = 268435456;

-- Core tables
CREATE TABLE hexagrams (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    gua_number INTEGER NOT NULL UNIQUE CHECK (gua_number BETWEEN 1 AND 64),
    gua_name TEXT NOT NULL,
    gua_name_pinyin TEXT NOT NULL,
    upper_trigram TEXT NOT NULL,
    lower_trigram TEXT NOT NULL,
    binary_code TEXT NOT NULL,
    unicode_symbol TEXT,
    sequence_order INTEGER,
    nature TEXT,
    category TEXT,
    basic_meaning TEXT NOT NULL,
    judgement TEXT,
    image TEXT,
    decision TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE lines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    hexagram_id INTEGER NOT NULL,
    line_position INTEGER NOT NULL CHECK (line_position BETWEEN 1 AND 6),
    line_type INTEGER NOT NULL CHECK (line_type IN (0, 1)),
    line_text TEXT NOT NULL,
    line_meaning TEXT,
    line_image TEXT,
    is_changing_line BOOLEAN DEFAULT 0,
    strength_level INTEGER CHECK (strength_level BETWEEN 1 AND 5),
    element TEXT,
    relationship TEXT,
    practical_application TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (hexagram_id) REFERENCES hexagrams(id) ON DELETE CASCADE
);

CREATE TABLE interpretations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    target_type TEXT NOT NULL CHECK (target_type IN ('hexagram', 'line')),
    target_id INTEGER NOT NULL,
    author TEXT NOT NULL,
    dynasty TEXT,
    source_book TEXT,
    interpretation_text TEXT NOT NULL,
    interpretation_type TEXT CHECK (interpretation_type IN ('象', '义', '占', '理', '数')),
    importance_level INTEGER DEFAULT 3 CHECK (importance_level BETWEEN 1 AND 5),
    content_length INTEGER,
    is_core_content BOOLEAN DEFAULT 0,
    keywords TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE divination_cases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    case_title TEXT NOT NULL,
    hexagram_id INTEGER NOT NULL,
    changing_lines TEXT,
    result_hexagram_id INTEGER,
    question_type TEXT,
    question_detail TEXT,
    divination_date DATE,
    diviner_name TEXT,
    interpretation TEXT NOT NULL,
    actual_result TEXT,
    accuracy_rating INTEGER CHECK (accuracy_rating BETWEEN 1 AND 5),
    case_source TEXT,
    is_verified BOOLEAN DEFAULT 0,
    tags TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (hexagram_id) REFERENCES hexagrams(id) ON DELETE CASCADE,
    FOREIGN KEY (result_hexagram_id) REFERENCES hexagrams(id) ON DELETE SET NULL
);

CREATE TABLE keywords_tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    keyword TEXT NOT NULL UNIQUE,
    category TEXT,
    frequency INTEGER DEFAULT 1,
    importance_score REAL DEFAULT 1.0,
    related_keywords TEXT,
    description TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE content_tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content_type TEXT NOT NULL CHECK (content_type IN ('hexagram', 'line', 'interpretation', 'case')),
    content_id INTEGER NOT NULL,
    keyword_id INTEGER NOT NULL,
    relevance_score REAL DEFAULT 1.0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (keyword_id) REFERENCES keywords_tags(id) ON DELETE CASCADE
);

CREATE TABLE query_performance_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query_type TEXT NOT NULL,
    query_text TEXT,
    execution_time_ms INTEGER,
    result_count INTEGER,
    cache_hit BOOLEAN DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE db_usage_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    table_name TEXT NOT NULL,
    operation_type TEXT NOT NULL,
    record_count INTEGER DEFAULT 1,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Critical indexes
CREATE UNIQUE INDEX idx_hexagrams_number ON hexagrams(gua_number);
CREATE INDEX idx_hexagrams_name ON hexagrams(gua_name);
CREATE INDEX idx_hexagrams_category ON hexagrams(category);
CREATE INDEX idx_lines_hexagram ON lines(hexagram_id);
CREATE INDEX idx_lines_position ON lines(line_position);
CREATE UNIQUE INDEX idx_lines_hex_pos ON lines(hexagram_id, line_position);
CREATE INDEX idx_interpretations_target ON interpretations(target_type, target_id);
CREATE INDEX idx_interpretations_core ON interpretations(is_core_content);
CREATE INDEX idx_cases_hexagram ON divination_cases(hexagram_id);
CREATE INDEX idx_content_tags_content ON content_tags(content_type, content_id);
CREATE INDEX idx_content_tags_keyword ON content_tags(keyword_id);
CREATE UNIQUE INDEX idx_keywords_keyword ON keywords_tags(keyword);

-- Sample data
INSERT INTO hexagrams (gua_number, gua_name, gua_name_pinyin, upper_trigram, lower_trigram, binary_code, unicode_symbol, basic_meaning, judgement, category, nature) VALUES
(1, '乾', 'qian', '乾', '乾', '111111', '☰', '天，刚健', '元，亨，利，贞。', '乾宫', '吉'),
(2, '坤', 'kun', '坤', '坤', '000000', '☷', '地，柔顺', '元，亨，利牝马之贞。', '坤宫', '吉');

INSERT INTO lines (hexagram_id, line_position, line_type, line_text, line_meaning, element) VALUES
(1, 1, 1, '初九：潜龙勿用。', '龙潜在渊，不要轻举妄动', '金'),
(1, 2, 1, '九二：见龙在田，利见大人。', '龙出现在田野，利于见到德高望重的人', '金'),
(2, 1, 0, '初六：履霜，坚冰至。', '踩到霜，坚冰即将到来', '土'),
(2, 2, 0, '六二：直，方，大，不习无不利。', '正直，方正，广大', '土');

INSERT INTO keywords_tags (keyword, category, frequency, importance_score, description) VALUES
('天', '自然', 100, 5.0, '代表天空、至高无上'),
('地', '自然', 95, 5.0, '代表大地、承载'),
('龙', '象征', 80, 4.5, '象征帝王、力量、变化');

INSERT INTO interpretations (target_type, target_id, author, dynasty, source_book, interpretation_text, interpretation_type, importance_level, is_core_content, keywords) VALUES
('hexagram', 1, '孔子', '春秋', '易传', '乾，健也。刚健中正，纯粹精也。', '象', 5, 1, '刚健,中正,纯粹');

-- Mark completion
INSERT INTO db_usage_stats (table_name, operation_type, record_count) VALUES ('database_rebuild', 'COMPLETED', 1);