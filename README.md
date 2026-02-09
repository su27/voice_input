# Voice Input - 语音输入工具

按住快捷键说话，松开后自动转写并粘贴到光标位置。支持 LLM 润色（纠错、意图理解、格式化）。

## 功能

- **语音转文字**：本地 faster-whisper（GPU 加速）或远程 API
- **LLM 润色**：可选，支持 OpenAI 兼容 API（DeepSeek、Ollama 等）
- **智能 Profile**：根据当前活动窗口自动切换润色策略（邮件、代码、聊天等）
- **系统托盘**：后台运行，托盘图标显示录音状态
- **繁转简 + 标点修正**：自动处理 Whisper 输出的繁体和半角标点

## 安装

```bash
# 需要 Python 3.10+，Windows 环境
pip install -r requirements.txt
```

GPU 加速需要额外安装 NVIDIA 运行时：

```bash
pip install nvidia-cublas-cu12 nvidia-cudnn-cu12
```

并将 dll 路径加入 PATH：

```powershell
$env:PATH += ";path\to\site-packages\nvidia\cublas\bin;path\to\site-packages\nvidia\cudnn\bin"
```

## 配置

复制示例配置并编辑：

```bash
cp config.example.yaml config.yaml
```

主要配置项：

| 配置 | 说明 |
|------|------|
| `hotkey` | 录音快捷键，默认 `ctrl_r`（右Ctrl） |
| `stt.engine` | `local`（faster-whisper）或 `remote` |
| `stt.local.model` | Whisper 模型：tiny/base/small/medium/large-v3 |
| `llm.enabled` | 是否启用 LLM 润色 |
| `llm.api_url` | LLM API 地址（OpenAI 兼容） |
| `llm.profiles` | 润色策略，按窗口标题自动匹配 |

## 使用

```bash
python main.py
```

1. 启动后系统托盘出现麦克风图标（绿色=待机，红色=录音中）
2. 按住快捷键说话，松开后自动转写 → 润色 → 粘贴
3. 托盘右键可加载/卸载模型或退出

## 项目结构

```
├── main.py           # 入口：热键监听 + 系统托盘
├── recorder.py       # 录音：常驻音频流 + 预缓冲
├── stt.py            # 语音转文字：faster-whisper / 远程 API
├── llm.py            # LLM 润色：按窗口自动选择 profile
├── output.py         # 输出：剪贴板 + 模拟粘贴
├── config.example.yaml
├── requirements.txt
└── start.bat         # Windows 启动脚本
```

## License

MIT
