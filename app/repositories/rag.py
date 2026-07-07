"""
RAG를 위한 문서 검색
- query(사용자 입력)와 가장 유사한 Lumi문서 K개를 반환
"""
from typing import Literal

from langchain_upstage import UpstageEmbeddings
from loguru import logger
from app.core.config import settings
from app.repositories import get_supabase_client

class RAGRepository :
    """
    Supabase pgvector를 사용하여 시멘틱 검색을 수행합니다.

    메타데이터 필터링 지원
    - filter_state="active" : 활성화된 문서만 검색(기본값)
    - filter_state="deprecated" : 폐기된 문서만 검색
    - filter_state="all" : 모든 문서 검색
    
    Attributes:
        embeddings: Upstage 임베딩 클라이언트
    """

    def __init__(self):
        """
        RAGRepository 초기화
        """

        self.embeddings = UpstageEmbeddings(
            api_key=settings.upstage_api_key,
            model=settings.embedding_model
        )

        logger.info("RAGRepository 초기화 완료")
    
    async def search_similar(
        self,
        query: str,
        k: int = 3,
        filter_status: Literal["active", "deprecated", "all"] = "active"
    ) -> list[dict] :
        """
        쿼리와 유사한 문서를 검색합니다.

        Args:
            query: 검색 쿼리
            k: 반환할 문서 수 (기본값: 3)
            filter_status: 필터링 조건 (기본값: "active")

        Return:
            list[dict]: 검색된 문서 목록
                - id : 문서 ID
                - content : 문서 내용
                - metadata : 버전, 상태 정보 등
                - similarity : 유사도 점수 (0~1)
        """
        logger.info(f"RAG 검색: '{query[:30]}... (k={k}, filter={filter_status})")

        try :
            pass
            # (1) 쿼리 임베딩
            query_embedding = await self.embeddings.aembed_query(query)

            # (2) Supabase 함수로 유사 문서 검색
            client = await get_supabase_client()
            result = await client.rpc(
                "match_documents",
                {
                    "query_embedding": query_embedding,
                    "match_count":k,
                    "filter_status": filter_status
                }
            ).execute()

            docs = result.data or []

            # 결과 로깅 (디버깅용)
            for doc in docs:
                version = doc.get("metadata", {}).get("version", "?")
                status = doc.get("metadata", {}).get("status", "?")
                similarity = doc.get("similarity", 0)
                logger.debug(f"  - v{version} ({status}): {similarity:.3f}")
            logger.info(f"RAG 검색 결과: {len(docs)}개 문서")

            return docs

        except Exception as e :
            logger.error(f"RAG 검색 실패: {e}")
            return []

# 싱글톤 인스턴스
_rag_repository: RAGRepository | None = None

def get_rag_repository() -> RAGRepository :
    """
    RAGRepository 싱글톤 인스턴스를 반환합니다.
    """
    global _rag_repository

    if _rag_repository is None :
        _rag_repository = RAGRepository()
    
    return _rag_repository