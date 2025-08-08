#!/bin/bash
# 云端易学知识系统部署脚本

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查Docker和Docker Compose
check_docker() {
    log_info "检查Docker环境..."
    
    if ! command -v docker &> /dev/null; then
        log_error "Docker未安装，请先安装Docker"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose未安装，请先安装Docker Compose"
        exit 1
    fi
    
    if ! docker info &> /dev/null; then
        log_error "Docker服务未运行，请启动Docker服务"
        exit 1
    fi
    
    log_success "Docker环境检查通过"
}

# 创建必要的目录
create_directories() {
    log_info "创建必要目录..."
    
    directories=(
        "data"
        "data/qdrant"
        "data/redis"
        "uploads"
        "exports"
        "logs"
        "backups"
        "letsencrypt"
        "static"
        "monitoring/grafana/provisioning/dashboards"
        "monitoring/grafana/provisioning/datasources"
        "nginx"
    )
    
    for dir in "${directories[@]}"; do
        mkdir -p "$dir"
        log_info "创建目录: $dir"
    done
    
    log_success "目录创建完成"
}

# 设置权限
set_permissions() {
    log_info "设置目录权限..."
    
    chmod -R 755 data/
    chmod -R 755 uploads/
    chmod -R 755 exports/
    chmod -R 755 logs/
    chmod -R 755 backups/
    
    log_success "权限设置完成"
}

# 生成环境配置文件
generate_env_file() {
    log_info "生成环境配置文件..."
    
    if [ ! -f ".env" ]; then
        cat > .env << EOF
# 云端易学知识系统环境配置

# 基本配置
SECRET_KEY=yixue-secret-key-$(date +%s)-$(shuf -i 1000-9999 -n 1)
ACME_EMAIL=admin@yixue.local

# 数据库配置
POSTGRES_USER=yixue_user
POSTGRES_PASSWORD=secure_password_$(shuf -i 1000-9999 -n 1)

# MinIO配置
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=minioadmin123456

# Grafana配置
GRAFANA_PASSWORD=admin123456

# Jupyter配置
JUPYTER_TOKEN=yixue2024

# 其他配置
TZ=Asia/Shanghai
COMPOSE_PROJECT_NAME=yixue
EOF
        log_success "环境配置文件已生成: .env"
    else
        log_warning "环境配置文件已存在，跳过生成"
    fi
}

# 构建Docker镜像
build_images() {
    log_info "构建Docker镜像..."
    
    if [ ! -f "Dockerfile" ]; then
        log_warning "Dockerfile不存在，创建基础Dockerfile..."
        cat > Dockerfile << 'EOF'
FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    curl \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# 复制项目文件
COPY . .

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["python", "api/api_server.py"]
EOF
    fi
    
    docker-compose build --no-cache
    log_success "Docker镜像构建完成"
}

# 启动服务
start_services() {
    log_info "启动服务..."
    
    # 首先启动基础服务
    docker-compose up -d redis postgres qdrant
    
    log_info "等待基础服务就绪..."
    sleep 10
    
    # 检查服务状态
    check_service_health() {
        local service=$1
        local max_attempts=30
        local attempt=1
        
        while [ $attempt -le $max_attempts ]; do
            if docker-compose ps | grep "$service" | grep -q "healthy\|Up"; then
                log_success "$service 服务已就绪"
                return 0
            fi
            
            log_info "等待 $service 服务就绪... ($attempt/$max_attempts)"
            sleep 5
            attempt=$((attempt + 1))
        done
        
        log_error "$service 服务启动超时"
        return 1
    }
    
    # 检查基础服务
    check_service_health "redis"
    check_service_health "postgres"
    check_service_health "qdrant"
    
    # 启动其他服务
    docker-compose up -d
    
    log_success "所有服务启动完成"
}

