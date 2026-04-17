"""
app/utils/rule_engine.py
────────────────────────
Fully intervention-aware Samagra Shiksha validation.

Each intervention type has its own check set:
  New_Classrooms → PTR, overcrowding, over-provisioning, land, construction
  Repairs        → structural urgency, repair scope, cost reasonableness
  Sanitation     → toilet types, water source, swachh bharat compliance
  Lab            → electricity, lab type justification, student count
  Digital        → electricity, internet, teacher ICT training, device count

Girls toilet missing = SUPPORTING evidence for sanitation proposals
Girls toilet missing = CRITICAL violation for all other proposals

PTR and classroom density checks ONLY run for New_Classrooms.
"""
import re, sys, logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from config import PTR_THRESHOLDS, MAX_FUNDING_RATIO

log = logging.getLogger(__name__)


@dataclass
class RuleViolation:
    code:     str
    severity: str   # "critical" | "warning" | "info" | "supporting"
    message:  str
    field:    str


@dataclass
class RuleResult:
    verdict:       str
    violations:    List[RuleViolation] = field(default_factory=list)
    score_penalty: float = 0.0
    checks_run:    List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "verdict":      self.verdict,
            "score_penalty":self.score_penalty,
            "checks_run":   self.checks_run,
            "violations": [
                {"code":v.code,"severity":v.severity,"message":v.message,"field":v.field}
                for v in self.violations
            ],
        }


# ─────────────────────────────────────────────────────────────
# INTERVENTION ROUTING
# ─────────────────────────────────────────────────────────────

INTERVENTION_CHECKS = {
    "New_Classrooms": ["common","ptr","overcrowding","over_provisioning","construction","girls_toilet_critical"],
    "Repairs":        ["common","repair_scope","structural","girls_toilet_warning"],
    "Sanitation":     ["common","sanitation_specific","girls_toilet_supporting"],
    "Lab":            ["common","electricity_required","lab_specific","girls_toilet_critical"],
    "Digital":        ["common","electricity_required","digital_specific","girls_toilet_critical"],
}


