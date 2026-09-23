import pytest
from backend.app.schemas.blueprints import BUILTIN_BLUEPRINTS, get_blueprint, ExtractionBlueprint
from backend.app.pipeline.relational_decomposer import RelationalDecomposer


def test_builtin_blueprints():
    assert "qualifications" in BUILTIN_BLUEPRINTS
    assert "occupations" in BUILTIN_BLUEPRINTS
    assert "codebooks" in BUILTIN_BLUEPRINTS
    assert "financial" in BUILTIN_BLUEPRINTS

    qual_bp = get_blueprint("qualifications")
    assert qual_bp.primary_key == "saqa_id"

    fin_bp = get_blueprint("financial")
    assert fin_bp.name == "Financial Statements & Balance Sheets"


def test_universal_decomposer_occupations():
    raw_occupations = [
        {
            "ofo_code": "251201",
            "occupation_title": "Software Developer",
            "priority_rank": "1",
            "major_group": "Professionals",
            "province": "National",
            "entry_qualification": "Bachelor Degree / NQF 7",
        },
        {
            "ofo_code": "251202",
            "occupation_title": "Developer Programmer",
            "priority_rank": "2",
            "major_group": "Professionals",
            "province": "National",
            "entry_qualification": "Diploma / NQF 6",
        },
    ]

    occup_bp = get_blueprint("occupations")
    res = RelationalDecomposer.decompose(raw_occupations, blueprint=occup_bp)

    assert "occupations" in res
    assert len(res["occupations"]) == 2
    assert res["occupations"][0]["ofo_code"] == "251201"
    assert res["occupations"][0]["occupation_title"] == "Software Developer"


def test_universal_decomposer_financial():
    raw_financial = [
        {
            "account_code": "1001",
            "line_item": "Cash and Cash Equivalents",
            "amount": "1500000.00",
            "period": "2026",
        },
        {
            "account_code": "2001",
            "line_item": "Accounts Payable",
            "amount": "450000.00",
            "period": "2026",
        },
    ]

    fin_bp = get_blueprint("financial")
    res = RelationalDecomposer.decompose(raw_financial, blueprint=fin_bp)

    assert "financial" in res
    assert len(res["financial"]) == 2
    assert res["financial"][0]["account_code"] == "1001"
    assert res["financial"][0]["amount"] == 1500000.0
