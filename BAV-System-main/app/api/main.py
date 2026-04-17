"""
app/api/main.py
────────────────
Complete ShikshaGaurd FastAPI application.

Endpoints:
  GET  /                          health check
  GET  /health                    detailed health
  POST /train                     retrain all models
  POST /proposal/submit           submit a proposal (stores in DB)
  POST /proposal/validate         validate a proposal (ML + rules + AI)
  POST /forecast                  forecast enrollment / infrastructure need
  POST /risk-score                compute risk + urgency scores
  GET  /school/{pseudocode}       get school baseline data
  GET  /dashboard                 district-level aggregated stats

Run:
  uvicorn app.api.main:app --reload --host 0.0.0.0 --port 8000
"""

import sys
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import joblib
import numpy as np
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from config import (
    MODEL_VALIDATOR, MODEL_ANOMALY, MODEL_LABEL_ENC,
    ARTIFACTS_DIR, FINAL_DATASET, CORS_ORIGINS, RATE_LIMIT_PER_MINUTE,
)

limiter = Limiter(key_func=get_remote_address, default_limits=[f"{RATE_LIMIT_PER_MINUTE}/minute"])
from app.database.db import get_db, init_db, seed_schools
from app.database.models import School, Proposal, ValidationResult
from app.services.validation_service import validate_proposal
from app.services.risk_service import compute_risk_score
from app.services.ai_service import summarize_proposal
from app.utils.feature_builder import build_feature_vector
from app.api.routes.planning import router as planning_router
from app.api.routes.auth_routes import router as auth_router
from app.api.routes.data_routes import router as data_router
from app.api.auth.auth import get_current_user, require_admin, require_principal
from app.database.models import User

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────
# APP INIT
# ─────────────────────────────────────────────────────────────

app = FastAPI(
    title="BAV System — School Infrastructure Validation API",
    version="3.0",
    description="AI-powered Baseline Assessment and Validation for school infrastructure proposals",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(planning_router)
app.include_router(auth_router)
app.include_router(data_router)


from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    """Return clean error messages instead of raw Pydantic objects."""
    errors = []
    for error in exc.errors():
        field = " → ".join(str(loc) for loc in error.get("loc", []))
        errors.append({"field": field, "message": error.get("msg", "Invalid value"), "input": str(error.get("input", ""))})
    return JSONResponse(
        status_code=422,
        content={"detail": "Validation error", "errors": errors}
    )


from fastapi import Request as FastAPIRequest
from fastapi.responses import JSONResponse

@app.exception_handler(Exception)
async def global_exception_handler(request: FastAPIRequest, exc: Exception):
    """Never expose raw stack traces to clients."""
    log.error(f"Unhandled exception on {request.url}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error. Check server logs."}
    )


@app.on_event("startup")
def startup():
    """Initialise DB and seed schools on first start."""
    init_db()
    try:
        seed_schools(force=False)
    except FileNotFoundError:
        log.warning("final_dataset.csv not found — run pipeline first")
    except Exception as e:
        log.warning(f"School seeding skipped: {e}")

    # Seed default users
    try:
        from app.database.db import seed_users
        seed_users(force=False)
    except Exception as e:
        log.warning(f"User seeding skipped: {e}")
    # Seed default users on first run
    try:
        from app.database.db import SessionLocal
        from app.api.auth import hash_password
        from app.database.models import User
        _db = SessionLocal()
        if _db.query(User).count() == 0:
            from sqlalchemy.orm import Session
            defaults = [
                User(username="admin",     hashed_password=hash_password("admin123"),
                     role="admin",     full_name="System Administrator", is_active=True),
                User(username="principal1",hashed_password=hash_password("school123"),
                     role="principal", full_name="Dr. Pranav Kumar",
                     school_pseudocode="1003076", is_active=True),
            ]
            for u in defaults: _db.add(u)
            _db.commit()
            log.info("Default users seeded: admin/admin123, principal1/school123")
        _db.close()
    except Exception as e:
        log.warning(f"User seeding skipped: {e}")


# ─────────────────────────────────────────────────────────────
# REQUEST / RESPONSE MODELS
# ─────────────────────────────────────────────────────────────

