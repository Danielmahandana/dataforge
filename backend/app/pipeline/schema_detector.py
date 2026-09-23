import re
from typing import List, Dict, Any, Tuple

class SchemaDetector:
    """Infers database-ready column names, types, and constraints from extracted tables."""

    @staticmethod
    def to_snake_case(name: str) -> str:
        if not name:
            return "unnamed_column"
        cleaned = re.sub(r"[^\w\s-]", "", name).strip()
        cleaned = re.sub(r"[-\s]+", "_", cleaned)
        s1 = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", cleaned)
        snake = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s1).lower()
        snake = re.sub(r"_+", "_", snake).strip("_")
        return snake or "column"

    @classmethod
    def infer_column_type(cls, values: List[Any]) -> str:
        non_nulls = [v for v in values if v is not None and str(v).strip() != ""]
        if not non_nulls:
            return "string"

        total = len(non_nulls)
        int_count = 0
        float_count = 0
        bool_count = 0

        for v in non_nulls:
            s = str(v).strip()
            if isinstance(v, bool) or s.lower() in ["true", "false", "yes", "no"]:
                bool_count += 1
            elif isinstance(v, int) or (s.lstrip("-").isdigit() and not s.startswith("0") or s == "0"):
                int_count += 1
            elif isinstance(v, float) or re.match(r"^-?\d+\.\d+$", s):
                float_count += 1

        if bool_count / total >= 0.85:
            return "boolean"
        if int_count / total >= 0.85:
            return "integer"
        if (int_count + float_count) / total >= 0.85:
            return "float"

        return "string"

    @classmethod
    def detect_columns(cls, raw_headers: List[str], sample_rows: List[List[Any]]) -> List[Dict[str, Any]]:
        columns: List[Dict[str, Any]] = []
        seen_names: Dict[str, int] = {}

        for idx, raw_header in enumerate(raw_headers):
            original = raw_header.strip() if raw_header else f"Column_{idx+1}"
            snake_name = cls.to_snake_case(original)

            # Ensure uniqueness
            if snake_name in seen_names:
                seen_names[snake_name] += 1
                final_name = f"{snake_name}_{seen_names[snake_name]}"
            else:
                seen_names[snake_name] = 1
                final_name = snake_name

            # Extract sample values for this column index
            col_values = [row[idx] for row in sample_rows if idx < len(row)]
            inferred_type = cls.infer_column_type(col_values)

            # Special column handling for code fields
            if any(term in final_name for term in ["saqa", "ofo", "code", "id"]):
                inferred_type = "string"

            is_required = any(term in final_name for term in ["id", "code", "title", "name"])

            columns.append({
                "name": final_name,
                "original_name": original,
                "type": inferred_type,
                "required": is_required,
                "description": f"Field extracted from {original}"
            })

        return columns
