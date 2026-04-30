# 📖 Archive of Feelings: AI 감정 분석 및 공감형 상담 일기장

**Archive of Feelings**는 사용자의 일상 기록에서 감정을 분석하고, 과거의 기록을 바탕으로 AI와 대화하며 마음을 치유하는 **RAG(Retrieval-Augmented Generation) 기반 지능형 일기 서비스**입니다.

---

## ✨ 핵심 기능 (Key Features)

### 1. AI 감정 분석 및 캘린더 시각화
* **정교한 감정 분류**: 사용자가 작성한 일기를 분석하여 8가지 감정(기쁨 😊, 놀라움 😮, 두려움 😨, 분노 😠, 불쾌함 😒, 설렘 🤩, 슬픔 😢, 평범함 😐)으로 분류합니다.
* **감정 캘린더**: 날짜별로 분석된 감정을 이모지로 표시하여 한눈에 한 달의 기분 변화를 확인할 수 있습니다.

    - **Core Model**: LimYeri/HowRU-KoELECTRA-Emotion-Classifier (Fine-tuned on Korean Emotion Dataset), 로컬 `model/` 디렉토리에서 로드
    - **Implementation**: HuggingFace `transformers` 라이브러리의 `AutoTokenizer` / `AutoModelForSequenceClassification`, `@st.cache_resource`로 모델 캐싱
    - **Analysis Strategy**:
        - Sentence-level Scoring: 일기 전체를 문장 단위(`.`, `?`, `!` 기준)로 분리하여 각 문장의 감정 확률을 개별 추론합니다.
        - Weighted Decision: 각 감정 클래스별로 누적 확률 합산(total_prob), 출현 빈도(count), 마지막 등장 위치(last_step)를 종합하여 최종 감정을 결정합니다.

### 2. 나의 감정 주치의 (Proactive AI Doctor)
* **임베딩 기반 심리 위기 감지**: 최근 7일치 일기를 OpenAI `text-embedding-3-small`로 임베딩하고, 4개의 심리적 고통 앵커 벡터와의 코사인 유사도로 `necessity_score`를 산출합니다. 점수가 임계값(0.6)을 초과하면 개입을 시작합니다.
    - `necessity_score = negativity_score × 0.7 + cohesion × 0.3`
    - 연속 부정 감정(분노·슬픔·두려움·불쾌함)에는 스택 가중치(`1.3 + stack × 0.2`) 적용
* **3단계 파이프라인**:
    1. **Trigger Analysis**: 7일치 일기 임베딩 → necessity_score 산출 → 개입 여부 결정
    2. **Context Extraction**: 감정 벡터 centroid와 가장 가까운 일기를 핵심 맥락으로 추출
    3. **Streaming Generation**: LangChain Few-Shot 프롬프트 + `gpt-4o-mini` 스트리밍으로 공감 메시지 생성
* **TTS 음성 출력**: 생성된 공감 메시지를 gTTS로 한국어 음성 변환하여 재생합니다. MD5 해시 기반으로 사용자별 캐싱하며, 로그아웃 시 캐시를 자동 삭제합니다.

### 3. 기억 탐험가 (RAG-based Memory Explorer)
* **구조화된 의도 분석**: 사용자 쿼리를 LangChain Structured Output(`SearchIntent` Pydantic 모델)으로 파싱하여 검색 키워드, 날짜/기간, 감정, 시간 이동 여부, 유효성 등을 추출합니다.
* **다양한 검색 전략**: 추출된 의도에 따라 세 가지 검색 방식을 선택합니다.
    - 특정 날짜: Chroma 메타데이터 직접 조회 (`where: {date: ...}`)
    - 날짜 범위: 시맨틱 검색 후 Python-side 필터링
    - 날짜 미확정: 시맨틱 검색 후 상위 3개 후보 제시
* **시간 이동 탐색**: "다음 날", "전날" 같은 상대적 시간 표현을 인식하여 이전 대화의 날짜를 기준으로 탐색합니다.
* **대화 맥락 유지**: `ConversationBufferMemory`로 멀티턴 대화 히스토리를 관리합니다. MemoryExplorer 인스턴스는 사용자별로 `session_state`에 캐싱되며, 일기 저장 시 vectorstore에 자동 upsert됩니다.

---

## 🛠 기술 스택 (Tech Stack)

* **Frontend**: Streamlit (Demo version)
* **Deep Learning**: PyTorch, HuggingFace Transformers (AutoModelForSequenceClassification)
* **LLM**: OpenAI `gpt-4o-mini` (감정 주치의·기억 탐험가 생성)
* **Embeddings**: OpenAI `text-embedding-3-small` (벡터 검색·심리 위기 감지)
* **LLM Framework**: LangChain (RAG, Structured Output, Few-Shot Prompting, ConversationBufferMemory)
* **TTS**: gTTS (한국어 음성 생성, 사용자별 MD5 캐싱)
* **Database**: Local File System (JSON 기반, `data/{username}/diary.json`) & Chroma (Vector Store, `data/{username}/chroma_db`)
* **Numerical**: NumPy, scikit-learn (코사인 유사도)
* **Language**: Python 3.12+