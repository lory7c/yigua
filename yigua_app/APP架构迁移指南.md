# 📱 易卦APP架构迁移指南

## 🎯 迁移目标

将APP从**离线优先架构**迁移到**服务器中心化架构**，实现所有数据和智能功能都在服务器端。

## 🏗️ 新架构说明

### 旧架构（离线优先）
```
APP（包含所有数据）
  ├── 本地SQLite数据库
  ├── 内置JSON数据文件
  └── 离线计算逻辑
```

### 新架构（服务器中心）
```
APP（纯展示层）
  ├── API调用层
  ├── 状态管理
  └── UI展示
       ↓ API请求
服务器（数据+智能）
  ├── 完整64卦数据
  ├── 占卜算法
  ├── AI智能解析
  └── 用户数据
```

## 📂 新增文件结构

```
lib/
├── config/
│   └── app_config.dart          # APP配置管理（API模式切换）
├── services/
│   ├── api_service.dart         # API服务层（所有HTTP请求）
│   └── data_service_api.dart    # 数据服务（使用API）
├── providers/
│   └── app_data_provider.dart   # 全局数据状态管理
└── screens/
    └── settings_screen.dart      # 设置页面（API配置）
```

## 🔄 迁移步骤

### 第1步：安装新文件
✅ 已完成 - 创建了以下新文件：
- `api_service.dart` - API调用服务
- `data_service_api.dart` - 新的数据服务
- `app_data_provider.dart` - 状态管理
- `app_config.dart` - 配置管理

### 第2步：修改main.dart
✅ 已完成 - 使用新的Provider：
```dart
// 旧代码
ChangeNotifierProvider(create: (_) => DataService())

// 新代码
ChangeNotifierProvider(create: (_) => AppDataProvider())
```

### 第3步：修改页面文件
需要修改所有页面，从直接访问本地数据改为使用Provider：

#### 示例：修改YijingScreen
```dart
// 旧代码
final dataService = DataService.instance;
final hexagrams = await dataService.getAllHexagrams();

// 新代码
final provider = Provider.of<AppDataProvider>(context, listen: false);
final hexagrams = await provider.loadHexagrams();
```

### 第4步：添加加载状态UI
在每个页面添加加载指示器：
```dart
Consumer<AppDataProvider>(
  builder: (context, provider, child) {
    if (provider.isLoading) {
      return Center(child: CircularProgressIndicator());
    }
    if (provider.errorMessage != null) {
      return Center(child: Text(provider.errorMessage!));
    }
    // 显示数据
    return ListView(...);
  },
)
```

## 🔌 API端点映射

| 功能 | 旧方法 | 新API端点 |
|------|--------|-----------|
| 获取64卦 | 读取本地JSON | GET /api/hexagrams |
| 六爻起卦 | 本地计算 | POST /api/divination/liuyao |
| 梅花易数 | 本地计算 | POST /api/divination/meihua |
| 八字排盘 | 本地计算 | POST /api/divination/bazi |
| 解梦查询 | 本地数据库 | GET /api/dreams/search |
| 黄历查询 | 本地数据 | GET /api/calendar/today |
| AI问答 | 不支持 | POST /api/ai/ask |
| 智能解卦 | 不支持 | POST /api/ai/interpret |

## 🔧 配置说明

### API模式配置
APP支持3种模式：
1. **local** - 本地模式（离线，使用内置数据）
2. **lan** - 局域网模式（连接本地服务器）
3. **internet** - 公网模式（连接云服务器）

### 在设置页面切换模式
```dart
// 切换到局域网模式
await provider.switchApiMode(
  AppConfig.ApiMode.lan,
  apiUrl: 'http://192.168.1.84:8888/api'
);
```

## 📝 待完成任务

### 页面迁移清单
- [ ] home_screen_v2.dart - 首页
- [ ] yijing_screen.dart - 易经页面
- [ ] liuyao_screen.dart - 六爻页面
- [ ] meihua_screen.dart - 梅花易数
- [ ] bazi_screen.dart - 八字页面
- [ ] dream_screen_v2.dart - 解梦页面
- [ ] calendar_screen_v2.dart - 黄历页面
- [ ] history_screen.dart - 历史记录
- [ ] study_screen.dart - 学习页面
- [ ] settings_screen.dart - 设置页面

### 服务器端任务
- [ ] 导入完整64卦数据（等Allen完成）
- [ ] 实现所有占卜算法API
- [ ] 部署Python RAG系统
- [ ] 实现AI智能解析
- [ ] 添加用户系统

## 🚀 测试步骤

### 1. 启动服务器
```bash
cd server
node server.js
```

### 2. 配置APP连接
在APP设置页面：
1. 选择"局域网模式"
2. 输入服务器地址：`http://192.168.1.84:8888/api`
3. 点击"测试连接"
4. 保存配置

### 3. 验证功能
- ✅ 能否获取卦象列表
- ✅ 能否进行占卜计算
- ✅ 能否保存历史记录
- ✅ 能否使用AI功能（需要服务器支持）

## ⚠️ 注意事项

1. **网络依赖**：新架构需要网络连接才能使用完整功能
2. **数据缓存**：APP会缓存部分数据以提高性能
3. **离线降级**：本地模式仍保留基本功能
4. **API兼容**：服务器API需要保持向后兼容

## 🔄 回滚方案

如果需要回滚到旧架构：
1. 在`main.dart`中改回使用`DataService`
2. 删除新增的API相关文件
3. 恢复页面中的本地数据访问代码

## 📊 迁移进度

- [x] 创建API服务层
- [x] 创建新的数据服务
- [x] 创建状态管理Provider
- [x] 修改main.dart
- [ ] 迁移所有页面
- [ ] 添加错误处理UI
- [ ] 完整测试
- [ ] 部署到生产环境

## 🎉 迁移完成标志

当以下条件都满足时，迁移完成：
1. APP能正常连接服务器
2. 所有占卜功能通过API调用
3. AI功能正常工作
4. 历史记录同步到服务器
5. 用户体验流畅无卡顿

---

**最后更新**：2025-08-08
**状态**：进行中（70%完成）