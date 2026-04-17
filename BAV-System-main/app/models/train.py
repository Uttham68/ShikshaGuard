"""
app/models/train.py
────────────────────
Trains all three models on the real UDISE+ dataset:
  1. Random Forest   → validation_label classifier (Accept/Flag/Reject)
  2. XGBoost         → enrollment forecaster (regression)
  3. Isolation Forest→ anomaly detector

Run:
    python app/models/train.py

All artifacts saved to app/models/artifacts/
"""

import sys
import logging
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, IsolationForest
from sklearn.model_selection import train_test_split, StratifiedKFold, cross_val_score
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import (
    classification_report, confusion_matrix,
    mean_absolute_error, r2_score,
)
from xgboost import XGBRegressor

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from config import (
    FINAL_DATASET, ARTIFACTS_DIR,
    MODEL_VALIDATOR, MODEL_FORECASTER, MODEL_ANOMALY,
    MODEL_FEATURES, MODEL_LABEL_ENC,
    ANOMALY_CONTAMINATION, MIN_TRAINING_SAMPLES,
)
from app.utils.feature_builder import build_feature_matrix, FEATURE_COLUMNS

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────
# LOAD DATA
# ─────────────────────────────────────────────────────────────

def load_dataset() -> pd.DataFrame:
    if not FINAL_DATASET.exists():
        raise FileNotFoundError(
            f"Dataset not found: {FINAL_DATASET}\n"
            f"Run: python app/data/pipeline.py first"
        )
    df = pd.read_csv(FINAL_DATASET)
    log.info(f"Loaded dataset: {len(df)} rows × {df.shape[1]} cols")

    if len(df) < MIN_TRAINING_SAMPLES:
        raise ValueError(
            f"Only {len(df)} rows — need ≥{MIN_TRAINING_SAMPLES} to train."
        )
    return df


# ─────────────────────────────────────────────────────────────
# MODEL 1 — RANDOM FOREST CLASSIFIER
# ─────────────────────────────────────────────────────────────

def train_validator(df: pd.DataFrame) -> dict:
    log.info("=" * 50)
    log.info("MODEL 1 — Random Forest Validator")
    log.info("=" * 50)

    X = build_feature_matrix(df)
    y_raw = df["validation_label"].values

    # Encode labels
    le = LabelEncoder()
    y = le.fit_transform(y_raw)
    log.info(f"Classes: {dict(zip(le.classes_, le.transform(le.classes_)))}")
    log.info(f"Class distribution: {dict(zip(*np.unique(y_raw, return_counts=True)))}")

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    clf = RandomForestClassifier(
        n_estimators=300,
        max_depth=12,
        min_samples_leaf=5,
        min_samples_split=10,
        class_weight="balanced",   # handles imbalanced Accept/Flag/Reject
        random_state=42,
        n_jobs=-1,
    )
    clf.fit(X_train, y_train)

    # Evaluate
    y_pred = clf.predict(X_test)
    acc = (y_pred == y_test).mean()

    log.info(f"\nTest Accuracy: {acc:.4f} ({acc*100:.2f}%)")
    log.info("\nClassification Report:")
    log.info("\n" + classification_report(
        y_test, y_pred, target_names=le.classes_
    ))

    # Cross-validation for robustness
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    cv_scores = cross_val_score(clf, X, y, cv=cv, scoring="accuracy", n_jobs=-1)
    log.info(f"5-Fold CV Accuracy: {cv_scores.mean():.4f} ± {cv_scores.std():.4f}")

    # Feature importance
    importances = pd.Series(clf.feature_importances_, index=FEATURE_COLUMNS)
    top10 = importances.nlargest(10)
    log.info(f"\nTop 10 features:\n{top10.round(4).to_string()}")

    # Save
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(clf, MODEL_VALIDATOR)
    joblib.dump(le,  MODEL_LABEL_ENC)
    joblib.dump(list(FEATURE_COLUMNS), MODEL_FEATURES)
    log.info(f"Saved feature list: {len(FEATURE_COLUMNS)} features → {MODEL_FEATURES}")
    log.info(f"Saved: {MODEL_VALIDATOR}")

    return {
        "model": "RandomForestClassifier",
        "test_accuracy": round(float(acc), 4),
        "cv_accuracy_mean": round(float(cv_scores.mean()), 4),
        "cv_accuracy_std": round(float(cv_scores.std()), 4),
        "n_train": len(X_train),
        "n_test": len(X_test),
        "classes": le.classes_.tolist(),
    }


# ─────────────────────────────────────────────────────────────
# MODEL 2 — XGBOOST FORECASTER
# ─────────────────────────────────────────────────────────────

def train_forecaster(df: pd.DataFrame) -> dict:
    log.info("=" * 50)
    log.info("MODEL 2 — XGBoost Enrollment Forecaster")
    log.info("=" * 50)

    X = build_feature_matrix(df)

    # Target: total_students (we predict enrollment given school features)
    # In production, you'd use multi-year data for true forecasting.
    # With single-year data we train a school-profile → enrollment estimator,
    # then at inference time use it to project "if X classrooms added → Y students".
    y = df["total_students"].values.astype(float)

    # Remove total_students from features to avoid target leakage
    feature_cols_no_target = [c for c in FEATURE_COLUMNS if c != "total_students"]
    X_notarget = X[feature_cols_no_target]

    X_train, X_test, y_train, y_test = train_test_split(
        X_notarget, y, test_size=0.2, random_state=42
    )

    model = XGBRegressor(
        n_estimators=400,
        max_depth=6,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        reg_alpha=0.1,
        reg_lambda=1.0,
        random_state=42,
        n_jobs=-1,
        verbosity=0,
    )
    model.fit(
        X_train, y_train,
        eval_set=[(X_test, y_test)],
        verbose=False,
    )

    y_pred = model.predict(X_test)
    mae = mean_absolute_error(y_test, y_pred)
    r2  = r2_score(y_test, y_pred)

    log.info(f"MAE:  {mae:.2f} students")
    log.info(f"R²:   {r2:.4f}")

    joblib.dump(model, MODEL_FORECASTER)
    joblib.dump(feature_cols_no_target,
                ARTIFACTS_DIR / "forecaster_features.joblib")
    log.info(f"Saved: {MODEL_FORECASTER}")

    return {
        "model": "XGBRegressor",
        "mae_students": round(float(mae), 2),
        "r2_score": round(float(r2), 4),
        "n_train": len(X_train),
        "n_test": len(X_test),
    }


