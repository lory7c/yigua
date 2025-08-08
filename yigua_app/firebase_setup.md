# Firebase App Distribution 设置指南

## 步骤：

1. **创建 Firebase 项目**
   - 访问 https://console.firebase.google.com
   - 点击"创建项目"
   - 输入项目名称：yigua-app

2. **添加 Android 应用**
   - 点击 Android 图标
   - 包名：com.example.yigua_app
   - 下载 google-services.json
   - 放到 android/app/ 目录

3. **启用 App Distribution**
   - 左侧菜单 → Release & Monitor → App Distribution
   - 点击"开始"

4. **安装 Firebase CLI**
   ```bash
   npm install -g firebase-tools
   firebase login
   ```

5. **分发 APK**
   ```bash
   firebase appdistribution:distribute build/app/outputs/flutter-apk/app-release.apk \
     --app YOUR_APP_ID \
     --groups testers
   ```

## 优点：
- 免费
- 可以管理测试人员
- 自动通知更新
- 详细的安装统计