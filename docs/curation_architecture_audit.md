# Darkroom DataForge — Semantic Curation Architecture Audit & Research-Grade Hardening Report

**System**: Darkroom DataForge  
**Version**: 2.2.0-research  
**Ruleset Version**: 2024.1  
**Audit Scope**: Evidence-Driven Curation Engine, OFO Classification Resolver, Conflict Detection Engine, Confidence Scoring, Provenance Tracking, and Reproducibility Manifests  
**Author**: Senior Research Data Systems Architect  
**Status**: VERIFIED & RESEARCH-GRADE HARDENED  

---

## 1. Current Architecture

Darkroom DataForge is designed specifically for the Wits–merSETA Darkroom team as an evidence-driven document intelligence, data curation, validation, and research data engineering platform.

Its lifecycle strictly decouples four distinct scientific transformations:

```
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│   EXTRACTION    │ ----> │  NORMALIZATION  │ ----> │   VALIDATION    │ ----> │    CURATION     │
│  Source Facts   │       │ Structural Clean│       │ Quality Checks  │       │ Semantic Ground │
└─────────────────┘       └─────────────────┘       └─────────────────┘       └─────────────────┘
         │                         │                         │                         │
         ▼                         ▼                         ▼                         ▼
   Raw Text & BBox          Typed Formats            Schema Adherence          Evidence Items
   (Immutable Source)      (Derived Fields)          (Format/Integrity)       (Audit Decisions)
```

1. **Extraction**: "What does the source document contain?" Direct capture of physical textual tokens and tabular coordinates.
2. **Normalization**: "Can the extracted data be structurally cleaned?" Whitespace collapsing, date parsing, title casing, and currency standardization.
3. **Validation**: "Does the cleaned data adhere to structural schemas?" Regex checks, type safety, missing key detection, and null-constraint verification.
4. **Curation**: "Does this record truthfully belong to the research dataset?" Grounding against domain taxonomies (e.g., merSETA OFO), resolving multi-source evidence, evaluating enterprise context, identifying contradictions, and enforcing reproducible inclusion/exclusion policies.

---

## 2. What Was Correct in the Initial Implementation

The initial implementation established sound foundations:
- **Three-State Decision Model**: Refusal to compress curation into a binary include/discard filter. All borderline, ambiguous, or contradictory items route to `REVIEW`.
- **Append-Only Decision Ledger**: An explicit audit trail tracking operator overrides and state transitions.
- **Configurable Dataset Intent & Policies**: Rule policies decoupled from business code, allowing parameterized thresholding.
- **Relational Lineage**: Records maintain relational foreign keys connecting back to source documents, pages, and extraction batches.
- **Modular Pipeline Separation**: Curation operates as an independent post-validation pipeline stage without mutating upstream raw extractions.

---

## 3. Problems Identified During Deep Audit

A rigorous architectural review uncovered critical semantic vulnerabilities in the naive rule-based setup:

1. **The Employer $\neq$ Occupation Fallacy (Blind Keyword Filtering)**:
   - *Issue*: An "Accountant" or "Cleaner" working at Toyota Automotive Manufacturing SA was previously scored high for manufacturing relevance because employer name matches triggered automotive chamber rules.
   - *Scientific Flaw*: Employer corporate context was conflated with occupational domain functions.

2. **Unsound Taxonomy Inheritance**:
   - *Issue*: Treating Major Group 2 ("Professionals") as uniformly technical engineering. In the South African OFO taxonomy, Major 2 includes Sub-Major 21 (Science/Engineering), but also Sub-Major 24 (Business Administration, including Accountants/Auditors).
   - *Scientific Flaw*: Classifications inherited attributes from parent groups without validating whether the sub-major was in-scope or out-of-scope.

3. **Untyped Evidence Flattening**:
   - *Issue*: A raw string from a PDF, a regex rule deduction, an LLM guess, and an operator override were all treated as interchangeable evidence items.
   - *Scientific Flaw*: Violated epistemological hierarchy. Research systems must distinguish observed empirical facts from inferred probabilistic deductions.

4. **Silent Overrides & Average-Out Logic in Conflicts**:
   - *Issue*: When OFO code denoted Mechanical Engineering (2144) while the title explicitly read "Financial Bookkeeper", the system calculated a weighted average score that resulted in an arbitrary score rather than halting for review.
   - *Scientific Flaw*: Violated Zero Blind Trust. Contradictory evidence must halt automated ingestion and route to Human Review with structured conflict records.

