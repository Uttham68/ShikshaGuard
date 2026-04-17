"""
app/api/routes/data_routes.py
──────────────────────────────
Dataset upload and management endpoints.
Admin only.

POST /data/upload     — upload CSV, validate columns, append to final_dataset.csv
POST /data/retrain    — retrain all models on current dataset
GET  /data/stats      — dataset statistics
GET  /data/preview    — first 10 rows of current dataset
"""

import sys
import io
import logging
import subprocess
from pathlib import Path
from datetime import datetime

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from config import FINAL_DATASET, DATA_DIR
from app.database.db import get_db, seed_schools
from app.api.auth import require_admin
from app.database.models import User

log = logging.getLogger(__name__)
router = APIRouter(prefix="/data", tags=["Dataset"])

# Minimum required columns for the system to work
REQUIRED_COLUMNS = {
    "pseudocode", "total_students", "total_tch",
    "school_level", "has_girls_toilet", "has_electricity",
    "infrastructure_gap", "risk_score", "validation_label",
}

# All known columns — upload may have a subset
KNOWN_COLUMNS = {
    "pseudocode","school_level","total_students","total_boys","total_girls",
    "students_primary","students_upper_primary","students_secondary",
    "total_tch","regular","contract","classrooms_total","classrooms_pucca",
    "classrooms_good","has_girls_toilet","has_boys_toilet","has_ramp",
    "has_library","has_playground","has_electricity","has_internet",
    "has_handwash","has_boundary_wall","has_comp_lab","ptr",
    "infrastructure_gap","risk_score","risk_level","validation_label",
    "urgency_score","ptr_violation_severity","students_per_classroom",
    "eligible_grant_norm","funding_ratio","qualified_teacher_ratio",
    "contract_ratio","growth_rate",
}


# ─────────────────────────────────────────────────────────────
# UPLOAD
# ─────────────────────────────────────────────────────────────

@router.post("/upload")
async def upload_dataset(
    file:             UploadFile = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    admin:            User    = Depends(require_admin),
    db:               Session = Depends(get_db),
):
    """
    Upload a CSV dataset. Validates required columns.
    Appends to existing final_dataset.csv (deduplicates on pseudocode).
    Triggers school DB reseed in background.
    """
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are accepted.")

    content = await file.read()
    try:
        df_new = pd.read_csv(io.BytesIO(content))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not parse CSV: {e}")

    df_new.columns = df_new.columns.str.strip().str.lower()

    # Column validation
    uploaded_cols  = set(df_new.columns)
    missing_req    = REQUIRED_COLUMNS - uploaded_cols
    unknown_cols   = uploaded_cols - KNOWN_COLUMNS
    recognised_cols= uploaded_cols & KNOWN_COLUMNS

    if missing_req:
        raise HTTPException(
            status_code=422,
            detail={
                "error":           "Missing required columns",
                "missing":         sorted(missing_req),
                "you_uploaded":    sorted(uploaded_cols),
                "required":        sorted(REQUIRED_COLUMNS),
                "hint":            "Run app/data/pipeline.py to regenerate a valid dataset.",
            }
        )

    # Load existing dataset
    existing_rows = 0
    if FINAL_DATASET.exists():
        df_existing  = pd.read_csv(FINAL_DATASET)
        existing_rows = len(df_existing)
        # Append only new pseudocodes
        new_only = df_new[~df_new["pseudocode"].astype(str).isin(
            df_existing["pseudocode"].astype(str)
        )]
        duplicate_count = len(df_new) - len(new_only)
        df_merged = pd.concat([df_existing, new_only], ignore_index=True)
    else:
        df_merged       = df_new
        duplicate_count = 0
        new_only        = df_new

    df_merged.to_csv(FINAL_DATASET, index=False)

    # Re-seed schools in background
    background_tasks.add_task(_reseed_schools_bg)

    return {
        "status":             "success",
        "filename":           file.filename,
        "rows_in_upload":     len(df_new),
        "rows_appended":      len(new_only),
        "rows_duplicate":     duplicate_count,
        "total_rows_now":     len(df_merged),
        "existing_rows_before": existing_rows,
        "columns_recognised": sorted(recognised_cols),
        "columns_unknown":    sorted(unknown_cols),
        "message":            (
            f"Appended {len(new_only)} new schools. "
            f"{duplicate_count} duplicates skipped. "
            f"Dataset now has {len(df_merged)} schools. "
            f"Run POST /data/retrain to update models."
        ),
        "uploaded_at": datetime.utcnow().isoformat(),
    }


