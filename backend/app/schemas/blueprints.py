from __future__ import annotations
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class BlueprintField(BaseModel):
    name: str
    original_aliases: List[str] = Field(default_factory=list)
    type: str = "string"  # string, integer, float, boolean, date, currency
    required: bool = False
    description: str = ""
    regex_pattern: Optional[str] = None
    numeric_min: Optional[float] = None
    numeric_max: Optional[float] = None
    allowed_values: Optional[List[str]] = None
    is_array_field: bool = False  # If True, values are split into 1:N dimension & junction tables
    array_delimiter: str = ";"


class ExtractionBlueprint(BaseModel):
    id: str
    name: str
    description: str
    category: str = "general"
    fields: List[BlueprintField]
    primary_key: Optional[str] = None
    dimension_entity_name: Optional[str] = None
    array_field_name: Optional[str] = None


BUILTIN_BLUEPRINTS: Dict[str, ExtractionBlueprint] = {
    "qualifications": ExtractionBlueprint(
        id="qualifications",
        name="TVET & Higher Education Qualifications",
        description="Extracts registered occupational qualifications, SAQA IDs, NQF levels, and participating college offerings.",
        category="education",
        primary_key="saqa_id",
        dimension_entity_name="colleges",
        array_field_name="participating_colleges",
        fields=[
            BlueprintField(
                name="saqa_id",
                original_aliases=["saqa", "saqa id", "qual id", "qualification id", "code", "id"],
                type="string",
                required=True,
                regex_pattern=r"^\d{4,7}$",
                description="SAQA qualification registration code",
            ),
            BlueprintField(
                name="qualification_name",
                original_aliases=["qualification", "learning programme", "programme", "title", "description"],
                type="string",
                required=True,
                description="Official qualification title",
            ),
            BlueprintField(
                name="nqf_level",
                original_aliases=["nqf", "level", "nqf level"],
                type="integer",
                numeric_min=1,
                numeric_max=10,
                description="National Qualifications Framework Level (1 to 10)",
            ),
            BlueprintField(
                name="nqf_sub_framework",
                original_aliases=["sub-framework", "framework", "subframework", "qualification type"],
                type="string",
                allowed_values=["OQSF", "HEQSF", "GFETQSF"],
                description="Sub-framework classification",
            ),
            BlueprintField(
                name="nsfas_eligible",
                original_aliases=["nsfas", "funded", "bursary", "eligible"],
                type="boolean",
                description="NSFAS bursary funding eligibility",
            ),
            BlueprintField(
                name="participating_colleges",
                original_aliases=["college", "colleges", "delivery centre", "offering", "institution", "campus", "tvet", "provider"],
                type="string",
                is_array_field=True,
                array_delimiter=";",
                description="Delimited list of offering TVET colleges / delivery campuses",
            ),
        ],
    ),
    "occupations": ExtractionBlueprint(
        id="occupations",
        name="Occupations in High Demand (OIHD / OFO)",
        description="Extracts priority occupational lists, OFO codes, priority ranks, and entry qualifications.",
        category="labour_market",
        primary_key="ofo_code",
        fields=[
            BlueprintField(
                name="ofo_code",
                original_aliases=["ofo", "ofo code", "occupation code", "code"],
                type="string",
                required=True,
                regex_pattern=r"^\d{4,6}$",
                description="Organisational Framework for Occupations (OFO) code",
            ),
            BlueprintField(
                name="occupation_title",
                original_aliases=["occupation", "title", "description", "occupation title"],
                type="string",
                required=True,
                description="Occupational designation title",
            ),
            BlueprintField(
                name="priority_rank",
                original_aliases=["rank", "priority", "demand rank"],
                type="integer",
                numeric_min=1,
                description="National or regional demand priority rank",
            ),
            BlueprintField(
                name="major_group",
                original_aliases=["group", "major group", "category"],
                type="string",
                description="OFO Major Group classification",
            ),
            BlueprintField(
                name="province",
                original_aliases=["province", "region", "location"],
                type="string",
                description="Target province or National designation",
            ),
            BlueprintField(
                name="entry_qualification",
                original_aliases=["qualification", "entry level", "requirement", "minimum qual"],
                type="string",
                description="Minimum required entry qualification",
            ),
        ],
    ),
    "codebooks": ExtractionBlueprint(
        id="codebooks",
        name="Survey Metadata & Variable Codebooks",
        description="Extracts statistical survey variables, category values, and labels (e.g. StatsSA QLFS).",
        category="statistics",
        primary_key="variable_name",
        fields=[
            BlueprintField(
                name="variable_name",
                original_aliases=["variable", "var_name", "variable name", "field"],
                type="string",
                required=True,
                description="Dataset variable identifier",
            ),
            BlueprintField(
                name="variable_label",
                original_aliases=["label", "var_label", "variable label", "description"],
                type="string",
                description="Human-readable variable descriptor",
            ),
            BlueprintField(
                name="value_code",
                original_aliases=["value", "code", "val", "category_code"],
                type="string",
                description="Numeric or character category code",
            ),
            BlueprintField(
                name="value_label",
                original_aliases=["value label", "cat_label", "category_label", "meaning"],
                type="string",
                description="Description of the coded value",
            ),
        ],
    ),
    "financial": ExtractionBlueprint(
        id="financial",
        name="Financial Statements & Balance Sheets",
        description="Extracts financial statement line items, account codes, period amounts, and currencies.",
        category="finance",
        primary_key="account_code",
        fields=[
            BlueprintField(
                name="account_code",
                original_aliases=["account", "code", "item_no", "ref"],
                type="string",
                description="Chart of accounts reference code",
            ),
            BlueprintField(
                name="line_item",
                original_aliases=["description", "line item", "account name", "particulars"],
                type="string",
                required=True,
                description="Financial line item description",
            ),
            BlueprintField(
                name="amount",
                original_aliases=["amount", "value", "balance", "total", "sum"],
                type="currency",
                required=True,
                description="Monetary amount",
            ),
            BlueprintField(
                name="period",
                original_aliases=["year", "period", "date", "fy"],
                type="string",
                description="Reporting period or fiscal year",
            ),
        ],
    ),
    "universal_auto": ExtractionBlueprint(
        id="universal_auto",
        name="Universal AI Auto-Inferred Schema",
        description="Dynamically infers entity fields, data types, and relationships for any arbitrary PDF document.",
        category="general",
        fields=[],
    ),
}


def get_blueprint(blueprint_id: str) -> ExtractionBlueprint:
    return BUILTIN_BLUEPRINTS.get(blueprint_id.lower()) or BUILTIN_BLUEPRINTS["universal_auto"]
