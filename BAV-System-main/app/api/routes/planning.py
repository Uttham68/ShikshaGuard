"""
app/api/routes/planning.py
───────────────────────────
Endpoints for multi-level planning:
  GET /planning/district          — district-level aggregated stats
  GET /planning/block             — block-level breakdown
  GET /planning/state-summary     — state-level overview
  GET /planning/gap-analysis      — infrastructure demand estimation
  GET /planning/prioritize        — ranked schools by urgency + risk
  GET /planning/alerts            — continuous monitoring alerts
"""

import sys
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

log = logging.getLogger(__name__)
from app.database.db import get_db
from app.database.models import School, Proposal, ValidationResult
from config import PTR_THRESHOLDS

router = APIRouter(prefix="/planning", tags=["Planning"])


def _school_display_name(school: School, db: Session) -> str:
    proposal = (
        db.query(Proposal.school_name)
        .filter(Proposal.school_pseudocode == school.pseudocode)
        .order_by(Proposal.submitted_at.desc())
        .first()
    )
    if proposal and proposal.school_name:
        return proposal.school_name
    return f"School {school.pseudocode}"


# ─────────────────────────────────────────────────────────────
# HELPER — aggregate schools into planning metrics
# ─────────────────────────────────────────────────────────────

def _aggregate_schools(schools: list) -> dict:
    if not schools:
        return {}

    total = len(schools)
    high_risk    = sum(1 for s in schools if s.risk_level == "High")
    medium_risk  = sum(1 for s in schools if s.risk_level == "Medium")
    low_risk     = sum(1 for s in schools if s.risk_level == "Low")
    total_students = sum(s.total_students or 0 for s in schools)
    total_teachers = sum(s.total_tch or 0 for s in schools)

    # Infrastructure gap counts
    missing_girls_toilet = sum(1 for s in schools if (s.has_girls_toilet or 0) == 0)
    missing_boys_toilet  = sum(1 for s in schools if (s.has_boys_toilet  or 0) == 0)
    missing_ramp         = sum(1 for s in schools if (s.has_ramp         or 0) == 0)
    missing_library      = sum(1 for s in schools if (s.has_library      or 0) == 0)
    missing_electricity  = sum(1 for s in schools if (s.has_electricity  or 0) == 0)
    missing_boundary     = sum(1 for s in schools if (s.has_boundary_wall or 0) == 0)

    # Classrooms needed (target: 40 students/room)
    classrooms_needed = sum(
        max(0, round(s.total_students / 40) - (s.classrooms_total or 1))
        for s in schools
    )

    # Teachers needed based on PTR thresholds
    teachers_needed = 0
    for s in schools:
        threshold = PTR_THRESHOLDS.get(s.school_level or "primary", 35)
        needed = max(0, round((s.total_students or 0) / threshold) - (s.total_tch or 0))
        teachers_needed += needed

    avg_ptr  = sum(s.ptr or 0 for s in schools) / total if total else 0
    avg_risk = sum(s.risk_score or 0 for s in schools) / total if total else 0
    avg_gap  = sum(s.infrastructure_gap or 0 for s in schools) / total if total else 0

    return {
        "total_schools":        total,
        "total_students":       int(total_students),
        "total_teachers":       int(total_teachers),
        "avg_ptr":              round(avg_ptr, 2),
        "avg_risk_score":       round(avg_risk, 2),
        "avg_infrastructure_gap": round(avg_gap, 2),
        "risk_breakdown": {
            "High":   high_risk,
            "Medium": medium_risk,
            "Low":    low_risk,
        },
        "infrastructure_demand": {
            "classrooms_needed":       int(classrooms_needed),
            "teachers_needed":         int(teachers_needed),
            "schools_missing_girls_toilet": missing_girls_toilet,
            "schools_missing_boys_toilet":  missing_boys_toilet,
            "schools_missing_ramp":         missing_ramp,
            "schools_missing_library":      missing_library,
            "schools_missing_electricity":  missing_electricity,
            "schools_missing_boundary_wall":missing_boundary,
        },
    }


