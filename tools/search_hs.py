"""ChromaDB RAG 검색 + HS-Code 후보 생성 + conflict 판정.
Azure OpenAI 설정 시 AzureOpenAIEmbeddings 사용, 없으면 HuggingFace Fallback.
"""
import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pathlib import Path
from langchain.tools import tool
from langchain_chroma import Chroma
from configs.settings import settings

# 모델과 벡터스토어를 모듈 레벨에서 캐싱 (매 호출마다 재로드 방지)
_embeddings = None
_vectorstore: Chroma | None = None

# Cosine distance 컬렉션 메타데이터
_COLLECTION_METADATA = {"hnsw:space": "cosine"}


def _get_embeddings():
    """Azure OpenAI 설정 시 AzureOpenAIEmbeddings, 없으면 HuggingFaceEmbeddings."""
    global _embeddings
    if _embeddings is not None:
        return _embeddings
    if settings.use_azure:
        from langchain_openai import AzureOpenAIEmbeddings
        _embeddings = AzureOpenAIEmbeddings(
            azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
            azure_deployment=settings.AZURE_OPENAI_EMBEDDING_DEPLOYMENT,
            api_key=settings.AZURE_OPENAI_API_KEY,
            api_version=settings.AZURE_OPENAI_API_VERSION,
        )
    else:
        from langchain_huggingface import HuggingFaceEmbeddings
        _embeddings = HuggingFaceEmbeddings(model_name=settings.EMBEDDING_MODEL)
    return _embeddings


def _get_vectorstore() -> Chroma:
    global _vectorstore
    if _vectorstore is None:
        _vectorstore = Chroma(
            collection_name=settings.CHROMA_COLLECTION_NAME,
            embedding_function=_get_embeddings(),
            persist_directory=settings.CHROMA_DB_PATH,
            collection_metadata=_COLLECTION_METADATA,
        )
    return _vectorstore


def _score_to_confidence(score: float) -> str:
    if score >= 0.85:
        return "높음"
    if score >= 0.75:
        return "중간"
    return "낮음"


def _detect_conflict(candidates: list, existing_hs_code: str, top5_chunks: list) -> tuple:
    """(conflict_flag, conflict_type, conflict_detail) 반환"""
    top3_codes = [c["hs_code"] for c in candidates[:3]]

    # TYPE-2: 기존 코드와 1순위 코드가 6단위 불일치 (후보 1개여도 검사)
    if top3_codes and existing_hs_code and len(existing_hs_code) >= 6 and len(top3_codes[0]) >= 6:
        if existing_hs_code[:6] != top3_codes[0][:6]:
            return True, "TYPE-2", f"기존코드 {existing_hs_code[:6]} ↔ 추천코드 {top3_codes[0][:6]}"

    # TYPE-1·3은 후보가 2개 이상일 때만 의미 있음
    if len(candidates) < 2:
        return False, None, None

    top3_classes = [code[:2] for code in top3_codes if len(code) >= 2]

    # TYPE-1: 상위 3개 코드 중 2개 이상이 서로 다른 2단위(류)
    if len(set(top3_classes)) >= 2:
        return True, "TYPE-1", f"류 충돌: {', '.join(sorted(set(top3_classes)))}"

    # TYPE-3: 상위 5청크 중 서로 다른 코드를 각 2개 이상 지지
    chunk_codes = [
        c.get("supports_hs", "")[:4]
        for c in top5_chunks
        if c.get("supports_hs", "")
    ]
    code_counts: dict = {}
    for code in chunk_codes:
        code_counts[code] = code_counts.get(code, 0) + 1
    competing = [c for c, n in code_counts.items() if n >= 2]
    if len(competing) >= 2:
        return True, "TYPE-3", f"복수 코드 병렬 지지: {', '.join(competing)}"

    return False, None, None


