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

# 加载环境变量
load_dotenv()

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
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT 1 FROM blocked_chains WHERE address = ? AND chain_id = ?",
                (address, chain_id)
            )
            result = await cursor.fetchone()
            return result is not None
    
    async def block_chain(self, address: str, chain_name: str, chain_id: int, reason: str = "No transaction history"):
        """屏蔽链"""
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
        
        # API限频控制
        self.last_request_time = 0
        self.min_request_interval = 0.1  # 100ms间隔，按用户要求
    
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
    
    async def check_asset_transfers(self, address: str, chain_config: Dict) -> bool:
        """检查地址是否有交易历史"""
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
                    "maxCount": "0x1"
                }
            ]
        }
        
        try:
            response = self.session.post(url, json=payload, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if 'result' in data:
                transfers = data['result'].get('transfers', [])
                return len(transfers) > 0
            
            return False
        except requests.exceptions.HTTPError as http_error:
            status_code = getattr(http_error.response, 'status_code', None)
            # 对于 400/403/404，视为该链在 Alchemy 上不受支持或密钥未开通，返回 False 以触发屏蔽
            if status_code in (400, 403, 404):
                logging.debug(
                    f"{chain_config['name']} 在 Alchemy 上不可用或未开通 (HTTP {status_code})，将屏蔽该链"
                )
                return False
            # 其它HTTP错误，保守处理为暂不屏蔽
            logging.debug(f"检查交易历史失败 {chain_config['name']} (HTTP {status_code}): {http_error}")
            return True
        except Exception as e:
            # 网络超时等暂时性错误，不屏蔽
            logging.warning(f"检查交易历史失败 {chain_config['name']}: {e}")
            return True  # 网络错误时假设有交易历史，避免误屏蔽
    
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
            web3 = Web3(Web3.HTTPProvider(rpc_url))
            
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
                    logging.warning(f"POA中间件注入失败: {e}")
                    # 继续执行，不影响主要功能
            
            self.web3_instances[chain_name] = web3
        
        return self.web3_instances[chain_name]
    
    async def estimate_gas_cost(self, from_address: str, to_address: str, 
                              amount_wei: int, chain_config: Dict) -> Tuple[int, int]:
        """估算gas成本"""
        web3 = self.get_web3_instance(chain_config)
        
        try:
            # 估算gas limit
            gas_estimate = web3.eth.estimate_gas({
                'from': from_address,
                'to': to_address,
                'value': amount_wei
            })
            
            # 获取gas价格
            gas_data = await self.alchemy_api.get_gas_price(chain_config)
            gas_price = gas_data['gas_price']
            
            # 增加10%的gas limit缓冲
            gas_limit = int(gas_estimate * 1.1)
            total_gas_cost = gas_limit * gas_price
            
            return gas_limit, total_gas_cost
            
        except Exception as e:
            logging.error(f"估算gas失败 {chain_config['name']}: {e}")
            # 默认值
            return 21000, 21000 * 20000000000  # 21k gas * 20 gwei
    
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
                
                # 估算gas成本
                gas_limit, gas_cost = await self.estimate_gas_cost(
                    from_address, to_address, amount_wei, chain_config
                )
                
                # 检查余额是否足够
                balance_wei = Web3.to_wei(await self.alchemy_api.get_balance(from_address, chain_config), 'ether')
                if balance_wei < (amount_wei + gas_cost):
                    # 调整转账金额，保留gas费用
                    amount_wei = max(0, balance_wei - gas_cost)
                    if amount_wei <= 0:
                        raise ValueError("余额不足以支付gas费用")
                
                # 获取gas价格
                gas_data = await self.alchemy_api.get_gas_price(chain_config)
                
                # 构建交易
                transaction = {
                    'nonce': nonce,
                    'to': to_address,
                    'value': amount_wei,
                    'gas': gas_limit,
                    'chainId': chain_config['chain_id']
                }
                
                # 根据链支持情况设置gas价格
                if 'max_fee' in gas_data and chain_config['chain_id'] in [1, 137, 10, 42161]:  # 支持EIP-1559的链
                    transaction.update({
                        'maxFeePerGas': gas_data['max_fee'],
                        'maxPriorityFeePerGas': gas_data['priority_fee']
                    })
                else:
                    transaction['gasPrice'] = gas_data['gas_price']
                
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
                    tx_hash_hex, str(receipt.gasUsed), str(gas_data['gas_price']),
                    "success"
                )
                
                return {
                    "success": True,
                    "tx_hash": tx_hash_hex,
                    "amount": Web3.from_wei(amount_wei, 'ether'),
                    "gas_used": receipt.gasUsed,
                    "gas_price": gas_data['gas_price'],
                    "type": "native"
                }
                
            except Exception as e:
                error_msg = str(e)
                logging.error(f"原生代币转账失败 (重试 {retry + 1}/{max_retries}) {chain_config['name']}: {error_msg}")
                
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
                transaction_data = contract.functions.transfer(
                    Web3.to_checksum_address(to_address),
                    amount_raw
                ).build_transaction({
                    'chainId': chain_config['chain_id'],
                    'gas': 100000,  # ERC-20转账的gas limit
                    'nonce': nonce,
                })
                
                # 获取gas价格
                gas_data = await self.alchemy_api.get_gas_price(chain_config)
                
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
        # 初始化数据库
        await self.db_manager.init_database()
        
        # 加载配置
        await self.load_config()
        
        # 使用固定的API密钥
        api_key = "MYr2ZG1P7bxc4F1qVTLIj"
        logging.info(f"使用API密钥: {api_key[:8]}...")
        
        self.alchemy_api = AlchemyAPI(api_key)
        self.transfer_manager = TransferManager(self.alchemy_api, self.db_manager)
        
        # 提取私钥和地址
        private_keys_input = os.getenv('PRIVATE_KEYS', '')
        if private_keys_input:
            private_keys = self.extract_private_keys(private_keys_input)
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
        
        logging.info(f"已加载 {len(self.addresses)} 个地址进行监控")
    
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
        has_history = await self.alchemy_api.check_asset_transfers(address, chain_config)
        
        if not has_history:
            # 屏蔽无交易历史的链
            await self.db_manager.block_chain(
                address, chain_config['name'], chain_config['chain_id']
            )
            logging.debug(f"屏蔽链 {chain_config['name']} (地址: {address}): 无交易历史或不可用")
        
        return has_history
    
    async def monitor_address_chain(self, address_info: Dict, chain_config: Dict):
        """监控单个地址在单个链上的所有代币余额"""
        address = address_info['address']
        private_key = address_info['private_key']
        
        try:
            # 使用缓存快速检查链是否已被屏蔽
            cache_key = f"{address}:{chain_config['chain_id']}"
            if cache_key in self.blocked_chains_cache:
                return
            
            # 检查数据库中是否已屏蔽
            if await self.db_manager.is_chain_blocked(address, chain_config['chain_id']):
                self.blocked_chains_cache.add(cache_key)
                return
            
            # 检查链是否被屏蔽或不受支持
            if not await self.check_chain_history(address, chain_config):
                self.blocked_chains_cache.add(cache_key)
                return
            
            # 获取所有代币余额（原生代币+ERC-20）
            all_balances = await self.alchemy_api.get_all_token_balances(address, chain_config)
            
            if not all_balances:
                return
            
            # 查找对应的配置
            chain_setting = None
            for setting in self.config['chains']:
                if setting['chain_id'] == chain_config['chain_id']:
                    chain_setting = setting
                    break
            
            if not chain_setting:
                logging.warning(f"未找到链 {chain_config['name']} 的配置")
                return
            
            recipient = chain_setting['recipient_address']
            
            if recipient == "0x0000000000000000000000000000000000000000":
                logging.debug(f"链 {chain_config['name']} 未配置有效的接收地址")
                return
            
            # 处理每种代币
            for token_key, token_info in all_balances.items():
                if token_info['balance'] <= 0:
                    continue
                
                token_type = token_info['type']
                symbol = token_info['symbol']
                balance = token_info['balance']
                
                # 检查最小转账金额（仅对原生代币）
                if token_type == 'native':
                    min_amount = float(chain_setting.get('min_amount', '0.001'))
                    if balance < min_amount:
                        logging.debug(f"余额低于最小转账金额 {chain_config['name']}: {balance} < {min_amount} {symbol}")
                        continue
                
                logging.info(f"发现可转账余额 {chain_config['name']}: {balance} {symbol} ({token_type}) (地址: {address})")
                
                try:
                    # 根据代币类型选择转账方法
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
                        logging.warning(f"不支持的代币类型: {token_type}")
                        continue
                    
                    if result['success']:
                        if token_type == 'native':
                            logging.info(f"原生代币转账成功 {chain_config['name']}: {result['amount']} {symbol} -> {recipient}")
                        elif token_type == 'erc20':
                            logging.info(f"ERC-20转账成功 {chain_config['name']}: {result['amount']} {symbol} -> {recipient}")
                        
                        logging.info(f"交易哈希: {result['tx_hash']}")
                        
                        # 发送Discord通知
                        await self.send_discord_notification(
                            f"✅ {token_type.upper()}转账成功\n"
                            f"链: {chain_config['name']}\n"
                            f"代币: {symbol}\n"
                            f"数量: {balance}\n"
                            f"从: {address}\n"
                            f"到: {recipient}\n"
                            f"交易: {result['tx_hash']}"
                        )
                    else:
                        logging.error(f"{token_type.upper()}转账失败 {chain_config['name']} {symbol}: {result['error']}")
                        await self.send_discord_notification(
                            f"❌ {token_type.upper()}转账失败\n"
                            f"链: {chain_config['name']}\n"
                            f"代币: {symbol}\n"
                            f"地址: {address}\n"
                            f"错误: {result['error']}"
                        )
                        
                except Exception as transfer_error:
                    logging.error(f"转账过程中出错 {symbol}: {transfer_error}")
                    await self.db_manager.log_message("ERROR", f"转账错误: {transfer_error}", address, chain_config['name'])
            
        except Exception as e:
            logging.error(f"监控地址 {address} 在链 {chain_config['name']} 时出错: {e}")
            await self.db_manager.log_message("ERROR", f"监控错误: {e}", address, chain_config['name'])
    
    async def send_discord_notification(self, message: str):
        """发送Discord通知（占位实现）"""
        # TODO: 实现Discord Webhook通知
        # 用户需要在环境变量中设置 DISCORD_WEBHOOK_URL
        webhook_url = os.getenv('DISCORD_WEBHOOK_URL')
        if not webhook_url:
            logging.debug("Discord通知已禁用（未设置DISCORD_WEBHOOK_URL）")
            return
        
        try:
            payload = {
                "content": message,
                "username": "EVM监控机器人"
            }
            
            response = requests.post(webhook_url, json=payload, timeout=10)
            response.raise_for_status()
            logging.debug("Discord通知发送成功")
            
        except Exception as e:
            logging.error(f"Discord通知发送失败: {e}")
    
    async def start_monitoring(self):
        """开始监控"""
        # 验证前置条件
        if not self.addresses:
            print("❌ 没有可监控的地址，请先导入私钥")
            logging.error("没有可监控的地址")
            return
        
        if not self.config.get('chains'):
            print("❌ 没有配置监控链，请重新导入私钥")
            logging.error("没有配置监控链")
            return
            
        if not self.alchemy_api:
            print("❌ API未初始化")
            logging.error("API未初始化")
            return
        
        print(f"✅ 开始监控 {len(self.addresses)} 个地址在 {len(self.config['chains'])} 条链上...")
        print("按 Ctrl+C 停止监控")
        
        self.monitoring_active = True
        logging.info("开始监控...")
        
        try:
            round_count = 0
            while self.monitoring_active:
                round_count += 1
                print(f"\n🔍 第 {round_count} 轮监控开始...")
                
                # 监控所有地址在所有链上的余额
                tasks = []
                
                for address_info in self.addresses:
                    for chain_setting in self.config['chains']:
                        # 获取链配置
                        chain_config = None
                        for chain_name, supported_config in ChainConfig.SUPPORTED_CHAINS.items():
                            if supported_config['chain_id'] == chain_setting['chain_id']:
                                chain_config = supported_config
                                break
                        
                        if chain_config:
                            task = self.monitor_address_chain(address_info, chain_config)
                            tasks.append(task)
                
                # 分批执行监控任务以提高速度
                if tasks:
                    batch_size = 50  # 每批50个任务
                    total_success = 0
                    total_errors = 0
                    
                    for i in range(0, len(tasks), batch_size):
                        batch_tasks = tasks[i:i + batch_size]
                        results = await asyncio.gather(*batch_tasks, return_exceptions=True)
                        
                        # 统计结果
                        batch_success = 0
                        batch_errors = 0
                        for result in results:
                            if isinstance(result, Exception):
                                batch_errors += 1
                            else:
                                batch_success += 1
                        
                        total_success += batch_success
                        total_errors += batch_errors
                        
                        # 批次间短暂暂停
                        if i + batch_size < len(tasks):
                            await asyncio.sleep(0.1)
                    
                    print(f"✅ 第 {round_count} 轮监控完成: {total_success} 成功, {total_errors} 错误")
                
                # 轮询间隔
                monitoring_interval = self.config.get('settings', {}).get('monitoring_interval', 0.1)
                if monitoring_interval > 0:
                    await asyncio.sleep(monitoring_interval)
                
                # 每轮监控后暂停
                round_pause = self.config.get('settings', {}).get('round_pause', 10)
                print(f"⏸️  暂停 {round_pause} 秒后开始下一轮...")
                await asyncio.sleep(round_pause)
                
        except KeyboardInterrupt:
            print("\n⏹️  监控被用户中断")
            logging.info("监控被用户中断")
        except Exception as e:
            print(f"❌ 监控过程中出错: {e}")
            logging.error(f"监控过程中出错: {e}")
        finally:
            self.monitoring_active = False
            print("🛑 监控已停止")
            logging.info("监控已停止")
    
    def stop_monitoring(self):
        """停止监控"""
        self.monitoring_active = False
    
    async def show_interactive_menu(self):
        """显示交互式菜单"""
        while True:
            try:
                print("\n" + "="*50)
                print("EVM多链自动监控转账工具")
                print("="*50)
                print("1. 导入私钥")
                print("2. 开始监控")
                print("3. 退出")
                print("-"*50)
                
                choice = input("请选择操作 (1-3): ").strip()
                
                if choice == "3":
                    print("感谢使用！")
                    break
                elif choice == "1":
                    await self.configure_private_keys()
                elif choice == "2":
                    if not self.addresses:
                        print("❌ 请先导入私钥！")
                        continue
                    if not self.config.get('chains'):
                        print("❌ 配置错误，请重新导入私钥！")
                        continue
                    print("开始监控...")
                    await self.start_monitoring()
                else:
                    print("无效选择，请重试")
                    
            except KeyboardInterrupt:
                print("\n\n程序被中断，正在退出...")
                break
            except Exception as e:
                print(f"菜单操作出错: {e}")
                logging.error(f"菜单操作出错: {e}")
    
    async def configure_private_keys(self):
        """导入私钥"""
        print("\n导入私钥")
        print("请输入私钥（支持一次性粘贴多个私钥，系统会自动提取有效私钥）:")
        print("支持格式:")
        print("- 单个私钥: 0xabc123...def789")
        print("- 多个私钥: 0xabc123...def789,0x123...456")
        print("- 每行一个私钥（支持多行粘贴）")
        print("- 输入 'END' 结束多行输入")
        print("-"*50)

        # 支持多行输入
        lines = []
        print("请输入私钥内容:")
        
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
            # 处理粘贴多行后的EOF
            pass
        except Exception as e:
            print(f"输入错误: {e}")
            return

        private_keys_input = ' '.join(lines)

        if private_keys_input and private_keys_input.strip():
            private_keys = self.extract_private_keys(private_keys_input)
            if private_keys:
                print(f"✅ 提取到 {len(private_keys)} 个有效私钥")

                # 显示对应的地址
                print("\n对应地址:")
                for i, private_key in enumerate(private_keys):
                    try:
                        account = Account.from_key(private_key)
                        print(f"{i+1}. {account.address}")
                    except Exception as e:
                        print(f"{i+1}. 错误: {e}")

                # 询问接收地址
                print("\n请输入接收地址 (所有转账的目标地址):")
                recipient_address = input("接收地址: ").strip()
                
                # 验证地址格式
                if not recipient_address:
                    print("❌ 接收地址不能为空")
                    return
                    
                if not Web3.is_address(recipient_address):
                    print("❌ 无效的以太坊地址格式")
                    return

                try:
                    # 将私钥写入.env
                    joined_keys = ",".join(private_keys)
                    with open('.env', 'w', encoding='utf-8') as f:
                        f.write(f"ALCHEMY_API_KEY=MYr2ZG1P7bxc4F1qVTLIj\n")
                        f.write(f"PRIVATE_KEYS=\"{joined_keys}\"\n")

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

                    # 创建配置 - 只包含确认可用的主要链
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
                                "recipient_address": recipient_address,
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

                    print(f"✅ 私钥导入完成！")
                    print(f"✅ 已配置 {len(self.addresses)} 个地址监控")
                    print(f"✅ 已配置 {len(chains_config)} 条链监控")
                    print(f"✅ 接收地址: {recipient_address}")
                    
                except Exception as e:
                    print(f"❌ 保存配置失败: {e}")
                    logging.error(f"保存配置失败: {e}")
            else:
                print("❌ 未找到有效私钥，请检查输入格式")
        else:
            print("❌ 未输入任何内容")
    
async def main():
    """主函数"""
    print("🚀 正在初始化EVM多链监控工具...")
    
    app = MonitoringApp()
    
    try:
        await app.initialize()
        print("✅ 初始化完成！")
        
        # 显示状态信息
        print(f"📊 支持 {len(ChainConfig.SUPPORTED_CHAINS)} 条区块链")
        if app.addresses:
            print(f"📝 已加载 {len(app.addresses)} 个监控地址")
        else:
            print("📝 未加载监控地址，请先导入私钥")
        
        # 进入交互式菜单
        await app.show_interactive_menu()
        
    except Exception as e:
        print(f"❌ 初始化失败: {e}")
        logging.error(f"初始化失败: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    # 设置异步事件循环策略（Windows兼容性）
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    exit_code = asyncio.run(main())
    exit(exit_code)
