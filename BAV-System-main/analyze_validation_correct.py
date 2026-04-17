"""
Correct validation analysis using categorical labels
"""
import pandas as pd
import joblib
import numpy as np
from pathlib import Path

# ─────────────────────────────────────────────────────────────────
# LOAD DATA AND MODEL
# ─────────────────────────────────────────────────────────────────

dataset_path = Path("app/data/final_dataset.csv")
model_path = Path("app/models/artifacts/rf_validator.joblib")
features_path = Path("app/models/artifacts/feature_names.joblib")

print("=" * 90)
print("SCHOOL INFRASTRUCTURE VALIDATION ANALYSIS (CATEGORICAL LABELS)")
print("=" * 90)
print()

# Load dataset
df = pd.read_csv(dataset_path)
print(f"✓ Loaded {len(df)} schools from dataset")
print()

# Load model and feature names
model = joblib.load(model_path)
feature_names = joblib.load(features_path)

print(f"✓ Loaded RF validator model with classes: {model.classes_}")
print(f"✓ Loaded {len(feature_names)} features")
print()

print("-" * 90)
print("VALIDATION LABEL DISTRIBUTION")
print("-" * 90)
print()

# Show label distribution
label_dist = df['validation_label'].value_counts()
print(f"Accept (✓ PASSES):     {label_dist.get('Accept', 0):>4} schools ({label_dist.get('Accept', 0)/len(df)*100:>5.2f}%)")
print(f"Flag (⚠ NEEDS REVIEW): {label_dist.get('Flag', 0):>4} schools ({label_dist.get('Flag', 0)/len(df)*100:>5.2f}%)")
print(f"Reject (✗ FAILS):      {label_dist.get('Reject', 0):>4} schools ({label_dist.get('Reject', 0)/len(df)*100:>5.2f}%)")
print()

# ─────────────────────────────────────────────────────────────────
# PREPARE FEATURES & GET PREDICTIONS
# ─────────────────────────────────────────────────────────────────

available_features = [f for f in feature_names if f in df.columns]
X = df[available_features].fillna(0)

# Get predictions and probabilities
predictions = model.predict(X)
probabilities = model.predict_proba(X)

# Create results dataframe
results = pd.DataFrame({
    'pseudocode': df['pseudocode'].values,
    'school_level': df.get('school_level', 'Unknown').values,
    'total_students': df.get('total_students', 0).values,
    'total_tch': df.get('total_tch', 0).values,
    'risk_score': df.get('risk_score', 0).values,
    'risk_level': df.get('risk_level', 'Unknown').values,
    'actual_label': df.get('validation_label', 'Unknown').values,
    'predicted_label': predictions,
})

# Add confidence for Accept class (highest success)
accept_idx = list(model.classes_).index('Accept') if 'Accept' in model.classes_ else 0
results['accept_confidence'] = probabilities[:, accept_idx]

print()
print("=" * 90)
print("TOP 20 SCHOOLS WITH HIGHEST VALIDATION SUCCESS RATE (ACCEPT CONFIDENCE)")
print("=" * 90)
print()

# Get schools predicted as Accept or with highest confidence
top_schools = results.sort_values(by=['accept_confidence'], ascending=False).head(20)

print(f"{'Rank':<6} {'School ID':<15} {'Level':<15} {'Students':<12} {'Teachers':<10} {'Risk':<8} {'Actual':<12} {'Accept %':<10}")
print("-" * 90)

for idx, (i, row) in enumerate(top_schools.iterrows(), 1):
    print(f"{idx:<6} {str(row['pseudocode']):<15} {str(row['school_level']):<15} "
          f"{int(row['total_students']):<12} {int(row['total_tch']):<10} "
          f"{str(row['risk_level']):<8} {str(row['actual_label']):<12} {row['accept_confidence']*100:>8.2f}%")

print()
print("🏆 HIGHEST SUCCESS RATE SCHOOL:")
best = top_schools.iloc[0]
print(f"   School ID: {best['pseudocode']}")
print(f"   School Level: {best['school_level']}")
print(f"   Students: {int(best['total_students'])}")
print(f"   Teachers: {int(best['total_tch'])}")
print(f"   Risk Level: {best['risk_level']}")
print(f"   Risk Score: {best['risk_score']:.2f}")
print(f"   Actual Validation Status: {best['actual_label']}")
print(f"   Accept Probability: {best['accept_confidence']*100:.2f}%")
print()

# ─────────────────────────────────────────────────────────────────
# SCHOOLS PREDICTED AS ACCEPT
# ─────────────────────────────────────────────────────────────────

print("=" * 90)
print("TOP 15 SCHOOLS PREDICTED AS 'ACCEPT' (MEETS ALL VALIDATION NORMS)")
print("=" * 90)
print()

accept_schools = results[results['predicted_label'] == 'Accept'].sort_values(
    by=['accept_confidence'], ascending=False
).head(15)

