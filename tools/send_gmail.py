"""PDF 리포트를 Gmail 앱 비밀번호로 발송한다.

사용법:
    python tools/send_gmail.py --pdf .tmp/weekly_report_20260921.pdf --subject "9월 21일 주간 트렌드 리포트"

필요한 환경변수 (.env): GMAIL_ADDRESS, GMAIL_APP_PASSWORD, REPORT_RECIPIENT_EMAIL
"""

import argparse
import os
import smtplib
import sys
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 465


def main():
    parser = argparse.ArgumentParser(description="PDF 리포트를 Gmail로 발송")
    parser.add_argument("--pdf", required=True)
    parser.add_argument("--to", default=None)
    parser.add_argument("--subject", default="주간 콘텐츠 트렌드 리포트")
    parser.add_argument("--body", default="이번 주 콘텐츠 트렌드 리포트를 첨부합니다.")
    args = parser.parse_args()

    load_dotenv(ROOT / ".env")
    gmail_address = os.environ.get("GMAIL_ADDRESS")
    app_password = os.environ.get("GMAIL_APP_PASSWORD")
    recipient = args.to or os.environ.get("REPORT_RECIPIENT_EMAIL")

    if not gmail_address or not app_password:
        print("[에러] .env에 GMAIL_ADDRESS 또는 GMAIL_APP_PASSWORD가 없습니다.", file=sys.stderr)
        sys.exit(1)
    if not recipient:
        print("[에러] 수신자 이메일이 없습니다 (--to 또는 REPORT_RECIPIENT_EMAIL).", file=sys.stderr)
        sys.exit(1)

    pdf_path = Path(args.pdf)
    if not pdf_path.exists():
        print(f"[에러] PDF 파일을 찾을 수 없습니다: {pdf_path}", file=sys.stderr)
        sys.exit(1)

    message = MIMEMultipart()
    message["From"] = gmail_address
    message["To"] = recipient
    message["Subject"] = args.subject
    message.attach(MIMEText(args.body, "plain"))

    with open(pdf_path, "rb") as f:
        attachment = MIMEApplication(f.read(), _subtype="pdf")
    attachment.add_header("Content-Disposition", "attachment", filename=pdf_path.name)
    message.attach(attachment)

    with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as server:
        server.login(gmail_address, app_password)
        server.sendmail(gmail_address, recipient, message.as_string())

    print(f"이메일 발송 완료 -> {recipient}")


if __name__ == "__main__":
    main()