def _reseed_schools_bg():
    try:
        from app.database.db import seed_schools, get_db_context
        with get_db_context() as db:
            seed_schools(force=True)
        log.info("Schools reseeded after dataset upload")
    except Exception as e:
        log.error(f"Background reseed failed: {e}")


# ─────────────────────────────────────────────────────────────
# RETRAIN
# ─────────────────────────────────────────────────────────────

# In-memory training state (persists across requests in same process)
_training_state = {
    "status":     "idle",   # idle | running | completed | failed
    "started_at": None,
    "completed_at": None,
    "message":    "",
    "log_tail":   "",
}


@router.get("/training-status")
def training_status(admin: User = Depends(require_admin)):
    """Poll this endpoint to check training progress."""
    return dict(_training_state)


@router.post("/retrain")
def retrain_models(
    background_tasks: BackgroundTasks,
    admin:            User    = Depends(require_admin),
):
    """Retrain all ML models on current final_dataset.csv. Runs in background."""
    global _training_state

    if _training_state["status"] == "running":
        return {
            "status":  "already_running",
            "message": "Training is already in progress. Poll GET /data/training-status.",
            "started_at": _training_state["started_at"],
        }

    if not FINAL_DATASET.exists():
        raise HTTPException(
            status_code=400,
            detail="No dataset found. Upload a dataset first via POST /data/upload"
        )

    row_count = len(pd.read_csv(FINAL_DATASET))
    if row_count < 100:
        raise HTTPException(
            status_code=400,
            detail=f"Dataset too small ({row_count} rows). Need at least 100 rows."
        )

    _training_state.update({
        "status":       "running",
        "started_at":   datetime.utcnow().isoformat(),
        "completed_at": None,
        "message":      f"Training started on {row_count} rows...",
        "log_tail":     "",
    })

    background_tasks.add_task(_run_training_bg)

    return {
        "status":       "training_started",
        "dataset_rows": row_count,
        "message":      "Training started. Poll GET /data/training-status for progress.",
        "started_at":   _training_state["started_at"],
    }


def _run_training_bg():
    global _training_state
    try:
        result = subprocess.run(
            ["python", "app/models/train.py"],
            capture_output=True, text=True, timeout=300
        )
        if result.returncode == 0:
            # Parse accuracy from output
            accuracy_line = ""
            for line in result.stdout.split("\n"):
                if "accuracy" in line.lower() or "CV" in line:
                    accuracy_line = line.strip()
                    break
            _training_state.update({
                "status":       "completed",
                "completed_at": datetime.utcnow().isoformat(),
                "message":      f"Training completed successfully. {accuracy_line}",
                "log_tail":     result.stdout[-800:],
            })
            log.info("Background training complete")
        else:
            _training_state.update({
                "status":       "failed",
                "completed_at": datetime.utcnow().isoformat(),
                "message":      "Training failed. Check log for details.",
                "log_tail":     result.stderr[-800:],
            })
            log.error(f"Training failed: {result.stderr[-500:]}")
    except subprocess.TimeoutExpired:
        _training_state.update({
            "status":       "failed",
            "completed_at": datetime.utcnow().isoformat(),
            "message":      "Training timed out after 5 minutes.",
            "log_tail":     "",
        })
    except Exception as e:
        _training_state.update({
            "status":       "failed",
            "completed_at": datetime.utcnow().isoformat(),
            "message":      f"Training error: {str(e)}",
            "log_tail":     "",
        })


