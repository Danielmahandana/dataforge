import os
import pytest
from typing import List, Tuple

from backend.app.document_intelligence.document_profile import (
    DocumentProfile,
    DocumentType,
    SemanticTableRole,
    UnitOfObservation,
    SectionNode,
    TableMetadata,
    DatasetCandidate,
)
from backend.app.document_intelligence.unit_of_observation import UnitOfObservationDetector
from backend.app.document_intelligence.section_detector import SectionDetector
from backend.app.document_intelligence.table_classifier import TableClassifier
from backend.app.document_intelligence.dataset_role_resolver import DatasetRoleResolver
from backend.app.document_intelligence.table_reconstructor import TableReconstructor
from backend.app.document_intelligence.profiler import DocumentProfiler
from backend.app.curation.quality_engine import QualityEngine
from backend.app.pipeline.validator import Validator, OFOCodeValidator, IdentifierValidator, NumericRangeValidator
from backend.app.models.record import Record


def test_unit_of_observation_detection():
    # 1. Occupation unit
    occ_headers = ["ofo_code", "occupation_title", "minimum_qualification"]
    occ_rows = [["2021-112101", "Director", "Bachelor's Degree"]]
    occ_unit = UnitOfObservationDetector.detect(occ_headers, occ_rows)
    assert occ_unit == UnitOfObservation.OCCUPATION

    # 2. Qualification unit
    qual_headers = ["saqa_id", "qualification_title", "nqf_level"]
    qual_rows = [["67491", "National Certificate: Mechanical Engineering", "Level 4"]]
    qual_unit = UnitOfObservationDetector.detect(qual_headers, qual_rows)
    assert qual_unit == UnitOfObservation.QUALIFICATION

    # 3. Survey response unit
    survey_headers = ["question", "sample_size", "percentage_agree"]
    survey_rows = [["Q1: Skills availability", "250", "42%"]]
    survey_unit = UnitOfObservationDetector.detect(survey_headers, survey_rows)
    assert survey_unit == UnitOfObservation.SURVEY_RESPONSE

    # 4. Employer unit
    emp_headers = ["company_name", "sector", "employees_count"]
    emp_rows = [["Sasol Synfuels", "Chemical", "5000"]]
    emp_unit = UnitOfObservationDetector.detect(emp_headers, emp_rows)
    assert emp_unit == UnitOfObservation.COMPANY


def test_section_hierarchy_discovery():
    pages_text: List[Tuple[int, str]] = [
        (1, "Mpumalanga List of Occupations in High Demand: A Technical Research Report\n2024"),
        (5, "Table of Contents\nPart 1: Introduction\nPart 2: Methodology\nPart 5: Consolidation of Evidence"),
        (8, "PART 1: INTRODUCTION AND BACKGROUND\n1.1 Purpose of the Study\nThis study identifies critical skills."),
        (15, "PART 2: RESEARCH METHODOLOGY AND DATA SOURCES\n2.1 Quantitative indicators\nWe analyze wage data."),
        (25, "PART 5: CONSOLIDATION OF EVIDENCE AND THE FINAL LIST OF OCCUPATIONS IN HIGH DEMAND IN MPUMALANGA\n"
             "5.1 Final Selection\nThe process produced 167 occupations in high demand."),
        (31, "Table 4: The final list of OIHD in Mpumalanga\n2021-112101 Director"),
        (40, "ANNEXURE A: LIST OF STAKEHOLDERS CONSULTED\nStakeholder interviews"),
    ]

    sections = SectionDetector.detect_sections(pages_text)
    assert len(sections) >= 3

    # Check that Part 5 was detected and classified as FINAL_LIST
    part_5 = next((s for s in sections if "PART 5" in s.title.upper() or "CONSOLIDATION" in s.title.upper()), None)
    assert part_5 is not None
    assert part_5.semantic_type in ["FINAL_LIST", "EVIDENCE", "RESULTS"]
    assert part_5.page_start <= 25

    # Check Annexure
    annex = next((s for s in sections if "ANNEXURE" in s.title.upper()), None)
    assert annex is not None
    assert annex.semantic_type == "APPENDIX"


