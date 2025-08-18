#!/bin/bash

# EVM多链自动监控转账工具启动脚本

echo "🚀 EVM多链自动监控转账工具"
echo "================================"

# 检查Python版本
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 未安装，请先安装Python3"
    exit 1
fi

# 检查依赖是否安装
echo "📦 检查依赖..."
if ! python3 -c "import aiosqlite, web3, colorama, requests, dotenv, eth_account" 2>/dev/null; then
    echo "📥 安装依赖包..."
    pip3 install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "❌ 依赖安装失败，请手动安装: pip3 install -r requirements.txt"
        exit 1
    fi
fi

echo "✅ 依赖检查完成"
echo "🎯 目标地址: 0x6b219df8c31c6b39a1a9b88446e0199be8f63cf1"
echo "📱 Telegram通知已配置"
echo "⚡ 优化速度: 300-500 CU/s"
echo "================================"
echo ""

# 启动程序
python3 main.py
