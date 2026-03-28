"""
Tool: main.py
역할: 주간 트렌드 리포트 전체 파이프라인 오케스트레이터
실행: python tools/main.py
웹에서: run(topics=[...], send_email=True, progress_cb=fn) 으로 호출
"""

import os
import sys
import logging
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.youtube_collector import collect_all_data
from tools.claude_analyzer import analyze_trends
from tools.pdf_generator import generate_report
from tools.gmail_sender import send_report
from tools.notion_saver import save_weekly_data
from tools.cost_tracker import CostTracker

DEFAULT_TOPICS = ["수익형 브랜드", "콘텐츠 수익화", "1인 사업 런칭"]


# ── 로깅 설정 (직접 실행 시만 호출) ──────────────────────────────────────────

def setup_logging():
    os.makedirs("logs", exist_ok=True)
    log_file = f"logs/report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )
    return logging.getLogger("main")


# ── 메인 파이프라인 ───────────────────────────────────────────────────────────

def run(topics=None, send_email=True, progress_cb=None):
    """
    트렌드 리포트 파이프라인 실행.

    topics:      list[str] — 분석 주제. None이면 DEFAULT_TOPICS 사용.
    send_email:  bool      — Gmail 발송 여부.
    progress_cb: callable  — 진행 상황 콜백. fn({"step", "status", "message"})

    반환값: {
        "youtube": bool,
        "claude": bool,
        "pdf": str | None,
        "gmail": bool,
        "notion": str | None,
        "cost": dict,
        "elapsed": int,
    }
    """
    logger = logging.getLogger("main")
    start = datetime.now()

    if not topics:
        topics = DEFAULT_TOPICS

    cost_tracker = CostTracker()

    results = {
        "youtube": False,
        "claude": False,
        "pdf": None,
        "gmail": False,
        "notion": None,
        "cost": {},
        "elapsed": 0,
    }

    def progress(step, status, message=""):
        """진행 상황을 로그 + 콜백으로 전달"""
        logger.info(f"[{step}] {status}: {message}" if message else f"[{step}] {status}")
        if progress_cb:
            progress_cb({"step": step, "status": status, "message": message})

    logger.info("=" * 60)
    logger.info(f"유튜브 트렌드 리포트 시작 — 주제: {', '.join(topics)}")
    logger.info("=" * 60)

    # ── 1단계: YouTube 데이터 수집 ────────────────────────────────────────────
    progress("youtube", "running", "YouTube 데이터 수집 중...")
    try:
        all_data = collect_all_data(topics=topics, cost_tracker=cost_tracker)
        results["youtube"] = True
        total_videos = sum(
            len(nd.get("videos", []))
            for nd in all_data.get("niches", {}).values()
        )
        progress("youtube", "done", f"영상 {total_videos}개 수집 완료")
    except Exception as e:
        logger.error(f"YouTube 수집 실패: {e}")
        progress("youtube", "error", str(e))
        results["cost"] = cost_tracker.get_summary()
        results["elapsed"] = (datetime.now() - start).seconds
        return results

    # ── 2단계: Claude AI 분석 ─────────────────────────────────────────────────
    progress("claude", "running", "AI 분석 중...")
    try:
        analysis = analyze_trends(all_data, cost_tracker=cost_tracker)
        results["claude"] = True
        progress("claude", "done", f"트렌딩 주제 {len(analysis.get('trending_topics', []))}개 분석 완료")
    except Exception as e:
        logger.error(f"Claude 분석 실패: {e}")
        progress("claude", "error", str(e))
        from tools.claude_analyzer import _fallback_analysis
        analysis = _fallback_analysis()

    # ── 3단계: PDF 리포트 생성 ────────────────────────────────────────────────
    progress("pdf", "running", "PDF 생성 중...")
    try:
        cost_summary = cost_tracker.get_summary()
        pdf_path = generate_report(all_data, analysis, cost_summary=cost_summary)
        results["pdf"] = pdf_path
        progress("pdf", "done", pdf_path)
    except Exception as e:
        logger.error(f"PDF 생성 실패: {e}")
        progress("pdf", "error", str(e))

    # ── 4단계: Gmail 발송 ─────────────────────────────────────────────────────
    if send_email and results["pdf"]:
        progress("gmail", "running", "Gmail 발송 중...")
        week_str = all_data.get("week", "")
        ok = send_report(results["pdf"], week_str)
        results["gmail"] = ok
        progress("gmail", "done" if ok else "error",
                 "발송 완료" if ok else "발송 실패 (PDF는 로컬 저장됨)")
    else:
        progress("gmail", "skipped", "Gmail 발송 건너뜀")

    # ── 5단계: Notion 저장 ────────────────────────────────────────────────────
    progress("notion", "running", "Notion 저장 중...")
    try:
        page_url = save_weekly_data(all_data, analysis)
        results["notion"] = page_url
        progress("notion", "done", page_url or "저장 완료")
    except Exception as e:
        logger.error(f"Notion 저장 실패: {e}")
        progress("notion", "error", str(e))

    # ── 최종 ──────────────────────────────────────────────────────────────────
    results["cost"] = cost_tracker.get_summary()
    results["elapsed"] = (datetime.now() - start).seconds

    logger.info("=" * 60)
    logger.info("실행 결과 요약")
    logger.info(f"  YouTube 수집 : {'✅' if results['youtube'] else '❌'}")
    logger.info(f"  Claude 분석  : {'✅' if results['claude'] else '⚠️'}")
    logger.info(f"  PDF 생성     : {'✅ ' + str(results['pdf']) if results['pdf'] else '❌'}")
    logger.info(f"  Gmail 발송   : {'✅' if results['gmail'] else '❌'}")
    logger.info(f"  Notion 저장  : {'✅' if results['notion'] else '❌'}")
    logger.info(f"  총 소요 시간 : {results['elapsed']}초")
    logger.info("=" * 60)

    return results


if __name__ == "__main__":
    setup_logging()
    run()
