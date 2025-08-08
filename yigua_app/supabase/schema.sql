-- Supabase 数据库Schema
-- 创建易经卦象应用的数据库结构

-- 启用UUID扩展
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 启用全文搜索支持
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- 1. 卦象表（64卦基础数据）
CREATE TABLE hexagrams (
    id SERIAL PRIMARY KEY,
    number INTEGER UNIQUE NOT NULL CHECK (number >= 1 AND number <= 64),
    name VARCHAR(50) NOT NULL,
    symbol VARCHAR(10) NOT NULL,
    upper_trigram VARCHAR(10) NOT NULL,
    lower_trigram VARCHAR(10) NOT NULL,
    description TEXT NOT NULL,
    interpretation TEXT NOT NULL,
    fortune VARCHAR(20),
    advice TEXT,
    career_interpretation TEXT,
    relationship_interpretation TEXT,
    health_interpretation TEXT,
    finance_interpretation TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 2. 爻辞表（每卦的6爻）
CREATE TABLE yao_texts (
    id SERIAL PRIMARY KEY,
    hexagram_id INTEGER REFERENCES hexagrams(id) ON DELETE CASCADE,
    position INTEGER NOT NULL CHECK (position >= 1 AND position <= 6),
    yao_text TEXT NOT NULL,
    interpretation TEXT NOT NULL,
    is_changing BOOLEAN DEFAULT FALSE,
    UNIQUE(hexagram_id, position)
);

-- 3. 搜索索引表
CREATE TABLE search_index (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    type VARCHAR(50) NOT NULL, -- hexagram, liuyao, meihua, bazi, knowledge
    item_id INTEGER,
    title VARCHAR(200) NOT NULL,
    content TEXT NOT NULL,
    tags TEXT[],
    category VARCHAR(100),
    relevance_score FLOAT DEFAULT 1.0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    search_vector tsvector GENERATED ALWAYS AS (
        setweight(to_tsvector('chinese', coalesce(title, '')), 'A') ||
        setweight(to_tsvector('chinese', coalesce(content, '')), 'B')
    ) STORED
);

-- 创建全文搜索索引
CREATE INDEX idx_search_vector ON search_index USING GIN(search_vector);
CREATE INDEX idx_search_type ON search_index(type);
CREATE INDEX idx_search_category ON search_index(category);

-- 4. 用户表（如果使用Supabase Auth，可以省略）
CREATE TABLE users (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    email VARCHAR(255) UNIQUE,
    username VARCHAR(100),
    avatar_url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_login_at TIMESTAMP WITH TIME ZONE
);

-- 5. 用户历史记录表
CREATE TABLE user_history (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    type VARCHAR(50) NOT NULL, -- hexagram, liuyao, meihua, bazi
    content JSONB NOT NULL,
    result JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 创建索引以提高查询性能
CREATE INDEX idx_user_history_user_id ON user_history(user_id);
CREATE INDEX idx_user_history_type ON user_history(type);
CREATE INDEX idx_user_history_created_at ON user_history(created_at DESC);

-- 6. 用户收藏表
CREATE TABLE user_favorites (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    item_id VARCHAR(100) NOT NULL,
    type VARCHAR(50) NOT NULL,
    content JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, item_id, type)
);

-- 7. 用户设置表
CREATE TABLE user_settings (
    user_id VARCHAR(255) PRIMARY KEY,
    theme VARCHAR(20) DEFAULT 'light',
    language VARCHAR(10) DEFAULT 'zh-CN',
    notifications_enabled BOOLEAN DEFAULT TRUE,
    auto_sync BOOLEAN DEFAULT TRUE,
    custom_settings JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 8. AI解读记录表
CREATE TABLE interpretations (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    type VARCHAR(50) NOT NULL,
    data JSONB NOT NULL,
    aspect VARCHAR(50),
    question TEXT,
    interpretation TEXT NOT NULL,
    ai_model VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 9. 卦象浏览统计表
CREATE TABLE hexagram_views (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    hexagram_id INTEGER NOT NULL,
    user_id VARCHAR(255),
    viewed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 创建统计索引
CREATE INDEX idx_hexagram_views_hexagram_id ON hexagram_views(hexagram_id);
CREATE INDEX idx_hexagram_views_viewed_at ON hexagram_views(viewed_at DESC);

-- 10. 搜索日志表
CREATE TABLE search_logs (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    query TEXT NOT NULL,
    results_count INTEGER,
    user_id VARCHAR(255),
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 创建更新时间触发器
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_hexagrams_updated_at BEFORE UPDATE ON hexagrams
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_settings_updated_at BEFORE UPDATE ON user_settings
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 插入初始数据（前6卦示例）
INSERT INTO hexagrams (number, name, symbol, upper_trigram, lower_trigram, description, interpretation, fortune, advice) VALUES
(1, '乾卦', '☰☰', '乾', '乾', '元亨利贞', '乾卦象征天，代表刚健、积极、创造的力量。君子应当自强不息。', '大吉', '宜进取，不宜退守'),
(2, '坤卦', '☷☷', '坤', '坤', '元亨，利牝马之贞', '坤卦象征地，代表柔顺、包容、承载的品德。君子应当厚德载物。', '吉', '宜守正，顺势而为'),
(3, '屯卦', '☵☳', '坎', '震', '元亨利贞，勿用有攸往', '屯卦象征初生，事物刚刚开始，充满困难但也充满希望。', '吉凶参半', '宜守待时机'),
(4, '蒙卦', '☶☵', '艮', '坎', '亨。匪我求童蒙，童蒙求我', '蒙卦象征启蒙，需要教育和引导，虚心学习。', '吉', '宜求教学习'),
(5, '需卦', '☵☰', '坎', '乾', '有孚，光亨，贞吉', '需卦象征等待，须有耐心，时机成熟自然成功。', '吉', '宜耐心等待'),
(6, '讼卦', '☰☵', '乾', '坎', '有孚窒惕，中吉终凶', '讼卦象征争讼，应避免冲突，以和为贵。', '凶', '宜和解，避免争端');

-- 创建搜索索引数据
INSERT INTO search_index (type, item_id, title, content, tags, category) 
SELECT 
    'hexagram',
    number,
    name,
    name || ' ' || description || ' ' || interpretation || ' ' || COALESCE(advice, ''),
    ARRAY[fortune, upper_trigram, lower_trigram],
    '易经64卦'
FROM hexagrams;

-- 创建视图以方便查询
CREATE VIEW v_hexagram_stats AS
SELECT 
    h.id,
    h.number,
    h.name,
    COUNT(DISTINCT hv.id) as view_count,
    COUNT(DISTINCT uf.id) as favorite_count
FROM hexagrams h
LEFT JOIN hexagram_views hv ON h.number = hv.hexagram_id
LEFT JOIN user_favorites uf ON uf.item_id = h.number::text AND uf.type = 'hexagram'
GROUP BY h.id, h.number, h.name
ORDER BY view_count DESC;

-- 设置行级安全策略 (RLS)
ALTER TABLE user_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_favorites ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_settings ENABLE ROW LEVEL SECURITY;

-- 创建策略：用户只能访问自己的数据
CREATE POLICY "Users can view own history" ON user_history
    FOR ALL USING (user_id = current_user OR user_id = 'anonymous');

CREATE POLICY "Users can manage own favorites" ON user_favorites
    FOR ALL USING (user_id = current_user OR user_id = 'anonymous');

CREATE POLICY "Users can manage own settings" ON user_settings
    FOR ALL USING (user_id = current_user OR user_id = 'anonymous');

-- 授予公共访问权限（只读）
GRANT SELECT ON hexagrams TO anon;
GRANT SELECT ON yao_texts TO anon;
GRANT SELECT ON search_index TO anon;
GRANT SELECT ON v_hexagram_stats TO anon;

-- 授予认证用户权限
GRANT ALL ON user_history TO authenticated;
GRANT ALL ON user_favorites TO authenticated;
GRANT ALL ON user_settings TO authenticated;
GRANT INSERT ON hexagram_views TO authenticated;
GRANT INSERT ON search_logs TO authenticated;
GRANT INSERT ON interpretations TO authenticated;