5. **Deduplication Variant Merging Risk**:
   - *Issue*: Naive string distance algorithms (e.g., token similarity > 0.70) risked collapsing distinct professional qualification tiers (e.g., "Mechanical Engineering Technician" vs "Mechanical Engineering Technologist").
   - *Scientific Flaw*: In industrial and qualification taxonomies, technicians (diploma-level) and technologists (degree-level) are distinct occupational identities. Auto-merging corrupts longitudinal research data.

6. **Missing Cryptographic Reproducibility Manifest**:
   - *Issue*: Runs could not prove that identical inputs with identical policies produced exact deterministic outcomes across environments.
   - *Scientific Flaw*: Research-grade datasets require immutable execution manifests recording source document SHA-256 hashes, engine versions, and ruleset versions.

---

## 4. Changes Implemented

| Area | Prior Implementation | Hardened Implementation |
|---|---|---|
| **Evidence Model** | Generic strings & scores | 6 typed categories (`SOURCE_FACT`, `DERIVED_CLASSIFICATION`, `RULE_INFERENCE`, `SEMANTIC_INFERENCE`, `LLM_INFERENCE`, `HUMAN_DECISION`), observed values vs interpretations, `strength`, `is_inherited`, `inherited_from` |
| **Decision Engine** | Threshold score comparison | Zero Blind Trust priority tree: Hard Conflicts $\rightarrow$ Explicit Exclusions $\rightarrow$ Validation Errors $\rightarrow$ Contextual Divergence $\rightarrow$ Ambiguous Roles $\rightarrow$ Score Thresholds |
| **Taxonomy Resolver** | Flat dictionary lookups | 4-level OFO hierarchy (`major`, `sub_major`, `minor`, `unit`) with explicit `belongs_to` relationships, qualified confidence penalties for inherited traits, and chamber attribution provenance |
| **Conflict Detector** | Not implemented | Detects `CLASSIFICATION_VS_TITLE`, `COMPANY_VS_OCCUPATION`, and `RULE_VS_TAXONOMY` contradictions |
| **Deduplicator** | Binary merge vs keep | Tier-aware deduplicator: Identifies `LEGITIMATE_RELATED_RECORD` with `KEEP_SEPARATE` recommendation for distinct professional qualification levels |
| **Explanations** | Single summary string | Comprehensive `explanation_contract` dictionary + domain-grounded `why_not` explanation for all exclusions |
| **Reproducibility** | Timestamps only | Cryptographic `CurationManifest` capturing source SHA-256 hashes, engine/ruleset versions, policies, and quality metrics |
| **Security & Isolation**| Weak tenant filtering | Strict `project_id` tenant isolation on runs, review queues, quality gates, and dataset exports |

---

## 5. Evidence Model

Every claim evaluated by DataForge is encapsulated in a strongly typed `EvidenceItem`:

```
┌────────────────────────────────────────────────────────┐
│                      EvidenceItem                      │
├────────────────────────────────────────────────────────┤
│ - evidence_type: EvidenceType                          │
│   (SOURCE_FACT | DERIVED_CLASSIFICATION |              │
│    RULE_INFERENCE | SEMANTIC_INFERENCE |               │
│    LLM_INFERENCE | HUMAN_DECISION)                     │
│ - source_field: str                                    │
│ - observed_source_value: Any (Raw text verbatim)       │
│ - interpretation: str (Normalized semantic meaning)    │
│ - relation_nature: str (supports | refutes | conflicts)│
│ - strength: str (empirical | deterministic |           │
│                  probabilistic | qualified)            │
│ - confidence: float (0.00 - 1.00)                      │
│ - is_inherited: bool                                   │
│ - inherited_from: Optional[str] (e.g. Major Group 2)   │
│ - provenance: Dict[str, Any] (doc_id, page, bbox)      │
└────────────────────────────────────────────────────────┘
```

### Empirical Grounding Principles
- **Source Facts**: Extracted directly from primary source tokens (e.g., `observed_source_value="Accountant"`). Strength is `empirical` with 1.0 confidence.
- **Inherited Evidence**: Qualifications inherited from taxonomy parents (e.g., claiming automotive chamber relevance because an occupation belongs to Sub-Major 21) are flagged `is_inherited=True` and penalized with a qualified confidence (0.50–0.65).
- **Interpretations**: Never mutate or overwrite raw values; they reside in distinct fields (`observed_source_value` vs `interpretation`).

