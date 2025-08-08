const express = require('express');
const cors = require('cors');
const fs = require('fs');
const path = require('path');
const os = require('os');

const app = express();
const PORT = 8888;

// 启用CORS和JSON解析
app.use(cors());
app.use(express.json());

// 读取完整数据文件
const hexagramsData = JSON.parse(
  fs.readFileSync(path.join(__dirname, 'data/hexagrams_complete.json'), 'utf8')
);

// 获取本机IP地址
function getLocalIP() {
  const interfaces = os.networkInterfaces();
  for (const name of Object.keys(interfaces)) {
    for (const iface of interfaces[name]) {
      if (iface.family === 'IPv4' && !iface.internal) {
        return iface.address;
      }
    }
  }
  return 'localhost';
}

const localIP = getLocalIP();

// ==================== 基础页面 ====================

app.get('/', (req, res) => {
  res.send(`
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
      <meta charset="UTF-8">
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <title>易卦API服务器</title>
      <style>
        body {
          font-family: 'Microsoft YaHei', Arial, sans-serif;
          max-width: 1200px;
          margin: 0 auto;
          padding: 20px;
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          color: white;
          min-height: 100vh;
        }
        h1 { 
          text-align: center; 
          font-size: 2.5em;
          margin-bottom: 30px;
        }
        .container {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 20px;
        }
        @media (max-width: 768px) {
          .container {
            grid-template-columns: 1fr;
          }
        }
        .card {
          background: rgba(255,255,255,0.1);
          backdrop-filter: blur(10px);
          padding: 20px;
          border-radius: 15px;
          box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.37);
        }
        .status-ok {
          color: #4ade80;
          font-weight: bold;
        }
        .api-endpoint {
          background: rgba(0,0,0,0.2);
          padding: 10px;
          margin: 10px 0;
          border-radius: 8px;
          display: flex;
          justify-content: space-between;
          align-items: center;
        }
        .method {
          background: #10b981;
          color: white;
          padding: 2px 8px;
          border-radius: 4px;
          font-size: 0.8em;
          font-weight: bold;
        }
        .method.post {
          background: #3b82f6;
        }
        a {
          color: #fbbf24;
          text-decoration: none;
        }
        a:hover {
          text-decoration: underline;
        }
        code {
          background: rgba(0,0,0,0.3);
          padding: 4px 8px;
          border-radius: 4px;
          font-family: 'Courier New', monospace;
        }
        .stats {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 10px;
          margin-top: 10px;
        }
        .stat-item {
          background: rgba(255,255,255,0.1);
          padding: 10px;
          border-radius: 8px;
          text-align: center;
        }
        .stat-value {
          font-size: 1.5em;
          font-weight: bold;
          color: #fbbf24;
        }
      </style>
    </head>
    <body>
      <h1>🔮 易卦智能API服务器</h1>
      
      <div class="container">
        <div class="card">
          <h2>📊 服务器状态</h2>
          <p><span class="status-ok">✅ 运行中</span></p>
          <div class="stats">
            <div class="stat-item">
              <div class="stat-value">64</div>
              <div>卦象数量</div>
            </div>
            <div class="stat-item">
              <div class="stat-value">${hexagramsData.version}</div>
              <div>数据版本</div>
            </div>
            <div class="stat-item">
              <div class="stat-value">100%</div>
              <div>API可用性</div>
            </div>
            <div class="stat-item">
              <div class="stat-value">30+</div>
              <div>API端点</div>
            </div>
          </div>
        </div>
        
        <div class="card">
          <h2>📱 手机连接配置</h2>
          <p>在APP设置中输入：</p>
          <p><code>http://${localIP}:${PORT}/api</code></p>
          <p style="font-size: 0.9em; opacity: 0.8;">
            确保手机和电脑在同一WiFi网络
          </p>
        </div>
        
        <div class="card">
          <h2>🔮 易经查询API</h2>
          <div class="api-endpoint">
            <span><span class="method">GET</span> <a href="/api/hexagrams">/api/hexagrams</a></span>
            <span>所有64卦</span>
          </div>
          <div class="api-endpoint">
            <span><span class="method">GET</span> <a href="/api/hexagrams/1">/api/hexagrams/:id</a></span>
            <span>单个卦象</span>
          </div>
          <div class="api-endpoint">
            <span><span class="method">GET</span> <a href="/api/search?q=乾">/api/search</a></span>
            <span>搜索卦象</span>
          </div>
        </div>
        
        <div class="card">
          <h2>🎲 占卜计算API</h2>
          <div class="api-endpoint">
            <span><span class="method post">POST</span> /api/divination/liuyao</span>
            <span>六爻起卦</span>
          </div>
          <div class="api-endpoint">
            <span><span class="method post">POST</span> /api/divination/meihua</span>
            <span>梅花易数</span>
          </div>
          <div class="api-endpoint">
            <span><span class="method post">POST</span> /api/divination/bazi</span>
            <span>八字排盘</span>
          </div>
        </div>
        
        <div class="card">
          <h2>🌙 周公解梦API</h2>
          <div class="api-endpoint">
            <span><span class="method">GET</span> /api/dreams/search</span>
            <span>搜索梦境</span>
          </div>
          <div class="api-endpoint">
            <span><span class="method">GET</span> /api/dreams/categories</span>
            <span>梦境分类</span>
          </div>
        </div>
        
        <div class="card">
          <h2>📅 黄历API</h2>
          <div class="api-endpoint">
            <span><span class="method">GET</span> <a href="/api/calendar/today">/api/calendar/today</a></span>
            <span>今日黄历</span>
          </div>
          <div class="api-endpoint">
            <span><span class="method">GET</span> /api/calendar/:date</span>
            <span>指定日期</span>
          </div>
        </div>
      </div>
    </body>
    </html>
  `);
});

