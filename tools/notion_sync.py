"""분석 결과(JSON)를 노션 데이터베이스에 한 행으로 누적 저장한다.

사용법:
    python tools/notion_sync.py --analysis .tmp/analysis_20260921.json

노션 데이터베이스에는 아래 속성이 미리 만들어져 있어야 한다 (workflows 문서 참고):
    Name (제목), Date (날짜), Keywords (텍스트), Video Count (숫자), Recommended Topics (텍스트)

필요한 환경변수 (.env): NOTION_TOKEN, NOTION_DATABASE_ID
"""

import argparse
import json
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from notion_client import Client

ROOT = Path(__file__).resolve().parent.parent
# NOTION_DATABASE_ID로 페이지 ID가 들어왔을 때 databases.retrieve()가 실패하는 건
# resolve_data_source_id()가 알아서 처리하는 정상적인 흐름이라, 관련 경고 로그는 끈다.
logging.getLogger("notion_client").setLevel(logging.ERROR)


def resolve_data_source_id(client: Client, target_id: str) -> str:
    """NOTION_DATABASE_ID로 받은 값이 데이터베이스 ID든, 그 데이터베이스를 담고 있는
    페이지 ID든 상관없이 실제로 글을 쓸 수 있는 data_source_id를 찾아낸다.

    노션은 데이터베이스 하나가 여러 data source를 가질 수 있는 구조로 바뀌었고,
    또 사람들이 표를 담은 '바깥 페이지' 링크를 데이터베이스 ID로 착각해서 붙여넣는
    실수가 흔하기 때문에, 두 경우 모두 스스로 찾아서 처리한다.
    """
    try:
        db = client.databases.retrieve(target_id)
        if db.get("object") == "database":
            data_sources = db.get("data_sources", [])
            if data_sources:
                return data_sources[0]["id"]
            return target_id
    except Exception:
        pass

    children = client.blocks.children.list(target_id).get("results", [])
    for block in children:
        if block.get("type") == "child_database":
            db = client.databases.retrieve(block["id"])
            data_sources = db.get("data_sources", [])
            if data_sources:
                return data_sources[0]["id"]
            return block["id"]

    raise RuntimeError(
        "NOTION_DATABASE_ID로 데이터베이스를 찾지 못했습니다. "
        "노션에서 그 표(데이터베이스)를 '전체 페이지로 열기'한 뒤, 그 URL의 ID를 "
        "다시 넣어주세요."
    )


def build_properties(analysis: dict, video_count: int) -> dict:
    week_of = analysis.get("week_of", "")
    topic_names = [t.get("topic", "") for t in analysis.get("trending_topics", [])]
    rec_titles = [r.get("title_idea", "") for r in analysis.get("recommended_topics", [])]
    return {
        "Name": {"title": [{"text": {"content": f"{week_of} 주간 트렌드 리포트"}}]},
        "Date": {"date": {"start": week_of}},
        "Keywords": {"rich_text": [{"text": {"content": ", ".join(topic_names)[:2000]}}]},
        "Video Count": {"number": video_count},
        "Recommended Topics": {"rich_text": [{"text": {"content": "; ".join(rec_titles)[:2000]}}]},
    }


def build_children_blocks(analysis: dict) -> list[dict]:
    def heading(text):
        return {"object": "block", "type": "heading_2", "heading_2": {"rich_text": [{"text": {"content": text}}]}}

    def paragraph(text):
        return {"object": "block", "type": "paragraph", "paragraph": {"rich_text": [{"text": {"content": text or ""}}]}}

    def bullet(text):
        return {"object": "block", "type": "bulleted_list_item", "bulleted_list_item": {"rich_text": [{"text": {"content": text}}]}}

    def numbered(text):
        return {"object": "block", "type": "numbered_list_item", "numbered_list_item": {"rich_text": [{"text": {"content": text}}]}}

    blocks = [heading("요약"), paragraph(analysis.get("summary", ""))]

    blocks.append(heading("뜨는 주제"))
    for topic in analysis.get("trending_topics", []):
        blocks.append(bullet(f"{topic.get('topic', '')} — {topic.get('why', '')}"))

    blocks.append(heading("포맷 인사이트"))
    blocks.append(paragraph(analysis.get("format_insights", {}).get("notes", "")))

    blocks.append(heading("추천 콘텐츠 주제"))
    for rec in analysis.get("recommended_topics", []):
        blocks.append(numbered(f"{rec.get('title_idea', '')} — {rec.get('reason', '')}"))

    return blocks


def main():
    parser = argparse.ArgumentParser(description="주간 분석 결과를 노션 데이터베이스에 기록")
    parser.add_argument("--analysis", required=True)
    parser.add_argument("--videos", default=None, help="video_count를 채우기 위한 원본 videos json (선택)")
    args = parser.parse_args()

    load_dotenv(ROOT / ".env")
    token = os.environ.get("NOTION_TOKEN")
    database_id = os.environ.get("NOTION_DATABASE_ID")
    if not token or not database_id:
        print("[에러] .env에 NOTION_TOKEN 또는 NOTION_DATABASE_ID가 없습니다.", file=sys.stderr)
        sys.exit(1)

    analysis = json.loads(Path(args.analysis).read_text(encoding="utf-8"))

    video_count = analysis.get("video_count", 0)
    if args.videos:
        videos_payload = json.loads(Path(args.videos).read_text(encoding="utf-8"))
        video_count = videos_payload.get("video_count", video_count)

    client = Client(auth=token)
    data_source_id = resolve_data_source_id(client, database_id)
    page = client.pages.create(
        parent={"type": "data_source_id", "data_source_id": data_source_id},
        properties=build_properties(analysis, video_count),
        children=build_children_blocks(analysis),
    )

    print(f"노션 기록 완료 -> {page.get('url', page.get('id'))}")


if __name__ == "__main__":
    main()
