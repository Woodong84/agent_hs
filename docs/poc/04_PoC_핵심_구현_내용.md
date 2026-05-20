### 핵심 구현 내용

이번 PoC 단계에서 실제 코드로 구현된 핵심 기능들을 **동작 원리**와 **사용 기술** 중심으로 상세히 기술합니다.

**1.1 에이전트 워크플로우 (Agent Workflow)**

* **구현 기능:** [예: 사용자 의도 분류 및 라우팅]\
  반도체 품목 정보를 입력받아 HS-Code를 자동 추천하는 ReAct 오케스트레이터 에이전트

* **동작 원리:** [예: 사용자의 질문이 '검색'인지 '계산'인지 판단하여, 검색용 에이전트 또는 계산용 도구로 분기 처리]\
  사용자가 품목명·재질·용도·수출입 방향을 입력하면 에이전트가 다음 순서로 처리합니다.\
  (1) 입력값을 구조화된 질문으로 변환 후 에이전트에 전달\
  (2) ReAct(Reasoning + Acting) 루프에서 어떤 도구를 어떤 순서로 호출할지 자율 판단\
  (3) search_hs_code_rag → query_tax_rate 순으로 도구 호출\
  (4) RAG 검색 결과가 임계값 미만이면 LLM 지식 기반 Fallback으로 자동 전환\
  (5) 최종 HS-Code 추천 + 세율 정보를 통합하여 사용자에게 반환

* **주요 기술:** [예: LangGraph StateNode, GPT-4o-mini, System Prompting]\
  (1) LangChain\
  - create_react_agent : LLM이 **ReAct (Reasoning and Acting)**, 즉 '추론'과 '행동'을 결합하여 문제를 해결하도록 설정된 에이전트 객체를 생성하는 함수\
  - AgentExecutor : create_react_agent로 만든 에이전트 두뇌와 실제 실행할 도구들을 결합하여 구동시키는 런타임 환경\
  (2) LLM\
  - Azure OpenAI gpt-4.1 (메인) : 에이전트의 주력 두뇌로 사용\
  - Fallback Claude Sonnet 4.5 (대체) : 메인 모델 예외 경우 발생 시, 즉각적으로 요청을 이어받아 처리하는 백업 모델\
  (3) PromptTemplate (ReAct 형식)\
  - LLM이 환각(Hallucination)에 빠지지 않고, 정해진 도구를 논리적인 순서대로 사용하도록 통제하는 가이드라인\
  (4) Pydantic-Settings 기반 환경 설정\
  - DB 접속 정보, API 키, 모델 버전, 유사도 임계값 등 시스템 구동에 필요한 환경 변수들을 Pydantic 라이브러리를 통해 관리

**1.2 도구(Tool) 및 함수 연동**

* **구현 기능:** [예: 사내 API를 통한 재고 조회]\
  (1) HS-Code RAG 검색 도구 (search_hs_code_rag)\
  (2) 관세율 조회 도구 (query_tax_rate)

* **동작 원리:** [예: LLM이 추출한 상품명(Entity)을 Pydantic 모델로 검증 후 REST API 호출]\
  (1) HS-Code RAG 검색 도구 (search_hs_code_rag)\
  - LLM이 품목명·재질·용도를 JSON 형태의 Action Input으로 도구에 전달\
  - 입력값을 단일 쿼리 문자열로 결합 후 Pinecone에서 코사인 유사도 검색 (top-k=5)\
  - 유사도 최댓값이 임계값(기본 0.30) 이상인 경우에만 후보 HS-Code와 근거 문서 반환\
  - 동일 HS-Code를 지지하는 청크가 여러 개인 경우 합산하여 신뢰도 산정\
  - 상위 3개 류(類) 코드가 서로 다를 경우 충돌 플래그(TYPE-1/2/3) 자동 생성\
  (2) 관세율 조회 도구 (query_tax_rate)\
  - HS-Code 앞 4자리(류·호)를 키로 정적 세율 테이블에서 기본관세율 조회\
  - 한-미·한-EU·한-중 FTA 협정 세율 및 수입 요건 반환\
  - 실제 운영 시 관세청 UNI-PASS API 연동으로 대체 가능한 구조로 설계

