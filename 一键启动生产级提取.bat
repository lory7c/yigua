@echo off
chcp 65001 > nul
title 生产级PDF提取管道 - 一键启动

echo.
echo ===============================================================
echo 🚀 生产级易学PDF文档批量提取管道 - 一键启动
echo ===============================================================
echo 基于ETL_Architecture_Design.md方案实现
echo 整合最佳提取方法 + 并发处理 + 断点续传 + 智能分类
echo.
echo 功能特性：
echo   ✅ 多方法提取：pdfplumber + PyMuPDF + PyPDF2
echo   ✅ 智能分类：六爻、大六壬、周易基础等10大类
echo   ✅ 并发处理：自动优化工作进程数
echo   ✅ 断点续传：支持中断后继续处理
echo   ✅ 结构化提取：卦象、爻辞、注解、案例
echo   ✅ HTML报告：可视化处理结果
echo.
echo 目标：191个PDF文件，3小时内完成处理
echo ===============================================================
echo.

REM 检查Python是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python未安装或不在PATH中
    echo 请先安装Python 3.7+
    pause
    exit /b 1
)

echo ✅ Python环境检查通过
echo.

REM 检查数据目录
if not exist "data\" (
    echo ❌ data目录不存在
    echo 请确保PDF文件放在data目录中
    pause
    exit /b 1
)

REM 统计PDF文件数量
set pdf_count=0
for %%f in (data\*.pdf) do (
    set /a pdf_count+=1
)

if %pdf_count%==0 (
    echo ❌ data目录中没有PDF文件
    echo 请将PDF文件放入data目录后重试
    pause
    exit /b 1
)

echo ✅ 发现 %pdf_count% 个PDF文件
echo.

REM 检查快速启动脚本
if not exist "quick_production_run.py" (
    echo ❌ 快速启动脚本不存在
    echo 请确保quick_production_run.py在当前目录
    pause
    exit /b 1
)

if not exist "production_extract.py" (
    echo ❌ 主处理脚本不存在  
    echo 请确保production_extract.py在当前目录
    pause
    exit /b 1
)

echo ✅ 处理脚本检查通过
echo.

echo 🚀 启动快速配置向导...
echo 按任意键继续，或按Ctrl+C取消
pause >nul

echo.
echo ⚡ 正在启动生产级PDF提取管道...
echo.

REM 启动Python处理脚本
python quick_production_run.py

if errorlevel 1 (
    echo.
    echo ❌ 处理过程出现错误
) else (
    echo.
    echo 🎉 处理完成！
    echo.
    echo 📊 查看结果：
    echo   📁 structured_data\ - 完整结果和统计
    echo   📄 reports\ - HTML可视化报告  
    echo   📂 categories\ - 按类别分组结果
    echo   📝 raw_texts\ - 原始提取文本
    echo.
)

echo.
echo 按任意键退出...
pause >nul