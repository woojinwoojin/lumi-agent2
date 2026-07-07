"""
채팅 API 라우트

LangGraph 에이전트를 호출하여 사용자 메시지를 처리합니다.

엔드포인트:
    POST /chat/          - 채팅 메시지 전송
"""
from collections.abc import AsyncGenerator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from langchain_core.messages import AIMessage, AIMessageChunk, BaseMessage, HumanMessage
from loguru import logger

from app.graph import get_lumi_graph
from app.schemas.chat import ChatRequest, ChatResponse, StreamEvent

router = APIRouter()

# In-Memory 세션 저장소 (서버 재시작 시 초기화됨)
SESSION_STORE: dict[str, list[BaseMessage]] = {}


@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """
    채팅 엔드포인트

    사용자 메시지를 LangGraph 에이전트로 처리하고 응답을 반환합니다.

    Args:
        request: 채팅 요청 (message, session_id, user_id)

    Returns:
        ChatResponse: 루미의 응답

    Raises:
        HTTPException: 에이전트 처리 오류 시

    Example:
        ```bash
        curl -X POST "http://localhost:8000/api/v1/chat/" \\
            -H "Content-Type: application/json" \\
            -d '{"message": "오늘 방송 언제야?", "session_id": "user123"}'
        ```
    """
    logger.info(f"📩 채팅 요청: session={request.session_id}, message={request.message[:50]}...")

    try:
        # Step 1: LangGraph 그래프 가져오기
        graph = get_lumi_graph()

        # Step 2: 초기 상태 생성
        # 사용자 메시지를 messages에 포함
        initial_state = {

            "messages": [HumanMessage(content=request.message)], 
            "intent": None,
            "retrieved_docs": [],
            "tool_name": None,
            "tool_args": None,
            "tool_result": None,
            "session_id": request.session_id,
            "user_id": request.user_id,
        }

        # Step 3: 그래프 실행 (비동기)
        logger.debug("🔄 LangGraph 실행 시작")
        final_state = await graph.ainvoke(initial_state)
        logger.debug("✅ LangGraph 실행 완료")

        # Step 4: 최종 응답 추출
        # messages 리스트의 마지막 AIMessage가 최종 응답
        messages = final_state["messages"]
        if len(messages) < 2:
            raise ValueError("응답 메시지가 없습니다.")

        # 마지막 메시지 (AI 응답)
        ai_response = messages[-1].content
        tool_used = final_state.get("tool_name")

        logger.info(f"📤 응답 전송: tool_used={tool_used}")

        return ChatResponse(
            message=ai_response,
            tool_used=tool_used,
            cached=False,
        )
        # 대화 히스토리 유지는 안함

    except Exception as e:
        logger.error(f"채팅 처리 오류: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"에이전트 처리 중 오류가 발생했습니다: {str(e)}",
        )


# ─────────────────────────────────────────────────────────────
# Generator vs AsyncGenerator, 그리고 yield
# ─────────────────────────────────────────────────────────────
# Generator      : yield로 값을 하나씩 만들어 내보내는 함수
# AsyncGenerator : Generator의 비동기(async) 버전.
#                  → async for 로 값을 하나씩 받고, 기다리는 동안 다른 작업 가능
#
# return vs yield  (음식 주문 비유)
#   함수 + return : 요리를 "다 만든 뒤 한 번에" 건네줌   → 포장 주문
#   generator + yield : 만들어지는 대로 "하나씩" 건네줌  → 회전초밥
# ─────────────────────────────────────────────────────────────


