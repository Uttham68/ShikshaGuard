"""
app/utils/feature_builder.py
─────────────────────────────
Builds the exact feature vector used by all ML models.
Called during training (on dataset rows) AND at prediction time
(on a single proposal dict). Same function = no train/serve skew.
"""

import sys
import numpy as np
import pandas as pd
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from config import PTR_THRESHOLDS, GRANT_NORMS


# ── These are the EXACT features the models are trained on.
# ── Order matters. Never change order after training.
FEATURE_COLUMNS = [
    "total_students",
    "total_boys",
    "total_girls",
    "students_primary",
    "students_upper_primary",
    "students_secondary",
    "total_tch",
    "regular",
    "contract",
    "ptr",
    "ptr_threshold",
    "students_per_classroom",
    "classrooms_total",
    "classrooms_pucca",
    "classrooms_good",
    "has_girls_toilet",
    "has_boys_toilet",
    "has_ramp",
    "has_library",
    "has_playground",
    "has_electricity",
    "has_internet",
    "has_handwash",
    "has_boundary_wall",
    "has_comp_lab",
    "infrastructure_gap",
    "eligible_grant_norm",
    "funding_ratio",
    "qualified_teacher_ratio",
    "contract_ratio",
    "risk_score",
]


def get_grant_norm(total_students: float) -> float:
    """Lookup Samagra Shiksha composite school grant based on enrollment."""
    for threshold, amount in GRANT_NORMS:
        if total_students <= threshold:
            return float(amount)
    return float(GRANT_NORMS[-1][1])


def build_features_from_row(row: dict) -> dict:
    """
    Input:  a dict with raw school fields (from DB, proposal, or CSV row)
    Output: a dict with all engineered features in FEATURE_COLUMNS order

    Safe to call with partial data — missing fields default to 0.
    """
    r = {k: float(v) if v is not None else 0.0 for k, v in row.items()
         if isinstance(v, (int, float))}

    total_students  = r.get("total_students", 0)
    total_tch       = max(r.get("total_tch", 1), 1)
    classrooms      = max(r.get("classrooms_total", 1), 1)
    school_level    = row.get("school_level", "primary")

    # ── PTR
    ptr = total_students / total_tch
    ptr_threshold = PTR_THRESHOLDS.get(school_level, 35)
    ptr_violation_severity = (ptr - ptr_threshold) / ptr_threshold

    # ── Overcrowding
    students_per_classroom = total_students / classrooms

    # ── Infrastructure gap (mandatory items missing)
    mandatory = [
        "has_girls_toilet", "has_boys_toilet", "has_ramp",
        "has_library", "has_electricity", "has_boundary_wall",
    ]
    infrastructure_gap = sum(1 for m in mandatory if r.get(m, 0) == 0)

    # ── Grant norm
    eligible_grant_norm = get_grant_norm(total_students)

    # ── Funding ratio (proposal ask vs eligible norm)
    funding_requested = r.get("funding_requested", eligible_grant_norm)
    funding_ratio = funding_requested / eligible_grant_norm if eligible_grant_norm > 0 else 1.0

    # ── Teacher ratios
    post_grad = r.get("post_graduate_and_above", 0)
    graduate  = r.get("graduate", 0)
    qualified_teacher_ratio = min((post_grad + graduate) / total_tch, 1.0)

    contract = r.get("contract", 0)
    contract_ratio = min(contract / total_tch, 1.0)

    risk_score = r.get("risk_score", 0)

    features = {
        "total_students":          total_students,
        "total_boys":              r.get("total_boys", 0),
        "total_girls":             r.get("total_girls", 0),
        "students_primary":        r.get("students_primary", 0),
        "students_upper_primary":  r.get("students_upper_primary", 0),
        "students_secondary":      r.get("students_secondary", 0),
        "total_tch":               total_tch,
        "regular":                 r.get("regular", 0),
        "contract":                contract,
        "ptr_threshold":           float(ptr_threshold),
        "ptr_violation_severity":  round(ptr_violation_severity, 4),
        "students_per_classroom":  round(students_per_classroom, 4),
        "classrooms_total":        float(classrooms),
        "classrooms_pucca":        r.get("classrooms_pucca", 0),
        "classrooms_good":         r.get("classrooms_good", 0),
        "has_girls_toilet":        r.get("has_girls_toilet", 0),
        "has_boys_toilet":         r.get("has_boys_toilet", 0),
        "has_ramp":                r.get("has_ramp", 0),
        "has_library":             r.get("has_library", 0),
        "has_playground":          r.get("has_playground", 0),
        "has_electricity":         r.get("has_electricity", 0),
        "has_internet":            r.get("has_internet", 0),
        "has_handwash":            r.get("has_handwash", 0),
        "has_boundary_wall":       r.get("has_boundary_wall", 0),
        "has_comp_lab":            r.get("has_comp_lab", 0),
        "infrastructure_gap":      float(infrastructure_gap),
        "eligible_grant_norm":     eligible_grant_norm,
        "funding_ratio":           round(funding_ratio, 4),
        "qualified_teacher_ratio": round(qualified_teacher_ratio, 4),
        "contract_ratio":          round(contract_ratio, 4),
    }
    return features


def build_feature_vector(row: dict) -> np.ndarray:
    """Returns a 1×N numpy array in FEATURE_COLUMNS order. For model inference."""
    features = build_features_from_row(row)
    import pandas as pd
    # Use DataFrame with column names to match training format → no sklearn warnings
    df = pd.DataFrame([[features.get(col, 0.0) for col in FEATURE_COLUMNS]],
                       columns=FEATURE_COLUMNS)
    return df.values


def build_feature_matrix(df: pd.DataFrame) -> pd.DataFrame:
    """Returns a DataFrame with exactly FEATURE_COLUMNS, in order. For training."""
    result = []
    for _, row in df.iterrows():
        result.append(build_features_from_row(row.to_dict()))
    return pd.DataFrame(result, columns=FEATURE_COLUMNS)