class ProposalRequest(BaseModel):
    # School identification
    school_pseudocode:    str   = Field(..., description="11-digit UDISE code")
    principal_name:       str   = Field("")
    school_name:          str   = Field("School", min_length=1)

    # Proposal fields
    intervention_type:    str   = Field(..., description="New_Classrooms/Repairs/Digital/Sanitation/Lab")
    classrooms_requested: int   = Field(0, ge=0, le=200)
    funding_requested:    float = Field(..., gt=0, description="Total funding ask in INR")
    funding_recurring:    float = Field(0, ge=0)
    funding_nonrecurring: float = Field(0, ge=0)
    project_start_date:   Optional[str] = None
    project_end_date:     Optional[str] = None
    udise_data_verified:  bool  = Field(False)

    # Dynamic fields by intervention type (JSON object)
    dynamic_fields:       Optional[dict] = Field(None, description="Intervention-specific fields")
    # Optional free-text letter
    proposal_letter:      Optional[str] = Field(None, description="Full proposal letter text")


class SchoolInputDirect(BaseModel):
    """For direct school data input (when school not in DB)."""
    total_students:   float = Field(..., ge=0)
    total_tch:        float = Field(..., ge=1)
    classrooms_total: float = Field(1, ge=1)
    school_level:     str   = Field("primary")
    has_girls_toilet: int   = Field(0, ge=0, le=1)
    has_boys_toilet:  int   = Field(0, ge=0, le=1)
    has_ramp:         int   = Field(0, ge=0, le=1)
    has_library:      int   = Field(0, ge=0, le=1)
    has_electricity:  int   = Field(0, ge=0, le=1)
    has_boundary_wall:int   = Field(0, ge=0, le=1)
    has_handwash:     int   = Field(0, ge=0, le=1)
    contract:         float = Field(0, ge=0)
    infrastructure_gap: float = Field(0, ge=0)
    risk_score:       float = Field(0, ge=0)


class ForecastRequest(BaseModel):
    school_pseudocode: Optional[str] = None
    total_students:    float = Field(..., ge=0)
    total_tch:         float = Field(1, ge=1)
    classrooms_total:  float = Field(1, ge=1)
    school_level:      str   = Field("primary")
    years_ahead:       int   = Field(3, ge=1, le=10)


class RiskScoreRequest(BaseModel):
    school_pseudocode:   Optional[str] = None
    total_students:      float = Field(..., ge=0)
    total_tch:           float = Field(1, ge=1)
    classrooms_total:    float = Field(1, ge=1)
    school_level:        str   = Field("primary")
    has_girls_toilet:    int   = Field(1)
    has_ramp:            int   = Field(1)
    has_electricity:     int   = Field(1)
    has_handwash:        int   = Field(1)
    has_boundary_wall:   int   = Field(1)
    infrastructure_gap:  float = Field(0)
    funding_requested:   float = Field(0)
    udise_data_verified: bool  = Field(True)


# ─────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────

def _school_to_dict(school: School) -> dict:
    """Convert SQLAlchemy School object to plain dict for services."""
    return {
        "pseudocode":        school.pseudocode,
        "school_name":       f"School {school.pseudocode}",
        "school_level":      school.school_level,
        "total_students":    school.total_students,
        "total_boys":        school.total_boys,
        "total_girls":       school.total_girls,
        "total_tch":         school.total_tch,
        "regular":           school.regular,
        "contract":          school.contract,
        "classrooms_total":  school.classrooms_total,
        "classrooms_pucca":  school.classrooms_pucca,
        "classrooms_good":   school.classrooms_good,
        "has_girls_toilet":  school.has_girls_toilet,
        "has_boys_toilet":   school.has_boys_toilet,
        "has_ramp":          school.has_ramp,
        "has_library":       school.has_library,
        "has_playground":    school.has_playground,
        "has_electricity":   school.has_electricity,
        "has_internet":      school.has_internet,
        "has_handwash":      school.has_handwash,
        "has_boundary_wall": school.has_boundary_wall,
        "has_comp_lab":      school.has_comp_lab,
        "ptr":               school.ptr,
        "infrastructure_gap":school.infrastructure_gap,
        "risk_score":        school.risk_score,
        "risk_level":        school.risk_level,
    }


def _school_display_name(school: School, db: Session) -> str:
    """Use the latest proposal name when available; schools table stores codes only."""
    proposal = (
        db.query(Proposal.school_name)
        .filter(Proposal.school_pseudocode == school.pseudocode)
        .order_by(Proposal.submitted_at.desc())
        .first()
    )
    if proposal and proposal.school_name:
        return proposal.school_name
    return f"School {school.pseudocode}"


def _get_school_or_404(pseudocode: str, db: Session) -> School:
    school = db.query(School).filter(School.pseudocode == pseudocode).first()
    if not school:
        raise HTTPException(
            status_code=404,
            detail=f"School '{pseudocode}' not found in database. "
                   f"Verify UDISE code or seed the database."
        )
    return school


