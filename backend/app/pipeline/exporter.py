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
        selected_columns: Optional[List[str]] = None,
    ) -> bytes:
        flat_records = []
        for r in records:
            row_data = dict(r.get("data", {}))
            if include_provenance:
                prov = r.get("provenance", {})
                row_data["_prov_doc"] = prov.get("document_name", "")
                row_data["_prov_page"] = prov.get("page_number", "")
                row_data["_prov_confidence"] = r.get("confidence_score", 1.0)
                row_data["_prov_status"] = r.get("status", "valid")

            if selected_columns:
                row_data = {k: v for k, v in row_data.items() if k in selected_columns or k.startswith("_prov_")}

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
                "data_type": col.get("type"),
                "required": col.get("required", False),
                "description": col.get("description", ""),
            })
        return cls.export_raw_dicts(dict_records, format="csv")

    @classmethod
    def generate_provenance_manifest(cls, dataset_info: Dict[str, Any], documents_info: List[Dict[str, Any]]) -> bytes:
        """Generates source lineage and document provenance artifact."""
        prov_records = []
        for doc in documents_info:
            prov_records.append({
                "dataset_name": dataset_info.get("name"),
                "document_id": doc.get("id"),
                "filename": doc.get("filename"),
                "doc_type": doc.get("doc_type"),
                "page_count": doc.get("page_count"),
                "extraction_method": dataset_info.get("schema_name"),
            })
        return cls.export_raw_dicts(prov_records, format="csv")

    @classmethod
    def generate_extraction_manifest_json(cls, job_metrics: Dict[str, Any], notes: Optional[str] = None) -> bytes:
        """Generates full extraction execution manifest JSON artifact."""
        manifest = {
            "platform": "Darkroom DataForge v2.0",
            "extraction_timestamp": job_metrics.get("timestamp"),
            "metrics": job_metrics,
            "notes": notes or "Extraction execution completed with full provenance and zero factual mutation.",
        }
        return json.dumps(manifest, indent=2).encode("utf-8")
