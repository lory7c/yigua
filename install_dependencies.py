#!/usr/bin/env python3
"""
安装PDF处理所需依赖
"""

import subprocess
import sys
import os

def install_package(package):
    """安装Python包"""
    try:
        print(f"正在安装 {package}...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        print(f"✅ {package} 安装成功")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {package} 安装失败: {e}")
        return False

def main():
    """主函数"""
    print("🚀 开始安装PDF处理依赖...")
    
    # 必需的包
    required_packages = [
        "pdfplumber",
        "Pillow",
        "tqdm"
    ]
    
    success_count = 0
    for package in required_packages:
        if install_package(package):
            success_count += 1
    
    print(f"\n📊 安装结果: {success_count}/{len(required_packages)} 成功")
    
    if success_count == len(required_packages):
        print("✅ 所有依赖安装成功，可以运行 python extract_pdfs.py")
    else:
        print("⚠️ 部分依赖安装失败，请手动安装")

if __name__ == "__main__":
    main()