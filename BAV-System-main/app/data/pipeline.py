"""
app/data/pipeline.py
────────────────────
Loads the 3 raw Delhi UDISE+ 2023-24 CSVs, merges them on `pseudocode`,
engineers all features, and writes final_dataset.csv.

Run directly:
    python app/data/pipeline.py
"""

import sys
import logging
from pathlib import Path

import numpy as np
import pandas as pd

# Allow imports from project root
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from config import (
    RAW_ENROLLMENT, RAW_FACILITIES, RAW_TEACHERS, FINAL_DATASET,
    PTR_THRESHOLDS, GRANT_NORMS,
    PRIMARY_COLS, UPPER_PRIMARY_COLS, SECONDARY_COLS,
    CLASS_COLS_BOYS, CLASS_COLS_GIRLS,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────
# STEP 1 — LOAD RAW CSVs
# ─────────────────────────────────────────────────────────────

def load_enrollment(path: Path) -> pd.DataFrame:
    """
    enrollment.csv has multiple rows per school (one per item_group/item_id).
    We pivot to get one row per school with total students per class.
    """
    log.info(f"Loading enrollment: {path}")
    df = pd.read_csv(path, sep=None, engine="python")
    df.columns = df.columns.str.strip().str.lower()

    required = ["pseudocode"] + [c.lower() for c in CLASS_COLS_BOYS + CLASS_COLS_GIRLS]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"enrollment.csv missing columns: {missing}")

    # Sum across all item_group rows per school → one row per pseudocode
    class_cols = [c for c in CLASS_COLS_BOYS + CLASS_COLS_GIRLS if c in df.columns]
    enroll = df.groupby("pseudocode")[class_cols].sum().reset_index()

    # Derive enrollment by level
    p_cols  = [c for c in PRIMARY_COLS       if c in enroll.columns]
    up_cols = [c for c in UPPER_PRIMARY_COLS if c in enroll.columns]
    sec_cols= [c for c in SECONDARY_COLS     if c in enroll.columns]

    enroll["students_primary"]       = enroll[p_cols].sum(axis=1)  if p_cols  else 0
    enroll["students_upper_primary"] = enroll[up_cols].sum(axis=1) if up_cols else 0
    enroll["students_secondary"]     = enroll[sec_cols].sum(axis=1)if sec_cols else 0

    all_b = [c for c in CLASS_COLS_BOYS  if c in enroll.columns]
    all_g = [c for c in CLASS_COLS_GIRLS if c in enroll.columns]
    enroll["total_boys"]    = enroll[all_b].sum(axis=1)
    enroll["total_girls"]   = enroll[all_g].sum(axis=1)
    enroll["total_students"]= enroll["total_boys"] + enroll["total_girls"]

    # Determine dominant school level per school
    enroll["school_level"] = enroll.apply(_infer_school_level, axis=1)

    keep = ["pseudocode", "total_students", "total_boys", "total_girls",
            "students_primary", "students_upper_primary", "students_secondary",
            "school_level"]
    log.info(f"  → {len(enroll)} schools after enrollment pivot")
    return enroll[keep]


def _infer_school_level(row) -> str:
    """Assign school level based on which level has the most students."""
    levels = {
        "primary":       row.get("students_primary", 0),
        "upper_primary": row.get("students_upper_primary", 0),
        "secondary":     row.get("students_secondary", 0),
    }
    dominant = max(levels, key=levels.get)
    # If all zero, default to primary
    return dominant if levels[dominant] > 0 else "primary"


def load_teachers(path: Path) -> pd.DataFrame:
    log.info(f"Loading teachers: {path}")
    df = pd.read_csv(path, sep=None, engine="python")
    df.columns = df.columns.str.strip().str.lower()

    keep = [
        "pseudocode", "total_tch", "regular", "contract", "part_time",
        "trained_comp",
        "class_taught_pr", "class_taught_upr", "class_taught_pr_upr",
        "class_taught_sec_only", "class_taught_hsec_only",
        "post_graduate_and_above", "graduate",
    ]
    available = [c for c in keep if c in df.columns]
    df = df[available].copy()

    # One row per pseudocode (teachers.csv is already school-level)
    df = df.groupby("pseudocode").first().reset_index()
    log.info(f"  → {len(df)} schools in teachers file")
    return df


