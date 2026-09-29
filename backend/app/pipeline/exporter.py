import io
import json
from typing import List, Dict, Any, Optional
import pandas as pd


class DatasetExporter:
    """Exports relational datasets and Palantir-style metadata artifacts (data_dictionary, provenance, manifest, review_required)."""

    @classmethod
    def export(
        cls,
        records: List[Dict[str, Any]],
        format: str = "csv",
        include_provenance: bool = True,
        include_curation: bool = True,
        selected_columns: Optional[List[str]] = None,
        export_state: str = "NORMALIZED_DATASET",  # RAW_EXTRACTION, NORMALIZED_DATASET, CURATED_DATASET, REVIEW_DATASET, AUDIT_PACKAGE
    ) -> bytes:
        flat_records = []
        for r in records:
            row_data = dict(r.get("data", {}))
            if include_provenance:
                prov = r.get("provenance", {})
                row_data["_prov_doc"] = prov.get("document_name", "")
                row_data["_prov_page"] = prov.get("page_number", "")
                row_data["_prov_table"] = r.get("source_table") or prov.get("source_table", "")
                row_data["_prov_section"] = r.get("source_section") or prov.get("source_section", "")
                row_data["_prov_confidence"] = r.get("confidence_score", 0.85)
                row_data["_prov_status"] = r.get("status", "valid")

            if include_curation:
                cur_dec = r.get("curation_decision", "unprocessed")
                row_data["_curation_decision"] = cur_dec
                row_data["_curation_reason"] = r.get("curation_reason", "")
                multi_c = r.get("multi_confidence") or {}
                if isinstance(multi_c, dict):
                    # Never report 1.0 confidence for unprocessed records
                    cur_conf = multi_c.get("curation")
                    if cur_dec.lower() == "unprocessed" and (cur_conf is None or cur_conf == 1.0):
                        row_data["_curation_confidence"] = None
                    else:
                        row_data["_curation_confidence"] = cur_conf

                derived = r.get("derived_data") or {}
                if isinstance(derived, dict) and "derived_chambers" in derived:
                    chambers = derived.get("derived_chambers", [])
                    row_data["_derived_chambers"] = "; ".join(chambers) if isinstance(chambers, list) else str(chambers)

            if selected_columns:
                row_data = {
                    k: v for k, v in row_data.items()
                    if k in selected_columns or k.startswith("_prov_") or k.startswith("_curation_") or k.startswith("_derived_")
                }

            flat_records.append(row_data)

        return cls.export_raw_dicts(flat_records, format=format)

    @classmethod
    def export_raw_dicts(cls, records: List[Dict[str, Any]], format: str = "csv") -> bytes:
        """Export any list of dictionaries directly into CSV, JSON, or Excel bytes."""
        df = pd.DataFrame(records if records else [{}])

        fmt = format.lower().strip()
        if fmt == "csv":
            return df.to_csv(index=False).encode("utf-8")
        elif fmt == "json":
            return df.to_json(orient="records", indent=2).encode("utf-8")
        elif fmt in ["xlsx", "excel"]:
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                df.to_excel(writer, index=False, sheet_name="DataForge_Dataset")
            return output.getvalue()
        else:
            raise ValueError(f"Unsupported export format: {format}")

    @classmethod
    def generate_data_dictionary(cls, columns_info: List[Dict[str, Any]]) -> bytes:
        """Generates column-level data dictionary artifact."""
        dict_records = []
        for col in columns_info:
            dict_records.append({
                "column_name": col.get("name"),
                "original_header": col.get("original_name"),
                "inferred_data_type": col.get("type", "string"),
                "is_mandatory": "YES" if col.get("required") else "NO",
                "sample_values": col.get("sample_values", ""),
                "description": col.get("description", ""),
            })

        df = pd.DataFrame(dict_records if dict_records else [{}])
        return df.to_csv(index=False).encode("utf-8")

    @classmethod
    def create_export_bundle(
        cls,
        dataset_bytes: bytes,
        dataset_filename: str,
        knowledge_text: str,
        knowledge_filename: str,
    ) -> bytes:
        """Packages the dataset export and its domain knowledge text artifact into a single ZIP archive."""
        import zipfile
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr(dataset_filename, dataset_bytes)
            zf.writestr(knowledge_filename, knowledge_text.encode("utf-8"))
        return buffer.getvalue()

