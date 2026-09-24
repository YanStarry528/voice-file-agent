# 后续扩展思路（Roadmap）

> 本文档沉淀项目后续可选的改进方向。当前代码已可运行，以下均为**增量演进**，可按方向独立推进。

## 一、当前形态

```
录音 → faster-whisper（STT） → LLM 工具调用（Agent 循环） → 多步 skill 执行 → 语音播报 + 页面展示
```

已从「单次执行」演进为真正的 Agent 内核，当前具备：

- 会话上下文：`session_id` 串联多轮，「把刚才那个文件删掉」可正常执行
- 缺参数追问：没给文件名时反问，用户补充后自动继续执行
- 危险操作二次确认：`delete` 执行前回问，说「取消」即中止
- 工具调用循环：`agent/tool_calling.py`，思考 → 调用 → 观察 → 继续，支持复合指令
- 语音回复闭环：结果经 edge-tts 朗读，形成「说 → 听」
- 路径安全校验：文件名统一由 `safe_output_path` 归一化，拒绝 `../` 与绝对路径

下文各方向中标记 ✅ 的项已落地，其余为后续可增量推进的方向。

---

## 二、方向一：Agent 内核做深（纵向，含金量最高）

从 demo 到真 Agent 的质变，建议按此顺序推进：

| # | 改进项 | 状态 | 目标 | 优先级 |
|---|---|---|---|---|
| 1 | **多轮上下文（指代消解）** | ✅ 已实现（`agent/session.py`） | 会话历史 + 最近文件记忆，「再读一遍它」「把刚才那个删掉」可用 | ★★★ |
| 2 | **缺参数追问** | ✅ 已实现（`agent/orchestrator.py`） | 用户没给文件名时反问「请问文件名叫什么？」，补充后继续执行 | ★★★ |
| 3 | **危险操作二次确认** | ✅ 已实现（`delete_skill` + 前端确认态） | `delete` 等写操作执行前回问确认，避免语音误识别造成不可逆损失 | ★★★ |
| 4 | **function calling 升级** | ✅ 已实现（`agent/tool_calling.py`） | LLM 原生工具调用 + Agent 循环，支持复合指令，如「读会议记录，把待办存成 todo.txt」；旧 JSON 分类降级为 fallback | ★★ |

> 这一条线已全部落地，系统不再是"意图分类器"，而是具备 tool calling 闭环的 Agent。
> 若用于面试/作品集，建议把重点转向方向四（工程加固）继续深化。

---

## 三、方向二：补全语音交互闭环（体验）

| # | 改进项 | 状态 | 目标 | 优先级 |
|---|---|---|---|---|
| 1 | **TTS 语音回复** | ✅ 已实现（`agent/tts_skill.py` + `/api/tts`） | 执行完用语音回答，形成「说→听」完整闭环；页面右上角可开关，结果卡可重播/停止 | ★★★ |
| 2 | **流式 / 实时识别** | 待实现 | 改「录完再转」为边说边出字（WebSocket + 流式 STT） | ★★ |
| 3 | **唤醒 + 连续对话** | 待实现 | 免去每次点击录音按钮 | ★ |

---

## 四、方向三：能力横向扩展

依托现有可插拔机制（`@register` + `discover()`），新增 skill 成本极低——只需在 `agent/skills/` 下新建文件。

已新增（均为纯本地、零 LLM 依赖，用来验证可插拔机制确实"加文件即生效"）：
- ✅ `search_files`：按关键词搜索文件名与内容（`agent/skills/search_skill.py`）
- ✅ `count_words`：统计文件字数与行数（`agent/skills/count_skill.py`）
- ✅ `copy_file`：复制文件到新名字（`agent/skills/copy_skill.py`）
- ✅ `move_file`：移动文件到子文件夹（`agent/skills/move_skill.py`）
- ✅ `make_dir`：新建文件夹（`agent/skills/mkdir_skill.py`）
- ✅ `file_info`：查看文件大小与最后修改时间（`agent/skills/info_skill.py`）
- ✅ `add_todo`：记一条待办事项（`agent/skills/todo_skill.py`）
- ✅ `list_todo`：列出待办清单（`agent/skills/todo_skill.py`）
- ✅ `done_todo`：标记待办完成（`agent/skills/todo_skill.py`）
- ✅ `summarize_meeting`：把会议记录整理成结构化纪要（`agent/skills/meeting_summary_skill.py`，首个依赖 LLM 的 skill）
- ✅ `ask_doc`：基于 output 目录的文档回答问题（`agent/skills/ask_doc_skill.py`，轻量 RAG：实时切段 + bigram 检索 + 依据片段作答并标注来源，不落盘索引）

后续可选：
- **整理类**：本地文档问答（接 RAG）——待办清单、会议纪要、文档问答均已实现；后续可升级为 embedding 向量检索（需引入模型依赖）
- **越界类**：日程提醒、网页搜索、发邮件——**建议不用邮箱/账号类 ToB 发布测试场景**，与本项目的"文件 Agent"定位偏离，优先级放低

---

## 五、方向四：工程加固

| # | 改进项 | 状态 | 目标 | 优先级 |
|---|---|---|---|---|
| 1 | **安全检查** | ✅ 已实现（`agent/paths.py`） | 所有 skill 文件名统一经 `safe_output_path` 解析，`resolve()` 后做前缀校验，杜绝 `../`、绝对路径、反斜杠穿越 | ★★★ |
| 2 | **单元测试** | ✅ 已实现（`tests/` + 根 `conftest.py`） | 覆盖路径安全、意图解析、各 skill、orchestrator 主流程与异常分支、tool_calling 循环、session 多轮记忆、LLM/TTS 重试与 markdown 清洗、后缀补全，136 个用例 | ★★ |
| 3 | **错误兜底（重试 + 明确提示）** | ✅ 已实现（`common.chat` + `tts_skill`） | LLM 调用失败自动重试；TTS 合成失败自动重试，前端明确提示「语音播报失败」而非静默降级 | ★★ |
| 4 | **文件名后缀补全** | ✅ 已实现（`paths.resolve_output_file`） | 语音不会说出「点 txt」，无后缀文件名保存时自动补 `.txt`、读取时回退匹配「原名.txt」；已带其他后缀（`.md` 等）不改写；已存在的历史无后缀文件优先沿用，避免同一内容分裂成两份 | ★★ |

---

## 六、推进进度与下一步建议

主线已走完：

```
多轮上下文 → 缺参数追问 → 危险操作确认 → function calling 升级 → TTS 语音闭环
                    ↓
        期间穿插：文件名安全校验（paths.py）
```

系统已从"意图分类器"改造为**真正的 Agent 内核**。

**下一步优先级建议：**

1. **能力横向扩展**（方向三）——依托 `@register` 机制，新增 skill 成本极低
2. **流式 / 实时识别**（方向二 #2）——改「录完再转」为边说边出字，体验更顺
3. **测试深化**——补 `session.py` 多轮会话指代消解、异常分支的测试，进一步提升覆盖率

> 具体选哪条线取决于项目目标：自用实用 → 方向三 + 二；作品集展示 → 方向四（测试 + 工程加固）。
