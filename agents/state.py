from typing import TypedDict, Optional, List


class AgentState(TypedDict):
    # 입력 필드 (★1차 PoC 필수)
    user_input: str
    product_name: str
    material: str
    purpose: str
    trade_direction: str              # "수출" 또는 "수입"
    existing_hs_code: Optional[str]
    optional_fields: dict

    # RAG 검색 결과 (★1차 PoC 필수)
    rag_top5_chunks: List[dict]
    max_similarity: float
    candidates: List[dict]

    # 상충 판정
    conflict_flag: bool
    conflict_type: Optional[str]      # "TYPE-1" / "TYPE-2" / "TYPE-3"
    conflict_detail: Optional[str]

    # Clarification
    clarification_count: int
    clarification_questions: list
    clarification_answers: list

    # 세율 조회
    tax_info: Optional[dict]
    tax_fallback: bool

    # 최종 출력 (★1차 PoC 필수)
    fallback_triggered: bool
    fallback_reason: Optional[str]
    final_response: str
    evidence_quality_score: float
    response_time_sec: float
    audit_log: dict
    error_message: Optional[str]


def create_initial_state(user_input: str) -> AgentState:
    """새 조회 시작 시 초기 State 생성"""
    return AgentState(
        user_input=user_input,
        product_name="", material="", purpose="",
        trade_direction="", existing_hs_code=None,
        optional_fields={},
        rag_top5_chunks=[], max_similarity=0.0, candidates=[],
        conflict_flag=False, conflict_type=None, conflict_detail=None,
        clarification_count=0, clarification_questions=[], clarification_answers=[],
        tax_info=None, tax_fallback=False,
        fallback_triggered=False, fallback_reason=None,
        final_response="", evidence_quality_score=0.0,
        response_time_sec=0.0, audit_log={}, error_message=None
    )