# ─────────────────────────────────────────────────────────────
# 1. STATE SUMMARY
# ─────────────────────────────────────────────────────────────

@router.get("/state-summary")
def state_summary(db: Session = Depends(get_db)):
    """State-level aggregated overview of all schools."""
    schools = db.query(School).all()
    agg = _aggregate_schools(schools)

    # Proposal stats
    total_proposals  = db.query(Proposal).count()
    total_validated  = db.query(ValidationResult).count()
    pending          = db.query(Proposal).filter(Proposal.status == "Pending").count()

    return {
        "level": "state",
        "generated_at": datetime.utcnow().isoformat(),
        "schools": agg,
        "proposals": {
            "total":     total_proposals,
            "validated": total_validated,
            "pending":   pending,
        },
        "headline": (
            f"{agg.get('total_schools',0)} schools tracked. "
            f"{agg['infrastructure_demand']['classrooms_needed']} classrooms needed. "
            f"{agg['risk_breakdown']['High']} high-risk schools require immediate action."
        ),
    }


# ─────────────────────────────────────────────────────────────
# 2. GAP ANALYSIS — INFRASTRUCTURE DEMAND
# ─────────────────────────────────────────────────────────────

@router.get("/gap-analysis")
def gap_analysis(
    level: Optional[str] = Query(None, description="primary / upper_primary / secondary"),
    db: Session = Depends(get_db),
):
    """
    District-wide infrastructure gap estimation.
    Shows exactly what needs to be built / provided.
    """
    query = db.query(School)
    if level:
        query = query.filter(School.school_level == level)
    schools = query.all()

    agg = _aggregate_schools(schools)
    demand = agg.get("infrastructure_demand", {})

    # Estimate cost at SOR rates
    from config import INTERVENTION_COST_NORMS
    classroom_cost = demand.get("classrooms_needed", 0) * INTERVENTION_COST_NORMS["New_Classrooms"]["per_unit"]
    toilet_cost    = demand.get("schools_missing_girls_toilet", 0) * INTERVENTION_COST_NORMS["Sanitation"]["per_unit"]

    return {
        "filter_level":     level or "all",
        "total_schools":    agg.get("total_schools", 0),
        "demand": demand,
        "estimated_cost": {
            "classroom_construction": classroom_cost,
            "sanitation":             toilet_cost,
            "total_estimated":        classroom_cost + toilet_cost,
            "currency":               "INR",
            "note":                   "Based on Samagra Shiksha Schedule of Rates",
        },
        "top_gaps": _rank_gaps(demand),
    }


def _rank_gaps(demand: dict) -> list:
    """Return gaps sorted by severity."""
    items = [
        {"item": "Classrooms",     "schools_affected": demand.get("classrooms_needed", 0),              "priority": 1},
        {"item": "Girls Toilets",  "schools_affected": demand.get("schools_missing_girls_toilet", 0),   "priority": 2},
        {"item": "Boys Toilets",   "schools_affected": demand.get("schools_missing_boys_toilet", 0),    "priority": 3},
        {"item": "CWSN Ramps",     "schools_affected": demand.get("schools_missing_ramp", 0),           "priority": 4},
        {"item": "Electricity",    "schools_affected": demand.get("schools_missing_electricity", 0),    "priority": 5},
        {"item": "Library",        "schools_affected": demand.get("schools_missing_library", 0),        "priority": 6},
        {"item": "Boundary Wall",  "schools_affected": demand.get("schools_missing_boundary_wall", 0),  "priority": 7},
    ]
    return sorted(items, key=lambda x: x["schools_affected"], reverse=True)


# ─────────────────────────────────────────────────────────────
# 3. PRIORITIZATION ENGINE
# ─────────────────────────────────────────────────────────────