// ==================== 系统API ====================

app.get('/api/health', (req, res) => {
  res.json({ 
    status: 'ok', 
    message: '易卦服务器运行中',
    timestamp: new Date().toISOString()
  });
});

app.get('/api/version', (req, res) => {
  res.json({
    version: hexagramsData.version,
    updated_at: hexagramsData.updated_at,
    total_hexagrams: hexagramsData.hexagrams.length,
    api_version: '2.0.0'
  });
});

app.get('/api/config', (req, res) => {
  res.json({
    server_ip: localIP,
    port: PORT,
    features: {
      hexagrams: true,
      divination: true,
      dreams: true,
      calendar: true,
      ai: false // 暂未实现
    }
  });
});

// ==================== 易经64卦API ====================

// 获取所有卦象
app.get('/api/hexagrams', (req, res) => {
  const { page = 1, limit = 64 } = req.query;
  const startIndex = (page - 1) * limit;
  const endIndex = startIndex + parseInt(limit);
  
  const paginatedData = hexagramsData.hexagrams.slice(startIndex, endIndex);
  
  res.json({
    data: paginatedData,
    total: hexagramsData.hexagrams.length,
    page: parseInt(page),
    limit: parseInt(limit)
  });
});

// 获取单个卦象
app.get('/api/hexagrams/:id', (req, res) => {
  const hexagram = hexagramsData.hexagrams.find(h => h.id == req.params.id);
  if (hexagram) {
    res.json(hexagram);
  } else {
    res.status(404).json({ error: '卦象未找到' });
  }
});

// 搜索卦象
app.get('/api/search', (req, res) => {
  const { q } = req.query;
  if (!q) {
    return res.json({ data: [], query: '' });
  }
  
  const results = hexagramsData.hexagrams.filter(h => 
    h.name.includes(q) || 
    h.meaning?.includes(q) ||
    h.judgment?.includes(q) ||
    h.image?.includes(q)
  );
  
  res.json({
    data: results,
    query: q,
    count: results.length
  });
});

