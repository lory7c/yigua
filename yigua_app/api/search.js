// Vercel Serverless Function - 全文搜索
const { createClient } = require('@supabase/supabase-js');

// 初始化Supabase客户端
const supabase = createClient(
  process.env.SUPABASE_URL,
  process.env.SUPABASE_ANON_KEY
);

// 本地搜索数据（备用）
const searchableData = [
  {
    type: 'hexagram',
    id: 1,
    title: '乾卦',
    content: '元亨利贞 乾卦象征天 刚健 积极 创造 自强不息',
    tags: ['大吉', '进取', '阳刚', '天'],
    category: '易经64卦'
  },
  {
    type: 'hexagram',
    id: 2,
    title: '坤卦',
    content: '元亨利牝马之贞 坤卦象征地 柔顺 包容 承载 厚德载物',
    tags: ['吉', '守正', '阴柔', '地'],
    category: '易经64卦'
  },
  {
    type: 'knowledge',
    id: 101,
    title: '八卦基础',
    content: '乾坤震巽坎离艮兑 天地雷风水火山泽',
    tags: ['基础知识', '八卦'],
    category: '易学基础'
  },
  {
    type: 'liuyao',
    id: 201,
    title: '六爻起卦法',
    content: '铜钱起卦 摇卦方法 爻辞解读',
    tags: ['六爻', '占卜方法'],
    category: '六爻预测'
  },
  {
    type: 'meihua',
    id: 301,
    title: '梅花易数',
    content: '时间起卦 数字起卦 体用互变',
    tags: ['梅花易', '起卦法'],
    category: '梅花易数'
  }
];

module.exports = async (req, res) => {
  // 设置CORS头
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  // 处理OPTIONS请求
  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }

  // 获取搜索参数
  const { q, type, category, limit = 20, offset = 0 } = req.method === 'GET' ? req.query : req.body;

  if (!q || q.trim().length === 0) {
    return res.status(400).json({ 
      error: 'Search query is required',
      hint: 'Please provide a search term in the "q" parameter' 
    });
  }

  const searchTerm = q.toLowerCase().trim();

  try {
    // 尝试使用Supabase进行全文搜索
    if (process.env.SUPABASE_URL && process.env.SUPABASE_ANON_KEY) {
      let query = supabase
        .from('search_index')
        .select('*')
        .textSearch('content', searchTerm, {
          type: 'websearch',
          config: 'chinese'
        });

      // 添加类型过滤
      if (type) {
        query = query.eq('type', type);
      }

      // 添加分类过滤
      if (category) {
        query = query.eq('category', category);
      }

      // 分页
      query = query.range(offset, offset + limit - 1);

      const { data, error, count } = await query;

      if (!error && data) {
        // 记录搜索日志
        await supabase
          .from('search_logs')
          .insert({ 
            query: searchTerm, 
            results_count: data.length,
            timestamp: new Date().toISOString() 
          })
          .catch(() => {});

        return res.status(200).json({
          success: true,
          query: q,
          results: data,
          total: count || data.length,
          limit,
          offset,
          source: 'database'
        });
      }
    }

    // 降级到本地搜索
    let results = searchableData.filter(item => {
      // 全文搜索
      const matchContent = item.content.toLowerCase().includes(searchTerm) ||
                          item.title.toLowerCase().includes(searchTerm) ||
                          item.tags.some(tag => tag.toLowerCase().includes(searchTerm));
      
      // 类型过滤
      const matchType = !type || item.type === type;
      
      // 分类过滤
      const matchCategory = !category || item.category === category;
      
      return matchContent && matchType && matchCategory;
    });

    // 计算相关度并排序
    results = results.map(item => {
      let score = 0;
      
      // 标题匹配权重最高
      if (item.title.toLowerCase().includes(searchTerm)) score += 10;
      
      // 标签匹配
      item.tags.forEach(tag => {
        if (tag.toLowerCase().includes(searchTerm)) score += 5;
      });
      
      // 内容匹配
      if (item.content.toLowerCase().includes(searchTerm)) score += 1;
      
      return { ...item, relevance: score };
    }).sort((a, b) => b.relevance - a.relevance);

    // 分页
    const paginatedResults = results.slice(offset, offset + limit);

    return res.status(200).json({
      success: true,
      query: q,
      results: paginatedResults,
      total: results.length,
      limit,
      offset,
      source: 'local'
    });

  } catch (error) {
    console.error('Search error:', error);
    return res.status(500).json({ 
      error: 'Search failed',
      message: error.message 
    });
  }
};