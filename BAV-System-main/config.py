"""
config.py — Single source of truth for all settings.
Never hardcode paths or thresholds anywhere else.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ─────────────────────────────────────────────
# PATHS
# ─────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent

DATA_DIR          = BASE_DIR / "app" / "data"
RAW_ENROLLMENT    = DATA_DIR / "enrollment.csv"
RAW_FACILITIES    = DATA_DIR / "facilities.csv"
RAW_TEACHERS      = DATA_DIR / "teachers.csv"
FINAL_DATASET     = DATA_DIR / "final_dataset.csv"

ARTIFACTS_DIR     = BASE_DIR / "app" / "models" / "artifacts"
MODEL_VALIDATOR   = ARTIFACTS_DIR / "rf_validator.joblib"
MODEL_FORECASTER  = ARTIFACTS_DIR / "xgb_forecaster.joblib"
MODEL_ANOMALY     = ARTIFACTS_DIR / "iso_anomaly.joblib"
MODEL_FEATURES    = ARTIFACTS_DIR / "feature_names.joblib"
MODEL_LABEL_ENC   = ARTIFACTS_DIR / "label_encoder.joblib"

_sqlite_url = f"sqlite:///{BASE_DIR / 'shikshasgaurd.db'}"
DATABASE_URL = os.getenv("DATABASE_URL", _sqlite_url)

# ─────────────────────────────────────────────
# API KEYS — all from environment, never hardcoded
# ─────────────────────────────────────────────
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_URL     = "https://openrouter.ai/api/v1/chat/completions"
AI_MODEL           = os.getenv("AI_MODEL", "meta-llama/llama-3.1-8b-instruct:free")

# ─────────────────────────────────────────────
# SECURITY — all from environment
# ─────────────────────────────────────────────
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "CHANGE-THIS-IN-PRODUCTION-USE-RANDOM-256-BIT-KEY")
JWT_EXPIRE_HOURS = int(os.getenv("JWT_EXPIRE_HOURS", "8"))

# Default admin credentials — ONLY used for initial seed, sourced from env
DEFAULT_ADMIN_USERNAME = os.getenv("DEFAULT_ADMIN_USERNAME", "admin")
DEFAULT_ADMIN_PASSWORD = os.getenv("DEFAULT_ADMIN_PASSWORD", "")  # empty = no default seed

# ─────────────────────────────────────────────
# SERVER
# ─────────────────────────────────────────────
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",")
DATABASE_URL_OVERRIDE = os.getenv("DATABASE_URL", "")  # set to postgres:// in production
RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "30"))

# ─────────────────────────────────────────────
# PTR THRESHOLDS (Samagra Shiksha norms)
# ─────────────────────────────────────────────
PTR_THRESHOLDS = {
    "primary":       30,   # Classes 1-5
    "upper_primary": 35,   # Classes 6-8
    "secondary":     35,   # Classes 9-10
}

PTR_REJECT_MULTIPLIER = 1.5   # PTR > threshold × 1.5 → Reject

# ─────────────────────────────────────────────
# SAMAGRA SHIKSHA GRANT NORMS (INR)
# ─────────────────────────────────────────────
GRANT_NORMS = [
    (30,   10_000),
    (100,  25_000),
    (250,  50_000),
    (1000, 75_000),
    (float("inf"), 1_00_000),
]

# ─────────────────────────────────────────────
# RISK SCORING WEIGHTS (must sum to 100)
# ─────────────────────────────────────────────
RISK_WEIGHTS = {
    "ptr_violation":    25,
    "infra_gap":        20,
    "funding_ratio":    25,
    "anomaly_signal":   15,
    "udise_compliance": 15,
}

# ─────────────────────────────────────────────
# INTERVENTION-SPECIFIC COST NORMS (INR)
# Based on Schedule of Rates (SOR) & Samagra Shiksha guidelines
# ─────────────────────────────────────────────
INTERVENTION_COST_NORMS = {
    "New_Classrooms": {"per_unit": 6_00_000, "max_units": 10, "unit": "classroom"},
    "Repairs":        {"per_unit": 1_50_000, "max_units": 20, "unit": "room"},
    "Sanitation":     {"per_unit":   75_000, "max_units":  8, "unit": "toilet_block"},
    "Lab":            {"per_unit": 5_00_000, "max_units":  3, "unit": "lab"},
    "Digital":        {"per_unit": 2_00_000, "max_units":  5, "unit": "unit"},
}
COMPOSITE_GRANT_MULTIPLIER = 3.0

# ─────────────────────────────────────────────
# VALIDATION THRESHOLDS
# ─────────────────────────────────────────────
MAX_FUNDING_RATIO        = 5.0
ANOMALY_CONTAMINATION    = 0.08
MIN_TRAINING_SAMPLES     = 50

# ─────────────────────────────────────────────
# ENROLLMENT COLUMNS (class-wise, used in pipeline)
# ─────────────────────────────────────────────
CLASS_COLS_BOYS  = [f"c{i}_b" for i in range(1, 13)]
CLASS_COLS_GIRLS = [f"c{i}_g" for i in range(1, 13)]

# Primary = classes 1-5, Upper Primary = 6-8, Secondary = 9-10
PRIMARY_COLS       = [f"c{i}_b" for i in range(1, 6)]  + [f"c{i}_g" for i in range(1, 6)]
UPPER_PRIMARY_COLS = [f"c{i}_b" for i in range(6, 9)]  + [f"c{i}_g" for i in range(6, 9)]
SECONDARY_COLS     = [f"c{i}_b" for i in range(9, 11)] + [f"c{i}_g" for i in range(9, 11)]