#!/usr/bin/env python3
"""
PDF批量处理 - 一键安装和运行脚本

这个脚本会:
1. 检查和安装必要的依赖包
2. 创建输出目录
3. 运行主要的PDF处理脚本

使用方法:
python setup_and_run.py
"""

import subprocess
import sys
import os
from pathlib import Path


def install_requirements():
    """安装依赖包"""
    print("正在安装依赖包...")
    requirements_file = Path(__file__).parent / "requirements.txt"
    
    if requirements_file.exists():
        try:
            subprocess.check_call([
                sys.executable, "-m", "pip", "install", "-r", str(requirements_file)
            ])
            print("依赖包安装成功")
            return True
        except subprocess.CalledProcessError as e:
            print(f"依赖包安装失败: {e}")
            return False
    else:
        print("requirements.txt 文件不存在，尝试单独安装包...")
        packages = ["PyPDF2", "pdfplumber", "PyMuPDF", "tqdm"]
        for package in packages:
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", package])
                print(f"{package} 安装成功")
            except subprocess.CalledProcessError:
                print(f"{package} 安装失败")
        return True


def check_directories():
    """检查必要的目录"""
    data_dir = Path("/mnt/d/desktop/appp/data")
    output_dir = Path("/mnt/d/desktop/appp/extracted_data")
    
    if not data_dir.exists():
        print(f"警告: 数据目录不存在 {data_dir}")
        return False
    
    # 创建输出目录
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"输出目录已准备: {output_dir}")
    
    # 检查PDF文件数量
    pdf_files = list(data_dir.glob("*.pdf"))
    print(f"发现 {len(pdf_files)} 个PDF文件")
    
    if len(pdf_files) == 0:
        print("警告: 未发现PDF文件")
        return False
    
    return True


def run_main_script():
    """运行主要的处理脚本"""
    main_script = Path(__file__).parent / "extract_all_pdfs.py"
    
    if not main_script.exists():
        print(f"错误: 主脚本不存在 {main_script}")
        return False
    
    print("开始运行PDF批量处理...")
    try:
        subprocess.check_call([sys.executable, str(main_script)])
        print("PDF批量处理完成")
        return True
    except subprocess.CalledProcessError as e:
        print(f"处理过程中出错: {e}")
        return False
    except KeyboardInterrupt:
        print("\n用户中断处理")
        return False


def main():
    """主函数"""
    print("=" * 60)
    print("PDF批量处理 - 一键安装和运行")
    print("=" * 60)
    
    # 步骤1: 安装依赖
    if not install_requirements():
        print("依赖安装失败，请手动安装")
        return 1
    
    # 步骤2: 检查目录
    if not check_directories():
        print("目录检查失败，请确认数据目录存在且包含PDF文件")
        return 1
    
    # 步骤3: 运行处理
    if not run_main_script():
        print("处理失败")
        return 1
    
    print("\n所有步骤完成！")
    print("检查 /mnt/d/desktop/appp/extracted_data/ 目录查看结果")
    return 0


if __name__ == "__main__":
    exit(main())