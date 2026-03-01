# Voice Input - 语音输入工具

按住快捷键说话，松开后自动转写并粘贴到光标位置。支持 LLM 润色、语音指令和语音转 bash 命令。

## 功能

- **语音转文字**：本地 faster-whisper（GPU 加速）/ 腾讯云 ASR
- **LLM 润色**：支持 OpenAI 兼容 API（DeepSeek 等），按窗口自动切换策略
- **语音指令**：选中文本后按热键说话，对选中内容执行操作（翻译、格式化等）
- **语音转 bash**：按住右 Alt 说自然语言，自动转为 bash 命令
- **连续输入**：支持连续录音，队列顺序处理
- **长录音自动切割**：超过 6 秒检测静音自动分段，松开后合并输出
- **个人词典**：提高专有名词识别率
- **系统托盘**：绿色待机 / 红色录音 / 黄色处理中
- **剪贴板保护**：粘贴后恢复原内容
- **跨平台**：支持 Windows 和 macOS

## Windows 安装

需要 Python 3.10+

1. 下载 [最新 Release](https://github.com/su27/voice_input/releases/latest) 并解压
2. 双击 `install.bat`（自动创建虚拟环境、安装依赖、生成配置文件）
3. 编辑 `config.yaml`，填入 API key
4. （可选）本地 STT 需额外安装：`.venv\Scripts\pip.exe install -r requirements-local.txt`

### 运行

- 双击 `start.bat` — 后台运行，无窗口
- 双击 `start_debug.bat` — 显示控制台，调试用
- 日志写入 `voice.log`
- 右键托盘图标：查看配置、查看日志、退出

## macOS 安装

需要 Python 3（`brew install python`）

1. 下载 [最新 Release](https://github.com/su27/voice_input/releases/latest) 并解压
2. 终端运行 `./install.sh`
3. 编辑 `config.yaml`，填入 API key（推荐 `engine: tencent`）
4. 双击 `VoiceInput.app` 启动
5. 首次运行需授权「辅助功能」权限（系统设置 → 隐私与安全性 → 辅助功能）

## STT 引擎

| 引擎 | 说明 | 适用场景 |
|------|------|----------|
| `local` | 本地 faster-whisper | 有 NVIDIA GPU 的 Windows |
| `tencent` | 腾讯云一句话识别 | 无 GPU / macOS / 低延迟 |

## 热键

| 热键 | 功能 |
|------|------|
| 右 Ctrl（按住） | 语音输入，松开后转写粘贴 |
| 右 Alt（按住） | 语音转 bash 命令 |

热键可在 `config.yaml` 中自定义。macOS 可用 `cmd_r`。

## 语音指令

在非终端窗口中选中文本后按热键说话，语音作为指令对选中文本执行操作：
- "翻译成英文"
- "格式化成表格"
- "总结一下"

## LLM Profile 自动匹配

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
| `stt.engine` | `local` / `tencent` |
| `stt.tencent.secret_id/secret_key` | 腾讯云密钥 |
| `llm.enabled` | 是否启用 LLM 润色 |
| `llm.api_url` | OpenAI 兼容 API 地址 |
| `llm.api_key` | LLM API key |

## 项目结构

```
├── main.py              # 入口：热键监听 + 任务队列 + 系统托盘
├── recorder.py          # 录音：常驻音频流 + 预缓冲 + 静音切割
├── stt.py               # 语音转文字（本地/腾讯云/远程）
├── llm.py               # LLM 润色/指令
├── output.py            # 剪贴板粘贴 + 恢复
├── config.example.yaml  # 示例配置
├── requirements.txt     # 基础依赖
├── requirements-local.txt # 本地 STT 额外依赖
├── install.bat          # Windows 一键安装
├── start.bat            # Windows 启动（无窗口）
├── start_debug.bat      # Windows 启动（控制台）
├── install.sh           # macOS 一键安装
└── VoiceInput.app/      # macOS 启动器
```

## License

MIT
