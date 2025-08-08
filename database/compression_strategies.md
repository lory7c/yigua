# SQLite数据压缩策略
## 目标：核心数据包 < 10MB

### 1. 数据库层面压缩

#### 1.1 VACUUM和页面优化
```sql
-- 页面大小优化 (4KB页面，适合SSD)
PRAGMA page_size = 4096;

-- 自动VACUUM模式
PRAGMA auto_vacuum = INCREMENTAL;

-- 压缩数据库
VACUUM;

-- 重建索引以减少碎片
REINDEX;
```

#### 1.2 数据类型优化
```sql
-- 使用紧凑的数据类型
-- INTEGER (1,2,3,4,6,8字节变长存储)
-- TEXT (UTF-8编码，变长)
-- REAL (8字节IEEE浮点)
-- BLOB (二进制，最紧凑)

-- 示例：将枚举字符串转换为整型
ALTER TABLE interpretations ADD COLUMN category_id INTEGER;
UPDATE interpretations SET category_id = 
    CASE category 
        WHEN '传统注解' THEN 1
        WHEN '现代解释' THEN 2  
        WHEN '占断要诀' THEN 3
        ELSE 4
    END;
```

### 2. 内容压缩策略

#### 2.1 文本内容去重和归一化
```python
def normalize_content(text: str) -> str:
    """文本内容标准化和去重"""
    import re
    
    # 去除多余空白
    text = re.sub(r'\s+', ' ', text.strip())
    
    # 统一标点符号
    text = text.replace('，', ',').replace('。', '.')
    text = text.replace('：', ':').replace('；', ';')
    
    # 去除重复段落
    paragraphs = text.split('\n')
    unique_paragraphs = []
    seen = set()
    
    for para in paragraphs:
        para_clean = para.strip()
        if para_clean and para_clean not in seen:
            unique_paragraphs.append(para_clean)
            seen.add(para_clean)
    
    return '\n'.join(unique_paragraphs)
```

#### 2.2 内容引用表 (Content Deduplication)
```sql
-- 创建内容引用表，避免重复存储
CREATE TABLE content_blocks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content_hash TEXT UNIQUE NOT NULL,
    content TEXT NOT NULL,
    usage_count INTEGER DEFAULT 0
);

-- 修改主表使用引用
CREATE TABLE interpretations_v2 (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    target_type INTEGER NOT NULL,
    target_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    content_block_id INTEGER NOT NULL,
    -- 其他字段...
    FOREIGN KEY (content_block_id) REFERENCES content_blocks(id)
);

-- 内容去重插入示例
INSERT OR IGNORE INTO content_blocks (content_hash, content) 
VALUES (?, ?);

INSERT INTO interpretations_v2 (target_type, target_id, title, content_block_id)
SELECT ?, ?, ?, id FROM content_blocks WHERE content_hash = ?;
```

### 3. 智能数据分层

#### 3.1 核心数据优选算法
```python
def select_core_content(quality_threshold: float = 0.9) -> List[int]:
    """选择核心数据的智能算法"""
    
    # 质量权重 (40%)
    quality_weight = 0.4
    
    # 使用频率权重 (30%) - 基于标签使用次数
    usage_weight = 0.3
    
    # 内容丰富度权重 (20%)
    richness_weight = 0.2
    
    # 权威性权重 (10%) - 基于作者和来源
    authority_weight = 0.1
    
    sql = """
    SELECT id, 
           (quality_score * ? + 
            usage_score * ? + 
            richness_score * ? + 
            authority_score * ?) as composite_score
    FROM (
        SELECT i.id,
               i.quality_score,
               COALESCE(t.avg_usage, 0) / 100.0 as usage_score,
               LEAST(1.0, LENGTH(i.content) / 500.0) as richness_score,
               CASE 
                   WHEN i.author IS NOT NULL AND i.source_book IS NOT NULL THEN 1.0
                   WHEN i.author IS NOT NULL OR i.source_book IS NOT NULL THEN 0.7
                   ELSE 0.3
               END as authority_score
        FROM interpretations i
        LEFT JOIN (
            SELECT ct.content_id, AVG(t.usage_count) as avg_usage
            FROM content_tags ct 
            JOIN tags t ON ct.tag_id = t.id
            WHERE ct.content_type = 3  -- interpretations
            GROUP BY ct.content_id
        ) t ON i.id = t.content_id
    )
    ORDER BY composite_score DESC
    """
    
    return execute_sql(sql, [quality_weight, usage_weight, richness_weight, authority_weight])
```

