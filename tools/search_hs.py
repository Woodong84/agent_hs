"""ChromaDB RAG 검색 + HS-Code 후보 생성 + conflict 판정."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pathlib import Path
from langchain.tools import tool
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from configs.settings import settings


def _get_vectorstore() -> Chroma:
    embeddings = HuggingFaceEmbeddings(model_name=settings.EMBEDDING_MODEL)
    return Chroma(
        collection_name=settings.CHROMA_COLLECTION_NAME,
        embedding_function=embeddings,
        persist_directory=settings.CHROMA_DB_PATH,
    )


def _score_to_confidence(score: float) -> str:
    if score >= 0.85:
        return "높음"
    if score >= 0.75:
        return "중간"
    return "낮음"


def _detect_conflict(candidates: list, existing_hs_code: str, top5_chunks: list) -> tuple:
    """(conflict_flag, conflict_type, conflict_detail) 반환"""
    if len(candidates) < 2:
        return False, None, None

    top3_codes = [c["hs_code"] for c in candidates[:3]]
    top3_classes = [code[:2] for code in top3_codes if len(code) >= 2]

    # TYPE-1: 상위 3개 코드 중 2개 이상이 서로 다른 2단위(류)
    if len(set(top3_classes)) >= 2:
        return True, "TYPE-1", f"류 충돌: {', '.join(set(top3_classes))}"

    # TYPE-2: 기존 코드와 1순위 코드가 6단위 불일치
    if existing_hs_code and len(existing_hs_code) >= 6 and len(top3_codes[0]) >= 6:
        if existing_hs_code[:6] != top3_codes[0][:6]:
            return True, "TYPE-2", f"기존코드 {existing_hs_code[:6]} ↔ 추천코드 {top3_codes[0][:6]}"

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

    results = vectorstore.similarity_search_with_score(query, k=top_k)

    if not results:
        return {
            "candidates": [], "conflict_flag": False, "conflict_type": None,
            "conflict_detail": None, "fallback": True,
            "fallback_reason": "검색 결과 없음",
            "max_similarity": 0.0, "top5_chunks": [],
        }

    # ChromaDB 거리 점수(낮을수록 유사) → 유사도(높을수록 유사)로 변환
    max_raw = max(score for _, score in results)
    processed = []
    for doc, raw_score in results:
        sim = 1.0 - (raw_score / (max_raw + 1e-9)) if max_raw > 0 else 0.0
        processed.append((doc, sim))

    max_similarity = max(sim for _, sim in processed)

    if max_similarity < similarity_threshold:
        return {
            "candidates": [], "conflict_flag": False, "conflict_type": None,
            "conflict_detail": None, "fallback": True,
            "fallback_reason": f"유사도 {max_similarity:.2f} < 임계값 {similarity_threshold}",
            "max_similarity": max_similarity, "top5_chunks": [],
        }

    top5_chunks = []
    candidates = []
    seen_codes: dict = {}

    for idx, (doc, sim) in enumerate(processed):
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
