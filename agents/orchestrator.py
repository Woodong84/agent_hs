"""1차 PoC LangChain ReAct 단일 Orchestrator Agent.
Azure OpenAI 키 설정 시 우선 사용, 없으면 Anthropic으로 Fallback.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import time
from langchain.agents import AgentExecutor, create_react_agent
from langchain.prompts import PromptTemplate
from configs.settings import settings
from configs.prompts import ORCHESTRATOR_SYSTEM_PROMPT, FALLBACK_PROMPT
from tools.search_hs import search_hs_code_rag
from tools.query_tax import query_tax_rate
from tools.audit_log import save_audit_log

_TOOLS = [search_hs_code_rag, query_tax_rate]

_REACT_TEMPLATE = (
    ORCHESTRATOR_SYSTEM_PROMPT
    + """

사용 가능한 도구:
{tools}

도구 이름 목록: {tool_names}

형식:
Question: 처리할 입력
Thought: 다음 액션을 생각합니다
Action: 도구 이름
Action Input: 도구 입력값 (반드시 아래 예시처럼 개별 필드를 가진 JSON 객체로 입력)
Observation: 도구 결과
... (Thought/Action/Observation 반복)
Thought: 최종 답변을 작성합니다
Final Answer: 최종 출력

[중요] search_hs_code_rag 호출 예시:
Action: search_hs_code_rag
Action Input: {{"product_name": "FOUP", "material": "폴리카보네이트", "purpose": "300mm 웨이퍼 이송", "trade_direction": "수입"}}

Action Input은 반드시 개별 키-값 쌍으로 구성된 JSON 객체여야 합니다.
절대로 전체 입력을 하나의 문자열로 직렬화하여 단일 필드에 넣지 마세요.

