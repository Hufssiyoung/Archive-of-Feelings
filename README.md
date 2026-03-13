# 📖 Archive of Feelings: AI 감정 분석 및 공감형 상담 일기장

**Archive of Feelings**는 사용자의 일상 기록에서 감정을 분석하고, 과거의 기록을 바탕으로 AI와 대화하며 마음을 치유하는 **RAG(Retrieval-Augmented Generation) 기반 지능형 일기 서비스**입니다.

---

## ✨ 핵심 기능 (Key Features)

### 1. AI 감정 분석 및 캘린더 시각화
* **정교한 감정 분류**: 사용자가 작성한 일기를 분석하여 8가지 감정(기쁨, 놀라움, 두려움, 분노, 불쾌함, 설렘, 슬픔, 평범함)으로 분류합니다.
* **감정 캘린더**: 날짜별로 분석된 감정을 이모지로 표시하여 한눈에 한 달의 기분 변화를 확인할 수 있습니다.

### 2. 나의 감정 주치의 (Proactive AI Doctor)
* **부정 감정 감지**: 분노, 슬픔 등 부정적인 감정이 3일 이상 지속될 경우 시스템이 이를 자동으로 감지합니다.
* **선제적 공감 대화**: 사용자가 일기를 쓰러 들어왔을 때, AI가 먼저 따뜻한 위로의 말을 건네며 대화를 시도합니다.

### 3. 기억 탐험가 (RAG-based Memory Explorer)
* **과거 기록 기반 상담**: LangChain과 Vector DB(FAISS)를 활용하여 사용자가 과거에 쓴 일기 내용을 기반으로 답변합니다.
* **상시 대화 기능**: "내가 예전에 우울할 때 어떻게 극복했지?"와 같은 질문에 대해 실제 과거 기록을 바탕으로 맞춤형 조언을 제공합니다.

---

## 🛠 기술 스택 (Tech Stack)

* **Frontend**: Streamlit
* **Deep Learning**: PyTorch, HuggingFace Transformers (AutoModelForSequenceClassification)
* **LLM Framework**: LangChain (RAG Implementation)
* **Database**: Local File System (txt based) & FAISS (Vector Store)
* **Language**: Python 3.9+