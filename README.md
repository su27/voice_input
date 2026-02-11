# Voice Input - 语音输入工具

按住快捷键说话，松开后自动转写并粘贴到光标位置。支持 LLM 润色、语音指令和语音转 bash 命令。

## 功能

- **语音转文字**：本地 faster-whisper（GPU 加速）或远程 API
- **LLM 润色**：支持 OpenAI 兼容 API（DeepSeek、Ollama 等），按窗口自动切换策略
- **语音指令**：选中文本后按热键说话，对选中内容执行操作（翻译、格式化等）
- **语音转 bash**：按住右 Alt 说自然语言，自动转为 bash 命令
- **连续输入**：支持连续录音，队列顺序处理
- **长录音自动切割**：超过 6 秒检测静音自动分段，松开后合并输出
- **个人词典**：提高专有名词识别率
- **系统托盘**：绿色待机 / 红色录音 / 黄色处理中
- **剪贴板保护**：粘贴后恢复原内容

## 安装

需要 Windows + Python 3.10+

1. 下载或 clone 本项目
2. 双击 `install.bat`（自动创建虚拟环境、安装依赖、生成配置文件）
3. 编辑 `config.yaml`，填入 LLM API key 等配置

## 使用

- 双击 `start.bat` 启动（后台运行，无窗口）
- 双击 `start_debug.bat` 启动（显示控制台，调试用）
- 日志写入 `voice.log`
- 右键托盘图标可退出

### 热键

| 热键 | 功能 |
|------|------|
| 右 Ctrl（按住） | 语音输入，松开后转写粘贴 |
| 右 Alt（按住） | 语音转 bash 命令 |

### 语音指令

在非终端窗口中选中文本后按右 Ctrl 说话，语音作为指令对选中文本执行操作：
- "翻译成英文"
- "格式化成表格"
- "总结一下"

### LLM Profile 自动匹配

根据当前窗口标题自动选择润色策略：

| 窗口 | Profile |
|------|---------|
| Outlook / Gmail | email（正式邮件格式） |
| VS Code / IntelliJ | code（代码注释/commit message） |
| 微信 / 飞书 / Slack | chat（口语纠错） |
| 其他 | intent（保留原意纠错） |

## 配置说明

编辑 `config.yaml`，主要配置项：

| 配置 | 说明 |
|------|------|
| `hotkey` | 语音输入热键，默认 `ctrl_r` |
| `stt.engine` | `local` 或 `remote` |
| `stt.local.model` | tiny / base / small / medium / large-v3 |
| `stt.local.dictionary` | 个人词典列表 |
| `llm.enabled` | 是否启用 LLM 润色 |
| `llm.api_url` | OpenAI 兼容 API 地址 |
| `llm.api_key` | API key |

## 项目结构

```
├── main.py              # 入口：热键监听 + 任务队列 + 系统托盘
├── recorder.py          # 录音：常驻音频流 + 预缓冲 + 静音切割
├── stt.py               # 语音转文字
├── llm.py               # LLM 润色/指令
├── output.py            # 剪贴板粘贴 + 恢复
├── config.example.yaml  # 示例配置
├── requirements.txt
├── install.bat          # 一键安装
├── start.bat            # 启动（无窗口）
└── start_debug.bat      # 启动（控制台调试）
```

## License

MIT