@router.get("/prioritize")
def prioritize_schools(
    top_n:      int            = Query(20, ge=1, le=100),
    level:      Optional[str]  = Query(None),
    min_risk:   Optional[float]= Query(None),
    db: Session = Depends(get_db),
):
    """
    Rank schools by combined urgency + risk score.
    Prioritization score = risk_score × 0.4 + urgency_proxy × 0.4 + gap × 0.2
    """
    query = db.query(School)
    if level:
        query = query.filter(School.school_level == level)
    if min_risk:
        query = query.filter(School.risk_score >= min_risk)

    schools = query.all()

    ranked = []
    for s in schools:
        # Urgency proxy: overcrowding + missing critical items
        spc = (s.total_students or 0) / max(s.classrooms_total or 1, 1)
        ptr = s.ptr or 0
        threshold = PTR_THRESHOLDS.get(s.school_level or "primary", 35)

        urgency = 0
        if (s.has_girls_toilet or 0) == 0:  urgency += 30
        if (s.has_ramp or 0) == 0:          urgency += 15
        if (s.has_electricity or 0) == 0:   urgency += 15
        if ptr > threshold * 1.5:           urgency += 30
        elif ptr > threshold:               urgency += 15
        if spc > 55:                        urgency += 20
        elif spc > 45:                      urgency += 10

        # Prioritization score
        gap_score = (s.infrastructure_gap or 0) / 6 * 100
        priority_score = (
            (s.risk_score or 0) * 0.4 +
            min(urgency, 100) * 0.4 +
            gap_score * 0.2
        )

        ranked.append({
            "rank":              0,
            "pseudocode":        s.pseudocode,
            "school_name":       _school_display_name(s, db),
            "school_level":      s.school_level,
            "total_students":    int(s.total_students or 0),
            "ptr":               round(ptr, 2),
            "ptr_status":        "CRITICAL" if ptr > threshold * 1.5 else ("HIGH" if ptr > threshold else "OK"),
            "students_per_room": round(spc, 1),
            "risk_score":        s.risk_score,
            "risk_level":        s.risk_level,
            "urgency_score":     min(urgency, 100),
            "priority_score":    round(priority_score, 2),
            "infrastructure_gap":s.infrastructure_gap,
            "missing_items":     _missing_items(s),
        })

    ranked.sort(key=lambda x: x["priority_score"], reverse=True)
    for i, r in enumerate(ranked[:top_n], 1):
        r["rank"] = i

    return {
        "total_schools_ranked": len(ranked),
        "showing":              min(top_n, len(ranked)),
        "top_priority":         ranked[:top_n],
        "generated_at":         datetime.utcnow().isoformat(),
    }


def _missing_items(s: School) -> list:
    items = []
    if (s.has_girls_toilet  or 0) == 0: items.append("Girls toilet")
    if (s.has_boys_toilet   or 0) == 0: items.append("Boys toilet")
    if (s.has_ramp          or 0) == 0: items.append("CWSN ramp")
    if (s.has_library       or 0) == 0: items.append("Library")
    if (s.has_electricity   or 0) == 0: items.append("Electricity")
    if (s.has_boundary_wall or 0) == 0: items.append("Boundary wall")
    return items


def _school_issue_summary(s: School, db: Session) -> dict:
    return {
        "pseudocode": s.pseudocode,
        "school_name": _school_display_name(s, db),
        "school_level": s.school_level,
        "risk_score": round(s.risk_score or 0, 2),
        "risk_level": s.risk_level,
        "ptr": round(s.ptr or 0, 2),
        "total_students": int(s.total_students or 0),
        "classrooms_total": int(s.classrooms_total or 0),
        "missing_items": _missing_items(s),
    }


# ─────────────────────────────────────────────────────────────
# 4. CONTINUOUS MONITORING ALERTS
# ─────────────────────────────────────────────────────────────

