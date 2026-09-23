import re
import unicodedata
from typing import Any, Tuple

class Normalizer:
    """Standardizes string values, whitespace, unicode, identifiers, and null tokens while preserving raw provenance."""

    NULL_TOKENS = {
        "", "n/a", "na", "null", "none", "-", "--", "nil", "unknown", "undefined", "#n/a", "nan"
    }

    LIGATURES = {
        "ﬁ": "fi",
        "ﬂ": "fl",
        "ﬀ": "ff",
        "ﬃ": "ffi",
        "ﬄ": "ffl",
        "œ": "oe",
        "æ": "ae",
    }

    SA_PROVINCES = {
        "gp": "Gauteng",
        "gau": "Gauteng",
        "gauteng": "Gauteng",
        "kzn": "KwaZulu-Natal",
        "kwazulu-natal": "KwaZulu-Natal",
        "wc": "Western Cape",
        "western cape": "Western Cape",
        "ec": "Eastern Cape",
        "eastern cape": "Eastern Cape",
        "fs": "Free State",
        "free state": "Free State",
        "mp": "Mpumalanga",
        "mpu": "Mpumalanga",
        "mpumalanga": "Mpumalanga",
        "lp": "Limpopo",
        "lim": "Limpopo",
        "limpopo": "Limpopo",
        "nw": "North West",
        "north west": "North West",
        "nc": "Northern Cape",
        "northern cape": "Northern Cape",
        "national": "National",
    }

    @classmethod
    def clean_unicode(cls, text: str) -> str:
        if not text:
            return ""
        for zw in ["\u200b", "\u200c", "\u200d", "\ufeff", "\u00ad"]:
            text = text.replace(zw, "")
        for lig, repl in cls.LIGATURES.items():
            text = text.replace(lig, repl)
        text = unicodedata.normalize("NFKC", text)
        text = text.replace("\u00a0", " ")
        text = text.replace("“", '"').replace("”", '"')
        text = text.replace("‘", "'").replace("’", "'")
        text = text.replace("–", "-").replace("—", "-")
        return text

    @classmethod
    def normalize_value(cls, raw: Any, field_name: str = "") -> Tuple[Any, bool]:
        if raw is None:
            return None, False

        val_str = str(raw)
        cleaned = cls.clean_unicode(val_str)
        cleaned = re.sub(r"[\r\n\t]+", " ", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()

        # Check for null representations
        if cleaned.lower() in cls.NULL_TOKENS:
            return None, (raw is not None and str(raw).strip() != "")

        # Preserve leading zeros for specific ID / code columns (e.g. saqa_id, ofo_code, postal_code)
        is_code_field = any(term in field_name.lower() for term in ["id", "code", "ofo", "saqa"])
        if is_code_field and re.match(r"^0\d+$", cleaned):
            return cleaned, (cleaned != str(raw))

        # Check if integer
        if re.match(r"^-?\d+$", cleaned) and not is_code_field:
            try:
                num = int(cleaned)
                return num, (str(raw) != cleaned)
            except ValueError:
                pass

        # Check if float
        if re.match(r"^-?\d+\.\d+$", cleaned) and not is_code_field:
            try:
                num = float(cleaned)
                return num, (str(raw) != cleaned)
            except ValueError:
                pass

        # Check boolean
        if cleaned.lower() in ["yes", "true", "y"]:
            return True, (str(raw) != "True")
        if cleaned.lower() in ["no", "false", "n"]:
            return False, (str(raw) != "False")

        # SA Province normalization
        if "prov" in field_name.lower() or "region" in field_name.lower():
            prov_match = cls.SA_PROVINCES.get(cleaned.lower())
            if prov_match:
                return prov_match, (prov_match != cleaned)

        return cleaned, (cleaned != str(raw))

    @classmethod
    def normalize_record(cls, data: dict) -> Tuple[dict, dict]:
        """
        Normalizes a dictionary of field values.
        Returns: (normalized_data, raw_data)
        """
        normalized = {}
        raw_copy = {}
        for k, v in data.items():
            raw_copy[k] = v
            norm_val, _ = cls.normalize_value(v, k)
            normalized[k] = norm_val
        return normalized, raw_copy
