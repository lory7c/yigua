-- Database Performance and Integrity Test Report
-- Generated: 2025-08-07

-- Basic database information
SELECT 'Database Configuration' as test_category, 
       'WAL Mode: ' || (SELECT CASE WHEN journal_mode = 'wal' THEN 'Enabled' ELSE 'Disabled' END FROM pragma_journal_mode()) ||
       ', Cache Size: ' || (SELECT cache_size FROM pragma_cache_size()) ||
       ', Page Size: ' || (SELECT page_size FROM pragma_page_size()) ||
       ', Database Size: ' || (SELECT page_count * page_size FROM pragma_page_count(), pragma_page_size()) || ' bytes' as test_result

UNION ALL

-- Table counts
SELECT 'Table Record Counts' as test_category,
       'Hexagrams: ' || (SELECT COUNT(*) FROM hexagrams) ||
       ', Lines: ' || (SELECT COUNT(*) FROM lines) || 
       ', Interpretations: ' || (SELECT COUNT(*) FROM interpretations) as test_result

UNION ALL

-- Index verification
SELECT 'Index Performance' as test_category,
       'Indexes Created: ' || (SELECT COUNT(*) FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%') ||
       ', FTS Tables: ' || (SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name LIKE 'fts_%' AND name NOT LIKE '%_data' AND name NOT LIKE '%_idx' AND name NOT LIKE '%_docsize' AND name NOT LIKE '%_config') as test_result

UNION ALL

-- Integrity check
SELECT 'Database Integrity' as test_category,
       (SELECT CASE WHEN integrity_check = 'ok' THEN 'PASSED' ELSE 'FAILED: ' || integrity_check END FROM pragma_integrity_check()) as test_result

UNION ALL

-- Foreign key check  
SELECT 'Foreign Key Constraints' as test_category,
       CASE WHEN (SELECT COUNT(*) FROM pragma_foreign_key_check()) = 0 THEN 'PASSED' ELSE 'FAILED' END as test_result

UNION ALL

-- FTS search test
SELECT 'FTS5 Search Functionality' as test_category,
       CASE WHEN (SELECT COUNT(*) FROM fts_hexagrams WHERE fts_hexagrams MATCH '天') > 0 THEN 'PASSED' ELSE 'FAILED' END as test_result

UNION ALL

-- Query performance test
SELECT 'Complex Join Performance' as test_category,
       'Query executed successfully, returned ' || 
       (SELECT COUNT(*) FROM hexagrams h LEFT JOIN lines l ON h.id = l.hexagram_id) ||
       ' rows' as test_result;