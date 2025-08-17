#!/bin/bash

# 钱包监控系统快速安装脚本
# 解决文件不存在问题的专用版本

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${BLUE}🚀 钱包监控系统快速安装器${NC}"
echo -e "${BLUE}自动下载并安装所有必需文件${NC}"
echo "=" * 50

# 检查下载工具
if command -v curl &> /dev/null; then
    DOWNLOAD="curl -fsSL"
    echo -e "${GREEN}✅ 使用 curl 下载${NC}"
elif command -v wget &> /dev/null; then
    DOWNLOAD="wget -q -O"
    echo -e "${GREEN}✅ 使用 wget 下载${NC}"
else
    echo -e "${RED}❌ 需要 curl 或 wget${NC}"
    exit 1
fi

# 检查Python
PYTHON_CMD=""
for cmd in python3 python; do
    if command -v $cmd &> /dev/null; then
        VERSION=$($cmd -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null || echo "0.0")
        MAJOR=$(echo $VERSION | cut -d. -f1)
        MINOR=$(echo $VERSION | cut -d. -f2)
        
        if [ "$MAJOR" -eq 3 ] && [ "$MINOR" -ge 8 ]; then
            PYTHON_CMD=$cmd
            echo -e "${GREEN}✅ Python: $cmd (版本 $VERSION)${NC}"
            break
        fi
    fi
done

if [ -z "$PYTHON_CMD" ]; then
    echo -e "${RED}❌ 需要 Python 3.8+${NC}"
    exit 1
fi

# 下载文件
echo -e "\n${CYAN}📥 下载项目文件...${NC}"
BASE_URL="https://raw.githubusercontent.com/haohaoi34/jiankong/main"

if command -v curl &> /dev/null; then
    curl -fsSL "$BASE_URL/wallet_monitor.py" -o wallet_monitor.py
    curl -fsSL "$BASE_URL/wallet_monitor_launcher.py" -o wallet_monitor_launcher.py
else
    wget -q "$BASE_URL/wallet_monitor.py" -O wallet_monitor.py
    wget -q "$BASE_URL/wallet_monitor_launcher.py" -O wallet_monitor_launcher.py
fi

# 检查下载结果
if [ -f "wallet_monitor.py" ] && [ -f "wallet_monitor_launcher.py" ]; then
    echo -e "${GREEN}✅ 文件下载成功${NC}"
else
    echo -e "${RED}❌ 文件下载失败${NC}"
    exit 1
fi

# 安装依赖
echo -e "\n${CYAN}📦 安装依赖...${NC}"
packages=("web3" "eth-account" "alchemy-sdk" "colorama" "aiohttp" "cryptography")

# 尝试不同的安装方法
install_success=false

# 方法1: 标准安装
echo -e "尝试标准安装..."
if $PYTHON_CMD -m pip install "${packages[@]}" --upgrade 2>/dev/null; then
    install_success=true
    echo -e "${GREEN}✅ 标准安装成功${NC}"
fi

# 方法2: 用户安装
if [ "$install_success" = false ]; then
    echo -e "尝试用户安装..."
    if $PYTHON_CMD -m pip install "${packages[@]}" --user --upgrade 2>/dev/null; then
        install_success=true
        echo -e "${GREEN}✅ 用户安装成功${NC}"
    fi
fi

# 方法3: 系统包破坏安装 (macOS)
if [ "$install_success" = false ]; then
    echo -e "尝试系统包安装..."
    if $PYTHON_CMD -m pip install "${packages[@]}" --break-system-packages --upgrade 2>/dev/null; then
        install_success=true
        echo -e "${GREEN}✅ 系统包安装成功${NC}"
    fi
fi

if [ "$install_success" = false ]; then
    echo -e "${RED}❌ 所有安装方法都失败${NC}"
    echo -e "${YELLOW}💡 请手动安装依赖:${NC}"
    echo -e "   $PYTHON_CMD -m pip install web3 eth-account alchemy-sdk colorama aiohttp cryptography --user"
    exit 1
fi

# 创建启动脚本
echo -e "\n${CYAN}📝 创建启动脚本...${NC}"
cat > run_monitor.sh << EOF
#!/bin/bash
echo "🚀 启动钱包监控系统..."
$PYTHON_CMD wallet_monitor.py
EOF

chmod +x run_monitor.sh
echo -e "${GREEN}✅ 启动脚本: run_monitor.sh${NC}"

# 完成
echo -e "\n${GREEN}🎉 安装完成！${NC}"
echo -e "${YELLOW}启动命令: ./run_monitor.sh${NC}"
echo -e "${YELLOW}或直接运行: $PYTHON_CMD wallet_monitor.py${NC}"

# 询问是否立即启动
echo -e "\n${CYAN}是否立即启动? (y/N): ${NC}"
read -r choice
if [[ "$choice" =~ ^[Yy]$ ]]; then
    echo -e "${GREEN}🚀 启动钱包监控系统...${NC}"
    $PYTHON_CMD wallet_monitor.py
fi
