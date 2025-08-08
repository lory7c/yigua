#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
易学RAG系统依赖安装脚本
自动检测并安装必要的Python包
"""

import subprocess
import sys
import importlib.util

def check_package(package_name, import_name=None):
    """检查包是否已安装"""
    if import_name is None:
        import_name = package_name
    
    spec = importlib.util.find_spec(import_name)
    return spec is not None

def install_package(package_name):
    """安装包"""
    try:
        print(f"📦 安装 {package_name}...")
        subprocess.run([
            sys.executable, "-m", "pip", "install", package_name, "--quiet"
        ], check=True, capture_output=True)
        print(f"✅ {package_name} 安装成功")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {package_name} 安装失败: {e}")
        return False
    except Exception as e:
        print(f"❌ 安装 {package_name} 时出错: {e}")
        return False

def main():
    """主函数"""
    print("🔧 易学RAG系统依赖检查与安装")
    print("=" * 50)
    
    # 必需的包列表 (包名, 导入名)
    required_packages = [
        ("numpy", "numpy"),
        ("jieba", "jieba"), 
        ("scikit-learn", "sklearn"),
        ("networkx", "networkx"),
        ("pathlib", "pathlib"),  # 通常是内置的
    ]
    
    # 可选的包（提升性能）
    optional_packages = [
        ("faiss-cpu", "faiss"),  # 向量搜索
        ("sentence-transformers", "sentence_transformers"),  # 语义向量化
    ]
    
    print("\n🔍 检查必需依赖...")
    missing_required = []
    
    for pkg_name, import_name in required_packages:
        if import_name == "pathlib":
            continue  # pathlib是内置模块
            
        if check_package(pkg_name, import_name):
            print(f"✅ {pkg_name} 已安装")
        else:
            print(f"❌ {pkg_name} 未安装")
            missing_required.append(pkg_name)
    
    print("\n🔍 检查可选依赖...")
    missing_optional = []
    
    for pkg_name, import_name in optional_packages:
        if check_package(pkg_name, import_name):
            print(f"✅ {pkg_name} 已安装")
        else:
            print(f"⚠️ {pkg_name} 未安装 (可选，建议安装)")
            missing_optional.append(pkg_name)
    
    # 安装缺失的包
    if missing_required:
        print(f"\n📦 安装缺失的必需依赖...")
        for pkg in missing_required:
            if not install_package(pkg):
                print(f"❌ 必需依赖 {pkg} 安装失败！")
                print("请手动安装或检查网络连接")
                return False
    
    if missing_optional:
        print(f"\n📦 安装可选依赖 (推荐)...")
        for pkg in missing_optional:
            success = install_package(pkg)
            if not success:
                print(f"⚠️ 可选依赖 {pkg} 安装失败，系统仍可运行但性能可能受影响")
    
    print("\n✅ 依赖检查完成!")
    
    # 验证安装
    print("\n🧪 验证安装...")
    try:
        import numpy as np
        print("✅ NumPy 工作正常")
        
        import jieba
        print("✅ Jieba 工作正常")
        
        import sklearn
        print("✅ Scikit-learn 工作正常")
        
        import networkx as nx
        print("✅ NetworkX 工作正常")
        
        # 测试可选依赖
        try:
            import faiss
            print("✅ FAISS 工作正常")
        except:
            print("⚠️ FAISS 不可用，将使用备用方案")
        
        try:
            from sentence_transformers import SentenceTransformer
            print("✅ Sentence Transformers 工作正常")
        except:
            print("⚠️ Sentence Transformers 不可用，将使用TF-IDF")
    
    except ImportError as e:
        print(f"❌ 验证失败: {e}")
        return False
    
    print("\n🎉 所有依赖验证通过，系统可以正常运行！")
    print("\n🚀 现在可以运行:")
    print("   python quick_start_rag.py")
    
    return True

if __name__ == "__main__":
    main()