"""
Tool: youtube_collector.py
역할: YouTube Data API v3로 동적 주제별 탑 채널 및 인기 영상 수집
입력: topics (list[str]) — 예: ["수익형 브랜드", "AI 부업"]
출력: dict (주제별 채널 + 영상 데이터)
"""

import os
import re
import json
import logging
from datetime import datetime, timedelta, timezone

from googleapiclient.discovery import build
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

CHANNEL_CACHE_FILE = "data/channel_cache.json"

# 기본 주제 (웹에서 입력 없을 때 fallback)
DEFAULT_TOPICS = ["수익형 브랜드", "콘텐츠 수익화", "1인 사업 런칭"]


# ── 클라이언트 초기화 ─────────────────────────────────────────────────────────

def get_youtube_client():
    api_key = os.getenv("YOUTUBE_API_KEY")
    if not api_key:
        raise ValueError("YOUTUBE_API_KEY가 .env 파일에 없어.")
    return build("youtube", "v3", developerKey=api_key)


# ── 동적 NICHES 생성 ──────────────────────────────────────────────────────────

def _build_niches(topics: list) -> dict:
    """
    사용자 입력 주제 리스트로 NICHES 딕셔너리 생성.
    키워드: 한국어 3개 (주제, 주제+방법, 주제+전략)
    """
    niches = {}
    for topic in topics:
        key = topic.strip().replace(" ", "_")
        niches[key] = {
            "name": topic.strip(),
            "keywords_ko": [topic, f"{topic} 방법", f"{topic} 전략"],
            "keywords_en": [topic],
        }
    return niches


# ── 채널 검색 (100 유닛/호출) ─────────────────────────────────────────────────

def search_channels(youtube, keyword, region_code="KR", language="ko", max_results=5):
    try:
        resp = youtube.search().list(
            q=keyword,
            type="channel",
            regionCode=region_code,
            relevanceLanguage=language,
            maxResults=max_results,
            part="snippet",
            order="relevance",
        ).execute()
        return [
            {"channel_id": item["snippet"]["channelId"], "title": item["snippet"]["title"]}
            for item in resp.get("items", [])
        ]
    except Exception as e:
        logger.error(f"채널 검색 오류 ({keyword}): {e}")
        return []


# ── 채널 통계 조회 (1 유닛/호출) ──────────────────────────────────────────────

def get_channel_stats(youtube, channel_ids):
    if not channel_ids:
        return {}
    try:
        resp = youtube.channels().list(
            id=",".join(channel_ids[:50]),
            part="statistics,snippet",
        ).execute()
        result = {}
        for item in resp.get("items", []):
            s = item["statistics"]
            result[item["id"]] = {
                "channel_id": item["id"],
                "title": item["snippet"]["title"],
                "subscriber_count": int(s.get("subscriberCount", 0)),
                "video_count": int(s.get("videoCount", 0)),
                "view_count": int(s.get("viewCount", 0)),
            }
        return result
    except Exception as e:
        logger.error(f"채널 통계 조회 오류: {e}")
        return {}


# ── 업로드 플레이리스트 ID 조회 (1 유닛) ─────────────────────────────────────

def get_uploads_playlist_id(youtube, channel_id):
    try:
        resp = youtube.channels().list(
            id=channel_id,
            part="contentDetails",
        ).execute()
        items = resp.get("items", [])
        if items:
            return items[0]["contentDetails"]["relatedPlaylists"]["uploads"]
        return None
    except Exception as e:
        logger.error(f"플레이리스트 조회 오류 ({channel_id}): {e}")
        return None


# ── 플레이리스트 최근 영상 목록 (1 유닛) ─────────────────────────────────────

def get_playlist_video_ids(youtube, playlist_id, max_results=15):
    try:
        resp = youtube.playlistItems().list(
            playlistId=playlist_id,
            part="snippet",
            maxResults=max_results,
        ).execute()
        return [
            {
                "video_id": item["snippet"]["resourceId"]["videoId"],
                "published_at": item["snippet"]["publishedAt"],
            }
            for item in resp.get("items", [])
        ]
    except Exception as e:
        logger.error(f"플레이리스트 영상 조회 오류: {e}")
        return []


# ── 영상 상세 정보 (1 유닛/호출) ──────────────────────────────────────────────

def get_video_details(youtube, video_ids):
    if not video_ids:
        return []
    try:
        resp = youtube.videos().list(
            id=",".join(video_ids[:50]),
            part="snippet,statistics,contentDetails",
        ).execute()
        videos = []
        for item in resp.get("items", []):
            s = item["statistics"]
            snippet = item["snippet"]
            duration = item["contentDetails"]["duration"]
            is_shorts = _is_shorts(duration, snippet.get("title", ""))
            videos.append({
                "video_id": item["id"],
                "title": snippet["title"],
                "channel_id": snippet["channelId"],
                "channel_title": snippet["channelTitle"],
                "published_at": snippet["publishedAt"],
                "tags": snippet.get("tags", [])[:10],
                "view_count": int(s.get("viewCount", 0)),
                "like_count": int(s.get("likeCount", 0)),
                "comment_count": int(s.get("commentCount", 0)),
                "duration": duration,
                "is_shorts": is_shorts,
                "format": "쇼츠" if is_shorts else "일반 영상",
            })
        return videos
    except Exception as e:
        logger.error(f"영상 상세 조회 오류: {e}")
        return []


