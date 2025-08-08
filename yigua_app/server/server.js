const express = require('express');
const cors = require('cors');
const fs = require('fs');
const path = require('path');

const app = express();
const PORT = 8888;

// 启用CORS，允许手机访问
app.use(cors());
app.use(express.json());

// 读取数据文件
const hexagramsData = JSON.parse(
  fs.readFileSync(path.join(__dirname, '../assets/data/hexagrams.json'), 'utf8')
);

// 根路径 - 显示欢迎页面
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
          font-family: Arial, sans-serif;
          max-width: 800px;
          margin: 50px auto;
          padding: 20px;
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          color: white;
        }
        h1 { text-align: center; }
        .status {
          background: rgba(255,255,255,0.2);
          padding: 20px;
          border-radius: 10px;
          margin: 20px 0;
        }
        .api-list {
          background: rgba(255,255,255,0.1);
          padding: 20px;
          border-radius: 10px;
        }
        a {
          color: #ffd700;
          text-decoration: none;
        }
        a:hover {
          text-decoration: underline;
        }
        code {
          background: rgba(0,0,0,0.2);
          padding: 2px 5px;
          border-radius: 3px;
        }
      </style>
    </head>
    <body>
      <h1>🔮 易卦API服务器</h1>
      <div class="status">
        <h2>✅ 服务器运行中</h2>
        <p>版本: ${hexagramsData.version || '1.0.0'}</p>
        <p>卦象数量: ${hexagramsData.hexagrams.length}/64</p>
        <p>更新时间: ${hexagramsData.updated_at || '2024-01-01'}</p>
      </div>
      
      <div class="api-list">
        <h2>📡 可用的API端点</h2>
        <ul>
          <li><a href="/api/health">/api/health</a> - 健康检查</li>
          <li><a href="/api/hexagrams">/api/hexagrams</a> - 获取所有卦象</li>
          <li><a href="/api/hexagrams/1">/api/hexagrams/1</a> - 获取乾卦</li>
          <li><a href="/api/search?q=乾">/api/search?q=乾</a> - 搜索卦象</li>
          <li><a href="/api/version">/api/version</a> - 版本信息</li>
        </ul>
      </div>
      
      <div class="api-list">
        <h2>📱 手机APP连接</h2>
        <p>在APP设置中输入此IP地址：</p>
        <p><code>http://${localIP}:${PORT}</code></p>
      </div>
    </body>
    </html>
  `);
});

// API路由
app.get('/api/health', (req, res) => {
  res.json({ status: 'ok', message: '易卦服务器运行中' });
});

// 获取所有卦象
app.get('/api/hexagrams', (req, res) => {
  res.json(hexagramsData.hexagrams);
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
    return res.json([]);
  }
  
  const results = hexagramsData.hexagrams.filter(h => 
    h.name.includes(q) || 
    h.meaning.includes(q) ||
    h.judgment.includes(q)
  );
  
  res.json(results);
});

// 获取版本信息
app.get('/api/version', (req, res) => {
  res.json({
    version: hexagramsData.version || '1.0.0',
    updated_at: hexagramsData.updated_at,
    total_hexagrams: hexagramsData.hexagrams.length
  });
});

// 获取本机IP地址
const os = require('os');
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

// 启动服务器
app.listen(PORT, '0.0.0.0', () => {
  const localIP = getLocalIP();
  console.log('🚀 易卦服务器已启动！');
  console.log(`📱 局域网访问地址: http://${localIP}:${PORT}`);
  console.log(`💻 本地访问地址: http://localhost:${PORT}`);
  console.log('\n请在手机APP中使用局域网地址连接');
});