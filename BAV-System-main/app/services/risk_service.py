"""
app/services/risk_service.py
─────────────────────────────
Intervention-aware risk + urgency scoring.

New_Classrooms : PTR + overcrowding + infra gap + funding + anomaly
Sanitation     : missing sanitation items + water source + hygiene gap
Lab/Digital    : electricity + internet + funding + anomaly
Repairs        : structural urgency + classrooms condition

PTR weight increased: ptr_component = min(ptr_severity * 40, 40)
Composite school level properly handled.
"""
import sys, logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from config import PTR_THRESHOLDS, RISK_WEIGHTS

log = logging.getLogger(__name__)


def compute_risk_score(school: dict, proposal: dict = None) -> dict:
    proposal = proposal or {}
    intervention = proposal.get("intervention_type", "New_Classrooms")

    total_students  = float(school.get("total_students", 0))
    total_tch       = max(float(school.get("total_tch", 1)), 1)
    classrooms      = max(float(school.get("classrooms_total", 1)), 1)

    # Composite level fix
    school_level = school.get("school_level", "primary")
    if total_students > 1000 and school_level == "primary":
        school_level = "composite"

    ptr           = total_students / total_tch
    ptr_threshold = PTR_THRESHOLDS.get(school_level, 35)
    ptr_severity  = max((ptr - ptr_threshold) / ptr_threshold, 0)
    spc           = total_students / classrooms
    infra_gap     = float(school.get("infrastructure_gap", 0))

    eligible_norm = _get_eligible_ceiling(total_students, intervention, proposal)
    funding_req   = float(proposal.get("funding_requested", eligible_norm))
    funding_ratio = funding_req / eligible_norm if eligible_norm > 0 else 1.0
    funding_excess= max(funding_ratio - 1.0, 0)
    anomaly_flag  = float(school.get("is_anomaly", 0))
    udise_ok      = bool(proposal.get("udise_data_verified", True))
    compliance_penalty = 0 if udise_ok else RISK_WEIGHTS["udise_compliance"]

    # ── Intervention-specific scoring
    if intervention == "New_Classrooms":
        # PTR component — fixed weight: severity * 40, max 40
        ptr_comp    = min(ptr_severity * 40, 40)
        infra_comp  = min((infra_gap / 6) * 20, 20)
        fund_comp   = min((funding_excess / 4) * 20, 20)
        overcrowd   = min(max((spc - 40) / 40 * 15, 0), 15)
        anomaly_comp= anomaly_flag * 5
        risk_score  = ptr_comp + infra_comp + fund_comp + overcrowd + anomaly_comp + compliance_penalty

        urgency = 0
        if school.get("has_girls_toilet", 1) == 0: urgency += 20
        if school.get("has_ramp",         1) == 0: urgency += 15
        if school.get("has_electricity",  1) == 0: urgency += 15
        if ptr > ptr_threshold * 1.5:              urgency += 30
        elif ptr > ptr_threshold:                  urgency += 15
        if spc > 55:   urgency += 20
        elif spc > 45: urgency += 10

        breakdown = {
            "ptr_component":      round(ptr_comp, 2),
            "infra_component":    round(infra_comp, 2),
            "funding_component":  round(fund_comp, 2),
            "overcrowding":       round(overcrowd, 2),
            "anomaly_component":  round(anomaly_comp, 2),
            "compliance_penalty": round(compliance_penalty, 2),
        }

    elif intervention == "Sanitation":
        # Sanitation risk: missing items + water + hygiene
        missing_girls = 1 if school.get("has_girls_toilet", 1) == 0 else 0
        missing_boys  = 1 if school.get("has_boys_toilet",  1) == 0 else 0
        missing_wash  = 1 if school.get("has_handwash",     1) == 0 else 0
        missing_ramp  = 1 if school.get("has_ramp",         1) == 0 else 0
        sanit_gap     = missing_girls * 30 + missing_boys * 20 + missing_wash * 15 + missing_ramp * 10
        fund_comp     = min((funding_excess / 4) * 15, 15)
        anomaly_comp  = anomaly_flag * 5
        risk_score    = min(sanit_gap + fund_comp + anomaly_comp + compliance_penalty, 100)

        urgency = sanit_gap  # directly driven by missing items
        if missing_girls: urgency += 20  # extra urgency for RTE mandatory

        breakdown = {
            "missing_girls_toilet": missing_girls * 30,
            "missing_boys_toilet":  missing_boys * 20,
            "missing_handwash":     missing_wash * 15,
            "missing_ramp":         missing_ramp * 10,
            "funding_component":    round(fund_comp, 2),
            "anomaly_component":    round(anomaly_comp, 2),
            "compliance_penalty":   round(compliance_penalty, 2),
        }

    elif intervention in ("Lab", "Digital"):
        elec_missing = 1 if school.get("has_electricity", 1) == 0 else 0
        inet_missing = 1 if school.get("has_internet",    1) == 0 else 0
        elec_comp    = elec_missing * 40
        inet_comp    = inet_missing * 15 if intervention == "Digital" else 0
        fund_comp    = min((funding_excess / 4) * 20, 20)
        anomaly_comp = anomaly_flag * 5
        risk_score   = min(elec_comp + inet_comp + fund_comp + anomaly_comp + compliance_penalty, 100)

        urgency = 0
        if school.get("has_girls_toilet", 1) == 0: urgency += 25
        if elec_missing:                            urgency += 30

        breakdown = {
            "electricity_missing": elec_comp,
            "internet_missing":    inet_comp,
            "funding_component":   round(fund_comp, 2),
            "anomaly_component":   round(anomaly_comp, 2),
            "compliance_penalty":  round(compliance_penalty, 2),
        }

    elif intervention == "Repairs":
        # Repairs risk: infra gap + structural urgency
        infra_comp   = min((infra_gap / 6) * 30, 30)
        fund_comp    = min((funding_excess / 4) * 20, 20)
        anomaly_comp = anomaly_flag * 5
        risk_score   = min(infra_comp + fund_comp + anomaly_comp + compliance_penalty, 100)

        urgency = 0
        if school.get("has_girls_toilet", 1) == 0: urgency += 25
        if infra_gap >= 3: urgency += 30

        breakdown = {
            "infra_component":    round(infra_comp, 2),
            "funding_component":  round(fund_comp, 2),
            "anomaly_component":  round(anomaly_comp, 2),
            "compliance_penalty": round(compliance_penalty, 2),
        }

    else:
        # Generic fallback
        ptr_comp    = min(ptr_severity * 25, 25)
        infra_comp  = min((infra_gap / 6) * 20, 20)
        fund_comp   = min((funding_excess / 4) * 25, 25)
        anomaly_comp= anomaly_flag * 15
        risk_score  = ptr_comp + infra_comp + fund_comp + anomaly_comp + compliance_penalty
        urgency     = min(ptr_severity * 50 + infra_gap * 10, 100)
        breakdown   = {"ptr_component":round(ptr_comp,2),"infra_component":round(infra_comp,2),"funding_component":round(fund_comp,2),"anomaly_component":round(anomaly_comp,2),"compliance_penalty":round(compliance_penalty,2)}

    risk_score   = round(min(risk_score, 100), 2)
    urgency_score= round(min(urgency, 100), 2)
    risk_level   = "High" if risk_score >= 70 else "Medium" if risk_score >= 30 else "Low"

    return {
        "risk_score":    risk_score,
        "urgency_score": urgency_score,
        "risk_level":    risk_level,
        "breakdown":     breakdown,
        "key_metrics": {
            "ptr":                    round(ptr, 2),
            "ptr_threshold":          ptr_threshold,
            "students_per_classroom": round(spc, 2),
            "infrastructure_gap":     infra_gap,
            "funding_ratio":          round(funding_ratio, 2),
            "eligible_grant_norm":    eligible_norm,
            "school_level_used":      school_level,
        },
    }


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