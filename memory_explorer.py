import os
import yaml
from datetime import date, datetime, timedelta
from typing import List, Optional

from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain.memory import ConversationBufferMemory
from langchain_chroma import Chroma
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser

os.environ["ANONYMIZED_TELEMETRY"] = "False"


class SearchIntent(BaseModel):
    refined_query: str = Field(description="검색에 사용할 핵심 사건·인물·장소 키워드")
    target_date: Optional[str] = Field(default=None, description="특정 단일 날짜 (YYYY-MM-DD)")
    start_date: Optional[str] = Field(default=None, description="날짜 범위 시작 (YYYY-MM-DD)")
    end_date: Optional[str] = Field(default=None, description="날짜 범위 종료 (YYYY-MM-DD)")
    is_temporal_navigation: bool = Field(default=False, description="'다음 날', '전날' 등 상대적 시간 이동 여부")
    navigation_days: int = Field(default=0, description="이동 일수 (다음 날: 1, 전날: -1)")
    target_emotions: List[str] = Field(default=[], description="유사 감정 확장 리스트")
    is_date_unknown: bool = Field(default=False, description="날짜를 명확히 모를 때 True")
    is_valid_memory_query: bool = Field(
        default=True,
        description="사용자의 입력이 일기 기반 회상/탐험 질문인지 여부",
    )
    is_reference_to_previous: bool = Field(
        default=False,
        description="지시어를 사용하거나 이전 대화의 연장선상에서 질문하는지 여부",
    )


