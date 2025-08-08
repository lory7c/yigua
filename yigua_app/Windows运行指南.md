# Flutter Windows 运行指南

## 快速开始

### 方法一：使用批处理文件（最简单）
1. **双击运行** `quick_run.bat` - 最快速的运行方式
2. **双击运行** `run_windows.bat` - 带详细步骤提示的运行方式
3. **双击运行** `clean_and_run.bat` - 清理后运行（解决缓存问题）

### 方法二：使用 PowerShell 脚本（功能更强大）
1. 右键点击 `run_windows.ps1` → "使用 PowerShell 运行"
2. 或者打开 PowerShell，运行：
   ```powershell
   cd D:\desktop\appp\yigua_app
   .\run_windows.ps1
   ```

### 方法三：在命令行直接运行
打开 Windows Terminal、PowerShell 或命令提示符，执行：

```batch
# 设置中国镜像
set PUB_HOSTED_URL=https://pub.flutter-io.cn
set FLUTTER_STORAGE_BASE_URL=https://storage.flutter-io.cn

# 切换到项目目录
cd /d D:\desktop\appp\yigua_app

# 运行应用
D:\flutter\bin\flutter.bat run
```

## 脚本说明

| 脚本文件 | 用途 | 特点 |
|---------|------|------|
| `quick_run.bat` | 快速运行 | 最简化，直接运行 |
| `run_windows.bat` | 标准运行 | 包含完整步骤和错误检查 |
| `run_windows.ps1` | PowerShell 运行 | 彩色输出，详细日志 |
| `run_web.ps1` | Web 运行 | 在 Chrome 中运行 |
| `clean_and_run.bat` | 清理并运行 | 解决缓存问题 |
| `debug_run.ps1` | 调试运行 | 最详细的调试信息 |

## 运行 Web 版本

如果想在浏览器中运行：
```batch
D:\flutter\bin\flutter.bat run -d chrome
```

或使用提供的脚本：
- 运行 `run_web.ps1`

## 常见问题解决

### 1. PowerShell 脚本无法运行
如果 PowerShell 脚本被阻止，在管理员 PowerShell 中运行：
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### 2. 找不到设备
确保：
- Android 设备已连接并开启 USB 调试
- 或者 Android 模拟器已启动
- 运行 `flutter doctor` 检查环境

### 3. 依赖获取失败
- 确保网络连接正常
- 脚本已自动配置中国镜像
- 可以尝试运行 `clean_and_run.bat`

### 4. Flutter 命令找不到
确保 Flutter 已安装在 `D:\flutter` 目录

## 热键说明

应用运行时可用的热键：
- `r` - 热重载（Hot Reload）
- `R` - 热重启（Hot Restart）
- `h` - 显示帮助
- `q` - 退出应用
- `d` - 分离（在后台继续运行）

## 调试技巧

1. **查看详细日志**：使用 `debug_run.ps1`
2. **检查 Flutter 环境**：
   ```batch
   D:\flutter\bin\flutter.bat doctor -v
   ```
3. **查看设备列表**：
   ```batch
   D:\flutter\bin\flutter.bat devices
   ```

## 注意事项

- 所有脚本都已配置中国镜像加速
- 首次运行可能需要下载依赖，请耐心等待
- 确保防火墙没有阻止 Flutter 或 adb
- 建议使用最新版本的 Windows Terminal 获得最佳体验