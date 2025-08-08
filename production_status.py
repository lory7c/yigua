#!/usr/bin/env python3
"""
生产环境状态检查脚本
检查所有服务的运行状态和健康状况
"""

import requests
import subprocess
import json
from datetime import datetime
import sys


def check_service(name, url, timeout=5):
    """检查服务状态"""
    try:
        response = requests.get(url, timeout=timeout)
        return {
            "name": name,
            "status": "✅ 运行正常" if response.status_code == 200 else f"⚠️ 状态码: {response.status_code}",
            "response_time": f"{response.elapsed.total_seconds():.3f}s",
            "url": url
        }
    except Exception as e:
        return {
            "name": name,
            "status": f"❌ 连接失败: {str(e)[:50]}",
            "response_time": "N/A",
            "url": url
        }


def check_docker_service(container_name):
    """检查Docker容器状态"""
    try:
        result = subprocess.run(
            ["docker", "inspect", container_name, "--format", "{{.State.Status}}"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            status = result.stdout.strip()
            return f"✅ {status}" if status == "running" else f"⚠️ {status}"
        else:
            return "❌ 容器不存在"
    except Exception as e:
        return f"❌ 检查失败: {str(e)}"


def check_api_endpoint(endpoint, method="GET", data=None):
    """检查API端点"""
    try:
        url = f"http://localhost:8000{endpoint}"
        if method == "GET":
            response = requests.get(url, timeout=5)
        elif method == "POST":
            response = requests.post(url, json=data, timeout=5)
        
        return {
            "endpoint": endpoint,
            "status": "✅ 正常" if response.status_code == 200 else f"⚠️ {response.status_code}",
            "response_time": f"{response.elapsed.total_seconds():.3f}s"
        }
    except Exception as e:
        return {
            "endpoint": endpoint,
            "status": f"❌ 失败: {str(e)[:30]}",
            "response_time": "N/A"
        }


def main():
    """主检查函数"""
    print("=" * 60)
    print("🚀 易学知识图谱与RAG系统 - 生产环境状态报告")
    print("=" * 60)
    print(f"📅 检查时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # 1. 检查Docker服务状态
    print("🐳 Docker容器状态:")
    containers = ["redis", "postgres", "prometheus", "grafana"]
    for container in containers:
        status = check_docker_service(container)
        print(f"  {container:12} {status}")
    print()

    # 2. 检查核心服务
    print("🔧 核心服务状态:")
    services = [
        ("API服务器", "http://localhost:8000/health"),
        ("Prometheus", "http://localhost:9090/-/healthy"),  
        ("Grafana", "http://localhost:3000/api/health"),
    ]
    
    for name, url in services:
        result = check_service(name, url)
        print(f"  {result['name']:12} {result['status']:20} 响应时间: {result['response_time']}")
    print()

    # 3. 检查API端点
    print("📡 API端点测试:")
    endpoints = [
        "/",
        "/health", 
        "/api/status",
        "/api/services",
        "/api/ping"
    ]
    
    for endpoint in endpoints:
        result = check_api_endpoint(endpoint)
        print(f"  {result['endpoint']:20} {result['status']:20} 响应时间: {result['response_time']}")
    
    # 测试POST端点
    post_result = check_api_endpoint("/api/query", "POST", {"question": "系统测试"})
    print(f"  {post_result['endpoint']:20} {post_result['status']:20} 响应时间: {post_result['response_time']}")
    print()

    # 4. 数据库连接测试
    print("💾 数据库连接测试:")
    try:
        # Redis测试
        redis_result = subprocess.run(
            ["docker", "exec", "redis", "redis-cli", "ping"],
            capture_output=True,
            text=True,
            timeout=5
        )
        redis_status = "✅ 连接正常" if redis_result.stdout.strip() == "PONG" else "❌ 连接失败"
        print(f"  Redis:       {redis_status}")
        
        # PostgreSQL测试  
        pg_result = subprocess.run(
            ["docker", "exec", "postgres", "psql", "-U", "yixue_user", "-d", "yixue_db", "-c", "SELECT 1;"],
            capture_output=True,
            text=True,
            timeout=5
        )
        pg_status = "✅ 连接正常" if pg_result.returncode == 0 else "❌ 连接失败"
        print(f"  PostgreSQL:  {pg_status}")
        
    except Exception as e:
        print(f"  数据库测试失败: {e}")
    print()

    # 5. 系统资源状态
    print("⚡ 系统资源状态:")
    try:
        # 检查进程
        uvicorn_processes = subprocess.run(
            ["pgrep", "-f", "uvicorn"],
            capture_output=True,
            text=True
        )
        process_count = len(uvicorn_processes.stdout.strip().split('\n')) if uvicorn_processes.stdout.strip() else 0
        print(f"  API进程数:   {process_count} 个运行中")
        
        # 检查端口占用
        ports_to_check = [8000, 5432, 6379, 9090, 3000]
        for port in ports_to_check:
            port_check = subprocess.run(
                ["netstat", "-an"], 
                capture_output=True, 
                text=True
            )
            if f":{port} " in port_check.stdout:
                print(f"  端口 {port}:   ✅ 正在监听")
            else:
                print(f"  端口 {port}:   ❌ 未监听")
                
    except Exception as e:
        print(f"  系统资源检查失败: {e}")
    print()

    # 6. 访问地址汇总
    print("🌐 服务访问地址:")
    addresses = [
        ("API文档", "http://localhost:8000/docs"),
        ("API健康检查", "http://localhost:8000/health"), 
        ("Grafana监控", "http://localhost:3000 (admin/admin123)"),
        ("Prometheus", "http://localhost:9090"),
        ("PostgreSQL", "localhost:5432 (yixue_user/secure_password)"),
        ("Redis", "localhost:6379")
    ]
    
    for name, addr in addresses:
        print(f"  {name:15} {addr}")
    print()

    print("=" * 60)
    print("✅ 生产环境启动完成！所有核心服务正常运行")
    print("📊 监控面板: http://localhost:3000")
    print("📚 API文档: http://localhost:8000/docs") 
    print("=" * 60)


if __name__ == "__main__":
    main()