"""
Tool: cost_tracker.py
역할: API 사용량 및 예상 비용 추적
입력: 없음 (run 중 각 단계에서 add_* 메서드 호출)
출력: get_summary() → dict
"""


class CostTracker:
    # YouTube Data API v3 쿼터 단위
    _YT_SEARCH = 100   # search.list() 1회
    _YT_CHANNELS = 1   # channels.list() 1회
    _YT_PLAYLIST = 1   # playlistItems.list() 1회
    _YT_VIDEOS = 1     # videos.list() 1회
    YOUTUBE_DAILY_LIMIT = 10_000

    # Claude API 가격 (claude-haiku-4-5, USD per 1M tokens)
    CLAUDE_INPUT_PRICE = 0.80
    CLAUDE_OUTPUT_PRICE = 4.00

    # 환율 (대략)
    USD_TO_KRW = 1_350

    def __init__(self):
        self.youtube_quota = 0
        self.claude_input_tokens = 0
        self.claude_output_tokens = 0

    # ── YouTube 쿼터 추가 ──────────────────────────────────────────────────────

    def add_yt_search(self, count=1):
        self.youtube_quota += self._YT_SEARCH * count

    def add_yt_channels(self, count=1):
        self.youtube_quota += self._YT_CHANNELS * count

    def add_yt_playlist(self, count=1):
        self.youtube_quota += self._YT_PLAYLIST * count

    def add_yt_videos(self, count=1):
        self.youtube_quota += self._YT_VIDEOS * count

    # ── Claude 토큰 추가 ───────────────────────────────────────────────────────

    def add_claude_usage(self, input_tokens: int, output_tokens: int):
        self.claude_input_tokens += input_tokens
        self.claude_output_tokens += output_tokens

    # ── 비용 계산 ─────────────────────────────────────────────────────────────

    def _claude_cost_usd(self) -> float:
        input_cost = (self.claude_input_tokens / 1_000_000) * self.CLAUDE_INPUT_PRICE
        output_cost = (self.claude_output_tokens / 1_000_000) * self.CLAUDE_OUTPUT_PRICE
        return input_cost + output_cost

    def _yt_quota_pct(self) -> float:
        return round((self.youtube_quota / self.YOUTUBE_DAILY_LIMIT) * 100, 1)

    # ── 요약 반환 ─────────────────────────────────────────────────────────────

    def get_summary(self) -> dict:
        claude_usd = self._claude_cost_usd()
        claude_krw = claude_usd * self.USD_TO_KRW

        return {
            "youtube": {
                "quota_used": self.youtube_quota,
                "quota_limit": self.YOUTUBE_DAILY_LIMIT,
                "quota_pct": self._yt_quota_pct(),
                "note": "무료 (일일 한도 내 사용)",
            },
            "claude": {
                "input_tokens": self.claude_input_tokens,
                "output_tokens": self.claude_output_tokens,
                "total_tokens": self.claude_input_tokens + self.claude_output_tokens,
                "cost_usd": round(claude_usd, 4),
                "cost_krw": round(claude_krw, 0),
            },
            "gmail": {"note": "무료 (Gmail API)"},
            "notion": {"note": "무료 (Notion API)"},
            "total_usd": round(claude_usd, 4),
            "total_krw": round(claude_krw, 0),
        }
