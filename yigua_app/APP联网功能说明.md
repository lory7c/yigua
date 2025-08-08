# 📱 易卦APP联网功能说明

## 🌐 联网模式

APP支持3种数据模式：
1. **本地模式（离线）** - 使用内置数据，无需联网
2. **局域网模式** - 连接电脑服务器
3. **公网模式** - 通过ngrok等工具连接

## 📡 需要联网的功能

### 1. 数据同步功能
**位置**：`lib/repositories/sync_repository.dart`
**用途**：
- 同步最新的64卦数据
- 更新周公解梦数据库
- 下载最新黄历信息
- 获取版本更新

**API端点**：
```
GET  /api/sync/check    - 检查更新
GET  /api/sync/hexagrams - 同步卦象数据
GET  /api/sync/dreams    - 同步解梦数据
GET  /api/sync/calendar  - 同步黄历数据
```

### 2. 智能解卦功能（未来）
**用途**：
- AI智能解析卦象
- 个性化解释生成
- 历史案例匹配

**API端点**：
```
POST /api/interpret     - 智能解卦
POST /api/qa/ask       - 智能问答
```

### 3. 用户数据备份（未来）
**用途**：
- 备份占卜历史
- 同步收藏夹
- 跨设备数据同步

**API端点**：
```
POST /api/user/backup   - 上传备份
GET  /api/user/restore  - 恢复数据
```

### 4. 社区功能（未来）
**用途**：
- 分享占卜结果
- 查看他人解读
- 专家在线咨询

**API端点**：
```
GET  /api/community/posts  - 获取帖子
POST /api/community/share  - 分享内容
```

## 🔌 当前已实现的API

服务器端（`server/server.js`）已实现：
```javascript
✅ GET  /             - 欢迎页面
✅ GET  /api/health    - 健康检查
✅ GET  /api/hexagrams - 获取所有卦象
✅ GET  /api/hexagrams/:id - 获取单个卦象
✅ GET  /api/search    - 搜索功能
✅ GET  /api/version   - 版本信息
```

## 🎯 联网配置方式

### 在APP设置页面配置
**位置**：`lib/screens/settings_screen.dart`

用户可以：
1. 选择数据模式（本地/局域网/公网）
2. 输入服务器地址
3. 测试连接
4. 保存配置

### 配置存储
**位置**：`lib/config/app_config.dart`
```dart
// 默认局域网地址
static const String DEFAULT_API_URL = 'http://192.168.1.84:8888/api';

// 三种模式
enum ApiMode {
  local,      // 本地模式（不联网）
  lan,        // 局域网模式
  internet,   // 公网模式
}
```

## 📊 数据流程

```
APP启动
  ↓
检查配置模式
  ↓
┌─────────────┬─────────────┬─────────────┐
本地模式        局域网模式      公网模式
  ↓              ↓              ↓
读取内置数据    连接局域网服务器  连接公网服务器
  ↓              ↓              ↓
显示数据        获取最新数据      获取最新数据
```

## 🔒 离线优先策略

APP采用**离线优先**设计：
1. 核心数据内置在APP中（2个卦示例）
2. 联网时自动同步完整数据
3. 断网后使用本地缓存
4. 所有功能都有离线备选方案

## ⚙️ 网络库使用

**HTTP请求**：使用 `http` 包
**状态管理**：使用 `Provider` 模式
**本地存储**：使用 `SQLite` 数据库
**缓存管理**：使用 `SharedPreferences`

## 🚀 未来扩展

### 第一阶段（当前）
- ✅ 局域网数据同步
- ✅ 基础API接口
- ⏳ 完整64卦数据

### 第二阶段
- AI智能解卦
- 用户账号系统
- 云端备份

### 第三阶段
- 社区功能
- 专家咨询
- 付费内容

## 📝 总结

**当前状态**：
- APP可以完全离线运行
- 局域网模式可选，用于数据更新
- 已预留所有联网接口

**给用户的建议**：
1. 日常使用选择"本地模式"，速度最快
2. 需要更新数据时切换到"局域网模式"
3. 确保手机和电脑在同一WiFi网络

---

**注意**：目前服务器只有2个卦的示例数据，等Allen完成64卦数据收集后，APP将拥有完整的离线数据库！