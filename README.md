# Voice Input - 语音输入工具

按住快捷键说话，松开后自动转写并粘贴到光标位置。支持 LLM 润色、语音指令和语音转 bash 命令。

## 功能

- **语音转文字**：本地 faster-whisper（GPU 加速）或远程 API
- **LLM 润色**：可选，支持 OpenAI 兼容 API（DeepSeek、Ollama 等）
- **语音指令**：选中文本后按热键说话，可翻译、格式化、结构化等
- **语音转 bash**：按住右 Alt 说自然语言，自动转为 bash 命令
- **智能 Profile**：根据当前活动窗口自动切换润色策略（邮件、代码、聊天等）
- **连续输入**：上一条还在处理时可继续录音，队列顺序处理
- **个人词典**：通过 initial_prompt 提高专有名词识别率
- **系统托盘**：后台运行，托盘图标显示录音状态（绿色待机/红色录音）
- **繁转简 + 标点修正**：自动处理 Whisper 输出的繁体和半角标点
- **剪贴板保护**：粘贴后自动恢复剪贴板原内容
- **选中文本检测**：通过剪贴板序列号检测，非 Terminal 窗口自动 Ctrl+C 复制选中内容

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
| `hotkey` | 语音输入热键，默认 `ctrl_r`（右Ctrl） |
| `stt.engine` | `local`（faster-whisper）或 `remote` |
| `stt.local.model` | Whisper 模型：tiny/base/small/medium/large-v3 |
| `stt.local.dictionary` | 个人词典，提高专有名词识别率 |
| `llm.enabled` | 是否启用 LLM 润色 |
| `llm.api_url` | LLM API 地址（OpenAI 兼容） |
| `llm.profiles` | 润色策略，按窗口标题自动匹配 |

## 使用

```bash
python main.py
```

### 语音输入（右 Ctrl）

按住说话，松开后自动转写 → 润色 → 粘贴到光标位置。

- 无选中文本：根据当前窗口自动选择润色策略
  - 邮件客户端 → 整理为正式邮件格式
  - IDE → 转为代码注释/commit message
  - 聊天软件 → 保持口语风格纠错
  - 其他 → 纠错 + 口误修正
- 有选中文本：语音作为指令，对选中文本执行操作（如"翻译成英文"、"格式化成表格"）

### 语音转 bash（右 Alt）

按住右 Alt 说自然语言，自动转为 bash 命令粘贴到终端。

例如说"列出当前目录下所有 py 文件" → `find . -name "*.py"`

## 项目结构

```
├── main.py              # 入口：热键监听 + 任务队列 + 系统托盘
├── recorder.py          # 录音：常驻音频流 + 预缓冲
├── stt.py               # 语音转文字：faster-whisper / 远程 API
├── llm.py               # LLM 润色/指令：按窗口自动选择 profile
├── output.py            # 输出：剪贴板 + 模拟粘贴 + 剪贴板恢复
├── config.example.yaml
├── requirements.txt
└── start.bat            # Windows 启动脚本
```

## License

MIT
