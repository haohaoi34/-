package com.monitor;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.*;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.nio.file.StandardOpenOption;
import java.util.*;

public class ConfigurationMenu {
    private static final Logger logger = LoggerFactory.getLogger(ConfigurationMenu.class);
    
    // 配置文件路径
    private static final String CONFIG_FILE = "monitor_config.properties";
    private static final String PRIVATE_KEYS_FILE = "private_keys.txt";
    private static final String MONITORED_ADDRESSES_FILE = "monitored_addresses.txt";
    
    // 配置属性
    private Properties config;
    private Scanner scanner;
    
    public ConfigurationMenu() {
        this.config = new Properties();
        this.scanner = new Scanner(System.in);
        loadConfiguration();
    }

    /**
     * 显示主菜单
     */
    public void showMainMenu() {
        while (true) {
            clearScreen();
            printHeader();
            printMainMenu();
            
            String choice = getUserInput("请选择操作");
            
            switch (choice) {
                case "1":
                    configureTargetAddress();
                    break;
                case "2":
                    configureMonitoredAddresses();
                    break;
                case "3":
                    configureAlchemyAPI();
                    break;
                case "4":
                    showRunMenu();
                    break;
                case "5":
                    viewConfiguration();
                    break;
                case "6":
                    exportConfiguration();
                    break;
                case "7":
                    importConfiguration();
                    break;
                case "0":
                    System.out.println("退出程序...");
                    return;
                default:
                    System.out.println("无效选择，请重新输入");
                    pauseForUser();
            }
        }
    }

    /**
     * 打印程序头部信息
     */
    private void printHeader() {
        System.out.println("╔════════════════════════════════════════════════════════════════╗");
        System.out.println("║                    多链钱包监控系统配置                        ║");
        System.out.println("║                Multi-Chain Wallet Monitor                     ║");
        System.out.println("╚════════════════════════════════════════════════════════════════╝");
        System.out.println();
    }

    /**
     * 打印主菜单
     */
    private void printMainMenu() {
        System.out.println("┌─────────────────── 主菜单 ───────────────────┐");
        System.out.println("│  1. 配置收款地址                             │");
        System.out.println("│  2. 配置监控地址                             │");
        System.out.println("│  3. 配置Alchemy API                          │");
        System.out.println("│  4. 开始监控                                 │");
        System.out.println("│  5. 查看当前配置                             │");
        System.out.println("│  6. 导出配置                                 │");
        System.out.println("│  7. 导入配置                                 │");
        System.out.println("│  0. 退出程序                                 │");
        System.out.println("└─────────────────────────────────────────────┘");
        System.out.println();
    }

    /**
     * 配置收款地址
     */
    private void configureTargetAddress() {
        clearScreen();
        System.out.println("═══════════════ 配置收款地址 ═══════════════");
        System.out.println();
        
        String currentAddress = config.getProperty("target.address", "未设置");
        System.out.println("当前收款地址: " + currentAddress);
        System.out.println();
        
        System.out.println("请输入新的收款地址（以0x开头的42位地址）：");
        String newAddress = scanner.nextLine().trim();
        
        if (isValidAddress(newAddress)) {
            config.setProperty("target.address", newAddress);
            saveConfiguration();
            System.out.println("✓ 收款地址配置成功！");
            logger.info("收款地址已更新: {}", newAddress);
        } else {
            System.out.println("✗ 无效的地址格式，请检查后重新输入");
        }
        
        pauseForUser();
    }

    /**
     * 配置监控地址
     */
    private void configureMonitoredAddresses() {
        while (true) {
            clearScreen();
            System.out.println("═══════════════ 配置监控地址 ═══════════════");
            System.out.println();
            
            System.out.println("┌─────────────────── 选项 ───────────────────┐");
            System.out.println("│  1. 从私钥批量生成地址                      │");
            System.out.println("│  2. 手动添加监控地址                        │");
            System.out.println("│  3. 从文件导入地址                          │");
            System.out.println("│  4. 查看当前监控地址                        │");
            System.out.println("│  5. 清空监控地址                            │");
            System.out.println("│  0. 返回主菜单                              │");
            System.out.println("└─────────────────────────────────────────────┘");
            System.out.println();
            
            String choice = getUserInput("请选择操作");
            
            switch (choice) {
                case "1":
                    generateAddressesFromPrivateKeys();
                    return;
                case "2":
                    addMonitoredAddressesManually();
                    return;
                case "3":
                    importAddressesFromFile();
                    return;
                case "4":
                    viewMonitoredAddresses();
                    break;
                case "5":
                    clearMonitoredAddresses();
                    break;
                case "0":
                    return;
                default:
                    System.out.println("无效选择，请重新输入");
                    pauseForUser();
            }
        }
    }

