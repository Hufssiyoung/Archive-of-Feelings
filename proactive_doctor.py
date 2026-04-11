import os
import json
import yaml
import numpy as np
from collections import Counter

from dotenv import load_dotenv
from sklearn.metrics.pairwise import cosine_similarity
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, FewShotChatMessagePromptTemplate
from langchain_core.output_parsers import StrOutputParser

load_dotenv()

NEGATIVE_EMOTIONS = ["분노", "슬픔", "두려움", "불쾌함"]
PROMPT_PATH = "prompts/proactive_doctor.yaml"


class EmotionalTriggerAnalyzer:

    def __init__(self, model_name="text-embedding-3-small"):
        api_key = os.getenv("OPENAI_API_KEY")
        self.embeddings_model = OpenAIEmbeddings(openai_api_key=api_key, model=model_name)

    def load_diary_window(self, file_path, days=7):
        """최근 n일간의 일기 데이터를 로드하고 최신순으로 반환합니다."""
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        recent_dates = sorted(data.keys(), reverse=True)[:days]
        window_docs = []
        for date in recent_dates:
            entry = data[date]
            text = f"날짜: {entry['date']}, 감정: {entry['emotion']}, 일기: {entry['diary']}"
            window_docs.append({
                "date": entry["date"],
                "text": text,
                "emotion": entry["emotion"],
                "diary": entry["diary"],
            })
        return window_docs

    def _get_crisis_space(self):
        """심리적 고통의 본질을 담은 보편적 앵커 벡터를 반환합니다."""
        anchors = [
            "삶의 의욕이 전혀 없고 모든 것이 허무하게 느껴져 전문가의 상담이 필요하다.",
            "극심한 불안감과 중압감 때문에 일상생활을 유지하기가 힘들어 도움이 필요하다.",
            "혼자라는 고립감과 외로움이 깊어져 누구에게라도 마음을 털어놓고 싶다.",
            "정신적으로 한계에 다다른 것 같아 누군가의 개입이 절실한 상태이다.",
        ]
        return np.array(self.embeddings_model.embed_documents(anchors))

    def analyze_necessity(self, window_docs):
        """necessity_score, centroid, vectors를 반환합니다."""
        texts = [doc["text"] for doc in window_docs]
        vectors = np.array(self.embeddings_model.embed_documents(texts))

        crisis_space = self._get_crisis_space()
        similarity_matrix = cosine_similarity(vectors, crisis_space)
        individual_max_scores = np.max(similarity_matrix, axis=1)

        weighted_scores = []
        stack = 0
        for score, doc in zip(individual_max_scores, window_docs):
            if doc["emotion"] in NEGATIVE_EMOTIONS:
                stack += 1
                weight = 1.3 + stack * 0.2
            else:
                stack = 0
                weight = 1.0
            weighted_scores.append(score * weight)

        negativity_score = np.mean(weighted_scores)
        centroid = np.mean(vectors, axis=0)
        cohesion = float(np.mean(cosine_similarity(vectors, [centroid])))
        necessity_score = negativity_score * 0.7 + cohesion * 0.3

        return necessity_score, centroid, vectors

    def extract_key_context(self, window_docs, vectors, centroid):
        """centroid와 가장 가까운 일기 = 이번 주를 대표하는 핵심 맥락을 반환합니다."""
        similarities = cosine_similarity(vectors, [centroid]).flatten()
        idx = np.argmax(similarities)
        return window_docs[idx]


def _build_doctor_chain():
    with open(PROMPT_PATH, "r", encoding="utf-8") as f:
        prompt_config = yaml.safe_load(f)

    example_prompt = ChatPromptTemplate.from_messages([
        ("human", prompt_config["human_template"]),
        ("ai", "{answer}"),
    ])

    few_shot_prompt = FewShotChatMessagePromptTemplate(
        example_prompt=example_prompt,
        examples=prompt_config["few_shot_examples"],
    )

    final_prompt = ChatPromptTemplate.from_messages([
        ("system", prompt_config["system_prompt"]),
        few_shot_prompt,
        ("human", prompt_config["human_template"]),
    ])

    api_key = os.getenv("OPENAI_API_KEY")
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7, openai_api_key=api_key)
    return final_prompt | llm | StrOutputParser()


def analyze_trigger(username: str, threshold: float = 0.6) -> dict:
    """
    Stage 1~2: 트리거 분석 및 컨텍스트 추출만 수행합니다 (Generation 제외).

    Returns:
        {
            "triggered": bool,
            "score": float,
            "context": {"dominant_emotion", "key_context", "recent_diaries"} | None
        }
    """
    diary_path = os.path.join("data", username, "diary.json")
    if not os.path.exists(diary_path):
        return {"triggered": False, "score": 0.0, "context": None}

    analyzer = EmotionalTriggerAnalyzer()
    window_docs = analyzer.load_diary_window(diary_path, days=7)

    if not window_docs:
        return {"triggered": False, "score": 0.0, "context": None}

    score, centroid, vectors = analyzer.analyze_necessity(window_docs)

    if score <= threshold:
        return {"triggered": False, "score": score, "context": None}

    negative_labels = [doc["emotion"] for doc in window_docs if doc["emotion"] in NEGATIVE_EMOTIONS]
    if not negative_labels:
        return {"triggered": False, "score": score, "context": None}

    dominant_emotion = Counter(negative_labels).most_common(1)[0][0]
    key_doc = analyzer.extract_key_context(window_docs, vectors, centroid)
    key_context = f"[{key_doc['date']}] {key_doc['diary']}"
    recent_diaries = "\n".join(
        f"[{d['date']} / {d['emotion']}] {d['diary']}"
        for d in window_docs[:7]
    )

    return {
        "triggered": True,
        "score": score,
        "context": {
            "dominant_emotion": dominant_emotion,
            "key_context": key_context,
            "recent_diaries": recent_diaries,
        },
    }


def stream_generation(context: dict):
    """Stage 3: LangChain 체인을 스트리밍 모드로 실행하는 제너레이터."""
    doctor_chain = _build_doctor_chain()
    for chunk in doctor_chain.stream(context):
        yield chunk