#### 3.2 动态数据分层
```sql
-- 创建数据分层规则表
CREATE TABLE tier_rules (
    id INTEGER PRIMARY KEY,
    table_name TEXT NOT NULL,
    rule_type TEXT NOT NULL, -- 'include' or 'exclude'
    condition_sql TEXT NOT NULL,
    target_tier INTEGER NOT NULL,
    priority INTEGER DEFAULT 0
);

-- 插入分层规则
INSERT INTO tier_rules (table_name, rule_type, condition_sql, target_tier, priority) VALUES
('hexagrams', 'include', 'quality_score >= 0.95', 1, 100),
('interpretations', 'include', 'quality_score >= 0.9 AND author IS NOT NULL', 1, 90),
('divination_cases', 'include', 'accuracy_rating >= 0.8 AND result_verification IS NOT NULL', 1, 80),
('interpretations', 'exclude', 'LENGTH(content) < 100', 3, 10);

-- 自动应用分层规则
UPDATE interpretations 
SET data_tier = 1 
WHERE quality_score >= 0.9 AND author IS NOT NULL;
```

### 4. 压缩算法应用

#### 4.1 GZIP压缩大文本字段
```python
import gzip
import base64

def compress_large_content(text: str, threshold: int = 500) -> tuple:
    """压缩大型文本内容"""
    if len(text) < threshold:
        return text, False
    
    compressed = gzip.compress(text.encode('utf-8'))
    if len(compressed) < len(text.encode('utf-8')) * 0.8:  # 压缩率>20%才采用
        return base64.b64encode(compressed).decode('ascii'), True
    
    return text, False

def decompress_content(data: str, is_compressed: bool) -> str:
    """解压缩内容"""
    if not is_compressed:
        return data
    
    compressed = base64.b64decode(data.encode('ascii'))
    return gzip.decompress(compressed).decode('utf-8')
```

#### 4.2 数据库架构调整
```sql
-- 添加压缩标记字段
ALTER TABLE interpretations ADD COLUMN content_compressed BOOLEAN DEFAULT FALSE;
ALTER TABLE divination_cases ADD COLUMN analysis_compressed BOOLEAN DEFAULT FALSE;

-- 创建压缩内容视图
CREATE VIEW interpretations_view AS
SELECT id, target_type, target_id, title,
       CASE 
           WHEN content_compressed = 1 THEN '[COMPRESSED]'
           ELSE content 
       END as content,
       author, source_book, data_tier, quality_score
FROM interpretations;
```

### 5. 索引优化减少存储

#### 5.1 部分索引策略
```sql
-- 只为高频查询的数据建索引
CREATE INDEX idx_core_hexagrams_name ON hexagrams(name) WHERE data_tier = 1;
CREATE INDEX idx_quality_interpretations ON interpretations(quality_score) WHERE quality_score >= 0.8;

-- 复合部分索引
CREATE INDEX idx_core_cases_method ON divination_cases(method, difficulty_level) 
WHERE data_tier <= 2 AND accuracy_rating >= 0.7;
```

#### 5.2 表达式索引
```sql
-- 为计算字段建表达式索引
CREATE INDEX idx_content_length ON interpretations(LENGTH(content)) 
WHERE data_tier <= 2;

-- 哈希索引用于精确匹配
CREATE INDEX idx_content_hash ON interpretations(substr(content, 1, 50));
```

