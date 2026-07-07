"""
서버 상태 확인 엔드포인트

Production 환경에서 필수적인 헬스체크 API입니다.
로드밸런서, 쿠버네티스 등에서 서버 상태를 확인할 때 사용합니다.

엔드포인트:
    GET /api/v1/health/  - 기본 헬스체크 (main.py의 /api/v1 + routes의 /health prefix)
"""

from datetime import UTC, datetime

from fastapi import APIRouter

from app.core.config import settings

router = APIRouter()


@router.get("/")
async def health_check() -> dict:
    """
    기본 헬스체크 엔드포인트

    서버가 살아있는지 확인하는 가장 기본적인 API입니다.
    로드밸런서의 헬스체크 대상으로 사용됩니다.

    Returns:
        dict: 서버 상태 정보
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now(UTC).isoformat(),
        "service": "lumi-agent",
        "version": "0.5.0",
        "environment": settings.environment,
    }
