# 셋업 가이드 — 유튜브 트렌드 주간 리포트

## 순서 요약
1. Python 패키지 설치
2. YouTube API 키 발급
3. Gmail OAuth 설정
4. Anthropic API 키 발급
5. Notion 통합 설정
6. .env 파일 작성
7. Windows 작업 스케줄러 등록
8. 테스트 실행

---

## 1. Python 패키지 설치

```bash
pip install -r requirements.txt
```

---

## 2. YouTube API 키 발급

1. [Google Cloud Console](https://console.cloud.google.com) 접속
2. 프로젝트 만들기 → 이름 자유 (예: `youtube-trend-report`)
3. 왼쪽 메뉴 → **API 및 서비스 > 라이브러리**
4. `YouTube Data API v3` 검색 → 사용 설정
5. **사용자 인증 정보 > API 키 만들기**
6. 생성된 키를 복사 → `.env`에 `YOUTUBE_API_KEY=복사한키` 입력

---

## 3. Gmail OAuth 설정

1. 같은 Google Cloud Console 프로젝트에서
2. **API 및 서비스 > 라이브러리** → `Gmail API` 검색 → 사용 설정
3. **사용자 인증 정보 > OAuth 2.0 클라이언트 ID 만들기**
   - 애플리케이션 유형: **데스크톱 앱**
   - 이름 자유
4. 생성 후 **JSON 다운로드** → 파일명을 `credentials.json`으로 변경
5. `credentials.json`을 프로젝트 루트(`content_report/`)에 저장
6. **OAuth 동의 화면** → 테스트 사용자에 `manner205@gmail.com` 추가

> **최초 1회**: `python tools/main.py` 실행 시 브라우저가 열려 Google 로그인 요청.
> 로그인 완료 후 `token.json`이 자동 생성되고, 이후 자동 갱신됨.

---

## 4. Anthropic API 키 발급

1. [Anthropic Console](https://console.anthropic.com) 접속
2. **API Keys** → **Create Key**
3. 생성된 키를 복사 → `.env`에 `ANTHROPIC_API_KEY=복사한키` 입력

---

## 5. Notion 통합 설정

### 5-1. Integration 생성
1. [Notion Integrations](https://www.notion.so/profile/integrations) 접속
2. **새 통합 만들기**
   - 이름: `트렌드 리포트`
   - 유형: 내부 통합
3. 생성 후 **시크릿 토큰** 복사 → `.env`에 `NOTION_TOKEN=복사한토큰` 입력

### 5-2. 데이터베이스 생성
Notion에서 새 페이지를 만들고 아래 속성을 가진 **데이터베이스** 추가:

| 속성명 | 유형 |
|---|---|
| 이름 | 제목 (기본) |
| 날짜 | 날짜 |
| 수익형_브랜드_채널 | 텍스트 |
| 콘텐츠수익화_채널 | 텍스트 |
| 1인사업_채널 | 텍스트 |
| 트렌딩_주제 | 텍스트 |
| 콘텐츠_추천 | 텍스트 |
| 핵심_인사이트 | 텍스트 |

### 5-3. Integration 연결
- 데이터베이스 페이지 우상단 `...` → **연결 추가** → `트렌드 리포트` 선택

### 5-4. 데이터베이스 ID 복사
- 데이터베이스 URL: `https://www.notion.so/xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx?v=...`
- `?v=` 앞의 32자리 → `.env`에 `NOTION_DATABASE_ID=복사한ID` 입력

---

## 6. .env 파일 작성

프로젝트 루트에 `.env` 파일 생성:

```
YOUTUBE_API_KEY=발급받은키
ANTHROPIC_API_KEY=발급받은키
NOTION_TOKEN=발급받은토큰
NOTION_DATABASE_ID=데이터베이스ID
GMAIL_SENDER=manner205@gmail.com
GMAIL_RECIPIENT=manner205@gmail.com
CLAUDE_MODEL=claude-haiku-4-5-20251001
```

> `.env` 파일은 절대 GitHub에 올리지 마. `.gitignore`에 이미 포함되어 있어.

---

## 7. Windows 작업 스케줄러 등록

1. `Win + R` → `taskschd.msc` 실행
2. 오른쪽 패널 → **작업 만들기**
3. **일반** 탭
   - 이름: `유튜브 트렌드 주간 리포트`
   - 사용자가 로그온할 때만 실행 (or 로그온 여부에 관계없이 실행)
4. **트리거** 탭 → 새로 만들기
   - 작업 시작: 일정에 따라
   - 매주 → 일요일 → 오후 8:00:00
5. **동작** 탭 → 새로 만들기
   - 프로그램/스크립트: `D:\Claude-code-app\content_report\run_report.bat`
6. 확인 저장

---

## 8. 테스트 실행

```bash
cd D:\Claude-code-app\content_report
python tools/main.py
```

성공 시:
- `data/reports/trend_report_YYYYMMDD.pdf` 생성
- manner205@gmail.com으로 이메일 수신
- Notion 데이터베이스에 새 행 추가
- `logs/` 폴더에 실행 로그 저장