### 6. 存储格式优化

#### 6.1 JSON字段压缩
```sql
-- 将changing_lines从TEXT改为紧凑存储
-- 原来: "[1,3,5]" (7字节)
-- 优化: BLOB存储 (3字节)

CREATE TABLE changing_lines_compact (
    case_id INTEGER PRIMARY KEY,
    lines_bitmap INTEGER  -- 用位图存储: 第1,3,5爻 = 21 (10101二进制)
);

-- 转换函数
CREATE FUNCTION lines_to_bitmap(json_text TEXT) RETURNS INTEGER AS $$
    SELECT SUM(1 << (line_pos - 1)) 
    FROM json_each(json_text) 
    WHERE value BETWEEN 1 AND 6;
$$;
```

#### 6.2 符号和枚举优化
```sql
-- 卦象符号使用整数编码
CREATE TABLE symbol_encoding (
    symbol TEXT PRIMARY KEY,
    code INTEGER UNIQUE
);

INSERT INTO symbol_encoding VALUES 
('☰', 1), ('☱', 2), ('☲', 3), ('☳', 4),
('☴', 5), ('☵', 6), ('☶', 7), ('☷', 8);

-- 更新主表
ALTER TABLE hexagrams ADD COLUMN symbol_code INTEGER;
UPDATE hexagrams SET symbol_code = (SELECT code FROM symbol_encoding WHERE symbol = hexagrams.symbol);
```

### 7. 应用层压缩策略

#### 7.1 延迟加载 (Lazy Loading)
```python
class CompactHexagram:
    """紧凑型卦象模型，按需加载详细内容"""
    def __init__(self, id: int, name: str, symbol_code: int):
        self.id = id
        self.name = name
        self.symbol_code = symbol_code
        self._judgment = None
        self._lines = None
    
    @property
    def judgment(self) -> str:
        if self._judgment is None:
            self._judgment = db.fetch_judgment(self.id)
        return self._judgment
    
    @property
    def lines(self) -> List:
        if self._lines is None:
            self._lines = db.fetch_lines(self.id)
        return self._lines
```

#### 7.2 缓存策略
```python
import functools
from typing import LRU_Cache

@functools.lru_cache(maxsize=128)
def get_hexagram_interpretation(hex_id: int, category: int) -> str:
    """缓存高频访问的解释内容"""
    return db.fetch_interpretation(hex_id, category)
```

### 8. 数据包构建策略

#### 8.1 核心包优化算法
```python
def build_core_package(target_size_mb: float = 5.0) -> Dict:
    """构建核心数据包"""
    
    # 1. 必需数据 (64卦 + 384爻)
    essential_size = estimate_essential_data_size()
    remaining_size = target_size_mb - essential_size
    
    # 2. 按优先级添加可选内容
    priority_content = [
        ('interpretations', 'quality_score >= 0.95', 0.6),  # 60%权重给高质量解释
        ('divination_cases', 'accuracy_rating >= 0.9', 0.3),  # 30%权重给案例
        ('knowledge_relationships', 'strength >= 0.8', 0.1)   # 10%权重给关系
    ]
    
    selected_content = {}
    
    for table, condition, weight in priority_content:
        allocated_size = remaining_size * weight
        content_ids = select_content_by_size(table, condition, allocated_size)
        selected_content[table] = content_ids
    
    return selected_content

def estimate_content_size(table: str, ids: List[int]) -> float:
    """估算内容大小 (MB)"""
    sql = f"""
    SELECT SUM(LENGTH(content)) / (1024.0 * 1024.0) as size_mb
    FROM {table} WHERE id IN ({','.join(map(str, ids))})
    """
    return execute_scalar(sql)
```

