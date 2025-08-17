#!/bin/bash

# 钱包监控系统智能安装器 v4.0 - Ubuntu 24.04 兼容版
# 支持虚拟环境和系统包管理器

set -e  # 遇到错误时退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m' # No Color

# 清屏
clear

echo -e "${CYAN}🚀 钱包监控系统智能安装器 v4.0${NC}"
echo -e "${CYAN}自动下载 | 虚拟环境 | 一键启动 | Ubuntu 24.04 兼容${NC}"
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
            echo -e "${YELLOW}⚠️ 检测到 Linux 系统 (未知发行版)${NC}"
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        OS="macos"
        echo -e "${GREEN}✅ 检测到 macOS 系统${NC}"
    else
        OS="unknown"
        echo -e "${RED}❌ 未知操作系统: $OSTYPE${NC}"
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
            echo -e "${RED}❌ Python 版本过低: $PYTHON_VERSION，需要 Python 3.7+${NC}"
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
            echo -e "${CYAN}🔄 更新包列表...${NC}"
            sudo apt update -qq
            
            echo -e "${CYAN}🔄 安装必要的系统包...${NC}"
            sudo apt install -y python3-full python3-venv python3-pip curl wget git
            
            # 确保可以创建虚拟环境
            if ! $PYTHON_CMD -m venv --help &> /dev/null; then
                echo -e "${CYAN}🔄 安装 python3-venv...${NC}"
                sudo apt install -y python3.12-venv || sudo apt install -y python3-venv
            fi
            ;;
        "centos")
            echo -e "${CYAN}🔄 安装 EPEL 仓库...${NC}"
            sudo yum install -y epel-release || sudo dnf install -y epel-release
            
            echo -e "${CYAN}🔄 安装必要的系统包...${NC}"
            sudo yum install -y python3 python3-pip python3-venv curl wget git || \
            sudo dnf install -y python3 python3-pip python3-venv curl wget git
            ;;
        "macos")
            if command -v brew &> /dev/null; then
                echo -e "${CYAN}🔄 使用 Homebrew 安装依赖...${NC}"
                brew install python3 curl wget git
            else
                echo -e "${YELLOW}⚠️ 建议安装 Homebrew 来管理依赖${NC}"
            fi
            ;;
        *)
            echo -e "${YELLOW}⚠️ 未知系统，跳过系统依赖安装${NC}"
            ;;
    esac
}

# 创建项目目录和虚拟环境
setup_environment() {
    echo -e "${BLUE}🏗️ 设置项目环境...${NC}"
    
    # 创建项目目录
    PROJECT_DIR="$HOME/jiankong"
    VENV_DIR="$PROJECT_DIR/venv"
    
    echo -e "${CYAN}📁 创建项目目录: $PROJECT_DIR${NC}"
    mkdir -p "$PROJECT_DIR"
    cd "$PROJECT_DIR"
    
    # 检查是否已有虚拟环境
    if [ -d "$VENV_DIR" ] && [ -f "$VENV_DIR/bin/activate" ]; then
        echo -e "${GREEN}✅ 虚拟环境已存在${NC}"
    else
        echo -e "${CYAN}🔄 创建 Python 虚拟环境...${NC}"
        
        # 删除可能存在的损坏的虚拟环境
        rm -rf "$VENV_DIR"
        
        # 创建新的虚拟环境
        if ! $PYTHON_CMD -m venv "$VENV_DIR"; then
            echo -e "${RED}❌ 虚拟环境创建失败${NC}"
            echo -e "${YELLOW}💡 尝试使用系统包管理器安装...${NC}"
            
            if [[ $OS == "ubuntu" ]]; then
                sudo apt install -y python3-venv python3.12-venv
                $PYTHON_CMD -m venv "$VENV_DIR" || {
                    echo -e "${RED}❌ 仍然无法创建虚拟环境，请检查系统配置${NC}"
                    exit 1
                }
            else
                echo -e "${RED}❌ 请手动安装 python3-venv 包${NC}"
                exit 1
            fi
        fi
        
        echo -e "${GREEN}✅ 虚拟环境创建成功${NC}"
    fi
    
    # 激活虚拟环境
    echo -e "${CYAN}🔄 激活虚拟环境...${NC}"
    source "$VENV_DIR/bin/activate"
    
    # 验证虚拟环境
    if [[ "$VIRTUAL_ENV" ]]; then
        echo -e "${GREEN}✅ 虚拟环境已激活: $VIRTUAL_ENV${NC}"
    else
        echo -e "${RED}❌ 虚拟环境激活失败${NC}"
        exit 1
    fi
    
    # 升级 pip
    echo -e "${CYAN}🔄 升级 pip...${NC}"
    python -m pip install --upgrade pip
}

# 安装 Python 依赖
install_python_dependencies() {
    echo -e "${BLUE}📦 安装 Python 依赖包...${NC}"
    
    # 定义依赖包
    DEPENDENCIES=(
        "web3>=6.0.0"
        "eth-account>=0.8.0"
        "colorama>=0.4.4"
        "aiohttp>=3.8.0"
        "cryptography>=3.4.8"
        "requests>=2.25.1"
    )
    
    # 安装依赖
    for dep in "${DEPENDENCIES[@]}"; do
        echo -e "${CYAN}📦 安装 $dep...${NC}"
        if ! python -m pip install "$dep"; then
            echo -e "${YELLOW}⚠️ $dep 安装失败，尝试使用 --no-cache-dir${NC}"
            python -m pip install --no-cache-dir "$dep" || {
                echo -e "${RED}❌ $dep 安装失败${NC}"
                exit 1
            }
        fi
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
    else
        echo -e "${RED}❌ 程序下载失败${NC}"
        echo -e "${YELLOW}💡 请检查网络连接或手动下载${NC}"
        exit 1
    fi
    
    # 设置执行权限
    chmod +x wallet_monitor.py
    
    # 验证文件
    if [ -f "wallet_monitor.py" ] && [ -s "wallet_monitor.py" ]; then
        FILE_SIZE=$(wc -c < wallet_monitor.py)
        echo -e "${GREEN}✅ 程序文件验证成功 (大小: $FILE_SIZE 字节)${NC}"
    else
        echo -e "${RED}❌ 程序文件验证失败${NC}"
        exit 1
    fi
}