# 检查服务状态
check_services() {
    log_info "检查服务状态..."
    
    services=("redis" "postgres" "qdrant" "yixue-api-1" "yixue-api-2" "traefik" "nginx")
    
    for service in "${services[@]}"; do
        if docker-compose ps | grep -q "$service.*Up"; then
            log_success "$service: 运行中"
        else
            log_error "$service: 未运行"
        fi
    done
}

# 显示访问信息
show_access_info() {
    log_info "服务访问信息:"
    echo ""
    echo "🌐 主要服务:"
    echo "   API服务: http://localhost:80/api/"
    echo "   API文档: http://localhost:80/api/docs"
    echo ""
    echo "📊 监控服务:"
    echo "   Traefik面板: http://localhost:8080"
    echo "   Grafana监控: http://localhost:3000 (admin/admin123456)"
    echo "   Prometheus: http://localhost:9090"
    echo ""
    echo "🔧 开发服务:"
    echo "   Jupyter Lab: http://localhost:8888 (token: yixue2024)"
    echo "   MinIO控制台: http://localhost:9001 (minioadmin/minioadmin123456)"
    echo ""
    echo "💾 数据库服务:"
    echo "   PostgreSQL: localhost:5432 (yixue_user/secure_password)"
    echo "   Redis: localhost:6379"
    echo "   Qdrant: http://localhost:6333"
    echo ""
}

# 初始化数据
init_data() {
    log_info "初始化数据..."
    
    # 等待API服务就绪
    max_attempts=30
    attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if curl -s http://localhost:80/health > /dev/null 2>&1; then
            log_success "API服务已就绪"
            break
        fi
        
        log_info "等待API服务就绪... ($attempt/$max_attempts)"
        sleep 5
        attempt=$((attempt + 1))
    done
    
    if [ $attempt -gt $max_attempts ]; then
        log_error "API服务启动超时"
        return 1
    fi
    
    # 这里可以添加初始化数据的脚本
    log_info "可以开始使用系统了"
}

# 停止服务
stop_services() {
    log_info "停止服务..."
    docker-compose down
    log_success "服务已停止"
}

# 清理数据
clean_data() {
    log_warning "这将删除所有数据，包括数据库、缓存、日志等"
    read -p "确认清理数据？(y/N): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        log_info "清理数据..."
        docker-compose down -v
        docker system prune -f
        rm -rf data/ uploads/ exports/ logs/ backups/
        log_success "数据清理完成"
    else
        log_info "取消清理操作"
    fi
}

# 查看日志
view_logs() {
    local service=${1:-""}
    
    if [ -n "$service" ]; then
        docker-compose logs -f "$service"
    else
        docker-compose logs -f
    fi
}

# 主函数
main() {
    case "${1:-help}" in
        "deploy"|"up")
            check_docker
            create_directories
            set_permissions
            generate_env_file
            build_images
            start_services
            sleep 5
            check_services
            init_data
            show_access_info
            ;;
        "start")
            docker-compose up -d
            check_services
            show_access_info
            ;;
        "stop")
            stop_services
            ;;
        "restart")
            stop_services
            sleep 2
            docker-compose up -d
            check_services
            ;;
        "status")
            check_services
            ;;
        "logs")
            view_logs "$2"
            ;;
        "clean")
            clean_data
            ;;
        "info")
            show_access_info
            ;;
        "help"|*)
            echo "云端易学知识系统部署脚本"
            echo ""
            echo "用法: $0 [命令]"
            echo ""
            echo "命令:"
            echo "  deploy, up    完整部署系统（首次部署使用）"
            echo "  start         启动服务"
            echo "  stop          停止服务"
            echo "  restart       重启服务"
            echo "  status        查看服务状态"
            echo "  logs [服务名] 查看日志"
            echo "  clean         清理所有数据"
            echo "  info          显示访问信息"
            echo "  help          显示帮助信息"
            echo ""
            echo "示例:"
            echo "  $0 deploy     # 首次部署"
            echo "  $0 start      # 启动服务"
            echo "  $0 logs api   # 查看API日志"
            echo "  $0 status     # 查看服务状态"
            ;;
    esac
}

# 执行主函数
main "$@"