def test_table_semantic_classification():
    # Table 1: Methodology / Weights table
    t1_headers = ["Indicator", "Weight", "Data Source"]
    t1_rows = [["Wage premium", "0.30", "QLFS"], ["Vacancy duration", "0.40", "ESSA"]]
    t1_sec = SectionNode(title="Part 2: Methodology", level=1, page_start=15, page_end=24, semantic_type="METHODOLOGY")
    t1_meta = TableClassifier.classify_table(
        table_id="tab_1", page_num=16, headers=t1_headers, rows=t1_rows,
        page_text="Table 1: Indicator weights used in scoring model", current_section=t1_sec
    )
    assert t1_meta.semantic_role in [SemanticTableRole.METHODOLOGY, SemanticTableRole.INTERMEDIATE_ANALYSIS]

    # Table 4: Authoritative Target List
    t4_headers = ["OFO Code", "Occupation Title", "Minimum Qualification Required"]
    t4_rows = [["2021-112101", "Director", "Bachelor's Degree"], ["2021-121101", "Finance Manager", "Honours Degree"]]
    t4_sec = SectionNode(title="Part 5: Final List", level=1, page_start=25, page_end=38, semantic_type="FINAL_LIST")
    t4_meta = TableClassifier.classify_table(
        table_id="tab_4", page_num=31, headers=t4_headers, rows=t4_rows,
        page_text="TABLE 4: The final list of OIHD in Mpumalanga", current_section=t4_sec
    )
    assert t4_meta.semantic_role == SemanticTableRole.FINAL_DATASET
    assert t4_meta.unit_of_observation == UnitOfObservation.OCCUPATION


def test_adversarial_no_table_concatenation():
    """Adversarial test: Document contains multiple distinct tables across sections.
    The engine must NOT concatenate all tables into one single broken dataset."""
    tables_meta = [
        TableMetadata(
            table_id="tab_1", page_start=10, page_end=10, caption="Table 1: Macroeconomic indicators",
            headers=["Province", "GDP Growth", "Unemployment Rate"],
            row_count=9, column_count=3, semantic_role=SemanticTableRole.INTERMEDIATE_ANALYSIS,
            unit_of_observation=UnitOfObservation.PROVINCE, confidence=0.85
        ),
        TableMetadata(
            table_id="tab_2", page_start=18, page_end=18, caption="Table 2: Survey respondents by sector",
            headers=["Sector", "Number of Firms", "Share %"],
            row_count=12, column_count=3, semantic_role=SemanticTableRole.SURVEY,
            unit_of_observation=UnitOfObservation.SURVEY_RESPONSE, confidence=0.80
        ),
        TableMetadata(
            table_id="tab_4", page_start=31, page_end=36, caption="Table 4: The final list of OIHD in Mpumalanga",
            headers=["OFO Code", "Occupation Title", "Minimum Qualification"],
            row_count=167, column_count=3, semantic_role=SemanticTableRole.FINAL_DATASET,
            unit_of_observation=UnitOfObservation.OCCUPATION, confidence=0.98
        ),
    ]

    sections = [
        SectionNode(title="Part 1: Context", level=1, page_start=1, page_end=14, semantic_type="CONTEXT"),
        SectionNode(title="Part 2: Survey Results", level=1, page_start=15, page_end=24, semantic_type="RESULTS"),
        SectionNode(title="Part 5: Final List of OIHD", level=1, page_start=25, page_end=40, semantic_type="FINAL_LIST"),
    ]

    pages_text = [
        (25, "Consolidation of Evidence. The final list includes 167 occupations in high demand in Mpumalanga."),
    ]

    candidates = DatasetRoleResolver.discover_candidates(tables_meta, sections, pages_text)
    assert len(candidates) >= 1

    # Table 4 must be the authoritative target dataset
    authoritative = next((c for c in candidates if c.is_authoritative), None)
    assert authoritative is not None
    assert "Table 4" in authoritative.name
    assert authoritative.unit_of_observation == UnitOfObservation.OCCUPATION
    assert authoritative.stated_count == 167

    # Verify that other tables are distinct candidates or intermediate, NOT concatenated into Table 4
    assert authoritative.table_ids == ["tab_4"]


