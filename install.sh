#!/bin/bash

# 钱包监控系统一键安装器 v4.0 - 简化版
# 自动安装依赖并直接启动程序

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m'

clear

echo -e "${CYAN}🚀 钱包监控系统一键安装器 v4.0${NC}"
echo -e "${CYAN}自动安装 | 虚拟环境 | 直接启动 | 简化版${NC}"
echo -e "${BLUE}=========================================${NC}"

# 检测操作系统
detect_os() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        if command -v apt &> /dev/null; then
            OS="ubuntu"
            echo -e "${GREEN}✅ 检测到 Ubuntu/Debian 系统${NC}"
        elif command -v yum &> /dev/null; then
            OS="centos"
            echo -e "${GREEN}✅ 检测到 CentOS/RHEL 系统${NC}"
        else
            OS="linux"
            echo -e "${YELLOW}⚠️ 检测到 Linux 系统${NC}"
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        OS="macos"
        echo -e "${GREEN}✅ 检测到 macOS 系统${NC}"
    else
        OS="unknown"
        echo -e "${YELLOW}⚠️ 未知操作系统${NC}"
    fi
}

# 检查 Python
check_python() {
    echo -e "${BLUE}📋 检查 Python 环境...${NC}"
    
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2)
        echo -e "${GREEN}✅ Python3: $PYTHON_VERSION${NC}"
        PYTHON_CMD="python3"
    elif command -v python &> /dev/null; then
        PYTHON_VERSION=$(python --version 2>&1 | cut -d' ' -f2)
        if [[ $PYTHON_VERSION == 3.* ]]; then
            echo -e "${GREEN}✅ Python: $PYTHON_VERSION${NC}"
            PYTHON_CMD="python"
        else
            echo -e "${RED}❌ Python 版本过低，需要 Python 3.7+${NC}"
            exit 1
        fi
    else
        echo -e "${RED}❌ 未找到 Python，请先安装 Python 3.7+${NC}"
        exit 1
    fi
}

# 安装系统依赖
install_system_dependencies() {
    echo -e "${BLUE}📦 安装系统依赖...${NC}"
    
    case $OS in
        "ubuntu")
            sudo apt update -qq
            sudo apt install -y python3-full python3-venv python3-pip curl wget git
            ;;
        "centos")
            sudo yum install -y epel-release || sudo dnf install -y epel-release
            sudo yum install -y python3 python3-pip python3-venv curl wget git || \
            sudo dnf install -y python3 python3-pip python3-venv curl wget git
            ;;
        "macos")
            if command -v brew &> /dev/null; then
                brew install python3 curl wget git
            fi
            ;;
    esac
}

# 设置项目环境
setup_environment() {
    echo -e "${BLUE}🏗️ 设置项目环境...${NC}"
    
    PROJECT_DIR="$HOME/jiankong"
    VENV_DIR="$PROJECT_DIR/venv"
    
    echo -e "${CYAN}📁 创建项目目录: $PROJECT_DIR${NC}"
    mkdir -p "$PROJECT_DIR"
    cd "$PROJECT_DIR"
    
    # 创建虚拟环境
    if [ ! -d "$VENV_DIR" ] || [ ! -f "$VENV_DIR/bin/activate" ]; then
        echo -e "${CYAN}🔄 创建 Python 虚拟环境...${NC}"
        rm -rf "$VENV_DIR"
        
        if ! $PYTHON_CMD -m venv "$VENV_DIR"; then
            if [[ $OS == "ubuntu" ]]; then
                sudo apt install -y python3-venv python3.12-venv
                $PYTHON_CMD -m venv "$VENV_DIR"
            else
                echo -e "${RED}❌ 虚拟环境创建失败${NC}"
                exit 1
            fi
        fi
        echo -e "${GREEN}✅ 虚拟环境创建成功${NC}"
    else
        echo -e "${GREEN}✅ 虚拟环境已存在${NC}"
    fi
    
    # 激活虚拟环境
    source "$VENV_DIR/bin/activate"
    python -m pip install --upgrade pip
}

# 安装 Python 依赖
install_python_dependencies() {
    echo -e "${BLUE}📦 安装 Python 依赖包...${NC}"
    
    DEPENDENCIES=(
        "web3>=6.0.0"
        "eth-account>=0.8.0"
        "colorama>=0.4.4"
        "aiohttp>=3.8.0"
        "cryptography>=3.4.8"
        "requests>=2.25.1"
    )
    
    for dep in "${DEPENDENCIES[@]}"; do
        echo -e "${CYAN}📦 安装 $dep...${NC}"
        python -m pip install "$dep" --no-cache-dir
    done
    
    echo -e "${GREEN}✅ 所有依赖包安装完成${NC}"
}

