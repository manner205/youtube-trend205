"""
Tool: pdf_generator.py
역할: 수집 데이터 + Claude 분석 결과로 한국어 PDF 리포트 생성
입력: all_data (dict), analysis (dict)
출력: PDF 파일 경로 (str)
"""

import os
import logging
from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from fpdf import FPDF

logger = logging.getLogger(__name__)

# Windows 한국어 폰트 경로
_FONT_REGULAR = r"C:\Windows\Fonts\malgun.ttf"
_FONT_BOLD = r"C:\Windows\Fonts\malgunbd.ttf"

# 브랜드 컬러
COLOR_NAVY = (30, 30, 60)
COLOR_BLUE = (58, 95, 176)
COLOR_LIGHT = (240, 244, 255)
COLOR_WHITE = (255, 255, 255)
COLOR_GRAY = (100, 100, 100)


# ── PDF 클래스 ────────────────────────────────────────────────────────────────

class ReportPDF(FPDF):
    def __init__(self, week_str):
        super().__init__()
        self.week_str = week_str
        self._font = "Malgun" if os.path.exists(_FONT_REGULAR) else "Helvetica"
        if self._font == "Malgun":
            self.add_font("Malgun", "", _FONT_REGULAR)
            self.add_font("Malgun", "B", _FONT_BOLD)

    def header(self):
        self.set_fill_color(*COLOR_NAVY)
        self.set_text_color(*COLOR_WHITE)
        self.set_font(self._font, "B", 9)
        self.cell(0, 9, f"  유튜브 트렌드 주간 리포트  |  {self.week_str}", fill=True,
                  new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(0, 0, 0)
        self.ln(4)

    def footer(self):
        self.set_y(-13)
        self.set_font(self._font, "", 8)
        self.set_text_color(*COLOR_GRAY)
        self.cell(0, 8,
                  f"페이지 {self.page_no()}  |  자동 생성: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                  align="C")

    # 섹션 제목 (진한 배경)
    def section_title(self, title):
        self.set_fill_color(*COLOR_NAVY)
        self.set_text_color(*COLOR_WHITE)
        self.set_font(self._font, "B", 12)
        self.cell(0, 9, f"  {title}", fill=True, new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(0, 0, 0)
        self.ln(3)

    # 소제목
    def sub_title(self, title):
        self.set_font(self._font, "B", 10)
        self.set_text_color(*COLOR_BLUE)
        self.cell(0, 7, title, new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(0, 0, 0)
        self.set_draw_color(*COLOR_BLUE)
        self.line(self.l_margin, self.get_y(), self.l_margin + 180, self.get_y())
        self.ln(2)

    # 본문 텍스트
    def body(self, text, indent=0):
        self.set_font(self._font, "", 10)
        if indent:
            self.set_x(self.l_margin + indent)
        self.multi_cell(0, 6, str(text))
        self.ln(1)

    # 강조 박스
    def highlight_box(self, text):
        self.set_fill_color(*COLOR_LIGHT)
        self.set_draw_color(*COLOR_NAVY)
        self.set_font(self._font, "B", 10)
        self.set_text_color(*COLOR_NAVY)
        self.multi_cell(0, 8, text, border=1, fill=True)
        self.set_text_color(0, 0, 0)
        self.ln(3)


# ── 차트 생성 ─────────────────────────────────────────────────────────────────

def _setup_korean_font():
    if os.path.exists(_FONT_REGULAR):
        fe = fm.FontEntry(fname=_FONT_REGULAR, name="MalgunGothic")
        fm.fontManager.ttflist.insert(0, fe)
        plt.rcParams["font.family"] = "MalgunGothic"
    plt.rcParams["axes.unicode_minus"] = False


def generate_charts(data, chart_dir="data/charts"):
    os.makedirs(chart_dir, exist_ok=True)
    _setup_korean_font()
    paths = {}

    # 1. 분야별 평균 조회수 막대 차트
    names, avgs = [], []
    for nd in data.get("niches", {}).values():
        vids = nd.get("videos", [])
        if vids:
            names.append(nd["name"])
            avgs.append(sum(v["view_count"] for v in vids) / len(vids) / 10000)

    if names:
        fig, ax = plt.subplots(figsize=(8, 4))
        bars = ax.bar(names, avgs, color=["#1e1e3c", "#3a5fb0", "#6b9bd2"])
        ax.set_ylabel("평균 조회수 (만)")
        ax.set_title("분야별 평균 조회수 비교")
        for b, v in zip(bars, avgs):
            ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 0.3,
                    f"{v:.1f}만", ha="center", fontsize=9)
        plt.tight_layout()
        p = f"{chart_dir}/avg_views.png"
        plt.savefig(p, dpi=150, bbox_inches="tight")
        plt.close()
        paths["avg_views"] = p

    # 2. 쇼츠 vs 일반 영상 파이 차트
    counts = {"쇼츠": 0, "일반 영상": 0}
    for nd in data.get("niches", {}).values():
        for v in nd.get("videos", []):
            counts[v.get("format", "일반 영상")] += 1

    if sum(counts.values()) > 0:
        fig, ax = plt.subplots(figsize=(5, 4))
        ax.pie(counts.values(), labels=counts.keys(), autopct="%1.1f%%",
               colors=["#1e1e3c", "#6b9bd2"], startangle=90)
        ax.set_title("쇼츠 vs 일반 영상 비율")
        plt.tight_layout()
        p = f"{chart_dir}/format_ratio.png"
        plt.savefig(p, dpi=150, bbox_inches="tight")
        plt.close()
        paths["format_ratio"] = p

    return paths


# ── 리포트 생성 ───────────────────────────────────────────────────────────────

def generate_report(data, analysis, output_dir="data/reports"):
    os.makedirs(output_dir, exist_ok=True)
    week_str = data.get("week", datetime.now().strftime("%Y-W%V"))
    date_str = datetime.now().strftime("%Y%m%d")
    output_path = f"{output_dir}/trend_report_{date_str}.pdf"

    charts = generate_charts(data)

    pdf = ReportPDF(week_str)
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # ── 표지 ──
    pdf.ln(8)
    pdf.set_font(pdf._font, "B", 20)
    pdf.set_text_color(*COLOR_NAVY)
    pdf.cell(0, 14, "유튜브 트렌드 주간 리포트", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font(pdf._font, "", 12)
    pdf.set_text_color(*COLOR_GRAY)
    pdf.cell(0, 8,
             f"{week_str}  |  수익형 브랜드 · 콘텐츠 수익화 · 1인 사업 런칭",
             align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(0, 0, 0)
    pdf.ln(6)

    pdf.highlight_box(f"💡 이번 주 핵심 인사이트\n{analysis.get('key_insight', '')}")

    # ── 1. 주간 요약 ──
    pdf.section_title("1. 주간 트렌드 요약")
    pdf.body(analysis.get("weekly_summary", ""))

    # ── 2. 트렌딩 주제 TOP 5 ──
    pdf.section_title("2. 이번 주 트렌딩 주제 TOP 5")
    for t in analysis.get("trending_topics", []):
        pdf.set_font(pdf._font, "B", 11)
        pdf.cell(0, 7, f"#{t.get('rank', '')}  {t.get('topic', '')}", new_x="LMARGIN", new_y="NEXT")
        pdf.body(f"이유: {t.get('reason', '')}", indent=8)
        if t.get("evidence"):
            pdf.set_font(pdf._font, "", 9)
            pdf.set_text_color(*COLOR_GRAY)
            pdf.set_x(pdf.l_margin + 8)
            pdf.multi_cell(0, 5, f"근거: {t['evidence']}")
            pdf.set_text_color(0, 0, 0)
        pdf.ln(2)

    # ── 3. 포맷 분석 ──
    pdf.add_page()
    pdf.section_title("3. 콘텐츠 포맷 분석")
    fmt = analysis.get("format_analysis", {})
    for label, key in [
        ("쇼츠 트렌드", "shorts_trend"),
        ("장편 영상 트렌드", "long_form_trend"),
        ("최고 성과 포맷", "best_performing_format"),
        ("최적 영상 길이", "optimal_length"),
    ]:
        pdf.set_font(pdf._font, "B", 10)
        pdf.cell(42, 7, f"{label}:", new_x="END", new_y="TOP")
        pdf.set_font(pdf._font, "", 10)
        pdf.multi_cell(0, 7, fmt.get(key, ""))
        pdf.ln(1)

    if "format_ratio" in charts and os.path.exists(charts["format_ratio"]):
        pdf.ln(4)
        pdf.image(charts["format_ratio"], x=55, w=100)

    # ── 4. 분야별 채널 분석 ──
    pdf.add_page()
    pdf.section_title("4. 분야별 탑 채널 분석")

    for nd in data.get("niches", {}).values():
        pdf.sub_title(f"■ {nd['name']}")

        channels = nd.get("channels", [])[:5]
        if channels:
            # 테이블 헤더
            pdf.set_fill_color(*COLOR_NAVY)
            pdf.set_text_color(*COLOR_WHITE)
            pdf.set_font(pdf._font, "B", 9)
            pdf.cell(72, 7, "채널명", border=1, fill=True)
            pdf.cell(36, 7, "구독자", border=1, fill=True, align="C")
            pdf.cell(36, 7, "총 조회수", border=1, fill=True, align="C")
            pdf.cell(0, 7, "영상 수", border=1, fill=True, align="C",
                     new_x="LMARGIN", new_y="NEXT")
            pdf.set_text_color(0, 0, 0)

            for i, ch in enumerate(channels):
                fill = (i % 2 == 0)
                pdf.set_fill_color(*COLOR_LIGHT)
                pdf.set_font(pdf._font, "", 9)
                pdf.cell(72, 6, ch["title"][:28], border=1, fill=fill)
                pdf.cell(36, 6, f"{ch['subscriber_count']:,}", border=1, fill=fill, align="R")
                pdf.cell(36, 6, f"{ch['view_count'] // 10000:,}만", border=1, fill=fill, align="R")
                pdf.cell(0, 6, f"{ch['video_count']:,}", border=1, fill=fill, align="R",
                         new_x="LMARGIN", new_y="NEXT")

        videos = nd.get("videos", [])[:5]
        if videos:
            pdf.ln(3)
            pdf.set_font(pdf._font, "B", 9)
            pdf.cell(0, 5, "  이번 주 인기 영상 TOP 5", new_x="LMARGIN", new_y="NEXT")
            for i, v in enumerate(videos, 1):
                title = v["title"][:42] + ("…" if len(v["title"]) > 42 else "")
                pdf.set_font(pdf._font, "", 9)
                pdf.cell(0, 5,
                         f"  {i}. [{v['format']}] {title}  |  {v['view_count']:,}회",
                         new_x="LMARGIN", new_y="NEXT")

        pdf.ln(6)

    # 평균 조회수 차트
    if "avg_views" in charts and os.path.exists(charts["avg_views"]):
        pdf.add_page()
        pdf.section_title("분야별 평균 조회수 비교")
        pdf.image(charts["avg_views"], x=15, w=175)

    # ── 5. 채널 인사이트 ──
    pdf.add_page()
    pdf.section_title("5. 주목할 채널 인사이트")
    for ins in analysis.get("channel_insights", []):
        pdf.set_font(pdf._font, "B", 11)
        pdf.cell(0, 7, f"▶ {ins.get('channel', '')}", new_x="LMARGIN", new_y="NEXT")
        pdf.body(f"강점: {ins.get('strength', '')}", indent=10)
        pdf.body(f"콘텐츠 전략: {ins.get('content_strategy', '')}", indent=10)
        pdf.ln(3)

    # ── 6. 콘텐츠 주제 추천 ──
    pdf.section_title("6. 이번 주 콘텐츠 주제 추천")
    for i, rec in enumerate(analysis.get("content_recommendations", []), 1):
        pdf.highlight_box(
            f"추천 {i}: {rec.get('title_idea', '')}"
        )
        pdf.set_font(pdf._font, "", 10)
        pdf.body(f"분야: {rec.get('niche', '')}  |  포맷: {rec.get('format', '')}", indent=5)
        pdf.body(f"추천 이유: {rec.get('reason', '')}", indent=5)
        if rec.get("hook_suggestion"):
            pdf.body(f"훅 아이디어: {rec['hook_suggestion']}", indent=5)
        pdf.ln(3)

    pdf.output(output_path)
    logger.info(f"PDF 생성 완료: {output_path}")
    return output_path