# ─────────────────────────────────────────────────────────────
# STATS
# ─────────────────────────────────────────────────────────────

@router.get("/stats")
def dataset_stats(admin: User = Depends(require_admin)):
    """Dataset and model statistics for admin view."""
    from config import MODEL_VALIDATOR, MODEL_ANOMALY, MODEL_FEATURES, ARTIFACTS_DIR
    import joblib

    stats = {
        "dataset":  None,
        "models":   {},
        "artifacts_dir": str(ARTIFACTS_DIR),
    }

    if FINAL_DATASET.exists():
        df = pd.read_csv(FINAL_DATASET)
        label_dist = df["validation_label"].value_counts().to_dict() if "validation_label" in df.columns else {}
        risk_dist  = df["risk_level"].value_counts().to_dict()  if "risk_level"  in df.columns else {}
        stats["dataset"] = {
            "path":         str(FINAL_DATASET),
            "rows":         len(df),
            "columns":      list(df.columns),
            "label_distribution": label_dist,
            "risk_distribution":  risk_dist,
            "last_modified": datetime.fromtimestamp(
                FINAL_DATASET.stat().st_mtime
            ).isoformat(),
        }

    for name, path in [
        ("validator",   MODEL_VALIDATOR),
        ("anomaly",     MODEL_ANOMALY),
        ("features",    MODEL_FEATURES),
    ]:
        if path.exists():
            try:
                obj = joblib.load(path)
                info = {
                    "exists": True,
                    "last_modified": datetime.fromtimestamp(path.stat().st_mtime).isoformat(),
                }
                if name == "features":
                    info["feature_count"] = len(obj)
                elif hasattr(obj, "n_features_in_"):
                    info["n_features"] = obj.n_features_in_
                    info["n_estimators"] = getattr(obj, "n_estimators", None)
                stats["models"][name] = info
            except Exception as e:
                stats["models"][name] = {"exists": True, "error": str(e)}
        else:
            stats["models"][name] = {"exists": False}

    return stats


# ─────────────────────────────────────────────────────────────
# PREVIEW
# ─────────────────────────────────────────────────────────────

@router.get("/preview")
def preview_dataset(
    n:     int  = 10,
    admin: User = Depends(require_admin),
):
    """Return first N rows of current dataset as JSON."""
    if not FINAL_DATASET.exists():
        raise HTTPException(status_code=404, detail="No dataset found.")

    df = pd.read_csv(FINAL_DATASET, nrows=n)
    return {
        "rows":    n,
        "columns": list(df.columns),
        "data":    df.fillna(0).to_dict(orient="records"),
    }


# ─────────────────────────────────────────────────────────────
# DOWNLOAD TEMPLATE
# ─────────────────────────────────────────────────────────────

@router.get("/template")
def download_template(admin: User = Depends(require_admin)):
    """Return required column schema as JSON template."""
    return {
        "required_columns": sorted(REQUIRED_COLUMNS),
        "all_known_columns": sorted(KNOWN_COLUMNS),
        "example_row": {
            "pseudocode":        "1234567890123",
            "total_students":    250,
            "total_tch":         8,
            "school_level":      "primary",
            "has_girls_toilet":  1,
            "has_boys_toilet":   1,
            "has_electricity":   1,
            "has_ramp":          0,
            "has_library":       1,
            "has_boundary_wall": 1,
            "has_handwash":      1,
            "classrooms_total":  6,
            "infrastructure_gap":1,
            "risk_score":        25.0,
            "risk_level":        "Low",
            "validation_label":  "Flag",
        },
        "validation_label_values": ["Accept", "Flag", "Reject"],
        "school_level_values":     ["primary", "upper_primary", "secondary", "composite"],
        "boolean_columns_encoding": "1 = Yes/Available, 0 = No/Missing",
    }