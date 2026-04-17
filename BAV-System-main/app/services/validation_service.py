"""
app/services/validation_service.py
───────────────────────────────────
CRITICAL FIX: Always use the feature list that the model was TRAINED on.
Never hardcode FEATURE_COLUMNS — load from feature_names.joblib instead.
This makes the system immune to feature count mismatches.
"""
import sys, logging
from pathlib import Path
import joblib
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from config import MODEL_VALIDATOR, MODEL_ANOMALY, MODEL_LABEL_ENC, MODEL_FEATURES
from app.utils.feature_builder import build_features_from_row
from app.utils.rule_engine import validate as rule_validate
from app.services.ai_service import explain_decision, generate_rule_based_explanation

log = logging.getLogger(__name__)
_clf = _iso = _le = None
_model_feature_cols = None   # ← loaded from .joblib, not hardcoded


def _load_models():
    global _clf, _iso, _le, _model_feature_cols
    if _clf is None:
        if not MODEL_VALIDATOR.exists():
            raise RuntimeError(
                f"Model not found: {MODEL_VALIDATOR}\n"
                f"Run: python app/models/train.py"
            )
        _clf = joblib.load(MODEL_VALIDATOR)
        _iso = joblib.load(MODEL_ANOMALY)
        _le  = joblib.load(MODEL_LABEL_ENC)

        # Load the exact feature list the model was trained on
        if MODEL_FEATURES.exists():
            _model_feature_cols = joblib.load(MODEL_FEATURES)
            log.info(f"Model expects {len(_model_feature_cols)} features: {_model_feature_cols}")
        else:
            # Fallback: infer from model's n_features_in_
            n = getattr(_clf, "n_features_in_", 28)
            from app.utils.feature_builder import FEATURE_COLUMNS
            _model_feature_cols = FEATURE_COLUMNS[:n]
            log.warning(
                f"feature_names.joblib not found — using first {n} features. "
                f"Re-run: python app/models/train.py"
            )
        log.info("Validation models loaded")


def _build_model_input(combined: dict) -> pd.DataFrame:
    """
    Build feature DataFrame using EXACTLY the features the model was trained on.
    Extra features are ignored. Missing features default to 0.
    This is the single source of truth for inference input.
    """
    features = build_features_from_row(combined)
    row = {col: features.get(col, 0.0) for col in _model_feature_cols}
    return pd.DataFrame([row], columns=_model_feature_cols)


def validate_proposal(school: dict, proposal: dict, include_ai: bool = True) -> dict:
    _load_models()
    boosted_confidence = 0.5  # safe default confidence

    # Step 1: Rule engine
    rule_result = rule_validate(school, proposal)

    # Step 2: Build feature vector matching model's training features
    combined = {}
    for d in [school, proposal]:
        for k, v in d.items():
            if isinstance(v, (int, float, bool, str)) or v is None:
                combined[k] = v
    combined["dynamic_fields"] = proposal.get("dynamic_fields", {}) or {}

    X = _build_model_input(combined)  # DataFrame with correct column names

    # Step 3: ML classifier
    ml_pred_encoded = _clf.predict(X)[0]
    ml_pred_label   = _le.inverse_transform([ml_pred_encoded])[0]
    ml_probas       = _clf.predict_proba(X)[0]
    ml_confidence   = float(np.max(ml_probas))
    proba_dict      = {cls: round(float(p), 4) for cls, p in zip(_le.classes_, ml_probas)}

    # Step 4: Anomaly detection
    anomaly_pred  = _iso.predict(X)[0]
    anomaly_score = float(_iso.decision_function(X)[0])
    is_anomaly    = bool(anomaly_pred == -1)

    # Step 5: Merge verdict
    final_verdict = _merge_verdict(
        rule_result.verdict, ml_pred_label, ml_probas, _le.classes_,
        is_anomaly, rule_result.violations
    )

    # Step 6: Feature importances (top 5)
    feature_importances = _get_top_features()

    # Step 7: AI explanation — always returns a string
    violations_list = rule_result.to_dict()["violations"]
    ai_explanation = generate_rule_based_explanation(
        final_verdict, boosted_confidence, violations_list, school, proposal
    )
    if include_ai:
        try:
            ai_resp = explain_decision(
                final_verdict, boosted_confidence, violations_list, school, proposal
            )
            if ai_resp and not ai_resp.startswith("AI service"):
                ai_explanation = ai_resp
        except Exception as e:
            log.warning(f"AI explanation failed: {e}")

    # Boost confidence via rule agreement
    boosted_confidence = _boost_confidence(
        ml_confidence, rule_result.verdict, ml_pred_label,
        rule_result.violations
    )

    return {
        "verdict":             final_verdict,
        "confidence":          round(boosted_confidence, 4),
        "ml_prediction":       ml_pred_label,
        "ml_probabilities":    proba_dict,
        "rule_verdict":        rule_result.verdict,
        "is_anomaly":          is_anomaly,
        "anomaly_detected":    is_anomaly,
        "anomaly_score":       round(anomaly_score, 4),
        "violations":          violations_list,
        "score_penalty":       rule_result.score_penalty,
        "checks_run":          rule_result.checks_run,
        "ai_explanation":      ai_explanation,
        "feature_importances": feature_importances,
    }