# ─────────────────────────────────────────────────────────────
# ENDPOINT 0 — BUDGET ESTIMATION (AI-powered)
# ─────────────────────────────────────────────────────────────

class BudgetEstimateRequest(BaseModel):
    school_pseudocode: Optional[str] = None
    intervention_type: str
    dynamic_fields:    Optional[dict] = Field(default_factory=dict)
    funding_requested: float = Field(0, ge=0)

@app.post("/budget-estimate")
def budget_estimate(req: BudgetEstimateRequest, db: Session = Depends(get_db)):
    """AI-powered budget estimation for a given intervention type and fields."""
    from app.services.ai_service import estimate_budget
    school_dict = {}
    if req.school_pseudocode:
        try:
            school = _get_school_or_404(req.school_pseudocode, db)
            school_dict = _school_to_dict(school)
        except Exception:
            pass
    proposal_data = {
        "intervention_type": req.intervention_type,
        "dynamic_fields":    req.dynamic_fields or {},
        "funding_requested": req.funding_requested,
    }
    estimate = estimate_budget(proposal_data, school_dict)
    return estimate


# ─────────────────────────────────────────────────────────────
# ENDPOINT 1 — HEALTH
# ─────────────────────────────────────────────────────────────

@app.get("/my-proposals")
def my_proposals(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_principal),
):
    """Principal: get their own school's proposals and latest validation results."""
    if current_user.role == "principal":
        school_code = current_user.school_pseudocode
    else:
        school_code = None  # admin gets all (use /dashboard instead)

    query = db.query(Proposal)
    if school_code:
        query = query.filter(Proposal.school_pseudocode == school_code)

    proposals = query.order_by(Proposal.submitted_at.desc()).limit(20).all()

    result = []
    for p in proposals:
        vr = p.result  # ValidationResult relationship
        result.append({
            "proposal_id":        p.id,
            "school_pseudocode":  p.school_pseudocode,
            "school_name":        p.school_name,
            "intervention_type":  p.intervention_type,
            "funding_requested":  p.funding_requested,
            "status":             p.status,
            "submitted_at":       p.submitted_at.isoformat() if p.submitted_at else None,
            "verdict":            vr.verdict      if vr else None,
            "confidence":         vr.confidence   if vr else None,
            "risk_score":         vr.risk_score   if vr else None,
            "risk_level":         vr.risk_level   if vr else None,
        })
    return {"proposals": result, "total": len(result)}


@app.get("/")
@app.get("/health")
def health(db: Session = Depends(get_db)):
    models_ready = MODEL_VALIDATOR.exists() and MODEL_ANOMALY.exists()
    school_count = db.query(School).count()
    proposal_count = db.query(Proposal).count()

    return {
        "status": "running",
        "models_loaded": models_ready,
        "schools_in_db": school_count,
        "proposals_submitted": proposal_count,
        "timestamp": datetime.utcnow().isoformat(),
    }


# ─────────────────────────────────────────────────────────────
# ENDPOINT 2 — TRAIN
# ─────────────────────────────────────────────────────────────

@app.post("/train")
@limiter.limit("2/hour")
def train_models(
    background_tasks: BackgroundTasks,
    request: Request,
    admin: User = Depends(require_admin),
):
    """Retrain all models — admin only, rate limited to 2/hour."""
    if not FINAL_DATASET.exists():
        raise HTTPException(
            status_code=400,
            detail="Dataset not found. Run pipeline first: python app/data/pipeline.py"
        )

    def _run_training():
        import subprocess
        subprocess.run(
            ["python", "app/models/train.py"],
            capture_output=True
        )
        log.info("Background training complete")

    background_tasks.add_task(_run_training)

    return {
        "status": "training_started",
        "message": "Model training started in background. Check logs for progress.",
        "dataset": str(FINAL_DATASET),
    }


# ─────────────────────────────────────────────────────────────
# ENDPOINT 3 — SUBMIT PROPOSAL
# ─────────────────────────────────────────────────────────────

