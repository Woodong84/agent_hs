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

    try:
        executor = _build_agent_executor()
        question = _format_question(input_data)
        result = executor.invoke({"input": question})

        final_response = result.get("output", "")
        intermediate = result.get("intermediate_steps", [])

        rag_result: dict = {}
        tax_result: dict = {}
        for action, observation in intermediate:
            tool_name = getattr(action, "tool", "")
            parsed = _parse_observation(observation)
            if tool_name == "search_hs_code_rag" and parsed:
                rag_result = parsed
            elif tool_name == "query_tax_rate" and parsed:
                tax_result = parsed

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
            "response_time_sec": response_time,
            "llm_provider": base_result["llm_provider"],
        }

        # audit_log를 직접 저장 (LLM 경유 없이 → input_data 누락 방지)
        try:
            top1_code = candidates[0]["hs_code"] if candidates else ""
            save_audit_log.invoke({
                "audit_log": {"candidates": candidates, "input": input_data},
                "user_selection": top1_code,
                "modify_reason": "",
            })
        except Exception:
            pass

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
        return {
            **base_result,
            "response_time_sec": round(time.time() - start, 2),
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
