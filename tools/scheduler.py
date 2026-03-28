"""
Tool: scheduler.py
역할: Gmail 발송 스케줄 관리 (APScheduler 기반)
설정 파일: data/schedule_config.json
"""

import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from tools.notion_schedule import load_config, save_config

logger = logging.getLogger(__name__)

_scheduler = BackgroundScheduler(timezone="Asia/Seoul")


# ── 스케줄 실행 함수 ──────────────────────────────────────────────────────────

def _run_scheduled_report():
    """APScheduler가 호출하는 실제 파이프라인 실행"""
    config = load_config()
    topics = config.get("topics", DEFAULT_CONFIG["topics"])
    logger.info(f"[스케줄] 자동 실행 시작 — 주제: {topics}")
    try:
        from tools.main import run
        run(topics=topics, send_email=True)
    except Exception as e:
        logger.error(f"[스케줄] 자동 실행 오류: {e}")


# ── 스케줄러 시작 / 업데이트 ──────────────────────────────────────────────────

def start_scheduler():
    """앱 시작 시 1회 호출. 설정에 따라 스케줄 등록."""
    if not _scheduler.running:
        _scheduler.start()
        logger.info("APScheduler 시작")

    config = load_config()
    if config.get("enabled"):
        _apply_schedule(config)
        logger.info(f"스케줄 로드: {config['days']} {config['time']}")


def update_schedule(config: dict):
    """웹 UI에서 설정 변경 시 호출."""
    save_config(config)
    _scheduler.remove_all_jobs()

    if config.get("enabled"):
        _apply_schedule(config)
        logger.info(f"스케줄 업데이트: {config['days']} {config['time']}")
    else:
        logger.info("스케줄 비활성화")


def _apply_schedule(config: dict):
    """CronTrigger로 스케줄 등록"""
    days = config.get("days", ["sun"])
    time_str = config.get("time", "20:00")
    hour, minute = time_str.split(":")
    day_of_week = ",".join(days)

    _scheduler.add_job(
        _run_scheduled_report,
        CronTrigger(day_of_week=day_of_week, hour=int(hour), minute=int(minute)),
        id="trend_report",
        replace_existing=True,
        misfire_grace_time=3600,  # 1시간 내 놓쳐도 실행
    )


def get_next_run() -> str:
    """다음 실행 예정 시간 반환 (없으면 빈 문자열)"""
    job = _scheduler.get_job("trend_report")
    if job and job.next_run_time:
        return job.next_run_time.strftime("%Y-%m-%d %H:%M")
    return ""
