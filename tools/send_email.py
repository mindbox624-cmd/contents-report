"""PDF 리포트를 Resend 이메일 API로 발송한다.

클라우드 스케줄 환경은 SMTP 같은 직접 소켓 연결(raw TCP)을 지원하지 않고
HTTPS 요청만 통과시키기 때문에, Gmail SMTP 대신 HTTPS 기반 이메일 API(Resend)를 쓴다.

사용법:
    python tools/send_email.py --pdf .tmp/weekly_report_20260921.pdf --subject "9월 21일 주간 트렌드 리포트"

필요한 환경변수 (.env): RESEND_API_KEY, REPORT_RECIPIENT_EMAIL
"""

import argparse
import base64
import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
RESEND_API_URL = "https://api.resend.com/emails"
DEFAULT_SENDER = "Weekly Report <onboarding@resend.dev>"


def main():
    parser = argparse.ArgumentParser(description="PDF 리포트를 이메일로 발송")
    parser.add_argument("--pdf", required=True)
    parser.add_argument("--to", default=None)
    parser.add_argument("--subject", default="주간 콘텐츠 트렌드 리포트")
    parser.add_argument("--body", default="이번 주 콘텐츠 트렌드 리포트를 첨부합니다.")
    args = parser.parse_args()

    load_dotenv(ROOT / ".env")
    api_key = os.environ.get("RESEND_API_KEY")
    recipient = args.to or os.environ.get("REPORT_RECIPIENT_EMAIL")

    if not api_key:
        print("[에러] .env에 RESEND_API_KEY가 없습니다.", file=sys.stderr)
        sys.exit(1)
    if not recipient:
        print("[에러] 수신자 이메일이 없습니다 (--to 또는 REPORT_RECIPIENT_EMAIL).", file=sys.stderr)
        sys.exit(1)

    pdf_path = Path(args.pdf)
    if not pdf_path.exists():
        print(f"[에러] PDF 파일을 찾을 수 없습니다: {pdf_path}", file=sys.stderr)
        sys.exit(1)

    pdf_base64 = base64.b64encode(pdf_path.read_bytes()).decode("ascii")

    payload = {
        "from": DEFAULT_SENDER,
        "to": [recipient],
        "subject": args.subject,
        "text": args.body,
        "attachments": [
            {"filename": pdf_path.name, "content": pdf_base64},
        ],
    }

    response = requests.post(
        RESEND_API_URL,
        headers={"Authorization": f"Bearer {api_key}"},
        json=payload,
        timeout=30,
    )

    if response.status_code >= 400:
        print(f"[에러] 이메일 발송 실패 ({response.status_code}): {response.text}", file=sys.stderr)
        sys.exit(1)

    print(f"이메일 발송 완료 -> {recipient}")


if __name__ == "__main__":
    main()
