from sqlalchemy.ext.asyncio import AsyncSession

from app.services.terminology_service import terminology_service


async def meddra_lookup(session: AsyncSession, term: str, source_lang: str = 'zh', target_lang: str = 'en') -> str:
    return await terminology_service.lookup_term(session, term, source_lang, target_lang)