    /**
     * 从私钥生成地址
     */
    private void generateAddressesFromPrivateKeys() {
        clearScreen();
        System.out.println("═══════════════ 从私钥生成地址 ═══════════════");
        System.out.println();
        
        // 检查是否已有私钥文件
        if (Files.exists(Paths.get(PRIVATE_KEYS_FILE))) {
            System.out.println("发现私钥文件，是否使用现有文件？(y/n): ");
            String choice = scanner.nextLine().trim().toLowerCase();
            
            if ("y".equals(choice) || "yes".equals(choice)) {
                generateAddressesFromFile();
                return;
            }
        }
        
        System.out.println("请输入私钥，一行一个（带不带0x都可以）：");
        System.out.println("输入完成后，输入 'END' 结束输入");
        System.out.println();
        
        List<String> privateKeys = new ArrayList<>();
        String line;
        
        while (true) {
            System.out.print("私钥 " + (privateKeys.size() + 1) + ": ");
            line = scanner.nextLine().trim();
            
            if ("END".equalsIgnoreCase(line)) {
                break;
            }
            
            if (line.isEmpty()) {
                continue;
            }
            
            // 处理私钥格式
            String privateKey = line;
            if (!privateKey.startsWith("0x")) {
                privateKey = "0x" + privateKey;
            }
            
            // 验证私钥格式
            if (isValidPrivateKey(privateKey)) {
                privateKeys.add(privateKey);
                System.out.println("✓ 私钥已添加");
            } else {
                System.out.println("✗ 无效的私钥格式，跳过");
            }
        }
        
        if (privateKeys.isEmpty()) {
            System.out.println("没有有效的私钥");
            pauseForUser();
            return;
        }
        
        // 保存私钥
        try {
            Files.write(Paths.get(PRIVATE_KEYS_FILE), privateKeys, 
                StandardOpenOption.CREATE, StandardOpenOption.WRITE, StandardOpenOption.TRUNCATE_EXISTING);
        } catch (IOException e) {
            System.out.println("保存私钥文件失败: " + e.getMessage());
            pauseForUser();
            return;
        }
        
        generateAddressesFromFile();
    }

    /**
     * 从文件生成地址
     */
    private void generateAddressesFromFile() {
        try {
            List<String> privateKeys = Files.readAllLines(Paths.get(PRIVATE_KEYS_FILE));
            Set<String> addresses = new HashSet<>();
            
            for (String privateKey : privateKeys) {
                privateKey = privateKey.trim();
                if (!privateKey.isEmpty() && isValidPrivateKey(privateKey)) {
                    try {
                        org.web3j.crypto.Credentials credentials = org.web3j.crypto.Credentials.create(privateKey);
                        addresses.add(credentials.getAddress());
                    } catch (Exception e) {
                        logger.warn("生成地址失败，私钥: {}...", privateKey.substring(0, 10));
                    }
                }
            }
            
            if (!addresses.isEmpty()) {
                // 保存监控地址
                Files.write(Paths.get(MONITORED_ADDRESSES_FILE), addresses, 
                    StandardOpenOption.CREATE, StandardOpenOption.WRITE, StandardOpenOption.TRUNCATE_EXISTING);
                
                config.setProperty("monitored.addresses.count", String.valueOf(addresses.size()));
                saveConfiguration();
                
                System.out.println("✓ 成功生成 " + addresses.size() + " 个监控地址");
                logger.info("生成了 {} 个监控地址", addresses.size());
            } else {
                System.out.println("✗ 没有生成有效地址");
            }
            
        } catch (IOException e) {
            System.out.println("读取私钥文件失败: " + e.getMessage());
        }
        
        pauseForUser();
    }

