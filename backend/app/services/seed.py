from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sfia_level import SfiaLevel

# SFIA levels 1-7 — canonical reference data
SFIA_LEVELS = [
    (1, "Follow", "Works under close direction. Routine tasks with no significant decisions."),
    (2, "Assist", "Works under routine direction. Some autonomy in choosing work approach."),
    (3, "Apply", "Works under general direction. Uses discretion in approach."),
    (4, "Enable", "Works under general guidance. Substantial responsibility for outcomes."),
    (5, "Ensure/Advise", "Broad direction. Accountable for significant outcomes."),
    (6, "Initiate/Influence", "Has defined authority. Accountable for critical business outcomes."),
    (7, "Set Strategy/Inspire", "Highest level. Sets organizational strategy and direction."),
]


async def seed_sfia_levels(db: AsyncSession) -> None:
    """Idempotently seed 7 SFIA levels into the database.

    Checks existing count first — if 7 rows already exist, returns immediately
    without touching the database. Safe to call on every startup.
    """
    existing = (
        await db.execute(select(func.count()).select_from(SfiaLevel))
    ).scalar()
    if existing == 7:
        return
    for level, label, description in SFIA_LEVELS:
        db.add(SfiaLevel(level=level, label=label, description=description))