# SSE 스트리밍 - Helper 함수
async def stream_with_status(
    message: str,
    session_id: str,
    user_id: str | None = None,
) -> AsyncGenerator[tuple[str | None, str | None, str | None, str | None], None]:

    """
    노드 상태 + 토큰 스트리밍 결합

    진행 상황을 표시하면서 토큰도 스트리밍합니다.
    Gradio UI에서 "생각 중...", "Tool 실행 중..." 표시에 사용됩니다.

    핵심: stream_mode=["updates", "messages"]
        - updates: 노드 완료 시 이벤트 → 진행 상태 표시
        - messages: 토큰 단위 이벤트 → ChatGPT처럼 글자 스트리밍

    Yields:
        tuple[status, token, final_response, tool_used]:
            - (status, None, None, None): 진행 상황 메시지
            - (None, token, None, None): 스트리밍 중인 토큰
            - (None, None, final_response, tool_used): 최종 응답
    """
    graph = get_lumi_graph()

    # 세션에서 이전 메시지 히스토리 가져오기
    session_id = session_id or "default"
    history = SESSION_STORE.get(session_id, [])
    new_message = HumanMessage(content=message)

    # 초기 상태 생성
    initial_state = {
        "messages": history + [new_message],
        "intent": None,
        "retrieved_docs": [],
        "tool_name": None,
        "tool_args": None,
        "tool_result": None,
        "session_id": session_id,
        "user_id": user_id,
    }

    logger.debug(f"📜 [StreamWithStatus] 세션 히스토리: {len(history)}개 메시지")

    final_response = ""
    final_tool_name = None
    current_node = None

    # 노드 이름 → 사용자 친화적 메시지
    node_status = {
        "router": "🔀 루미 생각 중...",
        "rag": "📚 정보 검색 중...",
        "tool": "🔧 도구 실행 중...",
        "response": "💬 응답 작성 중...",
    }

    # 핵심: 두 모드 동시 사용(updates + messages)
    # stream_mode가 리스트일 때: (mode_name, event) 튜플로 반환됨
    async for mode, event in graph.astream(
        initial_state, stream_mode=["updates", "messages"]
    ):
        # 노드 스트리밍 (stream_mode="updates") : 노드가 완료될 때마다 이벤트 발생
        if mode == "updates":
            # event = {"node_name": {출력 상태}}
            for node_name, node_output in event.items():
                if node_name != current_node and node_name in node_status:
                    current_node = node_name
                    # 진행 상황 메시지 yield
                    yield (node_status[node_name], None, None, None)
                    logger.debug(f"🔄 [StreamWithStatus] 노드 진입: {node_name}")

                # tool 노드에서 tool_name 추출
                if node_name == "tool" and node_output:
                    final_tool_name = node_output.get("tool_name")

        # 토큰 스트리밍 (stream_mode="messages") : LLM이 토큰을 생성할 때마다 이벤트 발생
        elif mode == "messages":
            # event = (message, metadata) 튜플
            msg, meta = event
            node_name = meta.get("langgraph_node", "")

            # response 노드의 토큰만 스트리밍 (router 노드 토큰은 무시)
            if node_name != "response":
                continue

            # AIMessageChunk = 토큰 하나
            if isinstance(msg, AIMessageChunk):
                token = msg.content or ""
                if token:
                    final_response += token
                    yield (None, token, None, None)

    # 세션 히스토리에 저장
    if final_response:
        if session_id not in SESSION_STORE:
            SESSION_STORE[session_id] = []
        SESSION_STORE[session_id].append(new_message)
        SESSION_STORE[session_id].append(AIMessage(content=final_response))
        logger.debug(f"💾 [StreamWithStatus] 세션 저장: {session_id}")

    # 마지막에 최종 응답 yield : status, token, final_response, final_tool_name
    yield (None, None, final_response, final_tool_name)


# SSE 스트리밍 엔드포인트
@router.post("/stream")
async def chat_stream(request: ChatRequest) -> StreamingResponse:
    """
    SSE 노드 + 토큰 스트리밍 채팅 엔드포인트

    stream_with_status를 사용하여 노드 상태(thinking)와 토큰을 동시에 스트리밍합니다.

    SSE 이벤트 타입:
        - thinking: 노드 진행 상황 ("🔀 루미 생각 중...")
        - token: LLM 토큰 (글자 단위)
        - response: 최종 응답
        - error: 에러
        - done: 스트리밍 종료

    Example:
        ```bash
        curl -N -X POST "http://localhost:8000/api/v1/chat/stream" \\
            -H "Content-Type: application/json" \\
            -d '{"message": "오늘 방송 언제야?", "session_id": "user123"}'
        ```
    """
    logger.info(f"📩 [Stream] 노드+토큰 스트리밍 요청: session={request.session_id}")

    async def generate() -> AsyncGenerator[str, None]:
        """SSE 이벤트 생성기 - 노드 상태 + 토큰 스트리밍"""
        try:
            async for status, token, final, tool_used in stream_with_status(
                request.message,
                request.session_id,
                request.user_id,
            ):
                # 노드 상태 (thinking 이벤트)
                if status:
                    yield StreamEvent(type="thinking", content=status).to_sse()

                # 토큰 스트리밍 (token 이벤트)
                if token:
                    yield StreamEvent(type="token", content=token).to_sse()

                # 최종 응답 (response 이벤트)
                if final:
                    yield StreamEvent(
                        type="response", content=final, tool_used=tool_used
                    ).to_sse()

            yield StreamEvent(type="done").to_sse()
            logger.info(f"✅ [Stream] 완료: session={request.session_id}")

        except Exception as e:
            logger.error(f"❌ [Stream] 오류: {e}")
            yield StreamEvent(type="error", error=str(e)).to_sse()
            yield StreamEvent(type="done").to_sse()

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