def test_adversarial_multipage_stitching_and_header_dedup():
    """Multi-page table spanning pages with repeated running headers.
    Verify TableReconstructor deduplicates headers and discards artifacts."""
    raw_tables = [
        {
            "page_number": 1,
            "headers": ["OFO Code", "Occupation Title", "Minimum Qualification"],
            "rows": [
                ["2021-112101", "Director", "Bachelor's Degree"],
                ["2021-121101", "Finance Manager", "Honours Degree"],
            ]
        },
        {
            "page_number": 2,
            "headers": ["OFO Code", "Occupation Title", "Minimum Qualification"],
            "rows": [
                ["OFO Code", "Occupation Title", "Minimum Qualification"],  # Repeated header inside table
                ["2021-132101", "Manufacturing Operations Manager", "Diploma"],
                ["8 Interquartile range outlier footnote...", "", ""],      # Footnote artifact
            ]
        }
    ]

    reconstructed = TableReconstructor.reconstruct_table(
        raw_tables=raw_tables,
        target_caption="Table 4: Multi-page test",
        unit_of_observation="occupation"
    )

    # Exactly 3 genuine records (repeated header and footnote stripped)
    assert len(reconstructed.rows) == 3
    assert reconstructed.rows[0][0] == "2021-112101"
    assert reconstructed.rows[1][0] == "2021-121101"
    assert reconstructed.rows[2][0] == "2021-132101"


def test_adversarial_footnote_and_margin_stripping():
    # Test footnote recognition
    assert TableReconstructor.is_margin_or_footnote_artifact(["8 Interquartile range calculated from 2021 QLFS", ""]) is True
    assert TableReconstructor.is_margin_or_footnote_artifact(["9 Upper outlier boundary threshold applied", ""]) is True
    assert TableReconstructor.is_margin_or_footnote_artifact(["Note: Data sourced from DHET 2024", ""]) is True
    assert TableReconstructor.is_margin_or_footnote_artifact(["CONSOLIDATION OF EVIDENCE AND THE FINAL LIST 27", ""]) is True

    # Real data row must NOT be considered footnote
    assert TableReconstructor.is_margin_or_footnote_artifact(["2021-112101", "Director", "Bachelor's Degree"]) is False


def test_zero_blind_trust_unprocessed_records():
    """Rule: Unprocessed records must NEVER default to _curation_confidence = 1.0.
    Curation confidence must be None until an actual curation policy runs."""
    rec = Record(
        dataset_id="test_ds",
        row_index=1,
        data={"ofo_code": "2021-112101", "occupation_title": "Director"},
        raw_data={"ofo_code": "2021-112101", "occupation_title": "Director"},
        confidence_score=0.98,
        curation_decision="unprocessed",
    )

    # By default in our hardened model, multi_confidence["curation"] is None
    assert rec.curation_decision == "unprocessed"
    assert rec.multi_confidence.get("curation") is None
    assert rec.curation_confidence is None


def test_quality_engine_10_gates_evaluation():
    # 1. Clean dataset evaluation
    clean_eval = QualityEngine.evaluate(
        total_records=167,
        valid_records=165,
        error_records=0,
        warning_records=2,
        review_required_count=0,
        duplicate_count=0,
        conflict_count=0,
        null_cell_count=0,
        total_cells=501,
        provenance_missing_count=0,
        curation_processed=False,
        has_generic_columns=False,
        document_profile_valid=True,
        dataset_identified=True,
    )

    assert clean_eval.overall_score >= 90.0
    assert clean_eval.gates["document_understanding_gate"] == "passed"
    assert clean_eval.gates["dataset_identification_gate"] == "passed"
    assert clean_eval.gates["schema_gate"] == "passed"
    assert clean_eval.gates["validation_gate"] == "passed"
    assert clean_eval.gates["curation_gate"] == "partially_processed"  # Unprocessed policy state

    # 2. Corrupted generic columns dataset evaluation
    corrupt_eval = QualityEngine.evaluate(
        total_records=744,
        valid_records=300,
        error_records=200,
        warning_records=244,
        review_required_count=0,
        duplicate_count=45,
        conflict_count=10,
        null_cell_count=400,
        total_cells=1488,
        provenance_missing_count=50,
        curation_processed=False,
        has_generic_columns=True,  # column_1, column_2 detected!
        document_profile_valid=False,
        dataset_identified=False,
    )

    assert corrupt_eval.gates["schema_gate"] == "failed"
    assert corrupt_eval.gates["document_understanding_gate"] == "failed"
    assert corrupt_eval.gates["dataset_identification_gate"] == "failed"
    assert corrupt_eval.can_export_clean is False
    assert corrupt_eval.export_status in ["BLOCKED", "REQUIRES_REVIEW"]


