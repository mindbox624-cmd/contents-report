# Workflow: 주간 유튜브 트렌드 브랜드 리포트

## 목표

"수익성 브랜드 / 콘텐츠 수익화 / 1인 사업 런칭" 분야에서 최근 뜨고 있는 유튜브 콘텐츠를
데이터 기반으로 파악해서, 이번 주 추천 콘텐츠 주제가 담긴 브랜드 PDF 리포트를 만들고,
이메일로 발송하고, 노션에 누적 기록한다.

## 언제 실행하나

매주 일요일 저녁 8시(KST), 클라우드 스케줄 루틴으로 자동 실행된다.
(사람이 직접 시킬 때는 아래 단계를 그대로 순서대로 실행하면 된다.)

## 시작 전 체크리스트

- `.env`에 다음 값이 모두 채워져 있어야 한다: `YOUTUBE_API_KEY`, `NOTION_TOKEN`,
  `NOTION_DATABASE_ID`, `RESEND_API_KEY`, `REPORT_RECIPIENT_EMAIL`
  (값이 비어 있으면 각 tool이 바로 에러를 내고 멈춘다 — 그게 정상 동작이다.)
- 이메일 발송은 Gmail SMTP가 아니라 **Resend라는 이메일 API(HTTPS)**를 쓴다. 클라우드
  스케줄 환경은 SMTP 같은 직접 소켓 연결(raw TCP)을 지원하지 않고 HTTPS 요청만 통과시키기
  때문 — 실제로 2026-09-18 첫 클라우드 실행에서 SMTP가 `OSError: Address family not
  supported by protocol`로 구조적으로 막히는 걸 확인하고 이렇게 바꿨다.
- 클라우드 루틴이 쓰는 환경(Default 등)의 "네트워크 접근"이 `api.notion.com`과
  `api.resend.com`을 허용해야 한다 (Trusted 기본값에는 안 들어있을 수 있음 — Custom으로
  바꾸고 두 도메인을 추가).
- 노션 데이터베이스에 다음 속성이 미리 만들어져 있어야 한다:
  `Name`(제목/title), `Date`(날짜/date), `Keywords`(텍스트/rich_text),
  `Video Count`(숫자/number), `Recommended Topics`(텍스트/rich_text)
- `NOTION_DATABASE_ID`는 데이터베이스 자체의 ID든, 그 표를 담고 있는 페이지의 ID든
  상관없다. `tools/notion_sync.py`가 둘 다 자동으로 인식해서 실제로 쓸 수 있는
  data source를 스스로 찾아낸다 (노션이 데이터베이스/데이터소스 구조를 분리한 이후
  생긴 흔한 혼동이라 처음부터 흡수하도록 만들어놨다).
- 검색 키워드는 `tools/keywords.json`에 있다. 니치가 바뀌거나 특정 키워드 반응이
  계속 안 좋으면 이 파일만 수정하면 된다. 코드를 건드릴 필요 없음.

## 실행 순서

날짜는 `YYYYMMDD` 형식으로 오늘 날짜를 쓴다. 아래 예시는 2026년 9월 21일 기준.

### 1단계 — 유튜브 데이터 수집

```
python tools/youtube_search.py --output .tmp/videos_20260921.json
```

최근 30일 이내 업로드되고 조회수가 높은 영상을 키워드별로 모아서
`.tmp/videos_20260921.json`에 저장한다. 각 영상은 제목/채널/조회수/좋아요/댓글수/
업로드일/영상 길이/숏폼-롱폼 분류/링크를 담고 있다.

### 2단계 — 트렌드 분석 (Claude가 직접 판단하는 단계)

이 단계는 파이썬 스크립트가 아니라 **Claude가 1단계 결과 JSON을 직접 읽고 판단**해서
작성한다. 아래 형식으로 `.tmp/analysis_20260921.json`을 만든다:

