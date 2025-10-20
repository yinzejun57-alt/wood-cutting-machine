#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
木模板开料机 G-code生成程序 - 客户打包版
专为PyInstaller打包设计
"""

import os
import sys
import time
import threading
import webbrowser

def get_resource_path(relative_path):
    """获取资源文件路径（兼容PyInstaller打包）"""
    try:
        # PyInstaller创建临时文件夹，将路径存储在_MEIPASS中
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    
    return os.path.join(base_path, relative_path)

def open_browser_delayed(url):
    """延迟打开浏览器"""
    time.sleep(3)
    print(f"正在打开浏览器: {url}")
    try:
        webbrowser.open(url)
    except:
        print("无法自动打开浏览器，请手动访问上述地址")

def main():
    print("=" * 60)
    print("木模板开料机 G-code生成程序")
    print("客户测试版 v1.0")
    print("=" * 60)
    
    # 准备input目录（运行目录下的真实目录，不在打包内）
    input_dir = os.path.join(os.getcwd(), "input")
    os.makedirs(input_dir, exist_ok=True)
    
    # 检查input目录中的文件
    final_files = []
    try:
        final_files = [f for f in os.listdir(input_dir) if f.endswith('.dxf')]
    except:
        pass
    
    if final_files:
        print(f"input目录中有 {len(final_files)} 个DXF文件可供测试")
    else:
        print("input目录为空，请通过Web界面上传DXF文件")
    
    print("\n正在启动Web服务器...")
    print("请稍候，系统启动需要几秒钟...")
    
    # 在后台线程中打开浏览器
    browser_thread = threading.Thread(target=open_browser_delayed, args=("http://localhost:5001",))
    browser_thread.daemon = True
    browser_thread.start()
    
    try:
        # 直接导入并启动Flask应用  
        from app import app
        
        print("\n" + "=" * 60)
        print("✓ 系统启动成功！")
        print("访问地址: http://localhost:5001") 
        print("浏览器将自动打开...")
        print("\n提示：关闭此窗口将停止程序")
        print("=" * 60 + "\n")
        
        # 启动Flask服务器
        app.run(host='0.0.0.0', port=5001, debug=False, use_reloader=False)
        
    except KeyboardInterrupt:
        print("\n\n程序已停止")
    except ImportError as e:
        print(f"\n错误: 无法加载程序模块")
        print(f"详细信息: {e}")
        print("\n请确保程序文件完整，如问题持续请联系技术支持")
        input("\n按回车键退出...")
    except Exception as e:
        print(f"\n程序运行出错: {e}")
        print("\n可能的解决方案:")
        print("1. 检查端口5001是否被其他程序占用")
        print("2. 尝试以管理员身份运行")
        print("3. 检查防火墙设置")
        input("\n按回车键退出...")

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"\n启动失败: {e}")
        import traceback
        traceback.print_exc()
        input("\n按回车键退出...")

