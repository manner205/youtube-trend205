"""
Tool: notion_schedule.py
역할: Gmail 발송 스케줄 설정을 Notion 페이지에 영구 저장
입력: config (dict)
출력: 저장/로드 성공 여부
"""

import json
import logging
import os

from dotenv import load_dotenv
from notion_client import Client

load_dotenv()
logger = logging.getLogger(__name__)

DEFAULT_CONFIG = {
    "enabled": False,
    "days": ["sun"],
    "time": "20:00",
    "frequency": "weekly",
    "topics": ["수익형 브랜드", "콘텐츠 수익화", "1인 사업 런칭"],
}


def _get_client():
    token = os.getenv("NOTION_TOKEN")
    if not token:
        raise ValueError("NOTION_TOKEN이 없어.")
    return Client(auth=token)


def load_config() -> dict:
    """Notion 페이지에서 스케줄 설정 로드. 없으면 기본값 반환."""
    page_id = os.getenv("NOTION_SCHEDULE_PAGE_ID")
    if not page_id:
        logger.warning("NOTION_SCHEDULE_PAGE_ID 없음 — 기본값 사용")
        return DEFAULT_CONFIG.copy()

    try:
        notion = _get_client()
        blocks = notion.blocks.children.list(block_id=page_id)
        for block in blocks.get("results", []):
            if block["type"] == "code":
                content = block["code"]["rich_text"][0]["text"]["content"]
                return json.loads(content)
    except Exception as e:
        logger.error(f"Notion 스케줄 로드 오류: {e}")

    return DEFAULT_CONFIG.copy()


def save_config(config: dict):
    """스케줄 설정을 Notion 페이지의 code 블록에 JSON으로 저장."""
    page_id = os.getenv("NOTION_SCHEDULE_PAGE_ID")
    if not page_id:
        logger.warning("NOTION_SCHEDULE_PAGE_ID 없음 — Notion 저장 건너뜀")
        return

    try:
        notion = _get_client()
        config_json = json.dumps(config, ensure_ascii=False, indent=2)

        # 기존 code 블록 찾기
        blocks = notion.blocks.children.list(block_id=page_id)
        code_block_id = None
        for block in blocks.get("results", []):
            if block["type"] == "code":
                code_block_id = block["id"]
                break

        if code_block_id:
            # 기존 블록 업데이트
            notion.blocks.update(
                block_id=code_block_id,
                **{
                    "code": {
                        "rich_text": [{"type": "text", "text": {"content": config_json}}],
                        "language": "json",
                    }
                },
            )
        else:
            # 최초 저장 — 새 code 블록 생성
            notion.blocks.children.append(
                block_id=page_id,
                children=[
                    {
                        "object": "block",
                        "type": "code",
                        "code": {
                            "rich_text": [{"type": "text", "text": {"content": config_json}}],
                            "language": "json",
                        },
                    }
                ],
            )

        logger.info("Notion 스케줄 설정 저장 완료")

    except Exception as e:
        logger.error(f"Notion 스케줄 저장 오류: {e}")
