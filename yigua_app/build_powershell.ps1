# PowerShell 构建脚本
Set-Location "D:\Desktop\appp\yigua_app"

# 设置环境变量
$env:PUB_HOSTED_URL = "https://pub.flutter-io.cn"
$env:FLUTTER_STORAGE_BASE_URL = "https://storage.flutter-io.cn"

Write-Host "当前目录: $(Get-Location)" -ForegroundColor Green
Write-Host ""

# 检查 Flutter 是否存在
if (Test-Path "D:\flutter\bin\flutter.bat") {
    Write-Host "Flutter 找到，开始构建..." -ForegroundColor Green
    
    # 尝试运行 Flutter
    & "D:\flutter\bin\flutter.bat" --version
    
    Write-Host ""
    Write-Host "开始构建 APK..." -ForegroundColor Yellow
    & "D:\flutter\bin\flutter.bat" build apk --release
    
} else {
    Write-Host "错误: Flutter 未找到在 D:\flutter\bin\" -ForegroundColor Red
}

Write-Host ""
Write-Host "按任意键退出..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")