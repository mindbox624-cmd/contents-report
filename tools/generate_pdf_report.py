"""분석 결과(JSON)를 받아 브랜드 PDF 리포트를 만든다.

사용법:
    python tools/generate_pdf_report.py --analysis .tmp/analysis_20260921.json \
        --videos .tmp/videos_20260921.json --output .tmp/weekly_report_20260921.pdf

analysis JSON 구조 (Claude가 직접 작성):
{
  "week_of": "2026-09-21",
  "brand_name": "선택, 없으면 기본값",
  "summary": "이번 주 한눈에 보기 3~5문장",
  "trending_topics": [
    {"topic": "주제명", "why": "왜 뜨는지",
     "examples": [{"title": "..", "channel": "..", "view_count": 12345, "url": ".."}]}
  ],
  "format_insights": {
    "shorts_count": 10, "longform_count": 20,
    "shorts_avg_views": 50000, "longform_avg_views": 30000,
    "notes": "포맷 관련 해석 문장"
  },
  "recommended_topics": [
    {"title_idea": "영상 제목 아이디어", "reason": "이 트렌드에 기반한 이유"}
  ]
}
"""

import argparse
import json
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    ListFlowable,
    ListItem,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

ROOT = Path(__file__).resolve().parent.parent

FONT_DIR = ROOT / "tools" / "fonts"
BODY_FONT = "NotoSansKR"
HEADING_FONT = "NotoSansKR-Bold"
# 시스템에 한글 폰트가 없는 환경(클라우드 샌드박스 등)에서도 깨지지 않도록
# 폰트 파일을 PDF에 직접 임베드한다. 시스템 폰트에 의존하는 CID 폰트는 쓰지 않는다.
pdfmetrics.registerFont(TTFont(BODY_FONT, str(FONT_DIR / "NotoSansKR-Regular.ttf")))
pdfmetrics.registerFont(TTFont(HEADING_FONT, str(FONT_DIR / "NotoSansKR-Bold.ttf")))

NAVY = colors.HexColor("#1F2937")
ACCENT = colors.HexColor("#2563EB")
LIGHT_GRAY = colors.HexColor("#F3F4F6")

STYLES = {
    "title": ParagraphStyle("title", fontName=HEADING_FONT, fontSize=26, leading=32, textColor=NAVY, spaceAfter=6),
    "subtitle": ParagraphStyle("subtitle", fontName=BODY_FONT, fontSize=13, leading=18, textColor=colors.HexColor("#6B7280")),
    "h1": ParagraphStyle("h1", fontName=HEADING_FONT, fontSize=17, leading=22, textColor=NAVY, spaceBefore=18, spaceAfter=8),
    "h2": ParagraphStyle("h2", fontName=HEADING_FONT, fontSize=13, leading=18, textColor=ACCENT, spaceBefore=10, spaceAfter=4),
    "body": ParagraphStyle("body", fontName=BODY_FONT, fontSize=10.5, leading=16, textColor=colors.HexColor("#111827")),
    "small": ParagraphStyle("small", fontName=BODY_FONT, fontSize=9, leading=13, textColor=colors.HexColor("#4B5563")),
}


def build_title_page(story, analysis: dict):
    brand_name = analysis.get("brand_name") or "주간 콘텐츠 트렌드 리포트"
    week_of = analysis.get("week_of", "")
    story.append(Spacer(1, 60 * mm))
    story.append(Paragraph(brand_name, STYLES["title"]))
    story.append(Paragraph(f"수익성 브랜드 · 콘텐츠 수익화 · 1인 사업 런칭 트렌드 ({week_of} 기준)", STYLES["subtitle"]))
    story.append(PageBreak())


def build_summary(story, analysis: dict):
    story.append(Paragraph("이번 주 한눈에 보기", STYLES["h1"]))
    story.append(Paragraph(analysis.get("summary", ""), STYLES["body"]))


