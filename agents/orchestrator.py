"""1차 PoC LangChain ReAct 단일 Orchestrator Agent."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
from langchain_anthropic import ChatAnthropic
from langchain.agents import AgentExecutor, create_react_agent
from langchain.prompts import PromptTemplate
from configs.settings import settings
from configs.prompts import ORCHESTRATOR_SYSTEM_PROMPT, FALLBACK_PROMPT
from tools.search_hs import search_hs_code_rag
from tools.query_tax import query_tax_rate
from tools.audit_log import save_audit_log

_TOOLS = [search_hs_code_rag, query_tax_rate, save_audit_log]

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
Action Input: 도구 입력값 (JSON)
Observation: 도구 결과
... (Thought/Action/Observation 반복)
Thought: 최종 답변을 작성합니다
Final Answer: 최종 출력

Question: {input}
{agent_scratchpad}"""
)


def _build_agent_executor() -> AgentExecutor:
    llm = ChatAnthropic(
        model=settings.ANTHROPIC_MODEL,
        api_key=settings.ANTHROPIC_API_KEY,
        max_tokens=4096,
    )
    prompt = PromptTemplate.from_template(_REACT_TEMPLATE)
    agent = create_react_agent(llm=llm, tools=_TOOLS, prompt=prompt)
    return AgentExecutor(
        agent=agent,
        tools=_TOOLS,
        max_iterations=5,
        verbose=True,
        handle_parsing_errors=True,
        return_intermediate_steps=True,
    )


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
        "response_time_sec": 0.0,
        "audit_log": {},
        "error_message": None,
    }

    try:
        executor = _build_agent_executor()
        question = _format_question(input_data)
        result = executor.invoke({"input": question})

        final_response = result.get("output", "")
        intermediate = result.get("intermediate_steps", [])

        rag_result = {}
        tax_result = {}
        for action, observation in intermediate:
            tool_name = getattr(action, "tool", "")
            if tool_name == "search_hs_code_rag" and isinstance(observation, dict):
                rag_result = observation
            elif tool_name == "query_tax_rate" and isinstance(observation, dict):
                tax_result = observation

        fallback_triggered = rag_result.get("fallback", False)
        if fallback_triggered:
            similar_class = input_data.get("product_name", "해당 품목")[:10]
            final_response = FALLBACK_PROMPT.format(
                similarity_score=round(rag_result.get("max_similarity", 0.0), 2),
                similar_class=similar_class,
                similar_class_desc="참고용 분류",
            )

        candidates = rag_result.get("candidates", [])
        evidence_quality_score = _score_evidence(candidates)

        audit_log = {
            "input": input_data,
            "rag_result": rag_result,
            "tax_result": tax_result,
            "candidates": candidates,
            "fallback_triggered": fallback_triggered,
            "response_time_sec": round(time.time() - start, 2),
        }

        return {
            **base_result,
            "candidates": candidates,
            "final_response": final_response,
            "evidence_quality_score": evidence_quality_score,
            "fallback_triggered": fallback_triggered,
            "fallback_reason": rag_result.get("fallback_reason"),
            "response_time_sec": round(time.time() - start, 2),
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
