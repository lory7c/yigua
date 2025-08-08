-- SQLite I-Ching Knowledge Base Creation Script

-- Enable WAL mode and performance settings
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA cache_size = -64000;
PRAGMA foreign_keys = ON;

-- Create hexagrams table
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

-- Create lines table
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

-- Create interpretations table  
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

-- Create divination cases table
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

-- Create keywords and content tags tables
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

-- Create performance monitoring tables
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