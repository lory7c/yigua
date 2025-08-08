#!/usr/bin/env python3
"""
快速PDF批量处理启动脚本
自动检测依赖并启动处理
"""

import os
import sys
import subprocess
from pathlib import Path

def check_dependencies():
    """检查依赖"""
    required_packages = ['pdfplumber', 'tqdm']
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    return missing_packages

def install_dependencies(packages):
    """安装缺失的依赖"""
    print(f"🔧 正在安装缺失的依赖: {', '.join(packages)}")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install"] + packages)
        print("✅ 依赖安装完成")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ 依赖安装失败: {e}")
        return False

def main():
    """主函数"""
    print("🚀 快速PDF处理启动器")
    print("=" * 50)
    
    # 检查数据目录
    data_dir = Path("/mnt/d/desktop/appp/data")
    if not data_dir.exists():
        print(f"❌ 数据目录不存在: {data_dir}")
        print("请确保PDF文件放在data目录中")
        return
    
    pdf_count = len(list(data_dir.glob("*.pdf")))
    print(f"📋 发现 {pdf_count} 个PDF文件")
    
    if pdf_count == 0:
        print("❌ 没有找到PDF文件")
        return
    
    # 检查依赖
    print("🔍 检查依赖...")
    missing_packages = check_dependencies()
    
    if missing_packages:
        print(f"⚠️ 缺少依赖: {', '.join(missing_packages)}")
        choice = input("是否自动安装？(y/N): ")
        if choice.lower() == 'y':
            if not install_dependencies(missing_packages):
                return
        else:
            print("请先安装依赖: pip install pdfplumber tqdm")
            return
    else:
        print("✅ 依赖检查完成")
    
    # 选择处理模式
    print("\n处理模式:")
    print("1. 标准模式 (推荐)")
    print("2. 进度条模式")
    
    choice = input("请选择模式 (1/2, 默认1): ").strip() or "1"
    
    if choice == "2":
        script_path = Path(__file__).parent / "extract_pdfs_with_progress.py"
    else:
        script_path = Path(__file__).parent / "extract_pdfs.py"
    
    if not script_path.exists():
        print(f"❌ 处理脚本不存在: {script_path}")
        return
    
    # 启动处理
    print(f"\n🚀 启动PDF处理...")
    print(f"📄 使用脚本: {script_path.name}")
    
    try:
        subprocess.run([sys.executable, str(script_path)], check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ 处理失败: {e}")
    except KeyboardInterrupt:
        print("\n⚠️ 用户中断处理")

if __name__ == "__main__":
    main()