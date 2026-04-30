"""최근 2개 평가 결과를 비교하여 품질 회귀 감지. python eval/compare_results.py 로 실행."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
from pathlib import Path

RESULTS_DIR = Path(__file__).parent / "results"
REGRESSION_THRESHOLD = 5.0  # %p 이상 하락 시 경고


def _load_two_latest():
    files = sorted(RESULTS_DIR.glob("eval_*.json"))
    if len(files) < 2:
        return None, None
    try:
        with open(files[-2], encoding="utf-8") as f:
            prev = json.load(f)
        with open(files[-1], encoding="utf-8") as f:
            curr = json.load(f)
        return (files[-2].name, prev), (files[-1].name, curr)
    except (json.JSONDecodeError, KeyError):
        return None, None


def _diff_label(delta: float, higher_is_better: bool = True) -> str:
    sign = "+" if delta > 0 else ""
    if higher_is_better:
        bad = delta <= -REGRESSION_THRESHOLD
    else:
        bad = delta >= REGRESSION_THRESHOLD
    icon = "⚠️ " if bad else "✅"
    return f"{sign}{delta:.1f} {icon}"


def main():
    prev_pair, curr_pair = _load_two_latest()

    if prev_pair is None:
        print("[안내] 비교할 평가 결과가 2개 이상 필요합니다. eval_runner.py를 먼저 실행해주세요.")
        return

    prev_name, prev_data = prev_pair
    curr_name, curr_data = curr_pair

    p = prev_data.get("overall", {})
    c = curr_data.get("overall", {})

    if not p or not c:
        print("[오류] 평가 결과 파일 형식이 올바르지 않습니다.")
        return

    print("\n=== 회귀 테스트 결과 ===")
    print(f"이전: {prev_name} ({p.get('n', '?')}건)")
    print(f"현재: {curr_name} ({c.get('n', '?')}건)")
    print()

    top3_delta = c["top3_pct"] - p["top3_pct"]
    eq_delta = c["eq_pass_pct"] - p["eq_pass_pct"]
    rt_delta = c["avg_rt"] - p["avg_rt"]

    print(f"Top-3 Hit Rate: {p['top3_pct']}% → {c['top3_pct']}% ({_diff_label(top3_delta)}%p)")
    print(f"근거 품질 합격: {p['eq_pass_pct']}% → {c['eq_pass_pct']}% ({_diff_label(eq_delta)}%p)")
    print(f"평균 응답시간: {p['avg_rt']}초 → {c['avg_rt']}초 ({_diff_label(rt_delta, higher_is_better=False)}초)")

    regression = (
        top3_delta <= -REGRESSION_THRESHOLD
        or eq_delta <= -REGRESSION_THRESHOLD
        or rt_delta >= REGRESSION_THRESHOLD
    )

    print()
    if regression:
        print("[판정] ⚠️  품질 저하 감지. 변경 사항 롤백을 권장합니다.")
    else:
        print("[판정] ✅ 회귀 없음. 변경 사항 적용 가능.")


if __name__ == "__main__":
    main()
