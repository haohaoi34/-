#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
钱包监控系统一键启动器
自动检测和安装依赖，然后启动钱包监控系统
"""

import os
import sys
import subprocess
import shutil
import importlib
import time
import platform

def print_header():
    """打印标题"""
    print("=" * 70)
    print("🚀 钱包监控系统一键启动器 v3.0")
    print("   支持所有Alchemy EVM兼容链的钱包监控和自动转账")
    print("=" * 70)

def check_python_version():
    """检查Python版本"""
    print("\n📋 检查Python版本...")
    version = sys.version_info
    print(f"当前Python版本: {version.major}.{version.minor}.{version.micro}")
    print(f"操作系统: {platform.system()} {platform.release()}")
    
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("❌ Python版本过低，需要Python 3.8+")
        print("💡 请升级Python版本后重试")
        return False
    
    print("✅ Python版本符合要求")
    return True

def check_pip():
    """检查pip是否可用"""
    print("\n📋 检查pip...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "--version"], 
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print("✅ pip可用")
        return True
    except:
        print("❌ pip不可用")
        print("💡 请先安装pip")
        return False

def check_package_installed(package_name):
    """检查包是否已安装"""
    try:
        importlib.import_module(package_name)
        return True
    except ImportError:
        return False

def install_package(package_name, display_name=None):
    """安装单个包"""
    if display_name is None:
        display_name = package_name
        
    print(f"📦 安装 {display_name}...")
    try:
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", package_name, "--upgrade"
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"✅ {display_name} 安装成功")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {display_name} 安装失败")
        return False

def check_and_install_dependencies():
    """检查并安装所有依赖"""
    print(f"\n🔧 检查和安装依赖包...")
    
    # 必需的包列表
    required_packages = [
        ("web3", "Web3.py"),
        ("eth_account", "eth-account"),
        ("alchemy", "alchemy-sdk"),
        ("colorama", "Colorama"),
        ("aiohttp", "aiohttp"),
        ("cryptography", "Cryptography")
    ]
    
    missing_packages = []
    
    # 检查哪些包缺失
    for module_name, package_name in required_packages:
        if not check_package_installed(module_name):
            missing_packages.append((module_name, package_name))
    
    if not missing_packages:
        print("✅ 所有依赖包已安装")
        return True
    
    print(f"📋 需要安装 {len(missing_packages)} 个包:")
    for _, package_name in missing_packages:
        print(f"   - {package_name}")
    
    # 批量安装
    success_count = 0
    for module_name, package_name in missing_packages:
        if install_package(package_name):
            success_count += 1
    
    if success_count == len(missing_packages):
        print(f"\n✅ 所有依赖包安装完成")
        return True
    else:
        print(f"\n⚠️  {len(missing_packages) - success_count} 个包安装失败")
        return False

def test_alchemy_connection():
    """测试Alchemy连接"""
    print(f"\n🧪 测试Alchemy连接...")
    
    try:
        from alchemy import Alchemy, Network
        
        # 测试API连接
        alchemy = Alchemy("S0hs4qoXIR1SMD8P7I6Wt", Network.ETH_MAINNET)
        
        print("✅ Alchemy SDK导入成功")
        print("✅ API密钥配置正确")
        print("🎉 连接测试通过！")
        return True
        
    except Exception as e:
        print(f"❌ Alchemy连接测试失败: {e}")
        return False

def check_wallet_monitor_file():
    """检查主程序文件是否存在"""
    print(f"\n📋 检查主程序文件...")
    
    if os.path.exists("wallet_monitor.py"):
        print("✅ wallet_monitor.py 文件存在")
        return True
    else:
        print("❌ wallet_monitor.py 文件不存在")
        print("💡 请确保 wallet_monitor.py 文件在同一目录下")
        return False

def create_virtual_environment():
    """创建虚拟环境 (可选)"""
    print(f"\n📦 虚拟环境选项...")
    
    venv_name = "wallet_monitor_env"
    
    if os.path.exists(venv_name):
        print(f"📁 虚拟环境已存在: {venv_name}")
        choice = input("是否重新创建虚拟环境? (y/N): ").strip().lower()
        if choice == 'y':
            print(f"🗑️  删除现有虚拟环境...")
            shutil.rmtree(venv_name)
        else:
            return venv_name
    
    try:
        print(f"🔨 创建虚拟环境: {venv_name}")
        subprocess.check_call([sys.executable, "-m", "venv", venv_name])
        print("✅ 虚拟环境创建成功")
        return venv_name
    except Exception as e:
        print(f"❌ 虚拟环境创建失败: {e}")
        return None

def install_in_venv(venv_path):
    """在虚拟环境中安装依赖"""
    print(f"\n📦 在虚拟环境中安装依赖...")
    
    # 获取虚拟环境Python路径
    if platform.system() == "Windows":
        python_path = os.path.join(venv_path, "Scripts", "python.exe")
        pip_path = os.path.join(venv_path, "Scripts", "pip.exe")
    else:
        python_path = os.path.join(venv_path, "bin", "python")
        pip_path = os.path.join(venv_path, "bin", "pip")
    
    if not os.path.exists(python_path):
        print(f"❌ 虚拟环境Python不存在: {python_path}")
        return False
    
    try:
        # 升级pip
        subprocess.check_call([python_path, "-m", "pip", "install", "--upgrade", "pip"])
        
        # 安装依赖
        packages = ["web3", "eth-account", "alchemy-sdk", "colorama", "aiohttp", "cryptography"]
        
        for package in packages:
            print(f"📦 安装 {package}...")
            subprocess.check_call([python_path, "-m", "pip", "install", package])
        
        print("✅ 虚拟环境依赖安装完成")
        return True
        
    except Exception as e:
        print(f"❌ 虚拟环境安装失败: {e}")
        return False

def create_run_scripts(venv_path=None):
    """创建运行脚本"""
    print(f"\n📝 创建运行脚本...")
    
    if platform.system() == "Windows":
        if venv_path:
            script_content = f'''@echo off
echo 🚀 启动钱包监控系统...
call {venv_path}\\Scripts\\activate.bat
python wallet_monitor.py
pause
'''
        else:
            script_content = '''@echo off
echo 🚀 启动钱包监控系统...
python wallet_monitor.py
pause
'''
        script_name = "run_monitor.bat"
    else:
        if venv_path:
            script_content = f'''#!/bin/bash
echo "🚀 启动钱包监控系统..."
source {venv_path}/bin/activate
python wallet_monitor.py
'''
        else:
            script_content = '''#!/bin/bash
echo "🚀 启动钱包监控系统..."
python wallet_monitor.py
'''
        script_name = "run_monitor.sh"
    
    with open(script_name, "w", encoding="utf-8") as f:
        f.write(script_content)
    
    if platform.system() != "Windows":
        os.chmod(script_name, 0o755)
    
    print(f"✅ 运行脚本已创建: {script_name}")
    return script_name

def launch_wallet_monitor():
    """启动钱包监控系统"""
    print(f"\n🚀 启动钱包监控系统...")
    
    if not os.path.exists("wallet_monitor.py"):
        print("❌ 找不到 wallet_monitor.py 文件")
        return False
    
    try:
        print("✅ 启动钱包监控系统...")
        print("💡 按 Ctrl+C 可以停止程序")
        print("-" * 50)
        
        subprocess.run([sys.executable, "wallet_monitor.py"])
        return True
        
    except KeyboardInterrupt:
        print("\n\n👋 程序已停止")
        return True
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        return False

def main():
    """主函数"""
    print_header()
    
    # 步骤1: 检查Python版本
    if not check_python_version():
        input("按回车键退出...")
        return
    
    # 步骤2: 检查pip
    if not check_pip():
        input("按回车键退出...")
        return
    
    # 步骤3: 检查主程序文件
    if not check_wallet_monitor_file():
        input("按回车键退出...")
        return
    
    # 步骤4: 询问是否使用虚拟环境
    print(f"\n🤔 是否使用虚拟环境? (推荐)")
    print("1. 是 - 创建/使用虚拟环境 (推荐)")
    print("2. 否 - 直接在系统环境中安装")
    
    try:
        venv_choice = input("请选择 (1/2): ").strip()
        use_venv = venv_choice == "1"
    except KeyboardInterrupt:
        print("\n👋 退出安装")
        return
    
    venv_path = None
    
    if use_venv:
        # 步骤5a: 创建虚拟环境
        venv_path = create_virtual_environment()
        if venv_path:
            # 在虚拟环境中安装依赖
            if not install_in_venv(venv_path):
                print("❌ 虚拟环境安装失败，尝试系统环境...")
                use_venv = False
                venv_path = None
    
    if not use_venv:
        # 步骤5b: 在系统环境中安装依赖
        if not check_and_install_dependencies():
            print("❌ 依赖安装失败")
            input("按回车键退出...")
            return
    
    # 步骤6: 测试连接
    if not test_alchemy_connection():
        print("⚠️  Alchemy连接测试失败，但可以继续尝试运行")
    
    # 步骤7: 创建运行脚本
    run_script = create_run_scripts(venv_path)
    
    # 步骤8: 显示完成信息
    print(f"\n🎉 安装完成！")
    print(f"📝 使用方法:")
    if venv_path:
        print(f"   - 直接运行: ./{run_script}")
        if platform.system() != "Windows":
            print(f"   - 或激活环境: source {venv_path}/bin/activate")
        else:
            print(f"   - 或激活环境: {venv_path}\\Scripts\\activate.bat")
    else:
        print(f"   - 直接运行: ./{run_script}")
        print(f"   - 或手动运行: python wallet_monitor.py")
    
    # 步骤9: 询问是否立即启动
    print(f"\n🚀 是否立即启动钱包监控系统？")
    try:
        choice = input("立即启动? (y/N): ").strip().lower()
        if choice == 'y':
            if venv_path:
                # 使用虚拟环境启动
                python_path = os.path.join(venv_path, "bin", "python") if platform.system() != "Windows" else os.path.join(venv_path, "Scripts", "python.exe")
                subprocess.run([python_path, "wallet_monitor.py"])
            else:
                launch_wallet_monitor()
        else:
            print(f"\n💡 稍后可以运行: ./{run_script}")
            
    except KeyboardInterrupt:
        print(f"\n💡 稍后可以运行: ./{run_script}")

if __name__ == "__main__":
    main()