@app.post("/proposal/submit")
def submit_proposal(
    req: ProposalRequest,
    db: Session = Depends(get_db),
):
    """
    Submit a proposal. Generates AI summary if letter provided.
    Does NOT run validation — call /proposal/validate separately.
    """
    school = _get_school_or_404(req.school_pseudocode, db)

    # AI summary of free-text letter
    ai_summary = None
    if req.proposal_letter:
        ai_summary = summarize_proposal(
            proposal_letter=req.proposal_letter,
            structured_fields=req.dict(),
        )

    proposal = Proposal(
        school_pseudocode=req.school_pseudocode,
        principal_name=req.principal_name,
        school_name=req.school_name,
        intervention_type=req.intervention_type,
        classrooms_requested=req.classrooms_requested,
        funding_requested=req.funding_requested,
        funding_recurring=req.funding_recurring,
        funding_nonrecurring=req.funding_nonrecurring,
        project_start_date=req.project_start_date,
        project_end_date=req.project_end_date,
        udise_data_verified=req.udise_data_verified,
        proposal_letter=req.proposal_letter,
        dynamic_fields=req.dynamic_fields,
        ai_summary=ai_summary,
        status="Pending",
    )
    db.add(proposal)
    db.commit()
    db.refresh(proposal)

    return {
        "proposal_id": proposal.id,
        "status": "submitted",
        "school_name": req.school_name,
        "ai_summary": ai_summary,
        "message": "Proposal submitted. Call POST /proposal/validate with this proposal_id.",
    }


# ─────────────────────────────────────────────────────────────
# ENDPOINT 4 — VALIDATE PROPOSAL
# Two usage modes:
#   A) Pass full ProposalRequest body → submit + validate in one call
#   B) Pass {"proposal_id": N}        → validate an already-submitted proposal
# ─────────────────────────────────────────────────────────────

class ValidateByIdRequest(BaseModel):
    proposal_id: int


