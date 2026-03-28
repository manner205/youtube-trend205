"""
Tool: claude_analyzer.py
역할: 수집된 YouTube 데이터를 Claude API로 분석해 인사이트 생성
입력: all_data (dict), cost_tracker (CostTracker, 선택)
출력: 분석 결과 dict
"""

import os
import json
import logging

import anthropic
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


def analyze_trends(all_data, cost_tracker=None):
    """
    YouTube 데이터를 Claude로 분석.
    반환값: {
        "trending_topics": [...],
        "format_analysis": {...},
        "channel_insights": [...],
        "content_recommendations": [...],
        "weekly_summary": str,
        "key_insight": str
    }
    """
    client = anthropic.Anthropic()
    model = os.getenv("CLAUDE_MODEL", "claude-haiku-4-5-20251001")

    # 실제 분석 주제명 추출 (동적)
    topic_names = [nd["name"] for nd in all_data.get("niches", {}).values()]
    topics_str = ", ".join(topic_names) if topic_names else "유튜브 트렌드"

    data_summary = _prepare_summary(all_data)

    prompt = f"""당신은 유튜브 콘텐츠 트렌드 전문 애널리스트입니다.
아래는 이번 주 수집한 YouTube 데이터입니다.
분야: {topics_str}

=== 수집 데이터 ===
{data_summary}

아래 JSON 형식으로 분석 결과를 반환해주세요. JSON 외 다른 텍스트는 포함하지 마세요.

{{
  "trending_topics": [
    {{
      "rank": 1,
      "topic": "주제명",
      "reason": "이유 (반드시 수집 데이터 기반)",
      "evidence": "근거 채널 또는 영상 제목"
    }}
  ],
  "format_analysis": {{
    "shorts_trend": "쇼츠 트렌드 분석",
    "long_form_trend": "장편 영상 트렌드 분석",
    "best_performing_format": "가장 성과 좋은 포맷과 이유",
    "optimal_length": "데이터 기반 최적 영상 길이"
  }},
  "channel_insights": [
    {{
      "channel": "채널명",
      "strength": "이 채널의 핵심 강점",
      "content_strategy": "콘텐츠 전략 분석"
    }}
  ],
  "content_recommendations": [
    {{
      "title_idea": "구체적인 영상 제목 아이디어",
      "niche": "해당 분야",
      "format": "쇼츠 또는 일반 영상",
      "reason": "이 주제를 추천하는 데이터 근거",
      "hook_suggestion": "첫 5초 훅 아이디어"
    }}
  ],
  "weekly_summary": "이번 주 전체 트렌드를 2-3문장으로 요약",
  "key_insight": "가장 중요한 인사이트를 1문장으로"
}}

trending_topics는 5개, channel_insights는 3개, content_recommendations는 5개 작성해주세요."""

    try:
        response = client.messages.create(
            model=model,
            max_tokens=6000,
            messages=[{"role": "user", "content": prompt}],
        )

        # 토큰 사용량 추적
        if cost_tracker and hasattr(response, "usage"):
            cost_tracker.add_claude_usage(
                response.usage.input_tokens,
                response.usage.output_tokens,
            )

        text = response.content[0].text.strip()

        # 마크다운 코드블록 제거
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()

        return json.loads(text)

    except json.JSONDecodeError as e:
        logger.error(f"Claude 응답 JSON 파싱 오류: {e}")
        return _fallback_analysis()
    except Exception as e:
        logger.error(f"Claude API 오류: {e}")
        return _fallback_analysis()


def _prepare_summary(all_data):
    """데이터를 프롬프트용 텍스트로 변환"""
    lines = []
    for niche_data in all_data.get("niches", {}).values():
        lines.append(f"\n## {niche_data['name']}")

        lines.append("### 상위 채널")
        for ch in niche_data.get("channels", [])[:5]:
            lines.append(
                f"- {ch['title']}: 구독자 {ch['subscriber_count']:,}명, "
                f"총 조회수 {ch['view_count']:,}"
            )

        lines.append("### 이번 주 인기 영상 TOP 10")
        for v in niche_data.get("videos", [])[:10]:
            tag_str = ", ".join(v.get("tags", [])[:5])
            lines.append(
                f"- [{v['format']}] {v['title']} | 조회수: {v['view_count']:,} "
                f"| 채널: {v['channel_title']}"
            )
            if tag_str:
                lines.append(f"  태그: {tag_str}")

    return "\n".join(lines)


def _fallback_analysis():
    """API 오류 시 기본 반환값"""
    return {
        "trending_topics": [
            {"rank": i, "topic": "분석 불가", "reason": "Claude API 오류", "evidence": ""}
            for i in range(1, 6)
        ],
        "format_analysis": {
            "shorts_trend": "분석 불가",
            "long_form_trend": "분석 불가",
            "best_performing_format": "분석 불가",
            "optimal_length": "분석 불가",
        },
        "channel_insights": [],
        "content_recommendations": [],
        "weekly_summary": "Claude API 오류로 분석을 완료하지 못했습니다. 수집 데이터는 리포트에 포함됩니다.",
        "key_insight": "API 오류로 인사이트 생성 불가",
    }