def _merge_verdict(rule_verdict, ml_verdict, ml_probas, classes, is_anomaly, violations) -> str:
    reject_idx  = list(classes).index("Reject") if "Reject" in classes else -1
    flag_idx    = list(classes).index("Flag")   if "Flag"   in classes else -1
    accept_idx  = list(classes).index("Accept") if "Accept" in classes else -1

    reject_prob = float(ml_probas[reject_idx]) if reject_idx >= 0 else 0.0
    flag_prob   = float(ml_probas[flag_idx])   if flag_idx  >= 0 else 0.0

    def get_sev(v):
        if hasattr(v, "severity"):  return v.severity
        if isinstance(v, dict):     return v.get("severity", "")
        return ""

    has_critical = any(get_sev(v) == "critical" for v in violations)
    has_warnings = any(get_sev(v) == "warning"  for v in violations)
    has_violations = has_critical or has_warnings

    # Rule engine is authoritative for Reject
    if rule_verdict == "Reject":                        return "Reject"
    # High ML Reject confidence + any violation → Reject
    if reject_prob > 0.75 and has_violations:           return "Reject"
    # Rule says Flag → Flag
    if rule_verdict == "Flag":                          return "Flag"
    # Anomaly ALWAYS flags — regardless of ML verdict (fix: was Accept+Accept only)
    if is_anomaly:                                      return "Flag"
    # ML Flag with reasonable confidence
    if ml_verdict == "Flag" and flag_prob > 0.4:        return "Flag"
    # Moderate Reject probability + violations
    if reject_prob > 0.5 and has_violations:            return "Flag"
    return "Accept"


def _boost_confidence(ml_confidence: float, rule_verdict: str, ml_verdict: str,
                      violations: list) -> float:
    """
    Boost confidence when rule engine and ML agree.
    Rule-based boost: same verdict from both sources = higher confidence.
    """
    def get_sev(v):
        if hasattr(v, "severity"): return v.severity
        if isinstance(v, dict):    return v.get("severity", "")
        return ""

    critical_count = sum(1 for v in violations if get_sev(v) == "critical")
    warning_count  = sum(1 for v in violations if get_sev(v) == "warning")

    boost = 0.0
    # Rule + ML agree → boost
    if rule_verdict == ml_verdict:
        boost += 0.12
    # Strong rule signal → boost
    if critical_count >= 2:
        boost += 0.08
    elif critical_count == 1:
        boost += 0.05
    elif warning_count >= 2:
        boost += 0.04
    # No violations + no anomaly → boost accept confidence
    if critical_count == 0 and warning_count == 0:
        boost += 0.06

    return min(ml_confidence + boost, 0.97)


def _get_top_features() -> dict:
    try:
        importances = _clf.feature_importances_
        top_idx = np.argsort(importances)[::-1][:5]
        return {
            _model_feature_cols[i]: round(float(importances[i]), 4)
            for i in top_idx
            if i < len(_model_feature_cols)
        }
    except Exception as e:
        log.warning(f"_get_top_features failed: {e}")
        return {}