def load_facilities(path: Path) -> pd.DataFrame:
    log.info(f"Loading facilities: {path}")
    df = pd.read_csv(path, sep=None, engine="python")
    df.columns = df.columns.str.strip().str.lower()

    # Map raw column names → our schema names
    rename_map = {
        "total_class_rooms":          "classrooms_total",
        "pucca_building_blocks":      "classrooms_pucca",
        "classrooms_in_good_condition":"classrooms_good",
        "total_boys_toilet":          "toilets_boys_total",
        "total_boys_func_toilet":     "toilets_boys_func",
        "total_girls_toilet":         "toilets_girls_total",
        "total_girls_func_toilet":    "toilets_girls_func",
        "availability_ramps":         "has_ramp",
        "library_availability":       "has_library",
        "playground_available":       "has_playground",
        "electricity_availability":   "has_electricity",
        "internet":                   "has_internet",
        "handwash_facility_for_meal": "has_handwash",
        "boundary_wall":              "has_boundary_wall",
        "comp_lab_cond":              "has_comp_lab",
        "solar_panel":                "has_solar",
        "separate_room_for_hm":       "has_hm_room",
    }

    existing_renames = {k: v for k, v in rename_map.items() if k in df.columns}
    df = df.rename(columns=existing_renames)

    bool_cols = [
        "has_ramp", "has_library", "has_playground", "has_electricity",
        "has_internet", "has_handwash", "has_boundary_wall", "has_comp_lab",
        "has_solar", "has_hm_room",
    ]

    for col in bool_cols:
        if col in df.columns:
            # UDISE encodes: 1 = Yes, 2 = No, 9 = Not Applicable
            df[col] = df[col].apply(lambda x: 1 if x == 1 else 0)
        else:
            df[col] = 0

    # Toilet availability
    for col in ["toilets_boys_func", "toilets_girls_func",
                "toilets_boys_total", "toilets_girls_total"]:
        if col not in df.columns:
            df[col] = 0

    df["has_girls_toilet"] = (df["toilets_girls_func"] > 0).astype(int)
    df["has_boys_toilet"]  = (df["toilets_boys_func"]  > 0).astype(int)

    for col in ["classrooms_total", "classrooms_pucca", "classrooms_good"]:
        if col not in df.columns:
            df[col] = 0

    keep = ["pseudocode",
            "classrooms_total", "classrooms_pucca", "classrooms_good",
            "toilets_boys_func", "toilets_girls_func",
            "has_girls_toilet", "has_boys_toilet",
            "has_ramp", "has_library", "has_playground", "has_electricity",
            "has_internet", "has_handwash", "has_boundary_wall",
            "has_comp_lab", "has_solar", "has_hm_room"]

    available = [c for c in keep if c in df.columns]
    df = df[available]
    df = df.groupby("pseudocode").first().reset_index()
    log.info(f"  → {len(df)} schools in facilities file")
    return df


# ─────────────────────────────────────────────────────────────
# STEP 2 — MERGE
# ─────────────────────────────────────────────────────────────

def merge_datasets(enroll: pd.DataFrame,
                   teachers: pd.DataFrame,
                   facilities: pd.DataFrame) -> pd.DataFrame:
    log.info("Merging datasets on pseudocode...")

    df = enroll.merge(teachers,   on="pseudocode", how="left")
    df = df.merge(facilities,     on="pseudocode", how="left")

    # Fill missing numerics with sensible defaults
    numeric_defaults = {
        "total_tch": 1, "regular": 0, "contract": 0, "part_time": 0,
        "trained_comp": 0, "classrooms_total": 1, "classrooms_pucca": 0,
        "classrooms_good": 0,
    }
    for col, default in numeric_defaults.items():
        if col in df.columns:
            df[col] = df[col].fillna(default)

    bool_defaults = [
        "has_girls_toilet", "has_boys_toilet", "has_ramp", "has_library",
        "has_playground", "has_electricity", "has_internet", "has_handwash",
        "has_boundary_wall", "has_comp_lab",
    ]
    for col in bool_defaults:
        if col in df.columns:
            df[col] = df[col].fillna(0).astype(int)

    log.info(f"  → Merged: {len(df)} schools, {df.shape[1]} columns")
    return df


