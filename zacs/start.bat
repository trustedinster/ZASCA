@echo off
chcp 65001 >nul
title ZASCA 本地开发服务器

echo ========================================
echo  ZASCA 本地开发环境启动
echo ========================================
echo.

REM 检查Python
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [错误] 未找到Python，请先安装Python 3.10+
    pause
    exit /b 1
)

REM 检查虚拟环境
if not exist "venv\Scripts\activate.bat" (
    echo [INFO] 创建虚拟环境...
    python -m venv venv
)

REM 激活虚拟环境
call venv\Scripts\activate.bat

REM 安装依赖
if not exist "venv\Lib\site-packages\django" (
    echo [INFO] 安装依赖...
    pip install -r requirements.txt -q
)

REM 加载环境变量
if exist ".env" (
    for /f "usebackq tokens=1,* delims==" %%a in (".env") do (
        if not "%%a"=="" if not "%%a:~0,1%"=="#" set "%%a=%%b"
    )
)

REM 数据库迁移
echo [INFO] 检查数据库迁移...
python manage.py migrate --run-syncdb -v 0

REM 启动服务器
echo.
echo [OK] 启动服务器: http://127.0.0.1:8000
echo [OK] 后台管理: http://127.0.0.1:8000/admin/
echo.
echo 按 Ctrl+C 停止服务器
echo ========================================
python manage.py runserver
