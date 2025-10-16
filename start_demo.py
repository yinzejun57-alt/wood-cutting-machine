#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
木模板开料机 G-code生成程序 - Demo启动脚本
"""

import os
import sys
import subprocess
import webbrowser
import time
from threading import Timer

def check_dependencies():
    """检查依赖库是否安装"""
    try:
        import flask
        import ezdxf
        print("✓ 依赖库检查通过")
        return True
    except ImportError as e:
        print(f"✗ 缺少依赖库: {e}")
        print("正在自动安装依赖库...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
            print("✓ 依赖库安装完成")
            return True
        except Exception as install_error:
            print(f"✗ 依赖库安装失败: {install_error}")
            return False

def open_browser():
    """延迟打开浏览器"""
    webbrowser.open('http://localhost:5001')

def main():
    print("=" * 60)
    print("木模板开料机 G-code生成程序 - Demo版本")
    print("版本: v1.0")
    print("=" * 60)
    
    # 检查依赖
    if not check_dependencies():
        print("请手动安装依赖库后重试:")
        print("pip install -r requirements.txt")
        sys.exit(1)
    
    # 检查输入文件
    input_path = "/Users/yinlei/Downloads/木模板开料机"
    if not os.path.exists(input_path):
        print(f"⚠️  输入目录不存在: {input_path}")
        print("请确保客户提供的DXF文件放在该目录下")
    else:
        dxf_files = [f for f in os.listdir(input_path) if f.lower().endswith('.dxf')]
        print(f"✓ 找到 {len(dxf_files)} 个DXF文件")
        for f in dxf_files:
            print(f"  - {f}")
    
    print("\n启动Web服务器...")
    print("访问地址: http://localhost:5001")
    print("按 Ctrl+C 停止服务")
    print("-" * 60)
    
    # 延迟3秒后自动打开浏览器
    Timer(3.0, open_browser).start()
    
    try:
        # 启动Flask应用
        from app import app
        app.run(debug=False, host='0.0.0.0', port=5001)
    except KeyboardInterrupt:
        print("\n服务已停止")
    except Exception as e:
        print(f"启动失败: {e}")

if __name__ == '__main__':
    main()