# ─────────────────────────────────────────────────────────────
# STEP 3 — FEATURE ENGINEERING
# ─────────────────────────────────────────────────────────────

def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    log.info("Engineering features...")

    # Guard: ensure total_tch is never 0 for division
    df["total_tch"] = df["total_tch"].clip(lower=1)
    df["classrooms_total"] = df["classrooms_total"].clip(lower=1)

    # ── PTR (Pupil-Teacher Ratio)
    df["ptr"] = (df["total_students"] / df["total_tch"]).round(2)

    # ── PTR threshold per school level
    df["ptr_threshold"] = df["school_level"].map(PTR_THRESHOLDS).fillna(35)

    # ── PTR violation severity: 0 = at limit, positive = over limit
    df["ptr_violation_severity"] = (
        (df["ptr"] - df["ptr_threshold"]) / df["ptr_threshold"]
    ).round(4)

    # ── Students per classroom
    df["students_per_classroom"] = (
        df["total_students"] / df["classrooms_total"]
    ).round(2)

    # ── Infrastructure gap (count of missing mandatory items, max 6)
    mandatory = [
        "has_girls_toilet", "has_boys_toilet", "has_ramp",
        "has_library", "has_electricity", "has_boundary_wall",
    ]
    avail_mandatory = [c for c in mandatory if c in df.columns]
    df["infrastructure_gap"] = len(avail_mandatory) - df[avail_mandatory].sum(axis=1)

    # ── Eligible grant norm (lookup by total_students)
    df["eligible_grant_norm"] = df["total_students"].apply(_get_grant_norm)

    # ── Funding ratio placeholder (will be filled at proposal time)
    # Here we create a baseline "implied need" ratio
    df["funding_ratio"] = 1.0   # neutral default; overridden per proposal

    # ── Growth rate: we only have one year of data, so we simulate a
    #    conservative proxy using class distribution
    #    (c1 intake vs c5/c8/c10 exit gap as a proxy for retention/growth)
    df["growth_rate"] = 0.0     # will be updated when multi-year data available

    # ── Teacher qualification ratio
    if "post_graduate_and_above" in df.columns and "graduate" in df.columns:
        df["qualified_teacher_ratio"] = (
            (df["post_graduate_and_above"] + df["graduate"]) / df["total_tch"]
        ).round(4).clip(0, 1)
    else:
        df["qualified_teacher_ratio"] = 0.5

    # ── Contract teacher ratio (instability signal)
    if "contract" in df.columns:
        df["contract_ratio"] = (df["contract"] / df["total_tch"]).round(4).clip(0, 1)
    else:
        df["contract_ratio"] = 0.0

    log.info("  → Features engineered")
    return df


def _get_grant_norm(total_students: float) -> float:
    for threshold, amount in GRANT_NORMS:
        if total_students <= threshold:
            return float(amount)
    return float(GRANT_NORMS[-1][1])


# ─────────────────────────────────────────────────────────────
# STEP 4 — GENERATE TRAINING LABELS (rule-based)
# ─────────────────────────────────────────────────────────────

def generate_labels(df: pd.DataFrame) -> pd.DataFrame:
    """
    Accept / Flag / Reject labels generated from Samagra Shiksha rules.
    The ML model will learn to replicate and generalise these rules.
    """
    log.info("Generating training labels from rules...")

    labels = []
    for _, row in df.iterrows():
        label, _ = _apply_rules(row)
        labels.append(label)

    df["validation_label"] = labels

    counts = df["validation_label"].value_counts().to_dict()
    log.info(f"  → Labels: {counts}")
    return df


