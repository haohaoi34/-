#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
钱包监控系统启动器 v3.0
自动安装依赖并启动主程序
"""

import os
import sys
import subprocess
import importlib

def check_python_version():
    """检查Python版本"""
    if sys.version_info < (3, 7):
        print("❌ 需要Python 3.7或更高版本")
        print(f"💡 当前版本: {sys.version}")
        sys.exit(1)
    print(f"✅ Python版本检查通过: {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")

def install_package(package_name):
    """安装单个包"""
    try:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', package_name], 
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except:
        try:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', '--user', package_name],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except:
            return False

def check_and_install_dependencies():
    """检查并安装所有依赖"""
    required_packages = {
        'web3': 'web3',
        'eth_account': 'eth-account', 
        'colorama': 'colorama',
        'aiohttp': 'aiohttp',
        'cryptography': 'cryptography',
        'requests': 'requests'
    }
    
    print("🔍 检查依赖包...")
    missing_packages = []
    
    for module_name, package_name in required_packages.items():
        try:
            importlib.import_module(module_name)
            print(f"✅ {package_name}")
        except ImportError:
            missing_packages.append(package_name)
            print(f"❌ {package_name} (需要安装)")
    
    if missing_packages:
        print(f"\n📦 正在安装 {len(missing_packages)} 个缺失的包...")
        
        for i, package in enumerate(missing_packages, 1):
            print(f"🔄 安装 {package} ({i}/{len(missing_packages)})...")
            if install_package(package):
                print(f"✅ {package} 安装成功")
            else:
                print(f"❌ {package} 安装失败")
                return False
        
        print("✅ 所有依赖安装完成!")
    else:
        print("✅ 所有依赖已满足!")
    
    return True

def main():
    """启动器主函数"""
    print("=" * 60)
    print("🚀 钱包监控系统启动器 v3.0")
    print("=" * 60)
    
    # 检查Python版本
    check_python_version()
    
    # 检查并安装依赖
    if not check_and_install_dependencies():
        print("\n❌ 依赖安装失败，请手动安装后重试")
        input("按回车键退出...")
        sys.exit(1)
    
    print("\n🎯 启动主程序...")
    
    # 检查主程序文件
    main_program = "wallet_monitor.py"
    if not os.path.exists(main_program):
        print(f"❌ 找不到主程序文件: {main_program}")
        print("💡 请确保 wallet_monitor.py 文件在同一目录下")
        input("按回车键退出...")
        sys.exit(1)
    
    try:
        # 导入并运行主程序
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        
        # 动态导入主程序模块
        import wallet_monitor
        
        # 直接调用主程序的main函数
        wallet_monitor.main()
        
    except KeyboardInterrupt:
        print("\n👋 程序已退出")
    except Exception as e:
        print(f"\n❌ 启动失败: {e}")
        print("💡 请检查网络连接和文件权限")
        input("按回车键退出...")

if __name__ == "__main__":
    main()
