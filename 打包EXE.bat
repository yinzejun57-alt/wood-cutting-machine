@echo off
chcp 65001
echo ================================================================
echo 木模板开料机G-code生成程序 - Windows EXE打包工具
echo ================================================================
echo.

REM 检查Python是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 错误: 未检测到Python，请先安装Python 3.8或更高版本
    echo 📥 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo ✓ 检测到Python环境
echo.

REM 执行打包脚本
echo 🚀 开始自动打包...
python build_exe.py

REM 检查是否成功
if exist "木模板开料机-客户版.zip" (
    echo.
    echo ✅ 打包成功完成！
    echo 📦 客户交付文件: 木模板开料机-客户版.zip
    echo.
    echo 💡 使用说明:
    echo    1. 将ZIP文件发送给客户
    echo    2. 客户解压ZIP文件
    echo    3. 双击"木模板开料机程序.exe"即可使用
    echo.
) else (
    echo ❌ 打包失败，请检查错误信息
)

echo 按任意键退出...
pause >nul
