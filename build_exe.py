#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
木模板开料机G-code生成程序 - EXE打包脚本
在Windows服务器上运行此脚本生成可执行文件
"""

import os
import sys
import subprocess
import shutil
import zipfile
from pathlib import Path

def check_python():
    """检查Python版本"""
    if sys.version_info < (3, 8):
        print("错误: 需要Python 3.8或更高版本")
        return False
    print(f"✓ Python版本: {sys.version}")
    return True

def install_requirements():
    """安装依赖包"""
    print("\n正在安装依赖包...")
    
    requirements = [
        "Flask==3.0.0",
        "ezdxf==1.4.2", 
        "Werkzeug==3.0.1",
        "pyinstaller==6.1.0"
    ]
    
    for req in requirements:
        print(f"安装 {req}...")
        result = subprocess.run([sys.executable, "-m", "pip", "install", req], 
                              capture_output=True, text=True)
        if result.returncode != 0:
            print(f"错误: 安装 {req} 失败")
            print(result.stderr)
            return False
    
    print("✓ 所有依赖包安装完成")
    return True

def create_pyinstaller_spec():
    """创建PyInstaller配置文件"""
    spec_content = '''# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['简化客户版.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('templates', 'templates'),
        ('input', 'input'),
        ('客户版使用指南.txt', '.'),
    ],
    hiddenimports=[
        'flask',
        'ezdxf',
        'werkzeug',
        'jinja2',
        'click',
        'itsdangerous',
        'blinker',
        'fonttools',
        'numpy'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='木模板开料机程序',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
'''
    
    with open('木模板开料机.spec', 'w', encoding='utf-8') as f:
        f.write(spec_content)
    
    print("✓ PyInstaller配置文件已创建")

def build_exe():
    """构建EXE文件"""
    print("\n开始构建EXE文件...")
    print("这可能需要几分钟时间，请耐心等待...")
    
    result = subprocess.run([
        sys.executable, "-m", "PyInstaller", 
        "--clean", 
        "木模板开料机.spec"
    ], capture_output=True, text=True)
    
    if result.returncode != 0:
        print("构建失败:")
        print(result.stderr)
        return False
    
    print("✓ EXE文件构建完成")
    return True

def create_distribution():
    """创建分发包"""
    print("\n正在创建分发包...")
    
    dist_dir = "木模板开料机-客户版"
    if os.path.exists(dist_dir):
        shutil.rmtree(dist_dir)
    
    os.makedirs(dist_dir)
    
    # 复制EXE文件
    exe_path = "dist/木模板开料机程序.exe"
    if os.path.exists(exe_path):
        shutil.copy2(exe_path, dist_dir)
        print(f"✓ 复制EXE文件到 {dist_dir}")
    else:
        print("错误: 找不到生成的EXE文件")
        return False
    
    # 创建使用说明
    readme_content = """木模板开料机G-code生成程序 v1.0
================================

安装说明:
1. 双击 "木模板开料机程序.exe" 启动程序
2. 程序会自动打开浏览器界面
3. 如果浏览器没有自动打开，请手动访问: http://localhost:5001

使用步骤:
1. 点击"选择DXF文件"上传您的套料结果文件
2. 调整加工参数（材料厚度、切削速度等）
3. 选择要处理的文件（通过复选框）
4. 点击"一键生成G代码"
5. 下载生成的NC文件

注意事项:
- 支持中文文件名
- 建议单次处理不超过5个文件
- 生成的NC文件兼容宝元数控系统
- 程序运行时请不要关闭命令行窗口

技术支持: 如有问题请联系开发团队
版本: v1.0
日期: 2025年10月
"""
    
    with open(f"{dist_dir}/使用说明.txt", 'w', encoding='utf-8') as f:
        f.write(readme_content)
    
    # 创建示例文件夹
    example_dir = f"{dist_dir}/示例文件"
    os.makedirs(example_dir, exist_ok=True)
    
    # 如果存在示例文件，复制过去
    if os.path.exists("input"):
        for file in os.listdir("input"):
            if file.endswith('.dxf'):
                shutil.copy2(f"input/{file}", example_dir)
    
    # 创建ZIP包
    zip_name = "木模板开料机-客户版.zip"
    with zipfile.ZipFile(zip_name, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(dist_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arc_path = os.path.relpath(file_path, ".")
                zipf.write(file_path, arc_path)
    
    print(f"✓ 分发包已创建: {zip_name}")
    return True

def cleanup():
    """清理临时文件"""
    print("\n清理临时文件...")
    
    cleanup_items = ["build", "dist", "木模板开料机.spec", "__pycache__"]
    
    for item in cleanup_items:
        if os.path.exists(item):
            if os.path.isdir(item):
                shutil.rmtree(item)
            else:
                os.remove(item)
    
    print("✓ 清理完成")

def main():
    """主函数"""
    print("=" * 60)
    print("木模板开料机G-code生成程序 - EXE打包工具")
    print("=" * 60)
    
    # 检查Python版本
    if not check_python():
        return False
    
    # 安装依赖
    if not install_requirements():
        return False
    
    # 创建配置文件
    create_pyinstaller_spec()
    
    # 构建EXE
    if not build_exe():
        return False
    
    # 创建分发包
    if not create_distribution():
        return False
    
    # 清理临时文件
    cleanup()
    
    print("\n" + "=" * 60)
    print("✅ 打包完成!")
    print("📦 客户交付文件: 木模板开料机-客户版.zip")
    print("💡 请将ZIP文件发送给客户，客户解压后双击EXE即可使用")
    print("=" * 60)
    
    return True

if __name__ == "__main__":
    try:
        success = main()
        if not success:
            print("\n❌ 打包过程中出现错误")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n⚠️  用户取消操作")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 未预期的错误: {e}")
        sys.exit(1)
