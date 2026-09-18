"""최근 N일 이내 업로드된 인기 유튜브 영상을 키워드로 검색해서 JSON으로 저장한다.

사용법:
    python tools/youtube_search.py
    python tools/youtube_search.py --keywords-file tools/keywords.json --days 30 --output .tmp/videos_20260921.json

필요한 환경변수 (.env): YOUTUBE_API_KEY
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

ROOT = Path(__file__).resolve().parent.parent
DURATION_RE = re.compile(
    r"PT"
    r"(?:(?P<hours>\d+)H)?"
    r"(?:(?P<minutes>\d+)M)?"
    r"(?:(?P<seconds>\d+)S)?"
)


def parse_duration_seconds(iso_duration: str) -> int:
    match = DURATION_RE.match(iso_duration or "")
    if not match:
        return 0
    parts = match.groupdict()
    hours = int(parts["hours"] or 0)
    minutes = int(parts["minutes"] or 0)
    seconds = int(parts["seconds"] or 0)
    return hours * 3600 + minutes * 60 + seconds


def classify_format(duration_seconds: int) -> tuple[str, str]:
    if duration_seconds <= 180:
        return "숏폼", "0-3분"
    if duration_seconds <= 300:
        return "롱폼", "3-5분"
    if duration_seconds <= 900:
        return "롱폼", "5-15분"
    return "롱폼", "15분 이상"


def search_video_ids(youtube, keyword: str, published_after: str, max_results: int) -> list[str]:
    try:
        response = (
            youtube.search()
            .list(
                q=keyword,
                part="id",
                type="video",
                order="viewCount",
                publishedAfter=published_after,
                maxResults=max_results,
                relevanceLanguage="ko",
            )
            .execute()
        )
    except HttpError as exc:
        print(f"[경고] '{keyword}' 검색 중 오류 발생, 건너뜀: {exc}", file=sys.stderr)
        return []
    return [item["id"]["videoId"] for item in response.get("items", [])]


def fetch_video_details(youtube, video_ids: list[str]) -> list[dict]:
    details = []
    for i in range(0, len(video_ids), 50):
        chunk = video_ids[i : i + 50]
        response = (
            youtube.videos()
            .list(part="snippet,statistics,contentDetails", id=",".join(chunk))
            .execute()
        )
        details.extend(response.get("items", []))
    return details


def build_records(video_items: list[dict], keyword_by_id: dict[str, str]) -> list[dict]:
    records = []
    for item in video_items:
        video_id = item["id"]
        snippet = item.get("snippet", {})
        stats = item.get("statistics", {})
        content = item.get("contentDetails", {})
        duration_seconds = parse_duration_seconds(content.get("duration", "PT0S"))
        video_format, length_bucket = classify_format(duration_seconds)
        records.append(
            {
                "video_id": video_id,
                "url": f"https://www.youtube.com/watch?v={video_id}",
                "title": snippet.get("title", ""),
                "channel_title": snippet.get("channelTitle", ""),
                "published_at": snippet.get("publishedAt", ""),
                "matched_keyword": keyword_by_id.get(video_id, ""),
                "view_count": int(stats.get("viewCount", 0)),
                "like_count": int(stats.get("likeCount", 0)),
                "comment_count": int(stats.get("commentCount", 0)),
                "duration_seconds": duration_seconds,
                "format": video_format,
                "length_bucket": length_bucket,
                "thumbnail": snippet.get("thumbnails", {}).get("medium", {}).get("url", ""),
            }
        )
    return records


def main():
    parser = argparse.ArgumentParser(description="키워드 기반 유튜브 인기 영상 수집")
    parser.add_argument("--keywords-file", default=str(ROOT / "tools" / "keywords.json"))
    parser.add_argument("--output", default=None)
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--max-per-keyword", type=int, default=15)
    parser.add_argument("--max-total", type=int, default=60)
    args = parser.parse_args()

    load_dotenv(ROOT / ".env")
    api_key = os.environ.get("YOUTUBE_API_KEY")
    if not api_key:
        print("[에러] .env에 YOUTUBE_API_KEY가 없습니다.", file=sys.stderr)
        sys.exit(1)

    keywords = json.loads(Path(args.keywords_file).read_text(encoding="utf-8"))
    if not keywords:
        print("[에러] 키워드 목록이 비어 있습니다.", file=sys.stderr)
        sys.exit(1)

    published_after = (
        (datetime.now(timezone.utc) - timedelta(days=args.days))
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )

    youtube = build("youtube", "v3", developerKey=api_key)

    keyword_by_id: dict[str, str] = {}
    for keyword in keywords:
        ids = search_video_ids(youtube, keyword, published_after, args.max_per_keyword)
        for video_id in ids:
            keyword_by_id.setdefault(video_id, keyword)
        print(f"  - '{keyword}': {len(ids)}개 발견")

    all_ids = list(keyword_by_id.keys())
    if not all_ids:
        print("[경고] 조건에 맞는 영상을 하나도 찾지 못했습니다.", file=sys.stderr)

    video_items = fetch_video_details(youtube, all_ids)
    records = build_records(video_items, keyword_by_id)
    records.sort(key=lambda r: r["view_count"], reverse=True)
    records = records[: args.max_total]

    today = datetime.now().strftime("%Y%m%d")
    output_path = Path(args.output) if args.output else ROOT / ".tmp" / f"videos_{today}.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "days_window": args.days,
        "keywords": keywords,
        "video_count": len(records),
        "videos": records,
    }
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n총 {len(records)}개 영상 저장 완료 -> {output_path}")


if __name__ == "__main__":
    main()
