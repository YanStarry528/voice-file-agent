# 🎤 语音文件 Agent

> 对着麦克风说一句话，自动完成文件操作——保存、追加、查看、读取、改名、删除。

一个可插拔 Skill 的语音 Agent Demo：浏览器录音 → 本地语音识别 → LLM 工具调用 → 执行文件操作 → 语音播报结果。

## 工作原理

```
浏览器录音
   ↓
faster-whisper（本地 STT）      ← 音频不出本机
   ↓
LLM 工具调用 + Agent 循环        ← function calling，支持复合指令拆多步
   ↓
Skill 分发执行（缺参数会追问，删除会二次确认）
   ↓
页面展示「识别文字 / 意图 / 执行结果」三块 + 刷新文件列表
   ↓
edge-tts 语音播报结果            ← 「说 → 听」闭环
```

## 支持的语音指令

| 你说的话 | 意图 | 效果 |
|---|---|---|
| 帮我保存一句话，内容是今天开了会，文件名叫会议记录 | `save_file` | 新建文件 |
| 在会议记录里加一段明天继续 | `append_file` | 追加内容 |
| 现在有哪些文件 | `list_files` | 列出 output 目录 |
| 读一下会议记录里写了什么 | `read_file` | 查看文件内容 |
| 把会议记录改名为 会议记录2026 | `rename_file` | 给已有文件改名 |
| 把测试删掉 | `delete_file` | 删除文件（执行前会反问一次确认） |

说无关的话会返回 `unknown`，不会误执行任何操作。

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
cp .env.example .env
```

填写 `.env`（该文件已在 `.gitignore` 中，不会被提交）：

| 变量 | 说明 | 示例 |
|---|---|---|
| `API_KEY` | OpenAI 兼容中转网关密钥 | `sk-xxxxxx` |
| `BASE_URL` | 网关地址，必须以 `/v1` 结尾 | `https://xxx/v1` |
| `WHISPER_MODEL` | 本地语音模型：`tiny` / `base` / `small`（越大越准越慢） | `base` |
| `LLM_MODEL` | 意图分类模型，需网关支持 | `deepseek-v4-flash` |
| `TTS_VOICE` | 语音回复发音人（edge-tts，微软在线） | `zh-CN-XiaoxiaoNeural` |
| `TTS_PROXY` | 访问微软 TTS 需走代理时填写，一般留空 | （空） |

### 3. 启动

```bash
python server.py
```

浏览器打开 <http://127.0.0.1:8000>，点录音说话即可。

## 项目结构

```
voice-file-agent/
├── server.py              # FastAPI 入口
├── agent/
│   ├── orchestrator.py    # 主流程编排（分步捕获异常）
│   ├── tool_calling.py    # Agent 工具调用循环（思考→调用→观察→继续）
│   ├── stt_skill.py       # 语音转文字 + 繁体转简体
│   ├── intent_skill.py    # 意图分类（工具调用失败时降级为 fallback）
│   ├── tts_skill.py       # 语音合成（edge-tts，失败自动重试）
│   ├── session.py         # 多轮会话记忆（指代消解、追问补全）
│   ├── paths.py           # 路径安全校验（防穿越）
│   ├── skill_registry.py  # Skill 注册中心 + 生成 function calling 工具定义
│   ├── skills/            # 各个技能文件
│   └── common.py          # 配置 / 输出目录 / LLM 调用封装（带重试）
├── templates/index.html   # 前端页面（录音 / 播报开关 / 重播·停止）
├── docs/ROADMAP.md        # 后续扩展思路
├── output/                # 运行时产生的文件（已 gitignore）
├── requirements.txt
└── .env.example
```

## 扩展：新增一个 Skill

采用可插拔设计，**新增技能只需在 `agent/skills/` 下新建一个文件**，无需修改主流程或意图分类器：

```python
from agent.skill_registry import register

@register(
    intent="rename_file",
    description="重命名文件，触发词：改名、重命名",
    fields={"old_name": "原文件名", "new_name": "新文件名"},
)
def execute(args: dict) -> str:
    ...
    return "重命名成功"
```

启动时 `discover()` 会自动扫描加载，意图分类的 prompt 也会根据注册信息自动生成。

## 说明

- 所有文件操作限定在 `output/` 目录内，避免误删系统文件
- 删除不可逆，执行前会反问「确认/取消」；改名可逆，直接执行
- 多轮对话靠 `session_id` 串联：缺参数会追问，也可说「它」「上一个文件」指代最近操作的文件
- 复合指令会被自动拆成多步执行，例如「读一下会议记录，把里面的待办存成 todo.txt」
- 工具调用失败时自动降级为旧的 JSON 意图分类，保证基本可用性
- 语音识别在本地完成，只有识别出的**文字**会发往网关做意图分类
- 首次运行会自动下载 whisper 模型权重并缓存到本地
- 执行结果会用语音播报（edge-tts），形成「说 → 听」闭环；页面右上角可一键开关播报
- LLM 与 TTS 调用失败会自动重试（默认共尝试 3 次），重试仍失败时页面会明确提示「语音播报失败」而非静默无反应；重试次数/间隔/超时可在 `.env` 中调整
