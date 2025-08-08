# 易经卦象云端服务架构

## 🎨 架构图

```mermaid
graph TB
    subgraph "Client Layer"
        A[Flutter App] --> B[Web App]
        B --> C[Mobile App]
    end
    
    subgraph "CDN Layer"
        D[Vercel Edge Network]
        E[Cloudflare CDN]
    end
    
    subgraph "API Gateway"
        F[Vercel Serverless Functions]
        F --> G[/api/hexagram]
        F --> H[/api/search]
        F --> I[/api/interpret]
        F --> J[/api/sync]
    end
    
    subgraph "Data Layer"
        K[Supabase PostgreSQL]
        L[Supabase Storage]
        M[Redis Cache - Optional]
    end
    
    subgraph "AI Services"
        N[Cloudflare Workers AI]
        O[OpenAI API - Optional]
    end
    
    A --> D
    B --> D
    C --> D
    D --> F
    F --> K
    F --> L
    F --> N
    F --> O
    D --> E
```

## 💰 成本分析（月度）

### 免费套餐方案 （$0/月）

| 服务 | 免费额度 | 预计使用 | 成本 |
|------|---------|---------|------|
| **Vercel** | | | |
| - Serverless Functions | 100,000 次/月 | 50,000 次 | $0 |
| - 带宽 | 100GB/月 | 50GB | $0 |
| - 构建时间 | 6,000 分钟/月 | 1,000 分钟 | $0 |
| **Supabase** | | | |
| - 数据库 | 500MB | 100MB | $0 |
| - API调用 | 无限 | - | $0 |
| - 存储 | 1GB | 500MB | $0 |
| - 活跃用户 | 50,000/月 | 10,000 | $0 |
| **Cloudflare** | | | |
| - Workers AI | 10,000 次/日 | 5,000 次/日 | $0 |
| - CDN | 无限 | - | $0 |
| **总计** | | | **$0** |

### 基础付费方案 （$25/月）

| 服务 | 套餐 | 额度 | 成本 |
|------|------|------|------|
| Vercel Pro | Pro | 1TB 带宽, 1M 函数调用 | $20 |
| Supabase | - | 继续免费 | $0 |
| Cloudflare Workers | Paid | 10M 请求 | $5 |
| **总计** | | | **$25** |

### 企业级方案 （$150+/月）

| 服务 | 套餐 | 额度 | 成本 |
|------|------|------|------|
| Vercel Enterprise | Custom | 自定义 | $150+ |
| Supabase Pro | Pro | 8GB 数据库, 100GB 存储 | $25 |
| Redis Cloud | Pro | 250MB, 25K ops/s | $15 |
| OpenAI API | - | GPT-3.5 100K tokens | $10 |
| **总计** | | | **$200+** |

## 🚀 性能指标

### 响应时间 (P95)
- API 响应: < 200ms
- 静态资源: < 50ms (CDN)
- 数据库查询: < 100ms
- AI 解读: < 3s

### 可用性
- SLA: 99.9% (免费套餐)
- SLA: 99.95% (Pro套餐)
- 多区域备份: 自动

### 扩展性
- 自动横向扩展: ✅
- 按需计费: ✅
- 无服务器管理: ✅

## 🔒 安全特性

### 网络安全
- HTTPS/TLS 1.3: ✅
- DDoS 防护: ✅ (Cloudflare)
- WAF: ✅ (Vercel Shield)
- Rate Limiting: ✅

### 数据安全
- 加密存储: ✅
- 加密传输: ✅
- 备份: 每日自动
- RLS (行级安全): ✅

### 认证与授权
- JWT Token: ✅
- OAuth 2.0: ✅ (Supabase Auth)
- API Key: ✅
- RBAC: ✅

## 📊 监控与告警

### Vercel Analytics
- 实时流量监控
- 函数执行时间
- 错误率跟踪
- 成本预警

### Supabase Dashboard
- 数据库性能
- API 调用统计
- 存储使用量
- 实时日志

## 🛠️ 部署流程

```bash
# 1. 克隆项目
git clone <your-repo>
cd yigua_app

# 2. 运行部署脚本
chmod +x deploy.sh
./deploy.sh

# 3. 选择部署方式
# - 完整部署 (包括Supabase)
# - 仅API部署
# - 本地开发
```

## 📈 扩容策略

### 自动扩容触发条件
1. **CPU 使用率** > 70% 持续 5 分钟
2. **内存使用率** > 80%
3. **请求队列** > 100
4. **响应时间** > 1s

### 扩容策略
```yaml
scaling:
  min_instances: 0
  max_instances: 100
  target_cpu: 70
  scale_up_rate: 2x
  scale_down_rate: 0.5x
  cooldown: 60s
```

## 🔄 灾难恢复

### RTO (Recovery Time Objective)
- 免费套餐: 4 小时
- Pro 套餐: 1 小时
- Enterprise: 15 分钟

### RPO (Recovery Point Objective)
- 数据库: 24 小时
- 文件: 实时同步
- 配置: Git 版本控制

### 备份策略
1. **数据库备份**
   - 每日全量备份
   - 每小时增量备份
   - 保留 30 天

2. **代码备份**
   - Git 版本控制
   - 多分支策略
   - Tag 重要版本

## 📝 最佳实践

### API 设计
- RESTful 风格
- JSON 响应格式
- 版本控制 (/api/v1/)
- 限流保护

### 数据库优化
- 索引优化
- 查询缓存
- 连接池
- 读写分离 (可选)

### 缓存策略
- CDN 缓存静态资源
- API 响应缓存 (1小时)
- 数据库查询缓存
- 浏览器缓存

## 🌍 多区域部署

### 推荐区域
1. **亚洲**: 
   - 香港 (hkg1) - 主要
   - 新加坡 (sin1) - 备用
   
2. **全球**:
   - 美国西部 (sfo1)
   - 欧洲 (fra1)

### 路由策略
- GeoDNS 智能解析
- 就近访问原则
- 故障自动转移

## 📧 联系方式

- **技术支持**: support@yigua-app.com
- **GitHub**: https://github.com/your-repo
- **文档**: https://docs.yigua-app.com