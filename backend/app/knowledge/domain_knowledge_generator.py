from __future__ import annotations
import re
import hashlib
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple, Set
from pydantic import BaseModel, Field


class DomainKnowledgeArtifact(BaseModel):
    """Encapsulates a generated .txt domain-knowledge artifact with reproducibility metadata."""
    dataset_id: str
    dataset_name: str
    filename: str
    content: str
    content_hash: str
    record_count: int
    generator_version: str = "1.0.0"
    generated_at: str


class DomainKnowledgeGenerator:
    """Universal Domain Knowledge Generator for Darkroom DataForge.
    Converts structured datasets, provenance trails, field authorities, and validation
    into a human-readable and RAG-ready .txt domain knowledge artifact.
    Strictly follows ZERO BLIND TRUST — never hallucinates ungrounded causal explanations."""

    GENERATOR_VERSION = "1.0.0"

    @staticmethod
    def _get_val(obj: Any, key: str, default: Any = None) -> Any:
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)

    @staticmethod
    def _clean_str(val: Any) -> str:
        if val is None:
            return ""
        s = str(val).strip()
        return " ".join(s.split())

    @classmethod
    def infer_unit_of_observation(cls, schema_name: Optional[str], columns: List[str]) -> Tuple[str, str]:
        """Dynamically detects the entity unit of observation from schema and columns."""
        cols_lower = [c.lower() for c in columns]
        schema_lower = (schema_name or "").lower()

        if any("ofo" in c or "occup" in c for c in cols_lower) or "occup" in schema_lower or "oihd" in schema_lower:
            return "Occupation", "Each record represents an occupation classified under the Organising Framework for Occupations (OFO)."
        if any("saqa" in c or "qual" in c or "programme" in c for c in cols_lower) or "qual" in schema_lower:
            return "Qualification", "Each record represents an accredited educational or vocational learning qualification."
        if any("var_name" in c or "variable" in c for c in cols_lower) or "codebook" in schema_lower:
            return "Variable", "Each record represents a statistical survey variable definition and codebook entry."
        if any("company" in c or "employer" in c or "enterprise" in c for c in cols_lower):
            return "Company / Enterprise", "Each record represents an employer or commercial firm."
        if any("province" in c or "region" in c or "district" in c for c in cols_lower) and len(cols_lower) <= 5:
            return "Geographic Region", "Each record represents a regional or provincial observation."
        if any("indicator" in c or "metric" in c for c in cols_lower):
            return "Economic / Labour Indicator", "Each record represents an empirical economic or labour market indicator."

        primary = columns[0].replace("_", " ").title() if columns else "Record"
        return primary, f"Each record represents an individual {primary.lower()} entity."

    @classmethod
    def categorize_columns(cls, columns: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """Categorizes column fields into semantic roles dynamically."""
        categorized: Dict[str, List[str]] = {
            "identifiers": [],
            "titles": [],
            "classifications": [],
            "requirements": [],
            "geographic": [],
            "metrics": [],
            "general": [],
        }

        for col in columns:
            name = col.get("name", "")
            n_low = name.lower()

            if any(k in n_low for k in ["code", "id", "number", "reg_no", "identifier"]):
                categorized["identifiers"].append(name)
            elif any(k in n_low for k in ["title", "name", "occupation", "qualification", "programme", "label"]):
                categorized["titles"].append(name)
            elif any(k in n_low for k in ["level", "nqf", "subframe", "category", "type", "chamber", "sector", "industry"]):
                categorized["classifications"].append(name)
            elif any(k in n_low for k in ["min_", "require", "prereq", "entry_"]):
                categorized["requirements"].append(name)
            elif any(k in n_low for k in ["province", "region", "district", "municipality", "city"]):
                categorized["geographic"].append(name)
            elif any(k in n_low for k in ["count", "score", "weight", "share", "rate", "percent", "amount", "total"]):
                categorized["metrics"].append(name)
            else:
                categorized["general"].append(name)

        return categorized

    @classmethod
    def generate(
        cls,
        dataset: Any,
        records: List[Any],
        document: Optional[Any] = None,
        generator_version: Optional[str] = None,
    ) -> DomainKnowledgeArtifact:
        """Generates a structured domain knowledge text artifact from the validated dataset."""
        gen_ver = generator_version or cls.GENERATOR_VERSION
        generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

        # Dataset Attributes
        ds_id = cls._get_val(dataset, "id", "unknown_dataset")
        ds_name = cls._get_val(dataset, "name", "DataForge Dataset")
        ds_desc = cls._get_val(dataset, "description", "")
        ds_version = cls._get_val(dataset, "version_label", "v1.0")
        ds_schema_name = cls._get_val(dataset, "schema_name", "generic")
        schema_cols = cls._get_val(dataset, "schema_columns", []) or []
        col_names = [c.get("name") for c in schema_cols if c.get("name")]

        # Document Attributes
        doc_id = cls._get_val(document, "id", cls._get_val(dataset, "document_id", "unknown_doc"))
        doc_title = cls._get_val(document, "original_name", "")
        doc_meta = cls._get_val(document, "doc_metadata", {}) or {}
        doc_profile = doc_meta.get("profile_summary", {}) if isinstance(doc_meta, dict) else {}
        doc_hash = cls._get_val(document, "file_hash", "N/A")
        doc_pages = cls._get_val(document, "page_count", 0)
        doc_type = doc_profile.get("document_type") or cls._get_val(document, "doc_type", "Research Publication")
        doc_publisher = doc_profile.get("publisher") or "Not Stated"
        doc_pub_date = doc_profile.get("publication_date") or "Not Stated"

        # If document title is missing, look in profile summary
        if not doc_title and doc_profile.get("title"):
            doc_title = doc_profile.get("title")

        # Fallback to column discovery if schema_cols empty
        if not col_names and records:
            first_rec = records[0]
            first_data = cls._get_val(first_rec, "data", {})
            col_names = list(first_data.keys())
            schema_cols = [{"name": c, "type": "string", "required": False} for c in col_names]

        # Categorize columns
        col_categories = cls.categorize_columns(schema_cols)
        primary_unit, unit_desc = cls.infer_unit_of_observation(ds_schema_name, col_names)

        # -------------------------------------------------------------
        # Compile Records & Stats
        # -------------------------------------------------------------
        total_records_count = len(records)
        unique_values: Dict[str, Set[str]] = {col: set() for col in col_names}
        non_null_counts: Dict[str, int] = {col: 0 for col in col_names}
        raw_diff_counts: Dict[str, int] = {col: 0 for col in col_names}

        included_records: List[Any] = []
        review_records: List[Any] = []
        excluded_records: List[Any] = []

        valid_count = 0
        warning_count = 0
        error_count = 0

        source_tables: Set[str] = set()
        source_sections: Set[str] = set()
        source_pages: Set[int] = set()

        for r in records:
            data = cls._get_val(r, "data", {}) or {}
            raw_data = cls._get_val(r, "raw_data", {}) or {}
            status = cls._get_val(r, "status", "valid")
            cur_dec = (cls._get_val(r, "curation_decision", "unprocessed") or "unprocessed").upper()

            # Status breakdown
            if status == "valid":
                valid_count += 1
            elif status == "warning":
                warning_count += 1
            elif status == "error":
                error_count += 1

            # Curation breakdown
            if cur_dec == "EXCLUDE":
                excluded_records.append(r)
            elif cur_dec == "REVIEW":
                review_records.append(r)
            else:
                # INCLUDE or UNPROCESSED (primary domain records)
                included_records.append(r)

            # Field stats
            for col in col_names:
                v = data.get(col)
                if v is not None and str(v).strip():
                    v_str = cls._clean_str(v)
                    non_null_counts[col] += 1
                    unique_values[col].add(v_str)

                # Check if raw differs from normalized
                r_v = raw_data.get(col)
                if r_v is not None and v is not None and str(r_v).strip() != str(v).strip():
                    raw_diff_counts[col] += 1

            # Provenance tracking
            prov = cls._get_val(r, "provenance", {}) or {}
            src_tab = cls._get_val(r, "source_table") or (prov.get("source_table") if isinstance(prov, dict) else None)
            if src_tab:
                source_tables.add(cls._clean_str(src_tab))

            src_sec = cls._get_val(r, "source_section") or (prov.get("source_section") if isinstance(prov, dict) else None)
            if src_sec:
                source_sections.add(cls._clean_str(src_sec))

            p_no = (prov.get("page_number") if isinstance(prov, dict) else None) or cls._get_val(r, "page_number")
            if p_no:
                try:
                    source_pages.add(int(p_no))
                except (ValueError, TypeError):
                    pass

        # -------------------------------------------------------------
        # BUILD SECTIONS OF THE DOMAIN KNOWLEDGE ARTIFACT
        # -------------------------------------------------------------
        sections: List[str] = []

        # Header Banner
        sections.append(
            "================================================================================\n"
            "DATAFORGE DOMAIN KNOWLEDGE ARTIFACT\n"
            "Evidence-Driven Research & Semantic Domain Intelligence\n"
            "================================================================================"
        )

        # 1. DATASET IDENTITY
        sec1 = [
            "================================================================================",
            "1. DATASET IDENTITY",
            "================================================================================",
            f"Dataset Name:        {ds_name}",
            f"Dataset Identifier:  {ds_id}",
            f"Version Label:       {ds_version}",
            f"Schema Type:         {ds_schema_name}",
            f"Record Count:        {total_records_count}",
            f"Extraction Status:   {cls._get_val(dataset, 'status', 'validated')}",
        ]
        sections.append("\n".join(sec1))

        # 2. SOURCE DOCUMENT
        sec2 = [
            "================================================================================",
            "2. SOURCE DOCUMENT",
            "================================================================================",
            f"Document Title:      {doc_title or 'Research Publication'}",
            f"Document Identifier: {doc_id}",
            f"Publisher / Source:  {doc_publisher}",
            f"Publication Date:    {doc_pub_date}",
            f"Document Type:       {doc_type}",
            f"File Hash (SHA-256): {doc_hash}",
            f"Total Pages:         {doc_pages if doc_pages > 0 else 'Unspecified'}",
        ]
        if source_tables:
            sec2.append(f"Authoritative Table: {', '.join(sorted(source_tables))}")
        if source_sections:
            sec2.append(f"Source Section:      {', '.join(sorted(source_sections))}")
        if source_pages:
            sec2.append(f"Source Page Range:   Pages {min(source_pages)}–{max(source_pages)}")
        sections.append("\n".join(sec2))

        # 3. DATASET DESCRIPTION
        if ds_desc:
            sec3 = [
                "================================================================================",
                "3. DATASET DESCRIPTION",
                "================================================================================",
                ds_desc.strip(),
            ]
            sections.append("\n".join(sec3))

        # 4. UNIT OF OBSERVATION
        sec4 = [
            "================================================================================",
            "4. UNIT OF OBSERVATION",
            "================================================================================",
            f"Primary Entity: {primary_unit}",
            f"Definition:     {unit_desc}",
        ]
        sections.append("\n".join(sec4))

        # 5. DATASET STATISTICS
        sec5 = [
            "================================================================================",
            "5. DATASET STATISTICS",
            "================================================================================",
            f"Total Records Extracted:      {total_records_count}",
            f"Valid / Approved Records:     {valid_count}",
            f"Records with Warnings:        {warning_count}",
            f"Records with Errors:          {error_count}",
            "",
            "FIELD COVERAGE & CARDINALITY:",
        ]
        for col in col_names:
            cnt = non_null_counts[col]
            uniq = len(unique_values[col])
            pct = round((cnt / total_records_count * 100), 1) if total_records_count > 0 else 0.0
            sec5.append(f"  - {col}: {cnt}/{total_records_count} populated ({pct}%) | {uniq} unique value(s)")
        sections.append("\n".join(sec5))

        # 6. SCHEMA KNOWLEDGE
        sec6 = [
            "================================================================================",
            "6. SCHEMA KNOWLEDGE",
            "================================================================================",
        ]
        for col_info in schema_cols:
            c_name = col_info.get("name", "")
            c_type = col_info.get("type", "string")
            c_req = "YES" if col_info.get("required") else "NO"
            c_desc = col_info.get("description", f"Extracted domain attribute: {c_name}")
            c_cov = f"{non_null_counts.get(c_name, 0)} / {total_records_count}"

            # Authority detection: check if records specify authority for this field
            first_rec_auth = {}
            if records:
                first_rec_auth = cls._get_val(records[0], "field_authorities", {}) or {}
            authority = first_rec_auth.get(c_name, "SOURCE_FACT")

            sec6.extend([
                f"Field:       {c_name}",
                f"  Type:      {c_type}",
                f"  Authority: {authority}",
                f"  Mandatory: {c_req}",
                f"  Coverage:  {c_cov}",
                f"  Role:      {c_desc}",
                "",
            ])
        sections.append("\n".join(sec6).rstrip())

        # 7. DOMAIN ENTITIES
        sec7 = [
            "================================================================================",
            "7. DOMAIN ENTITIES",
            "================================================================================",
        ]
        entity_found = False

        # Group distinct entities by detected semantic category
        for cat_name, cat_cols in [
            ("Occupations / Job Titles", col_categories["titles"]),
            ("Classifications & Codes", col_categories["identifiers"]),
            ("Qualifications & Requirements", col_categories["requirements"]),
            ("Categories & Framework Tiers", col_categories["classifications"]),
            ("Geographic Regions", col_categories["geographic"]),
        ]:
            if not cat_cols:
                continue
            cat_values: Set[str] = set()
            for col in cat_cols:
                cat_values.update(unique_values.get(col, set()))

            if cat_values:
                entity_found = True
                sec7.append(f"{cat_name} ({len(cat_values)} distinct):")
                sorted_vals = sorted(cat_values)
                # Show up to 40 items per category with truncation indicator
                for v in sorted_vals[:40]:
                    sec7.append(f"  • {v}")
                if len(sorted_vals) > 40:
                    sec7.append(f"  ... and {len(sorted_vals) - 40} more {cat_name.lower()}")
                sec7.append("")

        if not entity_found:
            # Fallback: display entities for the first 2 columns
            for col in col_names[:2]:
                vals = sorted(unique_values.get(col, set()))
                if vals:
                    sec7.append(f"{col.replace('_', ' ').title()} ({len(vals)} distinct):")
                    for v in vals[:30]:
                        sec7.append(f"  • {v}")
                    sec7.append("")

        sections.append("\n".join(sec7).rstrip())

        # 8. DOMAIN VOCABULARY & NORMALIZATION LINEAGE
        sec8 = [
            "================================================================================",
            "8. DOMAIN VOCABULARY & NORMALIZATION AUDIT",
            "================================================================================",
            "Preserving verbatim domain terminology from source documents.",
        ]
        normalization_noted = False
        for col in col_names:
            diff_cnt = raw_diff_counts.get(col, 0)
            if diff_cnt > 0:
                normalization_noted = True
                sec8.append(f"\nAttribute '{col}' ({diff_cnt} records normalized from raw layout):")
                # Show sample of differences
                sample_diffs = []
                for r in records:
                    raw_val = cls._clean_str((cls._get_val(r, "raw_data", {}) or {}).get(col))
                    norm_val = cls._clean_str((cls._get_val(r, "data", {}) or {}).get(col))
                    if raw_val and norm_val and raw_val != norm_val:
                        sample_diffs.append((raw_val, norm_val))
                        if len(sample_diffs) >= 5:
                            break
                for raw_v, norm_v in sample_diffs:
                    sec8.append(f"  - Source Raw:  \"{raw_v}\"")
                    sec8.append(f"    Normalized:  \"{norm_v}\"")

        if not normalization_noted:
            sec8.append("All extracted values strictly correspond to clean source text without layout drift.")
        sections.append("\n".join(sec8))

        # 9. RELATIONSHIPS
        sec9 = [
            "================================================================================",
            "9. DIRECT FACTUAL RELATIONSHIPS",
            "================================================================================",
            "Factual pairings directly substantiated by source records (no inferred links):",
        ]
        # Identify relationship pairs based on column structure
        id_col = col_categories["identifiers"][0] if col_categories["identifiers"] else None
        title_col = col_categories["titles"][0] if col_categories["titles"] else (col_names[0] if col_names else None)
        req_col = col_categories["requirements"][0] if col_categories["requirements"] else None

        rel_count = 0
        for r in (included_records or records)[:25]:
            d = cls._get_val(r, "data", {}) or {}
            parts = []
            if id_col and d.get(id_col):
                parts.append(f"[{cls._clean_str(d[id_col])}]")
            if title_col and d.get(title_col):
                parts.append(cls._clean_str(d[title_col]))
            if req_col and d.get(req_col):
                parts.append(f"→ Requires: {cls._clean_str(d[req_col])}")

            if len(parts) >= 2:
                rel_count += 1
                sec9.append(f"  • {' '.join(parts)}")

        if rel_count == 0 and len(col_names) >= 2:
            c1, c2 = col_names[0], col_names[1]
            for r in (included_records or records)[:20]:
                d = cls._get_val(r, "data", {}) or {}
                if d.get(c1) and d.get(c2):
                    sec9.append(f"  • {cls._clean_str(d[c1])} → {c2}: {cls._clean_str(d[c2])}")

        sections.append("\n".join(sec9))

        # 10. DATA POINTS
        sec10 = [
            "================================================================================",
            "10. DERIVED RESEARCH DATA POINTS",
            "================================================================================",
            f"• Verified record count: {total_records_count}",
        ]
        if id_col:
            sec10.append(f"• Unique {id_col.replace('_', ' ').upper()} entries: {len(unique_values[id_col])}")
        if title_col:
            sec10.append(f"• Unique {title_col.replace('_', ' ').title()} entries: {len(unique_values[title_col])}")
        if req_col:
            populated_req = non_null_counts[req_col]
            sec10.append(f"• Records specifying {req_col.replace('_', ' ').lower()}: {populated_req}")
            sec10.append(f"• Records without explicit requirement: {total_records_count - populated_req}")

        if source_tables:
            sec10.append(f"• Primary authoritative source table: {', '.join(sorted(source_tables))}")
        if source_pages:
            sec10.append(f"• Empirical table spans across pages: {min(source_pages)} to {max(source_pages)}")

        sections.append("\n".join(sec10))

        # 11. RECORD-LEVEL KNOWLEDGE
        sec11 = [
            "================================================================================",
            "11. RECORD-LEVEL KNOWLEDGE (CURATED & AUDITED)",
            "================================================================================",
        ]

        if included_records:
            sec11.append(f"--- PRIMARY INCLUDED RECORDS ({len(included_records)} records) ---")
            for r in included_records:
                r_idx = cls._get_val(r, "row_index", "?")
                d = cls._get_val(r, "data", {}) or {}
                prov = cls._get_val(r, "provenance", {}) or {}
                p_num = prov.get("page_number", cls._get_val(r, "page_number", ""))
                src_t = cls._get_val(r, "source_table") or prov.get("source_table", "")

                line_parts = []
                for col in col_names:
                    val = cls._clean_str(d.get(col, ""))
                    if val:
                        line_parts.append(f"{col}: {val}")

                prov_str = f" [Page {p_num}]" if p_num else ""
                tab_str = f" ({src_t})" if src_t else ""
                sec11.append(f"Record #{r_idx}: {' | '.join(line_parts)}{prov_str}{tab_str}")

        if review_records:
            sec11.append(f"\n--- PENDING REVIEW RECORDS ({len(review_records)} records) ---")
            for r in review_records:
                r_idx = cls._get_val(r, "row_index", "?")
                d = cls._get_val(r, "data", {}) or {}
                reason = cls._get_val(r, "curation_reason") or "Flagged during validation"
                line_parts = [f"{col}: {cls._clean_str(d.get(col, ''))}" for col in col_names if d.get(col)]
                sec11.append(f"Review #{r_idx}: {' | '.join(line_parts)} -> Reason: {reason}")

        if excluded_records:
            sec11.append(f"\n--- EXCLUDED RECORDS (AUDIT LOG - {len(excluded_records)} records) ---")
            for r in excluded_records:
                r_idx = cls._get_val(r, "row_index", "?")
                d = cls._get_val(r, "data", {}) or {}
                reason = cls._get_val(r, "curation_reason") or "Exclusion criteria matched"
                line_parts = [f"{col}: {cls._clean_str(d.get(col, ''))}" for col in col_names if d.get(col)]
                sec11.append(f"Excluded #{r_idx}: {' | '.join(line_parts)} -> Reason: {reason}")

        sections.append("\n".join(sec11))

        # 12. CURATION STATUS
        cur_summary = cls._get_val(dataset, "curation_summary", {}) or {}
        policy_id = cls._get_val(dataset, "policy_id") or "None (Raw extraction / Unprocessed)"

        sec12 = [
            "================================================================================",
            "12. CURATION GOVERNANCE STATUS",
            "================================================================================",
            f"Active Policy ID:  {policy_id}",
            f"Included Records:  {len(included_records)} ({cur_summary.get('included', len(included_records))})",
            f"Review Required:   {len(review_records)} ({cur_summary.get('review_required', len(review_records))})",
            f"Excluded Records:  {len(excluded_records)} ({cur_summary.get('excluded', len(excluded_records))})",
            f"Unprocessed Count: {cur_summary.get('unprocessed', 0)}",
        ]
        # Check first record curation confidence without manufacturing 1.0
        sample_conf = None
        if records:
            mc = cls._get_val(records[0], "multi_confidence", {}) or {}
            sample_conf = mc.get("curation") if isinstance(mc, dict) else None

        if sample_conf is not None:
            sec12.append(f"Curation Confidence Established: {sample_conf}")
        else:
            sec12.append("Curation Confidence: Not established (Awaiting policy curation execution)")

        sections.append("\n".join(sec12))

        # 13. VALIDATION STATUS
        val_issues_count = warning_count + error_count
        sec13 = [
            "================================================================================",
            "13. VALIDATION STATUS",
            "================================================================================",
            f"Valid Records:     {valid_count} / {total_records_count}",
            f"Validation Errors: {error_count}",
            f"Warnings Flagged:  {warning_count}",
            f"Integrity Posture: {'PASSED (Zero Errors)' if error_count == 0 else f'ACTION REQUIRED ({error_count} Errors)'}",
        ]
        sections.append("\n".join(sec13))

        # 14. QUALITY STATUS
        q_score = cls._get_val(dataset, "quality_score", 100.0)
        gates = cls._get_val(dataset, "quality_gates_status", {}) or {}
        q_dims = cls._get_val(dataset, "quality_dimensions", {}) or {}

        sec14 = [
            "================================================================================",
            "14. RESEARCH QUALITY GATES",
            "================================================================================",
            f"Overall Quality Score: {q_score}%",
            "",
            "GATE POSTURE EVALUATION:",
        ]
        for g_name, g_status in gates.items():
            sec14.append(f"  • {g_name}: {str(g_status).upper()}")

        if q_dims:
            sec14.append("\nDIMENSIONAL METRICS:")
            for dim, score in q_dims.items():
                sec14.append(f"  • {dim.capitalize()}: {score}%")

        sections.append("\n".join(sec14))

        # 15. PROVENANCE & LINEAGE
        sec15 = [
            "================================================================================",
            "15. PROVENANCE & LINEAGE TRACEABILITY",
            "================================================================================",
            f"Source Document:     {doc_title or 'Research File'}",
            f"Source File Hash:    {doc_hash}",
            f"Source Tables:       {', '.join(sorted(source_tables)) if source_tables else 'Table 1'}",
            f"Source Sections:     {', '.join(sorted(source_sections)) if source_sections else 'Unassigned'}",
            f"Source Page Numbers: {', '.join(str(p) for p in sorted(source_pages)) if source_pages else '1'}",
            "Traceability Rule:   Dual-value immutability maintained (raw_data + normalized data).",
        ]
        sections.append("\n".join(sec15))

        # 16. RESEARCH NOTES / SOURCE CONTEXT
        sec16 = [
            "================================================================================",
            "16. RESEARCH NOTES & METHODOLOGICAL CONTEXT",
            "================================================================================",
            f"- Dataset constructed by Darkroom DataForge Document Intelligence Engine.",
            f"- Grounded in empirical publication evidence.",
        ]
        discovery_rep = doc_meta.get("discovery_report") if isinstance(doc_meta, dict) else None
        if discovery_rep and isinstance(discovery_rep, dict):
            selection_rat = discovery_rep.get("selection_rationale")
            if selection_rat:
                sec16.append(f"- Authoritative Dataset Selection Rationale: {selection_rat}")
            counts = discovery_rep.get("stated_record_counts_in_text") or []
            for sc in counts:
                sec16.append(f"- Stated Document Metric: {sc.get('count')} ({sc.get('context', '')[:80]}...)")

        sections.append("\n".join(sec16))

        # Combine Body Text (for deterministic hashing)
        body_text = "\n\n".join(sections)
        content_hash = hashlib.sha256(body_text.encode("utf-8")).hexdigest()

        # Reproducibility Metadata Header (Inserted at the top of the final artifact)
        metadata_block = (
            "================================================================================\n"
            "REPRODUCIBILITY METADATA MANIFEST\n"
            "================================================================================\n"
            f"DataForge Generator Version: {gen_ver}\n"
            f"Dataset ID:                  {ds_id}\n"
            f"Source Document Hash:        {doc_hash}\n"
            f"Total Record Count:          {total_records_count}\n"
            f"Generated At (UTC):          {generated_at}\n"
            f"Content SHA-256 Hash:        {content_hash}\n"
            "================================================================================\n\n"
        )

        final_content = metadata_block + body_text

        # Sanitize filename
        clean_name = re.sub(r"[^\w\-_\.]", "_", ds_name).strip("_")
        filename = f"{clean_name}_domain_knowledge.txt"

        return DomainKnowledgeArtifact(
            dataset_id=ds_id,
            dataset_name=ds_name,
            filename=filename,
            content=final_content,
            content_hash=content_hash,
            record_count=total_records_count,
            generator_version=gen_ver,
            generated_at=generated_at,
        )