def test_validator_ofo_and_saqa():
    # Valid OFO codes
    assert OFOCodeValidator.validate("ofo_code", "2021-112101", 1) is None
    assert OFOCodeValidator.validate("ofo_code", "112101", 1) is None
    assert OFOCodeValidator.validate("ofo_code", "1121", 1) is None

    # Invalid OFO codes
    assert OFOCodeValidator.validate("ofo_code", "INVALID_CODE", 1) is not None
    assert OFOCodeValidator.validate("ofo_code", "12", 1) is not None

    # SAQA ID validation
    assert IdentifierValidator.validate_saqa_id("saqa_id", "67491", 1) is None
    assert IdentifierValidator.validate_saqa_id("saqa_id", "ABCDEF", 1) is not None

    # NQF level validation
    assert NumericRangeValidator.validate_nqf_level("nqf_level", "Level 5", 1) is None
    assert NumericRangeValidator.validate_nqf_level("nqf_level", "NQF 15", 1) is not None  # Outside 1-10


def test_mpumalanga_pdf_benchmark_acceptance():
    """Authoritative benchmark test on Mpumalanga report (72 pages).
    Must discover Table 4 in Part 5, corroborate stated count of 167,
    and reconstruct exactly 167 records with clean domain schema."""
    benchmark_candidates = [
        os.path.join("backend", "storage", "benchmarks", "Mpumalanga-Occupations in High Demand List-April 2024.pdf"),
        os.path.join("backend", "storage", "uploads", "2f3386e5-b95d-4cc7-a452-aac8125f30b4_Mpumalanga-Occupations in High Demand List-April 2.pdf"),
    ]
    pdf_path = next((p for p in benchmark_candidates if os.path.exists(p)), None)
    if not pdf_path:
        pytest.skip("Benchmark PDF not found in benchmarks or uploads")

    # 1. Profile document
    profile = DocumentProfiler.profile_document(pdf_path, "benchmark_doc_01")
    assert profile.page_count == 72
    assert profile.document_type == DocumentType.RESEARCH_REPORT
    assert len(profile.sections) >= 10
    assert len(profile.dataset_candidates) >= 1

    # 2. Authoritative target candidate resolution
    authoritative = next((c for c in profile.dataset_candidates if c.is_authoritative), None)
    assert authoritative is not None
    assert "TABLE 4" in authoritative.name.upper()
    assert authoritative.unit_of_observation == UnitOfObservation.OCCUPATION
    assert authoritative.page_start == 31
    assert authoritative.page_end == 36
    assert authoritative.stated_count == 167

    # 3. Table reconstruction across pages 31 to 36
    import pdfplumber
    with pdfplumber.open(pdf_path) as pdf:
        pages_text = [(i + 1, pdf.pages[i].extract_text() or "") for i in range(len(pdf.pages))]

    reconstructed = TableReconstructor.reconstruct_from_text_lines(
        pages_text=pages_text,
        target_caption=authoritative.name,
        start_page=authoritative.page_start,
        end_page=authoritative.page_end,
        unit_of_observation=authoritative.unit_of_observation.value,
    )

    # Acceptance criteria: exactly 167 authoritative records
    assert len(reconstructed.rows) == 167
    assert reconstructed.headers == ["ofo_code", "occupation_title", "minimum_qualification_required"]

    # Verify first and last records
    first_row = reconstructed.rows[0]
    assert first_row[0] == "2021-112101"
    assert "Director" in first_row[1]
    assert "Diploma" in first_row[2] or "Certificate" in first_row[2]

    last_row = reconstructed.rows[-1]
    assert last_row[0] == "2021-734402"
    assert len(last_row[1]) > 0
    assert len(last_row[2]) > 0

    # Verify all OFO codes match valid format
    for r in reconstructed.rows:
        issue = OFOCodeValidator.validate("ofo_code", r[0], 0)
        assert issue is None, f"OFO code '{r[0]}' failed validation"
