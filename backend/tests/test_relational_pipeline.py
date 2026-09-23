import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.database import init_db
from backend.app.pipeline.table_healer import TableHealer
from backend.app.pipeline.relational_decomposer import RelationalDecomposer
from backend.app.extractors.base import RawTable

@pytest.fixture(scope="session", autouse=True)
def setup_db():
    init_db()

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c

def test_table_healer():
    # 1. Test header deduplication across page breaks
    tab1 = RawTable(page_number=1, table_index=0, headers=["SAQA ID", "Qualification Title"], rows=[["118792", "AI Developer"]])
    tab2 = RawTable(page_number=2, table_index=0, headers=["SAQA ID", "Qualification Title"], rows=[["SAQA ID", "Qualification Title"], ["118793", "Cloud Engineer"]])

    healed = TableHealer.clean_header_repeats([tab1, tab2])
    assert len(healed[1].rows) == 1
    assert healed[1].rows[0][0] == "118793"

    # 2. Test text bleed repair
    t_clean, c_rem = TableHealer.repair_text_wrap_bleed("Software Developer", "Engineer Motheo TVET")
    assert t_clean == "Software Developer Engineer"
    assert "Motheo TVET" in c_rem

    # 3. Test in-cell college deduplication
    uniques, dups = TableHealer.deduplicate_incell_colleges("Motheo TVET; Umfolozi TVET; Motheo TVET")
    assert len(uniques) == 2
    assert "Motheo TVET" in uniques
    assert "Umfolozi TVET" in uniques
    assert len(dups) == 1

def test_relational_decomposer():
    raw_recs = [
        {
            "saqa_id": "118792",
            "qualification": "Occupational Certificate: AI Developer",
            "nqf_level": "Level 5",
            "framework": "OQSF",
            "nsfas_eligible": "Yes",
            "participating_colleges": "Motheo TVET College; Umfolozi TVET College",
            "provenance": {"page_number": 1},
        },
        {
            "saqa_id": "102944",
            "qualification": "Occupational Certificate: Conference & Events Organiser",
            "nqf_level": "5",
            "framework": "OQSF",
            "nsfas_eligible": "No",
            "participating_colleges": "",  # zero colleges listed
            "provenance": {"page_number": 1},
        }
    ]

    decomp = RelationalDecomposer.decompose_tvet_qualifications(raw_recs)

    assert len(decomp["qualifications"]) == 2
    assert len(decomp["colleges"]) == 2
    assert len(decomp["qualification_colleges"]) == 2

def test_continuation_row_healing():
    tab = RawTable(
        page_number=1,
        table_index=0,
        headers=["SAQA ID", "Qualification", "Colleges"],
        rows=[
            ["97576", "Occupational Certificate: Electrician", "Motheo TVET"],
            ["", "", "Orbit TVET College"],
        ],
    )
    healed = TableHealer.heal_continuation_rows([tab])
    assert len(healed[0].rows) == 1
    assert healed[0].rows[0][0] == "97576"
    assert "Motheo TVET; Orbit TVET College" in healed[0].rows[0][2]

def test_cross_page_continuation_row_healing():
    tab1 = RawTable(
        page_number=1,
        table_index=0,
        headers=["SAQA ID", "Qualification", "Colleges"],
        rows=[
            ["97585", "Occupational Certificate: Millwright", "Umfolozi TVET College; Tshwane South TVET College"],
        ],
    )
    tab2 = RawTable(
        page_number=2,
        table_index=0,
        headers=["SAQA ID", "Qualification", "Colleges"],
        rows=[
            ["", "", "Gert Sibande TVET College; Majuba TVET College; Northlink TVET College"],
            ["93626", "Occupational Certificate: Boilermaker", "Majuba TVET College"],
        ],
    )
    healed = TableHealer.heal_continuation_rows([tab1, tab2])
    assert len(healed[0].rows) == 1
    assert healed[0].rows[0][0] == "97585"
    assert "Gert Sibande TVET College" in healed[0].rows[0][2]
    assert len(healed[1].rows) == 1
    assert healed[1].rows[0][0] == "93626"


def test_swapped_column_header_mapping():
    from backend.app.pipeline.engine import PipelineEngine

    schema_cols = [
        "saqa_id",
        "number",
        "qualification",
        "nqf_sub_framewo_rk",
        "nsfas_allowan_ces",
        "participating_colleges",
    ]

    # Table 2 has columns swapped: NQF Sub Framework is col 2, QUALIFICATION is col 3
    tab_headers = [
        "SAQA ID",
        "NUMBER",
        "NQF Sub Framework",
        "QUALIFICATION",
        "",
        "PARTICPATING COLLEGES",
    ]
    row_cells = [
        "91761",
        "60420002",
        "OQSF",
        "Occupational Certificate: Electrician",
        "",
        "Port Elizabeth TVET College",
    ]

    mapped = PipelineEngine.map_table_row_to_schema(tab_headers, row_cells, schema_cols)
    assert mapped["saqa_id"] == "91761"
    assert mapped["number"] == "60420002"
    assert mapped["qualification"] == "Occupational Certificate: Electrician"
    assert mapped["nqf_sub_framewo_rk"] == "OQSF"
    assert "Port Elizabeth" in mapped["participating_colleges"]


