#!/bin/bash

# EVM多链自动监控转账工具 - 一键安装脚本
# GitHub: https://github.com/haohaoi34/jiankong

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印彩色信息
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查操作系统
check_os() {
    print_info "检查操作系统..."
    
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        OS="linux"
        DISTRO=$(lsb_release -si 2>/dev/null || echo "Unknown")
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        OS="macos"
        DISTRO="macOS"
    elif [[ "$OSTYPE" == "cygwin" ]] || [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
        OS="windows"
        DISTRO="Windows"
    else
        print_error "不支持的操作系统: $OSTYPE"
        exit 1
    fi
    
    print_info "检测到操作系统: $DISTRO"
}

# 检查Python版本
check_python() {
    print_info "检查Python安装..."
    
    # 检查Python 3.10+
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
        PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
        PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)
        
        if [[ $PYTHON_MAJOR -eq 3 && $PYTHON_MINOR -ge 10 ]]; then
            PYTHON_CMD="python3"
            print_success "找到Python $PYTHON_VERSION"
            return 0
        else
            print_warning "Python版本过低: $PYTHON_VERSION (需要3.10+)"
        fi
    fi
    
    # 尝试安装Python
    print_info "尝试安装Python 3.10+..."
    
    # 根据用户权限选择安装方式
    if [[ $EUID -eq 0 ]]; then
        # root用户直接安装
        SUDO_CMD=""
    else
        # 普通用户使用sudo
        SUDO_CMD="sudo"
    fi
    
    if [[ "$OS" == "linux" ]]; then
        if command -v apt-get &> /dev/null; then
            $SUDO_CMD apt-get update
            $SUDO_CMD apt-get install -y python3.10 python3.10-pip python3.10-venv
            PYTHON_CMD="python3.10"
        elif command -v yum &> /dev/null; then
            $SUDO_CMD yum install -y python3.10 python3.10-pip
            PYTHON_CMD="python3.10"
        elif command -v dnf &> /dev/null; then
            $SUDO_CMD dnf install -y python3.10 python3.10-pip
            PYTHON_CMD="python3.10"
        else
            print_error "无法自动安装Python，请手动安装Python 3.10+"
            exit 1
        fi
    elif [[ "$OS" == "macos" ]]; then
        if command -v brew &> /dev/null; then
            brew install python@3.10
            PYTHON_CMD="python3.10"
        else
            print_error "请先安装Homebrew，然后运行: brew install python@3.10"
            exit 1
        fi
    else
        print_error "请手动安装Python 3.10+: https://www.python.org/downloads/"
        exit 1
    fi
    
    print_success "Python安装完成"
}

# 检查pip
check_pip() {
    print_info "检查pip..."
    
    if ! $PYTHON_CMD -m pip --version &> /dev/null; then
        print_info "安装pip..."
        
        # 根据用户权限选择安装方式
        if [[ $EUID -eq 0 ]]; then
            SUDO_CMD=""
        else
            SUDO_CMD="sudo"
        fi
        
        if [[ "$OS" == "linux" ]]; then
            if command -v apt-get &> /dev/null; then
                $SUDO_CMD apt-get install -y python3-pip
            elif command -v yum &> /dev/null; then
                $SUDO_CMD yum install -y python3-pip
            elif command -v dnf &> /dev/null; then
                $SUDO_CMD dnf install -y python3-pip
            fi
        fi
        
        # 如果仍然没有pip，尝试get-pip.py
        if ! $PYTHON_CMD -m pip --version &> /dev/null; then
            print_info "下载并安装pip..."
            curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
            $PYTHON_CMD get-pip.py
            rm get-pip.py
        fi
    fi
    
    print_success "pip检查完成"
}