---

## 6. Decision Model & Explanation Contract

DataForge follows a strict **Zero Blind Trust** priority-ordered decision cascade:

```
                            [Input Record Package]
                                      │
                                      ▼
                       ┌─────────────────────────────┐
                       │ Hard Contradiction Present? │
                       │ (e.g. OFO 2144 vs Bookkeeper│
                       └──────────────┬──────────────┘
                                      │
                         YES ─────────┴───────── NO
                          │                       │
                          ▼                       ▼
                  ┌──────────────┐      ┌─────────────────────────────┐
                  │Route: REVIEW │      │ Strong Domain Exclusion?    │
                  │(Reason:      │      │ (e.g. Accountant/Cleaner)   │
                  │ classification│      └──────────────┬──────────────┘
                  │ _conflict)   │                     │
                  └──────────────┘        YES ─────────┴───────── NO
                                           │                       │
                                           ▼                       ▼
                                   ┌──────────────┐      ┌─────────────────────────────┐
                                   │Decision:     │      │ Schema Validation Errors?   │
                                   │  EXCLUDE     │      └──────────────┬──────────────┘
                                   │(Domain why_not      YES ─────────┴───────── NO
                                   │  explanation)│       │                       │
                                   └──────────────┘       ▼                       ▼
                                                   ┌──────────────┐      ┌─────────────────────────────┐
                                                   │Route: REVIEW │      │ Contextual Divergence?      │
                                                   │(Reason:      │      │ (e.g. Industrial Employer   │
                                                   │ validation   │      │  vs Enterprise Support)     │
                                                   │ _error)      │      └──────────────┬──────────────┘
                                                   └──────────────┘                     │
                                                                           YES ─────────┴───────── NO
                                                                            │                       │
                                                                            ▼                       ▼
                                                                    ┌──────────────┐      ┌─────────────────────────────┐
                                                                    │Decision:     │      │ Ambiguous Leadership Role?  │
                                                                    │  EXCLUDE     │      │ (e.g. Operations Manager)   │
                                                                    │(with why_not)│      └──────────────┬──────────────┘
                                                                    └──────────────┘                     │
                                                                                           YES ─────────┴───────── NO
                                                                                            │                       │
                                                                                            ▼                       ▼
                                                                                    ┌──────────────┐      ┌──────────────────┐
                                                                                    │Route: REVIEW │      │ Score >= In threshold│
                                                                                    │(Reason:      │      └────────┬─────────┘
                                                                                    │ ambiguous    │               │
                                                                                    │ _evidence)   │         YES ──┴── NO
                                                                                    └──────────────┘          │         │
                                                                                                              ▼         ▼
                                                                                                       [INCLUDE]    [EXCLUDE]
```

### The Explanation Contract
Every decision includes a machine-readable, audit-compliant JSON contract:

```json
{
  "record_id": "rec_001",
  "primary_claim": "Excluded by domain relevance criteria",
  "decision": "EXCLUDE",
  "decision_method": "DETERMINISTIC_RULES",
  "why_not": "Record represents enterprise support role ('Accountant') without industrial or technical specialization. In research datasets for manufacturing skills, non-industrial support roles are excluded regardless of employer industry.",
  "confidence_basis": {
    "extraction_confidence": 0.98,
    "normalization_confidence": 0.99,
    "validation_confidence": 1.0,
    "curation_confidence": 0.95,
    "conflict_penalty": 0.0
  },
  "supporting_evidence_count": 0,
  "refuting_evidence_count": 2,
  "conflicts_count": 1,
  "uncertainties": []
}
```

---

## 7. Confidence Model

Confidence is computed using a multi-dimensional weighted formulation:

$$\text{Overall Confidence} = (0.20 \times C_{\text{ext}}) + (0.15 \times C_{\text{norm}}) + (0.25 \times C_{\text{val}}) + (0.40 \times C_{\text{cur}}) - P_{\text{conflict}}$$

Where:
- $C_{\text{ext}}$: Optical/extraction certainty of source tokens.
- $C_{\text{norm}}$: Structural normalization fidelity.
- $C_{\text{val}}$: Schema validation score ($1.0$ if clean, $0.85$ on minor warnings, $0.40$ on errors).
- $C_{\text{cur}}$: Weighted combination of deterministic rule scores and taxonomic verification depth.
- $P_{\text{conflict}}$: Conflict penalty ($0.25$ for hard contradictions, $0.05$ for contextual employer divergence).