```json
{
  "week_of": "2026-09-21",
  "brand_name": "(선택, 비워두면 기본 제목 사용)",
  "summary": "이번 주 트렌드를 3~5문장으로 요약",
  "trending_topics": [
    {
      "topic": "주제명 (예: 1인 지식창업 자동화)",
      "why": "왜 지금 뜨는지 데이터 기반 설명",
      "examples": [
        {"title": "영상 제목", "channel": "채널명", "view_count": 123456, "url": "https://..."}
      ]
    }
  ],
  "format_insights": {
    "shorts_count": 0,
    "longform_count": 0,
    "shorts_avg_views": 0,
    "longform_avg_views": 0,
    "notes": "숏폼/롱폼 중 뭐가 더 잘 되는지, 어떤 길이대가 유리한지 해석 문장"
  },
  "recommended_topics": [
    {"title_idea": "이번 주에 만들면 좋을 영상 제목 아이디어", "reason": "어떤 트렌드에 근거했는지"}
  ]
}
```

**분석 기준:**
- 뜨는 주제는 5~8개, 각 주제마다 실제 근거 영상 2~3개를 반드시 첨부한다 (숫자 없는
  주장 금지 — 조회수 데이터로 뒷받침할 것).
- 포맷 분석은 `format`/`length_bucket` 필드로 그룹핑해서 평균 조회수를 직접 계산한다.
- 추천 콘텐츠 주제는 5개, 남의 영상 제목을 베끼지 말고 이번 주 트렌드에서 뽑아낸
  새로운 각도로 제안한다.
- 영상이 너무 적게 모였거나(10개 미만) 특정 키워드에서 결과가 0개면, 그 사실을
  summary에 솔직하게 적는다.

### 3단계 — PDF 리포트 생성

```
python tools/generate_pdf_report.py --analysis .tmp/analysis_20260921.json --videos .tmp/videos_20260921.json --output .tmp/weekly_report_20260921.pdf
```

### 4단계 — 노션에 누적 기록

```
python tools/notion_sync.py --analysis .tmp/analysis_20260921.json --videos .tmp/videos_20260921.json
```

### 5단계 — 이메일 발송

```
python tools/send_email.py --pdf .tmp/weekly_report_20260921.pdf --subject "9월 21일 주간 콘텐츠 트렌드 리포트"
```

## 문제가 생겼을 때

- **YouTube API 에러/쿼터 초과**: `tools/youtube_search.py`가 어느 키워드에서
  실패했는지 로그로 남긴다. 일부 키워드만 실패했다면 나머지 결과로 계속 진행해도 된다.
- **노션 기록 실패 (속성 이름 불일치 등)**: 데이터베이스 속성 이름이 위 체크리스트와
  정확히 일치하는지 먼저 확인한다. 불일치가 반복되면 이 문서의 속성 이름을 실제
  데이터베이스에 맞게 업데이트한다.
- **노션/이메일이 클라우드에서만 실패 (로컬에서는 됨)**: 코드나 키 문제가 아니라
  클라우드 환경의 "네트워크 접근" 설정이 그 도메인을 막고 있는 것이다. 클라우드 환경
  설정에서 Network access를 Custom으로 바꾸고 필요한 도메인(`api.notion.com`,
  `api.resend.com`)을 추가한다.
- **이메일 발송 실패**: `RESEND_API_KEY`가 만료/폐기됐을 가능성이 크다. resend.com에서
  새로 발급받아 `.env`와 클라우드 루틴의 환경변수를 함께 갱신한다.
- 같은 실패가 두 번 이상 반복되면, 즉흥적으로 매번 고치지 말고 이 Workflow 문서와
  해당 tool을 업데이트해서 같은 문제가 다시 안 생기게 만든다 (claude.md 원칙).

## 완료 기준

- `.tmp/weekly_report_YYYYMMDD.pdf`가 생성되어 있다
- 노션 데이터베이스에 이번 주 행이 추가되어 있다
- 지정된 이메일 주소로 PDF가 첨부된 메일이 도착했다
