from __future__ import annotations
import re
from typing import List, Dict, Any, Optional
from backend.app.document_intelligence.document_profile import UnitOfObservation


class UnitOfObservationDetector:
    """Detects the primary entity / unit of observation of a table or dataset candidate.
    Prevents confusing survey responses, variables, or employer companies with occupations."""

    OCCUPATION_SIGNALS = [
        "ofo", "occupation", "job title", "trade", "artisan", "technician",
        "technologist", "engineer", "mechanic", "operator", "manager", "clerk",
        "specialist", "practitioner", "analyst", "moulder", "welder", "fitter"
    ]

    QUALIFICATION_SIGNALS = [
        "saqa", "nqf", "qualification", "diploma", "degree", "certificate",
        "learnership", "curriculum", "subframe", "accreditation", "programme"
    ]

    SURVEY_SIGNALS = [
        "survey", "respondent", "response", "question", "enterprise size",
        "micro", "small", "medium", "large", "mentions", "frequency", "score"
    ]

    VARIABLE_SIGNALS = [
        "variable", "var_name", "label", "codebook", "storage type", "value labels",
        "data type", "missing value", "format"
    ]

    INDUSTRY_SIGNALS = [
        "sic", "industry", "sector", "gdp", "employment growth", "economic sector",
        "manufacturing", "mining", "agriculture"
    ]

    PROVINCE_SIGNALS = [
        "province", "provincial", "gauteng", "mpumalanga", "kwazulu-natal",
        "western cape", "eastern cape", "limpopo", "free state", "north west", "northern cape"
    ]

    COMPANY_SIGNALS = [
        "company", "enterprise", "employer", "firm", "organisation", "organization", "sdl number"
    ]

    @classmethod
    def detect(cls, headers: List[str], sample_rows: List[List[str]], caption: str = "") -> UnitOfObservation:
        combined_text = " ".join([str(h).replace("_", " ").lower() for h in headers] + [caption.replace("_", " ").lower()])
        sample_text = " ".join([str(c).replace("_", " ").lower() for row in sample_rows[:5] for c in row if c])
        all_text = f"{combined_text} {sample_text}"

        scores: Dict[UnitOfObservation, float] = {u: 0.0 for u in UnitOfObservation}

        # Check for OFO Code pattern (e.g. 2021-112101 or 112101 or 6-digit number)
        has_ofo_pattern = any(
            re.search(r"\b(20\d{2}-)?\d{6}\b", str(c))
            for row in sample_rows for c in row
        )
        if has_ofo_pattern or "ofo" in combined_text:
            scores[UnitOfObservation.OCCUPATION] += 4.0

        # Check for SAQA ID pattern (e.g. 5-digit number like 93627)
        has_saqa_pattern = any(
            re.search(r"\b\d{5}\b", str(c))
            for row in sample_rows for c in row
        )
        if (has_saqa_pattern and "saqa" in combined_text) or "nqf level" in combined_text:
            scores[UnitOfObservation.QUALIFICATION] += 4.0

        # Signal matches in headers and caption
        for sig in cls.OCCUPATION_SIGNALS:
            if re.search(r"\b" + re.escape(sig) + r"\b", combined_text):
                scores[UnitOfObservation.OCCUPATION] += 1.5

        for sig in cls.QUALIFICATION_SIGNALS:
            if re.search(r"\b" + re.escape(sig) + r"\b", combined_text):
                scores[UnitOfObservation.QUALIFICATION] += 1.5

        for sig in cls.SURVEY_SIGNALS:
            if re.search(r"\b" + re.escape(sig) + r"\b", combined_text):
                scores[UnitOfObservation.SURVEY_RESPONSE] += 1.5

        for sig in cls.VARIABLE_SIGNALS:
            if re.search(r"\b" + re.escape(sig) + r"\b", combined_text):
                scores[UnitOfObservation.VARIABLE] += 2.0

        for sig in cls.INDUSTRY_SIGNALS:
            if re.search(r"\b" + re.escape(sig) + r"\b", combined_text):
                scores[UnitOfObservation.INDUSTRY] += 1.5

        for sig in cls.PROVINCE_SIGNALS:
            if re.search(r"\b" + re.escape(sig) + r"\b", combined_text):
                scores[UnitOfObservation.PROVINCE] += 1.5

        for sig in cls.COMPANY_SIGNALS:
            if re.search(r"\b" + re.escape(sig) + r"\b", combined_text):
                scores[UnitOfObservation.COMPANY] += 2.5

        # Check for survey question prompts e.g. "1. Please select...", "Is your enterprise..."
        if any(re.search(r"^\d+\.\s*(please|what|how|is|select)", str(r[0]).lower().strip()) for r in sample_rows if r):
            scores[UnitOfObservation.SURVEY_RESPONSE] += 5.0

        best_unit = max(scores.items(), key=lambda x: x[1])
        if best_unit[1] >= 1.5:
            return best_unit[0]

        return UnitOfObservation.UNKNOWN