@router.get("/alerts")
def get_alerts(db: Session = Depends(get_db)):
    """
    Auto-generated alerts for continuous monitoring.
    Detects schools that crossed thresholds.
    """
    alerts = []

    # Alert: schools with PTR > 1.5× threshold (critical overcrowding)
    schools = db.query(School).all()
    critical_ptr = [
        s for s in schools
        if (s.ptr or 0) > PTR_THRESHOLDS.get(s.school_level or "primary", 35) * 1.5
    ]
    if critical_ptr:
        alerts.append({
            "type":     "CRITICAL",
            "code":     "PTR_CRITICAL",
            "message":  f"{len(critical_ptr)} schools have PTR exceeding 1.5× the norm — immediate teacher deployment required.",
            "count":    len(critical_ptr),
            "schools":  [s.pseudocode for s in critical_ptr[:5]],
        })

    # Alert: schools missing girls toilet (RTE mandatory)
    no_toilet = [s for s in schools if (s.has_girls_toilet or 0) == 0]
    if no_toilet:
        alerts.append({
            "type":     "CRITICAL",
            "code":     "SANITATION_MISSING",
            "message":  f"{len(no_toilet)} schools have no functional girls toilet — mandatory RTE requirement.",
            "count":    len(no_toilet),
            "schools":  [s.pseudocode for s in no_toilet[:5]],
        })

    # Alert: high-risk schools without any submitted proposal
    high_risk = [s for s in schools if s.risk_level == "High"]
    submitted_codes = {p.school_pseudocode for p in db.query(Proposal).all()}
    unactioned = [s for s in high_risk if s.pseudocode not in submitted_codes]
    if unactioned:
        alerts.append({
            "type":     "WARNING",
            "code":     "HIGH_RISK_NO_PROPOSAL",
            "message":  f"{len(unactioned)} high-risk schools have not submitted any proposal.",
            "count":    len(unactioned),
            "schools":  [s.pseudocode for s in unactioned[:5]],
        })

    # Alert: duplicate proposals (same school, multiple pending)
    from sqlalchemy import func
    dup_query = (
        db.query(Proposal.school_pseudocode, func.count(Proposal.id).label("cnt"))
        .group_by(Proposal.school_pseudocode)
        .having(func.count(Proposal.id) > 1)
        .all()
    )
    if dup_query:
        alerts.append({
            "type":    "WARNING",
            "code":    "DUPLICATE_PROPOSALS",
            "message": f"{len(dup_query)} schools have submitted multiple proposals — review for duplication.",
            "count":   len(dup_query),
            "schools": [row.school_pseudocode for row in dup_query[:5]],
        })

    return {
        "alert_count":  len(alerts),
        "critical":     sum(1 for a in alerts if a["type"] == "CRITICAL"),
        "warnings":     sum(1 for a in alerts if a["type"] == "WARNING"),
        "alerts":       alerts,
        "generated_at": datetime.utcnow().isoformat(),
    }


@router.get("/issue-schools/{issue_code}")
def issue_schools(issue_code: str, db: Session = Depends(get_db)):
    """List all schools affected by a dashboard alert category."""
    schools = db.query(School).all()
    code = issue_code.upper()

    if code == "PTR_CRITICAL":
        affected = [
            s for s in schools
            if (s.ptr or 0) > PTR_THRESHOLDS.get(s.school_level or "primary", 35) * 1.5
        ]
        title = "Critical PTR"
        description = "Schools where pupil-teacher ratio exceeds 1.5x the norm."
    elif code == "SANITATION_MISSING":
        affected = [s for s in schools if (s.has_girls_toilet or 0) == 0]
        title = "Sanitation Missing"
        description = "Schools without a functional girls toilet."
    elif code == "HIGH_RISK_NO_PROPOSAL":
        submitted_codes = {p.school_pseudocode for p in db.query(Proposal).all()}
        affected = [
            s for s in schools
            if s.risk_level == "High" and s.pseudocode not in submitted_codes
        ]
        title = "High Risk Without Proposal"
        description = "High-risk schools that have not submitted a proposal."
    elif code == "DUPLICATE_PROPOSALS":
        dup_codes = [
            row.school_pseudocode
            for row in (
                db.query(Proposal.school_pseudocode, func.count(Proposal.id).label("cnt"))
                .group_by(Proposal.school_pseudocode)
                .having(func.count(Proposal.id) > 1)
                .all()
            )
        ]
        affected = db.query(School).filter(School.pseudocode.in_(dup_codes)).all() if dup_codes else []
        title = "Duplicate Proposals"
        description = "Schools with multiple submitted proposals."
    else:
        affected = []
        title = issue_code
        description = "No matching issue category was found."

    return {
        "code": code,
        "title": title,
        "description": description,
        "count": len(affected),
        "schools": [_school_issue_summary(s, db) for s in affected],
        "generated_at": datetime.utcnow().isoformat(),
    }


