-- FTS sync triggers for hexagrams
CREATE TRIGGER trg_hexagrams_fts_insert AFTER INSERT ON hexagrams BEGIN
    INSERT INTO fts_hexagrams(rowid, gua_name, basic_meaning, judgement, image, decision)
    VALUES (new.id, new.gua_name, new.basic_meaning, new.judgement, new.image, new.decision);
END;

CREATE TRIGGER trg_hexagrams_fts_delete AFTER DELETE ON hexagrams BEGIN
    DELETE FROM fts_hexagrams WHERE rowid = old.id;
END;

CREATE TRIGGER trg_hexagrams_fts_update AFTER UPDATE ON hexagrams BEGIN
    UPDATE fts_hexagrams SET 
        gua_name = new.gua_name,
        basic_meaning = new.basic_meaning,
        judgement = new.judgement,
        image = new.image,
        decision = new.decision
    WHERE rowid = new.id;
END;

-- FTS sync triggers for lines
CREATE TRIGGER trg_lines_fts_insert AFTER INSERT ON lines BEGIN
    INSERT INTO fts_lines(rowid, line_text, line_meaning, line_image, practical_application)
    VALUES (new.id, new.line_text, new.line_meaning, new.line_image, new.practical_application);
END;

CREATE TRIGGER trg_lines_fts_delete AFTER DELETE ON lines BEGIN
    DELETE FROM fts_lines WHERE rowid = old.id;
END;

CREATE TRIGGER trg_lines_fts_update AFTER UPDATE ON lines BEGIN
    UPDATE fts_lines SET 
        line_text = new.line_text,
        line_meaning = new.line_meaning,
        line_image = new.line_image,
        practical_application = new.practical_application
    WHERE rowid = new.id;
END;

-- FTS sync triggers for interpretations
CREATE TRIGGER trg_interpretations_fts_insert AFTER INSERT ON interpretations BEGIN
    INSERT INTO fts_interpretations(rowid, author, source_book, interpretation_text, keywords)
    VALUES (new.id, new.author, new.source_book, new.interpretation_text, new.keywords);
END;

CREATE TRIGGER trg_interpretations_fts_delete AFTER DELETE ON interpretations BEGIN
    DELETE FROM fts_interpretations WHERE rowid = old.id;
END;

CREATE TRIGGER trg_interpretations_fts_update AFTER UPDATE ON interpretations BEGIN
    UPDATE fts_interpretations SET 
        author = new.author,
        source_book = new.source_book,
        interpretation_text = new.interpretation_text,
        keywords = new.keywords
    WHERE rowid = new.id;
END;

-- FTS sync triggers for divination_cases
CREATE TRIGGER trg_cases_fts_insert AFTER INSERT ON divination_cases BEGIN
    INSERT INTO fts_cases(rowid, case_title, question_detail, interpretation, actual_result, tags)
    VALUES (new.id, new.case_title, new.question_detail, new.interpretation, new.actual_result, new.tags);
END;

CREATE TRIGGER trg_cases_fts_delete AFTER DELETE ON divination_cases BEGIN
    DELETE FROM fts_cases WHERE rowid = old.id;
END;

CREATE TRIGGER trg_cases_fts_update AFTER UPDATE ON divination_cases BEGIN
    UPDATE fts_cases SET 
        case_title = new.case_title,
        question_detail = new.question_detail,
        interpretation = new.interpretation,
        actual_result = new.actual_result,
        tags = new.tags
    WHERE rowid = new.id;
END;

-- Auto-update timestamp triggers
CREATE TRIGGER trg_hexagrams_updated AFTER UPDATE ON hexagrams BEGIN
    UPDATE hexagrams SET updated_at = CURRENT_TIMESTAMP WHERE id = new.id;
END;

CREATE TRIGGER trg_lines_updated AFTER UPDATE ON lines BEGIN
    UPDATE lines SET updated_at = CURRENT_TIMESTAMP WHERE id = new.id;
END;

CREATE TRIGGER trg_interpretations_updated AFTER UPDATE ON interpretations BEGIN
    UPDATE interpretations SET updated_at = CURRENT_TIMESTAMP WHERE id = new.id;
END;

CREATE TRIGGER trg_cases_updated AFTER UPDATE ON divination_cases BEGIN
    UPDATE divination_cases SET updated_at = CURRENT_TIMESTAMP WHERE id = new.id;
END;

CREATE TRIGGER trg_keywords_updated AFTER UPDATE ON keywords_tags BEGIN
    UPDATE keywords_tags SET updated_at = CURRENT_TIMESTAMP WHERE id = new.id;
END;

-- Core content marking trigger
CREATE TRIGGER trg_mark_core_interpretations 
AFTER INSERT ON interpretations
WHEN new.importance_level >= 4 OR new.author IN ('朱熹', '程颐', '王弼', '孔子')
BEGIN
    UPDATE interpretations 
    SET is_core_content = 1,
        content_length = LENGTH(new.interpretation_text)
    WHERE id = new.id;
END;