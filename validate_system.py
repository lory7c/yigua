#!/usr/bin/env python3
"""
系统验证脚本 - 验证生产级PDF提取管道完整性
检查所有依赖、配置和功能模块
"""

import sys
import importlib
from pathlib import Path
import json

def check_dependency(module_name, import_name=None):
    """检查单个依赖"""
    if import_name is None:
        import_name = module_name
    
    try:
        importlib.import_module(import_name)
        return True, "✅"
    except ImportError as e:
        return False, f"❌ {str(e)}"

def check_all_dependencies():
    """检查所有依赖"""
    print("📦 依赖库检查:")
    
    dependencies = [
        ("pdfplumber", "pdfplumber"),
        ("PyMuPDF", "fitz"), 
        ("PyPDF2", "PyPDF2"),
        ("tqdm", "tqdm"),
        ("pandas", "pandas"),
        ("psutil", "psutil"),
        ("PIL", "PIL")
    ]
    
    all_ok = True
    for display_name, import_name in dependencies:
        ok, status = check_dependency(display_name, import_name)
        print(f"   {status} {display_name}")
        if not ok:
            all_ok = False
    
    return all_ok

def check_files():
    """检查关键文件"""
    print("\n📁 关键文件检查:")
    
    required_files = [
        "production_extract.py",
        "quick_production_run.py",
        "ETL_Architecture_Design.md",
        "data/",
        "一键启动生产级提取.bat"
    ]
    
    all_ok = True
    for file_path in required_files:
        path = Path(file_path)
        if path.exists():
            if path.is_dir():
                pdf_count = len(list(path.glob("*.pdf"))) if file_path == "data/" else 0
                print(f"   ✅ {file_path} (目录, {pdf_count} 个PDF)")
            else:
                size_kb = path.stat().st_size / 1024
                print(f"   ✅ {file_path} ({size_kb:.1f} KB)")
        else:
            print(f"   ❌ {file_path} (不存在)")
            all_ok = False
    
    return all_ok

def check_system_resources():
    """检查系统资源"""
    print("\n💻 系统资源检查:")
    
    try:
        import psutil
        
        memory = psutil.virtual_memory()
        cpu_count = psutil.cpu_count()
        disk = psutil.disk_usage('/')
        
        total_gb = memory.total / (1024**3)
        available_gb = memory.available / (1024**3)
        disk_free_gb = disk.free / (1024**3)
        
        print(f"   💾 内存: {total_gb:.1f}GB 总计, {available_gb:.1f}GB 可用")
        print(f"   🖥️ CPU: {cpu_count} 核心")  
        print(f"   💿 磁盘: {disk_free_gb:.1f}GB 可用空间")
        
        # 资源充足性判断
        warnings = []
        if available_gb < 2.0:
            warnings.append("⚠️ 可用内存不足2GB")
        if cpu_count < 4:
            warnings.append("⚠️ CPU核心数少于4个")
        if disk_free_gb < 5.0:
            warnings.append("⚠️ 磁盘可用空间不足5GB")
        
        if warnings:
            print("   资源警告:")
            for warning in warnings:
                print(f"     {warning}")
        else:
            print("   ✅ 系统资源充足")
        
        return len(warnings) == 0
        
    except ImportError:
        print("   ❌ 无法检查系统资源 (psutil未安装)")
        return False

def check_data_directory():
    """检查数据目录"""
    print("\n📋 数据目录检查:")
    
    data_dir = Path("data")
    if not data_dir.exists():
        print("   ❌ data目录不存在")
        return False
    
    pdf_files = list(data_dir.glob("*.pdf"))
    total_count = len(pdf_files)
    
    if total_count == 0:
        print("   ❌ 没有找到PDF文件")
        return False
    
    # 计算总大小
    total_size = sum(f.stat().st_size for f in pdf_files)
    total_size_mb = total_size / (1024 * 1024)
    
    print(f"   ✅ 发现 {total_count} 个PDF文件")
    print(f"   📊 总大小: {total_size_mb:.1f} MB")
    
    # 检查文件名编码
    encoding_issues = []
    for pdf_file in pdf_files[:10]:  # 检查前10个
        try:
            pdf_file.name.encode('utf-8')
        except UnicodeEncodeError:
            encoding_issues.append(pdf_file.name)
    
    if encoding_issues:
        print(f"   ⚠️ {len(encoding_issues)} 个文件名存在编码问题")
    else:
        print("   ✅ 文件名编码正常")
    
    return True

