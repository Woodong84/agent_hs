"""HSAgent Streamlit 웹 UI. streamlit run app.py 로 실행."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv

load_dotenv()

import streamlit as st

# ── 페이지 기본 설정
st.set_page_config(
    page_title="HSAgent — HS-Code 추천",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS 스타일
st.markdown("""
<style>
.result-box   { background:#f0f4ff; border-left:4px solid #4a6cf7;
                padding:1rem 1.2rem; border-radius:6px; margin:0.5rem 0; }
.fallback-box { background:#fff8e1; border-left:4px solid #f0a500;
                padding:1rem 1.2rem; border-radius:6px; margin:0.5rem 0; }
.warn-box     { background:#fff3f3; border-left:4px solid #e53935;
                padding:0.8rem 1rem; border-radius:6px; margin:0.5rem 0; }
.meta-row     { color:#555; font-size:0.85rem; margin-top:0.4rem; }
</style>
""", unsafe_allow_html=True)


# ── 사이드바: 설정 및 안내
def _sidebar():
    with st.sidebar:
        st.title("⚙️ HSAgent 설정")

        api_key = st.text_input(
            "Anthropic API Key",
            value=os.environ.get("ANTHROPIC_API_KEY", ""),
            type="password",
            help=".env 파일에 설정하면 자동 로드됩니다.",
        )
        if api_key:
            os.environ["ANTHROPIC_API_KEY"] = api_key

        st.divider()
        st.markdown("**임계값 설정**")
        threshold = st.slider(
            "유사도 임계값", min_value=0.5, max_value=0.95,
            value=0.75, step=0.05,
            help="이 값 미만이면 Fallback 처리됩니다."
        )

        st.divider()
        st.markdown("**사용 안내**")
        st.markdown("""
1. 왼쪽 입력 폼에 품목 정보 입력
2. **HS-Code 추천 받기** 클릭
3. 추천 결과 및 세율 확인
4. 필요 시 관세사 최종 확인

⚠️ 본 결과는 **참고용**이며 최종 확정은 전문가 검토 필수
""")

        st.divider()
        with st.expander("❓ HS-Code란?"):
            st.markdown("""
국제 통일 상품 분류 체계(Harmonized System).
수출입 물품에 부여되는 **6~10자리 품목 코드**로,
관세율·수출입 규제가 이 코드 기준으로 적용됩니다.
""")
    return threshold


# ── 입력 폼
def _input_form():
    st.header("📦 품목 정보 입력")

    col1, col2 = st.columns(2)
    with col1:
        product_name = st.text_input(
            "품목명 *",
            placeholder="예: FOUP, Bond Wire, CMP Slurry",
            help="필수 입력 항목"
        )
        material = st.text_input(
            "재질·소재 *",
            placeholder="예: 폴리카보네이트, 알루미늄 99.9%, 콜로이달 실리카",
        )
        purpose = st.text_area(
            "용도·기능 *",
            placeholder="예: 300mm 웨이퍼 클린룸 이송 및 보관",
            height=80,
        )

    with col2:
        trade_direction = st.radio(
            "수출/수입 *",
            options=["수출", "수입"],
            horizontal=True,
        )
        process_stage = st.text_input(
            "공정 단계 (선택)",
            placeholder="예: 전공정 CMP, 후공정 패키징",
        )
        existing_hs_code = st.text_input(
            "기존 HS-Code (선택, 재검토 시 입력)",
            placeholder="예: 3923100000",
            max_chars=12,
        )

    return {
        "product_name": product_name.strip(),
        "material": material.strip(),
        "purpose": purpose.strip(),
        "trade_direction": trade_direction,
        "process_stage": process_stage.strip() or None,
        "existing_hs_code": existing_hs_code.strip() or None,
    }


# ── 결과 렌더링
def _render_result(result: dict):
    if result.get("error_message"):
        st.markdown(
            f'<div class="warn-box">❌ <b>오류 발생</b><br>{result["error_message"]}</div>',
            unsafe_allow_html=True,
        )
        return

    rt = result.get("response_time_sec", 0)
    eq = result.get("evidence_quality_score", 0)

    # 메타 지표
    col_a, col_b, col_c = st.columns(3)
    col_a.metric("응답 시간", f"{rt:.1f}초", delta="✅" if rt <= 10 else "⚠️ 초과")
    col_b.metric("근거 품질", f"{eq:.1f}/8.0점", delta="✅" if eq >= 6 else "보완 필요")
    col_c.metric("Fallback", "예" if result.get("fallback_triggered") else "아니오")

    st.divider()

    if result.get("fallback_triggered"):
        st.markdown(
            f'<div class="fallback-box">⚠️ <b>근거 부족 — HS-Code 추천 불가</b><br><br>'
            f'<pre style="white-space:pre-wrap">{result["final_response"]}</pre></div>',
            unsafe_allow_html=True,
        )
        return

    # 추천 결과 본문
    st.markdown("### 📋 추천 결과")
    final_response = result.get("final_response", "")
    if final_response:
        st.markdown(
            f'<div class="result-box"><pre style="white-space:pre-wrap;font-family:inherit">'
            f'{final_response}</pre></div>',
            unsafe_allow_html=True,
        )

    # candidates 상세 펼치기
    candidates = result.get("candidates", [])
    if candidates:
        with st.expander("🔍 후보 코드 상세 (RAG 근거 포함)"):
            for c in candidates:
                rank = c.get("rank", "?")
                hs = c.get("hs_code", "")
                conf = c.get("confidence", "")
                st.markdown(f"**[{rank}순위] {hs}** — 신뢰도: {conf}")
                for ev in c.get("evidence", []):
                    sim = ev.get("similarity_score", 0)
                    doc = ev.get("doc_name", "")
                    page = ev.get("page", "")
                    cite = ev.get("citation", "")
                    st.markdown(
                        f"&nbsp;&nbsp;`유사도 {sim:.2f}` · {doc} {page}  \n"
                        f"&nbsp;&nbsp;*\"{cite[:100]}...\"*"
                    )
                st.markdown("---")

    # 세율 정보
    audit = result.get("audit_log", {})
    tax = audit.get("tax_result", {})
    if tax and tax.get("hs_code"):
        with st.expander("💰 세율 정보"):
            t_col1, t_col2 = st.columns(2)
            with t_col1:
                st.markdown(f"**HS-Code**: `{tax['hs_code']}`")
                st.markdown(f"**기본관세율**: {tax.get('basic_rate', '확인필요')}")
                if tax.get("is_fallback"):
                    st.caption("※ 정적 세율표 기준 (UNI-PASS API 미연결)")
            with t_col2:
                st.markdown("**FTA 협정세율**")
                for fta in tax.get("fta_rates", []):
                    st.markdown(f"- {fta['country']} ({fta['agreement']}): **{fta['rate']}**")
            req = tax.get("import_requirements", "")
            if req:
                st.markdown(f"**수입 요건**: {req}")

    # 면책 고지
    st.markdown("""
---
> ⚠️ **면책 고지**: 본 결과는 AI 참고용이며 최종 HS-Code 확정은 반드시 담당자 또는 관세사 검토가 필요합니다.
""")


# ── 이력 관리
def _init_history():
    if "history" not in st.session_state:
        st.session_state.history = []


def _add_history(input_data: dict, result: dict):
    st.session_state.history.append({
        "product_name": input_data.get("product_name", ""),
        "trade_direction": input_data.get("trade_direction", ""),
        "fallback": result.get("fallback_triggered", False),
        "response_time": result.get("response_time_sec", 0),
        "result": result,
    })


def _render_history():
    if not st.session_state.get("history"):
        return
    st.sidebar.divider()
    st.sidebar.markdown("**📜 조회 이력**")
    for i, h in enumerate(reversed(st.session_state.history[-5:])):
        icon = "⚠️" if h["fallback"] else "✅"
        label = f"{icon} {h['product_name']} ({h['trade_direction']})"
        if st.sidebar.button(label, key=f"hist_{i}"):
            st.session_state.show_history = h["result"]


# ── 메인
def main():
    st.title("🔍 HSAgent — HS-Code 추천 AI")
    st.caption("반도체 수출입 담당자를 위한 HS-Code 분류 지원 시스템")

    _init_history()
    threshold = _sidebar()
    _render_history()

    # API 키 미설정 경고
    if not os.environ.get("ANTHROPIC_API_KEY"):
        st.warning("⚠️ Anthropic API Key가 설정되지 않았습니다. 사이드바에서 입력하거나 .env 파일을 설정해주세요.")

    input_data = _input_form()

    st.markdown("")
    submitted = st.button(
        "🚀 HS-Code 추천 받기",
        type="primary",
        disabled=not bool(
            input_data["product_name"]
            and input_data["material"]
            and input_data["purpose"]
            and os.environ.get("ANTHROPIC_API_KEY")
        ),
    )

    if submitted:
        # 설정값 반영
        from configs.settings import settings
        input_data["similarity_threshold"] = threshold

        with st.spinner("HSAgent 분석 중... (약 5~15초 소요)"):
            from agents.orchestrator import run_agent
            result = run_agent(input_data)

        _add_history(input_data, result)
        st.session_state.last_result = result
        st.session_state.last_input = input_data

    # 결과 표시
    if st.session_state.get("show_history"):
        st.header("📋 이전 조회 결과")
        _render_result(st.session_state.pop("show_history"))
    elif st.session_state.get("last_result"):
        st.header("📋 추천 결과")
        _render_result(st.session_state.last_result)
    else:
        st.info("👆 위에서 품목 정보를 입력하고 **HS-Code 추천 받기** 버튼을 클릭하세요.")


if __name__ == "__main__":
    main()