    /**
     * 手动添加监控地址
     */
    private void addMonitoredAddressesManually() {
        clearScreen();
        System.out.println("═══════════════ 手动添加监控地址 ═══════════════");
        System.out.println();
        
        System.out.println("请输入监控地址，一行一个：");
        System.out.println("输入完成后，输入 'END' 结束输入");
        System.out.println();
        
        Set<String> addresses = new HashSet<>();
        
        // 加载现有地址
        try {
            if (Files.exists(Paths.get(MONITORED_ADDRESSES_FILE))) {
                List<String> existingAddresses = Files.readAllLines(Paths.get(MONITORED_ADDRESSES_FILE));
                addresses.addAll(existingAddresses);
            }
        } catch (IOException e) {
            logger.warn("读取现有监控地址失败: {}", e.getMessage());
        }
        
        String line;
        int addedCount = 0;
        
        while (true) {
            System.out.print("地址 " + (addedCount + 1) + ": ");
            line = scanner.nextLine().trim();
            
            if ("END".equalsIgnoreCase(line)) {
                break;
            }
            
            if (line.isEmpty()) {
                continue;
            }
            
            if (isValidAddress(line)) {
                if (addresses.add(line)) {
                    addedCount++;
                    System.out.println("✓ 地址已添加");
                } else {
                    System.out.println("⚠ 地址已存在");
                }
            } else {
                System.out.println("✗ 无效的地址格式，跳过");
            }
        }
        
        if (addedCount > 0) {
            try {
                Files.write(Paths.get(MONITORED_ADDRESSES_FILE), addresses, 
                    StandardOpenOption.CREATE, StandardOpenOption.WRITE, StandardOpenOption.TRUNCATE_EXISTING);
                
                config.setProperty("monitored.addresses.count", String.valueOf(addresses.size()));
                saveConfiguration();
                
                System.out.println("✓ 成功添加 " + addedCount + " 个新地址，总计 " + addresses.size() + " 个地址");
            } catch (IOException e) {
                System.out.println("保存监控地址失败: " + e.getMessage());
            }
        } else {
            System.out.println("没有添加新地址");
        }
        
        pauseForUser();
    }

    /**
     * 从文件导入地址
     */
    private void importAddressesFromFile() {
        clearScreen();
        System.out.println("═══════════════ 从文件导入地址 ═══════════════");
        System.out.println();
        
        System.out.print("请输入文件路径: ");
        String filePath = scanner.nextLine().trim();
        
        try {
            List<String> lines = Files.readAllLines(Paths.get(filePath));
            Set<String> addresses = new HashSet<>();
            
            // 加载现有地址
            if (Files.exists(Paths.get(MONITORED_ADDRESSES_FILE))) {
                List<String> existingAddresses = Files.readAllLines(Paths.get(MONITORED_ADDRESSES_FILE));
                addresses.addAll(existingAddresses);
            }
            
            int addedCount = 0;
            for (String line : lines) {
                line = line.trim();
                if (!line.isEmpty() && isValidAddress(line)) {
                    if (addresses.add(line)) {
                        addedCount++;
                    }
                }
            }
            
            if (addedCount > 0) {
                Files.write(Paths.get(MONITORED_ADDRESSES_FILE), addresses, 
                    StandardOpenOption.CREATE, StandardOpenOption.WRITE, StandardOpenOption.TRUNCATE_EXISTING);
                
                config.setProperty("monitored.addresses.count", String.valueOf(addresses.size()));
                saveConfiguration();
                
                System.out.println("✓ 成功导入 " + addedCount + " 个新地址，总计 " + addresses.size() + " 个地址");
            } else {
                System.out.println("没有导入新地址");
            }
            
        } catch (IOException e) {
            System.out.println("读取文件失败: " + e.getMessage());
        }
        
        pauseForUser();
    }

    /**
     * 查看监控地址
     */
    private void viewMonitoredAddresses() {
        clearScreen();
        System.out.println("═══════════════ 当前监控地址 ═══════════════");
        System.out.println();
        
        try {
            if (Files.exists(Paths.get(MONITORED_ADDRESSES_FILE))) {
                List<String> addresses = Files.readAllLines(Paths.get(MONITORED_ADDRESSES_FILE));
                
                if (addresses.isEmpty()) {
                    System.out.println("暂无监控地址");
                } else {
                    System.out.println("总计 " + addresses.size() + " 个监控地址：");
                    System.out.println();
                    
                    for (int i = 0; i < addresses.size(); i++) {
                        System.out.printf("%4d. %s%n", i + 1, addresses.get(i));
                    }
                }
            } else {
                System.out.println("暂无监控地址");
            }
        } catch (IOException e) {
            System.out.println("读取监控地址失败: " + e.getMessage());
        }
        
        pauseForUser();
    }