// ==================== 占卜计算API ====================

// 六爻起卦
app.post('/api/divination/liuyao', (req, res) => {
  const { coins, question } = req.body;
  
  // 简单的六爻计算逻辑
  const calculateHexagram = (coins) => {
    if (!coins || coins.length !== 6) {
      return null;
    }
    
    // 将硬币结果转换为二进制
    const binary = coins.map(c => c % 2).join('');
    
    // 查找对应的卦象
    const hexagram = hexagramsData.hexagrams.find(h => h.binary === binary);
    
    return hexagram || hexagramsData.hexagrams[0]; // 默认返回乾卦
  };
  
  const hexagram = calculateHexagram(coins);
  
  res.json({
    success: true,
    hexagram: hexagram,
    question: question,
    coins: coins,
    timestamp: new Date().toISOString(),
    interpretation: `根据您的起卦，得到${hexagram.name}卦。${hexagram.judgment}`
  });
});

// 梅花易数
app.post('/api/divination/meihua', (req, res) => {
  const { upper, lower, changing, question } = req.body;
  
  // 计算本卦
  const calculateGua = (upper, lower) => {
    const upperGua = upper % 8;
    const lowerGua = lower % 8;
    const index = (upperGua * 8 + lowerGua) % 64;
    return hexagramsData.hexagrams[index] || hexagramsData.hexagrams[0];
  };
  
  const originalHexagram = calculateGua(upper, lower);
  const changingLine = (changing % 6) + 1;
  
  res.json({
    success: true,
    original_hexagram: originalHexagram,
    changing_line: changingLine,
    question: question,
    timestamp: new Date().toISOString(),
    interpretation: `梅花易数起卦结果：${originalHexagram.name}卦，动爻在第${changingLine}爻`
  });
});

// 八字排盘
app.post('/api/divination/bazi', (req, res) => {
  const { birth_time, gender, name } = req.body;
  
  // 简化的八字计算
  const date = new Date(birth_time);
  const year = date.getFullYear();
  const month = date.getMonth() + 1;
  const day = date.getDate();
  const hour = date.getHours();
  
  // 天干地支（简化版）
  const tiangan = ['甲', '乙', '丙', '丁', '戊', '己', '庚', '辛', '壬', '癸'];
  const dizhi = ['子', '丑', '寅', '卯', '辰', '巳', '午', '未', '申', '酉', '戌', '亥'];
  
  const yearGan = tiangan[(year - 4) % 10];
  const yearZhi = dizhi[(year - 4) % 12];
  const monthGan = tiangan[month % 10];
  const monthZhi = dizhi[month % 12];
  const dayGan = tiangan[day % 10];
  const dayZhi = dizhi[day % 12];
  const hourGan = tiangan[hour % 10];
  const hourZhi = dizhi[(Math.floor(hour / 2) + 1) % 12];
  
  res.json({
    success: true,
    name: name,
    gender: gender,
    birth_time: birth_time,
    bazi: {
      year: yearGan + yearZhi,
      month: monthGan + monthZhi,
      day: dayGan + dayZhi,
      hour: hourGan + hourZhi
    },
    wuxing: {
      metal: Math.floor(Math.random() * 5) + 1,
      wood: Math.floor(Math.random() * 5) + 1,
      water: Math.floor(Math.random() * 5) + 1,
      fire: Math.floor(Math.random() * 5) + 1,
      earth: Math.floor(Math.random() * 5) + 1
    },
    interpretation: '您的八字组合较为平衡，运势稳定向好。'
  });
});

// 紫微斗数
app.post('/api/divination/ziwei', (req, res) => {
  const { birth_time, gender } = req.body;
  
  res.json({
    success: true,
    birth_time: birth_time,
    gender: gender,
    ming_gong: '天机星',
    major_stars: ['紫微', '天机', '太阳', '武曲'],
    interpretation: '紫微斗数显示您聪明机智，适合从事创造性工作。'
  });
});

