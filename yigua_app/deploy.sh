#!/bin/bash

# 易经卦象云端服务部署脚本
# 支持Vercel + Supabase的零成本部署方案

set -e

echo "========================================"
echo "     易经卦象云端服务部署脚本      "
echo "========================================"
echo ""

# 检查必要的工具
check_requirements() {
    echo "✔ 检查部署环境..."
    
    # 检查Node.js
    if ! command -v node &> /dev/null; then
        echo "❌ 需要安装Node.js"
        echo "请访问: https://nodejs.org/"
        exit 1
    fi
    
    # 检查npm
    if ! command -v npm &> /dev/null; then
        echo "❌ 需要安装npm"
        exit 1
    fi
    
    echo "✓ Node.js 版本: $(node -v)"
    echo "✓ npm 版本: $(npm -v)"
    echo ""
}

# 安装Vercel CLI
install_vercel() {
    echo "✔ 安装Vercel CLI..."
    
    if ! command -v vercel &> /dev/null; then
        npm install -g vercel
        echo "✓ Vercel CLI 安装成功"
    else
        echo "✓ Vercel CLI 已安装: $(vercel --version)"
    fi
    echo ""
}

# 安装项目依赖
install_dependencies() {
    echo "✔ 安装项目依赖..."
    
    # 创建package.json如果不存在
    if [ ! -f "package.json" ]; then
        cat > package.json << 'EOF'
{
  "name": "yigua-api",
  "version": "1.0.0",
  "description": "易经卦象云端服务API",
  "scripts": {
    "dev": "vercel dev",
    "deploy": "vercel --prod",
    "deploy:preview": "vercel"
  },
  "dependencies": {
    "@supabase/supabase-js": "^2.38.0",
    "@vercel/node": "^3.0.0"
  },
  "engines": {
    "node": ">=18.x"
  }
}
EOF
        echo "✓ 创建 package.json"
    fi
    
    # 安装依赖
    npm install
    echo "✓ 依赖安装完成"
    echo ""
}

# 配置环境变量
setup_env() {
    echo "✔ 配置环境变量..."
    
    # 创建.env.example
    cat > .env.example << 'EOF'
# Supabase配置 (免费套餐)
# 获取地址: https://supabase.com/
SUPABASE_URL=your_supabase_url
SUPABASE_ANON_KEY=your_supabase_anon_key

# Cloudflare Workers AI (可选，免费套餐)
# 获取地址: https://developers.cloudflare.com/workers-ai/
CF_ACCOUNT_ID=your_cloudflare_account_id
CF_API_TOKEN=your_cloudflare_api_token

# OpenAI API (可选，付费)
# 获取地址: https://platform.openai.com/
OPENAI_API_KEY=your_openai_api_key

# 同步令牌 (用于简单认证)
SYNC_SECRET_TOKEN=your_secret_token_here

# 是否需要认证
REQUIRE_AUTH=false
EOF
    
    if [ ! -f ".env.local" ]; then
        echo "✓ 创建 .env.example"
        echo ""
        echo "⚠️  请复制 .env.example 为 .env.local 并填写您的配置："
        echo "   cp .env.example .env.local"
        echo "   然后编辑 .env.local 文件"
        echo ""
    else
        echo "✓ .env.local 已存在"
    fi
}

# 初始化Supabase数据库
setup_supabase() {
    echo "✔ Supabase数据库设置指南..."
    echo ""
    echo "1. 访问 https://supabase.com/ 并创建免费账号"
    echo "2. 创建新项目 (选择新加坡或香港区域)"
    echo "3. 在SQL编辑器中执行 supabase/schema.sql"
    echo "4. 在Settings > API中获取URL和Anon Key"
    echo "5. 将配置填入 .env.local"
    echo ""
    read -p "是否已完成Supabase设置？ (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "请先完成Supabase设置"
        exit 1
    fi
    echo ""
}

# 部署到Vercel
deploy_vercel() {
    echo "✔ 部署到Vercel..."
    echo ""
    
    # 检查是否登录
    if ! vercel whoami &> /dev/null; then
        echo "需要登录Vercel账号"
        vercel login
    fi
    
    echo "选择部署方式："
    echo "1. 预览部署 (测试环境)"
    echo "2. 生产部署 (正式环境)"
    read -p "请选择 (1/2): " deploy_choice
    
    case $deploy_choice in
        1)
            echo "正在进行预览部署..."
            vercel
            ;;
        2)
            echo "正在进行生产部署..."
            vercel --prod
            ;;
        *)
            echo "无效选择"
            exit 1
            ;;
    esac
    
    echo ""
    echo "✓ 部署完成！"
    echo ""
}

# 显示部署信息
show_info() {
    echo "========================================"
    echo "           部署成功！              "
    echo "========================================"
    echo ""
    echo "🎆 恭喜！您的易经卦象API已成功部署到云端"
    echo ""
    echo "📍 API端点："
    echo "   - 获取卦象: /api/hexagram/{id}"
    echo "   - 全文搜索: /api/search?q=关键词"
    echo "   - AI解读:  /api/interpret"
    echo "   - 数据同步: /api/sync"
    echo ""
    echo "📊 使用统计："
    echo "   Vercel免费套餐："
    echo "   - 100GB带宽/月"
    echo "   - 100,000函数调用/月"
    echo "   - 无限部署次数"
    echo ""
    echo "   Supabase免费套餐："
    echo "   - 500MB数据库"
    echo "   - 2GB文件存储"
    echo "   - 50,000活跃用户/月"
    echo ""
    echo "📖 文档："
    echo "   - Vercel: https://vercel.com/docs"
    echo "   - Supabase: https://supabase.com/docs"
    echo ""
    echo "🔧 管理面板："
    echo "   - Vercel: https://vercel.com/dashboard"
    echo "   - Supabase: https://app.supabase.com/"
    echo ""
    echo "========================================"
}

# 主流程
main() {
    check_requirements
    install_vercel
    install_dependencies
    setup_env
    
    echo "选择操作："
    echo "1. 完整部署 (包括Supabase设置)"
    echo "2. 仅部署API (跳过数据库设置)"
    echo "3. 本地开发模式"
    read -p "请选择 (1/2/3): " choice
    
    case $choice in
        1)
            setup_supabase
            deploy_vercel
            show_info
            ;;
        2)
            deploy_vercel
            show_info
            ;;
        3)
            echo "启动本地开发服务器..."
            vercel dev
            ;;
        *)
            echo "无效选择"
            exit 1
            ;;
    esac
}

# 捕获错误
trap 'echo "❌ 部署失败！请检查错误信息"; exit 1' ERR

# 运行主流程
main