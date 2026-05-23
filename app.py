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

# ── CSS 스타일 (파란색·주황색 계열 테마)
st.markdown("""
<style>
/* ── 전체 배경 */
.stApp {
    background: linear-gradient(160deg, #f0f5ff 0%, #fdf6ee 100%);
}

/* ── 사이드바 */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0f2d6b 0%, #1a4299 100%);
}
[data-testid="stSidebar"] * {
    color: #e8f0ff !important;
}
[data-testid="stSidebar"] .stTextInput input,
[data-testid="stSidebar"] .stSelectbox select {
    background: rgba(255,255,255,0.12) !important;
    border: 1px solid rgba(255,255,255,0.25) !important;
    color: #fff !important;
    border-radius: 6px;
}
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
[data-testid="stSidebar"] label {
    color: #c8d8ff !important;
}
[data-testid="stSidebar"] .stSlider [data-testid="stTickBar"] {
    color: #8ab4ff !important;
}
[data-testid="stSidebar"] hr {
    border-color: rgba(255,255,255,0.2) !important;
}

/* ── 사이드바 버튼 */
[data-testid="stSidebar"] .stButton > button {
    background: rgba(255,255,255,0.12) !important;
    border: 1px solid rgba(255,255,255,0.3) !important;
    color: #fff !important;
    border-radius: 6px;
    transition: background 0.2s;
}
[data-testid="stSidebar"] .stButton > button:hover {
    background: rgba(255,255,255,0.22) !important;
}

/* ── 메인 타이틀 */
h1 { color: #0f2d6b !important; letter-spacing: -0.5px; }
h2 { color: #1a4299 !important; }
h3 { color: #1e56c4 !important; }

/* ── 기본 버튼 (primary) */
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #1a4299 0%, #2563eb 100%) !important;
    border: none !important;
    color: #fff !important;
    font-weight: 600;
    border-radius: 8px;
    padding: 0.5rem 1.4rem;
    box-shadow: 0 2px 8px rgba(37,99,235,0.35);
    transition: all 0.2s;
}
.stButton > button[kind="primary"]:hover {
    background: linear-gradient(135deg, #0f2d6b 0%, #1a4299 100%) !important;
    box-shadow: 0 4px 14px rgba(37,99,235,0.45);
    transform: translateY(-1px);
}

/* ── 보조 버튼 */
.stButton > button:not([kind="primary"]) {
    border: 1.5px solid #2563eb !important;
    color: #1a4299 !important;
    border-radius: 8px;
    background: #fff !important;
    transition: all 0.2s;
}
.stButton > button:not([kind="primary"]):hover {
    background: #eff6ff !important;
    border-color: #1a4299 !important;
}

/* ── 결과 박스 (파란색 계열) */
.result-box {
    background: #eff6ff;
    border-left: 4px solid #2563eb;
    padding: 1rem 1.2rem;
    border-radius: 8px;
    margin: 0.5rem 0;
    box-shadow: 0 1px 6px rgba(37,99,235,0.1);
}

/* ── Fallback 박스 (주황색 계열) */
.fallback-box {
    background: #fff7ed;
    border-left: 4px solid #f97316;
    padding: 1rem 1.2rem;
    border-radius: 8px;
    margin: 0.5rem 0;
    box-shadow: 0 1px 6px rgba(249,115,22,0.12);
}

/* ── 경고 박스 (진한 주황) */
.warn-box {
    background: #fff3e0;
    border-left: 4px solid #ea580c;
    padding: 0.8rem 1rem;
    border-radius: 8px;
    margin: 0.5rem 0;
}

.meta-row { color: #475569; font-size: 0.85rem; margin-top: 0.4rem; }

/* ── 메트릭 카드 */
[data-testid="stMetric"] {
    background: #fff;
    border: 1px solid #bfdbfe;
    border-radius: 10px;
    padding: 0.7rem 1rem;
    box-shadow: 0 1px 4px rgba(37,99,235,0.08);
}
[data-testid="stMetricLabel"] { color: #1a4299 !important; font-size: 0.82rem; font-weight: 600; }
[data-testid="stMetricValue"] { color: #0f2d6b !important; font-weight: 700; }

/* ── Info 배너 */
[data-testid="stInfo"] {
    background: #eff6ff !important;
    border: 1px solid #93c5fd !important;
    border-radius: 8px;
    color: #1e40af !important;
}

/* ── Success 배너 */
[data-testid="stSuccess"] {
    background: #f0fdf4 !important;
    border: 1px solid #86efac !important;
    border-radius: 8px;
}

/* ── Warning 배너 */
[data-testid="stWarning"] {
    background: #fff7ed !important;
    border: 1px solid #fdba74 !important;
    border-radius: 8px;
    color: #9a3412 !important;
}

/* ── Error 배너 */
[data-testid="stError"] {
    background: #fff1f2 !important;
    border: 1px solid #fda4af !important;
    border-radius: 8px;
}

/* ── Expander */
[data-testid="stExpander"] {
    border: 1px solid #bfdbfe !important;
    border-radius: 8px !important;
    background: #fff !important;
}
[data-testid="stExpander"] summary {
    color: #1a4299 !important;
    font-weight: 600;
}
[data-testid="stExpander"] summary:hover {
    color: #f97316 !important;
}

/* ── 입력 필드 */
.stTextInput input,
.stTextArea textarea {
    border: 1.5px solid #bfdbfe !important;
    border-radius: 7px !important;
    background: #fff !important;
    transition: border-color 0.2s;
}
.stTextInput input:focus,
.stTextArea textarea:focus {
    border-color: #2563eb !important;
    box-shadow: 0 0 0 3px rgba(37,99,235,0.12) !important;
}

/* ── 라디오 버튼 */
[data-testid="stRadio"] label {
    color: #1a4299 !important;
    font-weight: 500;
}

/* ── 탭 */
[data-testid="stTabs"] [data-baseweb="tab"] {
    color: #64748b !important;
    border-bottom: 2px solid transparent;
}
[data-testid="stTabs"] [aria-selected="true"] {
    color: #f97316 !important;
    border-bottom: 2px solid #f97316 !important;
}

/* ── 구분선 */
hr { border-color: #bfdbfe !important; }

/* ── 슬라이더 */
[data-testid="stSlider"] [data-baseweb="slider"] [role="slider"] {
    background: #f97316 !important;
    border-color: #f97316 !important;
}
[data-testid="stSlider"] [data-baseweb="slider"] [data-testid="stTickBar"] {
    background: #2563eb !important;
}

/* ── 코드 블록 */
.stCode, code {
    background: #f0f5ff !important;
    border: 1px solid #bfdbfe !important;
    color: #1a4299 !important;
    border-radius: 5px;
}

/* ── 캡션 */
[data-testid="stCaptionContainer"] {
    color: #64748b !important;
}

/* ── 헤더 구분 배너 */
.section-header {
    background: linear-gradient(90deg, #1a4299, #2563eb);
    color: #fff !important;
    padding: 0.5rem 1rem;
    border-radius: 6px;
    font-weight: 600;
    margin-bottom: 0.8rem;
}

/* ── 충돌 감지 배너 (주황) */
.conflict-box {
    background: #fff7ed;
    border-left: 4px solid #ea580c;
    padding: 10px 14px;
    border-radius: 6px;
    margin-bottom: 8px;
    box-shadow: 0 1px 4px rgba(234,88,12,0.12);
}
</style>
""", unsafe_allow_html=True)