* **주요 기술:** [예: Python requests, Pydantic, Custom Tool Definition]\
  (1) LangChain @tool 데코레이터\
  - 파이썬으로 작성한 일반적인 Function을 LLM 에이전트가 인식하고 사용할 수 있는 '도구(Tool)'로 변환 처리\
  (2) Pydantic 자동 스키마 생성\
  - 데이터의 형태를 엄격하게 정의하고 검증하는 파이썬 라이브러리인 Pydantic을 활용하여, LLM이 내뱉는 결과물의 포맷을 강제 적용\
  (3) JSON 방어적 파싱 (LLM 오형식 대응)\
  - LLM이 전체 입력을 product_name 단일 필드에 JSON 문자열로 직렬화하는 오형식 발생 시, 자동 파싱하여 각 필드로 분해하는 방어 로직 내장\
  (4) 관세율 Fallback 정적 테이블\
  - 관세청 API나 외부 데이터베이스를 통해 관세율을 동적으로 가져오는 로직이 실패했을 때를 대비하여, 자주 사용되는 핵심 품목들의 관세율을 시스템 내부에 고정된 표(Static Table, 혹은 캐시) 형태로 저장해 두고 꺼내 쓰도록 처리 방식\
  . UNI-PASS API 호출 실패 시 내부 정적 테이블(류 38, 39, 84, 85, 76, 90)에서 즉시 반환

**1.3 데이터 및 메모리 (RAG & Context)**

* **구현 기능:** [예: PDF 매뉴얼 기반 질의응답]\
  반도체 HS-Code 참조 문서(TXT/PDF) 기반 검색 증강 생성(RAG)

* **동작 원리:** [예: 질문을 임베딩하여 Vector DB에서 상위 3개 문서를 검색(Retriever) 후 답변 생성]\
  문서 적재: data/raw/ 폴더의 TXT/PDF 파일을 로드 — TXT는 --- 구분자 기반 메타데이터(HS-Code·문서명·발행연도·류) 파싱, PDF는 PyPDFLoader로 페이지별 로드\
  청킹: RecursiveCharacterTextSplitter로 chunk_size=500 / overlap=50으로 분할 후 각 청크에 chunk_id 부여\
  임베딩: Azure OpenAI text-embedding-3-small (1,536차원) 으로 청크 벡터화\
  저장: Pinecone 인덱스(hs-code-docs, cosine metric)에 배치 50개 단위로 업로드\
  검색: 사용자 쿼리를 동일 임베딩 모델로 변환 후 similarity_search_with_score로 top-5 청크 반환\
  근거 품질 채점: 문서명·페이지·인용 문장·유사도를 기준으로 8점 만점 자동 채점

* **주요 기술:** [예: FAISS, OpenAI Embeddings, RecursiveCharacterTextSplitter]\
  Pinecone Serverless (cloud vector DB)\
  langchain-pinecone 0.2.0\
  Azure OpenAI text-embedding-3-small (1536차원)\
  RecursiveCharacterTextSplitter (chunk=500, overlap=50)\
  similarity_search_with_score (cosine)

### 주요 문제 해결 및 기술 리서치

구현 과정에서 마주친 기술적 문제와 이를 해결하기 위해 **찾아본 자료(리서치)** 및 **적용한 방법**을 기록합니다. 표의 내용은 예시입니다.

