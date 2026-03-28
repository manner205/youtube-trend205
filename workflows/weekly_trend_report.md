# Workflow: 유튜브 트렌드 주간 리포트 자동화

## 목표
매주 일요일 저녁 8시, 수익형 브랜드 / 콘텐츠 수익화 / 1인 사업 런칭 분야의
YouTube 트렌드를 수집·분석하여 PDF 리포트를 생성하고 Gmail 발송 + Notion 누적 저장.

---

## 실행 스케줄
- **주기:** 매주 일요일 20:00
- **방법:** Windows 작업 스케줄러 → `run_report.bat` 실행
- **로그:** `logs/` 폴더에 날짜별 저장

---

## 입력값
| 항목 | 값 |
|---|---|
| 분석 분야 | 수익형 브랜드, 콘텐츠 수익화, 1인 사업 런칭 |
| 채널 범위 | 한국 채널 우선 / 한국 채널 부족 시 영어권 보완 |
| 리포트 수신 이메일 | manner205@gmail.com |
| 리포트 언어 | 한국어 기본 (필요 시 영어 혼용) |

---

## 실행 단계

### 1단계 — YouTube 데이터 수집 (`tools/youtube_collector.py`)
- 각 분야별 한국어 키워드로 탑 채널 검색 (YouTube Data API v3)
- 한국 채널이 5개 미만이면 영어권 채널로 보완
- 채널 ID는 `data/channel_cache.json`에 캐시 (쿼터 절약)
- 각 채널의 최근 7일 인기 영상 수집
- 수집 데이터: 제목, 조회수, 좋아요, 댓글수, 길이, 쇼츠 여부, 태그

**쿼터 예상 소비:** 약 1,750유닛 / 일 (무료 한도 10,000의 17.5%)

### 2단계 — Claude AI 분석 (`tools/claude_analyzer.py`)
- 수집된 데이터를 Claude API (claude-haiku)로 전송
- 분석 항목:
  - 이번 주 트렌딩 주제 TOP 5 (데이터 근거 포함)
  - 쇼츠 vs 일반 영상 포맷 분석
  - 주목할 채널 인사이트 3개
  - 이번 주 콘텐츠 주제 추천 5개 (훅 아이디어 포함)
  - 핵심 인사이트 1문장 요약

### 3단계 — PDF 리포트 생성 (`tools/pdf_generator.py`)
- fpdf2 + matplotlib로 한국어 PDF 생성
- 구성: 표지 → 주간 요약 → 트렌딩 주제 → 포맷 분석 → 채널 분석 → 콘텐츠 추천
- 저장 위치: `data/reports/trend_report_YYYYMMDD.pdf`

### 4단계 — Gmail 발송 (`tools/gmail_sender.py`)
- Gmail API로 PDF 첨부 이메일 발송
- 수신: manner205@gmail.com
- 제목: `[트렌드 리포트] YYYY년 WW주차 유튜브 트렌드 분석`

### 5단계 — Notion 저장 (`tools/notion_saver.py`)
- 주간 데이터를 Notion 데이터베이스에 신규 페이지로 추가 (누적)
- 페이지 제목: `YYYY년 WW주차 트렌드 리포트`
- 저장 내용: 분야별 탑 채널, 인기 영상, 트렌딩 주제, 콘텐츠 추천

---

## 오류 처리 규칙
| 오류 상황 | 처리 방법 |
|---|---|
| YouTube API 쿼터 초과 | 캐시된 채널 데이터로 부분 실행, 로그에 기록 |
| Claude API 오류 | 분석 없이 데이터만 PDF에 포함, 계속 진행 |
| Gmail 발송 실패 | 로그에 기록, PDF는 로컬 저장 유지 |
| Notion 저장 실패 | 로그에 기록, 나머지 단계는 계속 진행 |

---

## 필요한 API 키 / 인증 (최초 1회 설정)

1. **YouTube API 키**
   - Google Cloud Console → 새 프로젝트 생성
   - YouTube Data API v3 활성화
   - 사용자 인증 정보 → API 키 생성
   - `.env`에 `YOUTUBE_API_KEY=` 입력

2. **Gmail OAuth 인증**
   - Google Cloud Console → OAuth 2.0 클라이언트 ID 생성 (데스크톱 앱)
   - `credentials.json` 다운로드 → 프로젝트 루트에 저장
   - 최초 실행 시 브라우저 인증 1회 → `token.json` 자동 생성
   - 이후 자동 갱신

3. **Anthropic API 키**
   - console.anthropic.com → API Keys
   - `.env`에 `ANTHROPIC_API_KEY=` 입력

4. **Notion 통합 토큰**
   - notion.so/profile/integrations → 새 통합 생성
   - 시크릿 토큰 → `.env`에 `NOTION_TOKEN=` 입력
   - 저장할 데이터베이스 페이지에 통합 연결
   - 데이터베이스 ID → `.env`에 `NOTION_DATABASE_ID=` 입력

자세한 설정 방법은 `setup_guide.md` 참조.

---

## 폴더 구조
```
content_report/
├── .env                    ← API 키 (git 제외)
├── credentials.json        ← Gmail OAuth 인증 파일 (git 제외)
├── token.json              ← Gmail 자동 갱신 토큰 (git 제외)
├── run_report.bat          ← Windows 작업 스케줄러 실행 파일
├── workflows/
│   └── weekly_trend_report.md
├── tools/
│   ├── main.py             ← 전체 흐름 오케스트레이터
│   ├── youtube_collector.py
│   ├── claude_analyzer.py
│   ├── pdf_generator.py
│   ├── gmail_sender.py
│   └── notion_saver.py
├── data/
│   ├── channel_cache.json  ← 채널 ID 캐시
│   ├── reports/            ← 생성된 PDF 저장
│   └── charts/             ← 차트 이미지 임시 저장
└── logs/                   ← 실행 로그
```
