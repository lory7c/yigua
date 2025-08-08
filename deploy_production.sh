#!/bin/bash

# 生产环境一键部署脚本
# 易学知识图谱与RAG系统完整启动

echo "🚀 启动易学知识图谱与RAG系统生产环境..."
echo "==============================================="

# 1. 启动核心Docker服务
echo "📦 启动核心服务..."
docker-compose up -d redis postgres prometheus grafana

echo "⏳ 等待服务初始化..."
sleep 10

# 2. 检查服务状态
echo "🔍 检查服务状态..."
echo "Redis: $(docker exec redis redis-cli ping 2>/dev/null || echo 'FAILED')"
echo "PostgreSQL: $(docker exec postgres psql -U yixue_user -d yixue_db -c 'SELECT 1' 2>/dev/null && echo 'CONNECTED' || echo 'FAILED')"

# 3. 启动API服务器
echo "🌐 启动API服务器..."
nohup python api/simple_main.py > logs/api.log 2>&1 &
API_PID=$!
echo "API服务器PID: $API_PID"

# 4. 等待API启动
echo "⏳ 等待API服务启动..."
sleep 5

# 5. 验证部署
echo "✅ 验证部署状态..."
python production_status.py

echo ""
echo "==============================================="
echo "🎉 生产环境部署完成！"
echo ""
echo "📊 监控面板: http://localhost:3000"
echo "📚 API文档: http://localhost:8000/docs"
echo "🏥 健康检查: http://localhost:8000/health"
echo ""
echo "🔧 服务端口:"
echo "  - API服务器: 8000"
echo "  - PostgreSQL: 5432"
echo "  - Redis: 6379"
echo "  - Prometheus: 9090"
echo "  - Grafana: 3000"
echo ""
echo "📋 管理命令:"
echo "  - 查看状态: python production_status.py"
echo "  - 查看日志: tail -f logs/api.log"
echo "  - 停止服务: docker-compose down"
echo "==============================================="