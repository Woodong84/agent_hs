"""PDF 문서를 로드 → 청킹 → 임베딩 → ChromaDB 적재하는 파이프라인."""
import os
import sys

# 프로젝트 루트를 절대경로로 추가
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _PROJECT_ROOT)

from pathlib import Path
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from configs.settings import settings

# search_hs.py와 동일한 cosine distance 메타데이터 사용
_COLLECTION_METADATA = {"hnsw:space": "cosine"}


def run_ingest():
    # 경로를 CWD가 아닌 프로젝트 루트 기준으로 해석
    chroma_path = Path(_PROJECT_ROOT) / settings.CHROMA_DB_PATH.lstrip("./")
    raw_dir = chroma_path.parent / "raw"

    print(f"[적재 시작] {raw_dir} 폴더에서 PDF 탐색 중...")

    pdf_files = list(raw_dir.glob("*.pdf"))
    if not pdf_files:
        print("[경고] data/raw/ 폴더에 PDF 파일이 없습니다. 적재할 문서를 추가해주세요.")
        return

    all_docs = []
    for pdf_path in pdf_files:
        loader = PyPDFLoader(str(pdf_path))
        docs = loader.load()
        print(f"[발견] {pdf_path.name} ({len(docs)}페이지)")
        all_docs.extend(docs)

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.CHUNK_SIZE,
        chunk_overlap=settings.CHUNK_OVERLAP,
    )
    chunks = splitter.split_documents(all_docs)
    print(f"[청킹] 총 {len(chunks):,}개 청크 생성")

    if settings.use_azure:
        from langchain_openai import AzureOpenAIEmbeddings
        print(f"[임베딩] Azure OpenAI {settings.AZURE_OPENAI_EMBEDDING_DEPLOYMENT} 모델 사용 중...")
        embeddings = AzureOpenAIEmbeddings(
            azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
            azure_deployment=settings.AZURE_OPENAI_EMBEDDING_DEPLOYMENT,
            api_key=settings.AZURE_OPENAI_API_KEY,
            api_version=settings.AZURE_OPENAI_API_VERSION,
        )
    else:
        from langchain_huggingface import HuggingFaceEmbeddings
        print(f"[임베딩] HuggingFace {settings.EMBEDDING_MODEL} 모델 사용 중...")
        embeddings = HuggingFaceEmbeddings(model_name=settings.EMBEDDING_MODEL)

    chroma_path.mkdir(parents=True, exist_ok=True)

    # cosine distance 컬렉션으로 생성 (search_hs.py와 일치)
    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        collection_name=settings.CHROMA_COLLECTION_NAME,
        persist_directory=str(chroma_path),
        collection_metadata=_COLLECTION_METADATA,
    )
    print(f"[적재 완료] ChromaDB에 {len(chunks):,}개 청크 저장")

    test_query = "FOUP 웨이퍼 이송"
    print(f'[검증] 테스트 쿼리: "{test_query}"')
    results = vectorstore.similarity_search_with_relevance_scores(test_query, k=3)
    for doc, score in results:
        source = doc.metadata.get("source", "알 수 없음")
        page = doc.metadata.get("page", "?")
        snippet = doc.page_content[:60].replace("\n", " ")
        print(f"  - 유사도 {score:.2f}: \"{snippet}...\" (p.{page}) [{Path(source).name}]")

    print("[완료] 문서 적재 파이프라인 정상 종료")


if __name__ == "__main__":
    run_ingest()
