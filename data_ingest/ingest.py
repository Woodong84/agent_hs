"""문서(PDF/TXT)를 로드 → 청킹 → 임베딩 → Pinecone 적재하는 파이프라인."""
import os
import sys

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _PROJECT_ROOT)

from pathlib import Path
from langchain.schema import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from configs.settings import settings


def _load_txt(path: Path) -> list:
    """TXT 파일 로드. '---' 구분자 사이를 메타데이터 헤더로 파싱."""
    text = path.read_text(encoding="utf-8")
    meta = {"source": path.name, "page": 1}

    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            header, content = parts[1], parts[2].strip()
            for line in header.strip().splitlines():
                if ":" in line:
                    key, val = line.split(":", 1)
                    meta[key.strip().lower()] = val.strip()
        else:
            content = text
    else:
        content = text

    return [Document(page_content=content, metadata=meta)]


def _load_pdf(path: Path) -> list:
    from langchain_community.document_loaders import PyPDFLoader
    loader = PyPDFLoader(str(path))
    return loader.load()


def run_ingest():
    raw_dir = Path(_PROJECT_ROOT) / "data" / "raw"
    print(f"[적재 시작] {raw_dir} 폴더에서 문서 탐색 중...")

    if not settings.use_pinecone:
        print("[오류] PINECONE_API_KEY 또는 PINECONE_INDEX_NAME이 설정되지 않았습니다.")
        return

    pdf_files = list(raw_dir.glob("*.pdf"))
    txt_files = [f for f in raw_dir.glob("*.txt") if f.name != ".gitkeep"]
    all_files = pdf_files + txt_files

    if not all_files:
        print("[경고] data/raw/ 폴더에 PDF/TXT 파일이 없습니다.")
        return

    all_docs = []
    for f in all_files:
        docs = _load_pdf(f) if f.suffix == ".pdf" else _load_txt(f)
        print(f"[발견] {f.name} ({len(docs)}페이지/섹션)")
        all_docs.extend(docs)

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.CHUNK_SIZE,
        chunk_overlap=settings.CHUNK_OVERLAP,
    )
    chunks = splitter.split_documents(all_docs)

    for i, chunk in enumerate(chunks):
        chunk.metadata["chunk_id"] = f"chunk_{i:04d}"

    print(f"[청킹] 총 {len(chunks):,}개 청크 생성")

    if settings.use_azure:
        from langchain_openai import AzureOpenAIEmbeddings
        print(f"[임베딩] Azure OpenAI {settings.AZURE_OPENAI_EMBEDDING_DEPLOYMENT} 사용 중...")
        embeddings = AzureOpenAIEmbeddings(
            azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
            azure_deployment=settings.AZURE_OPENAI_EMBEDDING_DEPLOYMENT,
            api_key=settings.AZURE_OPENAI_API_KEY,
            api_version=settings.AZURE_OPENAI_API_VERSION,
        )
    else:
        from langchain_huggingface import HuggingFaceEmbeddings
        print(f"[임베딩] HuggingFace {settings.EMBEDDING_MODEL} 사용 중...")
        embeddings = HuggingFaceEmbeddings(model_name=settings.EMBEDDING_MODEL)

    from pinecone import Pinecone
    from langchain_pinecone import PineconeVectorStore

    print(f"[Pinecone] 인덱스 '{settings.PINECONE_INDEX_NAME}'에 적재 중...")
    pc = Pinecone(api_key=settings.PINECONE_API_KEY)
    index = pc.Index(settings.PINECONE_INDEX_NAME)

    # langchain-pinecone 0.2.x 호환 방식: add_documents 사용
    vectorstore = PineconeVectorStore(index=index, embedding=embeddings)

    batch_size = 50
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]
        vectorstore.add_documents(batch)
        print(f"  → {min(i + batch_size, len(chunks))}/{len(chunks)} 청크 업로드 완료")

    print(f"[적재 완료] Pinecone에 {len(chunks):,}개 청크 저장")

    # 적재 후 벡터 수 확인
    stats = index.describe_index_stats()
    total_vectors = stats.get("total_vector_count", 0)
    print(f"[검증] Pinecone 총 벡터 수: {total_vectors}")

    test_query = "FOUP 웨이퍼 이송"
    print(f'[검증] 테스트 쿼리: "{test_query}"')
    results = vectorstore.similarity_search_with_score(test_query, k=3)
    for doc, score in results:
        source = doc.metadata.get("source", "알 수 없음")
        hs = doc.metadata.get("hs_code", "?")
        snippet = doc.page_content[:60].replace("\n", " ")
        print(f"  - 유사도 {score:.3f}: \"{snippet}...\" [HS:{hs}] [{source}]")

    print("[완료] Pinecone 적재 파이프라인 정상 종료")


if __name__ == "__main__":
    run_ingest()
