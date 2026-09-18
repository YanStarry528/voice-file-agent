import os
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
)

# 意图分类模型：必须是中转网关支持的模型 ID
LLM_MODEL = os.getenv("LLM_MODEL", "deepseek-v4-flash")

# 本地语音转文字模型（faster-whisper，不走中转）：tiny / base / small
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "base")

# 所有文件操作的输出目录（绝对路径，不受启动目录影响）
OUTPUT_DIR = ROOT / "output"
