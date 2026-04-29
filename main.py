"""HSAgent CLI 진입점. python main.py 로 실행."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv

load_dotenv()

from configs.settings import settings


def _check_env():
    if not settings.ANTHROPIC_API_KEY:
        print("[오류] ANTHROPIC_API_KEY가 설정되지 않았습니다.")
        print("  .env 파일에 ANTHROPIC_API_KEY=sk-ant-... 를 추가해주세요.")
        sys.exit(1)


def _collect_input() -> dict:
    print()
    product_name = input("품목명을 입력하세요: ").strip()
    if not product_name:
        print("[오류] 품목명은 필수입니다.")
        sys.exit(1)

    material = input("재질·소재를 입력하세요: ").strip()
    if not material:
        print("[오류] 재질은 필수입니다.")
        sys.exit(1)

    purpose = input("용도·기능을 입력하세요: ").strip()
    if not purpose:
        print("[오류] 용도는 필수입니다.")
        sys.exit(1)

    while True:
        trade_direction = input("수출/수입을 선택하세요 (수출/수입): ").strip()
        if trade_direction in ("수출", "수입"):
            break
        print("  '수출' 또는 '수입'을 입력해주세요.")

    process_stage = input("공정 단계 (선택, Enter 스킵): ").strip()
    existing_hs_code = input("기존 HS-Code (선택, Enter 스킵): ").strip()

    return {
        "product_name": product_name,
        "material": material,
        "purpose": purpose,
        "trade_direction": trade_direction,
        "process_stage": process_stage or None,
        "existing_hs_code": existing_hs_code or None,
    }


def _print_result(result: dict):
    print()
    print("=" * 42)
    print(" 추천 결과")
    print("=" * 42)

    if result.get("error_message"):
        print(f"[오류] {result['error_message']}")
        return

    print(result.get("final_response", "(응답 없음)"))
    print()
    rt = result.get("response_time_sec", 0)
    eq = result.get("evidence_quality_score", 0)
    print(f"응답시간: {rt:.1f}초 | 근거품질: {eq:.1f}/8점")
    print("=" * 42)


def main():
    print("=== HSAgent — HS-Code 추천 AI ===")
    print("반도체 수출입 담당자를 위한 HS-Code 분류 지원 시스템")

    _check_env()

    from agents.orchestrator import run_agent

    while True:
        input_data = _collect_input()

        print()
        print("[HSAgent 처리 중...]")

        result = run_agent(input_data)
        _print_result(result)

        again = input("\n다시 조회하시겠습니까? (y/n): ").strip().lower()
        if again != "y":
            print("HSAgent를 종료합니다.")
            break


if __name__ == "__main__":
    main()
