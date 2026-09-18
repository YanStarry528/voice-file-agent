from agent.stt_skill import transcribe
from agent.intent_skill import classify
from agent.skill_registry import discover, dispatch

# 启动时扫描并加载所有 skill（新增 skill 只需在 agent/skills/ 下新建文件）
discover()


def run(audio_data: bytes, audio_name: str = "audio.wav") -> dict:
    """
    完整流程：音频 → 文字 → 意图 → 执行
    分步捕获异常，返回 dict 供页面展示每一步结果，避免整体崩溃
    """
    # 1. 语音转文字
    try:
        text = transcribe(audio_data, audio_name)
    except Exception as e:
        return {"text": "", "intent": {}, "result": f"语音识别失败：{e}"}

    # 2. 意图分类
    try:
        intent_data = classify(text)
    except Exception as e:
        return {"text": text, "intent": {}, "result": f"意图分类失败：{e}"}

    intent = intent_data.get("intent")

    # 3. 根据意图执行
    try:
        result = dispatch(intent, intent_data)
    except Exception as e:
        result = f"执行失败：{e}"

    return {
        "text": text,
        "intent": intent_data,
        "result": result,
    }