def build_trending_topics(story, analysis: dict):
    story.append(Paragraph("뜨는 주제", STYLES["h1"]))
    for topic in analysis.get("trending_topics", []):
        story.append(Paragraph(topic.get("topic", ""), STYLES["h2"]))
        story.append(Paragraph(topic.get("why", ""), STYLES["body"]))
        examples = topic.get("examples", [])
        if examples:
            items = [
                ListItem(
                    Paragraph(
                        f"{ex.get('title', '')} — {ex.get('channel', '')} "
                        f"(조회수 {ex.get('view_count', 0):,}) {ex.get('url', '')}",
                        STYLES["small"],
                    )
                )
                for ex in examples
            ]
            story.append(ListFlowable(items, bulletType="bullet", start="circle"))
        story.append(Spacer(1, 4))


def build_format_insights(story, analysis: dict):
    story.append(Paragraph("잘 되는 포맷 분석", STYLES["h1"]))
    insights = analysis.get("format_insights", {})
    rows = [
        ["구분", "영상 수", "평균 조회수"],
        [
            "숏폼",
            str(insights.get("shorts_count", "-")),
            f"{insights.get('shorts_avg_views', 0):,}",
        ],
        [
            "롱폼",
            str(insights.get("longform_count", "-")),
            f"{insights.get('longform_avg_views', 0):,}",
        ],
    ]
    table = Table(rows, colWidths=[40 * mm, 40 * mm, 40 * mm])
    table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), BODY_FONT),
                ("FONTNAME", (0, 0), (-1, 0), HEADING_FONT),
                ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("BACKGROUND", (0, 1), (-1, -1), LIGHT_GRAY),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.white),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(table)
    story.append(Spacer(1, 8))
    story.append(Paragraph(insights.get("notes", ""), STYLES["body"]))


def build_recommendations(story, analysis: dict):
    story.append(Paragraph("이번 주 추천 콘텐츠 주제", STYLES["h1"]))
    items = [
        ListItem(
            Paragraph(f"<b>{rec.get('title_idea', '')}</b><br/>{rec.get('reason', '')}", STYLES["body"])
        )
        for rec in analysis.get("recommended_topics", [])
    ]
    story.append(ListFlowable(items, bulletType="1"))


def build_appendix(story, videos: list[dict]):
    story.append(PageBreak())
    story.append(Paragraph("부록: 전체 조사 영상 리스트", STYLES["h1"]))
    rows = [["채널", "제목", "조회수", "업로드일", "포맷"]]
    for v in videos:
        rows.append(
            [
                v.get("channel_title", ""),
                v.get("title", "")[:40],
                f"{v.get('view_count', 0):,}",
                v.get("published_at", "")[:10],
                v.get("format", ""),
            ]
        )
    table = Table(rows, colWidths=[32 * mm, 70 * mm, 22 * mm, 22 * mm, 14 * mm], repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), BODY_FONT),
                ("FONTNAME", (0, 0), (-1, 0), HEADING_FONT),
                ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_GRAY]),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E5E7EB")),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(table)


def main():
    parser = argparse.ArgumentParser(description="주간 트렌드 분석 결과를 브랜드 PDF로 렌더링")
    parser.add_argument("--analysis", required=True)
    parser.add_argument("--videos", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    analysis = json.loads(Path(args.analysis).read_text(encoding="utf-8"))
    videos_payload = json.loads(Path(args.videos).read_text(encoding="utf-8"))
    videos = videos_payload.get("videos", [])

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        title=analysis.get("brand_name", "주간 콘텐츠 트렌드 리포트"),
    )

    story = []
    build_title_page(story, analysis)
    build_summary(story, analysis)
    build_trending_topics(story, analysis)
    build_format_insights(story, analysis)
    build_recommendations(story, analysis)
    build_appendix(story, videos)

    doc.build(story)
    print(f"PDF 생성 완료 -> {output_path}")


if __name__ == "__main__":
    main()
