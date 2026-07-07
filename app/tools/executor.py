"""
Tool 실행 로직

ToolExecutor 클래스가 각 Tool의 실행을 담당합니다.
Tool 이름과 인자를 받아서 적절한 함수를 호출하고 결과를 반환합니다.

구현 상태:
    - get_schedule: ✅ Real (Supabase 조회)
    - send_fan_letter: ✅ Real (Supabase 저장)
    - recommend_song: 🔶 Mock (하드코딩된 데이터)
    - get_weather: 🔶 Mock (하드코딩된 데이터)
"""

import random
from typing import Any, Optional
from loguru import logger

from app.repositories.schedule import ScheduleRepository
from app.repositories.fan_letter import FanLetterRepository


# 🔶 Mock 데이터: 루미의 노래 목록
LUMI_SONGS = {
    "happy": [
        {"title": "Shine Bright", "album": "First Light"},
        {"title": "Happy Day", "album": "Luminous"},
        {"title": "Dancing Star", "album": "First Light"},
    ],
    "sad": [
        {"title": "Rainy Day", "album": "Moonlight"},
        {"title": "Missing You", "album": "Luminous"},
    ],
    "energetic": [
        {"title": "Power Up", "album": "Energy"},
        {"title": "Let's Go!", "album": "First Light"},
        {"title": "On Fire", "album": "Energy"},
    ],
    "calm": [
        {"title": "Starlight", "album": "Moonlight"},
        {"title": "Peaceful Night", "album": "Moonlight"},
    ],
    "romantic": [
        {"title": "First Love", "album": "Luminous"},
        {"title": "Heart Beat", "album": "Luminous"},
    ],
}

# 🔶 Mock 데이터: 날씨 정보
MOCK_WEATHER = {
    "location": "서울",
    "temperature": 5,
    "condition": "맑음",
    "humidity": 45,
    "wind_speed": 3.2,
}


