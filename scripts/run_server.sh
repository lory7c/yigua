#!/bin/bash

# 易学RAG系统启动脚本

echo "=========================================="
echo "易学知识图谱与RAG系统启动"
echo "=========================================="

# 设置环境变量
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
export CUDA_VISIBLE_DEVICES=0
export TOKENIZERS_PARALLELISM=false

# 检查Python环境
if ! command -v python3 &> /dev/null; then
    echo "错误: Python3未安装"
    exit 1
fi

# 检查虚拟环境
if [ ! -d "venv" ]; then
    echo "创建虚拟环境..."
    python3 -m venv venv
fi

# 激活虚拟环境
source venv/bin/activate

# 安装依赖
echo "检查并安装依赖..."
pip install -q --upgrade pip
pip install -q -r requirements.txt

# 创建必要的目录
mkdir -p data logs uploads exports cache models templates

# 初始化系统（如果需要）
if [ ! -f "data/knowledge_graph.pkl" ]; then
    echo "首次运行，初始化系统..."
    python scripts/init_system.py
fi

# 启动服务
echo "启动API服务..."

# 开发模式
if [ "$1" == "dev" ]; then
    uvicorn api.main:app --reload --host 0.0.0.0 --port 8000 --log-level info
# 生产模式
elif [ "$1" == "prod" ]; then
    uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers 4 --log-level warning
# Docker模式
elif [ "$1" == "docker" ]; then
    docker-compose up -d
    echo "服务已在Docker中启动"
    echo "API地址: http://localhost:8000"
    echo "Qdrant地址: http://localhost:6333"
    echo "Jupyter地址: http://localhost:8888 (token: yijing2024)"
else
    # 默认模式
    uvicorn api.main:app --host 0.0.0.0 --port 8000 --log-level info
fi