"""
app.py
역할: FastAPI 웹 서버 — 유튜브 트렌드 리포트 v2
실행: python app.py  또는  uvicorn app:app --reload
"""

import asyncio
import json
import logging
import os
import sys
import threading
import uuid
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).parent))

# ── 로깅 설정 ─────────────────────────────────────────────────────────────────
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    handlers=[
        logging.FileHandler(
            f"logs/web_{__import__('datetime').datetime.now().strftime('%Y%m%d')}.log",
            encoding="utf-8",
        ),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("app")

# ── FastAPI 앱 ────────────────────────────────────────────────────────────────
app = FastAPI(title="YouTube 트렌드 리포트 v2")
templates = Jinja2Templates(directory="templates")

# static 폴더가 있으면 마운트
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

# ── SSE 진행 상황 저장소 ──────────────────────────────────────────────────────
# run_id → asyncio.Queue
_progress_queues: dict[str, asyncio.Queue] = {}
_event_loop: asyncio.AbstractEventLoop | None = None


@app.on_event("startup")
async def startup():
    global _event_loop
    _event_loop = asyncio.get_event_loop()
    from tools.scheduler import start_scheduler
    start_scheduler()
    logger.info("웹 서버 시작 완료")


# ── 데이터 모델 ───────────────────────────────────────────────────────────────

class RunRequest(BaseModel):
    topics: list[str]
    send_email: bool = True


class ScheduleConfig(BaseModel):
    enabled: bool
    days: list[str]
    time: str
    frequency: str
    topics: list[str]


# ── 페이지 ────────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(request, "index.html")


# ── 리포트 실행 API ───────────────────────────────────────────────────────────

@app.post("/api/run")
async def run_report(req: RunRequest):
    """리포트 파이프라인 실행. run_id 반환 → /api/progress/{run_id} 로 진행 추적"""
    if not req.topics:
        return {"error": "주제를 최소 1개 입력해줘."}

    run_id = str(uuid.uuid4())[:8]
    queue: asyncio.Queue = asyncio.Queue()
    _progress_queues[run_id] = queue

    def _send(event: dict):
        """백그라운드 스레드에서 asyncio Queue에 안전하게 전달"""
        if _event_loop:
            asyncio.run_coroutine_threadsafe(queue.put(event), _event_loop)

    def _pipeline():
        try:
            from tools.main import run
            run(
                topics=req.topics,
                send_email=req.send_email,
                progress_cb=_send,
            )
        except Exception as e:
            _send({"step": "error", "status": "error", "message": str(e)})
        finally:
            _send(None)  # 종료 시그널

    thread = threading.Thread(target=_pipeline, daemon=True)
    thread.start()

    return {"run_id": run_id}


@app.get("/api/progress/{run_id}")
async def progress_stream(run_id: str):
    """SSE(Server-Sent Events)로 실행 진행 상황 실시간 전달"""
    if run_id not in _progress_queues:
        return {"error": "run_id를 찾을 수 없어."}

    queue = _progress_queues[run_id]

    async def generator():
        try:
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=120)
                except asyncio.TimeoutError:
                    yield "data: {\"ping\": true}\n\n"
                    continue

                if event is None:  # 종료
                    yield f"data: {json.dumps({'done': True})}\n\n"
                    break
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        finally:
            _progress_queues.pop(run_id, None)

    return StreamingResponse(
        generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# ── 스케줄 API ────────────────────────────────────────────────────────────────

@app.get("/api/schedule")
async def get_schedule():
    from tools.notion_schedule import load_config
    from tools.scheduler import get_next_run
    config = load_config()
    config["next_run"] = get_next_run()
    return config


@app.post("/api/schedule")
async def save_schedule(config: ScheduleConfig):
    from tools.scheduler import update_schedule
    data = config.model_dump()
    update_schedule(data)

    from tools.scheduler import get_next_run
    next_run = get_next_run()

    return {"ok": True, "next_run": next_run}


# ── 채널 캐시 API ─────────────────────────────────────────────────────────────

@app.get("/api/cache/status")
async def cache_status():
    """채널 캐시 상태 조회"""
    cache_file = "data/channel_cache.json"
    if not os.path.exists(cache_file):
        return {"exists": False, "saved_at": None, "niche_count": 0}
    with open(cache_file, "r", encoding="utf-8") as f:
        cache = json.load(f)
    saved_at = cache.get("_saved_at")
    niche_count = len([k for k in cache if not k.startswith("_")])
    return {"exists": True, "saved_at": saved_at, "niche_count": niche_count}


@app.post("/api/cache/clear")
async def clear_cache():
    """채널 캐시 삭제 — 다음 실행 시 채널을 새로 검색"""
    cache_file = "data/channel_cache.json"
    if os.path.exists(cache_file):
        os.remove(cache_file)
        logger.info("채널 캐시 수동 삭제")
        return {"ok": True, "message": "캐시가 삭제됐습니다. 다음 리포트 생성 시 채널을 새로 검색합니다."}
    return {"ok": True, "message": "삭제할 캐시가 없습니다."}


# ── 리포트 파일 API ───────────────────────────────────────────────────────────

@app.get("/api/reports")
async def list_reports():
    """생성된 PDF 목록 반환 (최신순)"""
    report_dir = "data/reports"
    if not os.path.exists(report_dir):
        return []
    files = sorted(
        [f for f in os.listdir(report_dir) if f.endswith(".pdf")],
        reverse=True,
    )
    return files


@app.get("/api/reports/{filename}")
async def download_report(filename: str):
    """PDF 다운로드"""
    # 경로 탈출 방지
    safe_name = Path(filename).name
    path = f"data/reports/{safe_name}"
    if not os.path.exists(path):
        return {"error": "파일을 찾을 수 없어."}
    return FileResponse(path, filename=safe_name, media_type="application/pdf")


# ── 직접 실행 ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=False)
