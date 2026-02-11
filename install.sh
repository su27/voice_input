#!/bin/bash
set -e
cd "$(dirname "$0")"

echo "=== 语音输入工具安装 ==="

if ! command -v python3 &>/dev/null; then
    echo "[错误] 未找到 python3，请先安装：brew install python"
    exit 1
fi

echo "[1/3] 创建虚拟环境..."
python3 -m venv .venv

echo "[2/3] 安装依赖..."
.venv/bin/pip install -q sounddevice numpy pynput pyperclip pyautogui httpx pystray Pillow pyyaml opencc-python-reimplemented

echo "[3/3] 初始化配置..."
if [ ! -f config.yaml ]; then
    cp config.example.yaml config.yaml
    echo "已创建 config.yaml，请编辑填入 API key"
else
    echo "config.yaml 已存在，跳过"
fi

echo ""
echo "=== 安装完成 ==="
echo "请编辑 config.yaml 后双击 VoiceInput.app 启动"
