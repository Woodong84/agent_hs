"""Agent KPI 자동 측정. python eval/eval_runner.py 로 실행."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

GROUND_TRUTH_PATH = Path(__file__).parent / "ground_truth.json"
RESULTS_DIR = Path(__file__).parent / "results"


def _top3_codes(candidates: list) -> list:
    return [c["hs_code"] for c in candidates[:3]]


def _hit_at_k(candidates: list, answer_10: str, k: int) -> bool:
    codes = _top3_codes(candidates)[:k]
    return answer_10 in codes


def _partial_hit(candidates: list, answer_6: str) -> bool:
    codes = _top3_codes(candidates)
    return any(c[:6] == answer_6 for c in codes)


def run_eval():
    from agents.orchestrator import run_agent

    with open(GROUND_TRUTH_PATH, encoding="utf-8") as f:
        cases = json.load(f)

    if not cases:
        print("[경고] ground_truth.json이 비어 있습니다. 평가셋을 먼저 추가해주세요.")
        return

    total = len(cases)
    by_difficulty: dict = {}
    all_results = []

    for case in cases:
        difficulty = case.get("difficulty", "normal")
        inp = case["input"]
        answer = case["answer"]
        answer_10 = answer["hs_code_10"]
        answer_6 = answer["hs_code_6"]

        result = run_agent(inp)

        candidates = result.get("candidates", [])
        fallback = result.get("fallback_triggered", False)
        eq_score = result.get("evidence_quality_score", 0.0)
        rt = result.get("response_time_sec", 0.0)

        top1_hit = _hit_at_k(candidates, answer_10, 1)
        top3_hit = _hit_at_k(candidates, answer_10, 3)
        partial = _partial_hit(candidates, answer_6)

        case_result = {
            "case_id": case["case_id"],
            "difficulty": difficulty,
            "answer_10": answer_10,
            "top3_codes": _top3_codes(candidates),
            "top1_hit": top1_hit,
            "top3_hit": top3_hit,
            "partial_hit": partial,
            "fallback": fallback,
            "evidence_quality_score": eq_score,
            "response_time_sec": rt,
            "error": result.get("error_message"),
        }
        all_results.append(case_result)

        if difficulty not in by_difficulty:
            by_difficulty[difficulty] = []
        by_difficulty[difficulty].append(case_result)

    def _metrics(results: list) -> dict:
        n = len(results)
        if n == 0:
            return {}
        top1 = sum(r["top1_hit"] for r in results) / n * 100
        top3 = sum(r["top3_hit"] for r in results) / n * 100
        partial = sum(r["partial_hit"] for r in results) / n * 100
        eq_pass = sum(1 for r in results if r["evidence_quality_score"] >= 6) / n * 100
        avg_rt = sum(r["response_time_sec"] for r in results) / n
        fallbacks = sum(r["fallback"] for r in results)
        return {
            "n": n,
            "top1_pct": round(top1, 1),
            "top3_pct": round(top3, 1),
            "partial_pct": round(partial, 1),
            "eq_pass_pct": round(eq_pass, 1),
            "avg_rt": round(avg_rt, 1),
            "fallback_count": fallbacks,
        }

    overall = _metrics(all_results)

    print(f"\n=== 평가 결과 ({total}건) ===")
    print("[전체]")
    print(f"  Top-1 정확도 : {overall['top1_pct']}%")
    print(f"  Top-3 Hit Rate: {overall['top3_pct']}%  ← PoC 목표: 70% 이상")
    print(f"  부분 정답률  : {overall['partial_pct']}%")
    print(f"  근거 품질 합격: {overall['eq_pass_pct']}%  ← PoC 목표: 75% 이상")
    print(f"  평균 응답시간 : {overall['avg_rt']}초   ← PoC 목표: 10초 이하")
    print(f"  Fallback 발생 : {overall['fallback_count']}건 ({overall['fallback_count']/total*100:.1f}%)")

    print("\n[난이도별]")
    for diff, results in by_difficulty.items():
        m = _metrics(results)
        fb = m["fallback_count"]
        print(f"  {diff:<10}({m['n']}건): Top-3 {m['top3_pct']}% / 응답시간 {m['avg_rt']}초 / Fallback {fb}건")

    print("\n[PoC 합격 판정]")
    top3_ok = overall["top3_pct"] >= 70
    eq_ok = overall["eq_pass_pct"] >= 75
    rt_ok = overall["avg_rt"] <= 10
    edge_results = by_difficulty.get("edge", [])
    edge_fb = sum(r["fallback"] for r in edge_results)
    edge_n = len(edge_results)
    edge_ok = edge_n == 0 or (edge_fb / edge_n >= 0.8)

    print(f"  Top-3 Hit Rate: {'✅' if top3_ok else '❌'} {overall['top3_pct']}% (목표 70%)")
    print(f"  근거 품질 합격: {'✅' if eq_ok else '❌'} {overall['eq_pass_pct']}% (목표 75%)")
    print(f"  평균 응답시간: {'✅' if rt_ok else '❌'} {overall['avg_rt']}초 (목표 10초)")
    if edge_n > 0:
        print(f"  엣지 Fallback: {'✅' if edge_ok else '❌'} {edge_fb}/{edge_n}건 코드 미출력")

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = RESULTS_DIR / f"eval_{ts}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(
            {"timestamp": ts, "total": total, "overall": overall,
             "by_difficulty": {d: _metrics(r) for d, r in by_difficulty.items()},
             "cases": all_results},
            f, ensure_ascii=False, indent=2,
        )
    print(f"\n[저장] {out_path}")


if __name__ == "__main__":
    run_eval()