|           |                                                                                                                                                                                                     |                                                                                                                                                                                                                                                |
| --------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **이슈 구분** | **문제 상황 및 원인**                                                                                                                                                                                      | **리서치 및 해결 과정 (Reference & Solution)**                                                                                                                                                                                                         |
| **프롬프트**  | LLM이 search_hs_code_rag 도구 호출 시 product_name, material, purpose 등 개별 파라미터를 각각 넣지 않고, 전체 입력을 하나의 JSON 문자열로 직렬화하여 product_name 필드 하나에 몰아넣는 오형식(Malformed Tool Call) 발생 → Pydantic Validation Error 발생 | • **리서치:** LangChain ReAct 프롬프트의 Action Input 형식 명세 문서 확인. LLM이 예시 없이 스키마만 보면 직렬화 실수를 반복하는 사례 확인 **적용 (2가지):** ① ReAct 프롬프트 내 올바른 Action Input 예시를 명시적으로 추가 ② 도구 함수 내부에 `product_name`이 JSON 문자열일 경우 파싱하여 각 필드로 분해하는 방어 로직 추가 → 오류 해소          |
| **도구 연동** | Streamlit Cloud(<https://streamlit.io)에> 로컬 CromaDB를 사용하면서 로컬에 저장했지만 쿼터이슈로 인한 운영 지속성 불가 발생                                                                                                          | **리서치:&#x20;**&#xCFFC;터량이 있음을 확인하여 다른 도구 연동 검토가 필요함을 확인 **적용:&#x20;**&#x52;ender Web Service + Pinecone cloud 간 API 검색 구조로 변경하여 시스템 운영 영속성 확보                                                                                                  |
| **도구 연동** | Pinecone 인덱스 차원(dimension)을 512로 생성했으나 Azure OpenAI `text-embedding-3-small` 임베딩 출력이 1,536차원이어서 업로드 시 dimension mismatch 오류 발생                                                                      | **리서치:** Azure OpenAI 임베딩 모델 스펙 문서에서 `text-embedding-3-small`의 기본 출력 차원이 1,536임을 확인 **적용:** Pinecone 콘솔에서 기존 인덱스 삭제 후 dimension=1,536, metric=cosine으로 재생성 → 정상 적재                                                                             |
| **성능/기타** | Python 3.13 환경(Render 기본값)에서 `langchain-community`가 요구하는 `numpy≥2.1`과 `langchain-chroma`가 요구하는 `numpy<2.0`이 충돌하여 빌드 실패                                                                              | **리서치:** Render 공식 문서의 Python 버전 지정 방법 확인 — `runtime.txt` 또는 환경변수 `PYTHON_VERSION`으로 버전 고정 가능  **적용:** 저장소 루트에 `runtime.txt` (`python-3.11`) 추가 + Render 대시보드 환경변수 `PYTHON_VERSION=3.11.0` 설정. 근본 원인인 `langchain-chroma` 의존성은 Pinecone 전환으로 제거 |
| **성능/기타** | ChromaDB를 로컬 벡터 DB로 사용했을 때 Render 배포 환경에서 컨테이너 재시작 시마다 인덱스 데이터가 초기화(휘발)되어 매번 재적재 필요                                                                                                                 | **리서치:** Render 무료 플랜의 파일시스템 정책 확인 — Disk는 유료 기능이며 무료 플랜은 배포 시마다 초기화됨. 클라우드 벡터 DB 비교 검토 (Pinecone 무료 Serverless 플랜: 100만 벡터 무료)  **적용:** ChromaDB → Pinecone Serverless로 전환. 적재는 인덱스 버튼 1회 실행으로 영구 보존                                          |

### 핵심 동작 검증

위에서 구현한 기능이 의도대로 동작하는지 보여주는 **대표적인 실행 결과**를 첨부합니다.

**[검증 시나리오 1: RAG 기반 HS-Code 정상 추천]**

* **입력:**\
  품목명: FOUP\
  재질/소재: 폴리카보네이트\
  용도/기능: 300mm 웨이퍼 클린룸 이송 및 보관\
  수출/수입: 수입

* **에이전트 동작:**

  1. 입력값을 구조화된 질문으로 변환 (품목명·재질·용도·유사도 임계값 포함)

  2. search_hs_code_rag("FOUP", material="폴리카보네이트", purpose="300mm 웨이퍼 클린룸 이송 및 보관", similarity_threshold=0.30) 호출\
     → Pinecone에서 hs_3923_FOUP.txt 청크 top-5 검색, 최고 유사도 0.47 반환\
     → 임계값(0.30) 초과 → fallback=False, 후보 HS-Code 반환

  3. query_tax_rate("3923") 호출\
     → 기본관세율 8%, 한-미 FTA 0%, 한-EU FTA 0% 반환

  4. RAG 근거 + 세율 정보를 종합하여 최종 답변 생성

* **최종 결과:**

Fallback: 아니오\
근거 품질: 6.0/8.0점\
추천 결과 예시:\
"**[1순위]&#x20;**&#x48;S-Code 3923100000 — FOUP(Front Opening Unified Pod)은 반도체 300mm 웨이퍼의 클린룸 이송·보관용 폴리카보네이트 재질의 특수 용기입니다. → 근거: hs_3923_FOUP.txt p.1.\
**[세율]&#x20;**&#xAE30;본관세율 8% / FTA 협정세율 0~5%"

**[검증 시나리오 2: RAG 문서 미매칭 시 LLM Fallback 전환]**

* **입력:**\
  품목명: 양자컴퓨터 희석냉동기\
  재질/소재: 알루미늄, 구리\
  용도/기능: 큐비트 냉각용 극저온 장치\
  수출/수입: 수출

* **에이전트 동작:**

  1. search_hs_code_rag("양자컴퓨터 희석냉동기", ...) 호출\
     → Pinecone 검색 실행, 최고 유사도 0.18 반환\
     → 임계값(0.30) 미달 → fallback=True, fallback_reason: "유사도 0.18 < 임계값 0.30" 반환

  2. RAG 근거 없음 인지 (Reasoning) → LLM 자체 지식 기반 추천으로 전환

  3. query_tax_rate() 호출 생략 또는 범용 세율 조회

  4. 경고 배너와 함께 LLM 지식 기반 추천 결과 반환

* **최종 결과:**

Fallback: 예\
근거 품질: 0.0/8.0점\
추천 결과 예시:\
"*&#xA0;RAG 문서 근거 없음 — LLM 지식 기반 추천. [1순위] HS-Code 8419899090 — 극저온 냉각 장치는 제84류 산업용 기계 중 기타 열처리 장치로 분류될 수 있습니다. 반드시 전문가 확인 필요*"
