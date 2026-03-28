# 개발일지 — 유튜브 트렌드 주간 리포트 자동화

---

## 2026-03-28

### 환경 세팅

- Python 재설치 후 VSCode 재시작
- `pip install -r requirements.txt` 로 전체 패키지 설치 완료
  - 주요 패키지: google-api-python-client, anthropic, notion-client, fpdf2, matplotlib

---

### 실행 #1 — 17:17 (첫 번째 테스트)

**결과**

| 단계 | 결과 |
|------|------|
| YouTube 수집 | ✅ 영상 32개 |
| Claude 분석 | ❌ JSON 파싱 오류 → 분석 불가로 대체 |
| PDF 생성 | ✅ |
| Gmail 발송 | ❌ Google OAuth 인증 오류 (access_denied) |
| Notion 저장 | ❌ |

**발생한 오류 2건**

1. **Gmail OAuth 인증 실패**
   - 원인: Google Cloud 앱이 테스트 모드이고, manner205@gmail.com이 테스터로 등록되지 않음
   - 해결: Google Cloud Console → OAuth 동의 화면 → 대상 → 테스트 사용자에 manner205@gmail.com 추가

2. **Claude 분석 JSON 파싱 오류**
   - 원인: `max_tokens=2500` 설정으로 응답이 중간에 잘려 JSON이 깨짐
   - 미해결 (이후 수정)

---

### 실행 #2 — 17:21 (Gmail 인증 후 재시도)

**결과**

| 단계 | 결과 |
|------|------|
| YouTube 수집 | ✅ 영상 32개 |
| Claude 분석 | ❌ JSON 파싱 오류 (max_tokens 부족) |
| PDF 생성 | ✅ |
| Gmail 발송 | ✅ manner205@gmail.com 발송 완료 |
| Notion 저장 | ❌ |

**발생한 오류 2건**

1. **Claude JSON 파싱 오류 지속** (max_tokens=2500)
2. **Notion 저장 실패**
   - 원인: 코드가 저장하려는 속성(날짜, 수익형_브랜드_채널 등 7개)이 Notion 데이터베이스에 없음. 데이터베이스에 `이름` 컬럼만 존재.
   - 해결: `notion_saver.py` 수정 — 데이터베이스에는 `이름`만 저장하고, 나머지 상세 내용은 페이지 내부 블록으로 작성

---

### 실행 #3 — 17:26 (Notion 수정 후)

**결과**

| 단계 | 결과 |
|------|------|
| YouTube 수집 | ✅ 영상 32개 |
| Claude 분석 | ❌ JSON 파싱 오류 (max_tokens 여전히 부족) |
| PDF 생성 | ✅ |
| Gmail 발송 | ✅ |
| Notion 저장 | ✅ |

**남은 오류**

- Claude 분석 실패로 PDF 1~2페이지 전체 "분석 불가" 상태로 발송됨
- 해결 필요: max_tokens 증가

---

### 실행 #4 — 17:31 (max_tokens=4000으로 증가)

**결과**

| 단계 | 결과 |
|------|------|
| YouTube 수집 | ✅ 영상 32개 |
| Claude 분석 | ❌ JSON 파싱 오류 (4000도 부족, char 4803에서 잘림) |
| PDF 생성 | ✅ |
| Gmail 발송 | ✅ |
| Notion 저장 | ✅ |

- 4000 토큰으로도 부족. 6000으로 재시도 필요.

---

### 실행 #5 — 17:35 (max_tokens=6000으로 증가) ✅ 전체 성공

**결과**

| 단계 | 결과 |
|------|------|
| YouTube 수집 | ✅ 영상 32개 |
| Claude 분석 | ✅ 트렌딩 주제 5개 정상 분석 |
| PDF 생성 | ✅ data/reports/trend_report_20260328.pdf |
| Gmail 발송 | ✅ manner205@gmail.com |
| Notion 저장 | ✅ |