def _is_shorts(duration, title):
    if "#shorts" in title.lower() or "#short" in title.lower():
        return True
    match = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", duration)
    if match:
        total = (
            int(match.group(1) or 0) * 3600
            + int(match.group(2) or 0) * 60
            + int(match.group(3) or 0)
        )
        return total <= 60
    return False


# ── 채널 캐시 ─────────────────────────────────────────────────────────────────

CACHE_EXPIRE_DAYS = 40


def load_channel_cache():
    os.makedirs("data", exist_ok=True)
    if os.path.exists(CHANNEL_CACHE_FILE):
        with open(CHANNEL_CACHE_FILE, "r", encoding="utf-8") as f:
            cache = json.load(f)
        saved_at_str = cache.get("_saved_at")
        if saved_at_str:
            saved_at = datetime.fromisoformat(saved_at_str)
            age_days = (datetime.now() - saved_at).days
            if age_days >= CACHE_EXPIRE_DAYS:
                logger.info(f"채널 캐시가 {age_days}일 경과 (만료 기준: {CACHE_EXPIRE_DAYS}일) → 캐시 초기화 후 재검색")
                return {}
        return {k: v for k, v in cache.items() if not k.startswith("_")}
    return {}


def save_channel_cache(cache):
    os.makedirs("data", exist_ok=True)
    data = {"_saved_at": datetime.now().isoformat(), **cache}
    with open(CHANNEL_CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ── 메인 수집 함수 ────────────────────────────────────────────────────────────

def collect_all_data(topics=None, cost_tracker=None):
    """
    주제별 YouTube 데이터 수집.

    topics: list[str] — 분석할 주제 목록. None이면 DEFAULT_TOPICS 사용.
    cost_tracker: CostTracker 인스턴스 (선택)

    반환값: {
        "collected_at": str,
        "week": str,
        "topics": list[str],
        "niches": { niche_key: { "name", "channels", "videos" } }
    }
    """
    if not topics:
        topics = DEFAULT_TOPICS

    niches = _build_niches(topics)
    youtube = get_youtube_client()
    channel_cache = load_channel_cache()
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)

    result = {
        "collected_at": datetime.now().isoformat(),
        "week": datetime.now().strftime("%Y-W%V"),
        "topics": topics,
        "niches": {},
    }

    for niche_key, niche_info in niches.items():
        logger.info(f"[{niche_info['name']}] 수집 시작")
        niche_data = {"name": niche_info["name"], "channels": [], "videos": []}

        # 채널 ID 수집 (캐시 우선)
        if niche_key in channel_cache:
            logger.info(f"  캐시된 채널 {len(channel_cache[niche_key])}개 사용")
            channel_ids = channel_cache[niche_key]
        else:
            channel_ids = []

            for kw in niche_info["keywords_ko"]:
                found = search_channels(youtube, kw, region_code="KR", language="ko", max_results=3)
                channel_ids += [c["channel_id"] for c in found]
                if cost_tracker:
                    cost_tracker.add_yt_search()

            if len(set(channel_ids)) < 5:
                logger.info("  한국 채널 부족 → 영어권 채널 보완")
                for kw in niche_info["keywords_en"]:
                    found = search_channels(youtube, kw, region_code="US", language="en", max_results=3)
                    channel_ids += [c["channel_id"] for c in found]
                    if cost_tracker:
                        cost_tracker.add_yt_search()

            channel_ids = list(dict.fromkeys(channel_ids))
            channel_cache[niche_key] = channel_ids
            save_channel_cache(channel_cache)

        # 채널 통계 → 구독자 수 기준 상위 5개
        stats = get_channel_stats(youtube, channel_ids)
        if cost_tracker:
            cost_tracker.add_yt_channels()
        top_channels = sorted(stats.values(), key=lambda x: x["subscriber_count"], reverse=True)[:5]
        niche_data["channels"] = top_channels

        # 상위 3개 채널의 최근 7일 영상 수집
        all_video_ids = []
        for ch in top_channels[:3]:
            playlist_id = get_uploads_playlist_id(youtube, ch["channel_id"])
            if cost_tracker:
                cost_tracker.add_yt_channels()  # contentDetails 조회
            if not playlist_id:
                continue
            recent = get_playlist_video_ids(youtube, playlist_id, max_results=15)
            if cost_tracker:
                cost_tracker.add_yt_playlist()
            for v in recent:
                pub = datetime.fromisoformat(v["published_at"].replace("Z", "+00:00"))
                if pub >= cutoff:
                    all_video_ids.append(v["video_id"])

        # 영상 상세 정보 → 조회수 기준 상위 20개
        if all_video_ids:
            details = get_video_details(youtube, list(dict.fromkeys(all_video_ids)))
            if cost_tracker:
                cost_tracker.add_yt_videos()
            details.sort(key=lambda x: x["view_count"], reverse=True)
            niche_data["videos"] = details[:20]

        result["niches"][niche_key] = niche_data
        logger.info(f"  완료: 채널 {len(top_channels)}개, 영상 {len(niche_data['videos'])}개")

    return result
