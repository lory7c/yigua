@echo off
chcp 65001 >nul
title 易卦算甲 - 新版本快速测试

cls
echo ╔════════════════════════════════════════╗
echo ║        易卦算甲 - 新版本测试           ║
echo ╚════════════════════════════════════════╝
echo.
echo 主要更新内容：
echo ✓ 全新UI设计 - 九宫格布局+动画效果
echo ✓ 六爻排盘系统 - 支持铜钱起卦
echo ✓ 优化用户体验 - 更流畅的交互
echo.

cd /d D:\desktop\appp\yigua_app

echo 正在启动应用...
echo.

D:\flutter\bin\flutter run -d chrome --web-renderer html

pause