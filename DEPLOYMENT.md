# 📱 易卦移动应用部署指南

## 📋 目录

- [环境准备](#环境准备)
- [本地开发](#本地开发)
- [Android构建](#android构建)
- [iOS构建](#ios构建)
- [GitHub Actions自动化](#github-actions自动化)
- [发布流程](#发布流程)
- [常见问题](#常见问题)

## 环境准备

### 系统要求

| 平台 | 最低要求 | 推荐配置 |
|------|----------|----------|
| **开发机** | 8GB RAM, 50GB磁盘 | 16GB RAM, 100GB SSD |
| **Android** | API 21 (5.0) | API 28+ (9.0+) |
| **iOS** | iOS 11.0 | iOS 14.0+ |
| **Flutter** | 3.19.0 | 最新稳定版 |

### 开发环境搭建

#### 1. 安装Flutter

```bash
# Windows (PowerShell)
git clone https://github.com/flutter/flutter.git -b stable
$env:Path += ";C:\flutter\bin"

# macOS/Linux
git clone https://github.com/flutter/flutter.git -b stable
export PATH="$PATH:`pwd`/flutter/bin"

# 验证安装
flutter doctor
```

#### 2. 安装Android Studio

```bash
# 下载并安装Android Studio
# https://developer.android.com/studio

# 配置Android SDK
flutter config --android-sdk /path/to/android/sdk

# 接受许可
flutter doctor --android-licenses
```

#### 3. 配置开发环境

```bash
# 检查环境
flutter doctor -v

# 应该看到类似输出:
# [✓] Flutter (Channel stable, 3.19.0)
# [✓] Android toolchain
# [✓] Chrome - develop for the web
# [✓] Android Studio
# [✓] VS Code
# [✓] Connected device
```

## 本地开发

### 项目设置

```bash
# 克隆项目
git clone https://github.com/lory7c/yigua.git
cd yigua/yigua_app

# 安装依赖
flutter pub get

# 生成代码
flutter pub run build_runner build
```

### 运行应用

```bash
# 列出可用设备
flutter devices

# 在指定设备运行
flutter run -d <device_id>

# 调试模式
flutter run --debug

# 性能模式
flutter run --profile

# 发布模式
flutter run --release
```

### 热重载开发

```bash
# 启动应用后
# r - 热重载
# R - 热重启
# h - 帮助
# q - 退出
```

## Android构建

### 配置签名

#### 1. 生成密钥库

```bash
keytool -genkey -v -keystore ~/yigua-key.jks \
  -keyalg RSA -keysize 2048 -validity 10000 \
  -alias yigua
```

#### 2. 配置 `android/key.properties`

```properties
storePassword=<密钥库密码>
keyPassword=<密钥密码>
keyAlias=yigua
storeFile=../../yigua-key.jks
```

#### 3. 修改 `android/app/build.gradle`

```gradle
def keystoreProperties = new Properties()
def keystorePropertiesFile = rootProject.file('key.properties')
if (keystorePropertiesFile.exists()) {
    keystoreProperties.load(new FileInputStream(keystorePropertiesFile))
}

android {
    signingConfigs {
        release {
            keyAlias keystoreProperties['keyAlias']
            keyPassword keystoreProperties['keyPassword']
            storeFile keystoreProperties['storeFile'] ? file(keystoreProperties['storeFile']) : null
            storePassword keystoreProperties['storePassword']
        }
    }
    buildTypes {
        release {
            signingConfig signingConfigs.release
        }
    }
}
```

### 构建APK

```bash
# 构建APK（通用）
flutter build apk --release

# 构建APK（分架构）
flutter build apk --split-per-abi

# 构建App Bundle（推荐）
flutter build appbundle --release

# 输出位置
# APK: build/app/outputs/flutter-apk/app-release.apk
# AAB: build/app/outputs/bundle/release/app-release.aab
```

### 性能优化配置

```gradle
// android/app/build.gradle
android {
    buildTypes {
        release {
            minifyEnabled true
            shrinkResources true
            proguardFiles getDefaultProguardFile('proguard-android-optimize.txt'), 'proguard-rules.pro'
            
            ndk {
                abiFilters 'armeabi-v7a', 'arm64-v8a'
            }
        }
    }
}
```

## iOS构建

### Xcode配置

```bash
# 打开iOS项目
cd ios
open Runner.xcworkspace

# 或使用Flutter命令
flutter build ios --release
```

### 证书配置

1. 在Apple Developer账户创建App ID
2. 创建开发和发布证书
3. 创建Provisioning Profile
4. 在Xcode中配置签名

### 构建IPA

```bash
# 构建iOS应用
flutter build ios --release

# 创建IPA（需要Xcode）
cd ios
xcodebuild -workspace Runner.xcworkspace \
  -scheme Runner -configuration Release \
  -archivePath build/Runner.xcarchive archive

xcodebuild -exportArchive \
  -archivePath build/Runner.xcarchive \
  -exportPath build/ipa \
  -exportOptionsPlist ExportOptions.plist
```

## GitHub Actions自动化

### 配置工作流

创建 `.github/workflows/flutter-ci.yml`：

```yaml
name: Flutter CI/CD

on:
  push:
    branches: [ main ]
    tags:
      - 'v*'
  pull_request:
    branches: [ main ]

jobs:
  test:
    name: Test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - uses: actions/setup-java@v3
        with:
          distribution: 'temurin'
          java-version: '17'
          
      - uses: subosito/flutter-action@v2
        with:
          flutter-version: '3.19.0'
          
      - name: Install dependencies
        run: |
          cd yigua_app
          flutter pub get
          
      - name: Run tests
        run: |
          cd yigua_app
          flutter test
          
      - name: Check code format
        run: |
          cd yigua_app
          flutter format --set-exit-if-changed .

  build-android:
    name: Build Android
    runs-on: ubuntu-latest
    needs: test
    if: github.event_name == 'push' && contains(github.ref, 'refs/tags/')
    
    steps:
      - uses: actions/checkout@v3
      
      - uses: actions/setup-java@v3
        with:
          distribution: 'temurin'
          java-version: '17'
          
      - uses: subosito/flutter-action@v2
        with:
          flutter-version: '3.19.0'
          
      - name: Setup signing
        env:
          KEYSTORE_BASE64: ${{ secrets.KEYSTORE_BASE64 }}
          KEY_PROPERTIES: ${{ secrets.KEY_PROPERTIES }}
        run: |
          echo "$KEYSTORE_BASE64" | base64 --decode > yigua-key.jks
          echo "$KEY_PROPERTIES" > yigua_app/android/key.properties
          
      - name: Build APK
        run: |
          cd yigua_app
          flutter build apk --release --split-per-abi
          
      - name: Build App Bundle
        run: |
          cd yigua_app
          flutter build appbundle --release
          
      - name: Upload APK
        uses: actions/upload-artifact@v3
        with:
          name: apk-release
          path: yigua_app/build/app/outputs/flutter-apk/*.apk
          
      - name: Upload AAB
        uses: actions/upload-artifact@v3
        with:
          name: aab-release
          path: yigua_app/build/app/outputs/bundle/release/*.aab

  release:
    name: Create Release
    runs-on: ubuntu-latest
    needs: build-android
    if: github.event_name == 'push' && contains(github.ref, 'refs/tags/')
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Download artifacts
        uses: actions/download-artifact@v3
        
      - name: Create Release
        id: create_release
        uses: actions/create-release@v1
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        with:
          tag_name: ${{ github.ref }}
          release_name: Release ${{ github.ref }}
          draft: false
          prerelease: false
          
      - name: Upload Release APK
        uses: actions/upload-release-asset@v1
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        with:
          upload_url: ${{ steps.create_release.outputs.upload_url }}
          asset_path: ./apk-release/app-arm64-v8a-release.apk
          asset_name: yigua-arm64-v8a.apk
          asset_content_type: application/vnd.android.package-archive
```

### 配置密钥

在GitHub仓库设置中添加Secrets：

1. **KEYSTORE_BASE64**: 
```bash
# 生成base64编码的密钥库
base64 yigua-key.jks > keystore.txt
# 复制内容到GitHub Secrets
```

2. **KEY_PROPERTIES**:
```properties
storePassword=你的密钥库密码
keyPassword=你的密钥密码
keyAlias=yigua
storeFile=../../yigua-key.jks
```

## 发布流程

### Google Play发布

#### 1. 准备材料

| 项目 | 要求 | 状态 |
|------|------|------|
| 应用图标 | 512x512 PNG | ✅ |
| 功能图形 | 1024x500 PNG | ✅ |
| 截图 | 手机至少2张 | ✅ |
| 应用描述 | 简短描述+完整描述 | ✅ |
| 隐私政策 | URL链接 | ✅ |
| 内容分级 | 填写问卷 | ✅ |

#### 2. 上传步骤

```bash
# 1. 构建App Bundle
flutter build appbundle --release

# 2. 登录Google Play Console
# https://play.google.com/console

# 3. 创建应用
# 4. 上传AAB文件
# 5. 填写商店信息
# 6. 设置定价和分发
# 7. 提交审核
```

### App Store发布

#### 1. 准备材料

| 项目 | 要求 | 规格 |
|------|------|------|
| 应用图标 | 1024x1024 | 无透明通道 |
| 截图 | 各尺寸设备 | 6.5", 5.5", iPad |
| 预览视频 | 可选 | 15-30秒 |
| 应用描述 | 多语言 | 至少中英文 |

#### 2. 发布流程

```bash
# 1. 构建iOS应用
flutter build ios --release

# 2. 使用Xcode上传
# - 打开Xcode
# - Product -> Archive
# - Distribute App
# - App Store Connect
# - Upload

# 3. 在App Store Connect配置
# - 填写应用信息
# - 上传截图
# - 设置定价
# - 提交审核
```

## 版本管理

### 版本号规范

```yaml
# pubspec.yaml
version: 1.0.0+1
# 格式: major.minor.patch+build
# 1.0.0 - 版本号（显示给用户）
# +1 - 构建号（内部使用）
```

### 更新版本

```bash
# 自动更新版本号
flutter pub global activate cider
cider bump patch # 1.0.0 -> 1.0.1
cider bump minor # 1.0.0 -> 1.1.0
cider bump major # 1.0.0 -> 2.0.0
```

## 常见问题

### 构建问题

#### Q: 构建APK失败
```bash
# 清理缓存
flutter clean
flutter pub get

# 重新构建
flutter build apk --release
```

#### Q: 签名配置错误
```bash
# 检查key.properties路径
# 确保密钥库文件存在
# 验证密码正确
```

#### Q: 内存不足
```gradle
// android/gradle.properties
org.gradle.jvmargs=-Xmx4G
```

### 性能优化

#### 减小APK大小
```bash
# 使用App Bundle
flutter build appbundle

# 按ABI拆分
flutter build apk --split-per-abi

# 启用混淆
flutter build apk --obfuscate --split-debug-info=./symbols
```

#### 提升启动速度
```dart
// 延迟加载
import 'package:flutter/material.dart' deferred as material;

// 预加载资源
precacheImage(AssetImage("assets/logo.png"), context);
```

## 监控和分析

### Firebase集成

```yaml
# pubspec.yaml
dependencies:
  firebase_core: ^2.24.0
  firebase_analytics: ^10.7.0
  firebase_crashlytics: ^3.4.0
```

```dart
// main.dart
void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await Firebase.initializeApp();
  
  // Crashlytics
  FlutterError.onError = FirebaseCrashlytics.instance.recordFlutterError;
  
  runApp(MyApp());
}
```

### 性能监控

```dart
// 使用Performance Monitoring
import 'package:firebase_performance/firebase_performance.dart';

final trace = FirebasePerformance.instance.newTrace('test_trace');
await trace.start();
// 执行操作
await trace.stop();
```

---

## 快速命令参考

```bash
# 开发
flutter run                          # 运行应用
flutter run --release                 # 发布模式运行
flutter devices                       # 查看设备
flutter clean                         # 清理构建

# 构建
flutter build apk                     # 构建APK
flutter build appbundle              # 构建AAB
flutter build ios                    # 构建iOS
flutter build web                    # 构建Web

# 测试
flutter test                         # 运行测试
flutter analyze                      # 代码分析
flutter format .                     # 格式化代码

# 发布
flutter pub publish                  # 发布包
flutter install                      # 安装到设备
```

---

<div align="center">
  <b>易卦部署指南 - 从开发到发布的完整流程</b><br>
  持续更新中...
</div>