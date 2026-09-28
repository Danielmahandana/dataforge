from __future__ import annotations
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from backend.app.curation.rule_engine import RuleAssertion


class EvidenceDraft(BaseModel):
    evidence_type: str  # SOURCE_FACT, DERIVED_CLASSIFICATION, RULE_INFERENCE, SEMANTIC_INFERENCE, LLM_INFERENCE, HUMAN_DECISION
    claim: str
    confidence: float = 1.0
    rule_id: Optional[str] = None
    document_id: Optional[str] = None
    document_name: Optional[str] = None
    page_number: Optional[int] = None
    table_index: Optional[int] = None
    row_index: Optional[int] = None
    cell_key: Optional[str] = None
    source_text: Optional[str] = None
    observed_source_value: Optional[str] = None
    relationship: Optional[str] = None
    interpretation: Optional[str] = None
    strength: str = "STRONG"  # STRONG, MEDIUM, WEAK
    is_inherited: bool = False
    inherited_from: Optional[str] = None


class EvidenceBuilder:
    """Constructs verifiable, traceable Evidence objects for record curation decisions.
    Strictly differentiates between source facts, taxonomic derivations, rule deductions,
    semantic inferences, and model/human assertions."""

    @classmethod
    def build_evidence_set(
        cls,
        record_data: Dict[str, Any],
        raw_data: Optional[Dict[str, Any]],
        provenance: Dict[str, Any],
        row_index: int,
        hierarchy_info: Dict[str, Any],
        rule_assertions: List[RuleAssertion],
        chambers: List[str],
        semantic_notes: Optional[str] = None,
        conflicts: Optional[List[Any]] = None,
    ) -> List[EvidenceDraft]:
        evidence_list: List[EvidenceDraft] = []
        doc_id = provenance.get("document_id")
        doc_name = provenance.get("document_name") or "Source Document"
        page_num = provenance.get("page_number")
        tab_idx = provenance.get("table_index")
        method = provenance.get("method", "table_extractor")

        primary_title = str(
            record_data.get("occupation_title")
            or record_data.get("occupation")
            or record_data.get("qualification")
            or record_data.get("title")
            or "Record"
        ).strip()

        raw_title = str(
            (raw_data or {}).get("occupation_title")
            or (raw_data or {}).get("occupation")
            or (raw_data or {}).get("qualification")
            or primary_title
        ).strip()

        # 1. SOURCE_FACT: Document Grounding & Cell Coordinates
        evidence_list.append(
            EvidenceDraft(
                evidence_type="SOURCE_FACT",
                claim=f"Extracted title '{primary_title}' from document '{doc_name}', page {page_num or 1} via {method}.",
                confidence=0.98,
                document_id=doc_id,
                document_name=doc_name,
                page_number=page_num,
                table_index=tab_idx,
                row_index=row_index,
                cell_key="title",
                source_text=raw_title,
                observed_source_value=raw_title,
                relationship="extracted_from_cell",
                interpretation="Verifiable source occurrence establishing physical existence in ingested document.",
                strength="STRONG",
                is_inherited=False,
            )
        )

        # 2. SOURCE_FACT: Code presence (if available)
        ofo_code = record_data.get("ofo_code") or record_data.get("code")
        if ofo_code:
            evidence_list.append(
                EvidenceDraft(
                    evidence_type="SOURCE_FACT",
                    claim=f"Source record contains explicit classification code: '{ofo_code}'.",
                    confidence=0.99,
                    document_id=doc_id,
                    document_name=doc_name,
                    page_number=page_num,
                    row_index=row_index,
                    cell_key="ofo_code",
                    source_text=str(ofo_code),
                    observed_source_value=str(ofo_code),
                    relationship="extracted_code_identifier",
                    interpretation="Authoritative numerical identifier present in source table row.",
                    strength="STRONG",
                    is_inherited=False,
                )
            )

        # 3. DERIVED_CLASSIFICATION: Direct or Inherited Taxonomy Nodes
        levels = hierarchy_info.get("levels", {})
        if levels:
            unit_info = levels.get("unit")
            minor_info = levels.get("minor")
            sub_major_info = levels.get("sub_major")
            major_info = levels.get("major")

            if unit_info:
                # Direct Unit Group match
                evidence_list.append(
                    EvidenceDraft(
                        evidence_type="DERIVED_CLASSIFICATION",
                        claim=f"Directly classified under OFO Unit Group {unit_info.get('code')}: '{unit_info.get('title')}'.",
                        confidence=0.95,
                        document_id=doc_id,
                        document_name=doc_name,
                        page_number=page_num,
                        row_index=row_index,
                        cell_key="ofo_code",
                        source_text=str(ofo_code),
                        observed_source_value=str(unit_info.get("code")),
                        relationship="belongs_to_unit_group",
                        interpretation="Unit group provides fine-grained occupational classification defining technical core.",
                        strength="STRONG",
                        is_inherited=False,
                    )
                )

            # Inherited Parent Classifications (marked with is_inherited=True and reduced confidence)
            if sub_major_info:
                evidence_list.append(
                    EvidenceDraft(
                        evidence_type="DERIVED_CLASSIFICATION",
                        claim=f"Inherited broad classification from Sub-Major {sub_major_info.get('code')}: '{sub_major_info.get('title')}'.",
                        confidence=0.75,
                        document_id=doc_id,
                        document_name=doc_name,
                        page_number=page_num,
                        row_index=row_index,
                        cell_key="ofo_code",
                        source_text=str(ofo_code),
                        observed_source_value=str(sub_major_info.get("code")),
                        relationship="belongs_to_sub_major_group",
                        interpretation="Taxonomy hierarchy context inherited from parent group (qualified confidence).",
                        strength="MEDIUM",
                        is_inherited=True,
                        inherited_from=f"Sub-Major {sub_major_info.get('code')}",
                    )
                )

        # 4. RULE_INFERENCE: Deterministic Policy Assertions
        for assertion in rule_assertions:
            if assertion.satisfied:
                evidence_list.append(
                    EvidenceDraft(
                        evidence_type="RULE_INFERENCE",
                        claim=assertion.claim,
                        confidence=assertion.confidence,
                        rule_id=assertion.rule_id,
                        document_id=doc_id,
                        document_name=doc_name,
                        page_number=page_num,
                        row_index=row_index,
                        relationship="evaluates_policy_rule",
                        interpretation=assertion.description,
                        strength="STRONG" if assertion.confidence >= 0.85 else "MEDIUM",
                        is_inherited=False,
                    )
                )

        # 5. SEMANTIC_INFERENCE: Chamber Alignment
        if chambers:
            basis_type = hierarchy_info.get("chamber_attribution_basis", "MODEL_INFERRED")
            evidence_list.append(
                EvidenceDraft(
                    evidence_type="SEMANTIC_INFERENCE",
                    claim=f"Identified sector alignment: {', '.join(chambers)} ({basis_type}).",
                    confidence=0.85 if basis_type == "TAXONOMY_INFERRED" else 0.70,
                    document_id=doc_id,
                    document_name=doc_name,
                    page_number=page_num,
                    row_index=row_index,
                    relationship="associated_industrial_domain",
                    interpretation=f"Occupational domain mapping based on {basis_type}; not a statutory gazette.",
                    strength="MEDIUM",
                    is_inherited=hierarchy_info.get("direct_unit_match") is False,
                    inherited_from="OFO Sector Profile" if hierarchy_info.get("direct_unit_match") is False else None,
                )
            )

        # 6. LLM_INFERENCE: Model Structured Reasoning (if applied)
        if semantic_notes:
            evidence_list.append(
                EvidenceDraft(
                    evidence_type="LLM_INFERENCE",
                    claim=semantic_notes,
                    confidence=0.80,
                    document_id=doc_id,
                    document_name=doc_name,
                    page_number=page_num,
                    row_index=row_index,
                    relationship="ai_model_synthesis",
                    interpretation="Structured LLM reasoning used for ambiguity resolution. Must not override source facts.",
                    strength="MEDIUM",
                    is_inherited=False,
                )
            )

        # 7. Conflicting Evidence Warnings (if any)
        if conflicts:
            for conf in conflicts:
                evidence_list.append(
                    EvidenceDraft(
                        evidence_type="RULE_INFERENCE",
                        claim=f"CONFLICT DETECTED: {conf.claim_a} vs {conf.claim_b}",
                        confidence=0.99,
                        document_id=doc_id,
                        document_name=doc_name,
                        page_number=page_num,
                        row_index=row_index,
                        relationship="evidence_contradiction",
                        interpretation=f"Contradiction between evidence sources requires human review: {conf.details}",
                        strength="STRONG",
                        is_inherited=False,
                    )
                )

        return evidence_list
