// Vercel Serverless Function - 获取单个卦象
// API路径: /api/hexagram/{id}

import { createClient } from '@supabase/supabase-js';

// 初始化Supabase客户端
const supabase = createClient(
  process.env.SUPABASE_URL,
  process.env.SUPABASE_ANON_KEY
);

// 64卦完整数据（作为备用，当数据库不可用时使用）
const hexagramsData = [
  {
    number: 1,
    name: '乾卦',
    symbol: '☰☰',
    trigrams: { upper: '乾', lower: '乾' },
    description: '元亨利贞',
    interpretation: '乾卦象征天，代表刚健、积极、创造的力量。君子应当自强不息。',
    fortune: '大吉',
    advice: '宜进取，不宜退守'
  },
  {
    number: 2,
    name: '坤卦',
    symbol: '☷☷',
    trigrams: { upper: '坤', lower: '坤' },
    description: '元亨，利牝马之贞',
    interpretation: '坤卦象征地，代表柔顺、包容、承载的品德。君子应当厚德载物。',
    fortune: '吉',
    advice: '宜守正，顺势而为'
  },
  {
    number: 3,
    name: '屯卦',
    symbol: '☵☳',
    trigrams: { upper: '坎', lower: '震' },
    description: '元亨利贞，勿用有攸往',
    interpretation: '屯卦象征初生，事物刚刚开始，充满困难但也充满希望。',
    fortune: '吉凶参半',
    advice: '宜守待时机'
  },
  {
    number: 4,
    name: '蒙卦',
    symbol: '☶☵',
    trigrams: { upper: '艮', lower: '坎' },
    description: '亨。匪我求童蒙，童蒙求我',
    interpretation: '蒙卦象征启蒙，需要教育和引导，虚心学习。',
    fortune: '吉',
    advice: '宜求教学习'
  },
  {
    number: 5,
    name: '需卦',
    symbol: '☵☰',
    trigrams: { upper: '坎', lower: '乾' },
    description: '有孚，光亨，贞吉',
    interpretation: '需卦象征等待，须有耐心，时机成熟自然成功。',
    fortune: '吉',
    advice: '宜耐心等待'
  },
  {
    number: 6,
    name: '讼卦',
    symbol: '☰☵',
    trigrams: { upper: '乾', lower: '坎' },
    description: '有孚窒惕，中吉终凶',
    interpretation: '讼卦象征争讼，应避免冲突，以和为贵。',
    fortune: '凶',
    advice: '宜和解，避免争端'
  },
  // ... 这里可以继续添加剩余的58个卦象
];

export default async function handler(req, res) {
  // 设置CORS头
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  // 处理OPTIONS请求
  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }

  // 只允许GET请求
  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  const { id } = req.query;

  // 验证ID
  const hexagramId = parseInt(id);
  if (isNaN(hexagramId) || hexagramId < 1 || hexagramId > 64) {
    return res.status(400).json({ error: 'Invalid hexagram ID. Must be between 1 and 64.' });
  }

  try {
    // 首先尝试从Supabase获取数据
    if (process.env.SUPABASE_URL && process.env.SUPABASE_ANON_KEY) {
      const { data, error } = await supabase
        .from('hexagrams')
        .select('*')
        .eq('number', hexagramId)
        .single();

      if (!error && data) {
        // 记录访问次数
        await supabase
          .from('hexagram_views')
          .insert({ hexagram_id: hexagramId, viewed_at: new Date().toISOString() })
          .catch(() => {}); // 忽略统计错误

        return res.status(200).json({
          success: true,
          data: data,
          source: 'database'
        });
      }
    }

    // 如果数据库不可用，使用本地数据
    const hexagram = hexagramsData.find(h => h.number === hexagramId);
    
    if (hexagram) {
      return res.status(200).json({
        success: true,
        data: hexagram,
        source: 'cache'
      });
    }

    // 如果没有找到数据
    return res.status(404).json({ 
      error: 'Hexagram not found',
      hexagramId 
    });

  } catch (error) {
    console.error('Error fetching hexagram:', error);
    
    // 降级到本地数据
    const hexagram = hexagramsData.find(h => h.number === hexagramId);
    if (hexagram) {
      return res.status(200).json({
        success: true,
        data: hexagram,
        source: 'fallback'
      });
    }

    return res.status(500).json({ 
      error: 'Internal server error',
      message: error.message 
    });
  }
}