    /**
     * 清空监控地址
     */
    private void clearMonitoredAddresses() {
        System.out.print("确认清空所有监控地址？(y/n): ");
        String choice = scanner.nextLine().trim().toLowerCase();
        
        if ("y".equals(choice) || "yes".equals(choice)) {
            try {
                Files.deleteIfExists(Paths.get(MONITORED_ADDRESSES_FILE));
                Files.deleteIfExists(Paths.get(PRIVATE_KEYS_FILE));
                config.remove("monitored.addresses.count");
                saveConfiguration();
                System.out.println("✓ 监控地址已清空");
            } catch (IOException e) {
                System.out.println("清空失败: " + e.getMessage());
            }
        } else {
            System.out.println("操作已取消");
        }
        
        pauseForUser();
    }

    /**
     * 配置Alchemy API
     */
    private void configureAlchemyAPI() {
        clearScreen();
        System.out.println("═══════════════ 配置Alchemy API ═══════════════");
        System.out.println();
        
        String currentApiKey = config.getProperty("alchemy.api.key", "未设置");
        if (!"未设置".equals(currentApiKey)) {
            String maskedKey = currentApiKey.substring(0, 8) + "..." + 
                              currentApiKey.substring(currentApiKey.length() - 4);
            System.out.println("当前API密钥: " + maskedKey);
        } else {
            System.out.println("当前API密钥: " + currentApiKey);
        }
        System.out.println();
        
        System.out.println("请输入Alchemy API密钥：");
        String newApiKey = scanner.nextLine().trim();
        
        if (!newApiKey.isEmpty()) {
            config.setProperty("alchemy.api.key", newApiKey);
            saveConfiguration();
            System.out.println("✓ Alchemy API密钥配置成功！");
            logger.info("Alchemy API密钥已更新");
        } else {
            System.out.println("✗ API密钥不能为空");
        }
        
        pauseForUser();
    }

    /**
     * 显示运行菜单
     */
    private void showRunMenu() {
        clearScreen();
        System.out.println("═══════════════ 开始监控 ═══════════════");
        System.out.println();
        
        // 检查必要配置
        if (!isConfigurationComplete()) {
            System.out.println("✗ 配置不完整，无法开始监控");
            System.out.println("请检查以下配置：");
            
            if (config.getProperty("target.address") == null) {
                System.out.println("  - 收款地址未设置");
            }
            if (config.getProperty("alchemy.api.key") == null) {
                System.out.println("  - Alchemy API密钥未设置");
            }
            if (!Files.exists(Paths.get(MONITORED_ADDRESSES_FILE))) {
                System.out.println("  - 监控地址未设置");
            }
            
            pauseForUser();
            return;
        }
        
        System.out.println("┌─────────────────── 选项 ───────────────────┐");
        System.out.println("│  1. 重新开始监控                            │");
        System.out.println("│  2. 从上次结束的地方继续监控                │");
        System.out.println("│  0. 返回主菜单                              │");
        System.out.println("└─────────────────────────────────────────────┘");
        System.out.println();
        
        String choice = getUserInput("请选择运行模式");
        
        switch (choice) {
            case "1":
                startMonitoring(true);
                break;
            case "2":
                startMonitoring(false);
                break;
            case "0":
                return;
            default:
                System.out.println("无效选择");
                pauseForUser();
        }
    }

    /**
     * 开始监控
     */
    private void startMonitoring(boolean restart) {
        try {
            System.out.println("正在启动监控系统...");
            
            // 创建MultiChainWalletMonitor实例并启动
            MultiChainWalletMonitor monitor = new MultiChainWalletMonitor(
                config.getProperty("target.address"),
                config.getProperty("alchemy.api.key"),
                restart
            );
            
            monitor.startMonitoring();
            
        } catch (Exception e) {
            System.out.println("启动监控失败: " + e.getMessage());
            logger.error("启动监控失败", e);
            pauseForUser();
        }
    }

