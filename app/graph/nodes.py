import json
from datetime import datetime
from typing import Literal

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_upstage import ChatUpstage
from loguru import logger
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.prompts import (
    RAG_GROUNDING,
    RESPONSE_PROMPT,
    ROUTER_PROMPT,
    TOOL_GROUNDING,
)
from app.graph.state import LumiState
from app.repositories.rag import get_rag_repository
from app.tools.executor import ToolExecutor


class RouterOutput(BaseModel):
    """
    라우터 노드의 출력 스키마

    LLM이 JSON 파싱 없이 직접 이 형식으로 응답합니다.
    with_structured_output()을 사용하면 자동으로 파싱됩니다.
    """

    intent: Literal["chat", "rag", "tool"] = Field(
        description="사용자 의도: chat(일반대화), rag(정보검색), tool(도구실행)"
    )
    tool_name: str | None = Field(
        default=None, description="실행할 도구 이름 (intent=tool일 때만)"
    )
    tool_args: dict | None = Field(
        default=None, description="도구 실행 인자 (intent=tool일 때만)"
    )


def get_llm() -> ChatUpstage:
    """
    Upstage Solar LLM 클라이언트를 반환
    """
    return ChatUpstage(
        api_key=settings.upstage_api_key, model="solar-pro3", timeout=30, max_retries=2
    )


async def router_node(state: LumiState) -> dict:
    """사용자 의도 분류"""
    last_message = state["messages"][-1]
    user_input = last_message.content

    # LLM 클라이언트 생성
    llm = get_llm()
    structured_llm = llm.with_structured_output(RouterOutput)
    current_date = datetime.now().strftime("%Y-%m-%d")

    messages = [
        SystemMessage(content=f"오늘 날짜: {current_date}\n\n{ROUTER_PROMPT}"),
        HumanMessage(content=user_input),
    ]

    try:
        result = await structured_llm.ainvoke(messages)
        return {
            "intent": result.intent,
            "tool_name": result.tool_name,
            "tool_args": result.tool_args,
        }
    except Exception as e:
        print(f"Router 오류: {e}")
        return {"intent": "chat", "tool_name": None, "tool_args": None}


# RAG Node : 문서 검색
async def rag_node(state: LumiState) -> dict:
    """
    RAG노드 : 사용자 질문과 관련된 문서 검색
    """
    logger.info("[RAG] 문서 검색 시작")

    user_input = state["messages"][-1].content

    try:
        pass
        rag_repo = get_rag_repository()

        docs = await rag_repo.search_similar(
            query=user_input, k=3, filter_status="active"
        )

        # 검색 결과에서 content만 추출
        retrieved_docs = [doc["content"] for doc in docs]

        logger.info(f"[RAG] 검색 완료: {len(retrieved_docs)}개 문서")

    except Exception as e:
        logger.error(f"[RAG] 검색 실패: {e}")

        retrieved_docs = []

    return {"retrieved_docs": retrieved_docs}


tool_executor = ToolExecutor()


async def tool_node(state: LumiState) -> dict:
    """
    Tool 노드 : Tool 실행
    Router에서 결정된 Tool을 실행합니다.

    Args:
        state: 현재 에이전트 상태
    Returns :
        dict : tool_result를 state에 업데이트 함
    """

    tool_name = state["tool_name"]
    tool_args = state["tool_args"] or {}

    logger.info(f"[Tool] 툴 실행: {tool_name}")

    # Tool 실행을 위해 ToolExecutor를 구현
    result = await tool_executor.execute(
        tool_name=tool_name,
        tool_args=tool_args,
        session_id=state["session_id"],
        user_id=state["user_id"],
    )

    logger.info(f"[Tool] 실행 결과: {result}")
    return {"tool_result": result}


async def response_node(state: LumiState) -> dict:
    """
    응답 노드: 최종 응답 생성

    라우팅 결과에 따라 적절한 응답을 생성합니다:
        - chat: 일반 대화 응답
        - rag: 검색된 문서 기반 응답
        - tool: Tool 결과 기반 응답

    Args:
        state: 현재 에이전트 상태

    Returns:
        dict: 업데이트할 상태 필드
            - messages: AI 응답 메시지 추가
    """
    logger.info(f"[Response] 응답 생성 시작 (intent: {state['intent']})")

    llm = get_llm()
    last_message = state["messages"][-1]
    user_input = last_message.content

    # 의도에 따른 프롬프트 구성
    intent = state["intent"]

    # intent에 따라 system 프롬프트를 한 덩어리로 조립
    # - 페르소나(RESPONSE_PROMPT)는 고정, 분기별로 '그라운딩 지시 + 근거 데이터'만 덧붙인다
    # - RAG 전용 프롬프트를 따로 두지 않고, 하나의 RESPONSE_PROMPT + 컨텍스트 주입으로 처리
    # - 그라운딩 지시를 근거 데이터 바로 옆에 두면(co-locate) 모델이 그 근거에만 답하도록 잘 지킨다
    if intent == "rag":
        # RAG 응답: 검색된 문서를 '참고 정보'로 붙이고, 그 내용에만 근거하도록 지시
        context = "\n".join(state["retrieved_docs"])
        system_prompt = f"{RESPONSE_PROMPT}\n\n{RAG_GROUNDING.format(context=context)}"

    elif intent == "tool":
        tool_result = json.dumps(state["tool_result"], ensure_ascii=False)
        system_prompt = (
            f"{RESPONSE_PROMPT}\n\n{TOOL_GROUNDING.format(tool_result=tool_result)}"
        )
    else:
        # 일반 대화 응답: 페르소나 프롬프트만 사용
        system_prompt = RESPONSE_PROMPT

    # 대화 히스토리를 LLM에 전달하여 과거 질문 기억
    # 최근 6개 메시지 (3턴: user+ai 쌍)를 히스토리로 포함
    # 마지막 메시지(현재 질문)는 별도로 추가하므로 제외
    history_messages = state["messages"][:-1][-6:] if len(state["messages"]) > 1 else []

    # 히스토리를 텍스트로 변환
    history_text = ""
    if history_messages:
        history_parts = []
        for msg in history_messages:
            role = "사용자" if isinstance(msg, HumanMessage) else "루미"
            history_parts.append(f"{role}: {msg.content}")
        history_text = "\n".join(history_parts)
        history_text = f"\n\n## 이전 대화:\n{history_text}\n"

    # LLM 호출 (히스토리 포함)
    messages = [
        HumanMessage(content=system_prompt + history_text),
        HumanMessage(content=f"사용자: {user_input}"),
    ]

    try:
        response = await llm.ainvoke(messages)
        ai_response = response.content

        logger.info("💬 [Response] 응답 생성 완료")

    except Exception as e:
        logger.error(f"응답 생성 오류: {e}")
        ai_response = "미안해, 지금 잠깐 문제가 생겼어! 다시 말해줄래? 😅"

    # AI 응답을 messages에 추가
    return {
        "messages": [AIMessage(content=ai_response)],
    }