def validate(school: dict, proposal: dict, existing_proposals=None) -> RuleResult:
    violations: List[RuleViolation] = []
    penalty   = 0.0
    reject    = False

    total_students  = float(school.get("total_students", 0))
    total_tch       = max(float(school.get("total_tch", 1)), 1)
    classrooms      = max(float(school.get("classrooms_total", 1)), 1)

    # ── Infer composite level for large schools
    school_level = school.get("school_level", "primary")
    if total_students > 1000 and school_level == "primary":
        school_level = "composite"
        log.info(f"School {school.get('pseudocode','?')}: level inferred as composite (>{total_students} students)")

    ptr           = total_students / total_tch
    ptr_threshold = PTR_THRESHOLDS.get(school_level, PTR_THRESHOLDS.get("upper_primary", 35))

    intervention  = proposal.get("intervention_type", "New_Classrooms")
    dynamic       = proposal.get("dynamic_fields", {}) or {}
    funding_req   = float(proposal.get("funding_requested", 0))
    udise_verified= bool(proposal.get("udise_data_verified", False))
    proposal_letter = proposal.get("proposal_letter", "") or ""

    eligible_norm = _get_eligible_ceiling(total_students, intervention, proposal)
    funding_ratio = funding_req / eligible_norm if eligible_norm > 0 else 0

    checks_to_run = INTERVENTION_CHECKS.get(intervention, INTERVENTION_CHECKS["New_Classrooms"])

    # ════════════ COMMON CHECKS (all interventions)
    if "common" in checks_to_run:
        # C001: Zero enrollment
        if total_students <= 0:
            violations.append(RuleViolation("C001","critical","Zero student enrollment — proposal not eligible.","total_students"))
            penalty += 30; reject = True

        # C004: UDISE not verified
        if not udise_verified:
            violations.append(RuleViolation("C004","critical",
                "Proposal data not verified against UDISE+ dashboard. "
                "All DBT funding requires UDISE+ verification. Update before resubmitting.",
                "udise_data_verified"))
            penalty += 20; reject = True

        # C003: Funding massively over ceiling
        if funding_ratio > MAX_FUNDING_RATIO and funding_req > 0:
            violations.append(RuleViolation("C003","critical",
                f"Funding ₹{funding_req:,.0f} is {funding_ratio:.1f}× the eligible ceiling "
                f"₹{eligible_norm:,.0f}. Exceeds maximum ratio of {MAX_FUNDING_RATIO}×.",
                "funding_requested"))
            penalty += 20; reject = True

        # W_FUNDING: Funding ratio 1.2–5× (flag range)
        elif 1.2 < funding_ratio <= MAX_FUNDING_RATIO:
            violations.append(RuleViolation("W_FUNDING","warning",
                f"Funding ₹{funding_req:,.0f} is {funding_ratio:.1f}× eligible ceiling "
                f"₹{eligible_norm:,.0f}. Justification required for amount above norm.",
                "funding_requested"))
            penalty += 10

    # W_BUDGET_LOW: Unrealistically low budget (applies to all interventions)
    if funding_req > 0 and funding_req < 5000:
        violations.append(RuleViolation("C_BUDGET","critical",
            f"Funding request ₹{funding_req:,.0f} is unrealistically low for any "
            f"school infrastructure intervention. Minimum viable budget is ₹5,000. "
            f"Please verify the amount entered.",
            "funding_requested"))
        penalty += 25; reject = True
    elif funding_req > 0:
        # Check against SOR minimum (30% of base cost)
        from config import INTERVENTION_COST_NORMS
        norm = INTERVENTION_COST_NORMS.get(intervention)
        if norm:
            dynamic = proposal.get("dynamic_fields", {}) or {}
            units = max(int(
                dynamic.get("classrooms_requested",
                dynamic.get("rooms_to_repair",
                dynamic.get("toilet_seats_requested",
                dynamic.get("devices_requested",
                proposal.get("classrooms_requested", 1))))) or 1
            ), 1)
            units = min(units, norm["max_units"])
            min_viable = norm["per_unit"] * units * 0.25  # 25% of SOR = absolute minimum
            if funding_req < min_viable:
                violations.append(RuleViolation("W_BUDGET_LOW","warning",
                    f"Budget ₹{funding_req:,.0f} is far below the minimum viable cost for "
                    f"{units} {norm['unit']}(s). Minimum expected: ₹{min_viable:,.0f} "
                    f"(25% of Schedule of Rates). Risk of incomplete construction.",
                    "funding_requested"))
                penalty += 12

        # C007: SMC resolution
        if proposal.get("smc_resolution_attached") is False:
            violations.append(RuleViolation("C007","critical",
                "SMC resolution not attached — mandatory Samagra Shiksha requirement.",
                "smc_resolution_attached"))
            penalty += 15; reject = True

        # W010: Previous grant not utilized
        if proposal.get("previous_grant_utilized") is False:
            violations.append(RuleViolation("W010","warning",
                "Previous year's grant was not fully utilized. "
                "Explain utilization before new funds are sanctioned.",
                "previous_grant_utilized"))
            penalty += 8

    # ════════════ NEW CLASSROOMS CHECKS
    if "ptr" in checks_to_run:
        critical_ptr = ptr_threshold * 1.5
        if ptr > critical_ptr:
            violations.append(RuleViolation("C002","critical",
                f"PTR {ptr:.1f} exceeds critical limit {critical_ptr:.1f} for {school_level} "
                f"(norm: {ptr_threshold}). Teacher deployment required before construction funding.",
                "ptr"))
            penalty += 25; reject = True
        elif ptr > ptr_threshold:
            violations.append(RuleViolation("W001","warning",
                f"PTR {ptr:.1f} exceeds {school_level} norm {ptr_threshold}. "
                f"Include teacher recruitment plan with construction proposal.",
                "ptr"))
            penalty += 10

    if "overcrowding" in checks_to_run:
        spc = total_students / classrooms
        if spc > 50:
            violations.append(RuleViolation("W005","warning",
                f"Severe overcrowding: {spc:.0f} students/classroom (max 40). Construction justified.",
                "students_per_classroom"))
            penalty += 7
        elif spc > 40:
            violations.append(RuleViolation("W006","warning",
                f"Overcrowding: {spc:.0f} students/classroom (recommended max 40).",
                "students_per_classroom"))
            penalty += 3

    if "over_provisioning" in checks_to_run:
        classrooms_req = int(dynamic.get("classrooms_requested",
                             proposal.get("classrooms_requested", 0)) or 0)
        if classrooms_req > 0:
            rooms_needed = max(0, round(total_students / 40) - classrooms)
            excess = classrooms_req - rooms_needed
            if excess > 3:
                violations.append(RuleViolation("W007","warning",
                    f"Over-provisioning: school needs ~{rooms_needed:.0f} room(s) but requesting {classrooms_req}. "
                    f"Excess of {excess} rooms for {int(total_students)} students requires justification.",
                    "classrooms_requested"))
                penalty += 10
            # Letter vs form mismatch
            if proposal_letter and classrooms_req > 0:
                matches = re.findall(r"(\d+)\s*(?:new\s+)?classroom", proposal_letter.lower())
                mismatches = [int(m) for m in matches if int(m) != classrooms_req]
                if mismatches:
                    violations.append(RuleViolation("W_FRAUD","warning",
                        f"Inconsistency: form requests {classrooms_req} classrooms but letter mentions "
                        f"{mismatches[0]}. Possible data entry error or fraudulent submission.",
                        "classrooms_requested"))
                    penalty += 15

    if "construction" in checks_to_run:
        # Required: construction_type
        if not dynamic.get("construction_type"):
            violations.append(RuleViolation("W_CONTYPE","warning",
                "Construction type not specified (Pucca/Semi-pucca/Prefab). "
                "Required for cost estimation and SOR compliance.",
                "construction_type"))
            penalty += 8

        # Required: land availability confirmed
        if not dynamic.get("land_available"):
            violations.append(RuleViolation("W_LAND","warning",
                "Land availability not confirmed. Construction proposals require "
                "explicit confirmation that land is available.",
                "land_available"))
            penalty += 8
        elif dynamic.get("land_available") == "No":
            violations.append(RuleViolation("C008","critical",
                "Land not available for construction. Proposal cannot proceed without confirmed land.",
                "land_available"))
            penalty += 20; reject = True

        # Required: classrooms_requested > 0
        classrooms_req_val = int(dynamic.get("classrooms_requested",
                                  proposal.get("classrooms_requested", 0)) or 0)
        if classrooms_req_val <= 0:
            violations.append(RuleViolation("W_NROOMS","warning",
                "Number of classrooms requested not specified. "
                "Enter the number of new classrooms needed.",
                "classrooms_requested"))
            penalty += 5

    # ════════════ GIRLS TOILET — CRITICAL (construction/lab/digital only)
    if "girls_toilet_critical" in checks_to_run:
        if school.get("has_girls_toilet", 1) == 0:
            has_active_sanitation = proposal.get("has_active_sanitation_proposal", False)
            if has_active_sanitation:
                violations.append(RuleViolation("I_SANITATION_PENDING","info",
                    "Girls toilet absent — however a sanitation proposal is already active. "
                    "Sanitation concern is being addressed. This proposal can proceed.",
                    "has_girls_toilet"))
            else:
                violations.append(RuleViolation("C005","critical",
                    "No functional girls toilet — CRITICAL. Government policy: sanitation before construction. "
                    "Address girls toilet before requesting other infrastructure funds.",
                    "has_girls_toilet"))
                penalty += 20; reject = True

    # ════════════ GIRLS TOILET — WARNING only (repairs — don't block structural work)
    if "girls_toilet_warning" in checks_to_run:
        if school.get("has_girls_toilet", 1) == 0:
            has_active_sanitation = proposal.get("has_active_sanitation_proposal", False)
            if has_active_sanitation:
                violations.append(RuleViolation("I_SANITATION_PENDING","info",
                    "Girls toilet absent — a sanitation proposal is already active for this school. "
                    "This repair proposal can proceed in parallel.",
                    "has_girls_toilet"))
            else:
                violations.append(RuleViolation("W_TOILET","warning",
                    "No functional girls toilet. While this repair proposal is valid, "
                    "a separate sanitation proposal should be submitted to address this "
                    "mandatory RTE Act requirement.",
                    "has_girls_toilet"))
                penalty += 8

    # ════════════ GIRLS TOILET — SUPPORTING EVIDENCE (sanitation proposals)
    if "girls_toilet_supporting" in checks_to_run:
        if school.get("has_girls_toilet", 1) == 0:
            sanitation_types = dynamic.get("sanitation_type", []) or []
            if isinstance(sanitation_types, list) and any("girl" in s.lower() for s in sanitation_types):
                violations.append(RuleViolation("S001","supporting",
                    "Girls toilet absent — this proposal correctly addresses that critical gap. "
                    "Priority funding is recommended under RTE Act mandate.",
                    "has_girls_toilet"))
            else:
                violations.append(RuleViolation("W_SANTYPE","warning",
                    "Girls toilet absent but proposal does not include girls toilet in sanitation_type. "
                    "Add girls toilet to the sanitation items requested.",
                    "sanitation_type"))
                penalty += 10

    # ════════════ SANITATION-SPECIFIC CHECKS
    if "sanitation_specific" in checks_to_run:
        # Check individual sanitation checkboxes from form
        has_girls_toilet = bool(dynamic.get("has_girls_toilet", False))
        has_boys_toilet = bool(dynamic.get("has_boys_toilet", False))
        has_handwash = bool(dynamic.get("has_handwash", False))
        has_drinking_water = bool(dynamic.get("has_drinking_water", False))
        
        # Legacy support: also check for sanitation_type array
        sanitation_types = dynamic.get("sanitation_type", []) or []
        toilet_seats     = int(dynamic.get("toilet_seats_requested", 0) or 0)

        # Check if ANY sanitation items were selected (either via checkboxes or legacy format)
        any_items_selected = (has_girls_toilet or has_boys_toilet or has_handwash or 
                             has_drinking_water or bool(sanitation_types))

        if not any_items_selected:
            violations.append(RuleViolation("W_SANTYPE2","warning",
                "No sanitation items selected. Specify what is being requested "
                "(girls toilet, boys toilet, handwash, drinking water, etc.).",
                "sanitation_items"))
            penalty += 10

        if toilet_seats == 0 and any_items_selected:
            violations.append(RuleViolation("W_SEATS","warning",
                "Number of toilet seats/units not specified. Required for cost estimation.",
                "toilet_seats_requested"))
            penalty += 5

        if dynamic.get("water_source_available") == "No":
            violations.append(RuleViolation("W_WATER","warning",
                "No water source available. Sanitation infrastructure requires confirmed water connection.",
                "water_source_available"))
            penalty += 12

        # CWSN ramp — always a consideration
        if school.get("has_ramp", 1) == 0:
            violations.append(RuleViolation("I003","info",
                "CWSN ramp missing — consider including barrier-free access in this sanitation proposal.",
                "has_ramp"))

    # ════════════ ELECTRICITY REQUIRED (Lab, Digital)
    if "electricity_required" in checks_to_run:
        if school.get("has_electricity", 1) == 0:
            violations.append(RuleViolation("C006","critical",
                f"{intervention} infrastructure requires electricity. "
                f"Power supply must be established before this proposal can proceed.",
                "has_electricity"))
            penalty += 20; reject = True

    # ════════════ LAB-SPECIFIC CHECKS
    if "lab_specific" in checks_to_run:
        lab_type = dynamic.get("lab_type", "")
        if not lab_type:
            violations.append(RuleViolation("W_LAB","warning",
                "Lab type not specified. Select from: Science, Mathematics, Computer, Language, Geography.",
                "lab_type"))
            penalty += 8

        # Computer lab without internet
        if lab_type == "Computer" and school.get("has_internet", 1) == 0:
            violations.append(RuleViolation("W_INET","warning",
                "Computer lab requested but school has no internet connection. "
                "Include internet connectivity in the proposal.",
                "has_internet"))
            penalty += 8

        # Lab for primary school
        if school_level == "primary" and lab_type in ("Science", "Chemistry", "Physics"):
            violations.append(RuleViolation("W_LABPRI","warning",
                f"{lab_type} lab unusual for primary level. "
                f"Verify this is appropriate for the school level.",
                "lab_type"))
            penalty += 5

    # ════════════ DIGITAL-SPECIFIC CHECKS
    if "digital_specific" in checks_to_run:
        digital_types   = dynamic.get("digital_type", []) or []
        devices_req     = int(dynamic.get("devices_requested", 0) or 0)
        ict_trained     = dynamic.get("teacher_ict_trained", "")

        if not digital_types:
            violations.append(RuleViolation("W_DIGTYPE","warning",
                "No device types selected. Specify devices requested.",
                "digital_type"))
            penalty += 8

        if devices_req == 0:
            violations.append(RuleViolation("W_DEVICES","warning",
                "Number of devices not specified. Required for cost validation.",
                "devices_requested"))
            penalty += 5

        if ict_trained == "No":
            violations.append(RuleViolation("W_ICT","warning",
                "No ICT-trained teacher. Devices without trained staff will be underutilized. "
                "Include teacher training plan.",
                "teacher_ict_trained"))
            penalty += 8

        if school.get("has_internet", 1) == 0 and "Internet Connection" not in digital_types:
            violations.append(RuleViolation("W_INET2","warning",
                "No internet connection — include internet connectivity in this digital proposal.",
                "has_internet"))
            penalty += 5

    # ════════════ REPAIRS-SPECIFIC CHECKS
    if "repair_scope" in checks_to_run:
        repair_types  = dynamic.get("repair_type", []) or []
        rooms_repair  = int(dynamic.get("rooms_to_repair", 0) or 0)

        if not repair_types:
            violations.append(RuleViolation("W_REPTYPE","warning",
                "Repair type not specified. Select from: Roof, Walls, Flooring, etc.",
                "repair_type"))
            penalty += 8

        if rooms_repair == 0:
            violations.append(RuleViolation("W_ROOMS","warning",
                "Number of rooms to repair not specified.",
                "rooms_to_repair"))
            penalty += 5

    if "structural" in checks_to_run:
        urgency = dynamic.get("repair_urgency", "")
        if "Major" in urgency and not dynamic.get("structural_assessment_done") == "Yes":
            violations.append(RuleViolation("W_STRUCT","warning",
                "Major structural repair requested but no structural assessment attached. "
                "Civil engineer assessment required for major repairs.",
                "structural_assessment_done"))
            penalty += 10

    # ════════════ COMMON INFRASTRUCTURE INFO (all types)
    if school.get("has_library", 1) == 0:
        violations.append(RuleViolation("I001","info",
            "Library absent. Annual grant ₹5,000–₹20,000 available under Samagra Shiksha.",
            "has_library"))
    if school.get("has_boundary_wall", 1) == 0:
        violations.append(RuleViolation("I002","info",
            "Boundary wall absent — required for school safety.",
            "has_boundary_wall"))

    # ════════════ DETERMINE VERDICT
    # Supporting evidence and info never affect verdict
    critical_count = sum(1 for v in violations if v.severity == "critical")
    warning_count  = sum(1 for v in violations if v.severity == "warning")

    if reject or critical_count >= 1:
        verdict = "Reject"
    elif warning_count >= 1:
        verdict = "Flag"
    else:
        verdict = "Accept"

    return RuleResult(
        verdict=verdict,
        violations=violations,
        score_penalty=round(penalty, 2),
        checks_run=checks_to_run,
    )


# ─────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────

def _get_grant_norm(total_students: float) -> float:
    from config import GRANT_NORMS
    for threshold, amount in GRANT_NORMS:
        if total_students <= threshold:
            return float(amount)
    return float(GRANT_NORMS[-1][1])


def _get_eligible_ceiling(total_students: float, intervention_type: str, proposal: dict) -> float:
    from config import INTERVENTION_COST_NORMS, COMPOSITE_GRANT_MULTIPLIER
    norm = INTERVENTION_COST_NORMS.get(intervention_type)
    if norm:
        dynamic = proposal.get("dynamic_fields", {}) or {}
        units = max(int(
            dynamic.get("classrooms_requested",
            dynamic.get("rooms_to_repair",
            dynamic.get("toilet_seats_requested",
            dynamic.get("devices_requested",
            proposal.get("classrooms_requested", 1))))) or 1
        ), 1)
        units = min(units, norm["max_units"])
        return float(norm["per_unit"] * units)
    return _get_grant_norm(total_students) * COMPOSITE_GRANT_MULTIPLIER