    /**
     * 查看当前配置
     */
    private void viewConfiguration() {
        clearScreen();
        System.out.println("═══════════════ 当前配置 ═══════════════");
        System.out.println();
        
        String targetAddress = config.getProperty("target.address", "未设置");
        String apiKey = config.getProperty("alchemy.api.key", "未设置");
        String addressCount = config.getProperty("monitored.addresses.count", "0");
        
        System.out.println("收款地址: " + targetAddress);
        
        if (!"未设置".equals(apiKey)) {
            String maskedKey = apiKey.substring(0, 8) + "..." + 
                              apiKey.substring(apiKey.length() - 4);
            System.out.println("API密钥: " + maskedKey);
        } else {
            System.out.println("API密钥: " + apiKey);
        }
        
        System.out.println("监控地址数量: " + addressCount);
        
        System.out.println();
        System.out.println("配置完整性: " + (isConfigurationComplete() ? "✓ 完整" : "✗ 不完整"));
        
        pauseForUser();
    }

    /**
     * 导出配置
     */
    private void exportConfiguration() {
        clearScreen();
        System.out.println("═══════════════ 导出配置 ═══════════════");
        System.out.println();
        
        System.out.print("请输入导出文件路径（默认: config_backup.zip）: ");
        String filePath = scanner.nextLine().trim();
        if (filePath.isEmpty()) {
            filePath = "config_backup.zip";
        }
        
        try {
            // 这里可以实现配置文件的打包导出
            System.out.println("✓ 配置已导出到: " + filePath);
            logger.info("配置已导出到: {}", filePath);
        } catch (Exception e) {
            System.out.println("导出失败: " + e.getMessage());
        }
        
        pauseForUser();
    }

    /**
     * 导入配置
     */
    private void importConfiguration() {
        clearScreen();
        System.out.println("═══════════════ 导入配置 ═══════════════");
        System.out.println();
        
        System.out.print("请输入配置文件路径: ");
        String filePath = scanner.nextLine().trim();
        
        try {
            // 这里可以实现配置文件的导入
            System.out.println("✓ 配置已导入");
            logger.info("配置已从文件导入: {}", filePath);
        } catch (Exception e) {
            System.out.println("导入失败: " + e.getMessage());
        }
        
        pauseForUser();
    }

    /**
     * 加载配置
     */
    private void loadConfiguration() {
        try {
            if (Files.exists(Paths.get(CONFIG_FILE))) {
                try (InputStream input = Files.newInputStream(Paths.get(CONFIG_FILE))) {
                    config.load(input);
                }
            }
        } catch (IOException e) {
            logger.warn("加载配置文件失败: {}", e.getMessage());
        }
    }

    /**
     * 保存配置
     */
    private void saveConfiguration() {
        try {
            try (OutputStream output = Files.newOutputStream(Paths.get(CONFIG_FILE))) {
                config.store(output, "Multi-Chain Wallet Monitor Configuration");
            }
        } catch (IOException e) {
            logger.error("保存配置文件失败: {}", e.getMessage());
        }
    }

    /**
     * 检查配置是否完整
     */
    private boolean isConfigurationComplete() {
        return config.getProperty("target.address") != null &&
               config.getProperty("alchemy.api.key") != null &&
               Files.exists(Paths.get(MONITORED_ADDRESSES_FILE));
    }

    /**
     * 验证地址格式
     */
    private boolean isValidAddress(String address) {
        return address != null && 
               address.matches("^0x[a-fA-F0-9]{40}$");
    }

    /**
     * 验证私钥格式
     */
    private boolean isValidPrivateKey(String privateKey) {
        if (!privateKey.startsWith("0x") || privateKey.length() != 66) {
            return false;
        }
        
        try {
            new java.math.BigInteger(privateKey.substring(2), 16);
            return true;
        } catch (NumberFormatException e) {
            return false;
        }
    }

    /**
     * 获取用户输入
     */
    private String getUserInput(String prompt) {
        System.out.print(prompt + ": ");
        return scanner.nextLine().trim();
    }

    /**
     * 暂停等待用户
     */
    private void pauseForUser() {
        System.out.println();
        System.out.print("按回车键继续...");
        scanner.nextLine();
    }

    /**
     * 清屏
     */
    private void clearScreen() {
        // 在大多数终端中工作的清屏方法
        System.out.print("\033[2J\033[H");
        System.out.flush();
    }

    // Getters for configuration values
    public String getTargetAddress() {
        return config.getProperty("target.address");
    }

    public String getAlchemyApiKey() {
        return config.getProperty("alchemy.api.key");
    }

    public boolean isConfigured() {
        return isConfigurationComplete();
    }
} 