# ── 사이드바: 설정 및 안내
def _sidebar():
    with st.sidebar:
        st.title("⚙️ HSAgent 설정")

        # ── API 키 탭 선택
        tab_azure, tab_anthropic = st.tabs(["Azure OpenAI", "Anthropic"])

        with tab_azure:
            az_key = st.text_input(
                "Azure OpenAI API Key",
                value=os.environ.get("AZURE_OPENAI_API_KEY", ""),
                type="password",
                key="az_key",
                help="이미지의 키(atl-...)를 입력하세요.",
            )
            az_endpoint = st.text_input(
                "Endpoint",
                value=os.environ.get("AZURE_OPENAI_ENDPOINT", ""),
                key="az_ep",
                placeholder="https://aitalentlab.skax.co.kr:18081",
            )
            az_deploy = st.text_input(
                "LLM 모델명 (deployment)",
                value=os.environ.get("AZURE_OPENAI_DEPLOYMENT", "gpt-4.1"),
                key="az_deploy",
            )
            az_emb = st.text_input(
                "임베딩 모델명",
                value=os.environ.get("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-3-small"),
                key="az_emb",
            )
            if az_key and az_endpoint:
                os.environ["AZURE_OPENAI_API_KEY"] = az_key
                os.environ["AZURE_OPENAI_ENDPOINT"] = az_endpoint
                os.environ["AZURE_OPENAI_DEPLOYMENT"] = az_deploy
                os.environ["AZURE_OPENAI_EMBEDDING_DEPLOYMENT"] = az_emb
                os.environ["AZURE_OPENAI_API_VERSION"] = "2024-12-01-preview"
                # 설정 변경 시 executor 캐시 초기화
                from agents.orchestrator import reset_executor_cache
                reset_executor_cache()
                st.success("Azure OpenAI 연결 준비 완료")

        with tab_anthropic:
            ant_key = st.text_input(
                "Anthropic API Key",
                value=os.environ.get("ANTHROPIC_API_KEY", ""),
                type="password",
                key="ant_key",
                help="sk-ant-... 형식의 키를 입력하세요.",
            )
            if ant_key:
                os.environ["ANTHROPIC_API_KEY"] = ant_key

        st.divider()
        st.markdown("**임계값 설정**")
        threshold = st.slider(
            "유사도 임계값", min_value=0.01, max_value=0.95,
            value=0.45, step=0.01,
            help="RAG 검색 최소 유사도. 낮을수록 더 많은 문서를 참조합니다."
        )

        st.divider()
        st.markdown("**RAG 데이터 관리**")
        from configs.settings import settings as _s2
        if _s2.use_pinecone:
            try:
                from pinecone import Pinecone as _PC
                _pc = _PC(api_key=_s2.PINECONE_API_KEY)
                _idx = _pc.Index(_s2.PINECONE_INDEX_NAME)
                _stats = _idx.describe_index_stats()
                _cnt = _stats.get("total_vector_count", 0)
                if _cnt > 0:
                    st.success(f"✅ Pinecone 벡터: {_cnt}개 적재됨")
                else:
                    st.warning("⚠️ Pinecone 비어있음 — 아래 버튼으로 적재하세요")
            except Exception:
                st.caption("Pinecone 상태 확인 불가")

            if st.button("📥 샘플 문서 Pinecone 적재"):
                with st.spinner("Pinecone에 문서 적재 중..."):
                    try:
                        from data_ingest.ingest import run_ingest
                        from tools.search_hs import reset_vectorstore_cache
                        run_ingest()
                        reset_vectorstore_cache()
                        st.success("✅ 적재 완료!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ 적재 실패: {str(e)[:300]}")

            with st.expander("🔬 RAG 유사도 진단"):
                test_q = st.text_input("진단 쿼리", value="FOUP 폴리카보네이트 웨이퍼 이송", key="diag_q")
                if st.button("유사도 점수 확인", key="diag_btn"):
                    try:
                        from tools.search_hs import _get_vectorstore, _get_embeddings, reset_vectorstore_cache
                        reset_vectorstore_cache()
                        vs = _get_vectorstore()
                        raw = vs.similarity_search_with_score(test_q, k=5)
                        if raw:
                            for doc, score in raw:
                                src = doc.metadata.get("source", "?")
                                hs = doc.metadata.get("hs_code", "?")
                                st.markdown(f"`{score:.4f}` — {src} (HS:{hs})")
                        else:
                            st.warning("검색 결과 없음")
                    except Exception as e:
                        st.error(f"오류: {str(e)[:300]}")
        else:
            st.caption("⚠️ PINECONE_API_KEY 미설정")

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

    # Fallback 원인 표시 (진단용)
    if result.get("fallback_triggered") and result.get("fallback_reason"):
        st.caption(f"ℹ️ Fallback 원인: `{result.get('fallback_reason')}`")

    st.divider()

    _HS_CLASS_DESC = {
        "28": "화학원소·화합물 (28류)",
        "38": "혼합 화학제품 (38류)",
        "39": "플라스틱 제품 (39류)",
        "69": "공업용 도자제품·세라믹 (69류)",
        "70": "유리·유리제품 (70류)",
        "76": "알루미늄 제품 (76류)",
        "84": "반도체 제조장비·기계 (84류)",
        "85": "전기기기·반도체 부품 (85류)",
        "90": "광학·측정기기 (90류)",
    }

    # 충돌 경고 배너
    if result.get("conflict_flag"):
        conflict_type = result.get("conflict_type", "")
        conflict_detail = result.get("conflict_detail", "")
        type_desc = {
            "TYPE-1": "상위 후보 간 류(類) 코드 충돌",
            "TYPE-2": "기존 HS-Code와 추천 코드 불일치",
            "TYPE-3": "복수 코드가 동등하게 지지됨",
        }.get(conflict_type, "분류 충돌 감지")
        st.markdown(
            f'<div class="conflict-box">'
            f'⚠️ <b style="color:#9a3412">분류 충돌 감지 ({conflict_type}) — {type_desc}</b><br>'
            f'<span style="font-size:0.85rem;color:#78350f">{conflict_detail} · 관세사 확인을 권장합니다.</span></div>',
            unsafe_allow_html=True,
        )

        # TYPE-2 전용: 사내 코드 통일 경고 + A/B 비교표
        if conflict_type == "TYPE-2":
            audit_in = result.get("audit_log", {}).get("input", {})
            existing_code = (audit_in.get("existing_hs_code") or "").strip()
            candidates_all = result.get("candidates", [])
            top1_code = candidates_all[0]["hs_code"] if candidates_all else ""

            st.warning(
                "⚠️ **사내 코드 불일치 감지** — 동일 품목에 서로 다른 HS-Code가 사용되고 있습니다. "
                "**사내 코드 통일 검토가 필요합니다.** 관세청 품목분류 사전심사 또는 관세사 확인을 권장합니다."
            )

            if existing_code and top1_code:
                st.markdown("#### 📊 후보 코드 비교 분석")
                col_a, col_b = st.columns(2)
                with col_a:
                    cls_a = existing_code[:2]
                    desc_a = _HS_CLASS_DESC.get(cls_a, f"{cls_a}류")
                    st.markdown(
                        f'<div style="background:#f8fafc;border:1.5px solid #94a3b8;padding:14px;border-radius:8px;box-shadow:0 1px 4px rgba(0,0,0,0.06)">'
                        f'<b style="color:#475569">후보 A — 기존 코드</b><br>'
                        f'<span style="font-size:1.15rem;font-family:monospace;color:#0f2d6b;font-weight:700">{existing_code}</span><br>'
                        f'<span style="color:#64748b;font-size:0.88rem">{desc_a}</span>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
                with col_b:
                    cls_b = top1_code[:2]
                    desc_b = _HS_CLASS_DESC.get(cls_b, f"{cls_b}류")
                    top1_conf = candidates_all[0].get("confidence", "") if candidates_all else ""
                    st.markdown(
                        f'<div style="background:#fff7ed;border:1.5px solid #f97316;padding:14px;border-radius:8px;box-shadow:0 1px 6px rgba(249,115,22,0.15)">'
                        f'<b style="color:#c2410c">후보 B — RAG 추천 코드</b><br>'
                        f'<span style="font-size:1.15rem;font-family:monospace;color:#ea580c;font-weight:700">{top1_code}</span><br>'
                        f'<span style="color:#9a3412;font-size:0.88rem">{desc_b} · 신뢰도: {top1_conf}</span>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

    if result.get("fallback_triggered"):
        st.markdown(
            '<div class="fallback-box">⚠️ <b>RAG 문서 근거 없음 — LLM 지식 기반 추천</b><br>'
            '<span style="font-size:0.85rem;color:#888">관련 문서가 DB에 없어 AI 자체 지식으로 추천합니다. 반드시 전문가 확인 필요.</span></div>',
            unsafe_allow_html=True,
        )
        st.markdown("### 📋 추천 결과 (LLM 지식 기반)")
        final_response = result.get("final_response", "")
        if final_response:
            st.markdown(
                f'<div class="result-box"><pre style="white-space:pre-wrap;font-family:inherit">'
                f'{final_response}</pre></div>',
                unsafe_allow_html=True,
            )
        st.markdown("""
---
> ⚠️ **면책 고지**: 문서 근거 없이 AI 지식만으로 생성된 참고용이며 최종 확정은 반드시 관세사 검토 필요.
""")
        return

    # 추천 결과 본문
    st.markdown("### 📋 추천 결과")
    final_response = result.get("final_response", "")
    if final_response:
        # 주요 섹션 마커 앞에 빈 줄 삽입 → 문장별 줄바꿈
        _MARKERS = [
            "[1순위]", "[2순위]", "[3순위]", "[4순위]", "[5순위]",
            "[주의]", "[세율]", "[경고]", "[Clarification", "[상충",
            "→ 근거:", "→ 품목 설명:", "→ 적용 조건:",
        ]
        formatted_response = final_response
        for marker in _MARKERS:
            formatted_response = formatted_response.replace(marker, f"\n\n{marker}")
        # 단일 \n → 줄바꿈 유지, 연속 공백 정리
        formatted_response = formatted_response.strip()
        st.markdown(
            f'<div class="result-box"><pre style="white-space:pre-wrap;font-family:inherit;line-height:1.7">'
            f'{formatted_response}</pre></div>',
            unsafe_allow_html=True,
        )

    # candidates 상세 펼치기
    candidates = result.get("candidates", [])
    if candidates:
        # 중복 HS 코드 제거 (이미 search_hs.py에서 처리되나 방어 처리)
        seen_hs: set = set()
        unique_candidates = []
        for c in candidates:
            hs = c.get("hs_code", "")
            if hs not in seen_hs:
                seen_hs.add(hs)
                unique_candidates.append(c)

        with st.expander("🔍 후보 코드 상세 (RAG 근거 포함)"):
            for c in unique_candidates:
                rank = c.get("rank", "?")
                hs = c.get("hs_code", "")
                conf = c.get("confidence", "")
                evidences = c.get("evidence", [])

                st.markdown(f"**[{rank}순위] `{hs}`** — 신뢰도: **{conf}**")

                # 근거 출처 목록 (문서+청크 동일 OR 유사도+인용문 동일 시 중복 제거)
                seen_docs: set = set()
                unique_evs = []
                for ev in evidences:
                    doc_key = ev.get("doc_name", "") + ev.get("chunk_id", "")
                    sim_key = str(ev.get("similarity_score", "")) + ev.get("citation", "")[:60]
                    if doc_key not in seen_docs and sim_key not in seen_docs:
                        seen_docs.add(doc_key)
                        seen_docs.add(sim_key)
                        unique_evs.append(ev)

                for ev in unique_evs[:3]:   # 출처 최대 3개 표시
                    sim = ev.get("similarity_score", 0)
                    doc = ev.get("doc_name", "")
                    page = ev.get("page", "")
                    cite = ev.get("citation", "")
                    st.markdown(
                        f"&nbsp;&nbsp;`유사도 {sim:.2f}` · **{doc}** {page}  \n"
                        f"&nbsp;&nbsp;*\"{cite[:120]}...\"*"
                    )

                # 유사 정보: 동일 코드를 지지하는 근거가 복수일 때 요약 표시
                if len(unique_evs) > 1:
                    extra_docs = [ev.get("doc_name", "") for ev in unique_evs[1:3]]
                    st.caption(
                        f"   ℹ️ 추가 유사 근거 {len(unique_evs)-1}건 확인됨: "
                        f"{', '.join(extra_docs)}"
                    )

                # 유사 정보: top5_chunks 중 같은 HS 코드 앞 4자리를 지지하는 청크 수
                # UNKNOWN/빈 코드는 제외
                top5 = result.get("audit_log", {}).get("rag_result", {}).get("top5_chunks", [])
                related = [
                    ch for ch in top5
                    if ch.get("supports_hs", "")
                    and not ch.get("supports_hs", "").startswith("UNKNOWN")
                    and ch.get("supports_hs", "")[:4] == hs[:4]
                    and ch.get("supports_hs", "") != hs
                ]
                if related:
                    related_codes = list({ch["supports_hs"] for ch in related})
                    st.caption(
                        f"   🔗 동일 류(類) 내 유사 코드: "
                        f"{', '.join(related_codes[:3])}"
                    )

                st.markdown("---")

        # JSON 출력 (Interface 연동용)
        import json as _json
        audit = result.get("audit_log", {})
        input_data = audit.get("input", {})
        json_output = {
            "product_info": {
                "product_name": input_data.get("product_name", ""),
                "material": input_data.get("material", ""),
                "purpose": input_data.get("purpose", ""),
                "trade_direction": input_data.get("trade_direction", ""),
                "process_stage": input_data.get("process_stage", ""),
                "existing_hs_code": input_data.get("existing_hs_code", ""),
            },
            "hs_code_candidates": [
                {
                    "rank": c.get("rank"),
                    "hs_code": c.get("hs_code", ""),
                    "confidence": c.get("confidence", ""),
                }
                for c in candidates
            ],
        }
        with st.expander("📎 JSON 출력 (Interface 연동용)"):
            st.code(_json.dumps(json_output, ensure_ascii=False, indent=2), language="json")

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

    # API 키 상태 확인 (Azure 우선, 없으면 Anthropic)
    from configs.settings import Settings
    _s = Settings()
    _has_llm = _s.use_azure or bool(os.environ.get("ANTHROPIC_API_KEY"))
    if not _has_llm:
        st.warning("⚠️ API Key가 설정되지 않았습니다. 사이드바의 **Azure OpenAI** 또는 **Anthropic** 탭에서 키를 입력해주세요.")
    else:
        provider = "Azure OpenAI" if _s.use_azure else "Anthropic Claude"
        st.info(f"✅ LLM 연결: **{provider}**")

    input_data = _input_form()

    st.markdown("")
    submitted = st.button(
        "🚀 HS-Code 추천 받기",
        type="primary",
        disabled=not bool(
            input_data["product_name"]
            and input_data["material"]
            and input_data["purpose"]
            and _has_llm
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