# ─────────────────────────────────────────────────────────────
# MODEL 3 — ISOLATION FOREST ANOMALY DETECTOR
# ─────────────────────────────────────────────────────────────

def train_anomaly_detector(df: pd.DataFrame) -> dict:
    log.info("=" * 50)
    log.info("MODEL 3 — Isolation Forest Anomaly Detector")
    log.info("=" * 50)

    X = build_feature_matrix(df)

    # Handle missing values (REQUIRED for IsolationForest)
    X = X.replace([np.inf, -np.inf], np.nan)
    
    # Option 1 (recommended): fill with median
    X = X.fillna(X.median())
    
    # Optional: if still any NaN remains
    X = X.fillna(0)

    iso = IsolationForest(
        n_estimators=200,
        contamination=ANOMALY_CONTAMINATION,
        max_features=0.8,
        random_state=42,
        n_jobs=-1,
    )
    iso.fit(X)

    scores = iso.decision_function(X)
    preds  = iso.predict(X)
    anomaly_count = (preds == -1).sum()

    log.info(f"Anomalies detected in training data: {anomaly_count} "
             f"({anomaly_count/len(df)*100:.1f}%)")
    log.info(f"Anomaly score range: [{scores.min():.4f}, {scores.max():.4f}]")

    joblib.dump(iso, MODEL_ANOMALY)
    log.info(f"Saved: {MODEL_ANOMALY}")

    return {
        "model": "IsolationForest",
        "contamination": ANOMALY_CONTAMINATION,
        "training_anomalies_detected": int(anomaly_count),
        "training_anomaly_pct": round(anomaly_count / len(df) * 100, 2),
    }


# ─────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────

def _version_artifacts():
    """
    Save timestamped copy of current artifacts.
    Keeps last 3 versions. Enables rollback.
    Directory: app/models/artifacts/versions/YYYYMMDD_HHMMSS/
    """
    import shutil
    from datetime import datetime
    versions_dir = ARTIFACTS_DIR / "versions"
    versions_dir.mkdir(exist_ok=True)

    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    version_path = versions_dir / ts
    version_path.mkdir()

    for artifact in ARTIFACTS_DIR.glob("*.joblib"):
        shutil.copy2(artifact, version_path / artifact.name)

    log.info(f"Artifacts versioned → {version_path}")

    # Keep only last 3 versions
    all_versions = sorted(versions_dir.iterdir(), key=lambda p: p.stat().st_mtime)
    for old in all_versions[:-3]:
        shutil.rmtree(old)
        log.info(f"Pruned old version: {old.name}")


def list_versions() -> list:
    """Return available model versions for rollback."""
    versions_dir = ARTIFACTS_DIR / "versions"
    if not versions_dir.exists():
        return []
    return sorted(
        [{"version": p.name, "artifacts": [f.name for f in p.glob("*.joblib")]}
         for p in versions_dir.iterdir() if p.is_dir()],
        key=lambda x: x["version"], reverse=True
    )


def rollback_to(version_ts: str) -> bool:
    """
    Rollback all artifacts to a previous version.
    version_ts: timestamp string like "20240415_143022"
    Returns True on success.
    """
    import shutil
    version_path = ARTIFACTS_DIR / "versions" / version_ts
    if not version_path.exists():
        raise FileNotFoundError(f"Version {version_ts} not found")

    for artifact in version_path.glob("*.joblib"):
        shutil.copy2(artifact, ARTIFACTS_DIR / artifact.name)

    log.info(f"Rolled back artifacts to version: {version_ts}")
    return True


def train_all() -> dict:
    log.info("╔══════════════════════════════════════════════════╗")
    log.info("║      BAV SYSTEM — MODEL TRAINING                 ║")
    log.info("╚══════════════════════════════════════════════════╝")

    df = load_dataset()

    results = {}
    results["validator"]        = train_validator(df)
    results["forecaster"]       = train_forecaster(df)
    results["anomaly_detector"] = train_anomaly_detector(df)

    # ── Version the artifacts: save timestamped copy, keep last 3
    _version_artifacts()

    log.info("╔══════════════════════════════════════════════════╗")
    log.info("║      TRAINING COMPLETE — SUMMARY                 ║")
    log.info("╚══════════════════════════════════════════════════╝")
    log.info(f"Validator   accuracy : {results['validator']['test_accuracy']*100:.2f}%")
    log.info(f"Validator   CV       : {results['validator']['cv_accuracy_mean']*100:.2f}% ± {results['validator']['cv_accuracy_std']*100:.2f}%")
    log.info(f"Forecaster  R²       : {results['forecaster']['r2_score']:.4f}")
    log.info(f"Forecaster  MAE      : {results['forecaster']['mae_students']:.1f} students")
    log.info(f"Anomaly     flagged  : {results['anomaly_detector']['training_anomaly_pct']:.1f}%")

    return results


if __name__ == "__main__":
    train_all()