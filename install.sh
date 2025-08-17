#!/bin/bash

# 钱包监控系统智能安装器 v3.0
# 自动下载、安装依赖、智能合并更新

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# 项目信息
GITHUB_REPO="https://raw.githubusercontent.com/haohaoi34/jiankong/main"
MAIN_PROGRAM="wallet_monitor.py"
README_FILE="README.md"

echo -e "${BLUE}🚀 钱包监控系统智能安装器 v3.0${NC}"
echo -e "${BLUE}自动下载 | 智能合并 | 一键启动${NC}"
echo "========================================="

# 检测操作系统
echo -e "${CYAN}📋 检查系统环境...${NC}"
OS_TYPE=$(uname -s)
case "$OS_TYPE" in
    Linux*)  OS="Linux";;
    Darwin*) OS="macOS";;
    CYGWIN*|MINGW*|MSYS*) OS="Windows";;
    *) OS="Unknown";;
esac
echo -e "${GREEN}✅ 操作系统: $OS${NC}"

# 检测Python
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

# 检查并安装pip
echo -e "${CYAN}📦 检查包管理器...${NC}"
if ! $PYTHON_CMD -m pip --version &> /dev/null; then
    echo -e "${YELLOW}🔄 安装pip...${NC}"
    curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
    $PYTHON_CMD get-pip.py
    rm get-pip.py
fi
echo -e "${GREEN}✅ pip可用${NC}"

# 智能下载或更新主程序
echo -e "${CYAN}📥 检查主程序文件...${NC}"
if [ -f "$MAIN_PROGRAM" ]; then
    echo -e "${YELLOW}💡 发现现有主程序，检查是否需要更新...${NC}"
    
    # 下载最新版本到临时文件
    if curl -fsSL "$GITHUB_REPO/$MAIN_PROGRAM" -o "${MAIN_PROGRAM}.new" 2>/dev/null; then
        # 比较文件差异
        if ! diff -q "$MAIN_PROGRAM" "${MAIN_PROGRAM}.new" &> /dev/null; then
            echo -e "${CYAN}🔄 发现新版本，正在智能合并...${NC}"
            
            # 备份当前版本
            cp "$MAIN_PROGRAM" "${MAIN_PROGRAM}.backup"
            
            # 替换为新版本
            mv "${MAIN_PROGRAM}.new" "$MAIN_PROGRAM"
            echo -e "${GREEN}✅ 主程序已更新${NC}"
        else
            echo -e "${GREEN}✅ 主程序已是最新版本${NC}"
            rm "${MAIN_PROGRAM}.new"
        fi
    else
        echo -e "${YELLOW}⚠️ 无法检查更新，使用现有版本${NC}"
    fi
else
    echo -e "${CYAN}📥 下载主程序...${NC}"
    if curl -fsSL "$GITHUB_REPO/$MAIN_PROGRAM" -o "$MAIN_PROGRAM"; then
        echo -e "${GREEN}✅ 主程序下载成功${NC}"
    else
        echo -e "${RED}❌ 主程序下载失败${NC}"
        echo -e "${YELLOW}💡 请检查网络连接或手动下载${NC}"
        exit 1
    fi
fi

# 下载README（如果不存在）
if [ ! -f "$README_FILE" ]; then
    echo -e "${CYAN}📄 下载README文档...${NC}"
    if curl -fsSL "$GITHUB_REPO/$README_FILE" -o "$README_FILE" 2>/dev/null; then
        echo -e "${GREEN}✅ README下载成功${NC}"
    else
        echo -e "${YELLOW}⚠️ README下载失败，将创建简单版本${NC}"
        cat > "$README_FILE" << 'EOF'
# 钱包监控转账系统 v3.0

## 快速启动
```bash
./install.sh
```

## 功能特性
- 🌐 多链支持：支持多个EVM兼容链
- 🔑 智能私钥导入：批量导入，智能识别
- 🎯 自动监控：实时监控钱包余额变化
- 💸 自动转账：发现余额立即转移
- 📊 交互式界面：简洁友好的命令行界面

## 使用方法
1. 运行 `python3 wallet_monitor.py`
2. 选择功能1导入私钥
3. 选择功能2开始监控

## 注意事项
- 需要Python 3.7+
- 需要稳定的网络连接
- 请在测试网络上先行测试
EOF
    fi
fi

# 安装Python依赖
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
    if $PYTHON_CMD -c "import ${package//-/_}" &> /dev/null; then
        echo -e "${GREEN}✅ $package 已安装${NC}"
    else
        echo -e "${CYAN}🔄 安装 $package...${NC}"
        if $PYTHON_CMD -m pip install "$package" &> /dev/null; then
            echo -e "${GREEN}✅ $package 安装成功${NC}"
        else
            if $PYTHON_CMD -m pip install --user "$package" &> /dev/null; then
                echo -e "${GREEN}✅ $package 安装成功 (用户模式)${NC}"
            else
                echo -e "${RED}❌ $package 安装失败${NC}"
            fi
        fi
    fi
done

# 设置执行权限
chmod +x "$MAIN_PROGRAM" 2>/dev/null || true

echo ""
echo -e "${GREEN}🎉 安装完成!${NC}"
echo "========================================="
echo -e "${GREEN}📋 项目文件:${NC}"
echo -e "${GREEN}  ✅ 主程序: $MAIN_PROGRAM${NC}"
echo -e "${GREEN}  ✅ 安装器: install.sh${NC}"
echo -e "${GREEN}  ✅ 文档: $README_FILE${NC}"
echo "========================================="
echo -e "${CYAN}🚀 启动方法:${NC}"
echo -e "${CYAN}  方法1: $PYTHON_CMD $MAIN_PROGRAM${NC}"
echo -e "${CYAN}  方法2: ./$MAIN_PROGRAM${NC}"
echo "========================================="

# 询问是否立即启动
echo ""
read -p "$(echo -e "${CYAN}是否立即启动钱包监控系统? (y/N): ${NC}")" start_now
if [[ "$start_now" =~ ^[Yy]$ ]]; then
    echo -e "${GREEN}🚀 启动钱包监控系统...${NC}"
    exec $PYTHON_CMD "$MAIN_PROGRAM"
else
    echo -e "${YELLOW}💡 稍后运行以下命令启动:${NC}"
    echo -e "${CYAN}  $PYTHON_CMD $MAIN_PROGRAM${NC}"
fi
