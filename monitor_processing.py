#!/usr/bin/env python3
"""
PDF处理进度监控脚本
实时显示处理状态和统计信息
"""

import time
import pickle
import json
from pathlib import Path
from datetime import datetime, timedelta
import psutil
import os

def format_time(seconds):
    """格式化时间"""
    if seconds < 60:
        return f"{seconds:.0f}s"
    elif seconds < 3600:
        return f"{seconds//60:.0f}m {seconds%60:.0f}s"
    else:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{hours:.0f}h {minutes:.0f}m"

def get_memory_usage():
    """获取内存使用情况"""
    memory = psutil.virtual_memory()
    return {
        'used_gb': memory.used / (1024**3),
        'available_gb': memory.available / (1024**3),
        'percent': memory.percent
    }

def monitor_processing():
    """监控处理进度"""
    cache_file = Path("/mnt/d/desktop/appp/structured_data/cache/processing_cache.pkl")
    progress_file = Path("/mnt/d/desktop/appp/structured_data/cache/progress.json")
    log_dir = Path("/mnt/d/desktop/appp/structured_data/logs")
    
    total_files = 191
    start_time = None
    
    print("🚀 PDF处理进度监控器启动")
    print("=" * 60)
    
    while True:
        try:
            # 检查缓存文件
            processed_count = 0
            if cache_file.exists():
                try:
                    with open(cache_file, 'rb') as f:
                        cache = pickle.load(f)
                        processed_count = len(cache)
                except Exception as e:
                    pass
            
            # 检查进度文件
            progress_info = {}
            if progress_file.exists():
                try:
                    with open(progress_file, 'r', encoding='utf-8') as f:
                        progress_info = json.load(f)
                        if not start_time and progress_info.get('start_time'):
                            start_time = datetime.fromisoformat(progress_info['start_time'])
                except Exception as e:
                    pass
            
            # 获取最新日志
            latest_log = None
            if log_dir.exists():
                log_files = list(log_dir.glob("*.log"))
                if log_files:
                    latest_log = max(log_files, key=lambda x: x.stat().st_mtime)
            
            # 内存使用
            memory = get_memory_usage()
            
            # 计算统计信息
            if not start_time:
                start_time = datetime.now()
            
            elapsed_time = (datetime.now() - start_time).total_seconds()
            
            # 显示状态
            os.system('clear' if os.name == 'posix' else 'cls')
            print("🚀 PDF处理进度监控")
            print("=" * 60)
            print(f"⏰ 开始时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"⏱️  已运行: {format_time(elapsed_time)}")
            print(f"📁 总文件数: {total_files}")
            
            if progress_info:
                proc_count = progress_info.get('processed_count', 0)
                failed_count = progress_info.get('failed_count', 0)
                cached_count = progress_info.get('cached_count', 0)
                
                total_processed = proc_count + failed_count + cached_count
                success_rate = (proc_count / max(total_processed, 1)) * 100
                progress_percent = (total_processed / total_files) * 100
                
                print(f"✅ 已处理: {proc_count}")
                print(f"❌ 失败: {failed_count}")
                print(f"💾 缓存命中: {cached_count}")
                print(f"📊 总进度: {total_processed}/{total_files} ({progress_percent:.1f}%)")
                print(f"📈 成功率: {success_rate:.1f}%")
                
                # 预估剩余时间
                if total_processed > 0 and elapsed_time > 0:
                    avg_time_per_file = elapsed_time / total_processed
                    remaining_files = total_files - total_processed
                    estimated_remaining = avg_time_per_file * remaining_files
                    
                    print(f"🔮 预计剩余: {format_time(estimated_remaining)}")
                    
                    # 预计完成时间
                    estimated_finish = datetime.now() + timedelta(seconds=estimated_remaining)
                    print(f"🎯 预计完成: {estimated_finish.strftime('%H:%M:%S')}")
            
            print("\n💾 系统资源:")
            print(f"   内存使用: {memory['used_gb']:.1f} GB ({memory['percent']:.1f}%)")
            print(f"   可用内存: {memory['available_gb']:.1f} GB")
            
            if latest_log:
                print(f"\n📝 最新日志: {latest_log.name}")
                try:
                    # 读取最后几行日志
                    with open(latest_log, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                        last_lines = lines[-3:] if len(lines) >= 3 else lines
                        for line in last_lines:
                            if line.strip():
                                print(f"   {line.strip()}")
                except Exception:
                    pass
            
            print(f"\n🔄 更新时间: {datetime.now().strftime('%H:%M:%S')}")
            print("按 Ctrl+C 退出监控")
            
            time.sleep(10)  # 每10秒更新一次
            
        except KeyboardInterrupt:
            print("\n👋 监控器已退出")
            break
        except Exception as e:
            print(f"\n❌ 监控错误: {e}")
            time.sleep(5)

if __name__ == "__main__":
    monitor_processing()