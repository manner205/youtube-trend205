"""
Tool: notion_saver.py
역할: 주간 트렌드 데이터를 Notion 데이터베이스에 누적 저장
입력: all_data (dict), analysis (dict)
출력: 생성된 Notion 페이지 URL (str) 또는 None
"""

import os
import logging
from datetime import datetime

from notion_client import Client
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


def _get_client():
    token = os.getenv("NOTION_TOKEN")
    if not token:
        raise ValueError("NOTION_TOKEN이 .env 파일에 없어.")
    return Client(auth=token)


def save_weekly_data(all_data, analysis):
    """
    Notion 데이터베이스에 주간 리포트 페이지 생성.
    반환: 생성된 페이지 URL (str) 또는 None (실패 시)
    """
    db_id = os.getenv("NOTION_DATABASE_ID")
    if not db_id:
        raise ValueError("NOTION_DATABASE_ID가 .env 파일에 없어.")

    notion = _get_client()
    week_str = all_data.get("week", datetime.now().strftime("%Y-W%V"))
    date_str = datetime.now().strftime("%Y-%m-%d")

    # 상위 채널명 수집 (분야별)
    channel_summaries = {}
    for niche_key, nd in all_data.get("niches", {}).items():
        top = [ch["title"] for ch in nd.get("channels", [])[:3]]
        channel_summaries[nd["name"]] = ", ".join(top)

    # 트렌딩 주제 텍스트
    topics_text = "\n".join(
        f"#{t['rank']} {t['topic']}"
        for t in analysis.get("trending_topics", [])
    )

    # 콘텐츠 추천 텍스트
    recs_text = "\n".join(
        f"{i+1}. {r['title_idea']} ({r.get('format', '')})"
        for i, r in enumerate(analysis.get("content_recommendations", []))
    )

    try:
        # 1. 데이터베이스에 요약 행(row) 생성 — 이름만 저장, 상세 내용은 페이지 블록으로
        page = notion.pages.create(
            parent={"database_id": db_id},
            properties={
                "이름": {
                    "title": [{"text": {"content": f"{week_str} 트렌드 리포트"}}]
                },
            },
        )
        page_id = page["id"]
        page_url = page.get("url", "")

        # 2. 페이지에 상세 내용 블록 추가
        _append_detail_blocks(notion, page_id, all_data, analysis, week_str)

        logger.info(f"Notion 저장 완료: {page_url}")
        return page_url

    except Exception as e:
        logger.error(f"Notion 저장 오류: {e}")
        return None


def _append_detail_blocks(notion, page_id, all_data, analysis, week_str):
    """페이지에 상세 분석 내용을 블록으로 추가"""
    blocks = []

    # 핵심 인사이트 콜아웃
    blocks.append({
        "object": "block",
        "type": "callout",
        "callout": {
            "rich_text": [{"type": "text", "text": {"content": analysis.get("key_insight", "")}}],
            "icon": {"emoji": "💡"},
        },
    })

    # 주간 요약
    blocks.append(_heading2("주간 요약"))
    blocks.append(_paragraph(analysis.get("weekly_summary", "")))

    # 트렌딩 주제 TOP 5
    blocks.append(_heading2("트렌딩 주제 TOP 5"))
    for t in analysis.get("trending_topics", []):
        blocks.append(_bullet(f"#{t['rank']} {t['topic']} — {t.get('reason', '')}"))

    # 포맷 분석
    blocks.append(_heading2("콘텐츠 포맷 분석"))
    fmt = analysis.get("format_analysis", {})
    for label, key in [
        ("쇼츠 트렌드", "shorts_trend"),
        ("장편 영상 트렌드", "long_form_trend"),
        ("최고 성과 포맷", "best_performing_format"),
        ("최적 영상 길이", "optimal_length"),
    ]:
        blocks.append(_bullet(f"{label}: {fmt.get(key, '')}"))

    # 분야별 채널 & 영상
    blocks.append(_heading2("분야별 채널 분석"))
    for nd in all_data.get("niches", {}).values():
        blocks.append(_heading3(nd["name"]))
        for ch in nd.get("channels", [])[:5]:
            blocks.append(_bullet(
                f"{ch['title']} — 구독자 {ch['subscriber_count']:,}명"
            ))
        if nd.get("videos"):
            blocks.append(_paragraph("이번 주 인기 영상:"))
            for v in nd["videos"][:5]:
                blocks.append(_bullet(
                    f"[{v['format']}] {v['title']} | {v['view_count']:,}회"
                ))

    # 콘텐츠 추천
    blocks.append(_heading2("이번 주 콘텐츠 주제 추천"))
    for i, rec in enumerate(analysis.get("content_recommendations", []), 1):
        blocks.append(_bullet(
            f"{i}. {rec['title_idea']} ({rec.get('format', '')}) — {rec.get('reason', '')}"
        ))
        if rec.get("hook_suggestion"):
            blocks.append(_bullet(f"훅 아이디어: {rec['hook_suggestion']}"))

    # Notion API 블록 한 번에 최대 100개 추가
    for i in range(0, len(blocks), 100):
        notion.blocks.children.append(block_id=page_id, children=blocks[i:i + 100])


# ── 블록 헬퍼 ─────────────────────────────────────────────────────────────────

def _heading2(text):
    return {"object": "block", "type": "heading_2",
            "heading_2": {"rich_text": [{"type": "text", "text": {"content": text}}]}}

def _heading3(text):
    return {"object": "block", "type": "heading_3",
            "heading_3": {"rich_text": [{"type": "text", "text": {"content": text}}]}}

def _paragraph(text):
    return {"object": "block", "type": "paragraph",
            "paragraph": {"rich_text": [{"type": "text", "text": {"content": str(text)[:2000]}}]}}

def _bullet(text):
    return {"object": "block", "type": "bulleted_list_item",
            "bulleted_list_item": {"rich_text": [{"type": "text", "text": {"content": str(text)[:2000]}}]}}
