"""
HTTP 엔드포인트 정의

각 라우터는 특정 도메인의 API를 담당합니다:
    - chat.py: 채팅 API
"""

from fastapi import APIRouter

from app.api.routes import chat, health

api_router = APIRouter()
# 💡 prefix="/chat" → chat.router 안의 "/" 경로가 실제로는 "/chat/"으로 열림
#    (창구 이름표를 붙여, 어느 도메인 API인지 URL만 보고 알 수 있게 함)
api_router.include_router(chat.router, prefix="/chat", tags=["Chat"])
api_router.include_router(health.router, prefix="/health", tags=["Health"])
