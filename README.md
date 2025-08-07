# 易卦算甲 - Flutter应用

一个基于Flutter开发的传统文化学习应用，包含易经占卜、周公解梦、老黄历等功能。

## 功能特点

- 🔮 易经六十四卦占卜
- 💭 周公解梦
- 📅 老黄历查询
- 📝 历史记录保存
- 🌓 支持深色模式

## 安装运行

### 前置要求

1. 安装Flutter SDK (3.0+)
2. 安装Android Studio或VS Code
3. 配置Android模拟器或连接真机

### 运行步骤

```bash
# 1. 进入项目目录
cd yigua_app

# 2. 获取依赖
flutter pub get

# 3. 运行应用
flutter run

# 4. 构建APK
flutter build apk --release
```

## 项目结构

```
yigua_app/
├── lib/
│   ├── main.dart              # 应用入口
│   ├── screens/               # 页面文件
│   │   ├── home_screen.dart   # 主页
│   │   ├── yijing_screen.dart # 易经占卜
│   │   ├── dream_screen.dart  # 周公解梦
│   │   ├── calendar_screen.dart # 老黄历
│   │   └── history_screen.dart  # 历史记录
│   ├── models/                # 数据模型
│   │   └── hexagram.dart      # 卦象模型
│   ├── services/              # 服务层
│   │   ├── yijing_service.dart # 易经服务
│   │   └── data_service.dart   # 数据服务
│   └── utils/                 # 工具类
├── assets/                    # 资源文件
│   ├── images/               # 图片资源
│   └── data/                 # 数据文件
└── pubspec.yaml              # 项目配置

```

## 主要依赖

- `provider`: 状态管理
- `http`: 网络请求
- `shared_preferences`: 本地存储
- `url_launcher`: 打开外部链接

## 注意事项

1. 本应用仅供学习传统文化使用
2. 占卜结果仅供参考，不应作为决策依据
3. 尊重传统文化，理性看待

## 后续优化

- [ ] 添加更多卦象数据
- [ ] 实现本地数据缓存
- [ ] 添加分享功能
- [ ] 优化UI动画效果
- [ ] 添加更多占卜方法

## 开发环境

- Flutter 3.0+
- Dart 3.0+
- Android SDK 21+