#### 8.2 增量更新包
```sql
-- 创建数据包版本表
CREATE TABLE data_packages (
    id INTEGER PRIMARY KEY,
    version TEXT NOT NULL,
    package_type TEXT NOT NULL, -- 'core', 'extended', 'incremental'
    size_mb REAL,
    content_hash TEXT,
    created_at INTEGER DEFAULT (strftime('%s', 'now'))
);

-- 创建增量更新表
CREATE TABLE package_updates (
    id INTEGER PRIMARY KEY,
    base_version TEXT NOT NULL,
    target_version TEXT NOT NULL,
    update_type TEXT NOT NULL, -- 'insert', 'update', 'delete'
    table_name TEXT NOT NULL,
    record_id INTEGER NOT NULL,
    change_data TEXT -- JSON格式的变更数据
);
```

### 9. 监控和优化指标

#### 9.1 压缩效果监控
```sql
-- 创建压缩统计视图
CREATE VIEW compression_stats AS
SELECT 
    'Database Size' as metric,
    (SELECT page_count * page_size / (1024.0 * 1024.0) FROM pragma_page_count(), pragma_page_size()) as value_mb,
    'MB' as unit
UNION ALL
SELECT 
    'Core Package Size' as metric,
    SUM(
        CASE 
            WHEN name = 'hexagrams' THEN pgsize * pgno
            WHEN name LIKE 'lines%' THEN pgsize * pgno  
            WHEN name LIKE 'interpretations%' AND sql LIKE '%data_tier = 1%' THEN pgsize * pgno
            ELSE 0
        END
    ) / (1024.0 * 1024.0) as value_mb,
    'MB' as unit
FROM dbstat
WHERE name NOT LIKE 'sqlite_%';
```

#### 9.2 性能基准测试
```python
def benchmark_compression_performance():
    """压缩性能基准测试"""
    import time
    
    # 测试查询性能
    queries = [
        "SELECT name FROM hexagrams WHERE data_tier = 1",
        "SELECT content FROM interpretations WHERE quality_score >= 0.9 LIMIT 10",
        "SELECT * FROM hexagrams_fts WHERE hexagrams_fts MATCH '天龙'"
    ]
    
    results = {}
    for query in queries:
        start_time = time.time()
        execute_query(query)
        end_time = time.time()
        results[query] = end_time - start_time
    
    return results
```

### 10. 部署和分发策略

#### 10.1 多层级数据包
```
yigua_core.db (< 5MB)
├── 64卦基础数据
├── 384爻辞
├── 高质量解释 (精选)
└── 核心索引

yigua_extended.db (< 50MB) 
├── 包含core所有内容
├── 更多解释和注释
├── 占卜案例集
└── 知识图谱关系

yigua_cloud.db (完整版)
├── 所有历史文献
├── 完整案例库
├── 多版本对比
└── 用户生成内容
```

#### 10.2 智能同步策略
```python
def sync_package_updates(current_version: str, target_version: str):
    """智能增量同步"""
    
    # 1. 获取更新列表
    updates = fetch_incremental_updates(current_version, target_version)
    
    # 2. 计算更新大小
    total_size = sum(len(update.change_data) for update in updates)
    
    # 3. 选择同步策略
    if total_size < 1024 * 1024:  # < 1MB，增量更新
        apply_incremental_updates(updates)
    else:  # > 1MB，重新下载
        download_full_package(target_version)
```

### 总结

通过以上压缩策略的组合应用，可以实现：

1. **核心包目标 < 5MB**
   - 数据库本身: ~2MB
   - 64卦+384爻: ~1MB  
   - 精选解释: ~1.5MB
   - 索引开销: ~0.5MB

2. **扩展包目标 < 50MB**
   - 完整解释库: ~30MB
   - 案例集合: ~15MB
   - 知识图谱: ~3MB
   - 其他数据: ~2MB

3. **性能保证**
   - 核心查询 < 10ms
   - 全文搜索 < 50ms
   - 批量操作 < 100ms

4. **存储效率**
   - 文本压缩率: 40-60%
   - 去重节省: 20-30%
   - 索引优化: 30-40%