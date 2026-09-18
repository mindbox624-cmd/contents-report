"""분석용 원본 영상 데이터를 받아 PDF 리포트에 넣을 차트 이미지(PNG)를 만든다.

reportlab 표만으로는 숫자를 한눈에 비교하기 어려워서, matplotlib으로
색약 사용자도 구분 가능한(Okabe-Ito 팔레트) 막대그래프를 그려 PDF에 삽입한다.
(scientific-visualization 스킬의 출판물 품질 기준 — 색약 안전 색상, 0에서 시작하는
막대, 불필요한 장식 제거, 축 라벨에 단위 표기 — 을 브랜드 리포트에 맞게 적용)

이 파일은 다른 tool에서 함수로 가져다 쓰는 용도다 (generate_pdf_report.py에서 호출).
"""

from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # 화면 없는 서버/샌드박스 환경에서도 렌더링 가능하게
import matplotlib.pyplot as plt
from matplotlib import font_manager

ROOT = Path(__file__).resolve().parent.parent
FONT_PATH = ROOT / "tools" / "fonts" / "NotoSansKR-Regular.ttf"
FONT_PATH_BOLD = ROOT / "tools" / "fonts" / "NotoSansKR-Bold.ttf"

# Okabe-Ito 색약 안전 팔레트 (scientific-visualization 스킬 권장)
OKABE_ITO = ["#0072B2", "#E69F00", "#009E73", "#D55E00", "#CC79A7", "#56B4E9", "#F0E442"]

_KOREAN_FONT = font_manager.FontProperties(fname=str(FONT_PATH))
_KOREAN_FONT_BOLD = font_manager.FontProperties(fname=str(FONT_PATH_BOLD))


def _apply_clean_style(ax):
    """차트 장식을 덜어내고(chart junk 제거) 색약 안전 팔레트를 적용한다."""
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#9CA3AF")
    ax.spines["bottom"].set_color("#9CA3AF")
    ax.tick_params(colors="#374151")
    ax.yaxis.grid(True, color="#E5E7EB", linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)


def render_format_chart(videos: list[dict], output_path: Path) -> Path:
    """숏폼 vs 롱폼 평균 조회수 막대그래프."""
    by_format = defaultdict(list)
    for v in videos:
        by_format[v.get("format", "기타")].append(v.get("view_count", 0))

    labels = [l for l in ["숏폼", "롱폼"] if l in by_format]
    avgs = [sum(by_format[l]) / len(by_format[l]) for l in labels]
    counts = [len(by_format[l]) for l in labels]

    fig, ax = plt.subplots(figsize=(6.2, 3.2), dpi=300)
    bars = ax.bar(labels, avgs, color=OKABE_ITO[: len(labels)], width=0.5, zorder=3)
    _apply_clean_style(ax)

    ax.set_ylabel("평균 조회수 (회)", fontproperties=_KOREAN_FONT, fontsize=10, color="#374151")
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, fontproperties=_KOREAN_FONT, fontsize=11)
    ax.tick_params(axis="y", labelsize=9)

    for bar, avg, n in zip(bars, avgs, counts):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() * 1.02,
            f"{avg:,.0f}회 (n={n})",
            ha="center",
            va="bottom",
            fontproperties=_KOREAN_FONT,
            fontsize=9,
            color="#111827",
        )

    ax.set_ylim(0, max(avgs) * 1.2 if avgs else 1)
    fig.tight_layout()
    fig.savefig(output_path, dpi=300, facecolor="white")
    plt.close(fig)
    return output_path


def render_keyword_chart(videos: list[dict], output_path: Path, top_n: int = 8) -> Path:
    """키워드별 평균 조회수 가로 막대그래프 (상위 top_n개)."""
    by_keyword = defaultdict(list)
    for v in videos:
        kw = v.get("matched_keyword")
        if kw:
            by_keyword[kw].append(v.get("view_count", 0))

    stats = [(kw, sum(vs) / len(vs), len(vs)) for kw, vs in by_keyword.items()]
    stats.sort(key=lambda x: x[1], reverse=True)
    stats = stats[:top_n]
    stats.reverse()  # 그래프에서 위로 갈수록 높은 값이 오도록

    labels = [s[0] for s in stats]
    avgs = [s[1] for s in stats]
    counts = [s[2] for s in stats]

    fig, ax = plt.subplots(figsize=(6.2, 0.5 * len(labels) + 1), dpi=300)
    bars = ax.barh(labels, avgs, color=OKABE_ITO[0], zorder=3)
    _apply_clean_style(ax)
    ax.xaxis.grid(True, color="#E5E7EB", linewidth=0.8, zorder=0)
    ax.yaxis.grid(False)

    ax.set_xlabel("평균 조회수 (회)", fontproperties=_KOREAN_FONT, fontsize=10, color="#374151")
    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels(labels, fontproperties=_KOREAN_FONT, fontsize=10)
    ax.tick_params(axis="x", labelsize=9)

    for bar, avg, n in zip(bars, avgs, counts):
        ax.text(
            bar.get_width() * 1.02,
            bar.get_y() + bar.get_height() / 2,
            f"{avg:,.0f}회 (n={n})",
            ha="left",
            va="center",
            fontproperties=_KOREAN_FONT,
            fontsize=8.5,
            color="#111827",
        )

    ax.set_xlim(0, max(avgs) * 1.25 if avgs else 1)
    fig.tight_layout()
    fig.savefig(output_path, dpi=300, facecolor="white")
    plt.close(fig)
    return output_path
