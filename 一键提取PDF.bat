@echo off
chcp 65001 >nul
title 易学PDF批量处理器

echo ========================================
echo        🔮 易学PDF批量处理器
echo ========================================
echo.

:: 检查Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 未找到Python，请先安装Python
    pause
    exit /b 1
)

echo ✅ Python环境检查通过
echo.

:: 检查数据目录
if not exist "data" (
    echo ❌ 未找到data目录
    echo 请将PDF文件放入data目录中
    pause
    exit /b 1
)

:: 统计PDF文件
set pdf_count=0
for %%f in (data\*.pdf) do set /a pdf_count+=1

if %pdf_count%==0 (
    echo ❌ 在data目录中未找到PDF文件
    pause
    exit /b 1
)

echo ✅ 发现 %pdf_count% 个PDF文件
echo.

:: 启动处理
echo 🚀 启动PDF处理...
python quick_extract.py

echo.
echo ✅ 处理完成，按任意键查看结果目录
pause

:: 打开结果目录
if exist "structured_data" (
    explorer structured_data
)

pause