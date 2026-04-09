from datetime import datetime, timezone

from sqlalchemy import case, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.terminology_term import TerminologyTerm
from app.models.terminology_version import TerminologyVersion


class TerminologyService:
    async def ensure_seed_terms(self, session: AsyncSession) -> None:
        version = await session.scalar(
            select(TerminologyVersion).where(
                TerminologyVersion.source == 'meddra',
                TerminologyVersion.version == '27.0',
            )
        )
        if version:
            return

        version = TerminologyVersion(
            source='meddra',
            version='27.0',
            status='active',
            description='Seed MedDRA terminology for local development',
            released_at=datetime.now(timezone.utc),
        )
        session.add(version)
        await session.flush()

        terms = [
            ('随机对照试验', 'randomized controlled trial', 'zh', 'en'),
            ('不良事件', 'adverse event', 'zh', 'en'),
            ('主要终点', 'primary endpoint', 'zh', 'en'),
            ('adverse event', '不良事件', 'en', 'zh'),
            ('primary endpoint', '主要终点', 'en', 'zh'),
        ]
        for term, translation, source_lang, target_lang in terms:
            session.add(
                TerminologyTerm(
                    version_id=version.id,
                    source='meddra',
                    term=term,
                    normalized_term=self.normalize(term),
                    translation=translation,
                    source_lang=source_lang,
                    target_lang=target_lang,
                    priority=100,
                )
            )
        await session.commit()

    def normalize(self, term: str) -> str:
        return ' '.join(term.strip().lower().split())

    async def lookup_term(self, session: AsyncSession, term: str, source_lang: str, target_lang: str) -> str:
        normalized = self.normalize(term)
        stmt = (
            select(TerminologyTerm.translation)
            .join(TerminologyVersion, TerminologyVersion.id == TerminologyTerm.version_id)
            .where(
                TerminologyTerm.normalized_term == normalized,
                TerminologyTerm.source_lang == source_lang,
                TerminologyTerm.target_lang == target_lang,
                TerminologyTerm.is_active.is_(True),
                TerminologyVersion.status == 'active',
            )
            .order_by(
                TerminologyTerm.priority.asc(),
                case((TerminologyTerm.source == 'enterprise', 0), else_=1),
                TerminologyVersion.released_at.desc(),
            )
            .limit(1)
        )
        return await session.scalar(stmt) or ''

    async def extract_terms(self, session: AsyncSession, text: str, source_lang: str, target_lang: str) -> list[dict[str, str]]:
        stmt = (
            select(TerminologyTerm)
            .join(TerminologyVersion, TerminologyVersion.id == TerminologyTerm.version_id)
            .where(
                TerminologyTerm.source_lang == source_lang,
                TerminologyTerm.target_lang == target_lang,
                TerminologyTerm.is_active.is_(True),
                TerminologyVersion.status == 'active',
            )
            .order_by(
                TerminologyTerm.priority.asc(),
                case((TerminologyTerm.source == 'enterprise', 0), else_=1),
            )
        )
        rows = (await session.scalars(stmt)).all()
        normalized_text = self.normalize(text)
        matches: list[dict[str, str]] = []
        for index, row in enumerate(rows):
            if row.normalized_term in normalized_text:
                matches.append(
                    {
                        'original': row.term,
                        'translation': row.translation,
                        'placeholder': f'__TERM_{index}__',
                    }
                )
        return matches

    async def version_snapshot(self, session: AsyncSession) -> str | None:
        stmt = select(TerminologyVersion).where(TerminologyVersion.status == 'active')
        rows = (await session.scalars(stmt)).all()
        if not rows:
            return None
        return '|'.join(f'{row.source}:{row.version}' for row in rows)


terminology_service = TerminologyService()