def test_basic_functionality():
    """测试基本功能"""
    print("\n🔧 基本功能测试:")
    
    try:
        # 测试PDF处理
        import pdfplumber
        print("   ✅ pdfplumber 可以导入")
        
        import fitz
        print("   ✅ PyMuPDF 可以导入")
        
        # 测试多进程
        import multiprocessing as mp
        print(f"   ✅ multiprocessing 支持 (最大进程: {mp.cpu_count()})")
        
        # 测试进度条
        from tqdm import tqdm
        print("   ✅ tqdm 进度条可用")
        
        # 测试JSON处理
        test_data = {"test": "中文测试"}
        json_str = json.dumps(test_data, ensure_ascii=False)
        parsed = json.loads(json_str)
        assert parsed["test"] == "中文测试"
        print("   ✅ JSON中文处理正常")
        
        return True
        
    except Exception as e:
        print(f"   ❌ 功能测试失败: {e}")
        return False

def estimate_performance():
    """性能预估"""
    print("\n⚡ 性能预估:")
    
    try:
        import psutil
        
        # 获取系统信息
        memory = psutil.virtual_memory()
        cpu_count = psutil.cpu_count()
        available_gb = memory.available / (1024**3)
        
        # 检查PDF文件数量
        data_dir = Path("data")
        pdf_files = list(data_dir.glob("*.pdf"))
        total_files = len(pdf_files)
        
        if total_files == 0:
            print("   ❌ 无法估算 (没有PDF文件)")
            return
        
        # 基于系统资源计算推荐配置
        recommended_workers = min(cpu_count - 1, 8)
        recommended_batch_size = max(4, min(recommended_workers * 2, 12))
        memory_limit_gb = min(available_gb * 0.7, 3.0)
        
        # 估算处理时间 (基于生产级优化管道)
        base_time_per_file = 0.008  # 每个文件基础处理时间(小时) - 优化后约30秒/文件
        parallelism_factor = 0.3    # 并发处理减少总时间
        cache_factor = 0.8          # 缓存和断点续传优化
        estimated_hours = total_files * base_time_per_file * parallelism_factor * cache_factor
        
        print(f"   📊 文件数量: {total_files}")
        print(f"   🔧 推荐配置:")
        print(f"      工作进程: {recommended_workers}")
        print(f"      批处理大小: {recommended_batch_size}")
        print(f"      内存限制: {memory_limit_gb:.1f} GB")
        print(f"   ⏰ 预估处理时间: {estimated_hours:.2f} 小时")
        
        if estimated_hours <= 3.0:
            print("   ✅ 预计在3小时目标内完成")
        else:
            print("   ⚠️ 预计超过3小时目标")
        
        return estimated_hours <= 3.0
        
    except Exception as e:
        print(f"   ❌ 性能预估失败: {e}")
        return False

def main():
    """主验证流程"""
    print("🔍 生产级PDF提取管道 - 系统验证")
    print("=" * 60)
    
    all_checks = []
    
    # 依赖检查
    all_checks.append(check_all_dependencies())
    
    # 文件检查
    all_checks.append(check_files())
    
    # 系统资源检查
    all_checks.append(check_system_resources())
    
    # 数据目录检查
    all_checks.append(check_data_directory())
    
    # 功能测试
    all_checks.append(test_basic_functionality())
    
    # 性能预估
    performance_ok = estimate_performance()
    all_checks.append(performance_ok)
    
    # 总结
    print("\n" + "=" * 60)
    passed_checks = sum(all_checks)
    total_checks = len(all_checks)
    
    print(f"📋 验证结果: {passed_checks}/{total_checks} 项检查通过")
    
    if passed_checks == total_checks:
        print("✅ 系统验证完全通过!")
        print("🚀 可以启动生产级PDF提取管道")
        print("\n启动方式:")
        print("   1. 双击: 一键启动生产级提取.bat")
        print("   2. 命令行: python quick_production_run.py") 
        print("   3. 直接运行: python production_extract.py")
    else:
        failed_checks = total_checks - passed_checks
        print(f"❌ 系统验证失败 ({failed_checks} 项问题)")
        print("🔧 请解决上述问题后重新验证")
    
    print("=" * 60)
    return passed_checks == total_checks

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)