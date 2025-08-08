@echo off
echo 易卦算甲 - 快速运行脚本
echo.

cd yigua_app

echo 检查Flutter环境...
flutter doctor

echo.
echo 可用设备：
flutter devices

echo.
echo 选择运行方式：
echo 1. Chrome浏览器（最快）
echo 2. Android模拟器
echo 3. 连接的真机
echo.

set /p choice=请输入选项(1-3): 

if %choice%==1 (
    echo 在Chrome浏览器中运行...
    flutter run -d chrome
) else if %choice%==2 (
    echo 启动Android模拟器...
    flutter emulators
    echo.
    set /p emulator=请输入模拟器名称: 
    flutter emulators --launch %emulator%
    timeout /t 10
    flutter run
) else if %choice%==3 (
    echo 在真机上运行...
    flutter run
) else (
    echo 无效选项！
)

pause