"""
Tool: main.py
역할: 주간 트렌드 리포트 전체 파이프라인 오케스트레이터
실행: python tools/main.py
"""

import os
import sys
import logging
from datetime import datetime
from pathlib import Path

# 프로젝트 루트를 경로에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.youtube_collector import collect_all_data
from tools.claude_analyzer import analyze_trends
from tools.pdf_generator import generate_report
from tools.gmail_sender import send_report
from tools.notion_saver import save_weekly_data

# ── 로깅 설정 ─────────────────────────────────────────────────────────────────

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

def run():
    logger = setup_logging()
    start = datetime.now()
    logger.info("=" * 60)
    logger.info("유튜브 트렌드 주간 리포트 시작")
    logger.info("=" * 60)

    results = {
        "youtube": False,
        "claude": False,
        "pdf": None,
        "gmail": False,
        "notion": None,
    }

    # ── 1단계: YouTube 데이터 수집 ────────────────────────────────────────────
    logger.info("[1/5] YouTube 데이터 수집 중...")
    try:
        all_data = collect_all_data()
        results["youtube"] = True

        total_videos = sum(
            len(nd.get("videos", []))
            for nd in all_data.get("niches", {}).values()
        )
        logger.info(f"  수집 완료: 영상 {total_videos}개")
    except Exception as e:
        logger.error(f"  YouTube 수집 실패: {e}")
        logger.error("  YouTube 데이터 없이는 계속 진행할 수 없어.")
        sys.exit(1)

    # ── 2단계: Claude AI 분석 ─────────────────────────────────────────────────
    logger.info("[2/5] Claude AI 분석 중...")
    try:
        analysis = analyze_trends(all_data)
        results["claude"] = True
        logger.info(f"  분석 완료: 트렌딩 주제 {len(analysis.get('trending_topics', []))}개")
    except Exception as e:
        logger.error(f"  Claude 분석 실패: {e} — 기본 분석으로 대체")
        from tools.claude_analyzer import _fallback_analysis
        analysis = _fallback_analysis()

    # ── 3단계: PDF 리포트 생성 ────────────────────────────────────────────────
    logger.info("[3/5] PDF 리포트 생성 중...")
    try:
        pdf_path = generate_report(all_data, analysis)
        results["pdf"] = pdf_path
        logger.info(f"  PDF 생성 완료: {pdf_path}")
    except Exception as e:
        logger.error(f"  PDF 생성 실패: {e}")

    # ── 4단계: Gmail 발송 ─────────────────────────────────────────────────────
    if results["pdf"]:
        logger.info("[4/5] Gmail 발송 중...")
        week_str = all_data.get("week", "")
        results["gmail"] = send_report(results["pdf"], week_str)
        if results["gmail"]:
            logger.info("  이메일 발송 완료")
        else:
            logger.warning("  이메일 발송 실패 (PDF는 로컬 저장됨)")
    else:
        logger.warning("[4/5] PDF가 없어 Gmail 발송 건너뜀")

    # ── 5단계: Notion 저장 ────────────────────────────────────────────────────
    logger.info("[5/5] Notion 저장 중...")
    try:
        page_url = save_weekly_data(all_data, analysis)
        results["notion"] = page_url
        if page_url:
            logger.info(f"  Notion 저장 완료: {page_url}")
    except Exception as e:
        logger.error(f"  Notion 저장 실패: {e}")

    # ── 최종 보고 ─────────────────────────────────────────────────────────────
    elapsed = (datetime.now() - start).seconds
    logger.info("=" * 60)
    logger.info("실행 결과 요약")
    logger.info(f"  YouTube 수집 : {'✅' if results['youtube'] else '❌'}")
    logger.info(f"  Claude 분석  : {'✅' if results['claude'] else '⚠️ 대체'}")
    logger.info(f"  PDF 생성     : {'✅ ' + str(results['pdf']) if results['pdf'] else '❌'}")
    logger.info(f"  Gmail 발송   : {'✅' if results['gmail'] else '❌'}")
    logger.info(f"  Notion 저장  : {'✅' if results['notion'] else '❌'}")
    logger.info(f"  총 소요 시간 : {elapsed}초")
    logger.info("=" * 60)


if __name__ == "__main__":
    run()
