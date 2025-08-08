// Vercel Serverless Function - AI解读
// 使用Cloudflare Workers AI或OpenAI API

const { createClient } = require('@supabase/supabase-js');

// 初始化Supabase客户端
const supabase = createClient(
  process.env.SUPABASE_URL,
  process.env.SUPABASE_ANON_KEY
);

// AI解读模板
const interpretationTemplates = {
  hexagram: {
    career: '根据{name}的卦象含义，在事业方面{interpretation}',
    relationship: '从{name}的角度看感情，{interpretation}',
    health: '健康方面，{name}提示{interpretation}',
    finance: '财运上，{name}表示{interpretation}'
  },
  liuyao: {
    general: '六爻卦象显示{interpretation}',
    timing: '时机方面{interpretation}',
    action: '行动建议{interpretation}'
  }
};

// 使用Cloudflare Workers AI进行AI解读
async function getAIInterpretation(prompt, context) {
  if (process.env.CF_ACCOUNT_ID && process.env.CF_API_TOKEN) {
    try {
      const response = await fetch(
        `https://api.cloudflare.com/client/v4/accounts/${process.env.CF_ACCOUNT_ID}/ai/run/@cf/meta/llama-2-7b-chat-int8`,
        {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${process.env.CF_API_TOKEN}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            prompt: `${context}\n\n${prompt}\n\n请用中文回答：`,
            max_tokens: 256,
            temperature: 0.7
          })
        }
      );

      const data = await response.json();
      if (data.success && data.result) {
        return data.result.response;
      }
    } catch (error) {
      console.error('Cloudflare AI error:', error);
    }
  }

  // 备用：使用OpenAI API（需要API密钥）
  if (process.env.OPENAI_API_KEY) {
    try {
      const response = await fetch('https://api.openai.com/v1/chat/completions', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${process.env.OPENAI_API_KEY}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          model: 'gpt-3.5-turbo',
          messages: [
            { role: 'system', content: '你是一位精通易经的大师，请根据卦象给出专业解读。' },
            { role: 'user', content: `${context}\n${prompt}` }
          ],
          max_tokens: 256,
          temperature: 0.7
        })
      });

      const data = await response.json();
      if (data.choices && data.choices[0]) {
        return data.choices[0].message.content;
      }
    } catch (error) {
      console.error('OpenAI API error:', error);
    }
  }

  // 如果没有AI服务可用，返回预设解读
  return null;
}

// 预设解读数据
const presetInterpretations = {
  1: {
    career: '事业蕴勃发展，宜积极进取，勇于开拓新领域。领导力强，适合担任重要职位。',
    relationship: '感情主动积极，宜大胆表达。单身者有望遇到良缘，已婚者关系稳定。',
    health: '身体健康，精力充沛。注意劳逸结合，避免过度劳累。',
    finance: '财运亨通，正财偏财俱佳。投资有利，但需谨慎决策。',
    general: '大吉大利，万事亨通。适合开展新计划，勇于进取。'
  },
  2: {
    career: '宜守正待时，不宜冒进。以柔克刚，顺势而为，可获成功。',
    relationship: '以柔情打动人心，包容理解是关键。宜守不宜攻。',
    health: '注意脾胃保养，饮食要有节制。适当运动，增强体质。',
    finance: '财运平稳，宜保守理财。不宜冒险投资，稳健为上。',
    general: '吉利平和，以静制动。宜守正待时，顺应自然。'
  }
};

module.exports = async (req, res) => {
  // 设置CORS头
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  // 处理OPTIONS请求
  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }

  // 只允许POST请求
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  const { 
    type = 'hexagram',  // hexagram, liuyao, meihua, bazi
    data,               // 卦象数据
    aspect = 'general', // general, career, relationship, health, finance
    question           // 用户的具体问题
  } = req.body;

  if (!data) {
    return res.status(400).json({ 
      error: 'Data is required',
      hint: 'Please provide hexagram or divination data' 
    });
  }

  try {
    // 构建AI提示词
    let prompt = '';
    let context = '';

    if (type === 'hexagram' && data.number) {
      context = `卦象：${data.name || ''}（第${data.number}卦）\n` +
                `卦辞：${data.description || ''}\n` +
                `基本含义：${data.interpretation || ''}`;
      
      if (question) {
        prompt = `针对问题"${question}"，请根据${data.name}的卦象含义给出解读和建议。`;
      } else {
        prompt = `请从${aspect === 'career' ? '事业' : 
                         aspect === 'relationship' ? '感情' :
                         aspect === 'health' ? '健康' :
                         aspect === 'finance' ? '财运' : '综合'}方面解读这个卦象。`;
      }
    }

    // 尝试获取AI解读
    let interpretation = await getAIInterpretation(prompt, context);

    // 如果AI解读失败，使用预设解读
    if (!interpretation) {
      if (data.number && presetInterpretations[data.number]) {
        interpretation = presetInterpretations[data.number][aspect] || 
                        presetInterpretations[data.number].general;
      } else {
        // 生成基础解读
        interpretation = `根据${data.name || '卦象'}的含义，${data.interpretation || '此卦象富有深意，需要结合具体情况分析。'}`;
      }
    }

    // 保存解读记录到数据库
    if (process.env.SUPABASE_URL && process.env.SUPABASE_ANON_KEY) {
      await supabase
        .from('interpretations')
        .insert({
          type,
          data: JSON.stringify(data),
          aspect,
          question,
          interpretation,
          created_at: new Date().toISOString()
        })
        .catch(() => {}); // 忽略保存错误
    }

    // 返回解读结果
    return res.status(200).json({
      success: true,
      interpretation,
      type,
      aspect,
      hexagram: data.name || null,
      suggestions: [
        '请结合实际情况参考',
        '易经智慧需要灵活运用',
        '建议多角度思考问题'
      ],
      timestamp: new Date().toISOString()
    });

  } catch (error) {
    console.error('Interpretation error:', error);
    return res.status(500).json({ 
      error: 'Failed to generate interpretation',
      message: error.message 
    });
  }
};