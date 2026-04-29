# HSAgent — 반도체 수출입 HS-Code 추천 AI Agent

반도체 부품·소재·장비의 수출입 HS-Code 분류를 지원하는 AI Agent입니다.
RAG(검색 증강 생성) 기반으로 관세청 공식 문서를 근거로 Top-3 후보 코드와 출처를 함께 제공합니다.
건당 60분 → 10초 이내 처리를 목표로 합니다.

---

## 기술 스택

| 구분 | 기술 |
|------|------|
| LLM | Claude (Anthropic) — `claude-sonnet-4-5-20251001` |
| Agent 프레임워크 | LangChain ReAct → LangGraph (2차) |
| 임베딩 | HuggingFace `paraphrase-multilingual-MiniLM-L12-v2` (무료, 로컬) |
| Vector DB | ChromaDB (로컬 영속 저장) |
| 문서 파싱 | PyPDF |
| 설정 관리 | pydantic-settings |
| UI (2차) | Streamlit |

---

## 빠른 시작 (Quick Start)

### 1. 저장소 클론

```bash
git clone <repo-url>
cd agent_hs
```

### 2. 가상환경 생성 및 활성화

```bash
python -m venv venv
# macOS/Linux
source venv/bin/activate
# Windows
venv\Scripts\activate
```

### 3. 의존성 설치

```bash
pip install -r requirements.txt
```

### 4. 환경변수 설정

```bash
cp .env.example .env
```

`.env` 파일을 열고 아래 항목을 입력합니다.

```
ANTHROPIC_API_KEY=sk-ant-...   # 필수
UNIPASS_API_KEY=               # 선택 (미설정 시 정적 세율표 사용)
```

### 5. 문서 적재 (RAG 데이터 준비)

`data/raw/` 폴더에 관세청 품목분류 사례집 등 PDF를 넣은 후 실행합니다.

```bash
python data_ingest/ingest.py
```

### 6. Agent 실행

```bash
python main.py
```

### 7. 평가 실행

```bash
python eval/eval_runner.py
```

### 8. 회귀 비교

```bash
python eval/compare_results.py
```

---

## 디렉토리 구조

```
agent_hs/
├── agents/          Agent 로직 (orchestrator, state, rag_agent, tax_agent)
├── tools/           LangChain Tool 함수 (RAG 검색, 세율 조회, 감사 로그)
├── data_ingest/     PDF 적재 파이프라인 (로더, 청커, 임베딩)
├── eval/            평가 스크립트 및 정답셋
├── configs/         설정 및 프롬프트 템플릿
├── data/raw/        원본 PDF (git 제외)
├── data/chroma_db/  ChromaDB 벡터 저장소 (git 제외)
├── logs/            감사 로그 (git 제외)
├── main.py          CLI 진입점
└── app.py           Streamlit UI (2차 구현)
```

---

## PoC 합격 기준 (KPI)

| 지표 | 목표 |
|------|------|
| Top-3 Hit Rate | ≥ 70% |
| 근거 품질 합격률 | ≥ 75% |
| 평균 응답시간 | ≤ 10초 |
| 엣지 케이스 Fallback | ≥ 80% |

---

## 주의사항

- **API 키 보안**: `.env` 파일은 절대 git에 커밋하지 마세요. `.gitignore`에 포함되어 있습니다.
- **문서 저작권**: WCO HS 해설서는 저작권이 있습니다. 공개 배포 전 사용 권한을 확인하세요.
- **면책 고지**: 이 시스템의 추천 결과는 참고용이며, 최종 HS-Code 확정은 반드시 담당자 또는 관세사의 검토가 필요합니다.
- **UNI-PASS API**: 관세청 UNI-PASS 연동은 별도 API 키 신청이 필요합니다. 미설정 시 정적 세율표로 동작합니다.