# 检查git
check_git() {
    print_info "检查Git..."
    
    if ! command -v git &> /dev/null; then
        print_info "安装Git..."
        
        # 根据用户权限选择安装方式
        if [[ $EUID -eq 0 ]]; then
            SUDO_CMD=""
        else
            SUDO_CMD="sudo"
        fi
        
        if [[ "$OS" == "linux" ]]; then
            if command -v apt-get &> /dev/null; then
                $SUDO_CMD apt-get install -y git
            elif command -v yum &> /dev/null; then
                $SUDO_CMD yum install -y git
            elif command -v dnf &> /dev/null; then
                $SUDO_CMD dnf install -y git
            fi
        elif [[ "$OS" == "macos" ]]; then
            if command -v brew &> /dev/null; then
                brew install git
            else
                print_error "请先安装Homebrew，然后运行: brew install git"
                exit 1
            fi
        fi
    fi
    
    print_success "Git检查完成"
}

# 克隆仓库
clone_repository() {
    print_info "克隆GitHub仓库..."
    
    REPO_URL="https://github.com/haohaoi34/jiankong.git"
    PROJECT_DIR="jiankong"
    
    # 如果目录已存在，询问是否覆盖
    if [[ -d "$PROJECT_DIR" ]]; then
        read -p "目录 $PROJECT_DIR 已存在，是否删除并重新克隆？(y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            rm -rf "$PROJECT_DIR"
        else
            print_info "使用现有目录"
            cd "$PROJECT_DIR"
            git pull origin main
            return 0
        fi
    fi
    
    # 克隆仓库
    if git clone "$REPO_URL" "$PROJECT_DIR"; then
        cd "$PROJECT_DIR"
        print_success "仓库克隆完成"
    else
        print_error "克隆仓库失败，请检查网络连接"
        exit 1
    fi
}

# 创建虚拟环境
create_venv() {
    print_info "创建Python虚拟环境..."
    
    if [[ -d "venv" ]]; then
        print_info "虚拟环境已存在，跳过创建"
    else
        $PYTHON_CMD -m venv venv
        print_success "虚拟环境创建完成"
    fi
    
    # 激活虚拟环境
    if [[ "$OS" == "windows" ]]; then
        source venv/Scripts/activate
    else
        source venv/bin/activate
    fi
    
    print_info "虚拟环境已激活"
}

# 安装依赖
install_dependencies() {
    print_info "安装Python依赖包..."
    
    # 升级pip
    python -m pip install --upgrade pip
    
    # 创建requirements.txt
    cat > requirements.txt << EOF
web3>=6.0.0
prompt-toolkit>=3.0.0
aiosqlite>=0.19.0
requests>=2.28.0
python-dotenv>=1.0.0
eth-account>=0.8.0
asyncio
EOF
    
    # 安装依赖
    python -m pip install -r requirements.txt
    
    print_success "依赖包安装完成"
}

# 配置环境变量
configure_env() {
    print_info "配置环境变量..."
    
    # 检查.env文件是否存在
    if [[ -f ".env" ]]; then
        print_info ".env文件已存在"
        read -p "是否重新配置？(y/n): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            return 0
        fi
    fi
    
    # 提示输入Alchemy API密钥
    echo
    print_info "请访问 https://www.alchemy.com/ 获取免费API密钥"
    print_info "注册账户后，在Dashboard中创建新的API Key"
    echo
    
    while true; do
        read -p "请输入您的Alchemy API密钥: " ALCHEMY_API_KEY
        if [[ -n "$ALCHEMY_API_KEY" ]]; then
            break
        else
            print_warning "API密钥不能为空，请重新输入"
        fi
    done
    
    # 创建.env文件
    cat > .env << EOF
# Alchemy API密钥 - 从 https://www.alchemy.com/ 获取
ALCHEMY_API_KEY=$ALCHEMY_API_KEY

# 私钥 - 支持混合文本输入，系统会自动提取有效私钥
PRIVATE_KEYS=

# Discord Webhook URL（可选） - 用于通知
# DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/your_webhook_url
EOF
    
    print_success "环境变量配置完成"
    print_info "您可以稍后在程序中配置私钥，或编辑.env文件"
}

