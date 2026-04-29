"""PDF 문서를 로드 → 청킹 → 임베딩 → ChromaDB 적재하는 파이프라인."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pathlib import Path
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from configs.settings import settings


def run_ingest():
    raw_dir = Path(settings.CHROMA_DB_PATH).parent / "raw"
    pdf_files = list(raw_dir.glob("*.pdf"))

    print(f"[적재 시작] {raw_dir} 폴더에서 PDF 탐색 중...")

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

    print(f"[임베딩] HuggingFace {settings.EMBEDDING_MODEL} 모델 사용 중...")
    embeddings = HuggingFaceEmbeddings(model_name=settings.EMBEDDING_MODEL)

    db_path = settings.CHROMA_DB_PATH
    Path(db_path).mkdir(parents=True, exist_ok=True)

    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        collection_name=settings.CHROMA_COLLECTION_NAME,
        persist_directory=db_path,
    )
    print(f"[적재 완료] ChromaDB에 {len(chunks):,}개 청크 저장")

    test_query = "FOUP 웨이퍼 이송"
    print(f'[검증] 테스트 쿼리: "{test_query}"')
    results = vectorstore.similarity_search_with_score(test_query, k=3)
    for doc, score in results:
        source = doc.metadata.get("source", "알 수 없음")
        page = doc.metadata.get("page", "?")
        snippet = doc.page_content[:60].replace("\n", " ")
        print(f"  - 유사도 {score:.2f}: \"{snippet}...\" (p.{page}) [{Path(source).name}]")

    print("[완료] 문서 적재 파이프라인 정상 종료")


if __name__ == "__main__":
    run_ingest()
