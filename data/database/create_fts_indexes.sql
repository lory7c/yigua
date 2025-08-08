-- Create FTS5 full-text search tables

-- Hexagrams FTS
CREATE VIRTUAL TABLE fts_hexagrams USING fts5(
    gua_name,
    basic_meaning,
    judgement,
    image,
    decision,
    content='hexagrams',
    content_rowid='id',
    tokenize='unicode61 remove_diacritics 1'
);

-- Lines FTS
CREATE VIRTUAL TABLE fts_lines USING fts5(
    line_text,
    line_meaning,
    line_image,
    practical_application,
    content='lines',
    content_rowid='id',
    tokenize='unicode61 remove_diacritics 1'
);

-- Interpretations FTS
CREATE VIRTUAL TABLE fts_interpretations USING fts5(
    author,
    source_book,
    interpretation_text,
    keywords,
    content='interpretations',
    content_rowid='id',
    tokenize='unicode61 remove_diacritics 1'
);

-- Cases FTS
CREATE VIRTUAL TABLE fts_cases USING fts5(
    case_title,
    question_detail,
    interpretation,
    actual_result,
    tags,
    content='divination_cases',
    content_rowid='id',
    tokenize='unicode61 remove_diacritics 1'
);

-- Critical performance indexes
CREATE UNIQUE INDEX idx_hexagrams_number ON hexagrams(gua_number);
CREATE INDEX idx_hexagrams_name ON hexagrams(gua_name);
CREATE INDEX idx_hexagrams_category ON hexagrams(category);
CREATE INDEX idx_hexagrams_nature ON hexagrams(nature);
CREATE INDEX idx_hexagrams_trigrams ON hexagrams(upper_trigram, lower_trigram);

CREATE INDEX idx_lines_hexagram ON lines(hexagram_id);
CREATE INDEX idx_lines_position ON lines(line_position);
CREATE INDEX idx_lines_type ON lines(line_type);
CREATE INDEX idx_lines_changing ON lines(is_changing_line);
CREATE INDEX idx_lines_element ON lines(element);
CREATE UNIQUE INDEX idx_lines_hex_pos ON lines(hexagram_id, line_position);

CREATE INDEX idx_interpretations_target ON interpretations(target_type, target_id);
CREATE INDEX idx_interpretations_author ON interpretations(author);
CREATE INDEX idx_interpretations_dynasty ON interpretations(dynasty);
CREATE INDEX idx_interpretations_type ON interpretations(interpretation_type);
CREATE INDEX idx_interpretations_importance ON interpretations(importance_level);
CREATE INDEX idx_interpretations_core ON interpretations(is_core_content);

CREATE INDEX idx_cases_hexagram ON divination_cases(hexagram_id);
CREATE INDEX idx_cases_result_hexagram ON divination_cases(result_hexagram_id);
CREATE INDEX idx_cases_type ON divination_cases(question_type);
CREATE INDEX idx_cases_date ON divination_cases(divination_date);
CREATE INDEX idx_cases_verified ON divination_cases(is_verified);
CREATE INDEX idx_cases_accuracy ON divination_cases(accuracy_rating);

CREATE UNIQUE INDEX idx_keywords_keyword ON keywords_tags(keyword);
CREATE INDEX idx_keywords_category ON keywords_tags(category);
CREATE INDEX idx_keywords_frequency ON keywords_tags(frequency DESC);
CREATE INDEX idx_keywords_importance ON keywords_tags(importance_score DESC);

CREATE INDEX idx_content_tags_content ON content_tags(content_type, content_id);
CREATE INDEX idx_content_tags_keyword ON content_tags(keyword_id);
CREATE INDEX idx_content_tags_relevance ON content_tags(relevance_score DESC);
CREATE UNIQUE INDEX idx_content_tags_unique ON content_tags(content_type, content_id, keyword_id);

CREATE INDEX idx_perf_log_type ON query_performance_log(query_type);
CREATE INDEX idx_perf_log_time ON query_performance_log(execution_time_ms);
CREATE INDEX idx_usage_stats_table ON db_usage_stats(table_name);
CREATE INDEX idx_usage_stats_operation ON db_usage_stats(operation_type);
CREATE INDEX idx_usage_stats_timestamp ON db_usage_stats(timestamp);