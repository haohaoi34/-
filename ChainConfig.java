package com.monitor;

import java.util.*;

public class ChainConfig {
    private final String name;
    private final String rpcUrl;
    private final long chainId;
    private final String symbol;
    private final int decimals;
    private final long gasLimit;
    private final String gasPrice;
    private final boolean isEVM;

    public ChainConfig(String name, String rpcUrl, long chainId, String symbol, int decimals, long gasLimit, String gasPrice, boolean isEVM) {
        this.name = name;
        this.rpcUrl = rpcUrl;
        this.chainId = chainId;
        this.symbol = symbol;
        this.decimals = decimals;
        this.gasLimit = gasLimit;
        this.gasPrice = gasPrice;
        this.isEVM = isEVM;
    }

    // Getters
    public String getName() { return name; }
    public String getRpcUrl() { return rpcUrl; }
    public long getChainId() { return chainId; }
    public String getSymbol() { return symbol; }
    public int getDecimals() { return decimals; }
    public long getGasLimit() { return gasLimit; }
    public String getGasPrice() { return gasPrice; }
    public boolean isEVM() { return isEVM; }

    // 支持的区块链网络配置
    public static Map<String, ChainConfig> getSupportedChains(String alchemyApiKey) {
        Map<String, ChainConfig> chains = new HashMap<>();
        
        // ===================
        // 主要 EVM 链
        // ===================
        
        // Ethereum Mainnet
        chains.put("eth-mainnet", new ChainConfig(
            "Ethereum Mainnet",
            "https://eth-mainnet.g.alchemy.com/v2/" + alchemyApiKey,
            1L,
            "ETH",
            18,
            21000L,
            "20000000000", // 20 Gwei
            true
        ));

        // Polygon
        chains.put("polygon-mainnet", new ChainConfig(
            "Polygon Mainnet",
            "https://polygon-mainnet.g.alchemy.com/v2/" + alchemyApiKey,
            137L,
            "MATIC",
            18,
            21000L,
            "30000000000", // 30 Gwei
            true
        ));

        // Arbitrum One
        chains.put("arb-mainnet", new ChainConfig(
            "Arbitrum One",
            "https://arb-mainnet.g.alchemy.com/v2/" + alchemyApiKey,
            42161L,
            "ETH",
            18,
            800000L,
            "100000000", // 0.1 Gwei
            true
        ));

        // Arbitrum Nova
        chains.put("arb-nova", new ChainConfig(
            "Arbitrum Nova",
            "https://arb-nova.g.alchemy.com/v2/" + alchemyApiKey,
            42170L,
            "ETH",
            18,
            800000L,
            "100000000",
            true
        ));

        // Optimism
        chains.put("opt-mainnet", new ChainConfig(
            "Optimism Mainnet",
            "https://opt-mainnet.g.alchemy.com/v2/" + alchemyApiKey,
            10L,
            "ETH",
            18,
            21000L,
            "1000000", // 0.001 Gwei
            true
        ));

        // Base
        chains.put("base-mainnet", new ChainConfig(
            "Base Mainnet",
            "https://base-mainnet.g.alchemy.com/v2/" + alchemyApiKey,
            8453L,
            "ETH",
            18,
            21000L,
            "1000000000", // 1 Gwei
            true
        ));

        // Polygon zkEVM
        chains.put("polygonzkevm-mainnet", new ChainConfig(
            "Polygon zkEVM",
            "https://polygonzkevm-mainnet.g.alchemy.com/v2/" + alchemyApiKey,
            1101L,
            "ETH",
            18,
            21000L,
            "1000000000",
            true
        ));

        // Avalanche C-Chain
        chains.put("avax-mainnet", new ChainConfig(
            "Avalanche C-Chain",
            "https://avax-mainnet.g.alchemy.com/v2/" + alchemyApiKey,
            43114L,
            "AVAX",
            18,
            21000L,
            "25000000000", // 25 Gwei
            true
        ));

        // BNB Smart Chain
        chains.put("bnb-mainnet", new ChainConfig(
            "BNB Smart Chain",
            "https://bnb-mainnet.g.alchemy.com/v2/" + alchemyApiKey,
            56L,
            "BNB",
            18,
            21000L,
            "5000000000", // 5 Gwei
            true
        ));

        // ===================
        // Layer 2 和其他 EVM 链
        // ===================

        // Blast
        chains.put("blast-mainnet", new ChainConfig(
            "Blast Mainnet",
            "https://blast-mainnet.g.alchemy.com/v2/" + alchemyApiKey,
            81457L,
            "ETH",
            18,
            21000L,
            "1000000000",
            true
        ));

        // Scroll
        chains.put("scroll-mainnet", new ChainConfig(
            "Scroll Mainnet",
            "https://scroll-mainnet.g.alchemy.com/v2/" + alchemyApiKey,
            534352L,
            "ETH",
            18,
            21000L,
            "1000000000",
            true
        ));

        // Linea
        chains.put("linea-mainnet", new ChainConfig(
            "Linea Mainnet",
            "https://linea-mainnet.g.alchemy.com/v2/" + alchemyApiKey,
            59144L,
            "ETH",
            18,
            21000L,
            "1000000000",
            true
        ));

        // Mantle
        chains.put("mantle-mainnet", new ChainConfig(
            "Mantle Mainnet",
            "https://mantle-mainnet.g.alchemy.com/v2/" + alchemyApiKey,
            5000L,
            "MNT",
            18,
            21000L,
            "1000000000",
            true
        ));

        // Celo
        chains.put("celo-mainnet", new ChainConfig(
            "Celo Mainnet",
            "https://celo-mainnet.g.alchemy.com/v2/" + alchemyApiKey,
            42220L,
            "CELO",
            18,
            21000L,
            "5000000000",
            true
        ));

        // zkSync Era
        chains.put("zksync-mainnet", new ChainConfig(
            "zkSync Era Mainnet",
            "https://zksync-mainnet.g.alchemy.com/v2/" + alchemyApiKey,
            324L,
            "ETH",
            18,
            21000L,
            "1000000000",
            true
        ));

        // Gnosis Chain
        chains.put("gnosis-mainnet", new ChainConfig(
            "Gnosis Chain",
            "https://gnosis-mainnet.g.alchemy.com/v2/" + alchemyApiKey,
            100L,
            "XDAI",
            18,
            21000L,
            "2000000000",
            true
        ));

        // Metis
        chains.put("metis-mainnet", new ChainConfig(
            "Metis Mainnet",
            "https://metis-mainnet.g.alchemy.com/v2/" + alchemyApiKey,
            1088L,
            "METIS",
            18,
            21000L,
            "15000000000",
            true
        ));

        // ===================
        // 新兴 EVM 链
        // ===================

        // Sonic
        chains.put("sonic-mainnet", new ChainConfig(
            "Sonic Mainnet",
            "https://sonic-mainnet.g.alchemy.com/v2/" + alchemyApiKey,
            146L,
            "S",
            18,
            21000L,
            "1000000000",
            true
        ));

        // ZetaChain
        chains.put("zetachain-mainnet", new ChainConfig(
            "ZetaChain Mainnet",
            "https://zetachain-mainnet.g.alchemy.com/v2/" + alchemyApiKey,
            7000L,
            "ZETA",
            18,
            21000L,
            "20000000000",
            true
        ));

        // Berachain
        chains.put("berachain-mainnet", new ChainConfig(
            "Berachain Mainnet",
            "https://berachain-mainnet.g.alchemy.com/v2/" + alchemyApiKey,
            80085L,
            "BERA",
            18,
            21000L,
            "1000000000",
            true
        ));

        // CrossFi
        chains.put("crossfi-mainnet", new ChainConfig(
            "CrossFi Mainnet",
            "https://crossfi-mainnet.g.alchemy.com/v2/" + alchemyApiKey,
            4157L,
            "XFI",
            18,
            21000L,
            "1000000000",
            true
        ));

        // Soneium
        chains.put("soneium-mainnet", new ChainConfig(
            "Soneium Mainnet",
            "https://soneium-mainnet.g.alchemy.com/v2/" + alchemyApiKey,
            1946L,
            "ETH",
            18,
            21000L,
            "1000000000",
            true
        ));

        // Unichain
        chains.put("unichain-mainnet", new ChainConfig(
            "Unichain Mainnet",
            "https://unichain-mainnet.g.alchemy.com/v2/" + alchemyApiKey,
            1301L,
            "ETH",
            18,
            21000L,
            "1000000000",
            true
        ));

        // World Chain
        chains.put("worldchain-mainnet", new ChainConfig(
            "World Chain Mainnet",
            "https://worldchain-mainnet.g.alchemy.com/v2/" + alchemyApiKey,
            480L,
            "WLD",
            18,
            21000L,
            "1000000000",
            true
        ));

        // Rootstock
        chains.put("rootstock-mainnet", new ChainConfig(
            "Rootstock Mainnet",
            "https://rootstock-mainnet.g.alchemy.com/v2/" + alchemyApiKey,
            30L,
            "RBTC",
            18,
            21000L,
            "1000000000",
            true
        ));

        // Shape
        chains.put("shape-mainnet", new ChainConfig(
            "Shape Mainnet",
            "https://shape-mainnet.g.alchemy.com/v2/" + alchemyApiKey,
            360L,
            "ETH",
            18,
            21000L,
            "1000000000",
            true
        ));

        // Apechain
        chains.put("apechain-mainnet", new ChainConfig(
            "ApeChain Mainnet",
            "https://apechain-mainnet.g.alchemy.com/v2/" + alchemyApiKey,
            33139L,
            "APE",
            18,
            21000L,
            "1000000000",
            true
        ));

        // Geist
        chains.put("geist-mainnet", new ChainConfig(
            "Geist Mainnet",
            "https://geist-mainnet.g.alchemy.com/v2/" + alchemyApiKey,
            63157L,
            "GEIST",
            18,
            21000L,
            "1000000000",
            true
        ));

        // Lens
        chains.put("lens-mainnet", new ChainConfig(
            "Lens Mainnet",
            "https://lens-mainnet.g.alchemy.com/v2/" + alchemyApiKey,
            7777L,
            "GRASS",
            18,
            21000L,
            "1000000000",
            true
        ));

        // Abstract
        chains.put("abstract-mainnet", new ChainConfig(
            "Abstract Mainnet",
            "https://abstract-mainnet.g.alchemy.com/v2/" + alchemyApiKey,
            11124L,
            "ETH",
            18,
            21000L,
            "1000000000",
            true
        ));

        // opBNB
        chains.put("opbnb-mainnet", new ChainConfig(
            "opBNB Mainnet",
            "https://opbnb-mainnet.g.alchemy.com/v2/" + alchemyApiKey,
            204L,
            "BNB",
            18,
            21000L,
            "1000000000",
            true
        ));

        // Ink
        chains.put("ink-mainnet", new ChainConfig(
            "Ink Mainnet",
            "https://ink-mainnet.g.alchemy.com/v2/" + alchemyApiKey,
            57073L,
            "ETH",
            18,
            21000L,
            "1000000000",
            true
        ));

        // Lumia
        chains.put("lumia-mainnet", new ChainConfig(
            "Lumia Mainnet",
            "https://lumia-mainnet.g.alchemy.com/v2/" + alchemyApiKey,
            994873L,
            "LUMIA",
            18,
            21000L,
            "1000000000",
            true
        ));

        // Superseed
        chains.put("superseed-mainnet", new ChainConfig(
            "Superseed Mainnet",
            "https://superseed-mainnet.g.alchemy.com/v2/" + alchemyApiKey,
            5330L,
            "ETH",
            18,
            21000L,
            "1000000000",
            true
        ));

        // Anime
        chains.put("anime-mainnet", new ChainConfig(
            "Anime Mainnet",
            "https://anime-mainnet.g.alchemy.com/v2/" + alchemyApiKey,
            11501L,
            "ANIME",
            18,
            21000L,
            "1000000000",
            true
        ));

        // Story
        chains.put("story-mainnet", new ChainConfig(
            "Story Mainnet",
            "https://story-mainnet.g.alchemy.com/v2/" + alchemyApiKey,
            1513L,
            "IP",
            18,
            21000L,
            "1000000000",
            true
        ));

        // Botanix
        chains.put("botanix-mainnet", new ChainConfig(
            "Botanix Mainnet",
            "https://botanix-mainnet.g.alchemy.com/v2/" + alchemyApiKey,
            3636L,
            "BTC",
            8,
            21000L,
            "1000000000",
            true
        ));

        // HyperEVM
        chains.put("hyperevm-mainnet", new ChainConfig(
            "HyperEVM Mainnet",
            "https://hyperevm-mainnet.g.alchemy.com/v2/" + alchemyApiKey,
            998899L,
            "ETH",
            18,
            21000L,
            "1000000000",
            true
        ));

        // ===================
        // 自定义链 - t3rn
        // ===================
        
        chains.put("t3rn-mainnet", new ChainConfig(
            "t3rn Mainnet",
            "https://t3rn.calderachain.xyz/http",
            819L,
            "TRN",
            18,
            21000L,
            "1000000000",
            true
        ));

        // ===================
        // 非 EVM 链
        // ===================

        // Solana (使用不同的API格式)
        chains.put("solana-mainnet", new ChainConfig(
            "Solana Mainnet",
            "https://solana-mainnet.g.alchemy.com/v2/" + alchemyApiKey,
            0L, // Solana doesn't use chainId
            "SOL",
            9,
            0L,
            "0",
            false
        ));

        // Starknet
        chains.put("starknet-mainnet", new ChainConfig(
            "Starknet Mainnet",
            "https://starknet-mainnet.g.alchemy.com/v2/" + alchemyApiKey,
            0L,
            "ETH",
            18,
            21000L,
            "1000000000",
            false
        ));

        return chains;
    }

    @Override
    public String toString() {
        return String.format("ChainConfig{name='%s', chainId=%d, symbol='%s', isEVM=%s}", 
            name, chainId, symbol, isEVM);
    }
} 