---

## 8. Taxonomy Model

The South African Organising Framework for Occupations (OFO) is structured across four formal relational tiers:

1. **Major Group (1 digit)**: Broadest socio-economic category (e.g., `2` = Professionals).
2. **Sub-Major Group (2 digits)**: Domain discipline (e.g., `21` = Science & Engineering Professionals; `24` = Business & Administration Professionals).
3. **Minor Group (3 digits)**: Functional specialization (e.g., `214` = Engineering Professionals).
4. **Unit Group (4 digits)**: Specific occupational unit (e.g., `2144` = Mechanical Engineers).

### Chamber Attribution Provenance
- Direct 4-digit unit matches carry `chamber_attribution_basis = "TAXONOMY_INFERRED"` with full confidence.
- Mappings derived from parent sub-majors carry `chamber_attribution_basis = "MODEL_INFERRED"` and `is_inherited = True` with down-weighted confidence.

---

## 9. Review Model & Human-in-the-Loop Governance

1. **Queue Prioritization**:
   - `critical`: Contradictory evidence (e.g., code vs title) and validation errors.
   - `high`: Broad/ambiguous leadership occupations without technical trade designations.
   - `medium`: Borderline relevance scores within policy review windows.
2. **Immutable Action Ledger**:
   - Every operator intervention logs old status, new status, reviewer ID, timestamp, and justification reason into `DecisionLedger`.
   - Generates an `EvidenceItem` with `evidence_type = "HUMAN_DECISION"`, establishing that a human operator evaluated and accepted the borderline claim.

---

## 10. Relational Lineage Model

DataForge preserves uncorrupted lineage across every data lifecycle event:
- **Raw Data Integrity**: Raw extractions are immutable. Any normalized value, imputed field, or inferred chamber is stored in dedicated derived columns.
- **Traceability Chain**:
  $$\text{Source PDF} \xrightarrow{\text{SHA-256}} \text{Page Number} \xrightarrow{\text{BBox}} \text{Raw Record} \xrightarrow{} \text{Normalized Record} \xrightarrow{} \text{Evidence Items} \xrightarrow{} \text{Curation Decision}$$

---

## 11. Reproducibility Model & Curation Manifest

Every curation execution outputs an immutable `CurationManifest`:

```json
{
  "manifest_id": "man_a1b2c3d4",
  "run_id": "run_001",
  "dataset_id": "ds_merseta_2024",
  "dataset_name": "merSETA Skills Baseline",
  "dataset_intent": {
    "objective": "Identify core engineering and manufacturing occupational demand",
    "scope": ["Auto", "Metal", "Plastics"],
    "review_threshold": 0.60
  },
  "engine_version": "2.2.0",
  "ruleset_version": "2024.1",
  "policy_id": "merseta_ofo_relevance",
  "policy_version": "1.0.0",
  "source_documents": [
    {
      "document_id": "doc_auto_wsp",
      "sha256_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    }
  ],
  "record_counts": {
    "total": 5420,
    "included": 4120,
    "excluded": 980,
    "reviewed": 320,
    "conflicts": 45
  },
  "quality_gate_passed": true,
  "created_at": "2026-09-26T18:55:00Z"
}
```

Deterministic re-execution tests verify that running identical inputs across different sessions produces identical decisions, scores, and hashable manifests.

---

## 12. API Changes

- `GET /api/v1/curation/runs/{run_id}/manifest`: Returns the cryptographic reproducibility manifest for a run.
- `GET /api/v1/curation/datasets/{dataset_id}/review-queue`: Enhanced with `project_id` tenant isolation, priority filters, and conflict annotations.
- `POST /api/v1/curation/datasets/{dataset_id}/review`: Records operator decisions into `DecisionLedger` and generates a `HUMAN_DECISION` evidence item.
- `GET /api/v1/curation/datasets/{dataset_id}/quality-gates`: Validates quality gates against active intent thresholds before permitting downstream export.
- `GET /api/v1/curation/datasets/{dataset_id}/export`: Exports research datasets filtered strictly to `INCLUDE` decisions, appending manifest headers.

---

## 13. Frontend Changes