class MemoryExplorer:
    def __init__(self, username: str):
        self.username = username
        chroma_path = f"./data/{username}/chroma_db"

        embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
        self.vectorstore = Chroma(
            collection_name="langchain",
            embedding_function=embeddings,
            persist_directory=chroma_path,
        )

        with open("./prompts/memory_explorer.yaml", "r", encoding="utf-8") as f:
            prompts_config = yaml.safe_load(f)

        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

        self.analysis_prompt = ChatPromptTemplate.from_messages([
            ("system", prompts_config["analysis_system_prompt"]),
            ("user", prompts_config["analysis_human_template"]),
        ])
        self.response_prompt = ChatPromptTemplate.from_messages([
            ("system", prompts_config["response_system_prompt"]),
            MessagesPlaceholder(variable_name="chat_history"),
            ("user", prompts_config["response_human_template"]),
        ])
        self.multi_response_prompt = ChatPromptTemplate.from_messages([
            ("system", prompts_config["multi_response_system_prompt"]),
            MessagesPlaceholder(variable_name="chat_history"),
            ("user", prompts_config["multi_response_human_template"]),
        ])

        structured_llm = self.llm.with_structured_output(SearchIntent, method="function_calling")
        self.analyzer = self.analysis_prompt | structured_llm

        self.memory = ConversationBufferMemory(return_messages=True, memory_key="chat_history")
        self.state = {"last_date": None, "last_summary": "없음", "candidates": []}

    def diary_count(self) -> int:
        return self.vectorstore._collection.count()

    def _chroma_search(self, query_text: str, k: int = 20) -> List[dict]:
        total = self.vectorstore._collection.count()
        if total == 0:
            return []
        n = min(k, total)
        results = self.vectorstore.similarity_search_with_score(query_text, k=n)
        return [
            {"content": doc.page_content, "metadata": doc.metadata, "distance": score}
            for doc, score in results
        ]

    def _get_by_date(self, date_str: str) -> List[dict]:
        """특정 날짜의 일기를 날짜 메타데이터로 직접 조회 (시맨틱 검색 우회)."""
        result = self.vectorstore._collection.get(where={"date": date_str})
        return [
            {"content": doc, "metadata": meta, "distance": 0.0}
            for doc, meta in zip(result["documents"], result["metadatas"])
        ]

    def chat(self, query: str) -> str:
        today = date.today().strftime("%Y-%m-%d")
        chat_history = self.memory.load_memory_variables({})["chat_history"]

        # (1) 의도 분석
        intent = self.analyzer.invoke({
            "query": query,
            "chat_history": chat_history,
            "last_date": self.state["last_date"] or "없음",
            "last_summary": self.state["last_summary"],
            "today": today,
        })

        # (0) 유효성 검증
        if not intent.is_valid_memory_query:
            return (
                "죄송하지만, 그건 제가 도와드릴 수 없는 질문이네요.\n"
                "과거의 일기 기록을 함께 탐험하는 걸 도와드릴 수 있어요.\n"
                "예를 들어, '작년 12월에 딸이랑 가구 보러 갔던 거 기억나?'처럼 물어봐 주세요."
            )

        # (2) 날짜 결정
        # 우선순위: target_date > is_temporal_navigation > is_reference_to_previous
        # (temporal navigation은 이전 날짜 기반이므로 reference보다 먼저 처리해야 함)
        search_date = None
        if intent.target_date:
            search_date = intent.target_date
        elif intent.is_temporal_navigation and self.state["last_date"]:
            base = datetime.strptime(self.state["last_date"], "%Y-%m-%d")
            search_date = (base + timedelta(days=intent.navigation_days)).strftime("%Y-%m-%d")
        elif intent.is_reference_to_previous and self.state["last_date"]:
            search_date = self.state["last_date"]

        # (3) enriched query
        emotions_str = " ".join(intent.target_emotions)
        enriched_query = f"{intent.refined_query} {emotions_str}".strip()

        # (4) 문서 검색
        # search_date가 확정된 경우: 날짜 메타데이터로 직접 조회 (k 제한으로 누락되는 문제 방지)
        # 날짜 범위/미확정인 경우: 시맨틱 검색 후 Python-side 필터링
        if search_date:
            docs = self._get_by_date(search_date)
        elif intent.start_date and intent.end_date:
            candidates = self._chroma_search(enriched_query, k=20)
            docs = [
                c for c in candidates
                if intent.start_date <= c["metadata"].get("date", "") <= intent.end_date
            ]
        else:
            docs = self._chroma_search(enriched_query, k=20)

        if not docs:
            if search_date:
                return f"[{search_date}] 날짜에 해당하는 일기 기록을 찾지 못했습니다."
            return "해당 기억에 대한 기록을 찾지 못했습니다."

        # (6) 날짜 불명확 → top-3 후보 제시
        if intent.is_date_unknown and not search_date and len(docs) >= 2:
            top_docs = docs[:3]
            self.state["candidates"] = [d["metadata"].get("date") for d in top_docs]
            self.state["last_date"] = top_docs[0]["metadata"].get("date")
            self.state["last_summary"] = top_docs[0]["content"][:150]

            context_parts = [
                f"[후보 {i}] [{d['metadata'].get('date')} / {d['metadata'].get('emotion')}]\n{d['content']}"
                for i, d in enumerate(top_docs, 1)
            ]
            context = "\n\n".join(context_parts)

            chain = self.multi_response_prompt | self.llm | StrOutputParser()
            answer = chain.invoke({"query": query, "context": context, "chat_history": chat_history})
            self.memory.save_context({"input": query}, {"output": answer})

            dates_str = " / ".join(self.state["candidates"])
            return f"[후보: {dates_str}]\n{answer}"

        # (7) 단일 결과
        top = docs[0]
        self.state["last_date"] = top["metadata"].get("date")
        self.state["last_summary"] = top["content"][:150]
        self.state["candidates"] = []
        context = f"[{top['metadata'].get('date')} / {top['metadata'].get('emotion')}]\n{top['content']}"

        chain = self.response_prompt | self.llm | StrOutputParser()
        answer = chain.invoke({"query": query, "context": context, "chat_history": chat_history})
        self.memory.save_context({"input": query}, {"output": answer})

        return f"[{top['metadata'].get('date')}]\n{answer}"

    def add_entry(self, date_str: str, emotion: str, diary_text: str) -> None:
        """일기를 vectorstore에 upsert. 같은 날짜 기록이 있으면 먼저 삭제 후 추가."""
        from langchain_core.documents import Document

        existing = self.vectorstore._collection.get(where={"date": date_str})
        if existing["ids"]:
            self.vectorstore._collection.delete(ids=existing["ids"])

        doc = Document(
            page_content=diary_text,
            metadata={"date": date_str, "emotion": emotion, "source": f"diary_{date_str}"},
        )
        self.vectorstore.add_documents([doc])

    def reset(self):
        self.memory.clear()
        self.state = {"last_date": None, "last_summary": "없음", "candidates": []}


def add_diary_to_vectorstore(username: str, date_str: str, emotion: str, diary_text: str) -> None:
    """MemoryExplorer 없이 vectorstore에 직접 upsert하는 독립 함수."""
    from langchain_core.documents import Document

    chroma_path = f"./data/{username}/chroma_db"
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    vs = Chroma(
        collection_name="langchain",
        embedding_function=embeddings,
        persist_directory=chroma_path,
    )

    existing = vs._collection.get(where={"date": date_str})
    if existing["ids"]:
        vs._collection.delete(ids=existing["ids"])

    doc = Document(
        page_content=diary_text,
        metadata={"date": date_str, "emotion": emotion, "source": f"diary_{date_str}"},
    )
    vs.add_documents([doc])