# 创建默认配置
create_config() {
    print_info "创建默认配置文件..."
    
    if [[ -f "config.json" ]]; then
        print_info "config.json已存在，跳过创建"
        return 0
    fi
    
    cat > config.json << 'EOF'
{
  "chains": [
    {
      "name": "ETH_MAINNET",
      "chain_id": 1,
      "recipient_address": "0x0000000000000000000000000000000000000000",
      "min_amount": "0.01"
    }
  ],
  "erc20": [],
  "settings": {
    "monitoring_interval": 0.1,
    "round_pause": 60,
    "gas_threshold_gwei": 50,
    "gas_wait_time": 60
  }
}
EOF
    
    print_success "默认配置文件创建完成"
}

# 创建目录结构
create_directories() {
    print_info "创建必要的目录..."
    
    mkdir -p logs
    mkdir -p data
    
    print_success "目录结构创建完成"
}

# 测试安装
test_installation() {
    print_info "测试安装..."
    
    # 测试Python导入
    if python -c "
import asyncio
import json
import logging
import os
import re
import sqlite3
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import aiosqlite
import requests
from web3 import Web3
from web3.middleware import geth_poa_middleware
from eth_account import Account
from prompt_toolkit import prompt
from dotenv import load_dotenv
print('所有依赖包导入成功')
"; then
        print_success "依赖包测试通过"
    else
        print_error "依赖包测试失败"
        exit 1
    fi
    
    # 测试主程序语法
    if python -m py_compile main.py; then
        print_success "主程序语法检查通过"
    else
        print_error "主程序语法检查失败"
        exit 1
    fi
}

# 显示完成信息
show_completion() {
    echo
    print_success "=============================================="
    print_success "  EVM多链监控工具安装完成！"
    print_success "=============================================="
    echo
    print_info "安装信息："
    echo "  • 操作系统: $DISTRO"
    echo "  • Python版本: $($PYTHON_CMD --version)"
    echo "  • 用户权限: $(if [[ $EUID -eq 0 ]]; then echo "管理员(root)"; else echo "普通用户"; fi)"
    echo "  • 安装路径: $(pwd)"
    echo
    print_info "下一步操作："
    echo "  1. 配置私钥和转账设置"
    echo "  2. 启动监控程序"
    echo
    print_info "启动命令："
    if [[ "$OS" == "windows" ]]; then
        echo "  venv\\Scripts\\activate && python main.py"
    else
        echo "  source venv/bin/activate && python main.py"
    fi
    echo
    print_info "或者直接运行："
    echo "  python main.py"
    echo
    print_info "重要提醒："
    echo "  • 请在交互式菜单中配置您的私钥和接收地址"
    echo "  • 建议先在测试网测试后再使用主网"
    echo "  • 请妥善保管您的私钥，不要泄露给他人"
    echo "  • 程序会自动屏蔽无交易历史的链以节省资源"
    echo "  • 支持所有用户权限运行，包括root用户"
    echo
    print_info "获取帮助："
    echo "  • GitHub: https://github.com/haohaoi34/jiankong"
    echo "  • 文档: 查看README.md"
    echo
}

# 启动程序
start_program() {
    echo
    read -p "是否立即启动程序？(y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_info "启动EVM多链监控工具..."
        python main.py
    else
        print_info "您可以稍后运行 'python main.py' 启动程序"
    fi
}

# 主函数
main() {
    echo "=============================================="
    echo "  EVM多链自动监控转账工具 - 一键安装"
    echo "  GitHub: https://github.com/haohaoi34/jiankong"
    echo "=============================================="
    echo
    
    # 检查用户权限信息（仅显示，不阻止）
    if [[ $EUID -eq 0 ]]; then
        print_info "检测到root权限，正在以管理员身份运行"
    else
        print_info "检测到普通用户权限，正在以用户身份运行"
    fi
    
    # 执行安装步骤
    check_os
    check_python
    check_pip
    check_git
    clone_repository
    create_venv
    install_dependencies
    configure_env
    create_config
    create_directories
    test_installation
    show_completion
    start_program
}

# 错误处理
trap 'print_error "安装过程中发生错误，请检查输出信息"; exit 1' ERR

# 运行主函数
main "$@"