# ─────────────────────────────────────────────────────────────
# 5. SCENARIO SIMULATION
# ─────────────────────────────────────────────────────────────

@router.post("/simulate")
def simulate_scenario(
    school_pseudocode: str,
    classrooms_to_add: int   = Query(0, ge=0),
    teachers_to_add:   int   = Query(0, ge=0),
    intervention_type: str   = Query("New_Classrooms"),
    devices_to_add:    int   = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """
    Intervention-aware scenario simulation.

    New_Classrooms → room density + PTR change
    Repairs        → room condition change (count unchanged)
    Sanitation     → toilet availability + infra gap change
    Digital        → device coverage + ICT readiness
    Lab            → PTR + risk change
    """
    from fastapi import HTTPException
    school = db.query(School).filter(School.pseudocode == school_pseudocode).first()
    if not school:
        raise HTTPException(status_code=404, detail=f"School {school_pseudocode} not found")

    total_students   = school.total_students or 0
    threshold        = PTR_THRESHOLDS.get(school.school_level or "primary", 35)
    current_teachers = max(school.total_tch or 1, 1)

    db_classrooms = school.classrooms_total or 0
    if db_classrooms <= 0 and total_students > 0:
        inferred_rooms = max(round(total_students / 40), 1)
        log.warning(f"School {school.pseudocode} has classrooms_total=0 — inferring {inferred_rooms} from density")
        current_rooms = inferred_rooms
    else:
        current_rooms = max(db_classrooms, 1)

    new_rooms    = current_rooms    + classrooms_to_add
    new_teachers = current_teachers + teachers_to_add

    before_spc = total_students / current_rooms
    after_spc  = total_students / max(new_rooms, 1)
    before_ptr = school.ptr or (total_students / current_teachers)
    after_ptr  = total_students / max(new_teachers, 1)

    # ── Classroom density commentary (New_Classrooms, Repairs)
    RECOMMENDED_SPC = 40
    if after_spc <= RECOMMENDED_SPC:
        room_impact = "Optimal — at or below recommended limit"
        room_status = "RESOLVED"
    elif after_spc <= 45:
        room_impact = f"Improved but still above recommended limit ({after_spc:.1f} > {RECOMMENDED_SPC})"
        room_status = "PARTIAL"
    else:
        room_impact = f"Still overcrowded ({after_spc:.1f} students/room — limit is {RECOMMENDED_SPC})"
        room_status = "INSUFFICIENT"

    # ── PTR commentary
    if after_ptr <= threshold:
        ptr_impact = f"PTR normalized ({after_ptr:.1f} ≤ {threshold})"
        ptr_status = "RESOLVED"
    elif after_ptr <= threshold * 1.2:
        ptr_impact = f"PTR improved but slightly above norm ({after_ptr:.1f} vs {threshold})"
        ptr_status = "PARTIAL"
    else:
        ptr_impact = f"PTR still elevated ({after_ptr:.1f} vs norm {threshold})"
        ptr_status = "INSUFFICIENT"

    # ── Risk delta (used by all types)
    from app.services.risk_service import compute_risk_score

    # For Sanitation: simulate infra gap reducing by 1 (girls toilet added)
    after_girls_toilet  = school.has_girls_toilet
    after_infra_gap     = school.infrastructure_gap or 0
    if intervention_type == "Sanitation":
        if (school.has_girls_toilet or 0) == 0:
            after_girls_toilet = 1
            after_infra_gap    = max(0, after_infra_gap - 1)

    before_risk = compute_risk_score({
        "total_students": total_students, "total_tch": current_teachers,
        "classrooms_total": current_rooms, "school_level": school.school_level,
        "has_girls_toilet": school.has_girls_toilet, "has_ramp": school.has_ramp,
        "has_electricity": school.has_electricity, "has_handwash": school.has_handwash,
        "has_boundary_wall": school.has_boundary_wall,
        "infrastructure_gap": school.infrastructure_gap,
    })
    after_risk = compute_risk_score({
        "total_students": total_students, "total_tch": new_teachers,
        "classrooms_total": new_rooms, "school_level": school.school_level,
        "has_girls_toilet": after_girls_toilet, "has_ramp": school.has_ramp,
        "has_electricity": school.has_electricity, "has_handwash": school.has_handwash,
        "has_boundary_wall": school.has_boundary_wall,
        "infrastructure_gap": after_infra_gap,
    })

    risk_delta     = before_risk["risk_score"] - after_risk["risk_score"]
    overall_status = "HIGH_IMPACT" if risk_delta > 15 else ("MODERATE_IMPACT" if risk_delta > 5 else "LOW_IMPACT")

    # ── Intervention-specific impact dict
    impact = {
        "risk_reduction": round(risk_delta, 2),
        "overall_status": overall_status,
        "recommendation": _simulate_recommendation(room_status, ptr_status, school, intervention_type),
    }

    if intervention_type == "New_Classrooms":
        impact.update({
            "simulation_label": "classrooms added",
            "simulation_note":  None,
            "classroom_status": room_status,
            "classroom_detail": room_impact,
            "ptr_status":       ptr_status,
            "ptr_detail":       ptr_impact,
        })

    elif intervention_type == "Repairs":
        impact.update({
            "simulation_label": "rooms repaired",
            "simulation_note":  "Repairs restore existing capacity — room count unchanged.",
            "classroom_status": room_status,
            "classroom_detail": room_impact,
            "ptr_status":       ptr_status,
            "ptr_detail":       ptr_impact,
        })

    elif intervention_type == "Sanitation":
        had_girls  = (school.has_girls_toilet or 0) == 0
        had_boys   = (school.has_boys_toilet  or 0) == 0
        toilet_status = "RESOLVED" if (not had_girls) else "RESOLVED"   # after adding
        impact.update({
            "simulation_label":   "sanitation units installed",
            "simulation_note":    "Sanitation proposals improve health outcomes and RTE compliance.",
            "girls_toilet_before": "Missing" if had_girls  else "Present",
            "girls_toilet_after":  "Present" if had_girls  else "Present",
            "boys_toilet_before":  "Missing" if had_boys   else "Present",
            "boys_toilet_after":   "Present",
            "infra_gap_before":    int(school.infrastructure_gap or 0),
            "infra_gap_after":     int(after_infra_gap),
            "toilet_status":       "RESOLVED" if had_girls else "ALREADY_MET",
            "toilet_detail":       (
                "Girls toilet gap resolved — RTE requirement will be met."
                if had_girls else
                "Girls toilet already present. Proposal improves additional sanitation items."
            ),
        })

    elif intervention_type == "Digital":
        current_devices   = int(school.has_comp_lab or 0) * 10    # proxy: comp lab → ~10 devices
        after_devices     = current_devices + max(devices_to_add, classrooms_to_add)
        devices_per_student_before = round(current_devices / max(total_students, 1) * 100, 1)
        devices_per_student_after  = round(after_devices  / max(total_students, 1) * 100, 1)
        has_ict   = bool(school.has_comp_lab)
        has_elec  = bool(school.has_electricity)
        ict_readiness_before = "Ready"    if (has_ict and has_elec) else \
                               "Partial"  if has_elec else "Not Ready"
        ict_readiness_after  = "Ready"    if has_elec else "Partial"
        impact.update({
            "simulation_label":          "devices deployed",
            "simulation_note":           "Digital proposals improve learning outcomes, not room density.",
            "devices_before":            current_devices,
            "devices_after":             after_devices,
            "device_coverage_before":    f"{devices_per_student_before}%",
            "device_coverage_after":     f"{devices_per_student_after}%",
            "ict_readiness_before":      ict_readiness_before,
            "ict_readiness_after":       ict_readiness_after,
            "electricity_available":     "Yes" if has_elec else "No — must be resolved first",
            "digital_status":            "RESOLVED" if has_elec else "BLOCKED",
            "digital_detail":            (
                f"Device coverage improves from {devices_per_student_before}% to {devices_per_student_after}% of students. "
                f"ICT readiness: {ict_readiness_before} → {ict_readiness_after}."
                if has_elec else
                "Electricity not available — digital infrastructure cannot function without power."
            ),
        })

    elif intervention_type == "Lab":
        impact.update({
            "simulation_label": "lab constructed",
            "simulation_note":  "Lab improves learning infrastructure. PTR and risk are key readiness indicators.",
            "ptr_status":       ptr_status,
            "ptr_detail":       ptr_impact,
        })

    else:
        impact.update({
            "simulation_label": "units added",
            "simulation_note":  None,
            "classroom_status": room_status,
            "classroom_detail": room_impact,
            "ptr_status":       ptr_status,
            "ptr_detail":       ptr_impact,
        })

    return {
        "school_pseudocode": school_pseudocode,
        "school_level":      school.school_level,
        "intervention_type": intervention_type,
        "changes_applied": {
            "classrooms_added": classrooms_to_add,
            "teachers_added":   teachers_to_add,
            "devices_added":    devices_to_add,
        },
        "before": {
            "classrooms":        int(current_rooms),
            "teachers":          int(current_teachers),
            "ptr":               round(before_ptr, 2),
            "students_per_room": round(before_spc, 2),
            "risk_score":        before_risk["risk_score"],
            "risk_level":        before_risk["risk_level"],
        },
        "after": {
            "classrooms":        int(new_rooms),
            "teachers":          int(new_teachers),
            "ptr":               round(after_ptr, 2),
            "students_per_room": round(after_spc, 2),
            "risk_score":        after_risk["risk_score"],
            "risk_level":        after_risk["risk_level"],
        },
        "impact": impact,
    }


def _simulate_recommendation(room_status: str, ptr_status: str, school: School, intervention_type: str = "New_Classrooms") -> str:
    if intervention_type == "Sanitation":
        parts = ["Sanitation proposal — address girls toilet, boys toilet, and handwash as priority."]
        if (school.has_girls_toilet or 0) == 0:
            parts.append("Girls toilet absent — RTE mandatory, prioritize above all other requests.")
        return " ".join(parts)
    if intervention_type in ("Lab","Digital"):
        parts = [f"{intervention_type} proposal — ensure electricity and teacher training are in place."]
        return " ".join(parts)
    parts = []
    if room_status == "RESOLVED" and ptr_status == "RESOLVED":
        parts.append("Proposal fully resolves identified infrastructure gaps. Recommend approval.")
    elif room_status == "PARTIAL":
        parts.append("Classroom addition improves but does not fully resolve overcrowding. Consider requesting additional rooms.")
    elif room_status == "INSUFFICIENT":
        parts.append("Proposed classrooms are insufficient to address overcrowding. Revise upward.")
    if (school.has_girls_toilet or 0) == 0:
        parts.append("Girls toilet must be constructed before classroom expansion — sanitation is priority.")
    return " ".join(parts) if parts else "Review proposal against current norms."
