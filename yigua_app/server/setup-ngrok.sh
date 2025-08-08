#!/bin/bash

echo "📱 易卦服务器内网穿透设置"
echo "=========================="
echo ""
echo "选择内网穿透工具："
echo "1. ngrok (国际，免费)"
echo "2. 花生壳 (国内，稳定)"
echo "3. cpolar (国内备选)"
echo ""

# ngrok方案
echo "【ngrok设置步骤】"
echo "1. 注册账号: https://ngrok.com/signup"
echo "2. 下载ngrok: https://ngrok.com/download"
echo "3. 配置token: ngrok authtoken YOUR_TOKEN"
echo "4. 启动穿透: ngrok http 8888"
echo ""

# 自动化脚本
echo "启动本地服务器..."
cd server
npm install
npm start &

echo ""
echo "服务器已启动在端口 8888"
echo "现在运行: ngrok http 8888"
echo "将获得的公网地址填入APP配置中"