@tool
def search_hs_code_rag(
    product_name: str,
    material: str,
    purpose: str,
    trade_direction: str,
    existing_hs_code: str = "",
    top_k: int = 5,
    similarity_threshold: float = 0.75,
) -> dict:
    """ChromaDB에서 유사 문서를 검색하고 HS-Code 후보와 근거를 반환한다."""
    # LLM이 전체 입력을 product_name 하나에 JSON 문자열로 넣는 경우 방어 처리
    try:
        if isinstance(product_name, str) and product_name.strip().startswith("{"):
            parsed = json.loads(product_name)
            if isinstance(parsed, dict):
                product_name = parsed.get("product_name", product_name)
                material = parsed.get("material", material)
                purpose = parsed.get("purpose", purpose)
                trade_direction = parsed.get("trade_direction", trade_direction)
                existing_hs_code = parsed.get("existing_hs_code", existing_hs_code)
                similarity_threshold = float(parsed.get("similarity_threshold", similarity_threshold))
    except (json.JSONDecodeError, AttributeError, TypeError, ValueError):
        pass

    query = f"{product_name} {material} {purpose} {trade_direction}"

    try:
        vectorstore = _get_vectorstore()
    except Exception as e:
        return {
            "candidates": [], "conflict_flag": False, "conflict_type": None,
            "conflict_detail": None, "fallback": True,
            "fallback_reason": f"ChromaDB 로드 실패: {e}",
            "max_similarity": 0.0, "top5_chunks": [],
        }

    # relevance_score는 cosine similarity 기반 [0, 1] 값 (높을수록 유사)
    try:
        results = vectorstore.similarity_search_with_relevance_scores(query, k=top_k)
    except Exception as e:
        return {
            "candidates": [], "conflict_flag": False, "conflict_type": None,
            "conflict_detail": None, "fallback": True,
            "fallback_reason": f"RAG 검색 실패: {e}",
            "max_similarity": 0.0, "top5_chunks": [],
        }

    if not results:
        return {
            "candidates": [], "conflict_flag": False, "conflict_type": None,
            "conflict_detail": None, "fallback": True,
            "fallback_reason": "검색 결과 없음",
            "max_similarity": 0.0, "top5_chunks": [],
        }

    max_similarity = max(score for _, score in results)

    if max_similarity < similarity_threshold:
        return {
            "candidates": [], "conflict_flag": False, "conflict_type": None,
            "conflict_detail": None, "fallback": True,
            "fallback_reason": f"유사도 {max_similarity:.2f} < 임계값 {similarity_threshold}",
            "max_similarity": round(max_similarity, 4), "top5_chunks": [],
        }

    top5_chunks = []
    candidates = []
    seen_codes: dict = {}

    for idx, (doc, sim) in enumerate(results):
        meta = doc.metadata
        source = Path(meta.get("source", "알 수 없는 문서")).name
        page = meta.get("page", "?")
        hs_code = meta.get("hs_code", f"UNKNOWN_{idx:03d}")
        chunk_id = meta.get("chunk_id", f"chunk_{idx:03d}")

        chunk_info = {
            "chunk_id": chunk_id,
            "supports_hs": hs_code,
            "similarity_score": round(sim, 4),
            "snippet": doc.page_content[:100],
        }
        top5_chunks.append(chunk_info)

        evidence = {
            "evidence_id": f"ev_{idx+1:03d}",
            "doc_name": source,
            "pub_year": meta.get("pub_year", ""),
            "page": f"p.{page}",
            "section": meta.get("section", ""),
            "citation": doc.page_content[:120].replace("\n", " "),
            "similarity_score": round(sim, 4),
            "chunk_id": chunk_id,
            "supports_hs": hs_code,
        }

        if hs_code not in seen_codes:
            seen_codes[hs_code] = len(candidates)
            candidates.append({
                "rank": len(candidates) + 1,
                "hs_code": hs_code,
                "confidence": _score_to_confidence(sim),
                "evidence": [evidence],
            })
        else:
            candidates[seen_codes[hs_code]]["evidence"].append(evidence)

    conflict_flag, conflict_type, conflict_detail = _detect_conflict(
        candidates, existing_hs_code, top5_chunks
    )

    return {
        "candidates": candidates[:3],
        "conflict_flag": conflict_flag,
        "conflict_type": conflict_type,
        "conflict_detail": conflict_detail,
        "fallback": False,
        "fallback_reason": None,
        "max_similarity": round(max_similarity, 4),
        "top5_chunks": top5_chunks,
    }
