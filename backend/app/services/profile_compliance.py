"""Advisory profile compliance checker service.

PROFILE-04: Evaluates candidate data against profile requirements.
Produces MET/PARTIALLY_MET/NOT_MET per requirement and an overall status.

This function is ADVISORY ONLY — it never raises exceptions or blocks operations.
Called by Phase 6 shortlist compliance endpoint.

Compliance result is intended to be stored in shortlist_entries.compliance_result JSONB.
"""
from typing import Any

from app.models.profile_requirement import ProfileRequirement

# CEFR level ordering — higher number = higher proficiency
_CEFR_ORDER: dict[str, int] = {
    "A1": 1,
    "A2": 2,
    "B1": 3,
    "B2": 4,
    "C1": 5,
    "C2": 6,
}


def _cefr_meets_minimum(candidate_level: str, required_level: str) -> bool:
    """Return True if candidate_level is at or above required_level.

    Unknown levels are treated as 0 (does not meet any minimum).
    """
    return _CEFR_ORDER.get(candidate_level.upper(), 0) >= _CEFR_ORDER.get(
        required_level.upper(), 0
    )


def _evaluate_requirement(
    req: ProfileRequirement, candidate_data: dict[str, Any]
) -> str:
    """Evaluate a single profile requirement against candidate data.

    Returns one of: MET, PARTIALLY_MET, NOT_MET.
    Never raises — all exceptions are caught and result in NOT_MET.
    """
    try:
        req_type = req.req_type.lower()

        if req_type == "skill":
            # Free-text skill match: candidate_data["skills"] contains requirement description
            skills_raw = candidate_data.get("skills", "")
            if isinstance(skills_raw, list):
                skills_text = " ".join(str(s) for s in skills_raw)
            else:
                skills_text = str(skills_raw) if skills_raw else ""
            if req.description.lower() in skills_text.lower():
                return "MET"
            return "NOT_MET"

        elif req_type == "certification":
            # Certification match: check certifications list for exact or partial match
            certs = candidate_data.get("certifications", [])
            if not isinstance(certs, list):
                certs = [str(certs)] if certs else []
            req_lower = req.description.lower()
            for cert in certs:
                cert_lower = str(cert).lower()
                if req_lower == cert_lower:
                    return "MET"
                if req_lower in cert_lower or cert_lower in req_lower:
                    return "PARTIALLY_MET"
            return "NOT_MET"

        elif req_type == "language":
            # Language match: check languages list for matching language with CEFR level
            languages = candidate_data.get("languages", [])
            if not isinstance(languages, list):
                languages = []
            req_lower = req.description.lower()
            for lang_entry in languages:
                if not isinstance(lang_entry, dict):
                    continue
                lang_name = str(lang_entry.get("language", "")).lower()
                if req_lower in lang_name or lang_name in req_lower:
                    # Language found — check CEFR level
                    candidate_cefr = str(lang_entry.get("cefr_level", "")).upper()
                    required_cefr = str(req.min_cefr_level or "").upper()
                    if not required_cefr:
                        # No minimum level required — presence is sufficient
                        return "MET"
                    if _cefr_meets_minimum(candidate_cefr, required_cefr):
                        return "MET"
                    return "PARTIALLY_MET"
            return "NOT_MET"

        elif req_type == "clearance":
            # Clearance match: check clearances list for mention of required clearance
            clearances = candidate_data.get("clearances", [])
            if not isinstance(clearances, list):
                clearances = [str(clearances)] if clearances else []
            req_lower = req.description.lower()
            for clearance_entry in clearances:
                if isinstance(clearance_entry, dict):
                    clearance_str = str(clearance_entry.get("level", "")).lower()
                else:
                    clearance_str = str(clearance_entry).lower()
                if req_lower in clearance_str or clearance_str in req_lower:
                    return "MET"
            return "NOT_MET"

        elif req_type == "education":
            # Education match: substring match in candidate's education field
            education = str(candidate_data.get("education", "")).lower()
            if req.description.lower() in education:
                return "MET"
            return "NOT_MET"

        else:
            # Unknown requirement type — cannot evaluate
            return "NOT_MET"

    except Exception:
        # Advisory service must never raise — return NOT_MET on any error
        return "NOT_MET"


def check_profile_compliance(
    requirements: list[ProfileRequirement],
    candidate_data: dict[str, Any] | None,
) -> dict[str, Any]:
    """Run advisory compliance check of candidate data against profile requirements.

    Evaluates each requirement against candidate_data and produces a per-requirement
    MET/PARTIALLY_MET/NOT_MET status plus an overall summary status.

    Overall status logic:
    - NOT_MET: if ANY mandatory requirement is NOT_MET
    - PARTIALLY_MET: if ANY requirement is PARTIALLY_MET (and no mandatory NOT_MET)
    - MET: all requirements are MET

    Args:
        requirements:   List of ProfileRequirement ORM objects to evaluate.
        candidate_data: Dict of candidate parsed data. If None or empty, all NOT_MET.

    Returns:
        {
            "overall": "MET" | "PARTIALLY_MET" | "NOT_MET",
            "items": [
                {
                    "req_id": str(UUID),
                    "req_type": str,
                    "description": str,
                    "is_mandatory": bool,
                    "status": "MET" | "PARTIALLY_MET" | "NOT_MET"
                }
            ]
        }

    Advisory only — never raises exceptions or blocks operations.
    """
    # Handle empty/None candidate data gracefully
    if not candidate_data:
        candidate_data = {}

    items: list[dict[str, Any]] = []
    for req in requirements:
        item_status = _evaluate_requirement(req, candidate_data)
        items.append(
            {
                "req_id": str(req.id),
                "req_type": req.req_type,
                "description": req.description,
                "is_mandatory": req.is_mandatory,
                "status": item_status,
            }
        )

    # Compute overall status
    has_mandatory_not_met = any(
        item["is_mandatory"] and item["status"] == "NOT_MET" for item in items
    )
    has_partially_met = any(item["status"] == "PARTIALLY_MET" for item in items)

    if has_mandatory_not_met:
        overall = "NOT_MET"
    elif has_partially_met:
        overall = "PARTIALLY_MET"
    else:
        overall = "MET"

    return {"overall": overall, "items": items}
