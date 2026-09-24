import os
from pathlib import Path

import uvicorn
from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.templating import Jinja2Templates

from agent.common import OUTPUT_DIR
from agent.orchestrator import run, run_text
from agent.tts_skill import synthesize

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title="语音文件 Agent")

templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


def _list_files() -> list[str]:
    """返回 output 目录下的文件名列表（按名称排序）。"""
    OUTPUT_DIR.mkdir(exist_ok=True)
    return sorted(os.listdir(OUTPUT_DIR))


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse(
        request, "index.html", {"files": _list_files()}
    )


@app.post("/api/upload")
async def upload(audio: UploadFile = File(...), session_id: str = Form("")):
    data = await audio.read()
    result = run(data, audio.filename or "audio.wav", session_id or None)
    result["files"] = _list_files()
    return result


@app.post("/api/text")
async def text_command(text: str = Form(...), session_id: str = Form("")):
    result = run_text(text, session_id or None)
    result["files"] = _list_files()
    return result


@app.post("/api/tts")
async def tts(text: str = Form(...)):
    try:
        audio = await synthesize(text)
    except Exception as e:
        # 明确返回错误原因，前端据此提示用户而非静默失败
        return JSONResponse(status_code=500, content={"error": f"语音合成失败：{e}"})
    return Response(content=audio, media_type="audio/mpeg")


if __name__ == "__main__":
    # 默认监听 0.0.0.0，让同一局域网下的手机也能访问；只想本机用时设 HOST=127.0.0.1
    host = os.environ.get("HOST", "0.0.0.0")
    uvicorn.run("server:app", host=host, port=8000, reload=True)
