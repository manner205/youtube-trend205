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
