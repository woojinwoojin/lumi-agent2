"""
데이터베이스 접근 계층

이 패키지에서는 데이터베이스(Supabase) 접근 로직을 정의합니다.
"""
from app.core.config import settings
from loguru import logger

# Supabasse 클라이언트 싱글톤
_supabase_client = None


async def get_supabase_client():
    """
    Supabase 클라이언트를 반환합니다 (싱글톤 패턴).
    
    설정(settings)에 Supabase URL과 Key가 있을 때만 연결을 시도합니다.
    연결 실패 시 None을 반환합니다.
    """
    global _supabase_client

    if _supabase_client is None and settings.supabase_url and settings.supabase_key:
        try:
            from supabase import acreate_client
            _supabase_client = await acreate_client(
                settings.supabase_url,
                settings.supabase_key,
            )
            logger.info("✅ Supabase 비동기 클라이언트 초기화 완료")
        except Exception as e:
            logger.warning(f"Supabase 초기화 실패: {e}")
            _supabase_client = None

    return _supabase_client


# DB연결 클라이언 함수를 선언
# def get_supabase_client():
#     """
#     Supabase 클라이언트를 반환합니다 (싱글톤 패턴).

#     설정(settings)에 Supabase URL과 Key가 있을 때만 연결을 시도합니다.
#     연결 실패 시 None을 반환합니다.
#     """
#     global _supabase_client

#     if _supabase_client is None and settings.supabase_url and settings.supabase_key:
#         try:
#             from supabase import create_client

#             _supabase_client = create_client(
#                 settings.supabase_url,
#                 settings.supabase_key,
#             )
#             logger.info("✅ Supabase 클라이언트 초기화 완료")
#         except Exception as e:
#             logger.warning(f"Supabase 초기화 실패: {e}")
#             _supabase_client = None

#     return _supabase_client