- 총 소요시간: 46초
- **모든 단계 정상 작동 확인**

---

### 수정된 파일 목록

| 파일 | 수정 내용 |
|------|-----------|
| `tools/claude_analyzer.py` | max_tokens 2500 → 6000 (Claude 응답 잘림 방지) |
| `tools/notion_saver.py` | Notion DB에 `이름`만 저장, 나머지는 페이지 블록으로 변경 |

---

### 남아있는 알려진 이슈

| 이슈 | 상태 | 내용 |
|------|------|------|
| YouTube 플레이리스트 404 오류 | 방치 중 | `UUHEGVdZfTBUapyCoV0kkWhA` 채널의 플레이리스트를 찾을 수 없음. 해당 채널 데이터만 누락되고 나머지는 정상 수집됨 |
| 터미널 한글 인코딩 경고 | 방치 중 | Windows CP949 환경에서 로그 출력 시 일부 특수문자 깨짐. 로그 파일(UTF-8)은 정상 |

---

## 2026-03-29

### 버전 2 — Render 클라우드 배포 + GitHub Actions 스케줄러

---

### Render 배포

- **플랫폼**: Render (무료 플랜, Free tier)
- **배포 방식**: GitHub 저장소(`manner205/youtube-trend205`) 연동 → `main` 브랜치 push 시 자동 배포
- **URL**: https://youtube-trend205.onrender.com
- **무료 플랜 특성**: 15분 비활성 시 슬립 모드 진입, 첫 접속 시 ~50초 웨이크업 소요

**환경변수 설정 (Render Dashboard → Environment)**

| KEY | 비고 |
|-----|------|
| `YOUTUBE_API_KEY` | YouTube Data API v3 |
| `ANTHROPIC_API_KEY` | Claude API |
| `NOTION_TOKEN` | Notion 통합 토큰 |
| `NOTION_DATABASE_ID` | 리포트 저장 DB |
| `NOTION_SCHEDULE_PAGE_ID` | 스케줄 설정 저장 페이지 |
| `GMAIL_RECIPIENT` | 수신 이메일 |
| `GMAIL_SENDER` | 발신 이메일 |
| `GMAIL_CREDENTIALS_JSON` | OAuth 인증 파일 내용 |
| `GMAIL_TOKEN_JSON` | OAuth 토큰 파일 내용 |

---

### Gmail 자동 발송 스케줄러 구조 변경

**문제**: Render 무료 플랜 슬립 모드에서 APScheduler가 함께 잠들어 자동 발송 불가

**해결**: GitHub Actions를 외부 트리거로 사용

```
GitHub Actions (3시간마다, 무료)
    ↓ Render 서버 깨움 + /api/schedule 호출
    ↓ 설정 확인 (활성화 여부 / 요일 / 시간 ±89분)
    └── 조건 맞으면 → /api/run 호출 → 리포트 실행 + 이메일 발송
```

**Render 사용 시간 계산**
- 실행 횟수: 240회/월 (3시간 간격)
- 1회 소요: ~2분
- 월 총 소요: **8시간** (750시간 한도 대비 여유 충분)

---

### 신규 생성 파일

| 파일 | 내용 |
|------|------|
| `tools/notion_schedule.py` | 스케줄 설정을 Notion 페이지 code 블록에 JSON으로 영구 저장/로드 |
| `.github/workflows/schedule.yml` | 3시간마다 실행, Render API 호출로 자동 발송 트리거 |

### 수정된 파일

| 파일 | 수정 내용 |
|------|-----------|
| `tools/scheduler.py` | 파일 기반 설정 → Notion 기반으로 변경 |
| `app.py` | `/api/schedule` 엔드포인트 Notion 연동 |

---

### GitHub Secrets 설정

| Secret | 값 |
|--------|----|
| `RENDER_URL` | `https://youtube-trend205.onrender.com` |
