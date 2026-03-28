"""
Tool: gmail_sender.py
역할: PDF 리포트를 Gmail API로 이메일 발송
입력: pdf_path (str), week_str (str)
출력: 발송 성공 여부 (bool)
"""

import os
import base64
import logging
from email.message import EmailMessage
from datetime import datetime

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/gmail.send"]
TOKEN_FILE = "token.json"
CREDENTIALS_FILE = "credentials.json"


def _get_gmail_service():
    """Gmail API 클라이언트 반환 (OAuth 2.0 자동 갱신)"""
    creds = None

    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CREDENTIALS_FILE):
                raise FileNotFoundError(
                    f"{CREDENTIALS_FILE} 파일이 없어. "
                    "Google Cloud Console에서 OAuth 2.0 클라이언트 ID를 생성하고 "
                    "credentials.json으로 저장해."
                )
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(TOKEN_FILE, "w") as f:
            f.write(creds.to_json())

    return build("gmail", "v1", credentials=creds)


def send_report(pdf_path, week_str=None):
    """
    PDF 리포트를 Gmail로 발송.
    반환: True (성공) / False (실패)
    """
    recipient = os.getenv("GMAIL_RECIPIENT", "manner205@gmail.com")
    sender = os.getenv("GMAIL_SENDER", "manner205@gmail.com")

    if week_str is None:
        week_str = datetime.now().strftime("%Y-W%V")

    subject = f"[트렌드 리포트] {week_str} 유튜브 트렌드 분석"
    body = f"""안녕하세요.

이번 주({week_str}) 유튜브 트렌드 분석 리포트가 도착했습니다.

📊 분석 분야: 수익형 브랜드 / 콘텐츠 수익화 / 1인 사업 런칭
📎 첨부파일에서 PDF 리포트를 확인하세요.

---
자동 발송 | 유튜브 트렌드 주간 리포트 시스템
"""

    try:
        service = _get_gmail_service()

        msg = EmailMessage()
        msg["To"] = recipient
        msg["From"] = sender
        msg["Subject"] = subject
        msg.set_content(body)

        # PDF 첨부
        filename = os.path.basename(pdf_path)
        with open(pdf_path, "rb") as f:
            msg.add_attachment(f.read(), maintype="application", subtype="pdf",
                               filename=filename)

        encoded = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        service.users().messages().send(
            userId="me", body={"raw": encoded}
        ).execute()

        logger.info(f"이메일 발송 완료: {recipient}")
        return True

    except Exception as e:
        logger.error(f"이메일 발송 오류: {e}")
        return False
