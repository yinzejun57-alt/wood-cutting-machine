#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
木模板开料机 G-code生成程序 - 简化客户版
双击运行，自动启动Web界面
"""

import os
import sys
import time
import threading
import webbrowser
import subprocess

def check_dependencies():
    """检查和安装依赖"""
    try:
        import flask
        import ezdxf
        print("依赖库检查通过")
        return True
    except ImportError as e:
        print(f"缺少依赖库: {e}")
        print("正在自动安装...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "flask", "ezdxf"])
            print("依赖库安装完成")
            return True
        except Exception as install_error:
            print(f"安装失败: {install_error}")
            print("请手动执行: pip install flask ezdxf")
            input("按回车键退出...")
            return False

def check_files():
    """检查必要文件"""
    required_files = ['app.py', 'templates/index.html']
    missing = [f for f in required_files if not os.path.exists(f)]
    
    if missing:
        print("错误：缺少必要文件:")
        for f in missing:
            print(f"  - {f}")
        input("按回车键退出...")
        return False
    return True

def open_browser_delayed(url):
    """延迟打开浏览器"""
    time.sleep(3)
    print(f"正在打开浏览器: {url}")
    webbrowser.open(url)

def main():
    print("=" * 60)
    print("木模板开料机 G-code生成程序")
    print("客户测试版 v1.0")
    print("=" * 60)
    
    # 检查文件和依赖
    if not check_files() or not check_dependencies():
        return
    
    # 准备input目录和测试文件
    input_dir = "input"
    os.makedirs(input_dir, exist_ok=True)
    
    # 如果input目录为空，尝试复制测试文件
    existing_files = [f for f in os.listdir(input_dir) if f.endswith('.dxf')]
    if not existing_files:
        test_path = "/Users/yinlei/Downloads/木模板开料机"
        if os.path.exists(test_path):
            import shutil
            dxf_files = [f for f in os.listdir(test_path) if f.endswith('.dxf')]
            for dxf_file in dxf_files[:2]:  # 复制前2个文件作为示例
                src = os.path.join(test_path, dxf_file)
                dst = os.path.join(input_dir, dxf_file)
                try:
                    shutil.copy2(src, dst)
                    print(f"复制示例文件: {dxf_file}")
                except:
                    pass
    
    # 检查最终的文件情况
    final_files = [f for f in os.listdir(input_dir) if f.endswith('.dxf')]
    if final_files:
        print(f"input目录中有 {len(final_files)} 个DXF文件可供测试")
    else:
        print("input目录为空，请通过Web界面上传DXF文件进行测试")
    
    print("\n正在启动Web服务器...")
    print("请稍候，系统启动需要几秒钟...")
    
    # 在后台线程中打开浏览器
    browser_thread = threading.Thread(target=open_browser_delayed, args=("http://localhost:5001",))
    browser_thread.daemon = True
    browser_thread.start()
    
    try:
        # 启动Flask应用  
        from app import app
        print("\n" + "=" * 60)
        print("系统启动成功！")
        print("访问地址: http://localhost:5001") 
        print("浏览器将自动打开...")
        print("关闭此窗口将停止程序")
        print("=" * 60)
        
        app.run(host='0.0.0.0', port=5001, debug=False, use_reloader=False)
        
    except KeyboardInterrupt:
        print("\n程序已停止")
    except Exception as e:
        print(f"\n程序运行出错: {e}")
        print("可能的解决方案:")
        print("1. 检查端口5001是否被占用")
        print("2. 重新安装依赖: pip install flask ezdxf")
        input("按回车键退出...")

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"启动失败: {e}")
        input("按回车键退出...")