# 下载主程序
download_main_program() {
    echo -e "${BLUE}📥 下载钱包监控程序...${NC}"
    
    GITHUB_URL="https://raw.githubusercontent.com/haohaoi34/jiankong/main/wallet_monitor.py"
    
    echo -e "${CYAN}🔄 从 GitHub 下载最新版本...${NC}"
    if curl -fsSL "$GITHUB_URL" -o wallet_monitor.py; then
        echo -e "${GREEN}✅ 程序下载成功${NC}"
        chmod +x wallet_monitor.py
        
        if [ -f "wallet_monitor.py" ] && [ -s "wallet_monitor.py" ]; then
            FILE_SIZE=$(wc -c < wallet_monitor.py)
            echo -e "${GREEN}✅ 程序文件验证成功 (大小: $FILE_SIZE 字节)${NC}"
        else
            echo -e "${RED}❌ 程序文件验证失败${NC}"
            exit 1
        fi
    else
        echo -e "${RED}❌ 程序下载失败，请检查网络连接${NC}"
        exit 1
    fi
}

# 创建启动脚本
create_startup_script() {
    echo -e "${BLUE}📝 创建启动脚本...${NC}"
    
    cat > start.sh << 'EOF'
#!/bin/bash

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$PROJECT_DIR/venv"

echo "🚀 启动钱包监控系统..."
echo "📁 项目目录: $PROJECT_DIR"

if [ ! -f "$VENV_DIR/bin/activate" ]; then
    echo "❌ 虚拟环境不存在，请重新运行安装脚本"
    exit 1
fi

source "$VENV_DIR/bin/activate"

if [ ! -f "$PROJECT_DIR/wallet_monitor.py" ]; then
    echo "❌ 主程序文件不存在"
    exit 1
fi

cd "$PROJECT_DIR"
exec python wallet_monitor.py "$@"
EOF
    
    chmod +x start.sh
    
    # 创建全局命令
    USER_BIN="$HOME/.local/bin"
    mkdir -p "$USER_BIN"
    
    cat > "$USER_BIN/jiankong" << EOF
#!/bin/bash
cd "$PROJECT_DIR" && ./start.sh "\$@"
EOF
    
    chmod +x "$USER_BIN/jiankong"
    
    if [[ ":$PATH:" != *":$USER_BIN:"* ]]; then
        echo "export PATH=\"\$HOME/.local/bin:\$PATH\"" >> "$HOME/.bashrc"
    fi
    
    echo -e "${GREEN}✅ 启动脚本和全局命令创建成功${NC}"
}

# 显示完成信息并自动启动
show_completion_and_start() {
    echo ""
    echo -e "${GREEN}🎉 钱包监控系统安装完成！${NC}"
    echo -e "${BLUE}=========================================${NC}"
    echo ""
    echo -e "${CYAN}📁 安装目录: $PROJECT_DIR${NC}"
    echo -e "${CYAN}🐍 虚拟环境: $VENV_DIR${NC}"
    echo -e "${CYAN}🚀 主程序: $PROJECT_DIR/wallet_monitor.py${NC}"
    echo ""
    echo -e "${YELLOW}🚀 启动方式:${NC}"
    echo -e "${WHITE}1. 直接启动:${NC}"
    echo -e "   cd $PROJECT_DIR && ./start.sh"
    echo ""
    echo -e "${WHITE}2. 全局命令 (推荐):${NC}"
    echo -e "   jiankong"
    echo ""
    echo -e "${WHITE}3. 手动启动:${NC}"
    echo -e "   cd $PROJECT_DIR"
    echo -e "   source venv/bin/activate"
    echo -e "   python wallet_monitor.py"
    echo ""
    echo -e "${YELLOW}💡 功能特性:${NC}"
    echo -e "• 🔍 支持 46+ 个 EVM 兼容网络"
    echo -e "• 🪙 自动检测和转账"
    echo -e "• ⚡ 智能 Gas 费优化"
    echo -e "• 🔄 API 密钥自动轮询"
    echo -e "• 💾 智能缓存和状态恢复"
    echo ""
    echo -e "${GREEN}🎯 程序即将自动启动，进入主菜单...${NC}"
    echo ""
    
    # 自动启动程序
    sleep 3
    echo -e "${GREEN}🚀 启动钱包监控系统...${NC}"
    ./start.sh
}

# 错误处理
handle_error() {
    echo ""
    echo -e "${RED}❌ 安装过程中发生错误${NC}"
    echo -e "${YELLOW}💡 请检查错误信息并重试${NC}"
    exit 1
}

# 主安装流程
main() {
    echo -e "${BLUE}📋 开始安装...${NC}"
    
    detect_os
    check_python
    install_system_dependencies
    setup_environment
    install_python_dependencies
    download_main_program
    create_startup_script
    show_completion_and_start
}

# 设置错误处理
trap 'handle_error' ERR

# 运行主程序
main "$@"
