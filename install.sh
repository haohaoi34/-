#!/bin/bash

# 钱包监控系统安装脚本 v3.0 - 纯RPC网络版
# 自动安装依赖并启动主程序

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${BLUE}🚀 钱包监控系统安装器 v3.0 - 纯RPC网络版${NC}"
echo -e "${BLUE}支持多个EVM兼容链 | 纯RPC模式 | 智能并发优化${NC}"
echo "========================================="

# 检测操作系统
echo -e "${CYAN}📋 检查操作系统...${NC}"
OS_TYPE=$(uname -s)
case "$OS_TYPE" in
    Linux*)  OS="Linux";;
    Darwin*) OS="macOS";;
    CYGWIN*|MINGW*|MSYS*) OS="Windows";;
    *) OS="Unknown";;
esac
echo -e "${GREEN}✅ 检测到 $OS 系统${NC}"

# 检测Python
echo -e "${CYAN}📋 检查Python...${NC}"
PYTHON_CMD=""
if command -v python3 &> /dev/null; then
    PY_VERSION=$(python3 --version 2>&1 | grep -oE '[0-9]+\.[0-9]+' | head -1)
    MAJOR=$(echo $PY_VERSION | cut -d. -f1)
    MINOR=$(echo $PY_VERSION | cut -d. -f2)
    if [[ $MAJOR -ge 3 && $MINOR -ge 7 ]]; then
        PYTHON_CMD="python3"
        echo -e "${GREEN}✅ Python: python3 (版本 $PY_VERSION)${NC}"
    fi
elif command -v python &> /dev/null; then
    PY_VERSION=$(python --version 2>&1 | grep -oE '[0-9]+\.[0-9]+' | head -1)
    MAJOR=$(echo $PY_VERSION | cut -d. -f1)
    MINOR=$(echo $PY_VERSION | cut -d. -f2)
    if [[ $MAJOR -ge 3 && $MINOR -ge 7 ]]; then
        PYTHON_CMD="python"
        echo -e "${GREEN}✅ Python: python (版本 $PY_VERSION)${NC}"
    fi
fi

if [ -z "$PYTHON_CMD" ]; then
    echo -e "${RED}❌ 未找到Python 3.7+${NC}"
    echo -e "${YELLOW}💡 请先安装Python 3.7或更高版本${NC}"
    exit 1
fi

# 检查pip
echo -e "${CYAN}📋 检查pip...${NC}"
if ! $PYTHON_CMD -m pip --version &> /dev/null; then
    echo -e "${RED}❌ pip未安装${NC}"
    echo -e "${YELLOW}💡 正在安装pip...${NC}"
    
    if [[ "$OS" == "macOS" ]]; then
        curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
        $PYTHON_CMD get-pip.py
        rm get-pip.py
    elif [[ "$OS" == "Linux" ]]; then
        if command -v apt-get &> /dev/null; then
            sudo apt-get update && sudo apt-get install -y python3-pip
        elif command -v yum &> /dev/null; then
            sudo yum install -y python3-pip
        elif command -v dnf &> /dev/null; then
            sudo dnf install -y python3-pip
        else
            curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
            $PYTHON_CMD get-pip.py
            rm get-pip.py
        fi
    fi
fi
echo -e "${GREEN}✅ pip可用${NC}"

# 安装依赖
echo -e "${CYAN}📦 安装Python依赖...${NC}"
PACKAGES=(
    "web3"
    "eth-account" 
    "colorama"
    "aiohttp"
    "cryptography"
    "requests"
)

for package in "${PACKAGES[@]}"; do
    echo -e "${CYAN}🔄 安装 $package...${NC}"
    if $PYTHON_CMD -m pip install "$package" &> /dev/null; then
        echo -e "${GREEN}✅ $package 安装成功${NC}"
    else
        echo -e "${YELLOW}🔄 尝试用户模式安装 $package...${NC}"
        if $PYTHON_CMD -m pip install --user "$package" &> /dev/null; then
            echo -e "${GREEN}✅ $package 安装成功 (用户模式)${NC}"
        else
            echo -e "${RED}❌ $package 安装失败${NC}"
        fi
    fi
done

# 检查文件
echo -e "${CYAN}📋 检查程序文件...${NC}"
if [ ! -f "wallet_monitor.py" ]; then
    echo -e "${RED}❌ 找不到 wallet_monitor.py${NC}"
    echo -e "${YELLOW}💡 请确保主程序文件在同一目录下${NC}"
    exit 1
fi
echo -e "${GREEN}✅ 主程序文件存在${NC}"

if [ ! -f "wallet_monitor_launcher.py" ]; then
    echo -e "${RED}❌ 找不到 wallet_monitor_launcher.py${NC}"
    echo -e "${YELLOW}💡 请确保启动器文件在同一目录下${NC}"
    exit 1
fi
echo -e "${GREEN}✅ 启动器文件存在${NC}"

# 设置执行权限
chmod +x wallet_monitor.py
chmod +x wallet_monitor_launcher.py

echo ""
echo -e "${GREEN}🎉 安装完成!${NC}"
echo "========================================="
echo -e "${GREEN}📋 安装摘要:${NC}"
echo -e "${GREEN}  ✅ Python环境: $PYTHON_CMD${NC}"
echo -e "${GREEN}  ✅ 依赖包: 已安装${NC}"
echo -e "${GREEN}  ✅ 主程序: wallet_monitor.py${NC}"
echo -e "${GREEN}  ✅ 启动器: wallet_monitor_launcher.py${NC}"
echo "========================================="

# 询问是否立即启动
echo ""
read -p "$(echo -e "${CYAN}是否立即启动钱包监控系统? (y/N): ${NC}")" start_now
if [[ "$start_now" =~ ^[Yy]$ ]]; then
    echo -e "${GREEN}🚀 启动钱包监控系统...${NC}"
    exec $PYTHON_CMD wallet_monitor_launcher.py
else
    echo -e "${YELLOW}💡 稍后可以运行以下命令启动:${NC}"
    echo -e "${CYAN}  $PYTHON_CMD wallet_monitor_launcher.py${NC}"
    echo -e "${CYAN}  或者${NC}"
    echo -e "${CYAN}  $PYTHON_CMD wallet_monitor.py${NC}"
fi