The Darkroom DataForge frontend workstation reflects the hardened curation contracts:
- **Decision Inspector**: Displays the complete `explanation_contract`, composite `confidence_basis`, and itemized evidence cards.
- **Review Queue**: Color-coded badges for `critical` contradictions vs `high` ambiguity; structured resolution modal enforcing justification notes.
- **Duplicate Workbench**: Distinct visual representation for `LEGITIMATE_RELATED_RECORD` with an explicit `KEEP_SEPARATE` badge versus `POSSIBLE_SEMANTIC_DUPLICATE` with a `MERGE` option.
- **Manifest Inspector**: Dedicated audit screen allowing researchers to verify document SHA-256 hashes and download the machine-readable manifest JSON.

---

## 14. Database Changes

Safe schema auto-migrations were implemented in `backend/app/database.py`:
- `evidence_items`: Added `observed_source_value`, `relation_nature` (`Column("relationship")`), `interpretation`, `strength`, `is_inherited`, `inherited_from`.
- `curation_decisions`: Added `decision_method`, `why_not`, `explanation_contract`, `conflict_ids`.
- `curation_runs`: Added `engine_version`, `ruleset_version`, `manifest`.
- `dataset_intents`: Added `version`, `classification_system`, `target_entities`, `target_relationships`, `review_threshold`.
- `source_conflicts`: Added `claims`, `recommended_action`.

All migrations run idempotently on startup with safe dialect detection (PostgreSQL and SQLite).

---

## 15. Test Coverage & Adversarial Verification

A dedicated adversarial test suite (`backend/tests/test_curation_adversarial.py`) and full integration test suite verify system correctness:

| Test Case | Scenario Description | Expected Outcome | Actual Result |
|---|---|---|---|
| **Example A** | Accountant at Toyota Automotive SA | `EXCLUDE` (Employer $\neq$ Occupation) | **PASSED** |
| **Example B** | Mechanical Engineering Technician (no company) | `INCLUDE` (Core OFO 3115 / Metal chamber) | **PASSED** |
| **Example C** | Operations Manager (broad leadership) | `REVIEW` (Ambiguous role) | **PASSED** |
| **Example D** | Automotive Assembly Line Technician (General Assembly) | `INCLUDE` (Core Automotive trade) | **PASSED** |
| **Example E** | Cleaner at GoodYear Tyre Firm | `EXCLUDE` (Non-industrial support role) | **PASSED** |
| **Example F** | Mechanical Technician vs Mechanical Technologist | `KEEP_SEPARATE` (Distinct professional tiers) | **PASSED** |
| **Example G** | OFO 2144 (Engineering) vs Title: Bookkeeper | `REVIEW` (`classification_conflict`) | **PASSED** |
| **Reproducibility**| Re-running identical input twice | Deterministic scores, decisions & manifest | **PASSED** |

### Test Suite Execution Summary
- **Backend Tests**: **30 passed in 9.71s** (100% pass rate)
- **Frontend Build**: **Passed with 0 errors** (`tsc && vite build`)

---

## 16. Remaining Risks & Nuances

1. **Scalability of Pairwise Deduplication**:
   - Current implementation compares records within a sliding 50-record window.
   - For datasets exceeding 100,000 records, a blocking-key pre-clustering step (e.g., by 2-digit OFO sub-major) is recommended to maintain $O(N \log N)$ complexity.
2. **Annual Taxonomy Drift**:
   - The South African Department of Higher Education and Training (DHET) updates OFO codes periodically (e.g., OFO 2015, 2019, 2021, 2024).
   - Datasets spanning multiple years require multi-version taxonomy mapping tables.
3. **Database Indexing**:
   - When deploying to production PostgreSQL with millions of evidence items, composite indexes on `(record_id, evidence_type)` and `(decision, priority)` should be monitored.

---

## 17. Recommended Next Phase

1. **Taxonomy Versioning Engine**: Implement explicit OFO version migration trees (e.g., mapping OFO 2019 codes to OFO 2021 equivalents with transformation evidence).
2. **Cryptographic Signing (Ed25519)**: Digitally sign the `CurationManifest` with the Darkroom institution's private key, guaranteeing tamper-proof exchange across university partners.
3. **Active Learning Feedback Loop**: Utilize confirmed human review decisions from the `DecisionLedger` to fine-tune borderline threshold parameters via Bayesian updating.