if len(accept_schools) > 0:
    print(f"{'Rank':<6} {'School ID':<15} {'Level':<15} {'Students':<12} {'Teachers':<10} {'Risk':<8} {'Actual':<12} {'Accept %':<10}")
    print("-" * 90)
    
    for idx, (i, row) in enumerate(accept_schools.iterrows(), 1):
        status = "✓" if row['actual_label'] == 'Accept' else "⚠"
        print(f"{idx:<6} {str(row['pseudocode']):<15} {str(row['school_level']):<15} "
              f"{int(row['total_students']):<12} {int(row['total_tch']):<10} "
              f"{str(row['risk_level']):<8} {str(row['actual_label']):<12} {row['accept_confidence']*100:>8.2f}%")
else:
    print("No schools predicted as Accept")

print()

# ─────────────────────────────────────────────────────────────────
# SCHOOLS ACTUALLY LABELED AS ACCEPT (VALIDATION PASSES)
# ─────────────────────────────────────────────────────────────────

print("=" * 90)
print("TOP 15 SCHOOLS ACTUALLY LABELED AS 'ACCEPT' (HIGHEST ACCEPTANCE CONFIDENCE)")
print("=" * 90)
print()

truly_accept = results[results['actual_label'] == 'Accept'].sort_values(
    by=['accept_confidence'], ascending=False
).head(15)

if len(truly_accept) > 0:
    print(f"{'Rank':<6} {'School ID':<15} {'Level':<15} {'Students':<12} {'Teachers':<10} {'Risk':<8} {'Predicted':<12} {'Accept %':<10}")
    print("-" * 90)
    
    for idx, (i, row) in enumerate(truly_accept.iterrows(), 1):
        print(f"{idx:<6} {str(row['pseudocode']):<15} {str(row['school_level']):<15} "
              f"{int(row['total_students']):<12} {int(row['total_tch']):<10} "
              f"{str(row['risk_level']):<8} {str(row['predicted_label']):<12} {row['accept_confidence']*100:>8.2f}%")
    
    print()
    print("🥇 #1 SCHOOL WITH HIGHEST VALIDATION SUCCESS RATE:")
    first = truly_accept.iloc[0]
    print(f"   School ID: {first['pseudocode']}")
    print(f"   School Level: {first['school_level']}")
    print(f"   Total Students: {int(first['total_students'])}")
    print(f"   Total Teachers: {int(first['total_tch'])}")
    print(f"   Risk Level: {first['risk_level']}")
    print(f"   Risk Score: {first['risk_score']:.2f}")
    print(f"   Validation Status: {first['actual_label']}")
    print(f"   Model Confidence (Accept): {first['accept_confidence']*100:.2f}%")

print()

# ─────────────────────────────────────────────────────────────────
# MODEL ACCURACY
# ─────────────────────────────────────────────────────────────────

print("=" * 90)
print("MODEL PERFORMANCE")
print("=" * 90)
print()

accurate = (results['actual_label'] == results['predicted_label']).sum()
accuracy = (accurate / len(results)) * 100

print(f"Model Accuracy: {accuracy:.2f}%")
print(f"Correct Predictions: {accurate}/{len(results)}")
print()

# Confusion matrix style
print("Prediction Breakdown:")
for label in model.classes_:
    actual_count = (results['actual_label'] == label).sum()
    predicted_count = (results['predicted_label'] == label).sum()
    correct = ((results['actual_label'] == label) & (results['predicted_label'] == label)).sum()
    print(f"  {label:>8}: {actual_count:>4} actual, {predicted_count:>4} predicted, {correct:>4} correct")

print()

# ─────────────────────────────────────────────────────────────────
# SUCCESS METRICS BY CATEGORY
# ─────────────────────────────────────────────────────────────────

print("=" * 90)
print("VALIDATION SUCCESS RATE BY SCHOOL LEVEL & RISK")
print("=" * 90)
print()

print("By School Level:")
for level in results['school_level'].unique():
    subset = results[results['school_level'] == level]
    accept_pct = (subset['actual_label'] == 'Accept').sum() / len(subset) * 100
    avg_confidence = subset[subset['actual_label'] == 'Accept']['accept_confidence'].mean() * 100 if (subset['actual_label'] == 'Accept').any() else 0
    print(f"  {level:>15}: {accept_pct:>5.2f}% Accept | Avg Confidence: {avg_confidence:>6.2f}%")

print()
print("By Risk Level:")
for risk in ['Low', 'Medium', 'High']:
    subset = results[results['risk_level'] == risk]
    if len(subset) > 0:
        accept_pct = (subset['actual_label'] == 'Accept').sum() / len(subset) * 100
        avg_score = subset['risk_score'].mean()
        print(f"  {risk:>15}: {accept_pct:>5.2f}% Accept | Avg Risk Score: {avg_score:>6.2f}")

print()
print("=" * 90)
print("ANALYSIS COMPLETE")
print("=" * 90)
