#!/usr/bin/env python3
"""
生产级PDF提取管道 - 快速启动器
一键启动高效PDF批量处理，自动检测环境和配置优化参数
"""

import os
import sys
import subprocess
import time
from pathlib import Path

def check_dependencies():
    """检查依赖"""
    required_packages = [
        'pdfplumber', 'pymupdf', 'PyPDF2', 'tqdm', 
        'pandas', 'psutil', 'pillow'
    ]
    missing_packages = []
    
    for package in required_packages:
        try:
            if package == 'pymupdf':
                import fitz
            elif package == 'pillow':
                from PIL import Image
            else:
                __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    return missing_packages

def install_dependencies(packages):
    """安装依赖"""
    print(f"🔧 正在安装缺失依赖: {', '.join(packages)}")
    try:
        subprocess.check_call([
            sys.executable, "-m", "pip", "install"
        ] + packages + ["--upgrade", "--user"])
        print("✅ 依赖安装完成")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ 依赖安装失败: {e}")
        return False

def check_system_resources():
    """检查系统资源"""
    try:
        import psutil
        memory = psutil.virtual_memory()
        cpu_count = psutil.cpu_count()
        
        total_gb = memory.total / (1024**3)
        available_gb = memory.available / (1024**3)
        
        print(f"💻 系统资源检查:")
        print(f"   CPU 核心: {cpu_count}")
        print(f"   总内存: {total_gb:.1f} GB")
        print(f"   可用内存: {available_gb:.1f} GB")
        
        # 资源充足性检查
        if available_gb < 1.0:
            print("⚠️ 可用内存不足1GB，建议关闭其他程序")
            return False
        
        if cpu_count < 2:
            print("⚠️ CPU核心数少于2个，可能影响并发性能")
        
        return True
        
    except ImportError:
        print("⚠️ 无法检查系统资源，继续执行")
        return True

def check_data_directory():
    """检查数据目录"""
    data_dir = Path("/mnt/d/desktop/appp/data")
    
    if not data_dir.exists():
        print(f"❌ 数据目录不存在: {data_dir}")
        print("请确保PDF文件放在data目录中")
        return False, 0
    
    pdf_files = list(data_dir.glob("*.pdf"))
    pdf_count = len(pdf_files)
    
    if pdf_count == 0:
        print("❌ 数据目录中没有找到PDF文件")
        return False, 0
    
    total_size = sum(f.stat().st_size for f in pdf_files)
    total_size_mb = total_size / (1024 * 1024)
    
    print(f"📋 发现 {pdf_count} 个PDF文件")
    print(f"💿 总数据量: {total_size_mb:.1f} MB")
    
    return True, pdf_count

def estimate_processing_time(pdf_count):
    """估算处理时间"""
    # 基于经验数据估算
    base_time_per_file = 0.05  # 基础处理时间（小时）
    complexity_factor = 1.2   # 复杂度因子
    
    estimated_hours = pdf_count * base_time_per_file * complexity_factor
    
    if estimated_hours <= 1:
        time_desc = f"{estimated_hours * 60:.0f} 分钟"
    else:
        time_desc = f"{estimated_hours:.1f} 小时"
    
    print(f"⏰ 预计处理时间: {time_desc}")
    
    if estimated_hours > 3:
        print("⚠️ 预计时间超过3小时，建议分批处理")
    
    return estimated_hours

def main():
    """主程序"""
    print("🚀 生产级PDF提取管道 - 快速启动器")
    print("=" * 60)
    print("基于ETL_Architecture_Design.md方案")
    print("整合最佳提取方法 + 并发处理 + 断点续传")
    print("=" * 60)
    
    # 步骤1: 检查依赖
    print("\n📦 步骤1: 检查依赖...")
    missing_packages = check_dependencies()
    
    if missing_packages:
        print(f"⚠️ 缺少依赖: {', '.join(missing_packages)}")
        install_choice = input("是否自动安装？(y/N): ")
        if install_choice.lower() == 'y':
            if not install_dependencies(missing_packages):
                print("❌ 依赖安装失败，退出")
                return
        else:
            print("❌ 请先手动安装依赖")
            print(f"pip install {' '.join(missing_packages)}")
            return
    else:
        print("✅ 所有依赖已满足")
    
    # 步骤2: 检查系统资源
    print("\n💻 步骤2: 检查系统资源...")
    if not check_system_resources():
        continue_choice = input("是否继续执行？(y/N): ")
        if continue_choice.lower() != 'y':
            print("❌ 用户取消执行")
            return
    
    # 步骤3: 检查数据目录
    print("\n📁 步骤3: 检查数据目录...")
    data_ok, pdf_count = check_data_directory()
    
    if not data_ok:
        print("❌ 数据目录检查失败，退出")
        return
    
    # 步骤4: 估算处理时间
    print("\n⏰ 步骤4: 处理时间估算...")
    estimated_hours = estimate_processing_time(pdf_count)
    
    # 步骤5: 用户确认
    print("\n🎯 步骤5: 启动确认...")
    print("处理配置:")
    print(f"   📄 文件数量: {pdf_count} 个PDF")
    print(f"   ⏰ 预计时间: {estimated_hours:.1f} 小时")
    print(f"   📁 输出目录: /mnt/d/desktop/appp/structured_data")
    print(f"   💾 缓存启用: 是（支持断点续传）")
    print(f"   🔧 并发处理: 是（自动优化配置）")
    
    print("\n特性说明:")
    print("   ✅ 多方法提取: pdfplumber + PyMuPDF + PyPDF2")
    print("   ✅ 智能分类: 六爻、大六壬、周易基础等10大类")
    print("   ✅ 结构化提取: 卦象、爻辞、注解、案例")
    print("   ✅ 断点续传: 支持中断后继续处理")
    print("   ✅ 进度监控: 实时显示处理进度")
    print("   ✅ HTML报告: 可视化处理结果")
    
    start_choice = input(f"\n🚀 开始处理 {pdf_count} 个PDF文件？(y/N): ")
    if start_choice.lower() != 'y':
        print("❌ 用户取消处理")
        return
    
    # 步骤6: 启动处理
    print(f"\n⚡ 启动生产级PDF提取管道...")
    print("💡 可随时按 Ctrl+C 中断，已处理的文件会保存到缓存")
    
    script_path = Path(__file__).parent / "production_extract.py"
    
    if not script_path.exists():
        print(f"❌ 主处理脚本不存在: {script_path}")
        return
    
    try:
        start_time = time.time()
        print(f"⏰ 开始时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        print("-" * 60)
        
        # 启动主处理脚本
        result = subprocess.run([
            sys.executable, str(script_path)
        ], check=False)
        
        end_time = time.time()
        actual_hours = (end_time - start_time) / 3600
        
        print("-" * 60)
        print(f"⏰ 结束时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"⏱️ 实际耗时: {actual_hours:.2f} 小时")
        
        if result.returncode == 0:
            print("🎉 处理完成!")
            print("📊 查看结果:")
            print("   📁 structured_data/ - 完整结果")
            print("   📄 reports/ - HTML可视化报告")
            print("   📂 categories/ - 按类别分组")
        else:
            print("⚠️ 处理过程中出现问题")
            print("💾 已处理的文件已保存到缓存")
            print("🔄 可重新运行继续处理")
            
    except KeyboardInterrupt:
        print("\n⚠️ 用户中断处理")
        print("💾 处理进度已保存")
        print("🔄 下次运行将从断点继续")
        
    except Exception as e:
        print(f"\n❌ 启动失败: {e}")
        print("🔍 请检查错误信息或联系技术支持")

if __name__ == "__main__":
    main()