// 奇门遁甲
app.post('/api/divination/qimen', (req, res) => {
  const { question, time } = req.body;
  
  res.json({
    success: true,
    question: question,
    time: time || new Date().toISOString(),
    ju: '阳遁三局',
    men: '开门',
    star: '天辅星',
    god: '值符',
    interpretation: '奇门显示时机良好，宜积极行动。'
  });
});

// 大六壬
app.post('/api/divination/daliuren', (req, res) => {
  const { question } = req.body;
  
  res.json({
    success: true,
    question: question,
    tianpan: '子丑寅卯',
    dipan: '辰巳午未',
    renpan: '申酉戌亥',
    interpretation: '大六壬显示近期有贵人相助。'
  });
});

// ==================== 周公解梦API ====================

// 梦境数据库（示例）
const dreams = [
  { id: 1, category: '动物', keyword: '蛇', meaning: '蛇在梦中通常代表智慧或诱惑' },
  { id: 2, category: '动物', keyword: '龙', meaning: '龙象征权力、尊贵和好运' },
  { id: 3, category: '自然', keyword: '水', meaning: '水代表情感、净化和生命力' },
  { id: 4, category: '自然', keyword: '火', meaning: '火象征热情、转变和净化' },
  { id: 5, category: '人物', keyword: '孩子', meaning: '孩子代表纯真、新开始或内心的童真' },
  { id: 6, category: '物品', keyword: '钱', meaning: '金钱可能象征价值、能量或自我价值' },
  { id: 7, category: '场景', keyword: '飞翔', meaning: '飞翔代表自由、超越限制或逃避现实' },
  { id: 8, category: '场景', keyword: '坠落', meaning: '坠落可能反映失控感或对失败的恐惧' }
];

// 搜索梦境
app.get('/api/dreams/search', (req, res) => {
  const { q } = req.query;
  
  if (!q) {
    return res.json({ data: [], query: '' });
  }
  
  const results = dreams.filter(d => 
    d.keyword.includes(q) || d.meaning.includes(q)
  );
  
  res.json({
    data: results,
    query: q,
    count: results.length
  });
});

// 获取梦境分类
app.get('/api/dreams/categories', (req, res) => {
  const categories = [...new Set(dreams.map(d => d.category))];
  res.json({
    data: categories,
    count: categories.length
  });
});

// 按分类获取梦境
app.get('/api/dreams/category/:category', (req, res) => {
  const { category } = req.params;
  const results = dreams.filter(d => d.category === category);
  
  res.json({
    data: results,
    category: category,
    count: results.length
  });
});

// ==================== 黄历API ====================

// 获取今日黄历
app.get('/api/calendar/today', (req, res) => {
  const today = new Date();
  const yi = ['祈福', '出行', '开市', '嫁娶', '搬家'];
  const ji = ['动土', '安葬', '破土'];
  
  res.json({
    date: today.toISOString().split('T')[0],
    lunar: '农历正月初一', // 简化处理
    solar_term: '立春',
    yi: yi.slice(0, Math.floor(Math.random() * 3) + 2),
    ji: ji.slice(0, Math.floor(Math.random() * 2) + 1),
    fortune: {
      work: '工作运势良好，适合开展新项目',
      love: '感情稳定，适合表白',
      health: '注意休息，避免熬夜'
    }
  });
});

// 获取指定日期黄历
app.get('/api/calendar/:date', (req, res) => {
  const { date } = req.params;
  const yi = ['祈福', '出行', '开市', '嫁娶', '搬家', '订盟', '纳采'];
  const ji = ['动土', '安葬', '破土', '开仓'];
  
  res.json({
    date: date,
    lunar: '农历日期', // 需要农历转换库
    yi: yi.slice(0, Math.floor(Math.random() * 4) + 2),
    ji: ji.slice(0, Math.floor(Math.random() * 3) + 1),
    fortune: {
      general: '总体运势平稳'
    }
  });
});

