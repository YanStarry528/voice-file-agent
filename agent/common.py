import os
import time
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

# 项目根目录（本文件位于 agent/ 下，向上两级即根目录）
ROOT = Path(__file__).resolve().parent.parent

# 统一在这里加载 .env，其他模块从 common 导入配置，不依赖启动目录
load_dotenv(ROOT / ".env")

# 意图分类走公司中转网关（OpenAI 兼容），只此一个 client。
# 语音转文字已改为本地 faster-whisper，不再需要 STT 网关 client。
llm_client = OpenAI(
    api_key=os.getenv("API_KEY"),
    base_url=os.getenv("BASE_URL"),
    # 单次请求超时（秒）：网关偶发卡住时尽快失败，交给下方重试逻辑接管
    timeout=float(os.getenv("LLM_TIMEOUT", "30")),
)

# 意图分类模型：必须是中转网关支持的模型 ID
LLM_MODEL = os.getenv("LLM_MODEL", "deepseek-v4-flash")

# LLM 调用失败后的最大重试次数（网关偶发抖动时自动重试）
LLM_MAX_RETRIES = int(os.getenv("LLM_MAX_RETRIES", "2"))
# 重试间隔的基数（秒），按次数递增：1s、2s、…
LLM_RETRY_DELAY = float(os.getenv("LLM_RETRY_DELAY", "1.0"))


def chat(messages: list[dict], tools: list[dict] | None = None, temperature: float = 0):
    """带重试的 LLM 补全调用。

    网关偶发超时 / 抖动时自动重试（次数由 LLM_MAX_RETRIES 控制），
    全部失败才抛出最后一个异常，交由上层（orchestrator）回退处理。
    """
    kwargs = {
        "model": LLM_MODEL,
        "messages": messages,
        "temperature": temperature,
    }
    if tools:
        kwargs["tools"] = tools

    last_err = None
    for attempt in range(LLM_MAX_RETRIES + 1):
        try:
            return llm_client.chat.completions.create(**kwargs)
        except Exception as e:  # noqa: BLE001 - 网关异常类型不固定，统一重试
            last_err = e
            if attempt < LLM_MAX_RETRIES:
                time.sleep(LLM_RETRY_DELAY * (attempt + 1))
    raise last_err

# 本地语音转文字模型（faster-whisper，不走中转）：tiny / base / small
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "base")

# TTS 语音合成（edge-tts，微软在线服务，免费）：回复语音的发音人与可选代理
TTS_VOICE = os.getenv("TTS_VOICE", "zh-CN-XiaoxiaoNeural")
TTS_PROXY = os.getenv("TTS_PROXY", "")

# 所有文件操作的输出目录（绝对路径，不受启动目录影响）
OUTPUT_DIR = ROOT / "output"