def _apply_rules(row) -> tuple:
    """
    Returns (label, list_of_violations).
    Reject  → any critical rule fails
    Flag    → soft violations / warnings
    Accept  → passes all checks
    """
    violations = []
    reject_triggered = False

    ptr = row.get("ptr", 0)
    threshold = row.get("ptr_threshold", 35)
    reject_limit = threshold * 1.5

    # ── REJECT rules
    if ptr > reject_limit:
        violations.append(f"PTR {ptr:.1f} exceeds critical limit {reject_limit:.1f}")
        reject_triggered = True

    if row.get("total_students", 0) <= 0:
        violations.append("Zero student enrollment reported")
        reject_triggered = True

    if row.get("infrastructure_gap", 0) >= 5:
        violations.append("5+ mandatory infrastructure items missing — critical gap")
        reject_triggered = True

    # ── FLAG rules
    if ptr > threshold and not reject_triggered:
        violations.append(f"PTR {ptr:.1f} exceeds norm {threshold} — needs teacher")

    if row.get("students_per_classroom", 0) > 45:
        violations.append(f"Overcrowding: {row['students_per_classroom']:.0f} students/classroom")
        if not reject_triggered:
            reject_triggered = False  # flag only

    if row.get("infrastructure_gap", 0) >= 3:
        violations.append(f"Infrastructure gap score: {row['infrastructure_gap']}/6")

    if row.get("has_girls_toilet", 1) == 0:
        violations.append("No functional girls toilet — mandatory requirement")

    if row.get("has_drinking_water", row.get("has_handwash", 1)) == 0:
        violations.append("Safe drinking water facility missing")

    if row.get("has_ramp", 1) == 0:
        violations.append("CWSN ramp missing — mandatory accessibility requirement")

    if row.get("contract_ratio", 0) > 0.6:
        violations.append(f"High contract teacher ratio: {row['contract_ratio']:.0%}")

    # ── Determine final label
    if reject_triggered:
        return "Reject", violations
    elif violations:
        return "Flag", violations
    else:
        return "Accept", []


# ─────────────────────────────────────────────────────────────
# STEP 5 — RISK SCORE
# ─────────────────────────────────────────────────────────────

def compute_risk_scores(df: pd.DataFrame) -> pd.DataFrame:
    """Compute baseline risk score (0–100) from real features."""

    # PTR component (0–25)
    ptr_score = (df["ptr_violation_severity"].clip(lower=0) * 25).clip(0, 25)

    # Infrastructure gap component (0–20)
    infra_score = (df["infrastructure_gap"] / 6 * 20).clip(0, 20)

    # Funding ratio component (0–25) — neutral at this stage
    funding_score = pd.Series([0.0] * len(df))

    # Overcrowding component (0–15)
    overcrowd = ((df["students_per_classroom"] - 40) / 40 * 15).clip(0, 15)

    # Contract teacher instability (0–15)
    contract_score = (df["contract_ratio"] * 15).clip(0, 15)

    df["risk_score"] = (
        ptr_score + infra_score + funding_score + overcrowd + contract_score
    ).round(2).clip(0, 100)

    df["risk_level"] = pd.cut(
        df["risk_score"],
        bins=[0, 30, 70, 100],
        labels=["Low", "Medium", "High"],
        include_lowest=True,
    )

    log.info(f"  → Risk scores: {df['risk_level'].value_counts().to_dict()}")
    return df


# ─────────────────────────────────────────────────────────────
# MAIN PIPELINE
# ─────────────────────────────────────────────────────────────

def run_pipeline() -> pd.DataFrame:
    log.info("=" * 55)
    log.info("ShikshaGaurd DATA PIPELINE — START")
    log.info("=" * 55)

    # Validate raw files exist
    for path in [RAW_ENROLLMENT, RAW_FACILITIES, RAW_TEACHERS]:
        if not Path(path).exists():
            raise FileNotFoundError(
                f"Raw file not found: {path}\n"
                f"Place your CSVs in: {path.parent}"
            )

    enroll    = load_enrollment(RAW_ENROLLMENT)
    teachers  = load_teachers(RAW_TEACHERS)
    facilities= load_facilities(RAW_FACILITIES)

    df = merge_datasets(enroll, teachers, facilities)
    df = engineer_features(df)
    df = generate_labels(df)
    df = compute_risk_scores(df)

    # Drop rows with no students (data quality)
    before = len(df)
    df = df[df["total_students"] > 0].copy()
    dropped = before - len(df)
    if dropped:
        log.warning(f"  Dropped {dropped} rows with 0 students")

    # Save
    FINAL_DATASET.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(FINAL_DATASET, index=False)
    log.info(f"Saved: {FINAL_DATASET}")
    log.info(f"Final dataset: {len(df)} schools × {df.shape[1]} columns")
    log.info(f"Label distribution:\n{df['validation_label'].value_counts()}")
    log.info("=" * 55)
    log.info("PIPELINE COMPLETE")
    log.info("=" * 55)

    return df


if __name__ == "__main__":
    run_pipeline()