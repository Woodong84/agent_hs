# HSAgent — CLAUDE.md

> Andrej Karpathy 하네스 엔지니어링 원칙 적용:
> AI가 이 파일만 읽고도 코드를 안전하게 수정할 수 있도록,
> "무엇을 해도 되는지"보다 "무엇을 절대 바꾸지 말아야 하는지"를 먼저 명시한다.

---

## 1. 프로젝트 한 줄 요약

반도체 수출입 담당자를 위한 **HS-Code 자동 추천 AI 에이전트**.
Pinecone RAG + LangChain ReAct + Azure OpenAI(gpt-4.1)로 구동되며, Streamlit UI를 통해 서비스된다.

---

## 2. 아키텍처 개요

```
사용자 입력 (Streamlit UI)
        │
        ▼
agents/orchestrator.py  ← run_agent() 진입점
        │
        ├─► tools/search_hs.py       search_hs_code_rag()
        │         └─ Pinecone (cosine, 1536dim)
        │               └─ Azure OpenAI text-embedding-3-small
        │
        ├─► tools/query_tax.py       query_tax_rate()
        │         └─ 정적 세율 테이블 (UNI-PASS API fallback)
        │
        └─► tools/audit_log.py       save_audit_log()  ← orchestrator 직접 호출 (LLM 경유 X)
                  └─ logs/audit_log.json (JSONL 누적)
```

**LLM 우선순위:** Azure OpenAI gpt-4.1 → (미설정 시) Claude Sonnet 4.5  
**벡터 DB:** Pinecone Serverless, 인덱스명 `hs-code-docs`, 현재 242벡터 적재

---

## 3. 절대 불변 규칙 (AI가 임의로 바꾸면 안 되는 것)

```
INVARIANT-01  save_audit_log는 _TOOLS 목록에 넣지 않는다.
              반드시 run_agent() 내부에서 직접 invoke()로 호출해야 한다.
              (LLM 경유 시 input 필드가 빈 {} 로 저장되는 버그 재발)

INVARIANT-02  search_hs_code_rag의 similarity_threshold 기본값은 0.30 이하로 내리지 않는다.
              UI 슬라이더 기본값은 0.45. 이 값이 낮아지면 도메인 외 품목 오매칭 발생.

INVARIANT-03  Pinecone 인덱스 차원은 1536, 메트릭은 cosine.
              인덱스를 재생성할 경우 반드시 이 두 값을 유지해야 한다.

INVARIANT-04  _score_to_confidence() 기준: 높음≥0.60 / 중간≥0.45 / 낮음<0.45.
              Pinecone 코사인 유사도의 실측 범위(0.37~0.55)에 맞춰진 값이므로 0.75 이상으로 올리지 않는다.

INVARIANT-05  LangGraph(agents/rag_agent.py, agents/tax_agent.py)는 현재 미사용 스텁이다.
              ReAct(orchestrator.py)가 유일한 실행 경로이며, LangGraph를 활성화하려면
              별도 브랜치에서 전체 흐름을 재설계해야 한다.

INVARIANT-06  Render 배포는 Python 3.11로 고정(runtime.txt).
              Python 3.13으로 올리면 numpy 버전 충돌로 빌드 실패.

INVARIANT-07  면책 문구("본 결과는 참고용이며 최종 확정은 담당자·관세사 검토 필수")는
              모든 추천 응답 마지막에 반드시 포함되어야 한다. 프롬프트에서 삭제 금지.
```

---

## 4. 핵심 파일 지도

| 파일 | 역할 | 수정 시 주의사항 |
|------|------|----------------|
| `agents/orchestrator.py` | ReAct 에이전트 빌드 + run_agent() | INVARIANT-01 준수 필수 |
| `tools/search_hs.py` | Pinecone RAG 검색 + 충돌 감지 | INVARIANT-02/04 준수 필수 |
| `tools/query_tax.py` | 관세율 조회 (정적 테이블 / UNI-PASS API) | 세율 테이블 변경 시 류 코드 2자리 키로 관리 |
| `tools/audit_log.py` | 감사 로그 저장 (JSONL) | Top-1 외 선택 시 수정 사유 필수 로직 유지 |
| `configs/settings.py` | Pydantic-Settings 환경변수 | .env에 없는 키 추가 시 여기도 선언 필요 |
| `configs/prompts.py` | 시스템 프롬프트 + Fallback 메시지 | INVARIANT-07 준수, 면책 문구 삭제 금지 |
| `data_ingest/ingest.py` | 문서 적재 파이프라인 | batch_size=50 유지 (Pinecone 무료 플랜 rate limit) |
| `app.py` | Streamlit UI 메인 | 슬라이더 기본값 0.45 (INVARIANT-02) |

