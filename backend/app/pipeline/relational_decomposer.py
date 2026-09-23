from __future__ import annotations
import re
import uuid
import logging
from typing import List, Dict, Any, Tuple, Optional
from backend.app.schemas.blueprints import ExtractionBlueprint, BlueprintField, get_blueprint
from backend.app.pipeline.table_healer import TableHealer
from backend.app.pipeline.normalizer import Normalizer

logger = logging.getLogger("dataforge.pipeline.decomposer")


class RelationalDecomposer:
    """Universal domain-agnostic relational decomposer for any document schema blueprint."""

    @classmethod
    def decompose(
        cls,
        raw_records: List[Dict[str, Any]],
        blueprint: Optional[ExtractionBlueprint] = None,
        blueprint_id: str = "universal_auto",
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Decomposes flat raw extractions according to an ExtractionBlueprint into:
        - primary_entity table
        - dimension_entity table (if array/list fields present)
        - junction table
        - review_required audit table
        """
        bp = blueprint or get_blueprint(blueprint_id)
        if bp.id == "qualifications":
            return cls.decompose_tvet_qualifications(raw_records)

        primary_table_name = bp.id if bp.id != "universal_auto" else "extracted_entity"
        dim_table_name = bp.dimension_entity_name or "dimension_items"
        junction_table_name = f"{primary_table_name}_{dim_table_name}"

        primary_table: List[Dict[str, Any]] = []
        dimension_table: List[Dict[str, Any]] = []
        junction_table: List[Dict[str, Any]] = []
        review_required: List[Dict[str, Any]] = []

        dim_item_to_id: Dict[str, str] = {}
        dim_counter = 0
        seen_primary_keys: Dict[str, int] = {}

        # Identify array fields
        array_fields = [f for f in bp.fields if f.is_array_field]

        pk_field_name = bp.primary_key or (bp.fields[0].name if bp.fields else "id")

        for idx, rec in enumerate(raw_records, start=1):
            pk_val = str(rec.get(pk_field_name) or rec.get("id") or f"ROW-{idx:04d}").strip()
            prov = rec.get("provenance") or {}
            page_num = prov.get("page_number", 1)

            # Check PK duplication
            if pk_val in seen_primary_keys:
                review_required.append({
                    "row_index": idx,
                    "entity_id": pk_val,
                    "field_name": pk_field_name,
                    "anomaly_type": "duplicate_primary_key",
                    "description": f"Primary key '{pk_val}' appears multiple times.",
                    "raw_value": pk_val,
                    "recommended_action": "Verify row uniqueness or merge duplicate records.",
                })
            else:
                seen_primary_keys[pk_val] = idx

            primary_row: Dict[str, Any] = {"id": pk_val}

            # Process defined fields
            for field in bp.fields:
                val = rec.get(field.name)
                norm_val, _ = Normalizer.normalize_value(val, field.name)

                # Required check
                if field.required and (norm_val is None or str(norm_val).strip() == ""):
                    review_required.append({
                        "row_index": idx,
                        "entity_id": pk_val,
                        "field_name": field.name,
                        "anomaly_type": "missing_required_field",
                        "description": f"Required field '{field.name}' is missing.",
                        "raw_value": str(val) if val is not None else None,
                        "recommended_action": "Inspect source document for missing value.",
                    })

                # Regex pattern check
                if field.regex_pattern and norm_val is not None:
                    if not re.match(field.regex_pattern, str(norm_val)):
                        review_required.append({
                            "row_index": idx,
                            "entity_id": pk_val,
                            "field_name": field.name,
                            "anomaly_type": "pattern_mismatch",
                            "description": f"Value '{norm_val}' does not match pattern {field.regex_pattern}.",
                            "raw_value": str(val),
                            "recommended_action": "Correct field format.",
                        })

                # Array / Delimited field decomposition into dimension & junction tables
                if field.is_array_field and val:
                    val_str = str(val)
                    items, dups = TableHealer.deduplicate_incell_colleges(val_str)

                    if not items:
                        review_required.append({
                            "row_index": idx,
                            "entity_id": pk_val,
                            "field_name": field.name,
                            "anomaly_type": "empty_array_field",
                            "description": f"Array field '{field.name}' is empty.",
                            "raw_value": val_str,
                            "recommended_action": "Confirm zero entries in source document.",
                        })

                    for dup_item in dups:
                        review_required.append({
                            "row_index": idx,
                            "entity_id": pk_val,
                            "field_name": field.name,
                            "anomaly_type": "in_cell_duplicate_item",
                            "description": f"Item '{dup_item}' was repeated within the same cell.",
                            "raw_value": dup_item,
                            "recommended_action": "Deduplicated automatically in junction table.",
                        })

                    for item_str in items:
                        i_key = item_str.lower().strip()
                        if i_key not in dim_item_to_id:
                            dim_counter += 1
                            dim_id = f"DIM-{dim_counter:04d}"
                            dim_item_to_id[i_key] = dim_id
                            dimension_table.append({
                                "item_id": dim_id,
                                "item_name_raw": item_str,
                                "item_name": Normalizer.clean_unicode(item_str),
                            })
                        else:
                            dim_id = dim_item_to_id[i_key]

                        junction_table.append({
                            "entity_id": pk_val,
                            "item_id": dim_id,
                            "page_number": page_num,
                        })

                primary_row[field.name] = norm_val
                primary_row[f"{field.name}_raw"] = val

            primary_row["page_number"] = page_num
            primary_row["confidence"] = rec.get("confidence_score", 0.95)
            primary_table.append(primary_row)

        res = {
            primary_table_name: primary_table,
            "review_required": review_required,
        }

        if dimension_table:
            res[dim_table_name] = dimension_table
            res[junction_table_name] = junction_table

        return res

    @classmethod
    def decompose_tvet_qualifications(
        cls,
        raw_records: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Specialized TVET qualifications decomposer."""
        qualifications_table: List[Dict[str, Any]] = []
        colleges_table: List[Dict[str, Any]] = []
        junction_table: List[Dict[str, Any]] = []
        dspp_table: List[Dict[str, Any]] = []
        review_required_table: List[Dict[str, Any]] = []

        college_name_to_id: Dict[str, str] = {}
        college_counter = 0
        seen_saqa_ids: Dict[str, int] = {}

        for idx, rec in enumerate(raw_records, start=1):
            saqa_id = str(rec.get("saqa_id") or rec.get("saqa") or rec.get("id") or "").strip()
            title_raw = str(rec.get("qualification") or rec.get("title") or rec.get("qualification_title") or "").strip()
            nqf_raw = str(rec.get("nqf_level") or rec.get("nqf") or rec.get("level") or "").strip()
            framework_raw = str(rec.get("framework") or rec.get("sub_framework") or "OQSF").strip()
            nsfas_raw = str(rec.get("nsfas_eligible") or rec.get("nsfas") or "No").strip()
            colleges_raw = str(rec.get("participating_colleges") or rec.get("colleges") or "").strip()

            prov = rec.get("provenance") or {}
            page_num = prov.get("page_number", 1)

            title_clean, colleges_raw = TableHealer.repair_text_wrap_bleed(title_raw, colleges_raw)

            qual_num_match = re.search(r"qual(?:ification)?\s*(?:no|number|#)?\s*:?\s*(\d+)", title_raw, re.IGNORECASE)
            qual_number = qual_num_match.group(1) if qual_num_match else None

            nqf_match = re.search(r"\d+", nqf_raw)
            nqf_level = int(nqf_match.group(0)) if nqf_match and 1 <= int(nqf_match.group(0)) <= 10 else None

            if not saqa_id or not re.match(r"^\d{4,7}$", saqa_id):
                review_required_table.append({
                    "row_index": idx,
                    "saqa_id": saqa_id,
                    "field_name": "saqa_id",
                    "anomaly_type": "invalid_saqa_id_format",
                    "description": f"SAQA ID '{saqa_id}' does not match standard 4-7 digit format.",
                    "raw_value": saqa_id,
                    "recommended_action": "Verify source document page for correct SAQA ID",
                })

            if saqa_id in seen_saqa_ids:
                review_required_table.append({
                    "row_index": idx,
                    "saqa_id": saqa_id,
                    "field_name": "saqa_id",
                    "anomaly_type": "duplicate_saqa_id",
                    "description": f"SAQA ID '{saqa_id}' appears multiple times across document.",
                    "raw_value": saqa_id,
                    "recommended_action": "Merge records or verify page split",
                })
            else:
                seen_saqa_ids[saqa_id] = idx

            nsfas_eligible, _ = Normalizer.normalize_value(nsfas_raw, "nsfas_eligible")

            qualifications_table.append({
                "saqa_id": saqa_id,
                "qualification_number": qual_number,
                "qualification_name": Normalizer.clean_unicode(title_clean),
                "qualification_name_raw": title_raw,
                "nqf_level": nqf_level,
                "nqf_sub_framework": framework_raw,
                "nsfas_allowance": "Eligible" if nsfas_eligible else "Not Eligible",
                "page_number": page_num,
                "confidence": rec.get("confidence_score", 0.95),
            })

            unique_colleges, duplicate_colleges = TableHealer.deduplicate_incell_colleges(colleges_raw)

            if not unique_colleges:
                review_required_table.append({
                    "row_index": idx,
                    "saqa_id": saqa_id,
                    "field_name": "participating_colleges",
                    "anomaly_type": "zero_colleges_listed",
                    "description": f"Qualification SAQA {saqa_id} has no listed participating colleges (source cell genuinely blank).",
                    "raw_value": colleges_raw,
                    "recommended_action": "Confirm zero offering colleges in source annexure",
                })

            for dup_c in duplicate_colleges:
                review_required_table.append({
                    "row_index": idx,
                    "saqa_id": saqa_id,
                    "field_name": "participating_colleges",
                    "anomaly_type": "in_cell_duplicate_college",
                    "description": f"College '{dup_c}' was repeated within the same cell for SAQA {saqa_id}.",
                    "raw_value": dup_c,
                    "recommended_action": "Deduplicated automatically in qualification_colleges junction",
                })

            for college_str in unique_colleges:
                c_key = college_str.lower().strip()
                if c_key not in college_name_to_id:
                    college_counter += 1
                    c_id = f"COL-{college_counter:03d}"
                    college_name_to_id[c_key] = c_id
                    is_variant = len(college_str) < 5 or not re.search(r"college|tvet|campus|centre", college_str, re.I)

                    colleges_table.append({
                        "college_id": c_id,
                        "college_name_raw": college_str,
                        "college_name": Normalizer.clean_unicode(college_str),
                        "is_variant_flag": is_variant,
                    })
                else:
                    c_id = college_name_to_id[c_key]

                junction_table.append({
                    "saqa_id": saqa_id,
                    "college_id": c_id,
                    "page_number": page_num,
                })

            if "dspp" in title_raw.lower() or "centre of specialisation" in title_raw.lower():
                dspp_table.append({
                    "saqa_id": saqa_id,
                    "qualification_name": title_clean,
                    "centre_college_name": colleges_raw,
                    "page_number": page_num,
                })

        return {
            "qualifications": qualifications_table,
            "colleges": colleges_table,
            "qualification_colleges": junction_table,
            "dspp_centres_of_specialisation": dspp_table,
            "review_required": review_required_table,
        }
