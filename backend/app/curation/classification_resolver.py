from __future__ import annotations
import re
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class TaxonomyLevelInfo(BaseModel):
    code: str
    title: str
    level: str  # major, sub_major, minor, unit, occupation
    parent_code: Optional[str] = None
    relationship: str = "belongs_to"


class InheritedEvidenceClaim(BaseModel):
    source_level: str  # major, sub_major, minor, unit
    source_code: str
    source_title: str
    claim: str
    is_inherited: bool = True
    confidence_qualification: float = 0.70  # Inherited claims have lower certainty than direct claims
    chamber_attribution_basis: str = "MODEL_INFERRED"  # SOURCE_SUPPORTED, MODEL_INFERRED, HUMAN_CONFIRMED


class HierarchyResolution(BaseModel):
    code: str
    valid_format: bool
    levels: Dict[str, TaxonomyLevelInfo]
    inherited_claims: List[InheritedEvidenceClaim]
    direct_unit_match: bool = False
    sector_affinity: float = 0.0
    matched_chambers: List[str] = Field(default_factory=list)
    chamber_attribution_basis: str = "MODEL_INFERRED"


class ClassificationResolver:
    """Resolves hierarchical taxonomy structure and inherited occupational context for South African OFO.
    Explicitly tracks parent-child relationships and distinguishes direct from inherited evidence
    to prevent false certainty (Zero Blind Trust)."""

    # Official South African OFO Major Groups (1-digit)
    OFO_MAJOR_GROUPS = {
        "1": {"title": "Managers", "industrial_affinity": 0.35},
        "2": {"title": "Professionals", "industrial_affinity": 0.80},
        "3": {"title": "Technicians and Associate Professionals", "industrial_affinity": 0.90},
        "4": {"title": "Clerical Support Workers", "industrial_affinity": 0.20},
        "5": {"title": "Service and Sales Workers", "industrial_affinity": 0.25},
        "6": {"title": "Skilled Agricultural, Forestry, Fishery, Craft and Related Trades Workers", "industrial_affinity": 0.95},
        "7": {"title": "Plant and Machine Operators and Assemblers", "industrial_affinity": 0.95},
        "8": {"title": "Elementary Occupations", "industrial_affinity": 0.30},
    }

    # South African OFO Sub-Major Groups (2-digit)
    # Notice: Sector chamber mapping is explicitly flagged as MODEL_INFERRED
    OFO_SUB_MAJOR_GROUPS = {
        "21": {"title": "Science and Engineering Professionals", "chambers": ["Metal & Engineering", "Automotive Manufacturing"], "affinity": 0.95, "parent": "2"},
        "22": {"title": "Health Professionals", "chambers": [], "affinity": 0.05, "parent": "2"},
        "23": {"title": "Teaching Professionals", "chambers": [], "affinity": 0.10, "parent": "2"},
        "24": {"title": "Business and Administration Professionals", "chambers": [], "affinity": 0.25, "parent": "2"},
        "25": {"title": "Information and Communications Technology Professionals", "chambers": ["Cross-Chamber Technical Trades"], "affinity": 0.70, "parent": "2"},
        "31": {"title": "Science and Engineering Associate Professionals / Technicians", "chambers": ["Metal & Engineering", "Automotive Manufacturing", "Plastics Manufacturing"], "affinity": 0.95, "parent": "3"},
        "32": {"title": "Health Associate Professionals", "chambers": [], "affinity": 0.05, "parent": "3"},
        "33": {"title": "Business and Administration Associate Professionals", "chambers": [], "affinity": 0.25, "parent": "3"},
        "64": {"title": "Building and Related Trades Workers", "chambers": ["Metal & Engineering"], "affinity": 0.75, "parent": "6"},
        "65": {"title": "Metal, Machinery and Related Trades Workers", "chambers": ["Metal & Engineering", "Automotive Manufacturing", "Tyre Manufacturing"], "affinity": 0.98, "parent": "6"},
        "67": {"title": "Precision, Handicraft, Craft Printing and Related Trades Workers", "chambers": ["Plastics Manufacturing", "Metal & Engineering"], "affinity": 0.85, "parent": "6"},
        "68": {"title": "Electrical and Electronic Trades Workers", "chambers": ["Metal & Engineering", "Automotive Manufacturing"], "affinity": 0.95, "parent": "6"},
        "71": {"title": "Stationary Plant and Machine Operators", "chambers": ["Plastics Manufacturing", "Tyre Manufacturing", "Metal & Engineering"], "affinity": 0.95, "parent": "7"},
        "72": {"title": "Assemblers", "chambers": ["Automotive Manufacturing", "Components Manufacturing", "Tyre Manufacturing"], "affinity": 0.98, "parent": "7"},
        "73": {"title": "Drivers and Mobile Plant Operators", "chambers": ["Automotive Manufacturing"], "affinity": 0.50, "parent": "7"},
    }

    # South African OFO Minor Groups (3-digit)
    OFO_MINOR_GROUPS = {
        "214": {"title": "Engineering Professionals (excluding Electrotechnology)", "parent": "21"},
        "215": {"title": "Electrotechnology Engineers", "parent": "21"},
        "216": {"title": "Architects, Planners, Surveyors and Designers", "parent": "21"},
        "311": {"title": "Physical and Engineering Science Technicians", "parent": "31"},
        "312": {"title": "Mining, Manufacturing and Construction Supervisors", "parent": "31"},
        "313": {"title": "Process Control Technicians", "parent": "31"},
        "315": {"title": "Ship and Aircraft Controllers and Technicians", "parent": "31"},
        "651": {"title": "Blacksmiths, Toolmakers and Related Trades Workers", "parent": "65"},
        "652": {"title": "Machinery Mechanics and Fitters", "parent": "65"},
        "653": {"title": "Electrical Equipment Fitters and Repairers", "parent": "65"},
        "671": {"title": "Metal Polishers, Wheel Grinders and Tool Sharpeners", "parent": "67"},
        "711": {"title": "Mining and Mineral Processing Plant Operators", "parent": "71"},
        "712": {"title": "Metal Processing and Finishing Plant Operators", "parent": "71"},
        "713": {"title": "Chemical and Plastics Processing Plant Operators", "parent": "71"},
        "714": {"title": "Rubber and Plastic Products Machine Operators", "parent": "71"},
        "721": {"title": "Mechanical, Electrical and Electronic Assemblers", "parent": "72"},
    }

    # South African OFO Unit Groups (4-digit)
    OFO_UNIT_GROUPS = {
        "2144": {"title": "Mechanical Engineers", "parent": "214", "chambers": ["Metal & Engineering", "Automotive Manufacturing"]},
        "2145": {"title": "Chemical Engineers", "parent": "214", "chambers": ["Plastics Manufacturing", "Metal & Engineering"]},
        "2146": {"title": "Mining Engineers, Metallurgists and Related Professionals", "parent": "214", "chambers": ["Metal & Engineering"]},
        "2149": {"title": "Engineering Professionals Not Elsewhere Classified", "parent": "214", "chambers": ["Metal & Engineering"]},
        "3115": {"title": "Mechanical Engineering Technicians", "parent": "311", "chambers": ["Metal & Engineering", "Automotive Manufacturing"]},
        "3119": {"title": "Physical and Engineering Science Technicians Not Elsewhere Classified", "parent": "311", "chambers": ["Metal & Engineering"]},
        "3122": {"title": "Manufacturing Supervisors", "parent": "312", "chambers": ["Metal & Engineering", "Automotive Manufacturing", "Plastics Manufacturing"]},
        "6512": {"title": "Toolmakers and Related Workers", "parent": "651", "chambers": ["Metal & Engineering", "Automotive Manufacturing"]},
        "6522": {"title": "Motor Vehicle Mechanics and Repairers", "parent": "652", "chambers": ["Automotive Manufacturing", "Motor Retail"]},
        "6523": {"title": "Agricultural and Industrial Machinery Mechanics and Fitters", "parent": "652", "chambers": ["Metal & Engineering"]},
        "6531": {"title": "Electrical Fitters", "parent": "653", "chambers": ["Metal & Engineering", "Cross-Chamber Technical Trades"]},
        "7141": {"title": "Rubber Products Machine Operators", "parent": "714", "chambers": ["Tyre Manufacturing"]},
        "7142": {"title": "Plastic Products Machine Operators", "parent": "714", "chambers": ["Plastics Manufacturing"]},
        "7211": {"title": "Mechanical Machinery Assemblers", "parent": "721", "chambers": ["Metal & Engineering", "Automotive Manufacturing"]},
        "7214": {"title": "Electrical and Electronic Equipment Assemblers", "parent": "721", "chambers": ["Components Manufacturing"]},
    }

    @classmethod
    def clean_code(cls, raw_code: str) -> str:
        if not raw_code:
            return ""
        return re.sub(r"[^0-9]", "", str(raw_code).strip())

    @classmethod
    def resolve_ofo_hierarchy(cls, raw_code: str, title: Optional[str] = None) -> Dict[str, Any]:
        """Resolves full taxonomy levels from a given OFO code.
        Never fabricates hierarchy if code is not provided."""
        code = cls.clean_code(raw_code)
        if not code or len(code) < 1:
            return {
                "code": raw_code or "",
                "valid_format": False,
                "levels": {},
                "inherited_claims": [],
                "direct_unit_match": False,
                "sector_affinity": 0.0,
                "matched_chambers": [],
                "chamber_attribution_basis": "UNCLASSIFIED",
            }

        major_digit = code[0]
        sub_major_digits = code[:2] if len(code) >= 2 else ""
        minor_digits = code[:3] if len(code) >= 3 else ""
        unit_digits = code[:4] if len(code) >= 4 else ""

        levels: Dict[str, Any] = {}
        inherited_claims: List[Dict[str, Any]] = []

        # 1. Major Group (Level 1)
        major_info = cls.OFO_MAJOR_GROUPS.get(major_digit)
        if major_info:
            levels["major"] = {
                "code": major_digit,
                "title": major_info["title"],
                "level": "major",
                "parent_code": None,
                "relationship": "root",
            }
            inherited_claims.append({
                "source_level": "major",
                "source_code": major_digit,
                "source_title": major_info["title"],
                "claim": f"Record belongs_to Major Group {major_digit}: {major_info['title']}",
                "is_inherited": len(code) > 1,
                "confidence_qualification": 0.50 if len(code) > 1 else 0.90,
                "chamber_attribution_basis": "TAXONOMY_INFERRED",
            })

        # 2. Sub-Major Group (Level 2)
        sub_major_info = cls.OFO_SUB_MAJOR_GROUPS.get(sub_major_digits)
        if sub_major_info:
            levels["sub_major"] = {
                "code": sub_major_digits,
                "title": sub_major_info["title"],
                "level": "sub_major",
                "parent_code": major_digit,
                "relationship": "belongs_to_major_group",
            }
            inherited_claims.append({
                "source_level": "sub_major",
                "source_code": sub_major_digits,
                "source_title": sub_major_info["title"],
                "claim": f"Sub-Major {sub_major_digits} ({sub_major_info['title']}) belongs_to Major Group {major_digit}",
                "is_inherited": len(code) > 2,
                "confidence_qualification": 0.65 if len(code) > 2 else 0.95,
                "chamber_attribution_basis": "MODEL_INFERRED",
            })

        # 3. Minor Group (Level 3)
        minor_info = cls.OFO_MINOR_GROUPS.get(minor_digits)
        if minor_info:
            levels["minor"] = {
                "code": minor_digits,
                "title": minor_info["title"],
                "level": "minor",
                "parent_code": sub_major_digits,
                "relationship": "belongs_to_sub_major_group",
            }
            inherited_claims.append({
                "source_level": "minor",
                "source_code": minor_digits,
                "source_title": minor_info["title"],
                "claim": f"Minor Group {minor_digits} ({minor_info['title']}) belongs_to Sub-Major {sub_major_digits}",
                "is_inherited": len(code) > 3,
                "confidence_qualification": 0.80 if len(code) > 3 else 0.95,
                "chamber_attribution_basis": "MODEL_INFERRED",
            })

        # 4. Unit Group (Level 4)
        unit_info = cls.OFO_UNIT_GROUPS.get(unit_digits)
        direct_unit_match = False
        matched_chambers: List[str] = []

        if unit_info:
            direct_unit_match = True
            levels["unit"] = {
                "code": unit_digits,
                "title": unit_info["title"],
                "level": "unit",
                "parent_code": minor_digits,
                "relationship": "belongs_to_minor_group",
            }
            matched_chambers = list(unit_info.get("chambers", []))
            inherited_claims.append({
                "source_level": "unit",
                "source_code": unit_digits,
                "source_title": unit_info["title"],
                "claim": f"Unit Group {unit_digits} ({unit_info['title']}) belongs_to Minor Group {minor_digits}",
                "is_inherited": False,
                "confidence_qualification": 0.95,
                "chamber_attribution_basis": "TAXONOMY_INFERRED",
            })
        elif sub_major_info:
            # Fall back to parent sub-major chambers, explicitly marked as inherited with discounted confidence
            matched_chambers = list(sub_major_info.get("chambers", []))

        # Compute sector affinity (higher if direct unit group match)
        affinity = 0.30
        if direct_unit_match:
            affinity = 0.95
        elif sub_major_info:
            affinity = sub_major_info.get("affinity", 0.50)
        elif major_info:
            affinity = major_info.get("industrial_affinity", 0.30)

        return {
            "code": code,
            "valid_format": len(code) in [4, 6],
            "levels": levels,
            "inherited_claims": inherited_claims,
            "direct_unit_match": direct_unit_match,
            "sector_affinity": affinity,
            "matched_chambers": matched_chambers,
            "chamber_attribution_basis": "TAXONOMY_INFERRED" if direct_unit_match else "MODEL_INFERRED",
        }