@app.post("/proposal/validate")
def validate_proposal_endpoint(
    req: ProposalRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Submit + validate in one call.
    Accepts the same body as /proposal/submit.
    Saves proposal to DB, runs full validation, returns complete result.
    """
    school = _get_school_or_404(req.school_pseudocode, db)

    # Principals can only submit for their own school
    if current_user.role == "principal":
        if current_user.school_pseudocode != req.school_pseudocode:
            raise HTTPException(
                status_code=403,
                detail=f"You are registered for school {current_user.school_pseudocode}. "
                       f"You cannot submit proposals for other schools."
            )

    school_dict = _school_to_dict(school)

    # AI summary of free-text letter (non-blocking)
    ai_summary = None
    if req.proposal_letter:
        try:
            ai_summary = summarize_proposal(
                proposal_letter=req.proposal_letter,
                structured_fields=req.dict(),
            )
        except Exception:
            ai_summary = None

    # Save proposal to DB
    proposal = Proposal(
        school_pseudocode    = req.school_pseudocode,
        principal_name       = req.principal_name,
        school_name          = req.school_name,
        intervention_type    = req.intervention_type,
        classrooms_requested = req.classrooms_requested,
        funding_requested    = req.funding_requested,
        funding_recurring    = req.funding_recurring,
        funding_nonrecurring = req.funding_nonrecurring,
        project_start_date   = req.project_start_date,
        project_end_date     = req.project_end_date,
        udise_data_verified  = req.udise_data_verified,
        proposal_letter      = req.proposal_letter,
        dynamic_fields       = req.dynamic_fields,
        ai_summary           = ai_summary,
        status               = "Pending",
    )
    db.add(proposal)
    db.commit()
    db.refresh(proposal)

    # Auto-fill names from user/DB if empty
    principal = req.principal_name or (current_user.full_name or current_user.username)
    school_nm = req.school_name or f"School {req.school_pseudocode}"

    # Check if school has an existing non-rejected sanitation proposal
    existing_sanitation = db.query(Proposal).filter(
        Proposal.school_pseudocode == req.school_pseudocode,
        Proposal.intervention_type == "Sanitation",
        Proposal.status != "Reject",
    ).first()

    # Check existing proposals for all types (for duplicate detection)
    existing_proposals_count = db.query(Proposal).filter(
        Proposal.school_pseudocode == req.school_pseudocode
    ).count()

    proposal_dict = {
        "intervention_type":          req.intervention_type,
        "classrooms_requested":       req.classrooms_requested,
        "funding_requested":          req.funding_requested,
        "udise_data_verified":        req.udise_data_verified,
        "dynamic_fields":             req.dynamic_fields or {},
        "proposal_letter":            req.proposal_letter or "",
        "smc_resolution_attached":    getattr(req, "smc_resolution_attached", True),
        "previous_grant_utilized":    getattr(req, "previous_grant_utilized", None),
        "has_active_sanitation_proposal": existing_sanitation is not None,
        "existing_proposals_count":   existing_proposals_count,
    }

    # Run full validation pipeline
    result = validate_proposal(school_dict, proposal_dict, include_ai=True)

    # Compute risk score
    risk = compute_risk_score(school_dict, proposal_dict)
    result["risk_score"]      = risk["risk_score"]
    result["urgency_score"]   = risk["urgency_score"]
    result["risk_level"]      = risk["risk_level"]
    result["score_breakdown"] = risk["breakdown"]
    result["key_metrics"]     = risk["key_metrics"]

    # Save validation result to DB
    db_result = ValidationResult(
        proposal_id         = proposal.id,
        verdict             = result["verdict"],
        confidence          = result["confidence"],
        risk_score          = result["risk_score"],
        urgency_score       = result["urgency_score"],
        risk_level          = result["risk_level"],
        is_anomaly          = result["is_anomaly"],
        anomaly_score       = result["anomaly_score"],
        rule_violations     = result["violations"],
        ai_explanation      = result["ai_explanation"],
        feature_importances = result["feature_importances"],
        score_breakdown     = result["score_breakdown"],
    )
    db.add(db_result)
    proposal.status = result["verdict"]
    db.commit()

    return {
        "proposal_id":          proposal.id,
        "school_pseudocode":    req.school_pseudocode,
        "school_name":          req.school_name,
        "verdict":              result["verdict"],
        "confidence":           result["confidence"],
        "risk_score":           result["risk_score"],
        "urgency_score":        result["urgency_score"],
        "risk_level":           result["risk_level"],
        "is_anomaly":           result["is_anomaly"],
        "anomaly_score":        result["anomaly_score"],
        "violations":           result["violations"],
        "ai_explanation":       result["ai_explanation"],
        "ai_summary":           ai_summary,
        "ml_probabilities":     result["ml_probabilities"],
        "feature_importances":  result["feature_importances"],
        "score_breakdown":      result["score_breakdown"],
        "key_metrics":          result["key_metrics"],
    }


@app.post("/proposal/validate-by-id")
def validate_by_id(
    req: ValidateByIdRequest,
    db: Session = Depends(get_db),
):
    """Validate an already-submitted proposal by its DB id."""
    proposal = db.query(Proposal).filter(Proposal.id == req.proposal_id).first()
    if not proposal:
        raise HTTPException(status_code=404, detail=f"Proposal {req.proposal_id} not found")

    school = _get_school_or_404(proposal.school_pseudocode, db)
    school_dict = _school_to_dict(school)
    proposal_dict = {
        "intervention_type":    proposal.intervention_type,
        "classrooms_requested": proposal.classrooms_requested,
        "funding_requested":    proposal.funding_requested,
        "udise_data_verified":  proposal.udise_data_verified,
        "dynamic_fields":       proposal.dynamic_fields or {},
        "proposal_letter":      proposal.proposal_letter or "",
    }

    result = validate_proposal(school_dict, proposal_dict, include_ai=True)
    risk   = compute_risk_score(school_dict, proposal_dict)
    result["risk_score"]      = risk["risk_score"]
    result["urgency_score"]   = risk["urgency_score"]
    result["risk_level"]      = risk["risk_level"]
    result["score_breakdown"] = risk["breakdown"]
    result["key_metrics"]     = risk["key_metrics"]

    db_result = ValidationResult(
        proposal_id         = proposal.id,
        verdict             = result["verdict"],
        confidence          = result["confidence"],
        risk_score          = result["risk_score"],
        urgency_score       = result["urgency_score"],
        risk_level          = result["risk_level"],
        is_anomaly          = result["is_anomaly"],
        anomaly_score       = result["anomaly_score"],
        rule_violations     = result["violations"],
        ai_explanation      = result["ai_explanation"],
        feature_importances = result["feature_importances"],
        score_breakdown     = result["score_breakdown"],
    )
    db.add(db_result)
    proposal.status = result["verdict"]
    db.commit()

    return {
        "proposal_id":         proposal.id,
        "verdict":             result["verdict"],
        "confidence":          result["confidence"],
        "risk_score":          result["risk_score"],
        "urgency_score":       result["urgency_score"],
        "risk_level":          result["risk_level"],
        "is_anomaly":          result["is_anomaly"],
        "violations":          result["violations"],
        "ai_explanation":      result["ai_explanation"],
        "ml_probabilities":    result["ml_probabilities"],
        "score_breakdown":     result["score_breakdown"],
        "key_metrics":         result["key_metrics"],
    }


# ─────────────────────────────────────────────────────────────
# ENDPOINT 4b — ADVANCED ANOMALY DETECTION
# ─────────────────────────────────────────────────────────────

@app.delete("/proposal/{proposal_id}")
def delete_proposal(
    proposal_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a proposal and its latest validation result."""
    proposal = db.query(Proposal).filter(Proposal.id == proposal_id).first()
    if not proposal:
        raise HTTPException(status_code=404, detail=f"Proposal {proposal_id} not found")

    if (
        current_user.role == "principal"
        and current_user.school_pseudocode != proposal.school_pseudocode
    ):
        raise HTTPException(
            status_code=403,
            detail="You can delete only proposals submitted for your school.",
        )

    db.query(ValidationResult).filter(ValidationResult.proposal_id == proposal.id).delete()
    db.delete(proposal)
    db.commit()

    return {"deleted": True, "proposal_id": proposal_id}


class AdvancedAnomalyRequest(BaseModel):
    school_pseudocode:    str
    funding_requested:    float   = Field(0, ge=0)
    classrooms_requested: int     = Field(0, ge=0)
    proposal_letter:      Optional[str] = None
    intervention_type:    str     = Field("New_Classrooms")


@app.post("/anomaly/advanced")
def advanced_anomaly(req: AdvancedAnomalyRequest, db: Session = Depends(get_db)):
    """
    Advanced fraud/anomaly detection beyond ML Isolation Forest.
    Checks: enrollment spike, multiple requests, funding mismatch, infra already exists.
    """
    school = _get_school_or_404(req.school_pseudocode, db)
    flags = []

    total_students = school.total_students or 0
    classrooms     = school.classrooms_total or 0

    # Check 1: school already has many classrooms but requesting more
    if req.classrooms_requested > 0:
        ratio = classrooms / max(req.classrooms_requested, 1)
        if ratio > 4:
            flags.append({
                "type": "SUSPICIOUS",
                "code": "EXCESS_CLASSROOMS",
                "message": f"School already has {int(classrooms)} classrooms but is requesting "
                           f"{req.classrooms_requested} more ({ratio:.1f}× existing capacity). "
                           f"Verify actual classroom shortage.",
            })

    # Check 2: multiple proposals from same school
    existing_proposals = db.query(Proposal).filter(
        Proposal.school_pseudocode == req.school_pseudocode
    ).count()
    if existing_proposals >= 2:
        flags.append({
            "type": "WARNING",
            "code": "MULTIPLE_PROPOSALS",
            "message": f"This school has already submitted {existing_proposals} proposal(s). "
                       f"Multiple concurrent requests require additional scrutiny.",
        })

    # Check 3: funding vs school size mismatch
    from config import INTERVENTION_COST_NORMS
    norm = INTERVENTION_COST_NORMS.get(req.intervention_type)
    if norm and req.funding_requested > 0 and req.classrooms_requested > 0:
        expected = norm["per_unit"] * req.classrooms_requested
        ratio = req.funding_requested / expected
        if ratio > 3:
            flags.append({
                "type": "SUSPICIOUS",
                "code": "FUNDING_INFLATION",
                "message": f"Funding request (₹{req.funding_requested:,.0f}) is "
                           f"{ratio:.1f}× the SOR expected cost (₹{expected:,.0f}). "
                           f"Possible cost inflation.",
            })

    # Check 4: letter vs form mismatch
    if req.proposal_letter and req.classrooms_requested > 0:
        import re
        matches = re.findall(r"(\d+)\s*(?:new\s+)?classroom", req.proposal_letter.lower())
        mismatches = [int(m) for m in matches if int(m) != req.classrooms_requested]
        if mismatches:
            flags.append({
                "type": "WARNING",
                "code": "FORM_LETTER_MISMATCH",
                "message": f"Form requests {req.classrooms_requested} classrooms but letter "
                           f"mentions {mismatches[0]}. Possible data entry error or inconsistency.",
            })

    # Check 5: ML isolation forest
    school_dict = _school_to_dict(school)
    X = build_feature_vector({**school_dict,
                               "funding_requested": req.funding_requested,
                               "classrooms_requested": req.classrooms_requested})
    try:
        _load_models()
        iso_pred  = _iso.predict(X)[0]
        iso_score = float(_iso.decision_function(X)[0])
        if iso_pred == -1:
            flags.append({
                "type": "ANOMALY",
                "code": "ML_ANOMALY",
                "message": f"Isolation Forest flagged this school profile as anomalous "
                           f"(score: {iso_score:.4f}). Statistical outlier in training data.",
            })
    except Exception:
        iso_score = 0.0

    severity = "CLEAN"
    if any(f["type"] == "SUSPICIOUS" for f in flags):
        severity = "SUSPICIOUS"
    elif any(f["type"] in ("WARNING", "ANOMALY") for f in flags):
        severity = "FLAGGED"

    return {
        "school_pseudocode": req.school_pseudocode,
        "severity":          severity,
        "flag_count":        len(flags),
        "flags":             flags,
        "isolation_score":   round(iso_score, 4),
        "recommendation":    "Manual review recommended." if flags else "No anomalies detected.",
    }


def _load_models():
    global _clf, _iso, _le
    if _clf is None:
        _clf = joblib.load(MODEL_VALIDATOR)
        _iso = joblib.load(MODEL_ANOMALY)
        _le  = joblib.load(MODEL_LABEL_ENC)

_clf = _iso = _le = None


# ─────────────────────────────────────────────────────────────
# ENDPOINT 5 — FORECAST
# ─────────────────────────────────────────────────────────────

@app.post("/forecast")
def forecast(req: ForecastRequest, db: Session = Depends(get_db)):
    """
    Forecasts enrollment and infrastructure need for N years ahead.
    Uses XGBoost forecaster + growth assumptions.
    """
    try:
        forecaster = joblib.load(ARTIFACTS_DIR / "xgb_forecaster.joblib")
        forecast_features = joblib.load(ARTIFACTS_DIR / "forecaster_features.joblib")
    except FileNotFoundError:
        raise HTTPException(status_code=503, detail="Forecaster model not trained yet.")

    # Get school data
    school_data = {}
    if req.school_pseudocode:
        try:
            school = _get_school_or_404(req.school_pseudocode, db)
            school_data = _school_to_dict(school)
        except HTTPException:
            pass

    # Build feature vector for forecaster (excludes total_students)
    row = {
        "total_students":    req.total_students,
        "total_tch":         req.total_tch,
        "classrooms_total":  req.classrooms_total,
        "school_level":      req.school_level,
        **school_data,
    }

    from app.utils.feature_builder import build_features_from_row, FEATURE_COLUMNS
    all_features = build_features_from_row(row)
    X = np.array([[all_features.get(f, 0.0) for f in forecast_features]])

    base_prediction = float(forecaster.predict(X)[0])

    # Project forward using 5% annual growth assumption
    ANNUAL_GROWTH_RATE = 0.05
    projected_students = []
    for yr in range(1, req.years_ahead + 1):
        projected = round(req.total_students * ((1 + ANNUAL_GROWTH_RATE) ** yr))
        projected_students.append({"year": yr, "projected_students": projected})

    final_year_students = projected_students[-1]["projected_students"]

    # Calculate infrastructure needs for final year
    from config import PTR_THRESHOLDS
    ptr_threshold = PTR_THRESHOLDS.get(req.school_level, 35)
    teachers_needed = max(0, round(final_year_students / ptr_threshold) - req.total_tch)
    classrooms_needed = max(0, round(final_year_students / 40) - req.classrooms_total)

    return {
        "current_students":     int(req.total_students),
        "model_estimate":       round(base_prediction),
        "projected_enrollment": projected_students,
        "final_year_projection": {
            "year":             req.years_ahead,
            "students":         final_year_students,
            "teachers_needed":  int(teachers_needed),
            "classrooms_needed":int(classrooms_needed),
            "ptr_threshold":    ptr_threshold,
        },
        "assumptions": {
            "annual_growth_rate": f"{ANNUAL_GROWTH_RATE*100:.0f}%",
            "target_classroom_density": 40,
        },
    }


# ─────────────────────────────────────────────────────────────
# ENDPOINT 6 — RISK SCORE
# ─────────────────────────────────────────────────────────────

@app.post("/risk-score")
def risk_score_endpoint(req: RiskScoreRequest, db: Session = Depends(get_db)):
    """Compute risk + urgency score with full breakdown."""
    school_dict = req.dict()

    # Enrich with DB data if pseudocode provided
    if req.school_pseudocode:
        try:
            school = _get_school_or_404(req.school_pseudocode, db)
            school_dict = {**_school_to_dict(school), **school_dict}
        except HTTPException:
            pass

    proposal_dict = {
        "funding_requested":   req.funding_requested,
        "udise_data_verified": req.udise_data_verified,
    }

    return compute_risk_score(school_dict, proposal_dict)


# ─────────────────────────────────────────────────────────────
# ENDPOINT 7 — SCHOOL BASELINE
# ─────────────────────────────────────────────────────────────

@app.get("/school/{pseudocode}")
def get_school(
    pseudocode:   str,
    db:           Session = Depends(get_db),
    current_user: User    = Depends(get_current_user),
):
    """Return UDISE+ baseline data. Principal can only access their own school."""
    if current_user.role == "principal" and current_user.school_pseudocode != pseudocode:
        raise HTTPException(
            status_code=403,
            detail=f"Access denied. Your school: {current_user.school_pseudocode}"
        )
    school = _get_school_or_404(pseudocode, db)
    data = _school_to_dict(school)
    data["school_name"] = _school_display_name(school, db)
    return data


# ─────────────────────────────────────────────────────────────
# ENDPOINT 8 — DASHBOARD
# ─────────────────────────────────────────────────────────────

# ─────────────────────────────────────────────────────────────
# MODEL VERSIONING
# ─────────────────────────────────────────────────────────────

@app.get("/models/versions")
def list_model_versions(admin: User = Depends(require_admin)):
    """List available model versions for rollback."""
    from app.models.train import list_versions
    return {"versions": list_versions()}


@app.post("/models/rollback/{version_ts}")
def rollback_model(
    version_ts: str,
    admin:      User    = Depends(require_admin),
):
    """Rollback all model artifacts to a previous version."""
    from app.models.train import rollback_to
    try:
        rollback_to(version_ts)
        # Force reload on next request
        import app.services.validation_service as vs
        vs._clf = vs._iso = vs._le = vs._model_feature_cols = None
        return {"status": "success", "rolled_back_to": version_ts}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Version '{version_ts}' not found")


# ─────────────────────────────────────────────────────────────
# PROPOSALS LIST (admin sees all, principal sees own)
# ─────────────────────────────────────────────────────────────

@app.get("/proposals")
def list_proposals(
    db:           Session = Depends(get_db),
    current_user: User    = Depends(get_current_user),
    page:         int     = 1,
    page_size:    int     = 20,
):
    limit  = min(page_size, 100)   # cap at 100 per page
    offset = (max(page, 1) - 1) * limit
    """List proposals. Principal sees only their school's proposals."""
    query = db.query(Proposal)
    if current_user.role == "principal" and current_user.school_pseudocode:
        query = query.filter(Proposal.school_pseudocode == current_user.school_pseudocode)

    total    = query.count()
    proposals = query.order_by(Proposal.submitted_at.desc()).offset(offset).limit(limit).all()

    results = []
    for p in proposals:
        result_row = db.query(ValidationResult).filter(
            ValidationResult.proposal_id == p.id
        ).first()
        results.append({
            "id":                p.id,
            "school_pseudocode": p.school_pseudocode,
            "school_name":       p.school_name,
            "intervention_type": p.intervention_type,
            "funding_requested": p.funding_requested,
            "status":            p.status,
            "verdict":           result_row.verdict       if result_row else None,
            "confidence":        result_row.confidence    if result_row else None,
            "risk_score":        result_row.risk_score    if result_row else None,
            "urgency_score":     result_row.urgency_score if result_row else None,
            "is_anomaly":        result_row.is_anomaly    if result_row else None,
            "submitted_at":      p.submitted_at.strftime("%d/%m/%Y") if p.submitted_at else None,
        })

    return {"total": total, "proposals": results}


@app.get("/dashboard")
def dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Aggregated stats for district-level monitoring dashboard."""
    total_schools    = db.query(School).count()
    total_proposals  = db.query(Proposal).count()

    # Verdict breakdown
    results = db.query(ValidationResult).all()
    verdict_counts = {"Accept": 0, "Flag": 0, "Reject": 0}
    risk_levels    = {"Low": 0, "Medium": 0, "High": 0}
    avg_risk       = 0.0
    avg_confidence = 0.0

    for r in results:
        verdict_counts[r.verdict] = verdict_counts.get(r.verdict, 0) + 1
        risk_levels[r.risk_level] = risk_levels.get(r.risk_level, 0) + 1
        avg_risk       += r.risk_score or 0
        avg_confidence += r.confidence or 0

    n = len(results)
    if n > 0:
        avg_risk       = round(avg_risk / n, 2)
        avg_confidence = round(avg_confidence / n, 4)

    # Top 5 highest risk schools
    high_risk_schools = (
        db.query(School)
        .order_by(School.risk_score.desc())
        .limit(5)
        .all()
    )

    return {
        "summary": {
            "total_schools":   total_schools,
            "total_proposals": total_proposals,
            "validated":       n,
        },
        "verdicts":      verdict_counts,
        "risk_levels":   risk_levels,
        "averages": {
            "risk_score":  avg_risk,
            "confidence":  avg_confidence,
        },
        "top_risk_schools": [
            {
                "pseudocode":   s.pseudocode,
                "school_name":  _school_display_name(s, db),
                "risk_score":   s.risk_score,
                "risk_level":   s.risk_level,
                "total_students": s.total_students,
                "ptr":          s.ptr,
            }
            for s in high_risk_schools
        ],
        "generated_at": datetime.utcnow().isoformat(),
    }
