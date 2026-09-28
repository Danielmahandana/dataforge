from __future__ import annotations
import re
import difflib
from typing import List, Dict, Any, Tuple, Optional
from pydantic import BaseModel, Field


class DuplicateFlag(BaseModel):
    record_id: str
    target_record_id: str
    duplicate_type: str  # EXACT_DUPLICATE, STRUCTURAL_DUPLICATE, POSSIBLE_SEMANTIC_DUPLICATE, LEGITIMATE_RELATED_RECORD
    similarity_score: float
    field_compared: str
    value_a: str
    value_b: str
    recommendation: str  # MERGE, REVIEW, KEEP_SEPARATE
    reason: str


class SemanticDeduplicator:
    """Detects exact, structural, and semantic duplicate candidates without silently merging or discarding records."""

    @classmethod
    def normalize_text_for_comparison(cls, text: str) -> str:
        if not text:
            return ""
        s = str(text).lower().strip()
        # Remove punctuation
        s = re.sub(r"[^\w\s]", " ", s)
        # Collapse whitespace
        return " ".join(s.split())

    @classmethod
    def calculate_token_similarity(cls, a: str, b: str) -> float:
        norm_a = cls.normalize_text_for_comparison(a)
        norm_b = cls.normalize_text_for_comparison(b)
        if not norm_a or not norm_b:
            return 0.0
        if norm_a == norm_b:
            return 1.0

        # Sequence matcher similarity
        seq_ratio = difflib.SequenceMatcher(None, norm_a, norm_b).ratio()

        # Token set Jaccard similarity
        tokens_a = set(norm_a.split())
        tokens_b = set(norm_b.split())
        jaccard = len(tokens_a.intersection(tokens_b)) / max(len(tokens_a.union(tokens_b)), 1)

        return round(0.5 * seq_ratio + 0.5 * jaccard, 4)

    @classmethod
    def analyze_dataset_duplicates(
        cls,
        records: List[Dict[str, Any]],
        primary_key_field: Optional[str] = None,
        title_field: Optional[str] = None,
    ) -> List[DuplicateFlag]:
        """Analyzes records for duplicate candidates and returns categorized flags."""
        flags: List[DuplicateFlag] = []
        n = len(records)
        if n < 2:
            return flags

        # Helper to extract primary title
        def get_title(r: Dict[str, Any]) -> str:
            d = r.get("data") or {}
            if title_field and d.get(title_field):
                return str(d[title_field])
            return str(
                d.get("occupation_title")
                or d.get("occupation")
                or d.get("qualification")
                or d.get("qualification_name")
                or d.get("title")
                or ""
            )

        # Helper to extract identifier
        def get_pk(r: Dict[str, Any]) -> str:
            d = r.get("data") or {}
            if primary_key_field and d.get(primary_key_field):
                return str(d[primary_key_field])
            return str(d.get("ofo_code") or d.get("saqa_id") or d.get("code") or "")

        seen_pks: Dict[str, str] = {}  # pk -> record_id

        for i in range(n):
            rec_a = records[i]
            id_a = str(rec_a.get("id", f"rec_{i}"))
            pk_a = get_pk(rec_a)
            title_a = get_title(rec_a)

            # 1. Exact / Structural PK check
            if pk_a:
                if pk_a in seen_pks:
                    target_id = seen_pks[pk_a]
                    flags.append(
                        DuplicateFlag(
                            record_id=id_a,
                            target_record_id=target_id,
                            duplicate_type="STRUCTURAL_DUPLICATE",
                            similarity_score=1.0,
                            field_compared="primary_key",
                            value_a=pk_a,
                            value_b=pk_a,
                            recommendation="REVIEW",
                            reason=f"Duplicate primary identifier '{pk_a}' found in separate records. Needs review for multi-campus or multi-year revision.",
                        )
                    )
                else:
                    seen_pks[pk_a] = id_a

            # 2. Semantic title comparison against subsequent records (capped window for performance)
            compare_window = min(n, i + 50)
            for j in range(i + 1, compare_window):
                rec_b = records[j]
                id_b = str(rec_b.get("id", f"rec_{j}"))
                title_b = get_title(rec_b)

                if not title_a or not title_b:
                    continue

                sim = cls.calculate_token_similarity(title_a, title_b)

                if sim >= 0.98:
                    flags.append(
                        DuplicateFlag(
                            record_id=id_a,
                            target_record_id=id_b,
                            duplicate_type="EXACT_DUPLICATE",
                            similarity_score=sim,
                            field_compared="title",
                            value_a=title_a,
                            value_b=title_b,
                            recommendation="REVIEW",
                            reason="Near-identical title extracted across records.",
                        )
                    )
                elif sim >= 0.65:
                    norm_a = cls.normalize_text_for_comparison(title_a)
                    norm_b = cls.normalize_text_for_comparison(title_b)
                    # Check if titles denote distinct professional tiers (e.g. Technician vs Technologist vs Engineer vs Artisan)
                    distinct_tiers = ["technician", "technologist", "engineer", "artisan", "mechanic", "operator", "supervisor"]
                    words_a = set(norm_a.split())
                    words_b = set(norm_b.split())
                    tier_diff_a = words_a.intersection(distinct_tiers)
                    tier_diff_b = words_b.intersection(distinct_tiers)

                    if tier_diff_a and tier_diff_b and tier_diff_a != tier_diff_b:
                        flags.append(
                            DuplicateFlag(
                                record_id=id_a,
                                target_record_id=id_b,
                                duplicate_type="LEGITIMATE_RELATED_RECORD",
                                similarity_score=sim,
                                field_compared="title",
                                value_a=title_a,
                                value_b=title_b,
                                recommendation="KEEP_SEPARATE",
                                reason=(
                                    f"Distinct professional qualification tiers identified "
                                    f"('{', '.join(tier_diff_a)}' vs '{', '.join(tier_diff_b)}'). "
                                    f"Under Zero Blind Trust, related occupational variants must be kept separate and never merged."
                                ),
                            )
                        )
                    elif sim >= 0.78:
                        flags.append(
                            DuplicateFlag(
                                record_id=id_a,
                                target_record_id=id_b,
                                duplicate_type="POSSIBLE_SEMANTIC_DUPLICATE",
                                similarity_score=sim,
                                field_compared="title",
                                value_a=title_a,
                                value_b=title_b,
                                recommendation="REVIEW",
                                reason=f"High semantic overlap ({int(sim*100)}%). Potential synonym or variant occupation requiring operator review.",
                            )
                        )

        return flags
