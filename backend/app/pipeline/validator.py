import re
from typing import List, Dict, Any, Tuple

class Validator:
    """Rule-based data validation engine enforcing schema constraints and integrity."""

    @classmethod
    def validate_record(
        cls,
        data: Dict[str, Any],
        schema_columns: List[Dict[str, Any]],
        row_index: int,
    ) -> List[Dict[str, Any]]:
        issues: List[Dict[str, Any]] = []

        for col in schema_columns:
            name = col.get("name")
            dtype = col.get("type", "string")
            is_required = col.get("required", False)
            val = data.get(name)

            # 1. Required check
            if is_required and (val is None or str(val).strip() == ""):
                issues.append({
                    "row_index": row_index,
                    "column_name": name,
                    "rule_name": f"required_{name}",
                    "severity": "error",
                    "message": f"Required field '{name}' is missing or empty.",
                    "raw_value": str(val) if val is not None else None,
                })
                continue

            if val is None or str(val).strip() == "":
                continue

            val_str = str(val).strip()

            # 2. SAQA ID pattern check
            if "saqa" in name.lower():
                if not re.match(r"^\d{4,7}$", val_str):
                    issues.append({
                        "row_index": row_index,
                        "column_name": name,
                        "rule_name": "saqa_id_format",
                        "severity": "error",
                        "message": f"Invalid SAQA ID '{val_str}'. Expected 4 to 7 numeric digits.",
                        "raw_value": val_str,
                    })

            # 3. OFO Code pattern check
            if "ofo" in name.lower():
                if not re.match(r"^\d{4,6}$", val_str):
                    issues.append({
                        "row_index": row_index,
                        "column_name": name,
                        "rule_name": "ofo_code_format",
                        "severity": "error",
                        "message": f"Invalid OFO code '{val_str}'. Expected 4 to 6 numeric digits.",
                        "raw_value": val_str,
                    })

            # 4. NQF Level range check (1 to 10)
            # Only apply to NQF level columns, NOT NQF sub-framework text columns (e.g., nqf_sub_framework, nqf_sub_framewo_rk)
            if ("nqf_level" in name.lower() or name.lower() == "nqf") and not any(term in name.lower() for term in ["sub", "framework", "type", "desc"]):
                try:
                    # extract digits if any (e.g. "Level 4" -> 4)
                    match = re.search(r"\d+", val_str)
                    if match:
                        nqf_val = int(match.group(0))
                        if not (1 <= nqf_val <= 10):
                            issues.append({
                                "row_index": row_index,
                                "column_name": name,
                                "rule_name": "nqf_level_range",
                                "severity": "error",
                                "message": f"NQF Level {nqf_val} is outside allowed range (1 to 10).",
                                "raw_value": val_str,
                            })
                    else:
                        issues.append({
                            "row_index": row_index,
                            "column_name": name,
                            "rule_name": "nqf_level_numeric",
                            "severity": "warning",
                            "message": f"Could not parse numeric NQF level from '{val_str}'.",
                            "raw_value": val_str,
                        })
                except Exception:
                    pass

            # 5. Type validation
            if dtype == "integer":
                try:
                    int(str(val))
                except ValueError:
                    issues.append({
                        "row_index": row_index,
                        "column_name": name,
                        "rule_name": "type_integer",
                        "severity": "warning",
                        "message": f"Value '{val_str}' cannot be parsed as integer.",
                        "raw_value": val_str,
                    })
            elif dtype == "float":
                try:
                    float(str(val))
                except ValueError:
                    issues.append({
                        "row_index": row_index,
                        "column_name": name,
                        "rule_name": "type_float",
                        "severity": "warning",
                        "message": f"Value '{val_str}' cannot be parsed as float.",
                        "raw_value": val_str,
                    })

        return issues

    @classmethod
    def calculate_quality_score(
        cls,
        total_records: int,
        error_count: int,
        warning_count: int
    ) -> float:
        if total_records == 0:
            return 100.0
        # Errors deduct 1.5% per error up to 100%, warnings deduct 0.5%
        penalty = (error_count * 1.5 + warning_count * 0.5) / total_records * 100
        score = max(0.0, min(100.0, 100.0 - penalty))
        return round(score, 1)
