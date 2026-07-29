@echo off
chcp 65001 >nul
title 读书会图书搜索服务

echo ====================================================
echo   读书会图书搜索服务 - 启动脚本
echo ====================================================
echo.

REM 检查 Python 是否安装
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [错误] 未检测到 Python，请先安装 Python 3.8+
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

REM 检查依赖是否安装
echo [检查] 正在检查依赖...
pip show flask >nul 2>nul
if %errorlevel% neq 0 (
    echo [安装] 正在安装依赖...
    pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo [错误] 依赖安装失败
        pause
        exit /b 1
    )
) else (
    echo [完成] 依赖已安装
)

echo.
echo [启动] 正在启动服务...
echo.
echo 前端页面: http://localhost:5000
echo 搜索接口: http://localhost:5000/api/search?q=书名
echo 按 Ctrl+C 停止服务
echo.

python server.py
pause