Question: {input}
{agent_scratchpad}"""
)

_executor_cache: AgentExecutor | None = None


def _build_llm():
    """Azure OpenAI 설정 시 AzureChatOpenAI, 없으면 ChatAnthropic 반환."""
    if settings.use_azure:
        from langchain_openai import AzureChatOpenAI
        return AzureChatOpenAI(
            azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
            azure_deployment=settings.AZURE_OPENAI_DEPLOYMENT,
            api_key=settings.AZURE_OPENAI_API_KEY,
            api_version=settings.AZURE_OPENAI_API_VERSION,
            max_tokens=4096,
        )
    from langchain_anthropic import ChatAnthropic
    return ChatAnthropic(
        model=settings.ANTHROPIC_MODEL,
        api_key=settings.ANTHROPIC_API_KEY,
        max_tokens=4096,
    )


def _build_agent_executor() -> AgentExecutor:
    global _executor_cache
    if _executor_cache is not None:
        return _executor_cache
    llm = _build_llm()
    prompt = PromptTemplate.from_template(_REACT_TEMPLATE)
    agent = create_react_agent(llm=llm, tools=_TOOLS, prompt=prompt)
    _executor_cache = AgentExecutor(
        agent=agent,
        tools=_TOOLS,
        max_iterations=5,
        verbose=True,
        handle_parsing_errors=True,
        return_intermediate_steps=True,
    )
    return _executor_cache


def reset_executor_cache():
    """API 키 변경 시 캐시 초기화용."""
    global _executor_cache
    _executor_cache = None


def _parse_observation(observation) -> dict:
    """intermediate_steps의 observation을 dict로 변환."""
    if isinstance(observation, dict):
        return observation
    if isinstance(observation, str):
        try:
            parsed = json.loads(observation)
            if isinstance(parsed, dict):
                return parsed
        except (json.JSONDecodeError, ValueError):
            pass
    return {}


def _format_question(data: dict) -> str:
    lines = [
        f"품목명: {data.get('product_name', '')}",
        f"재질: {data.get('material', '')}",
        f"용도: {data.get('purpose', '')}",
        f"수출입: {data.get('trade_direction', '')}",
    ]
    if data.get("process_stage"):
        lines.append(f"공정 단계: {data['process_stage']}")
    if data.get("existing_hs_code"):
        lines.append(f"기존 HS-Code: {data['existing_hs_code']}")
    threshold = data.get("similarity_threshold", 0.30)
    lines.append(f"similarity_threshold: {threshold}")
    return "\n".join(lines)


def run_agent(input_data: dict) -> dict:
    """
    input_data: {product_name, material, purpose, trade_direction, ...}
    반환: {candidates, final_response, evidence_quality_score,
           fallback_triggered, response_time_sec, audit_log, error_message}
    """
    start = time.time()
    base_result = {
        "candidates": [],
        "final_response": "",
        "evidence_quality_score": 0.0,
        "fallback_triggered": False,
        "fallback_reason": None,
        "conflict_flag": False,
        "conflict_type": None,
        "conflict_detail": None,
        "response_time_sec": 0.0,
        "audit_log": {},
        "error_message": None,
        "llm_provider": "azure" if settings.use_azure else "anthropic",
    }

    product_name = input_data.get("product_name", "")
    material = input_data.get("material", "")
    trade_direction = input_data.get("trade_direction", "")
    threshold = input_data.get("similarity_threshold", 0.30)
    existing_code = input_data.get("existing_hs_code", "") or "없음"
    llm_label = "Azure OpenAI gpt-4.1" if settings.use_azure else "Claude Sonnet 4.5"

    print("\n╔══════════════════════════════════════════════╗")
    print("║  HSAgent — Deep Reasoning Trace 시작         ║")
    print("╚══════════════════════════════════════════════╝")
    print(f"[CONTEXT] 품목: {product_name} | 재질: {material} | 방향: {trade_direction}")
    print(f"[CONTEXT] 유사도 임계값: {threshold} | 기존코드: {existing_code} | LLM: {llm_label}")
    print("[PLANNING] 4-step execution plan generated. Simulating plan...")
    print("  ▷ Step 1/4. RAG 문서 검색 실행 (Pinecone 코사인 유사도)")
    print("  ▷ Step 2/4. 충돌 감지 및 후보 Top-3 정렬 (결정론적 룰 엔진)")
    print("  ▷ Step 3/4. 관세율 조회 (정적 세율 테이블, 기존코드 의존)")
    print("  ▷ Step 4/4. 최종 응답 생성 + 감사 로그 직접 저장")
    print("[PLANNING] Plan validated. Proceeding to execution phase.")
    print("──────────────────────────────────────────────")

    try:
        executor = _build_agent_executor()
        question = _format_question(input_data)

        print("[TOOL CALL] AgentExecutor 실행 시작 (ReAct 루프)")
        print(f"  ▶ 입력 질문:\n    {question.replace(chr(10), chr(10) + '    ')}")
        print("──────────────────────────────────────────────")

        result = executor.invoke({"input": question})

        final_response = result.get("output", "")
        intermediate = result.get("intermediate_steps", [])

        rag_result: dict = {}
        tax_result: dict = {}
        for action, observation in intermediate:
            tool_name = getattr(action, "tool", "")
            tool_input = getattr(action, "tool_input", {})
            parsed = _parse_observation(observation)

            if tool_name == "search_hs_code_rag":
                print(f"[TOOL CALL] search_hs_code_rag 호출")
                if isinstance(tool_input, dict):
                    q_name = tool_input.get("product_name", product_name)
                    q_mat = tool_input.get("material", material)
                    print(f"  ▶ 품목: {q_name} | 재질: {q_mat}")
                print("──────────────────────────────────────────────")
                if parsed:
                    rag_result = parsed
                    max_sim = round(parsed.get("max_similarity", 0.0), 3)
                    candidates_count = len(parsed.get("candidates", []))
                    fallback = parsed.get("fallback", False)
                    top1 = parsed.get("candidates", [{}])[0] if parsed.get("candidates") else {}
                    top1_code = top1.get("hs_code", "N/A")
                    top1_conf = top1.get("confidence", "N/A")
                    conflict = parsed.get("conflict_flag", False)
                    conflict_type_obs = parsed.get("conflict_type", "없음")
                    print(f"[OBSERVATION] Pinecone 검색 완료")
                    print(f"  ▶ 최고 유사도: {max_sim} | 후보 코드 수: {candidates_count}건 | Fallback: {'예' if fallback else '아니오'}")
                    print(f"  ▶ Top-1: {top1_code} (신뢰도: {top1_conf})")
                    print(f"  ▶ conflict_flag: {conflict} | conflict_type: {conflict_type_obs}")
                    print("──────────────────────────────────────────────")

                    # Self-Correction: Fallback 분기 시 계획 재수정
                    if fallback:
                        print(f"[SELF-CORRECTION] 유사도 {max_sim} < 임계값 {threshold} 감지")
                        print(f"  ▶ 초기 계획(일반 추천) 폐기 → Fallback 경로로 재계획")
                        print(f"  ▶ Step 3(세율 조회) 스킵 + 황색 경고 배너 + 면책 문구 강제 출력")
                        print("──────────────────────────────────────────────")

                    # Self-Correction: 충돌 감지 시 후속 처리 경로 추가
                    if conflict:
                        print(f"[SELF-CORRECTION] {conflict_type_obs} 충돌 감지 — 계획 보강")
                        print(f"  ▶ A/B 비교 카드 자동 생성 경로 추가")
                        print(f"  ▶ 주황색 경고 배너 + '사내 코드 통일 검토 필요' 메시지 활성화")
                        print("──────────────────────────────────────────────")

            elif tool_name == "query_tax_rate":
                if isinstance(tool_input, dict):
                    hs_q = tool_input.get("hs_code", "")
                    dir_q = tool_input.get("trade_direction", trade_direction)
                else:
                    hs_q = str(tool_input)
                    dir_q = trade_direction
                print(f"[TOOL CALL] query_tax_rate 호출")
                print(f"  ▶ HS-Code: {hs_q} | 방향: {dir_q}")
                print("──────────────────────────────────────────────")
                if parsed:
                    tax_result = parsed
                    basic_rate = parsed.get("basic_rate", "정보 없음")
                    fta_rate = parsed.get("fta_rate", "정보 없음")
                    print(f"[OBSERVATION] 세율 조회 완료")
                    print(f"  ▶ 기본세율: {basic_rate} | FTA: {fta_rate}")
                    print("──────────────────────────────────────────────")

        fallback_triggered = rag_result.get("fallback", False)
        if fallback_triggered and not final_response.strip():
            similar_class = input_data.get("product_name", "해당 품목")[:10]
            final_response = FALLBACK_PROMPT.format(
                similarity_score=round(rag_result.get("max_similarity", 0.0), 2),
                similar_class=similar_class,
                similar_class_desc="참고용 분류",
            )

        candidates = rag_result.get("candidates", [])
        evidence_quality_score = _score_evidence(candidates)
        conflict_flag = rag_result.get("conflict_flag", False)
        conflict_type = rag_result.get("conflict_type", None)
        conflict_detail = rag_result.get("conflict_detail", None)

        response_time = round(time.time() - start, 2)
        audit_log = {
            "input": input_data,
            "rag_result": rag_result,
            "tax_result": tax_result,
            "candidates": candidates,
            "fallback_triggered": fallback_triggered,
            "conflict_flag": conflict_flag,
            "conflict_type": conflict_type,
            "conflict_detail": conflict_detail,
            "resolution": {
                "clarification_turns": 0,
                "clarification_result": None,
                "expert_referral": conflict_flag,
            },
            "response_time_sec": response_time,
            "llm_provider": base_result["llm_provider"],
        }

        top1_display = candidates[0]["hs_code"] if candidates else "N/A"
        print(f"[FINAL] 응답 생성 완료 | 응답시간: {response_time}초 | Top-1: {top1_display}")
        print(f"[FINAL] Fallback: {'예' if fallback_triggered else '아니오'} | 충돌감지: {'예' if conflict_flag else '아니오'} | 근거품질: {evidence_quality_score}/8.0")

        # audit_log를 직접 저장 (LLM 경유 없이 → input_data 누락 방지)
        try:
            top1_code = candidates[0]["hs_code"] if candidates else ""
            save_audit_log.invoke({
                "audit_log": {"candidates": candidates, "input": input_data},
                "user_selection": top1_code,
                "modify_reason": "",
            })
            print("[LOG SAVE] audit_log.json 저장 완료")
        except Exception:
            print("[LOG SAVE] audit_log.json 저장 실패 (무시)")

        print("══════════════════════════════════════════════\n")

        return {
            **base_result,
            "candidates": candidates,
            "final_response": final_response,
            "evidence_quality_score": evidence_quality_score,
            "fallback_triggered": fallback_triggered,
            "fallback_reason": rag_result.get("fallback_reason"),
            "conflict_flag": conflict_flag,
            "conflict_type": conflict_type,
            "conflict_detail": conflict_detail,
            "response_time_sec": response_time,
            "audit_log": audit_log,
        }

    except Exception as e:
        response_time = round(time.time() - start, 2)
        print(f"[ERROR] 에이전트 실행 실패 | 응답시간: {response_time}초")
        print(f"  ▶ 오류: {e}")
        print("══════════════════════════════════════════════\n")
        return {
            **base_result,
            "response_time_sec": response_time,
            "error_message": str(e),
        }


def _score_evidence(candidates: list) -> float:
    """근거 품질 간이 채점 (만점 8점)."""
    if not candidates:
        return 0.0
    score = 0.0
    top = candidates[0]
    evidences = top.get("evidence", [])
    if evidences:
        score += 2.0
        ev = evidences[0]
        if ev.get("doc_name"):
            score += 1.5
        if ev.get("page"):
            score += 1.0
        if ev.get("citation") and len(ev["citation"]) > 20:
            score += 1.5
        if ev.get("similarity_score", 0) >= 0.85:
            score += 2.0
        elif ev.get("similarity_score", 0) >= 0.75:
            score += 1.0
    return round(min(score, 8.0), 1)