class ToolExecutor:
    """
    Tool 실행기

    에이전트의 Tool 호출을 처리합니다.
    각 Tool 이름에 해당하는 메서드를 호출하여 결과를 반환합니다.

    Attributes:
        schedule_repo: 스케줄 Repository
        fan_letter_repo: 팬레터 Repository

    Example:
        >>> executor = ToolExecutor()
        >>> result = await executor.execute(
        ...     tool_name="get_schedule",
        ...     tool_args={"start_date": "2025-01-06", "end_date": "2025-01-12"},
        ...     session_id="user123"
        ... )
    """

    def __init__(self):
        """ToolExecutor 초기화"""
        # Repository 인스턴스 생성
        self.schedule_repo = ScheduleRepository()
        self.fan_letter_repo = FanLetterRepository()

    async def execute(
        self,
        tool_name: str,
        tool_args: dict,
        session_id: str,
        user_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Tool을 실행합니다.

        Args:
            tool_name: 실행할 Tool 이름
            tool_args: Tool 인자
            session_id: 세션 식별자
            user_id: 사용자 식별자 (선택)

        Returns:
            dict: Tool 실행 결과
                - success: 성공 여부
                - data: 결과 데이터 (성공 시)
                - error: 에러 메시지 (실패 시)
                - mock: Mock 데이터 여부

        Raises:
            ValueError: 알 수 없는 Tool 이름인 경우
        """
        logger.info(f"🔧 [ToolExecutor] Tool 실행: {tool_name}")
        logger.debug(f"인자: {tool_args}")

        try:
            # 💡 match/case = '도구 이름표 보고 알맞은 서랍 열기'. tool_name 값에 맞는 전용 메서드로 분배(dispatch)합니다.
            #    - 다른 언어의 switch/case 문과 비슷합니다 (여러 값 중 하나에 맞춰 분기).
            #    - 파이썬엔 원래 없다가 3.10부터 추가된 문법입니다 (3.9 이하에선 SyntaxError → if/elif로 대체해야 함).
            #    - `case "get_schedule":` 처럼 값이 일치하면 그 블록 실행. `case _:` 는 '그 외 전부'(switch의 default).
            #      모르는 도구면 case _ 로 떨어져 success:False 반환 → 뒤의 response 노드가 부드럽게 안내합니다.
            match tool_name:
                case "get_schedule":
                    return await self._get_schedule(tool_args)

                case "send_fan_letter":
                    return await self._send_fan_letter(
                        tool_args, session_id, user_id
                    )

                case "recommend_song":
                    return await self._recommend_song(tool_args)

                case "get_weather":
                    return await self._get_weather(tool_args)

                case _:
                    logger.warning(f"알 수 없는 Tool: {tool_name}")
                    return {
                        "success": False,
                        "error": f"알 수 없는 Tool: {tool_name}",
                    }

        except Exception as e:
            logger.error(f"Tool 실행 오류: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    # 🗓️ get_schedule: 스케줄 조회 (Real - Supabase)
    async def _get_schedule(self, args: dict) -> dict:
        """
        ✅ Real: Supabase에서 스케줄 조회

        Args:
            args: {"start_date": str, "end_date": str, "event_type": str}

        Returns:
            dict: 스케줄 목록
        """
        start_date = args.get("start_date")
        end_date = args.get("end_date")
        event_type = args.get("event_type", "all")

        logger.info(f"📅 스케줄 조회: {start_date} ~ {end_date}, type={event_type}")

        # Supabase에서 조회
        schedules = await self.schedule_repo.get_schedules(
            start_date=start_date,
            end_date=end_date,
            event_type=event_type if event_type != "all" else None,
        )

        if not schedules:
            return {
                "success": True,
                "data": {
                    "schedules": [],
                    "message": "해당 기간에 예정된 스케줄이 없어요.",
                },
            }

        return {
            "success": True,
            "data": {
                "schedules": schedules,
                "count": len(schedules),
            },
        }

    # 💌 send_fan_letter: 팬레터 저장 (Real - Supabase)
    async def _send_fan_letter(
        self,
        args: dict,
        session_id: str,
        user_id: Optional[str],
    ) -> dict:
        """
        ✅ Real: Supabase에 팬레터 저장

        Args:
            args: {"category": str, "message": str}
            session_id: 세션 ID
            user_id: 사용자 ID

        Returns:
            dict: 저장 결과
        """
        category = args.get("category", "other")
        message = args.get("message", "")

        logger.info(f"💌 팬레터 저장: category={category}, message={message[:50]}...")

        # Supabase에 저장
        letter_id = await self.fan_letter_repo.create(
            session_id=session_id,
            user_id=user_id,
            category=category,
            message=message,
        )

        return {
            "success": True,
            "data": {
                "letter_id": letter_id,
                "message": "팬레터가 잘 전달됐어요!",
            },
        }

    # 🎵 recommend_song: 노래 추천 (Mock)
    async def _recommend_song(self, args: dict) -> dict:
        """
        🔶 Mock: 하드코딩된 노래 목록에서 추천

        Args:
            args: {"mood": str}

        Returns:
            dict: 추천 노래 정보
        """
        mood = args.get("mood", "happy")

        logger.info(f"🎵 노래 추천: mood={mood}")

        songs = LUMI_SONGS.get(mood, LUMI_SONGS["happy"])
        selected = random.choice(songs)

        return {
            "success": True,
            "data": {
                "song": selected,
                "mood": mood,
            },
            "mock": True,  # Mock 데이터임을 표시
        }

    # 🌤️ get_weather: 날씨 조회 (Mock)
    async def _get_weather(self, args: dict) -> dict:
        """
        🔶 Mock: 하드코딩된 날씨 정보 반환

        Args:
            args: {} (파라미터 없음)

        Returns:
            dict: 날씨 정보
        """
        logger.info("🌤️ 날씨 조회 (Mock)")

        return {
            "success": True,
            "data": MOCK_WEATHER,
            "mock": True,
        }