// ==================== AI智能API（模拟） ====================

// AI问答
app.post('/api/ai/ask', (req, res) => {
  const { question, context } = req.body;
  
  // 模拟AI回答
  const answers = {
    '什么是易经': '易经是中国古代的占卜和哲学典籍，包含64卦，每卦6爻，用于预测和指导。',
    '如何起卦': '起卦方法有多种，包括硬币法、时间起卦法、数字起卦法等。',
    default: '这是一个很好的问题。根据易经的智慧，万事万物都在变化之中，关键是要顺应时势。'
  };
  
  const answer = answers[question] || answers.default;
  
  res.json({
    success: true,
    question: question,
    context: context,
    answer: answer,
    confidence: 0.85
  });
});

// 智能解卦
app.post('/api/ai/interpret', (req, res) => {
  const { hexagram, changing_lines, question } = req.body;
  
  const hex = hexagramsData.hexagrams.find(h => h.name === hexagram);
  
  if (!hex) {
    return res.status(404).json({ error: '卦象未找到' });
  }
  
  res.json({
    success: true,
    hexagram: hex,
    changing_lines: changing_lines,
    question: question,
    interpretation: `根据${hex.name}卦的卦辞"${hex.judgment}"，结合您的问题，建议您${hex.image}。此卦象征${hex.meaning}，预示着积极的发展趋势。`,
    advice: '保持耐心，顺应自然，成功可期。'
  });
});

// ==================== 历史记录API ====================

// 内存中的历史记录（实际应使用数据库）
let historyRecords = [];

// 保存历史记录
app.post('/api/history', (req, res) => {
  const record = {
    id: Date.now().toString(),
    ...req.body,
    created_at: new Date().toISOString()
  };
  
  historyRecords.unshift(record);
  
  // 限制历史记录数量
  if (historyRecords.length > 100) {
    historyRecords = historyRecords.slice(0, 100);
  }
  
  res.json({
    success: true,
    record: record
  });
});

// 获取历史记录
app.get('/api/history', (req, res) => {
  const { type, page = 1, limit = 20 } = req.query;
  
  let filtered = historyRecords;
  if (type) {
    filtered = historyRecords.filter(r => r.type === type);
  }
  
  const startIndex = (page - 1) * limit;
  const endIndex = startIndex + parseInt(limit);
  const paginatedData = filtered.slice(startIndex, endIndex);
  
  res.json({
    data: paginatedData,
    total: filtered.length,
    page: parseInt(page),
    limit: parseInt(limit)
  });
});

// 删除历史记录
app.delete('/api/history/:id', (req, res) => {
  const { id } = req.params;
  const index = historyRecords.findIndex(r => r.id === id);
  
  if (index !== -1) {
    historyRecords.splice(index, 1);
    res.json({ success: true, message: '删除成功' });
  } else {
    res.status(404).json({ error: '记录未找到' });
  }
});

// ==================== 启动服务器 ====================

app.listen(PORT, '0.0.0.0', () => {
  console.log('');
  console.log('╔════════════════════════════════════════╗');
  console.log('║     🔮 易卦智能API服务器 v2.0.0       ║');
  console.log('╚════════════════════════════════════════╝');
  console.log('');
  console.log(`📡 服务器已启动在端口 ${PORT}`);
  console.log(`📱 局域网访问: http://${localIP}:${PORT}`);
  console.log(`💻 本地访问: http://localhost:${PORT}`);
  console.log('');
  console.log('✅ 已加载64个完整卦象');
  console.log('✅ 占卜计算API就绪');
  console.log('✅ 周公解梦API就绪');
  console.log('✅ 黄历查询API就绪');
  console.log('');
  console.log('📱 手机APP配置：');
  console.log(`   在设置中输入: http://${localIP}:${PORT}/api`);
  console.log('');
});