# 创建启动脚本
create_startup_script() {
    echo -e "${BLUE}📝 创建启动脚本...${NC}"
    
    cat > start.sh << 'EOF'
#!/bin/bash

# 钱包监控系统启动脚本
# 自动激活虚拟环境并启动程序

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$PROJECT_DIR/venv"

echo "🚀 启动钱包监控系统..."
echo "📁 项目目录: $PROJECT_DIR"

# 检查虚拟环境
if [ ! -f "$VENV_DIR/bin/activate" ]; then
    echo "❌ 虚拟环境不存在，请重新运行安装脚本"
    exit 1
fi

# 激活虚拟环境
source "$VENV_DIR/bin/activate"

# 检查主程序
if [ ! -f "$PROJECT_DIR/wallet_monitor.py" ]; then
    echo "❌ 主程序文件不存在"
    exit 1
fi

# 启动程序
cd "$PROJECT_DIR"
python wallet_monitor.py "$@"
EOF
    
    chmod +x start.sh
    echo -e "${GREEN}✅ 启动脚本创建成功${NC}"
}

# 创建便捷命令
create_convenience_commands() {
    echo -e "${BLUE}🔗 创建便捷命令...${NC}"
    
    # 创建符号链接到用户 bin 目录
    USER_BIN="$HOME/.local/bin"
    mkdir -p "$USER_BIN"
    
    # 创建全局命令脚本
    cat > "$USER_BIN/jiankong" << EOF
#!/bin/bash
cd "$PROJECT_DIR" && ./start.sh "\$@"
EOF
    
    chmod +x "$USER_BIN/jiankong"
    
    # 添加到 PATH（如果还没有）
    if [[ ":$PATH:" != *":$USER_BIN:"* ]]; then
        echo "export PATH=\"\$HOME/.local/bin:\$PATH\"" >> "$HOME/.bashrc"
        echo -e "${YELLOW}💡 请运行 'source ~/.bashrc' 或重新登录以使用全局命令${NC}"
    fi
    
    echo -e "${GREEN}✅ 便捷命令创建成功${NC}"
    echo -e "${CYAN}💡 您可以在任意目录运行 'jiankong' 命令启动程序${NC}"
}

# 创建桌面快捷方式（仅限有桌面环境的系统）
create_desktop_shortcut() {
    if [ -d "$HOME/Desktop" ] && command -v xdg-user-dir &> /dev/null; then
        echo -e "${BLUE}🖥️ 创建桌面快捷方式...${NC}"
        
        DESKTOP_FILE="$HOME/Desktop/钱包监控系统.desktop"
        cat > "$DESKTOP_FILE" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=钱包监控系统
Comment=智能钱包监控和自动转账系统
Exec=$PROJECT_DIR/start.sh
Icon=utilities-terminal
Terminal=true
Categories=Utility;Development;
StartupNotify=true
EOF
        
        chmod +x "$DESKTOP_FILE"
        echo -e "${GREEN}✅ 桌面快捷方式创建成功${NC}"
    fi
}

# 显示安装完成信息
show_completion_info() {
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
    echo -e "• 🔍 支持 ${#SUPPORTED_NETWORKS[@]} 个 EVM 兼容网络"
    echo -e "• 🪙 ERC20 代币自动检测和转账"
    echo -e "• 📱 Telegram 通知推送"
    echo -e "• ⚡ 智能 Gas 费优化"
    echo -e "• 🔄 API 密钥自动轮询"
    echo -e "• 💾 智能缓存和状态恢复"
    echo ""
    echo -e "${GREEN}🎯 现在就可以启动程序开始使用！${NC}"
}

# 主安装流程
main() {
    echo -e "${BLUE}📋 开始安装...${NC}"
    
    # 检测系统
    detect_os
    
    # 检查 Python
    check_python
    
    # 安装系统依赖
    install_system_dependencies
    
    # 设置环境
    setup_environment
    
    # 安装 Python 依赖
    install_python_dependencies
    
    # 下载主程序
    download_main_program
    
    # 创建启动脚本
    create_startup_script
    
    # 创建便捷命令
    create_convenience_commands
    
    # 创建桌面快捷方式
    create_desktop_shortcut
    
    # 显示完成信息
    show_completion_info
    
    # 询问是否立即启动
    echo ""
    read -p "🚀 是否立即启动钱包监控系统？ (y/N): " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${GREEN}🚀 启动钱包监控系统...${NC}"
        ./start.sh
    else
        echo -e "${CYAN}💡 稍后可以运行 './start.sh' 或 'jiankong' 命令启动程序${NC}"
    fi
}

# 错误处理
handle_error() {
    echo ""
    echo -e "${RED}❌ 安装过程中发生错误${NC}"
    echo -e "${YELLOW}💡 请检查错误信息并重试，或手动安装${NC}"
    echo ""
    echo -e "${CYAN}📞 获取支持:${NC}"
    echo -e "• 检查网络连接"
    echo -e "• 确保有足够的磁盘空间"
    echo -e "• 尝试使用 sudo 权限"
    echo -e "• 查看具体错误信息进行排查"
    exit 1
}

# 设置错误处理
trap 'handle_error' ERR

# 运行主程序
main "$@"
