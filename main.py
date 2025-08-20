#!/usr/bin/env python
import asyncio
import json
import logging
import os
import re
import sqlite3
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from decimal import Decimal
import aiosqlite
import requests
from web3 import Web3
import urllib.parse
import threading
import sys
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
TARGET_ADDRESS = os.getenv("TARGET_ADDRESS", "0x6b219df8c31c6b39a1a9b88446e0199be8f63cf1")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
COINGECKO_API_KEY = os.getenv("COINGECKO_API_KEY")

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
            "rpc_url": "https://eth-mainnet.g.alchemy.com/v2/PLACEHOLDER_API_KEY",
            "native_token": "ETH",
            "explorer": "https://etherscan.io"
        },
        "POLYGON_MAINNET": {
            "chain_id": 137,
            "name": "Polygon PoS",
            "rpc_url": "https://polygon-mainnet.g.alchemy.com/v2/PLACEHOLDER_API_KEY",
            "native_token": "MATIC",
            "explorer": "https://polygonscan.com"
        },
        "ARBITRUM_ONE": {
            "chain_id": 42161,
            "name": "Arbitrum One",
            "rpc_url": "https://arb-mainnet.g.alchemy.com/v2/PLACEHOLDER_API_KEY",
            "native_token": "ETH",
            "explorer": "https://arbiscan.io"
        },
        "OPTIMISM_MAINNET": {
            "chain_id": 10,
            "name": "OP Mainnet",
            "rpc_url": "https://opt-mainnet.g.alchemy.com/v2/PLACEHOLDER_API_KEY",
            "native_token": "ETH",
            "explorer": "https://optimistic.etherscan.io"
        },
        "BASE_MAINNET": {
            "chain_id": 8453,
            "name": "Base",
            "rpc_url": "https://base-mainnet.g.alchemy.com/v2/PLACEHOLDER_API_KEY",
            "native_token": "ETH",
            "explorer": "https://basescan.org"
        },
        "ARBITRUM_NOVA": {
            "chain_id": 42170,
            "name": "Arbitrum Nova",
            "rpc_url": "https://arbnova-mainnet.g.alchemy.com/v2/PLACEHOLDER_API_KEY",
            "native_token": "ETH",
            "explorer": "https://nova.arbiscan.io"
        },
        "ZKSYNC_ERA": {
            "chain_id": 324,
            "name": "ZKsync Era",
            "rpc_url": "https://zksync-mainnet.g.alchemy.com/v2/PLACEHOLDER_API_KEY",
            "native_token": "ETH",
            "explorer": "https://explorer.zksync.io"
        },
        "POLYGON_ZKEVM": {
            "chain_id": 1101,
            "name": "Polygon zkEVM",
            "rpc_url": "https://polygonzkevm-mainnet.g.alchemy.com/v2/PLACEHOLDER_API_KEY",
            "native_token": "ETH",
            "explorer": "https://zkevm.polygonscan.com"
        },
        "AVALANCHE_C": {
            "chain_id": 43114,
            "name": "Avalanche C-Chain",
            "rpc_url": "https://avax-mainnet.g.alchemy.com/v2/PLACEHOLDER_API_KEY",
            "native_token": "AVAX",
            "explorer": "https://snowtrace.io"
        },
        "BSC_MAINNET": {
            "chain_id": 56,
            "name": "BNB Smart Chain",
            "rpc_url": "https://bnb-mainnet.g.alchemy.com/v2/PLACEHOLDER_API_KEY",
            "native_token": "BNB",
            "explorer": "https://bscscan.com"
        },
        "FANTOM_OPERA": {
            "chain_id": 250,
            "name": "Fantom Opera",
            "rpc_url": "https://fantom-mainnet.g.alchemy.com/v2/PLACEHOLDER_API_KEY",
            "native_token": "FTM",
            "explorer": "https://ftmscan.com"
        },
        "BLAST": {
            "chain_id": 81457,
            "name": "Blast",
            "rpc_url": "https://blast-mainnet.g.alchemy.com/v2/PLACEHOLDER_API_KEY",
            "native_token": "ETH",
            "explorer": "https://blastscan.io"
        },
        "LINEA": {
            "chain_id": 59144,
            "name": "Linea",
            "rpc_url": "https://linea-mainnet.g.alchemy.com/v2/PLACEHOLDER_API_KEY",
            "native_token": "ETH",
            "explorer": "https://lineascan.build"
        },
        "MANTLE": {
            "chain_id": 5000,
            "name": "Mantle",
            "rpc_url": "https://mantle-mainnet.g.alchemy.com/v2/PLACEHOLDER_API_KEY",
            "native_token": "MNT",
            "explorer": "https://mantlescan.org"
        },
        "GNOSIS": {
            "chain_id": 100,
            "name": "Gnosis",
            "rpc_url": "https://gnosis-mainnet.g.alchemy.com/v2/PLACEHOLDER_API_KEY",
            "native_token": "xDAI",
            "explorer": "https://gnosisscan.io"
        },
        "CELO": {
            "chain_id": 42220,
            "name": "Celo",
            "rpc_url": "https://celo-mainnet.g.alchemy.com/v2/PLACEHOLDER_API_KEY",
            "native_token": "CELO",
            "explorer": "https://celoscan.io"
        },
        "SCROLL": {
            "chain_id": 534352,
            "name": "Scroll",
            "rpc_url": "https://scroll-mainnet.g.alchemy.com/v2/PLACEHOLDER_API_KEY",
            "native_token": "ETH",
            "explorer": "https://scrollscan.com"
        },
        
        # 新增链
        "WORLD_CHAIN": {
            "chain_id": 480,
            "name": "World Chain",
            "rpc_url": "https://worldchain-mainnet.g.alchemy.com/v2/PLACEHOLDER_API_KEY",
            "native_token": "ETH",
            "explorer": "https://worldscan.org"
        },
        "SHAPE": {
            "chain_id": 360,
            "name": "Shape",
            "rpc_url": "https://shape-mainnet.g.alchemy.com/v2/PLACEHOLDER_API_KEY",
            "native_token": "ETH",
            "explorer": "https://shapescan.xyz"
        },
        "BERACHAIN": {
            "chain_id": 80084,
            "name": "Berachain",
            "rpc_url": "https://berachain-mainnet.g.alchemy.com/v2/PLACEHOLDER_API_KEY",
            "native_token": "BERA",
            "explorer": "https://beratrail.io"
        },
        "UNICHAIN": {
            "chain_id": 1301,
            "name": "Unichain",
            "rpc_url": "https://unichain-mainnet.g.alchemy.com/v2/PLACEHOLDER_API_KEY",
            "native_token": "ETH",
            "explorer": "https://uniscan.xyz"
        },
        "ZORA": {
            "chain_id": 7777777,
            "name": "Zora",
            "rpc_url": "https://zora-mainnet.g.alchemy.com/v2/PLACEHOLDER_API_KEY",
            "native_token": "ETH",
            "explorer": "https://explorer.zora.energy"
        },
        "ASTAR": {
            "chain_id": 592,
            "name": "Astar",
            "rpc_url": "https://astar-mainnet.g.alchemy.com/v2/PLACEHOLDER_API_KEY",
            "native_token": "ASTR",
            "explorer": "https://astar.subscan.io"
        },
        "ZETACHAIN": {
            "chain_id": 7000,
            "name": "ZetaChain",
            "rpc_url": "https://zetachain-mainnet.g.alchemy.com/v2/PLACEHOLDER_API_KEY",
            "native_token": "ZETA",
            "explorer": "https://zetachain.blockscout.com"
        },
        "RONIN": {
            "chain_id": 2020,
            "name": "Ronin",
            "rpc_url": "https://ronin-mainnet.g.alchemy.com/v2/PLACEHOLDER_API_KEY",
            "native_token": "RON",
            "explorer": "https://app.roninchain.com"
        },
        "SETTLUS": {
            "chain_id": 5372,
            "name": "Settlus",
            "rpc_url": "https://settlus-mainnet.g.alchemy.com/v2/PLACEHOLDER_API_KEY",
            "native_token": "SETL",
            "explorer": "https://explorer.settlus.org"
        },
        "ROOTSTOCK": {
            "chain_id": 30,
            "name": "Rootstock",
            "rpc_url": "https://rootstock-mainnet.g.alchemy.com/v2/PLACEHOLDER_API_KEY",
            "native_token": "RBTC",
            "explorer": "https://explorer.rsk.co"
        },
        "STORY": {
            "chain_id": 1513,
            "name": "Story",
            "rpc_url": "https://story-mainnet.g.alchemy.com/v2/PLACEHOLDER_API_KEY",
            "native_token": "IP",
            "explorer": "https://testnet.storyscan.xyz"
        },
        "HUMANITY": {
            "chain_id": 1890,
            "name": "Humanity",
            "rpc_url": "https://humanity-mainnet.g.alchemy.com/v2/PLACEHOLDER_API_KEY",
            "native_token": "ETH",
            "explorer": "https://explorer.humanity.org"
        },
        "HYPERLIQUID": {
            "chain_id": 998,
            "name": "Hyperliquid",
            "rpc_url": "https://hyperliquid-mainnet.g.alchemy.com/v2/PLACEHOLDER_API_KEY",
            "native_token": "ETH",
            "explorer": "https://app.hyperliquid.xyz"
        },
        "GALACTICA": {
            "chain_id": 9302,
            "name": "Galactica",
            "rpc_url": "https://galactica-mainnet.g.alchemy.com/v2/PLACEHOLDER_API_KEY",
            "native_token": "GNET",
            "explorer": "https://explorer.galactica.com"
        },
        "LENS": {
            "chain_id": 37111,
            "name": "Lens",
            "rpc_url": "https://lens-mainnet.g.alchemy.com/v2/PLACEHOLDER_API_KEY",
            "native_token": "GRASS",
            "explorer": "https://block-explorer.lens.dev"
        },
        "FRAX": {
            "chain_id": 252,
            "name": "Frax",
            "rpc_url": "https://frax-mainnet.g.alchemy.com/v2/PLACEHOLDER_API_KEY",
            "native_token": "frxETH",
            "explorer": "https://fraxscan.com"
        },
        "INK": {
            "chain_id": 57073,
            "name": "Ink",
            "rpc_url": "https://ink-mainnet.g.alchemy.com/v2/PLACEHOLDER_API_KEY",
            "native_token": "ETH",
            "explorer": "https://explorer.inkonchain.com"
        },
        "BOTANIX": {
            "chain_id": 3636,
            "name": "Botanix",
            "rpc_url": "https://botanix-mainnet.g.alchemy.com/v2/PLACEHOLDER_API_KEY",
            "native_token": "BTC",
            "explorer": "https://blockscout.botanixlabs.dev"
        },
        "BOBA": {
            "chain_id": 288,
            "name": "Boba",
            "rpc_url": "https://boba-mainnet.g.alchemy.com/v2/PLACEHOLDER_API_KEY",
            "native_token": "ETH",
            "explorer": "https://bobascan.com"
        },
        "SUPERSEED": {
            "chain_id": 5330,
            "name": "Superseed",
            "rpc_url": "https://superseed-mainnet.g.alchemy.com/v2/PLACEHOLDER_API_KEY",
            "native_token": "ETH",
            "explorer": "https://explorer.superseed.xyz"
        },
        "FLOW_EVM": {
            "chain_id": 747,
            "name": "Flow EVM",
            "rpc_url": "https://flow-mainnet.g.alchemy.com/v2/PLACEHOLDER_API_KEY",
            "native_token": "FLOW",
            "explorer": "https://evm.flowscan.io"
        },
        "DEGEN": {
            "chain_id": 666666666,
            "name": "Degen",
            "rpc_url": "https://degen-mainnet.g.alchemy.com/v2/PLACEHOLDER_API_KEY",
            "native_token": "DEGEN",
            "explorer": "https://explorer.degen.tips"
        },
        "APECHAIN": {
            "chain_id": 33139,
            "name": "ApeChain",
            "rpc_url": "https://apechain-mainnet.g.alchemy.com/v2/PLACEHOLDER_API_KEY",
            "native_token": "APE",
            "explorer": "https://apechain.calderaexplorer.xyz"
        },
        "ANIME": {
            "chain_id": 11501,
            "name": "Anime",
            "rpc_url": "https://anime-mainnet.g.alchemy.com/v2/PLACEHOLDER_API_KEY",
            "native_token": "ANIME",
            "explorer": "https://animechain.ai"
        },
        "METIS": {
            "chain_id": 1088,
            "name": "Metis",
            "rpc_url": "https://metis-mainnet.g.alchemy.com/v2/PLACEHOLDER_API_KEY",
            "native_token": "METIS",
            "explorer": "https://explorer.metis.io"
        },
        "SONIC": {
            "chain_id": 146,
            "name": "Sonic",
            "rpc_url": "https://sonic-mainnet.g.alchemy.com/v2/PLACEHOLDER_API_KEY",
            "native_token": "S",
            "explorer": "https://explorer.soniclabs.com"
        },
        "SEI": {
            "chain_id": 1329,
            "name": "Sei",
            "rpc_url": "https://sei-mainnet.g.alchemy.com/v2/PLACEHOLDER_API_KEY",
            "native_token": "SEI",
            "explorer": "https://seitrace.com"
        },
        "OPBNB": {
            "chain_id": 204,
            "name": "opBNB",
            "rpc_url": "https://opbnb-mainnet-rpc.bnbchain.org",
            "native_token": "BNB",
            "explorer": "https://opbnbscan.com"
        },
        "ABSTRACT": {
            "chain_id": 11124,
            "name": "Abstract",
            "rpc_url": "https://abstract-mainnet.g.alchemy.com/v2/PLACEHOLDER_API_KEY",
            "native_token": "ETH",
            "explorer": "https://explorer.abstract.money"
        },
        "SONEIUM": {
            "chain_id": 1946,
            "name": "Soneium",
            "rpc_url": "https://soneium-mainnet.g.alchemy.com/v2/PLACEHOLDER_API_KEY",
            "native_token": "ETH",
            "explorer": "https://explorer.soneium.org"
        },
        
        # 测试网
        "ETH_SEPOLIA": {
            "chain_id": 11155111,
            "name": "Ethereum Sepolia",
            "rpc_url": "https://eth-sepolia.g.alchemy.com/v2/PLACEHOLDER_API_KEY",
            "native_token": "ETH",
            "explorer": "https://sepolia.etherscan.io"
        },
        "POLYGON_AMOY": {
            "chain_id": 80002,
            "name": "Polygon Amoy",
            "rpc_url": "https://polygon-amoy.g.alchemy.com/v2/PLACEHOLDER_API_KEY",
            "native_token": "MATIC",
            "explorer": "https://amoy.polygonscan.com"
        },
        "ARBITRUM_SEPOLIA": {
            "chain_id": 421614,
            "name": "Arbitrum Sepolia",
            "rpc_url": "https://arb-sepolia.g.alchemy.com/v2/PLACEHOLDER_API_KEY",
            "native_token": "ETH",
            "explorer": "https://sepolia.arbiscan.io"
        },
        "OPTIMISM_SEPOLIA": {
            "chain_id": 11155420,
            "name": "Optimism Sepolia",
            "rpc_url": "https://opt-sepolia.g.alchemy.com/v2/PLACEHOLDER_API_KEY",
            "native_token": "ETH",
            "explorer": "https://sepolia-optimism.etherscan.io"
        },
        "BASE_SEPOLIA": {
            "chain_id": 84532,
            "name": "Base Sepolia",
            "rpc_url": "https://base-sepolia.g.alchemy.com/v2/PLACEHOLDER_API_KEY",
            "native_token": "ETH",
            "explorer": "https://sepolia.basescan.org"
        },
        "TEA_SEPOLIA": {
            "chain_id": 10218,
            "name": "Tea Sepolia",
            "rpc_url": "https://tea-sepolia.g.alchemy.com/v2/PLACEHOLDER_API_KEY",
            "native_token": "TEA",
            "explorer": "https://testnet.teascan.org"
        },
        "GENSYN_TESTNET": {
            "chain_id": 42069,
            "name": "Gensyn Testnet",
            "rpc_url": "https://gensyn-testnet.g.alchemy.com/v2/PLACEHOLDER_API_KEY",
            "native_token": "GEN",
            "explorer": "https://explorer.gensyn.ai"
        },
        "RISE_TESTNET": {
            "chain_id": 1821,
            "name": "Rise Testnet",
            "rpc_url": "https://rise-testnet.g.alchemy.com/v2/PLACEHOLDER_API_KEY",
            "native_token": "ETH",
            "explorer": "https://testnet.risescan.co"
        },
        "MONAD_TESTNET": {
            "chain_id": 41454,
            "name": "Monad Testnet",
            "rpc_url": "https://monad-testnet.g.alchemy.com/v2/PLACEHOLDER_API_KEY",
            "native_token": "MON",
            "explorer": "https://testnet.monad.xyz"
        },
        "XMTP_SEPOLIA": {
            "chain_id": 2692,
            "name": "XMTP Sepolia",
            "rpc_url": "https://xmtp-testnet.g.alchemy.com/v2/PLACEHOLDER_API_KEY",
            "native_token": "ETH",
            "explorer": "https://explorer.testnet.xmtp.network"
        },
        "CROSSFI_TESTNET": {
            "chain_id": 4157,
            "name": "CrossFi Testnet",
            "rpc_url": "https://crossfi-testnet.g.alchemy.com/v2/PLACEHOLDER_API_KEY",
            "native_token": "XFI",
            "explorer": "https://test.xfiscan.com"
        },
        "LUMIA_PRISM": {
            "chain_id": 1952959480,
            "name": "Lumia Prism",
            "rpc_url": "https://lumia-prism.g.alchemy.com/v2/PLACEHOLDER_API_KEY",
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
            try:
                async with aiosqlite.connect(self.db_path) as db:
                    cursor = await db.execute(
                        "SELECT 1 FROM blocked_chains WHERE address = ? AND chain_id = ?",
                        (address, chain_id)
                    )
                    result = await cursor.fetchone()
                    return result is not None
            except Exception as e:
                logging.error(f"检查屏蔽链状态失败: {e}")
                return False  # 安全默认值：假设未屏蔽
    
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

class PriceChecker:
    """代币价格查询类 - 优化版本支持长期缓存和API限制"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        # 长期缓存设置 - 分层缓存策略
        self.price_cache = {}  # 内存缓存
        self.cache_duration = 24 * 3600  # 正常缓存1天（86400秒）
        self.extended_cache_duration = 7 * 24 * 3600  # API受限时使用7天缓存
        self.cache_file = "price_cache.json"  # 持久化缓存文件
        
        # API限制管理
        self.api_calls_per_minute = 30  # 每分钟最多30次
        self.api_calls_per_month = 10000  # 每月最多10000次
        self.minute_calls = []  # 记录每分钟的调用
        self.monthly_calls = 0  # 当月总调用次数
        self.month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # 常见代币的CoinGecko ID映射 - 扩展版
        self.token_id_map = {
            # 主要代币
            "USDT": "tether",
            "USDC": "usd-coin", 
            "DAI": "dai",
            "WETH": "weth",
            "ETH": "ethereum",
            "WBTC": "wrapped-bitcoin",
            "BTC": "bitcoin",
            "UNI": "uniswap",
            "LINK": "chainlink",
            "AAVE": "aave",
            "COMP": "compound-governance-token",
            "MKR": "maker",
            "SNX": "havven",
            "YFI": "yearn-finance",
            "SUSHI": "sushi",
            "1INCH": "1inch",
            "CRV": "curve-dao-token",
            "BAL": "balancer",
            "MATIC": "matic-network",
            "AVAX": "avalanche-2",
            "FTM": "fantom",
            "BNB": "binancecoin",
            "ADA": "cardano",
            "SOL": "solana",
            "DOT": "polkadot",
            "ATOM": "cosmos",
            "NEAR": "near",
            "ALGO": "algorand",
            "XTZ": "tezos",
            "EGLD": "elrond-erd-2",
            "LUNA": "terra-luna-2",
        }
        
        # 加载持久化缓存
        self._load_cache()
        self._load_api_stats()
    
    def _load_cache(self):
        """加载持久化缓存"""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r') as f:
                    cache_data = json.load(f)
                    self.price_cache = cache_data.get('prices', {})
                    print_info(f"📦 加载价格缓存: {len(self.price_cache)} 条记录")
        except Exception as e:
            logging.debug(f"加载价格缓存失败: {e}")
            self.price_cache = {}
    
    def _save_cache(self):
        """保存持久化缓存"""
        try:
            cache_data = {
                'prices': self.price_cache,
                'last_updated': time.time()
            }
            with open(self.cache_file, 'w') as f:
                json.dump(cache_data, f)
        except Exception as e:
            logging.debug(f"保存价格缓存失败: {e}")
    
    def _load_api_stats(self):
        """加载API调用统计"""
        try:
            stats_file = "api_stats.json"
            if os.path.exists(stats_file):
                with open(stats_file, 'r') as f:
                    stats = json.load(f)
                    self.monthly_calls = stats.get('monthly_calls', 0)
                    saved_month = stats.get('month_start')
                    if saved_month:
                        saved_month_dt = datetime.fromisoformat(saved_month)
                        current_month = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                        if saved_month_dt.month != current_month.month or saved_month_dt.year != current_month.year:
                            # 新月份，重置计数
                            self.monthly_calls = 0
                            self.month_start = current_month
                        else:
                            self.month_start = saved_month_dt
                    print_info(f"📊 本月API调用: {self.monthly_calls}/10,000")
        except Exception as e:
            logging.debug(f"加载API统计失败: {e}")
    
    def _save_api_stats(self):
        """保存API调用统计"""
        try:
            stats = {
                'monthly_calls': self.monthly_calls,
                'month_start': self.month_start.isoformat()
            }
            with open("api_stats.json", 'w') as f:
                json.dump(stats, f)
        except Exception as e:
            logging.debug(f"保存API统计失败: {e}")
    
    def _can_make_api_call(self) -> bool:
        """检查是否可以进行API调用"""
        current_time = time.time()
        
        # 清理1分钟前的调用记录
        self.minute_calls = [call_time for call_time in self.minute_calls if current_time - call_time <= 60]
        
        # 检查分钟限制
        if len(self.minute_calls) >= self.api_calls_per_minute:
            print_warning(f"⚠️ API分钟限制: {len(self.minute_calls)}/30，暂停调用")
            return False
        
        # 检查月度限制
        if self.monthly_calls >= self.api_calls_per_month:
            print_error(f"❌ API月度额度已用完: {self.monthly_calls}/10,000")
            return False
        
        return True
    
    def _record_api_call(self):
        """记录API调用"""
        current_time = time.time()
        self.minute_calls.append(current_time)
        self.monthly_calls += 1
        self._save_api_stats()
        
        print_info(f"🔌 API调用: 分钟 {len(self.minute_calls)}/30, 月度 {self.monthly_calls}/10,000")
    
    async def get_token_price_usd(self, token_symbol: str, contract_address: str = None) -> Optional[float]:
        """获取代币的USD价格 - 优化版本"""
        try:
            # 生成缓存键
            cache_key = f"{token_symbol.upper()}_{contract_address if contract_address else 'None'}"
            current_time = time.time()
            
            # 检查分层缓存
            if cache_key in self.price_cache:
                cached_data = self.price_cache[cache_key]
                if isinstance(cached_data, dict):
                    cached_price = cached_data.get('price')
                    cached_time = cached_data.get('time', 0)
                else:
                    # 兼容旧格式
                    cached_price, cached_time = cached_data if isinstance(cached_data, tuple) else (cached_data, 0)
                
                cache_age = current_time - cached_time
                # 正常情况下使用1天缓存，API受限时使用7天缓存
                active_cache_duration = self.extended_cache_duration if not self._can_make_api_call() else self.cache_duration
                
                if cache_age < active_cache_duration:
                    cache_status = "扩展" if cache_age > self.cache_duration else "正常"
                    print_info(f"💰 使用{cache_status}缓存价格: {token_symbol} = ${cached_price:.6f} (缓存剩余: {(active_cache_duration - cache_age)/3600:.1f}小时)")
                    return cached_price
            
            # 检查API调用限制
            if not self._can_make_api_call():
                print_warning(f"⚠️ API额度不足，返回缓存价格或默认值")
                # 返回过期缓存或None
                if cache_key in self.price_cache:
                    cached_data = self.price_cache[cache_key]
                    if isinstance(cached_data, dict):
                        return cached_data.get('price')
                    else:
                        return cached_data[0] if isinstance(cached_data, tuple) else cached_data
                return None
            
            # 尝试通过符号查询
            token_id = self.token_id_map.get(token_symbol.upper())
            price = None
            
            if token_id:
                price = await self._query_coingecko_by_id(token_id)
            
            # 如果符号查询失败且有合约地址，尝试通过合约地址查询
            if price is None and contract_address:
                price = await self._query_coingecko_by_contract(contract_address)
            
            # 如果都失败，尝试搜索（最后手段）
            if price is None:
                price = await self._search_coingecko_by_symbol(token_symbol)
            
            # 缓存结果
            if price is not None:
                self.price_cache[cache_key] = {
                    'price': price,
                    'time': current_time,
                    'symbol': token_symbol.upper(),
                    'contract': contract_address
                }
                self._save_cache()
                print_success(f"💰 获取新价格: {token_symbol} = ${price:.6f}")
                return price
            else:
                print_warning(f"⚠️ 无法获取价格: {token_symbol}")
                return None
            
        except Exception as e:
            logging.debug(f"获取代币价格失败 {token_symbol}: {e}")
            return None
    
    async def _query_coingecko_by_id(self, token_id: str) -> Optional[float]:
        """通过CoinGecko ID查询价格"""
        try:
            self._record_api_call()  # 记录API调用
            
            # 使用免费公共API URL
            url = f"https://api.coingecko.com/api/v3/simple/price?ids={token_id}&vs_currencies=usd"
            
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if token_id in data and 'usd' in data[token_id]:
                price = float(data[token_id]['usd'])
                print_success(f"🔍 API查询成功: {token_id} = ${price:.6f}")
                return price
            
            return None
            
        except Exception as e:
            logging.debug(f"CoinGecko ID查询失败 {token_id}: {e}")
            print_error(f"API查询失败: {token_id} - {e}")
            return None
    
    async def _query_coingecko_by_contract(self, contract_address: str) -> Optional[float]:
        """通过合约地址查询价格"""
        try:
            self._record_api_call()  # 记录API调用
            
            # 使用免费公共API URL，尝试以太坊主网
            url = f"https://api.coingecko.com/api/v3/simple/token_price/ethereum?contract_addresses={contract_address}&vs_currencies=usd"
            
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            contract_lower = contract_address.lower()
            if contract_lower in data and 'usd' in data[contract_lower]:
                price = float(data[contract_lower]['usd'])
                print_success(f"🔍 合约查询成功: {contract_address[:8]}... = ${price:.6f}")
                return price
            
            return None
            
        except Exception as e:
            logging.debug(f"CoinGecko合约查询失败 {contract_address}: {e}")
            print_error(f"合约查询失败: {contract_address[:8]}... - {e}")
            return None
    
    async def _search_coingecko_by_symbol(self, symbol: str) -> Optional[float]:
        """通过符号搜索价格（谨慎使用）"""
        try:
            # 搜索API调用消耗额度，谨慎使用
            if not self._can_make_api_call():
                return None
            self._record_api_call()  # 记录API调用
            
            url = f"https://api.coingecko.com/api/v3/search?query={urllib.parse.quote(symbol)}"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            if 'coins' in data and len(data['coins']) > 0:
                first_coin = data['coins'][0]
                token_id = first_coin['id']
                print_info(f"🔍 搜索找到: {symbol} -> {token_id}")
                # 注意：这里会再次调用API，但_query_coingecko_by_id会自己记录API调用
                return await self._query_coingecko_by_id(token_id)
            
            return None
            
        except Exception as e:
            logging.debug(f"CoinGecko搜索失败 {symbol}: {e}")
            print_error(f"搜索失败: {symbol} - {e}")
            return None
    
    def get_cache_stats(self) -> Dict:
        """获取缓存统计信息"""
        current_time = time.time()
        total_cached = len(self.price_cache)
        valid_cached = 0
        expired_cached = 0
        
        for cache_data in self.price_cache.values():
            if isinstance(cache_data, dict):
                cached_time = cache_data.get('time', 0)
            else:
                cached_time = cache_data[1] if isinstance(cache_data, tuple) else 0
            
            if current_time - cached_time < self.cache_duration:
                valid_cached += 1
            else:
                expired_cached += 1
        
        return {
            'total_cached': total_cached,
            'valid_cached': valid_cached,
            'expired_cached': expired_cached,
            'monthly_calls': self.monthly_calls,
            'monthly_limit': self.api_calls_per_month,
            'minute_calls': len(self.minute_calls),
            'minute_limit': self.api_calls_per_minute
        }

class AlchemyAPILoadBalancer:
    """Alchemy API 智能负载均衡器"""
    
    def __init__(self, api_keys: List[str]):
        self.api_keys = api_keys
        self.api_instances = []
        self.current_api_index = 0
        self.request_count = 0
        
        # 为每个API密钥创建实例
        for i, api_key in enumerate(api_keys):
            api_instance = AlchemyAPI(api_key, f"API-{i+1}")
            self.api_instances.append(api_instance)
            print_success(f"🔧 初始化API实例 {i+1}: {api_key[:12]}...")
        
        print_success(f"🚀 负载均衡器初始化完成：{len(self.api_instances)} 个API实例")
        print_info(f"📊 总目标速度：{len(self.api_instances) * 500} CU/s")
    
    def get_next_api(self) -> 'AlchemyAPI':
        """智能获取下一个可用的API实例"""
        # 轮询策略：均匀分配请求
        api = self.api_instances[self.current_api_index]
        
        # 检查当前API是否可用
        if api.is_api_available():
            self.current_api_index = (self.current_api_index + 1) % len(self.api_instances)
            return api
        
        # 如果当前API不可用，寻找可用的API
        for i in range(len(self.api_instances)):
            test_index = (self.current_api_index + i) % len(self.api_instances)
            test_api = self.api_instances[test_index]
            if test_api.is_api_available():
                self.current_api_index = (test_index + 1) % len(self.api_instances)
                return test_api
        
        # 所有API都不可用，返回第一个（让它处理限流）
        print_warning("⚠️ 所有API都达到限制，使用第一个API")
        return self.api_instances[0]
    
    def get_usage_stats(self) -> Dict:
        """获取所有API的使用统计"""
        total_stats = {
            "total_cu_rate": 0,
            "total_monthly_usage": 0,
            "total_monthly_limit": 0,
            "api_details": []
        }
        
        for i, api in enumerate(self.api_instances):
            stats = api.get_usage_stats()
            total_stats["total_cu_rate"] += stats["current_cu_rate"]
            total_stats["total_monthly_usage"] += stats["monthly_usage"]
            total_stats["total_monthly_limit"] += stats["monthly_limit"]
            
            api_detail = {
                "api_index": i + 1,
                "api_key_preview": api.api_key[:12] + "...",
                "current_cu_rate": stats["current_cu_rate"],
                "monthly_usage": stats["monthly_usage"],
                "monthly_limit": stats["monthly_limit"],
                "usage_percentage": stats["usage_percentage"],
                "available": api.is_api_available()
            }
            total_stats["api_details"].append(api_detail)
        
        total_stats["usage_percentage"] = (total_stats["total_monthly_usage"] / total_stats["total_monthly_limit"]) * 100 if total_stats["total_monthly_limit"] > 0 else 0
        return total_stats
    
    # 代理方法，自动选择最佳API
    async def check_asset_transfers(self, address: str, chain_config: Dict) -> Tuple[bool, int]:
        api = self.get_next_api()
        return await api.check_asset_transfers(address, chain_config)
    
    async def get_balance(self, address: str, chain_config: Dict) -> float:
        api = self.get_next_api()
        return await api.get_balance(address, chain_config)
    
    async def get_all_token_balances(self, address: str, chain_config: Dict) -> Dict[str, Dict]:
        api = self.get_next_api()
        return await api.get_all_token_balances(address, chain_config)
    
    async def get_token_metadata(self, contract_address: str, chain_config: Dict) -> Dict:
        api = self.get_next_api()
        return await api.get_token_metadata(contract_address, chain_config)
    
    async def get_gas_price(self, chain_config: Dict) -> Dict:
        api = self.get_next_api()
        return await api.get_gas_price(chain_config)

class AlchemyAPI:
    """Alchemy API 封装类"""
    
    def __init__(self, api_key: str, instance_name: str = "API"):
        self.api_key = api_key
        self.instance_name = instance_name
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
        })
        
        # API限频控制 - 智能速率控制，单个API目标480 CU/s（留10%余量）
        self.last_request_time = 0
        self.target_cu_per_second = 480  # 单个API目标480 CU/s，留20 CU/s余量
        self.max_cu_per_second = 500     # 最大不超过500 CU/s
        self.cu_per_request = 1          # 每个请求消耗的CU数，动态调整
        self.request_history = []        # 请求历史记录
        self.current_cu_rate = 0         # 当前CU速率
        
        # 月度额度管理
        self.monthly_cu_limit = 30_000_000  # 每月3000万CU
        self.current_month_usage = 0        # 当月已使用CU
        self.month_start_time = None        # 月初时间
        self.daily_cu_budget = 0            # 每日CU预算
        self.today_usage = 0                # 今日已使用CU
        
        # API可用性检查
        self.last_failure_time = 0
        self.failure_count = 0
        self.cooldown_duration = 60  # 失败后的冷却时间（秒）
    
    def is_api_available(self) -> bool:
        """检查API是否可用"""
        current_time = time.time()
        
        # 检查CU使用率是否超限
        if self.current_cu_rate >= self.max_cu_per_second:
            return False
        
        # 检查月度额度是否耗尽
        if self.current_month_usage >= self.monthly_cu_limit * 0.95:  # 95%预警
            return False
        
        # 检查是否在失败冷却期
        if self.failure_count > 3 and (current_time - self.last_failure_time) < self.cooldown_duration:
            return False
        
        return True
    
    def record_failure(self):
        """记录API失败"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        print_warning(f"⚠️ {self.instance_name} 记录失败 #{self.failure_count}")
    
    def record_success(self):
        """记录API成功，重置失败计数"""
        if self.failure_count > 0:
            print_success(f"✅ {self.instance_name} 恢复正常")
        self.failure_count = 0
    
    async def _rate_limit(self, cu_cost: int = 1):
        """智能API限频控制"""
        current_time = time.time()
        
        # 清理1秒前的请求记录
        self.request_history = [
            (timestamp, cu) for timestamp, cu in self.request_history 
            if current_time - timestamp <= 1.0
        ]
        
        # 计算当前CU速率
        current_cu_usage = sum(cu for _, cu in self.request_history)
        
        # 如果加上当前请求会超过目标速率，则等待
        if current_cu_usage + cu_cost > self.target_cu_per_second:
            # 计算需要等待的时间
            oldest_timestamp = min(timestamp for timestamp, _ in self.request_history) if self.request_history else current_time
            wait_time = 1.0 - (current_time - oldest_timestamp) + 0.001  # 减少等待时间，提升速度
            if wait_time > 0:
                print_info(f"🚦 {self.instance_name} 限频等待 {wait_time:.3f}s (当前: {current_cu_usage}/{self.target_cu_per_second} CU/s)")
                await asyncio.sleep(wait_time)
                current_time = time.time()
                # 重新清理请求记录
                self.request_history = [
                    (timestamp, cu) for timestamp, cu in self.request_history 
                    if current_time - timestamp <= 1.0
                ]
        
        # 记录当前请求
        self.request_history.append((current_time, cu_cost))
        self.last_request_time = current_time
        
        # 更新当前速率
        self.current_cu_rate = sum(cu for _, cu in self.request_history)
        
        # 更新月度和日度使用统计
        self._update_usage_stats(cu_cost)
    
    def _update_usage_stats(self, cu_cost: int):
        """更新使用统计"""
        from datetime import datetime, timezone
        
        now = datetime.now(timezone.utc)
        
        # 检查是否需要重置月度统计（新月份开始时）
        if self.month_start_time is None:
            # 首次初始化
            self.month_start_time = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            self.current_month_usage = 0
        elif now.month != self.month_start_time.month or now.year != self.month_start_time.year:
            # 新月份或新年份，重置统计
            self.month_start_time = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            self.current_month_usage = 0
            print_info(f"🔄 月度额度已重置: {self.monthly_cu_limit:,} CU")
        
        # 检查是否需要重置每日统计
        if hasattr(self, 'last_reset_day'):
            if now.day != self.last_reset_day:
                self.today_usage = 0
                self.last_reset_day = now.day
                print_info(f"🌅 每日统计已重置")
        else:
            self.last_reset_day = now.day
        
        # 更新使用量
        self.current_month_usage += cu_cost
        self.today_usage += cu_cost
        
        # 计算剩余天数和每日预算
        days_in_month = (now.replace(month=now.month+1 if now.month < 12 else 1, 
                                   year=now.year if now.month < 12 else now.year+1, day=1) - 
                        self.month_start_time).days
        days_remaining = days_in_month - now.day + 1
        
        if days_remaining > 0:
            remaining_cu = self.monthly_cu_limit - self.current_month_usage
            self.daily_cu_budget = max(0, remaining_cu // days_remaining)
            
            # 额度预警
            usage_percentage = (self.current_month_usage / self.monthly_cu_limit) * 100
            if usage_percentage >= 90 and not hasattr(self, 'warned_90'):
                print_warning(f"⚠️ 月度额度预警: 已使用 {usage_percentage:.1f}%")
                self.warned_90 = True
            elif usage_percentage >= 75 and not hasattr(self, 'warned_75'):
                print_warning(f"⚠️ 月度额度提醒: 已使用 {usage_percentage:.1f}%")
                self.warned_75 = True
    
    def get_usage_stats(self) -> Dict:
        """获取使用统计信息"""
        from datetime import datetime, timezone
        
        now = datetime.now(timezone.utc)
        days_in_month = (now.replace(month=now.month+1 if now.month < 12 else 1, 
                                   year=now.year if now.month < 12 else now.year+1, day=1) - 
                        self.month_start_time).days if self.month_start_time else 30
        days_remaining = days_in_month - now.day + 1
        
        return {
            "current_cu_rate": self.current_cu_rate,
            "monthly_usage": self.current_month_usage,
            "monthly_limit": self.monthly_cu_limit,
            "monthly_remaining": self.monthly_cu_limit - self.current_month_usage,
            "usage_percentage": (self.current_month_usage / self.monthly_cu_limit) * 100,
            "daily_budget": self.daily_cu_budget,
            "today_usage": self.today_usage,
            "days_remaining": days_remaining,
            "days_in_month": days_in_month
        }
    
    def _get_rpc_url(self, chain_config: Dict) -> str:
        """获取RPC URL，替换为当前API密钥"""
        base_url = chain_config.get('rpc_url', '').strip()
        
        # 替换URL中的PLACEHOLDER_API_KEY为当前实例的密钥
        if 'PLACEHOLDER_API_KEY' in base_url:
            return base_url.replace('PLACEHOLDER_API_KEY', self.api_key)
        
        # 兼容旧的替换方式
        if '/v2/' in base_url:
            parts = base_url.split('/v2/')
            if len(parts) == 2:
                return f"{parts[0]}/v2/{self.api_key}"
        
        return base_url
    
    async def check_asset_transfers(self, address: str, chain_config: Dict) -> Tuple[bool, int]:
        """检查地址是否有交易历史，返回(是否有交易, 交易数量)"""
        await self._rate_limit(15)  # alchemy_getAssetTransfers 消耗约15 CU
        
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
                self.record_success()  # 记录成功
                return transfer_count > 0, transfer_count
            
            self.record_success()  # 记录成功
            return False, 0
        except requests.exceptions.HTTPError as http_error:
            self.record_failure()  # 记录失败
            status_code = getattr(http_error.response, 'status_code', None)
            # 对于 400/403/404/429，视为该链在 Alchemy 上不受支持或密钥未开通
            if status_code in (400, 403, 404, 429):
                print_warning(f"🚫 {chain_config['name']} 在Alchemy上不可用 (HTTP {status_code})，已跳过")
                return False, 0
            # 其它HTTP错误，保守处理为暂不屏蔽
            logging.debug(f"检查交易历史失败 {chain_config['name']} (HTTP {status_code}): {http_error}")
            return True, 0
        except Exception as e:
            self.record_failure()  # 记录失败
            # 网络超时等暂时性错误，不屏蔽
            logging.warning(f"检查交易历史失败 {chain_config['name']}: {e}")
            return True, 0  # 网络错误时假设有交易历史，避免误屏蔽
    
    async def get_balance(self, address: str, chain_config: Dict) -> float:
        """获取原生代币余额"""
        await self._rate_limit(5)  # eth_getBalance 消耗约5 CU
        
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
                self.record_success()  # 记录成功
                return float(balance_eth)
            
            self.record_success()  # 记录成功
            return 0.0
        except requests.exceptions.HTTPError as http_error:
            self.record_failure()  # 记录失败
            status_code = getattr(http_error.response, 'status_code', None)
            if status_code in (400, 403, 404, 429):
                # 不支持的链，静默跳过，避免重复错误日志
                return 0.0
            logging.error(f"获取余额失败 {chain_config['name']}: {http_error}")
            return 0.0
        except Exception as e:
            self.record_failure()  # 记录失败
            logging.error(f"获取余额失败 {chain_config['name']}: {e}")
            return 0.0
    
    async def get_all_token_balances(self, address: str, chain_config: Dict) -> Dict[str, Dict]:
        """获取地址的所有代币余额（原生代币+ERC-20）"""
        await self._rate_limit(25)  # alchemy_getTokenBalances 消耗约25 CU
        
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
            
            self.record_success()  # 记录成功
            return all_balances
            
        except requests.exceptions.HTTPError as http_error:
            self.record_failure()  # 记录失败
            status_code = getattr(http_error.response, 'status_code', None)
            if status_code in (400, 403, 404, 429):
                # 不支持的链，静默跳过
                return {}
            logging.error(f"获取全代币余额失败 {chain_config['name']}: {http_error}")
            return {}
        except Exception as e:
            self.record_failure()  # 记录失败
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
        await self._rate_limit(10)  # alchemy_getTokenMetadata 消耗约10 CU
        
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
                self.record_success()  # 记录成功
                return data['result']
            
            self.record_success()  # 记录成功
            return {}
        except Exception as e:
            self.record_failure()  # 记录失败
            logging.warning(f"获取代币元数据失败 {contract_address}: {e}")
            return {}
    

    
    async def get_gas_price(self, chain_config: Dict) -> Dict:
        """获取实时gas价格"""
        await self._rate_limit(10)  # eth_feeHistory/eth_gasPrice 消耗约10 CU
        
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
                
                # opBNB特殊处理：使用超低gas价格模仿OKX策略
                if chain_config['chain_id'] == 204:  # opBNB
                    base_fee = 101000  # 超低0.000101 gwei，模仿OKX策略
                    priority_fee = 0
                    print_info(f"💡 opBNB超低gas模式: {base_fee/1e9:.6f} gwei (模仿OKX)")
                
                self.record_success()  # 记录成功
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
                
                # opBNB特殊处理：使用超低gas价格模仿OKX策略
                if chain_config['chain_id'] == 204:  # opBNB
                    gas_price = 101000  # 超低0.000101 gwei，模仿OKX策略
                    print_info(f"💡 opBNB超低gas模式: {gas_price/1e9:.6f} gwei (模仿OKX)")
                
                # 确保gas价格不为零
                if gas_price > 0:
                    self.record_success()  # 记录成功
                    return {
                        "gas_price": gas_price,
                        "max_fee": gas_price,
                        "base_fee": gas_price,
                        "priority_fee": 0
                    }
                else:
                    print_warning(f"Gas价格为0，使用最小值 {chain_config['name']}")
                    # opBNB链使用超低gas价格
                    if chain_config['chain_id'] == 204:  # opBNB
                        gas_price = 101000  # 超低0.000101 gwei，模仿OKX策略
                    else:
                        gas_price = 1000000000  # 1 gwei minimum
                    self.record_success()  # 记录成功
                    return {
                        "gas_price": gas_price,
                        "max_fee": gas_price,
                        "base_fee": gas_price,
                        "priority_fee": 0
                    }
        except Exception as e:
            self.record_failure()  # 记录失败
            logging.error(f"获取gas价格失败 {chain_config['name']}: {e}")
            
        # 默认gas价格 - 确保不为零
        if chain_config['chain_id'] == 204:  # opBNB
            default_gas = 101000  # 超低0.000101 gwei，模仿OKX策略
        else:
            default_gas = 20000000000  # 20 gwei
        print_warning(f"使用默认gas价格 {chain_config['name']}: {default_gas/1e9:.6f} gwei")
        return {
            "gas_price": default_gas,
            "max_fee": default_gas,
            "base_fee": default_gas,
            "priority_fee": 0
        }

class TransferManager:
    """转账管理类"""
    
    def __init__(self, alchemy_api: AlchemyAPI, db_manager: DatabaseManager, monitoring_app=None):
        self.alchemy_api = alchemy_api
        self.db_manager = db_manager
        self.web3_instances = {}
        self.monitoring_app = monitoring_app
        self._connection_cleanup_interval = 3600  # 1小时清理一次连接
        self._last_cleanup = time.time()
    
    def _cleanup_stale_connections(self):
        """清理过时的Web3连接"""
        current_time = time.time()
        if current_time - self._last_cleanup > self._connection_cleanup_interval:
            # 清理所有缓存的连接，强制重新创建
            self.web3_instances.clear()
            self._last_cleanup = current_time
            print_info("🧹 已清理Web3连接缓存")
    
    def get_web3_instance(self, chain_config: Dict) -> Web3:
        """获取Web3实例"""
        chain_name = chain_config['name']
        
        # 定期清理连接
        self._cleanup_stale_connections()
        
        if chain_name not in self.web3_instances:
            # 兼容负载均衡器与单实例两种模式
            try:
                if hasattr(self.alchemy_api, '_get_rpc_url'):
                    rpc_url = self.alchemy_api._get_rpc_url(chain_config)
                elif hasattr(self.alchemy_api, 'get_next_api'):
                    api = self.alchemy_api.get_next_api()
                    rpc_url = api._get_rpc_url(chain_config)
                else:
                    rpc_url = chain_config.get('rpc_url', '')
            except Exception:
                rpc_url = chain_config.get('rpc_url', '')
            
            try:
                # 创建HTTP提供者，设置超时
                provider = Web3.HTTPProvider(
                    rpc_url,
                    request_kwargs={'timeout': 30}
                )
                web3 = Web3(provider)
                
                # 为某些链添加POA中间件
                if chain_config['chain_id'] in [56, 137, 250, 43114, 59144]:  # BSC, Polygon, Fantom, Avalanche, Linea
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
                    # 连接性检查
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
            
            # 根据代币类型和链设置gas limit
            if is_erc20:
                if chain_config['chain_id'] == 324:  # ZKsync Era
                    base_gas_limit = 200000  # ZKsync ERC-20需要更多gas
                else:
                    base_gas_limit = 65000  # ERC-20转账基础gas
            else:
                if chain_config['chain_id'] in [421614, 42161]:  # Arbitrum Sepolia/One
                    base_gas_limit = 50000  # Arbitrum需要更多gas
                elif chain_config['chain_id'] == 324:  # ZKsync Era
                    base_gas_limit = 150000  # ZKsync原生转账需要更多gas
                else:
                    base_gas_limit = 21000  # 原生代币转账基础gas
            
            # 获取基础gas价格
            if chain_config['chain_id'] == 204:  # opBNB
                base_gas_price = gas_data.get('gas_price', 101000)  # 超低0.000101 gwei，模仿OKX
                if base_gas_price <= 0:
                    base_gas_price = 101000  # 如果价格为零，使用超低价格
            else:
                base_gas_price = gas_data.get('gas_price', 20000000000)  # 默认20 gwei
                if base_gas_price <= 0:
                    base_gas_price = 20000000000  # 如果价格为零，使用20 gwei
            
            # 🎯 粉尘金额特殊处理：使用合理的低gas价格
            dust_threshold = Web3.to_wei(0.001, 'ether')  # 0.001 ETH以下视为粉尘
            
            if not is_erc20 and balance_wei <= dust_threshold:
                print_info(f"💨 检测到粉尘金额，启用智能低gas模式")
                
                # 获取当前网络的基础费用，确保我们的gas价格不会太低
                try:
                    latest_block = web3.eth.get_block('latest')
                    base_fee = getattr(latest_block, 'baseFeePerGas', None)
                    if base_fee:
                        # 使用基础费用的1.1倍作为最低价格，确保交易能被接受
                        min_gas_price = max(int(base_fee * 1.1), base_gas_price // 5)
                        print_info(f"📊 网络基础费用: {base_fee/1e9:.3f} gwei，调整为: {min_gas_price/1e9:.3f} gwei")
                    else:
                        # 如果没有基础费用信息，使用保守的低价格
                        if chain_config['chain_id'] == 204:  # opBNB
                            min_gas_price = max(base_gas_price // 5, 50500)  # 超低价格，模仿OKX
                        else:
                            min_gas_price = max(base_gas_price // 5, 2000000000)  # 最低2 gwei
                except Exception as e:
                    print_warning(f"无法获取基础费用: {e}")
                    if chain_config['chain_id'] == 204:  # opBNB
                        min_gas_price = max(base_gas_price // 5, 50500)  # 超低价格，模仿OKX
                    else:
                        min_gas_price = max(base_gas_price // 5, 2000000000)  # 最低2 gwei
                
                # 使用最小gas limit
                min_gas_limit = 21000  # 标准最小
                
                # 计算gas成本
                min_gas_cost = min_gas_limit * min_gas_price
                
                # 检查是否还有足够余额
                if balance_wei > min_gas_cost:
                    available_amount = balance_wei - min_gas_cost
                    print_success(f"💎 智能低gas: {min_gas_limit} gas * {min_gas_price/1e9:.3f} gwei = {min_gas_cost/1e18:.9f} ETH")
                    return min_gas_limit, min_gas_price, available_amount
                else:
                    # 如果还是付不起，使用更保守的方法
                    try:
                        # 尝试获取网络建议的最低gas价格
                        suggested_gas = web3.eth.gas_price
                        conservative_gas_price = max(suggested_gas // 3, min_gas_price)
                        conservative_gas_cost = min_gas_limit * conservative_gas_price
                        
                        if balance_wei > conservative_gas_cost:
                            available_amount = balance_wei - conservative_gas_cost
                            print_warning(f"⚡ 保守模式: {min_gas_limit} gas * {conservative_gas_price/1e9:.3f} gwei = {conservative_gas_cost/1e18:.9f} ETH")
                            return min_gas_limit, conservative_gas_price, available_amount
                    except Exception:
                        pass
                    
                    print_error(f"💔 粉尘金额过小，无法支付网络最低gas费用")
                    print_info(f"   余额: {balance_wei/1e18:.9f} ETH")
                    print_info(f"   最低gas费: {min_gas_cost/1e18:.9f} ETH")
                    print_info(f"   差额: {(min_gas_cost - balance_wei)/1e18:.9f} ETH")
                    
                    # 如果差额太大（超过10倍），就不要尝试了
                    if min_gas_cost > balance_wei * 10:
                        print_warning(f"💀 金额过小，跳过转账尝试")
                        return 0, 0, 0
                    
                    # 对于差额不大的情况，给一个提示但仍返回0
                    print_info(f"🤏 金额接近可转账阈值，但仍然不足")
                    return 0, 0, 0
            
            # 正常金额处理
            if chain_config['chain_id'] == 204:  # opBNB
                base_gas_price = max(base_gas_price, 101000)  # 超低0.000101 gwei，模仿OKX
            else:
                base_gas_price = max(base_gas_price, 1000000000)  # 至少1 gwei
            gas_price_multiplier = 1.2
            if chain_config['chain_id'] in [1, 42161, 10]:  # 主网、Arbitrum、Optimism
                gas_price_multiplier = 1.0
            elif chain_config['chain_id'] == 324:  # ZKsync Era
                gas_price_multiplier = 2.0
            elif chain_config['chain_id'] == 204:  # opBNB
                gas_price_multiplier = 1.0  # opBNB gas价格本身就很低，不需要额外倍数
            
            gas_price = int(base_gas_price * gas_price_multiplier)
            
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
                total_needed = gas_limit * gas_price
                
                # 修复：如果gas价格为0，使用最小gas价格
                if gas_price <= 0:
                    if chain_config['chain_id'] == 204:  # opBNB
                        gas_price = 101000  # 超低0.000101 gwei，模仿OKX
                    else:
                        gas_price = 1000000000  # 1 gwei 最小值
                    total_needed = gas_limit * gas_price
                    print_warning(f"Gas价格异常，使用最小值: {gas_price/1e9:.6f} gwei")
                
                # 🎯 粉尘金额自动重新计算gas参数
                if balance_wei <= Web3.to_wei(0.001, 'ether'):
                    print_info(f"💨 粉尘金额重新计算gas参数...")
                    gas_limit, gas_price, available_amount = await self.estimate_smart_gas(
                        from_address, to_address, balance_wei, chain_config, False
                    )
                    total_needed = gas_limit * gas_price
                    if available_amount > 0:
                        print_success(f"✅ 粉尘优化成功，可转账金额: {available_amount/1e18:.9f} ETH")
                
                if available_amount <= 0 or balance_wei < total_needed:
                    logging.warning(f"余额不足以支付gas费用 {chain_config['name']}: 余额 {balance_wei/1e18:.9f}, gas费用 {total_needed/1e18:.9f}")
                    print_warning(f"取消重试 {chain_config['name']}: 余额不足以支付gas费用")
                    return {
                        "success": False,
                        "error": f"余额不足以支付gas费用: 余额 {balance_wei} wei, 需要 {total_needed} wei",
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
                
                # 计算转账金额（转出所有余额），并确保至少为1个最小单位
                decimals = int(token_info['decimals']) if 'decimals' in token_info else 18
                amount_raw = int(Decimal(str(token_info['balance'])) * (10 ** decimals))
                if amount_raw <= 0:
                    raise ValueError("代币余额过小，无法形成有效最小单位，跳过交易")
                
                # 根据链设置适当的gas limit
                if chain_config['chain_id'] == 324:  # ZKsync Era
                    gas_limit = 200000
                elif chain_config['chain_id'] in [421614, 42161]:  # Arbitrum
                    gas_limit = 150000
                else:
                    gas_limit = 100000
                
                # 构建交易数据 - 不包含gas价格
                base_transaction = {
                    'chainId': chain_config['chain_id'],
                    'gas': gas_limit,
                    'nonce': nonce,
                }
                
                try:
                    transaction_data = contract.functions.transfer(
                        Web3.to_checksum_address(to_address),
                        amount_raw
                    ).build_transaction(base_transaction)
                except AttributeError:
                    # 兼容不同版本的Web3
                    transaction_data = contract.functions.transfer(
                        Web3.to_checksum_address(to_address),
                        amount_raw
                    ).buildTransaction(base_transaction)
                
                # 检查原生代币余额是否足够支付gas
                native_balance = web3.eth.get_balance(from_address)
                
                # 获取gas价格
                gas_data = await self.alchemy_api.get_gas_price(chain_config)
                
                # 计算gas费用（使用设置的gas limit）
                estimated_gas_cost = gas_limit * gas_data['gas_price']
                
                if native_balance < estimated_gas_cost:
                    # 🎯 智能gas费用优化尝试
                    print_warning(f"原生代币余额不足，尝试优化gas费用...")
                    
                    try:
                        # 尝试使用最低gas费用模式
                        min_gas_limit = 65000  # ERC-20转账最小gas limit
                        
                        # 获取网络基础费用
                        try:
                            latest_block = web3.eth.get_block('latest')
                            base_fee = getattr(latest_block, 'baseFeePerGas', None)
                            if base_fee:
                                min_gas_price = int(base_fee * 1.1)  # 基础费用1.1倍
                            else:
                                min_gas_price = gas_data['gas_price'] // 5  # 原价格的1/5
                        except Exception:
                            min_gas_price = gas_data['gas_price'] // 5
                        
                        if chain_config['chain_id'] == 204:  # opBNB
                            min_gas_price = max(min_gas_price, 101000)  # 超低0.000101 gwei，模仿OKX
                        else:
                            min_gas_price = max(min_gas_price, 1000000000)  # 最低1 gwei
                        min_estimated_cost = min_gas_limit * min_gas_price
                        
                        if native_balance >= min_estimated_cost:
                            print_success(f"💎 启用低gas模式: {min_gas_limit} gas * {min_gas_price/1e9:.3f} gwei")
                            transaction_data['gas'] = min_gas_limit
                            
                            # 更新gas价格
                            if 'gasPrice' in transaction_data:
                                transaction_data['gasPrice'] = min_gas_price
                            elif 'maxFeePerGas' in transaction_data:
                                transaction_data['maxFeePerGas'] = min_gas_price
                                transaction_data['maxPriorityFeePerGas'] = min(min_gas_price // 10, 1000000000)
                            
                            estimated_gas_cost = min_estimated_cost
                        else:
                            # 检查ERC20代币价值，只有价值大于1美元才发送通知
                            token_price = await self.monitoring_app.price_checker.get_token_price_usd(
                                token_info['symbol'], 
                                token_info.get('contract_address')
                            ) if self.monitoring_app else None
                            
                            token_value_usd = (token_info['balance'] * token_price) if token_price else 0
                            
                            if token_value_usd >= 1.0:  # 只有价值>=1美元才发送通知
                                await self._send_erc20_gas_shortage_notification(
                                    from_address, token_info, chain_config, 
                                    min_estimated_cost, native_balance, token_price, token_value_usd,
                                    TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
                                )
                            else:
                                print_info(f"💡 ERC20代币 {token_info['symbol']} 价值过低 (${token_value_usd:.4f})，跳过通知")
                            
                            raise ValueError(f"原生代币余额不足支付gas费用: 需要 {min_estimated_cost/1e18:.8f} {chain_config['native_token']}, 余额 {native_balance/1e18:.8f}")
                    
                    except ValueError:
                        # 重新抛出ValueError（余额不足）
                        raise
                    except Exception as e:
                        print_warning(f"gas优化失败: {e}")
                        raise ValueError(f"原生代币余额不足支付gas费用: 需要 {estimated_gas_cost/1e18:.8f} {chain_config['native_token']}, 余额 {native_balance/1e18:.8f}")
                
                # 安全设置gas价格 - 避免参数冲突
                try:
                    # 移除可能冲突的gas价格字段
                    if 'gasPrice' in transaction_data:
                        del transaction_data['gasPrice']
                    if 'maxFeePerGas' in transaction_data:
                        del transaction_data['maxFeePerGas']
                    if 'maxPriorityFeePerGas' in transaction_data:
                        del transaction_data['maxPriorityFeePerGas']
                    
                    # 特殊链处理
                    if chain_config['chain_id'] == 324:  # ZKsync Era
                        # ZKsync Era使用传统gas价格，但需要特殊的gas估算
                        transaction_data['gasPrice'] = max(gas_data['gas_price'], 25000000)  # 最少0.025 gwei
                        transaction_data['gas'] = 200000  # ZKsync需要更多gas
                    elif chain_config['chain_id'] == 204:  # opBNB
                        # opBNB使用超低gas价格，模仿OKX策略
                        transaction_data['gasPrice'] = max(gas_data['gas_price'], 101000)  # 超低0.000101 gwei
                        transaction_data['gas'] = 21000  # 标准gas限制
                    elif 'max_fee' in gas_data and chain_config['chain_id'] in [1, 137, 10, 42161]:
                        # EIP-1559支持的链
                        transaction_data['maxFeePerGas'] = gas_data['max_fee']
                        transaction_data['maxPriorityFeePerGas'] = gas_data['priority_fee']
                    else:
                        # 传统gas价格
                        transaction_data['gasPrice'] = gas_data['gas_price']
                except Exception as e:
                    print_warning(f"设置gas价格出错，使用传统方式: {e}")
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
    
    async def _send_erc20_gas_shortage_notification(self, from_address: str, token_info: Dict, 
                                                   chain_config: Dict, estimated_gas_cost: int, 
                                                   native_balance: int, token_price: float = None,
                                                   token_value_usd: float = None,
                                                   telegram_bot_token: str = None,
                                                   telegram_chat_id: str = None):
       """发送ERC20代币gas不足的Telegram通知"""
       try:
           if not telegram_bot_token or not telegram_chat_id:
               return

           # 格式化余额显示
           if token_info['balance'] >= 1:
               balance_str = f"{token_info['balance']:.6f}"
           elif token_info['balance'] >= 0.000001:
               balance_str = f"{token_info['balance']:.8f}"
           else:
               balance_str = f"{token_info['balance']:.12f}"
           
           # 构建价值信息
           value_info = ""
           if token_price is not None and token_value_usd is not None:
               value_info = (
                   f"💵 <b>单价:</b> ${token_price:.6f}\n"
                   f"💎 <b>总价值:</b> ${token_value_usd:.2f}\n"
               )
           
           message = (
               f"🚨 <b>高价值ERC20代币发现但Gas不足</b>\n\n"
               f"🔗 <b>链:</b> {chain_config['name']}\n"
               f"💰 <b>代币:</b> {balance_str} {token_info['symbol']}\n"
               f"{value_info}"
               f"📍 <b>合约地址:</b> <code>{token_info.get('contract_address', 'N/A')}</code>\n"
               f"👤 <b>钱包地址:</b> <code>{from_address}</code>\n"
               f"⛽ <b>需要Gas:</b> {estimated_gas_cost/1e18:.8f} {chain_config['native_token']}\n"
               f"💳 <b>当前余额:</b> {native_balance/1e18:.8f} {chain_config['native_token']}\n"
               f"📊 <b>缺口:</b> {(estimated_gas_cost - native_balance)/1e18:.8f} {chain_config['native_token']}\n\n"
               f"💡 <b>建议操作:</b>\n"
               f"1. 向该地址转入足够的 {chain_config['native_token']} 作为Gas费\n"
               f"2. 手动转出ERC20代币\n"
               f"3. 或等待系统自动重试"
           )
           
           # 发送通知
           url = f"https://api.telegram.org/bot{telegram_bot_token}/sendMessage"
           payload = {
               "chat_id": telegram_chat_id,
               "text": message,
               "parse_mode": "HTML"
           }
           
           response = requests.post(url, json=payload, timeout=10)
           response.raise_for_status()
           print_warning(f"📱 已发送ERC20 Gas不足通知到Telegram")
           
       except Exception as e:
           print_error(f"发送ERC20 Gas不足通知失败: {e}")
           logging.error(f"发送ERC20 Gas不足通知失败: {e}")


class MonitoringApp:
    """主监控应用类"""
    
    def __init__(self):
        self.alchemy_api = None
        self.db_manager = DatabaseManager()
        self.transfer_manager = None
        self.price_checker = PriceChecker()  # 价格检查器
        self.addresses = []
        self.config = {}
        self.monitoring_active = False
        self.blocked_chains_cache = set()  # 缓存已屏蔽的链，避免重复数据库查询
        self.failed_transfers_cache = set()  # 缓存失败的转账，避免重复尝试
        self.db_semaphore = asyncio.Semaphore(20)  # 增加并发数据库操作数量，提升速度
        
        # 轮次统计 - 初始化所有必要属性
        self.round_start_time = time.time()
        self.round_cu_usage = 0
        self.round_count = 0
        
        # 转账统计
        self.total_transfers = 0
        self.total_value_usd = 0.0
        self.current_round_transfers = 0
        self.current_round_progress = {"current": 0, "total": 0}
        self.chain_progress = {"current": 0, "total": 0}
        self.stats_display_active = False
        self.start_time = time.time()
        
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
        
        print_progress("从环境变量加载私钥...")
        private_keys_str = os.getenv("PRIVATE_KEYS")
        if private_keys_str:
            private_keys = [k.strip() for k in private_keys_str.split(',') if k.strip()]
            self.addresses = []
            for pk in private_keys:
                try:
                    account = Account.from_key(pk)
                    self.addresses.append({'address': account.address, 'private_key': pk})
                except:
                    pass
            if self.addresses:
                print_success(f"从环境变量加载了 {len(self.addresses)} 个地址")
        else:
            print_info("未找到PRIVATE_KEYS环境变量，需要手动导入")
        
        # 硬编码API密钥配置（优先使用）
        hardcoded_api_keys = [
            "olq_SkZ9bg2R6kBMIS2-L",
            "B068RgsZ3lfHLgiYuH36L", 
            "aad36gwoDDP-Sxl8AI4Tu"
        ]
        
        # 优先使用硬编码密钥，环境变量作为备用
        env_api_keys = [
            key.strip() 
            for key in os.getenv("ALCHEMY_API_KEYS", "").split(',') 
            if key.strip()
        ]
        
        # 合并API密钥：硬编码 + 环境变量
        api_keys = hardcoded_api_keys + env_api_keys
        
        if not api_keys:
            print_error("未找到任何Alchemy API密钥")
            return

        print_info(f"配置负载均衡器，使用 {len(api_keys)} 个API密钥")
        
        self.alchemy_api = AlchemyAPILoadBalancer(api_keys)
        self.transfer_manager = TransferManager(self.alchemy_api, self.db_manager, self)
        
        # 显示价格缓存统计
        cache_stats = self.price_checker.get_cache_stats()
        print_info(f"💎 CoinGecko API状态:")
        print_info(f"   月度调用: {cache_stats['monthly_calls']}/10,000")
        print_info(f"   价格缓存: {cache_stats['valid_cached']} 有效 / {cache_stats['total_cached']} 总计")
        try:
            cache_hours = (self.price_checker.cache_duration // 3600) if self.price_checker else 24
        except Exception:
            cache_hours = 24
        cache_days = cache_hours / 24
        print_info(f"   缓存时长: {cache_days:g}天")
        
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
                        "min_amount": "0"
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
        self.stats_display_active = True  # 启用统计显示
        
        try:
            # 直接开始监控循环 - 跳过所有预检查
            print_progress("🚀 快速启动模式：直接开始余额监控和转账")
            print_info("⚡ 跳过RPC连接测试和交易记录扫描，立即开始余额查询")
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
        """第二步：扫描交易记录并屏蔽无交易记录的链（超高速版）"""
        print_chain("📜 扫描链上交易记录...")
        print_success(f"🚀 优化模式：每批1个地址，每次最多10条链并发扫描")
        
        total_scanned = 0
        blocked_count = 0
        
        # 批量并发处理 - 每批处理1个地址（降低并发压力）
        batch_size = 1
        address_batches = [self.addresses[i:i + batch_size] for i in range(0, len(self.addresses), batch_size)]
        
        for batch_index, address_batch in enumerate(address_batches):
            print_info(f"⚡ 批次 {batch_index + 1}/{len(address_batches)}: 并发处理 {len(address_batch)} 个地址")
            
            # 并发处理这一批地址
            tasks = []
            for address_info in address_batch:
                task = self.scan_address_chains(address_info, batch_index, len(address_batches))
                tasks.append(task)
            
            # 等待这一批完成
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 统计结果
            for result in batch_results:
                if isinstance(result, tuple):
                    scanned, blocked = result
                    total_scanned += scanned
                    blocked_count += blocked
                elif isinstance(result, Exception):
                    print_warning(f"批处理异常: {result}")
        
        print_success(f"🎉 高速扫描完成: 总扫描 {total_scanned}, 屏蔽 {blocked_count}")
    
    async def scan_address_chains(self, address_info, batch_index, total_batches):
        """并发扫描单个地址的所有链"""
        address = address_info['address']
        scanned = 0
        blocked = 0
        
        try:
            print_info(f"🔍 开始扫描地址: {address[:8]}...{address[-6:]}")
            
            # 限制并发处理链数量 - 每次最多10条链
            all_chain_configs = []
            
            for chain_setting in self.config['chains']:
                chain_config = None
                for chain_name, supported_config in ChainConfig.SUPPORTED_CHAINS.items():
                    if supported_config['chain_id'] == chain_setting['chain_id']:
                        chain_config = supported_config
                        break
                
                if chain_config:
                    all_chain_configs.append(chain_config)
            
            print_info(f"📋 地址 {address[:8]}... 将分批扫描 {len(all_chain_configs)} 条链")
            
            # 分批处理链，每批10条
            chain_batch_size = 10
            chain_batches = [all_chain_configs[i:i + chain_batch_size] for i in range(0, len(all_chain_configs), chain_batch_size)]
            
            all_chain_results = []
            
            for chain_batch_index, chain_batch in enumerate(chain_batches):
                print_info(f"🔗 扫描第 {chain_batch_index + 1}/{len(chain_batches)} 批链 ({len(chain_batch)} 条)")
                
                # 并发处理这一批链
                chain_tasks = []
                for chain_config in chain_batch:
                    task = self.scan_single_chain(address, chain_config)
                    chain_tasks.append(task)
                
                # 使用超时保护，避免卡死
                try:
                    batch_results = await asyncio.wait_for(
                        asyncio.gather(*chain_tasks, return_exceptions=True),
                        timeout=30.0  # 30秒超时
                    )
                    all_chain_results.extend(batch_results)
                except asyncio.TimeoutError:
                    print_error(f"⏰ 第 {chain_batch_index + 1} 批链扫描超时")
                    # 超时的链都标记为失败
                    timeout_results = [(False, 0, config['name']) for config in chain_batch]
                    all_chain_results.extend(timeout_results)
            
            chain_results = all_chain_results
            valid_chain_configs = all_chain_configs
            
            # 统计结果
            valid_chains = 0
            for i, result in enumerate(chain_results):
                if isinstance(result, tuple):
                    has_history, transfer_count, chain_name = result
                    scanned += 1
                    if not has_history:
                        blocked += 1
                    else:
                        valid_chains += 1
                elif isinstance(result, Exception):
                    print_warning(f"链扫描异常 {valid_chain_configs[i]['name']}: {result}")
                    scanned += 1
                    blocked += 1
            
            # 显示地址扫描结果
            if valid_chains > 0:
                print_success(f"✅ {address[:8]}...{address[-6:]}: {valid_chains} 个有效链 / {scanned} 总链")
            else:
                print_warning(f"⚠️ {address[:8]}...{address[-6:]}: 无有效链 / {scanned} 总链")
            
            return scanned, blocked
            
        except Exception as e:
            print_error(f"❌ 扫描地址 {address[:8]}... 出错: {e}")
            # 返回默认值，避免程序崩溃
            return len(self.config.get('chains', [])), len(self.config.get('chains', []))
    
    async def scan_single_chain(self, address, chain_config):
        """扫描单个地址在单条链上的交易历史"""
        try:
            # 检查是否已被屏蔽
            cache_key = f"{address}:{chain_config['chain_id']}"
            if cache_key in self.blocked_chains_cache:
                return False, 0, chain_config['name']
            
            # 添加超时保护的API调用
            try:
                has_history, transfer_count = await asyncio.wait_for(
                    self.alchemy_api.check_asset_transfers(address, chain_config),
                    timeout=30.0  # 30秒超时
                )
                
                if not has_history:
                    # 异步屏蔽链
                    asyncio.create_task(self.db_manager.block_chain(address, chain_config['name'], chain_config['chain_id']))
                    self.blocked_chains_cache.add(cache_key)
                    return False, 0, chain_config['name']
                else:
                    print_success(f"✅ {chain_config['name']}: 发现 {transfer_count}+ 条记录")
                    return True, transfer_count, chain_config['name']
                    
            except asyncio.TimeoutError:
                print_error(f"⏰ {chain_config['name']} API调用超时")
                # 超时的链也标记为屏蔽，避免重复尝试
                self.blocked_chains_cache.add(cache_key)
                return False, 0, chain_config['name']
                
        except Exception as e:
            print_error(f"❌ 扫描链 {chain_config['name']} 异常: {e}")
            import traceback
            print_warning(f"详细错误: {traceback.format_exc()}")
            return False, 0, chain_config['name']
    
    async def monitoring_loop(self):
        """第三步：监控循环"""
        print_chain("💰 开始余额监控循环...")
        
        round_count = 0
        while self.monitoring_active:
            round_count += 1
            self.round_count = round_count
            
            # 重置轮次统计
            import time
            self.round_start_time = time.time()
            # 获取初始CU使用量
            if isinstance(self.alchemy_api, AlchemyAPILoadBalancer):
                usage_stats = self.alchemy_api.get_usage_stats()
                round_start_cu = usage_stats.get('total_monthly_usage', 0)
            elif self.alchemy_api:
                round_start_cu = getattr(self.alchemy_api, 'current_month_usage', 0)
            else:
                round_start_cu = 0
            self.reset_round_stats()
            
            # 计算总操作数（地址数 * 链数）
            total_operations = len(self.addresses) * len(self.config.get('chains', []))
            self.update_round_progress(0, total_operations)
            
            print_progress(f"第 {round_count} 轮监控开始")
            
            # 为每个地址单独处理，提供更清晰的显示
            total_transfers_this_round = 0
            for addr_index, address_info in enumerate(self.addresses, 1):
                address = address_info['address']
                print(f"\n{Fore.CYAN}📍 地址 {addr_index}/{len(self.addresses)}: {address[:8]}...{address[-6:]}{Style.RESET_ALL}")
                
                # 处理该地址的所有链
                address_transfers = 0
                for chain_setting in self.config['chains']:
                    # 通过chain_id查找配置，更可靠
                    chain_config = None
                    for chain_name, supported_config in ChainConfig.SUPPORTED_CHAINS.items():
                        if supported_config['chain_id'] == chain_setting['chain_id']:
                            chain_config = supported_config
                            break
                    
                    if chain_config:
                        result = await self.check_and_transfer(address_info, chain_config)
                        if result:
                            address_transfers += 1
                            total_transfers_this_round += 1
                
                # 显示该地址的结果
                if address_transfers > 0:
                    print(f"{Fore.GREEN}✅ 地址 {addr_index}: {address_transfers} 笔转账{Style.RESET_ALL}")
                else:
                    print(f"{Fore.YELLOW}⭕ 地址 {addr_index}: 无转账{Style.RESET_ALL}")
            
            transfer_count = total_transfers_this_round

            # 计算本轮CU消耗
            if isinstance(self.alchemy_api, AlchemyAPILoadBalancer):
                usage_stats = self.alchemy_api.get_usage_stats()
                round_end_cu = usage_stats.get('total_monthly_usage', 0)
            elif self.alchemy_api:
                round_end_cu = getattr(self.alchemy_api, 'current_month_usage', 0)
            else:
                round_end_cu = 0
            self.round_cu_usage = round_end_cu - round_start_cu
            
            print_success(f"第 {round_count} 轮完成，执行 {transfer_count} 笔转账")
            
            # 每10轮清理一次失败转账缓存，避免缓存过大
            if round_count % 10 == 0 and len(self.failed_transfers_cache) > 0:
                print_info(f"🧹 清理失败转账缓存: {len(self.failed_transfers_cache)} 条记录")
                self.failed_transfers_cache.clear()
            
            # 显示API使用统计
            if self.alchemy_api:
                try:
                    usage_stats = self.alchemy_api.get_usage_stats()
                    print_info(f"📊 API使用统计:")
                    print_info(f"   当前速率: {usage_stats.get('current_cu_rate', 0)} CU/s")
                    print_info(f"   本轮消耗: {self.round_cu_usage:,} CU")
                    print_info(f"   月度使用: {usage_stats.get('monthly_usage', 0):,} / {usage_stats.get('monthly_limit', 0):,} CU ({usage_stats.get('usage_percentage', 0):.1f}%)")
                    print_info(f"   每日预算: {usage_stats.get('daily_budget', 0):,} CU")
                    print_info(f"   剩余天数: {usage_stats.get('days_remaining', 0)} 天")
                except Exception as e:
                    print_warning(f"获取API统计失败: {e}")
            
            # 动态计算暂停时间（对于负载均衡器减少暂停时间）
            try:
                if isinstance(self.alchemy_api, AlchemyAPILoadBalancer):
                    # 多API情况下减少暂停时间
                    dynamic_pause = max(2, self.calculate_dynamic_pause() // 3)
                else:
                    dynamic_pause = self.calculate_dynamic_pause()
            except Exception as e:
                print_warning(f"计算动态暂停时间出错: {e}，使用默认值")
                dynamic_pause = 5  # 默认暂停5秒
            
            print_info(f"⏱️ 智能暂停 {dynamic_pause} 秒...")
            await asyncio.sleep(dynamic_pause)
    
    async def check_and_transfer_with_progress(self, address_info: Dict, chain_config: Dict, 
                                             current_operation: int, total_operations: int) -> bool:
        """检查单个地址和链的余额并执行转账（带进度更新）"""
        self.update_round_progress(current_operation + 1, total_operations)
        return await self.check_and_transfer(address_info, chain_config)
    
    async def check_and_transfer(self, address_info: Dict, chain_config: Dict) -> bool:
        """检查单个地址和链的余额并执行转账"""
        address = address_info['address']
        chain_name = chain_config['name']
        
        try:
            all_balances = await self.alchemy_api.get_all_token_balances(address, chain_config)
            
            # 检查是否有余额
            has_balance = False
            total_tokens = 0
            
            if all_balances:
                for token_key, token_info in all_balances.items():
                    total_tokens += 1
                    if token_info['balance'] > 0:
                        has_balance = True
                        
                        # 生成失败转账缓存键
                        cache_key = f"{address}:{chain_config['chain_id']}:{token_info.get('symbol', 'UNKNOWN')}:{token_info.get('type', 'unknown')}"
                        
                        # 检查是否已经失败过，避免重复尝试相同的无效转账
                        if cache_key in self.failed_transfers_cache:
                            print(f"{Fore.YELLOW}⚠️ 跳过已知失败转账: {token_info['symbol']} ({chain_name}){Style.RESET_ALL}")
                            continue
                        
                        # 取消最小额度阈值限制，任何大于0的余额都进行转账
                        balance = token_info['balance']
                        balance_str = f"{balance:.6f}" if balance >= 1 else f"{balance:.12f}"
                        
                        # 🎯 粉尘金额特殊标识
                        if token_info.get('type') == 'native' and balance <= 0.001:
                            print(f"{Fore.YELLOW}💨 发现粉尘余额: {balance_str} {token_info['symbol']} ({chain_name}) - 启用超低gas模式{Style.RESET_ALL}")
                        else:
                            print(f"{Fore.RED}🔴 发现余额: {balance_str} {token_info['symbol']} ({chain_name}){Style.RESET_ALL}")
                        
                        result = await self.execute_transfer(address_info, chain_config, token_info)
                        
                        # 如果转账失败，添加到失败缓存中
                        if result and not result.get('success'):
                            error_msg = result.get('error', '')
                            # 缓存多种类型的失败，避免重复尝试
                            cache_conditions = [
                                "余额不足" in error_msg,
                                "insufficient funds" in error_msg.lower(),
                                "max fee per gas less than block base fee" in error_msg.lower(),
                                "金额过小，跳过转账尝试" in error_msg
                            ]
                            
                            if any(cache_conditions):
                                self.failed_transfers_cache.add(cache_key)
                                print(f"{Fore.GRAY}📝 已缓存失败转账: {token_info['symbol']} ({chain_name}){Style.RESET_ALL}")
                        if result and result.get('success'):
                            transfer_value_usd = 0.0
                            try:
                                token_price = await self.price_checker.get_token_price_usd(
                                    token_info['symbol'],
                                    token_info.get('contract_address')
                                )
                                if token_price:
                                    transfer_value_usd = (result.get('amount', 0) or 0) * token_price
                            except Exception as e:
                                logging.debug(f"计算转账价值失败: {e}")
                            
                            self.add_transfer_stats(transfer_value_usd)
                            print_transfer(f"转账成功: {result.get('amount', 0)} {token_info['symbol']} (${transfer_value_usd:.2f})")
            
            # 显示链状态
            if not has_balance:
                print(f"{Fore.BLACK}⚫ 无余额: {chain_name}{Style.RESET_ALL}")
            
            return has_balance
            
        except Exception as e:
            # 对于API错误，也显示为无余额状态
            print(f"{Fore.BLACK}⚫ 无余额: {chain_name} (API错误){Style.RESET_ALL}")
            return False
    
    async def execute_transfer(self, address_info: Dict, chain_config: Dict, token_info: Dict) -> Dict:
        """执行转账操作"""
        address = address_info['address']
        private_key = address_info['private_key']
        # 优先使用链级配置中的收款地址，回退到全局TARGET_ADDRESS
        recipient = None
        try:
            recipient = next((c.get('recipient_address') for c in self.config.get('chains', []) if c.get('chain_id') == chain_config.get('chain_id') and c.get('recipient_address')), None)
        except Exception:
            recipient = None
        recipient = recipient or TARGET_ADDRESS
        
        token_type = token_info['type']
        symbol = token_info['symbol']
        balance = token_info['balance']
        
        # 使用与发现余额相同的格式化逻辑
        if balance >= 1:
            balance_str = f"{balance:.6f}"
        elif balance >= 0.000001:
            balance_str = f"{balance:.8f}"
        else:
            balance_str = f"{balance:.12f}"
        
        print_transfer(f"💸 准备转账: {balance_str} {symbol} -> {recipient}")
        
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
    

    
    async def configure_private_keys(self):
        """导入私钥"""
        print_chain("📥 导入私钥")
        print_error("安全警告: 以纯文本格式存储私钥存在风险。请确保您的环境安全。")
        print_info("支持格式:")
        print_info("- 单个私钥: 0xabc123...def789")
        print_info("- 多个私钥: 0xabc123...def789,0x123...456")
        print_info("- 每行一个私钥（支持多行粘贴）")
        print_info("- 输入 'end' 结束输入（区分大小写）")
        print_warning("⚠️  注意：只有输入 'end' 才能结束，不支持双击回车结束")

        # 支持连续多行输入，直到输入 'end' 为止
        lines = []
        print_progress("请输入私钥内容（输入 'end' 结束）:")
        
        try:
            line_count = 0
            while True:
                try:
                    line = input(f"第{line_count + 1}行> ").strip()
                except EOFError:
                    print_info("检测到EOF，继续等待输入...")
                    continue
                
                # 只有输入 'end' 才结束
                if line == 'end':
                    print_success("检测到结束标记 'end'，开始处理输入...")
                    break
                
                # 即使是空行也添加到lines中，不会结束输入
                lines.append(line)
                line_count += 1
                
                # 显示当前已输入的行数
                if line_count % 5 == 0:
                    print_info(f"已输入 {line_count} 行，输入 'end' 结束")
                    
        except KeyboardInterrupt:
            print_warning("输入被中断")
            return
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
                    # API密钥已硬编码到程序中，无需手动配置.env文件
                    print_success("✅ API密钥已内置到程序中，无需额外配置")
                    print_info("💡 如需使用其他API密钥，可在.env文件中配置ALCHEMY_API_KEYS")
                    print_warning("⚠️  注意：存储明文私钥存在安全风险，请确保环境安全")

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

                    # 创建配置 - 只监控opBNB链
                    working_chains = [
                        "OPBNB"  # 只保留opBNB链
                    ]
                    
                    chains_config = []
                    for chain_name in working_chains:
                        if chain_name in ChainConfig.SUPPORTED_CHAINS:
                            chain_info = ChainConfig.SUPPORTED_CHAINS[chain_name]
                            chains_config.append({
                                "name": chain_name,
                                "chain_id": chain_info['chain_id'],
                                "recipient_address": TARGET_ADDRESS,
                                "min_amount": "0.0000005"  # 超低门槛，模仿OKX策略，确保0.01美金都能转出
                            })

                    self.config = {
                        "chains": chains_config,
                        "erc20": [],
                        "settings": {
                            "monitoring_interval": 1.0,  # 设置更合理的间隔
                            "round_pause": 5,
                            "gas_threshold_gwei": 50,
                            "gas_wait_time": 60,
                            "adaptive_timing": True  # 启用自适应时间调整
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
    
    def print_stats_header(self):
        """打印统计信息头部"""
        if not self.stats_display_active:
            return
            
        # 计算运行时间
        running_time = time.time() - self.start_time
        hours = int(running_time // 3600)
        minutes = int((running_time % 3600) // 60)
        seconds = int(running_time % 60)
        
        # 获取API使用统计
        usage_stats = self.get_normalized_usage_stats()
        cache_stats = self.price_checker.get_cache_stats() if self.price_checker else {}
        
        # 格式化统计信息
        stats_lines = [
            f"🚀 EVM多链监控工具 - 实时统计",
            f"⏰ 运行时间: {hours:02d}:{minutes:02d}:{seconds:02d}",
            f"🔄 监控轮次: {self.round_count}",
            f"💸 总转账数: {self.total_transfers} 笔",
            f"💰 总价值: ${self.total_value_usd:.2f}",
            f"📊 本轮进度: {self.current_round_progress['current']}/{self.current_round_progress['total']}",
            f"🔗 链进度: {self.chain_progress['current']}/{self.chain_progress['total']}",
            f"⚡ Alchemy: {usage_stats.get('total_cu_rate', 0)}/1500 CU/s ({usage_stats.get('usage_percentage', 0):.1f}%)",
            f"💎 CoinGecko: {cache_stats.get('monthly_calls', 0)}/10,000 ({cache_stats.get('minute_calls', 0)}/30/min)",
            f"🏪 价格缓存: {cache_stats.get('valid_cached', 0)} 有效 / {cache_stats.get('total_cached', 0)} 总计",
        ]
        
        # 简化显示（在终端顶部显示一行统计）
        api_status_summary = "/".join([f"API{api['api_index']}:{api['current_cu_rate']}" for api in usage_stats.get('api_details', [])])
        stats_summary = (f"🚀 轮次:{self.round_count} | 💸 转账:{self.total_transfers}笔 | "
                        f"💰 ${self.total_value_usd:.2f} | 📊 {self.current_round_progress['current']}/{self.current_round_progress['total']} | "
                        f"🔗 {self.chain_progress['current']}/{self.chain_progress['total']} | "
                        f"⚡ {usage_stats.get('total_cu_rate', 0)}/1500 CU/s | "
                        f"🔧 {api_status_summary} | "
                        f"📈 {usage_stats.get('usage_percentage', 0):.1f}%")
        
        # 使用ANSI转义序列在终端标题栏显示
        print(f"\033]0;{stats_summary}\007", end="")
        
        # 同时在每轮开始时显示详细统计
        if self.current_round_progress['current'] == 0:
            print(f"{Fore.CYAN}{'='*80}{Style.RESET_ALL}")
            print(f"{Fore.WHITE}{Back.BLUE} 📊 实时统计总览 {Style.RESET_ALL}")
            print(f"{Fore.CYAN}{'='*80}{Style.RESET_ALL}")
            for line in stats_lines:
                print(f"{Fore.YELLOW}{line}{Style.RESET_ALL}")
            print(f"{Fore.CYAN}{'='*80}{Style.RESET_ALL}")
    
    def update_round_progress(self, current: int, total: int):
        """更新轮次进度"""
        self.current_round_progress = {"current": current, "total": total}
        if self.stats_display_active:
            self.print_stats_header()
    
    def update_chain_progress(self, current: int, total: int):
        """更新链进度"""
        self.chain_progress = {"current": current, "total": total}
        if self.stats_display_active:
            self.print_stats_header()
    
    def add_transfer_stats(self, value_usd: float = 0.0):
        """添加转账统计"""
        self.total_transfers += 1
        self.current_round_transfers += 1
        self.total_value_usd += value_usd
        if self.stats_display_active:
            self.print_stats_header()
    
    def reset_round_stats(self):
        """重置轮次统计"""
        self.current_round_transfers = 0
        self.current_round_progress = {"current": 0, "total": 0}
        self.chain_progress = {"current": 0, "total": 0}
    
    def get_normalized_usage_stats(self) -> Dict:
        """获取统一化的API使用统计信息"""
        if not self.alchemy_api:
            return {
                "current_cu_rate": 0,
                "total_cu_rate": 0,
                "monthly_usage": 0,
                "total_monthly_usage": 0,
                "monthly_limit": 30_000_000,
                "total_monthly_limit": 30_000_000,
                "monthly_remaining": 30_000_000,
                "usage_percentage": 0,
                "daily_budget": 1_000_000,
                "days_remaining": 15,
                "api_details": []
            }
        
        usage_stats = self.alchemy_api.get_usage_stats()
        
        # 适配负载均衡器的统计结构
        if isinstance(self.alchemy_api, AlchemyAPILoadBalancer):
            # 负载均衡器返回的统计结构
            return {
                "current_cu_rate": usage_stats.get("total_cu_rate", 0),
                "total_cu_rate": usage_stats.get("total_cu_rate", 0),
                "monthly_usage": usage_stats.get("total_monthly_usage", 0),
                "total_monthly_usage": usage_stats.get("total_monthly_usage", 0),
                "monthly_limit": usage_stats.get("total_monthly_limit", 90_000_000),
                "total_monthly_limit": usage_stats.get("total_monthly_limit", 90_000_000),
                "monthly_remaining": usage_stats.get("total_monthly_limit", 90_000_000) - usage_stats.get("total_monthly_usage", 0),
                "usage_percentage": usage_stats.get("usage_percentage", 0),
                "daily_budget": (usage_stats.get("total_monthly_limit", 90_000_000) - usage_stats.get("total_monthly_usage", 0)) // 15,
                "days_remaining": 15,
                "api_details": usage_stats.get("api_details", [])
            }
        else:
            # 单个API的统计结构
            return {
                "current_cu_rate": usage_stats.get("current_cu_rate", 0),
                "total_cu_rate": usage_stats.get("current_cu_rate", 0),
                "monthly_usage": usage_stats.get("monthly_usage", 0),
                "total_monthly_usage": usage_stats.get("monthly_usage", 0),
                "monthly_limit": usage_stats.get("monthly_limit", 30_000_000),
                "total_monthly_limit": usage_stats.get("monthly_limit", 30_000_000),
                "monthly_remaining": usage_stats.get("monthly_remaining", 30_000_000),
                "usage_percentage": usage_stats.get("usage_percentage", 0),
                "daily_budget": usage_stats.get("daily_budget", 1_000_000),
                "days_remaining": usage_stats.get("days_remaining", 15),
                "api_details": [{
                    "api_index": 1,
                    "api_key_preview": "Single API",
                    "current_cu_rate": usage_stats.get("current_cu_rate", 0),
                    "monthly_usage": usage_stats.get("monthly_usage", 0),
                    "monthly_limit": usage_stats.get("monthly_limit", 30_000_000),
                    "usage_percentage": usage_stats.get("usage_percentage", 0),
                    "available": True
                }]
            }
    
    def calculate_dynamic_pause(self) -> int:
        """根据月度额度使用情况计算动态暂停时间"""
        if not self.alchemy_api:
            return 5  # 默认5秒
            
        normalized_stats = self.get_normalized_usage_stats()
        
        # 使用统一化的统计信息
        monthly_remaining = normalized_stats["monthly_remaining"]
        days_remaining = normalized_stats["days_remaining"]
        daily_budget = normalized_stats["daily_budget"]
        
        if days_remaining <= 0 or daily_budget <= 0:
            return 300  # 如果额度用尽，暂停5分钟
        
        # 初始化轮次统计属性（如果不存在）
        if not hasattr(self, 'round_cu_usage'):
            self.round_cu_usage = 0
        if not hasattr(self, 'round_start_time'):
            self.round_start_time = time.time()
        
        # 如果这一轮消耗了CU，计算建议的暂停时间
        if self.round_cu_usage > 0 and self.round_start_time:
            round_duration = time.time() - self.round_start_time
            
            # 计算每秒CU消耗率
            cu_per_second = self.round_cu_usage / max(round_duration, 1)
            
            # 计算每日CU分配下，剩余时间可以运行的秒数
            if cu_per_second > 0:
                daily_runtime_seconds = daily_budget / cu_per_second
                
                # 一天有86400秒，如果当前消耗速度下只能运行少于一天，需要暂停
                seconds_in_day = 86400
                if daily_runtime_seconds < seconds_in_day:
                    # 计算需要暂停多久才能均匀分配到全天
                    pause_seconds = seconds_in_day - daily_runtime_seconds
                    
                    # 限制暂停时间在合理范围内（5秒到30分钟）
                    pause_seconds = max(5, min(1800, int(pause_seconds)))
                    
                    print_info(f"📊 动态暂停计算:")
                    print_info(f"   本轮消耗: {self.round_cu_usage:,} CU ({round_duration:.1f}秒)")
                    print_info(f"   每日预算: {daily_budget:,} CU")
                    print_info(f"   剩余天数: {days_remaining} 天")
                    print_info(f"   建议暂停: {pause_seconds} 秒")
                    
                    return pause_seconds
        
        # 默认暂停时间
        return 5
    
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
    
    async def show_interactive_menu(self):
        """显示交互式主菜单"""
        while True:
            try:
                print(f"\n{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
                print(f"{Fore.WHITE}{Back.BLUE} 🚀 EVM多链监控工具 - 主菜单 {Style.RESET_ALL}")
                print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
                
                # 显示当前状态
                if self.addresses:
                    print_success(f"✅ 已配置 {len(self.addresses)} 个监控地址")
                else:
                    print_warning("⚠️  未配置监控地址")
                
                if self.alchemy_api:
                    # 显示API使用统计
                    usage_stats = self.get_normalized_usage_stats()
                    cache_stats = self.price_checker.get_cache_stats()
                    print_info(f"📊 API状态:")
                    print_info(f"   Alchemy总计: {usage_stats.get('total_cu_rate', 0)}/1500 CU/s ({usage_stats.get('usage_percentage', 0):.1f}%)")
                    
                    # 显示各个API的详细状态
                    for api_detail in usage_stats.get('api_details', []):
                        status = "🟢" if api_detail['available'] else "🔴"
                        print_info(f"   {status} API-{api_detail['api_index']}: {api_detail['current_cu_rate']}/500 CU/s ({api_detail['usage_percentage']:.1f}%)")
                    
                    print_info(f"   CoinGecko: {cache_stats.get('monthly_calls', 0)}/10,000 ({cache_stats.get('minute_calls', 0)}/30/min)")
                    print_info(f"   价格缓存: {cache_stats.get('valid_cached', 0)} 有效 / {cache_stats.get('total_cached', 0)} 总计")
                
                print(f"\n{Fore.YELLOW}请选择操作:{Style.RESET_ALL}")
                print(f"{Fore.GREEN}1.{Style.RESET_ALL} 📥 导入私钥")
                print(f"{Fore.GREEN}2.{Style.RESET_ALL} 🚀 开始监控")
                print(f"{Fore.GREEN}3.{Style.RESET_ALL} 📊 查看统计")
                print(f"{Fore.GREEN}0.{Style.RESET_ALL} 🚪 退出程序")
                
                try:
                    choice = input(f"\n{Fore.CYAN}请输入选择 (0-3): {Style.RESET_ALL}").strip()
                except EOFError:
                    print_warning("检测到EOF，退出程序")
                    break
                
                if choice == '1':
                    await self.configure_private_keys()
                elif choice == '2':
                    if not self.addresses:
                        print_error("请先导入私钥！")
                        continue
                    await self.start_monitoring()
                elif choice == '3':
                    await self.show_statistics()
                elif choice == '0':
                    print_success("退出程序")
                    break
                else:
                    print_error("无效选择，请输入 0-3")
                    
            except KeyboardInterrupt:
                print_warning("\n程序被中断，正在退出...")
                break
            except Exception as e:
                print_error(f"菜单操作出错: {e}")
                logging.error(f"菜单操作出错: {e}")
    
    async def show_statistics(self):
        """显示详细统计信息"""
        print(f"\n{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
        print(f"{Fore.WHITE}{Back.BLUE} 📊 系统统计信息 {Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
        
        # 地址统计
        print(f"{Fore.YELLOW}📍 地址配置:{Style.RESET_ALL}")
        print(f"   监控地址数量: {len(self.addresses)}")
        if self.addresses:
            for i, addr_info in enumerate(self.addresses, 1):
                print(f"   {i}. {addr_info['address']}")
        
        # 链配置统计
        if self.config.get('chains'):
            print(f"\n{Fore.YELLOW}🔗 链配置:{Style.RESET_ALL}")
            print(f"   配置链数量: {len(self.config['chains'])}")
        
        # API使用统计
        if self.alchemy_api:
            usage_stats = self.get_normalized_usage_stats()
            print(f"\n{Fore.YELLOW}⚡ Alchemy API负载均衡器:{Style.RESET_ALL}")
            print(f"   总当前速率: {usage_stats.get('total_cu_rate', 0)} CU/s (目标: 1500)")
            print(f"   总月度使用: {usage_stats.get('total_monthly_usage', 0):,} / {usage_stats.get('total_monthly_limit', 0):,} CU")
            print(f"   总使用百分比: {usage_stats.get('usage_percentage', 0):.1f}%")
            
            print(f"\n{Fore.YELLOW}   API实例详情:{Style.RESET_ALL}")
            for api_detail in usage_stats.get('api_details', []):
                status = "🟢 可用" if api_detail['available'] else "🔴 不可用"
                print(f"   API-{api_detail['api_index']} ({api_detail['api_key_preview']}): {api_detail['current_cu_rate']}/500 CU/s ({api_detail['usage_percentage']:.1f}%) - {status}")
        
        # CoinGecko统计
        cache_stats = self.price_checker.get_cache_stats()
        print(f"\n{Fore.YELLOW}💎 CoinGecko API:{Style.RESET_ALL}")
        print(f"   月度调用: {cache_stats.get('monthly_calls', 0)} / {cache_stats.get('monthly_limit', 10000)}")
        print(f"   分钟调用: {cache_stats.get('minute_calls', 0)} / {cache_stats.get('minute_limit', 30)}")
        print(f"   价格缓存: {cache_stats.get('valid_cached', 0)} 有效 / {cache_stats.get('total_cached', 0)} 总计")
        print(f"   缓存时长: 3天")
        
        # 转账统计
        print(f"\n{Fore.YELLOW}💸 转账统计:{Style.RESET_ALL}")
        print(f"   总转账数: {self.total_transfers} 笔")
        print(f"   总价值: ${self.total_value_usd:.2f}")
        print(f"   监控轮次: {self.round_count}")
        
        print(f"\n{Fore.GREEN}按回车键返回主菜单...{Style.RESET_ALL}")
        try:
            input()
        except EOFError:
            pass
    
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
