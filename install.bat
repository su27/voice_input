@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo === 语音输入工具安装 ===
echo.

where python >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python，请先安装 Python 3.10+
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [1/3] 创建虚拟环境...
python -m venv .venv
if errorlevel 1 (
    echo [错误] 创建虚拟环境失败
    pause
    exit /b 1
)

echo [2/3] 安装依赖...
.venv\Scripts\pip.exe install -r requirements.txt -q
if errorlevel 1 (
    echo [错误] 安装依赖失败
    pause
    exit /b 1
)

echo [3/3] 初始化配置...
if not exist config.yaml (
    copy config.example.yaml config.yaml >nul
    echo 已创建 config.yaml，请编辑填入 API key 等配置
) else (
    echo config.yaml 已存在，跳过
)

echo.
echo === 安装完成 ===
echo 请编辑 config.yaml 后双击 start.bat 启动
pause