**사용하지 않는 파일 (건드리지 말 것):**
- `agents/state.py` — LangGraph AgentState 스텁 (미사용)
- `agents/rag_agent.py`, `agents/tax_agent.py` — LangGraph 노드 스텁 (미사용)

---

## 5. 환경 설정 (재현 절차)

```bash
# 1. Python 버전 확인
python --version  # 반드시 3.11.x

# 2. 의존성 설치
pip install -r requirements.txt

# 3. 환경변수 설정 (.env.example 복사 후 키 입력)
cp .env.example .env
# → AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT, PINECONE_API_KEY 필수 입력

# 4. Pinecone 문서 적재 (최초 1회 또는 문서 추가 시)
python data_ingest/ingest.py
# 정상 완료 로그: "[완료] Pinecone 적재 파이프라인 정상 종료"
# 검증: Pinecone 총 벡터 수 출력 확인 (현재 기준 242개)

# 5. Streamlit 실행
streamlit run app.py
# → http://localhost:8501
```

---

## 6. 개발 브랜치 규칙

```
main                  ← Render 배포 브랜치 (직접 push 금지)
claude/show-selected-repo-lYEUY  ← 현재 개발 브랜치
```

커밋 후 항상 아래 명령으로 push:
```bash
git push -u origin claude/show-selected-repo-lYEUY
```

---

## 7. 알려진 버그 및 해결 이력

| 버그 | 원인 | 해결 방법 | 상태 |
|------|------|---------|------|
| 항상 Fallback 발생 | similarity_threshold가 LLM에 전달 안 됨 | `_format_question()`에 threshold 포함 | 해결 |
| 신뢰도 항상 "낮음" | 기준값 0.85/0.75이 Pinecone 실측값(0.4~0.5) 대비 너무 높음 | 기준 0.60/0.45로 하향 | 해결 |
| audit_log input 빈 {} | LLM이 audit_log 구성 시 input_data 미참조 | save_audit_log를 _TOOLS에서 제거, 직접 호출 | 해결 |
| 충돌 감지 후 UI 미표시 | orchestrator 반환값에 conflict 필드 누락 | base_result + 반환 dict에 conflict 3필드 추가 | 해결 |
| Pinecone dimension mismatch | 인덱스를 512dim으로 생성했으나 임베딩은 1536dim | 인덱스 삭제 후 1536dim으로 재생성 | 해결 |
| Render 빌드 실패 | Python 3.13 + numpy 충돌 | runtime.txt에 python-3.11 고정 | 해결 |
| 도메인 외 품목 오매칭 | 임계값 0.30으로 무관한 문서도 통과 | UI 슬라이더 기본값 0.45로 상향 | 부분 해결 |

---

## 8. 현재 한계 (E2E 단계에서 해결 예정)

- **참조 문서 11개(242벡터)**: HS 4~6자리 정밀 분류 불가 → PDF 규정집 추가 적재 필요
- **Clarification 흐름 미구현**: 충돌 시 배너만 표시, 에이전트의 추가 질문 생성 없음
- **UNI-PASS API 미연동**: 정적 세율 테이블 6개 류만 커버, 실시간 관세율 조회 불가
- **응답 시간 7~15초**: LLM API 왕복 지연, 스트리밍 응답 미적용

---

## 9. 자주 쓰는 테스트 입력

**정상 추천 (FOUP):**
```
품목명: FOUP
재질:   폴리카보네이트
용도:   300mm 웨이퍼 클린룸 이송
수출입: 수입
유사도 임계값: 0.30
→ 기대: Top-1=3923100000, 근거품질≥5.0, Fallback=아니오
```

**Fallback 전환 (양자컴퓨터 희석냉동기):**
```
품목명: 양자컴퓨터 희석냉동기
재질:   알루미늄, 구리
용도:   큐비트 냉각용 극저온 장치
수출입: 수출
유사도 임계값: 0.45
→ 기대: Fallback=예, 근거품질=0.0, 경고 배너 표시
```

**충돌 감지 (포토마스크):**
```
품목명: 포토마스크
재질:   합성 석영
용도:   EUV 리소그래피용
수출입: 수입
→ 기대: conflict_flag=True, TYPE-1 주황 배너 표시
```

---

## 10. Render 배포 시 필수 환경변수

Render 대시보드 → Environment 탭에서 아래 키 설정 필요:

```
AZURE_OPENAI_API_KEY
AZURE_OPENAI_ENDPOINT
AZURE_OPENAI_DEPLOYMENT        = gpt-4.1
AZURE_OPENAI_EMBEDDING_DEPLOYMENT = text-embedding-3-small
AZURE_OPENAI_API_VERSION       = 2024-12-01-preview
PINECONE_API_KEY
PINECONE_INDEX_NAME            = hs-code-docs
PYTHON_VERSION                 = 3.11.0
```

Start Command: `streamlit run app.py --server.port $PORT --server.address 0.0.0.0`
