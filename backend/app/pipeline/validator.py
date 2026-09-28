import re
from typing import List, Dict, Any, Optional, Tuple


class RequiredFieldValidator:
    """Validates that mandatory fields are present and non-empty."""

    @classmethod
    def validate(cls, field_name: str, value: Any, row_index: int) -> Optional[Dict[str, Any]]:
        if value is None or str(value).strip() == "":
            return {
                "row_index": row_index,
                "column_name": field_name,
                "rule_name": f"required_{field_name}",
                "severity": "error",
                "message": f"Required field '{field_name}' is missing or empty.",
                "raw_value": str(value) if value is not None else None,
            }
        return None


class IdentifierValidator:
    """Validates alphanumeric identifiers, SAQA IDs, and registration codes."""

    @classmethod
    def validate_saqa_id(cls, field_name: str, val_str: str, row_index: int) -> Optional[Dict[str, Any]]:
        if not re.match(r"^\d{4,7}$", val_str):
            return {
                "row_index": row_index,
                "column_name": field_name,
                "rule_name": "saqa_id_format",
                "severity": "error",
                "message": f"Invalid SAQA ID '{val_str}'. Expected 4 to 7 numeric digits.",
                "raw_value": val_str,
            }
        return None


class OFOCodeValidator:
    """Validates South African Organising Framework for Occupations (OFO) codes.
    Accepts standard 4-digit unit codes, 6-digit specific codes, or release-prefixed codes (e.g. 2021-112101)."""

    @classmethod
    def validate(cls, field_name: str, val_str: str, row_index: int) -> Optional[Dict[str, Any]]:
        # Match either 2021-112101 or 112101 or 1121
        if not re.match(r"^(?:20\d{2}-)?\d{4,6}$", val_str):
            return {
                "row_index": row_index,
                "column_name": field_name,
                "rule_name": "ofo_code_format",
                "severity": "error",
                "message": f"Invalid OFO code '{val_str}'. Expected 4 to 6 numeric digits (optionally prefixed by release year e.g. 2021-112101).",
                "raw_value": val_str,
            }
        return None


class NumericRangeValidator:
    """Validates numeric ranges including NQF levels, percentages, and ranks."""

    @classmethod
    def validate_nqf_level(cls, field_name: str, val_str: str, row_index: int) -> Optional[Dict[str, Any]]:
        if any(term in field_name.lower() for term in ["sub", "framework", "type", "desc"]):
            return None
        match = re.search(r"\d+", val_str)
        if match:
            nqf_val = int(match.group(0))
            if not (1 <= nqf_val <= 10):
                return {
                    "row_index": row_index,
                    "column_name": field_name,
                    "rule_name": "nqf_level_range",
                    "severity": "error",
                    "message": f"NQF Level {nqf_val} is outside allowed range (1 to 10).",
                    "raw_value": val_str,
                }
        else:
            return {
                "row_index": row_index,
                "column_name": field_name,
                "rule_name": "nqf_level_numeric",
                "severity": "warning",
                "message": f"Could not parse numeric NQF level from '{val_str}'.",
                "raw_value": val_str,
            }
        return None


class DateValidator:
    """Validates date formats."""

    @classmethod
    def validate_year(cls, field_name: str, val_str: str, row_index: int) -> Optional[Dict[str, Any]]:
        if not re.match(r"^(?:19|20)\d{2}$", val_str):
            return {
                "row_index": row_index,
                "column_name": field_name,
                "rule_name": "year_format",
                "severity": "warning",
                "message": f"Value '{val_str}' is not a valid 4-digit calendar year.",
                "raw_value": val_str,
            }
        return None


class EnumValidator:
    """Validates allowed values for enumerated fields (provinces, chambers, decision states)."""

    VALID_PROVINCES = [
        "gauteng", "mpumalanga", "kwazulu-natal", "western cape",
        "eastern cape", "limpopo", "free state", "north west", "northern cape", "national"
    ]

    @classmethod
    def validate_province(cls, field_name: str, val_str: str, row_index: int) -> Optional[Dict[str, Any]]:
        if val_str.lower() not in cls.VALID_PROVINCES:
            return {
                "row_index": row_index,
                "column_name": field_name,
                "rule_name": "province_enum",
                "severity": "warning",
                "message": f"Unknown South African province '{val_str}'.",
                "raw_value": val_str,
            }
        return None


class Validator:
    """Schema-aware data validation engine enforcing field semantics, structural constraints, and integrity."""

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
            if is_required:
                req_issue = RequiredFieldValidator.validate(name, val, row_index)
                if req_issue:
                    issues.append(req_issue)
                    continue

            if val is None or str(val).strip() == "":
                continue

            val_str = str(val).strip()

            # 2. SAQA ID check
            if "saqa" in name.lower():
                saqa_issue = IdentifierValidator.validate_saqa_id(name, val_str, row_index)
                if saqa_issue:
                    issues.append(saqa_issue)

            # 3. OFO Code check
            if "ofo" in name.lower() or name.lower() == "code":
                ofo_issue = OFOCodeValidator.validate(name, val_str, row_index)
                if ofo_issue:
                    issues.append(ofo_issue)

            # 4. NQF Level check
            if "nqf_level" in name.lower() or name.lower() == "nqf":
                nqf_issue = NumericRangeValidator.validate_nqf_level(name, val_str, row_index)
                if nqf_issue:
                    issues.append(nqf_issue)

            # 5. Province check
            if "province" in name.lower():
                prov_issue = EnumValidator.validate_province(name, val_str, row_index)
                if prov_issue:
                    issues.append(prov_issue)

            # 6. Type validation
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
