import asyncio

import httpx
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.database import async_session
from app.models.esco_skill import EscoSkill
from app.utils.logging import logger

ESCO_API_BASE = "https://ec.europa.eu/esco/api"


async def sync_esco_skills() -> None:
    """Fetch all ESCO KnowledgeSkillCompetence entries and upsert into esco_skills."""
    logger.info("Starting ESCO weekly sync")
    offset = 0
    limit = 100
    total_synced = 0

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            while True:
                resp = await client.get(
                    f"{ESCO_API_BASE}/resource/skill",
                    params={
                        "language": "en",
                        "type": "KnowledgeSkillCompetence",
                        "offset": offset,
                        "limit": limit,
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                embedded = data.get("_embedded", {}).get("results", [])

                if not embedded:
                    break

                async with async_session() as db:
                    for skill in embedded:
                        stmt = pg_insert(EscoSkill).values(
                            uri=skill["uri"],
                            preferred_label=skill.get("title", ""),
                            description=skill.get("description", {}).get("en", {}).get("literal")
                            if isinstance(skill.get("description"), dict)
                            else None,
                            concept_type=skill.get("className", "KnowledgeSkillCompetence"),
                        ).on_conflict_do_update(
                            index_elements=["uri"],
                            set_={
                                "preferred_label": skill.get("title", ""),
                                "synced_at": func.now(),
                            },
                        )
                        await db.execute(stmt)
                    await db.commit()

                total_synced += len(embedded)

                if len(embedded) < limit:
                    break

                offset += limit
                await asyncio.sleep(0.1)

        logger.info(f"ESCO sync complete: {total_synced} skills upserted")

    except Exception as e:
        logger.error(f"ESCO sync failed: {e}")
