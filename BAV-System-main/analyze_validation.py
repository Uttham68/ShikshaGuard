"""
Analyze school validation success rates using the RF validator model
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

print("=" * 80)
print("SCHOOL INFRASTRUCTURE VALIDATION ANALYSIS")
print("=" * 80)
print()

# Load dataset
df = pd.read_csv(dataset_path)
print(f"✓ Loaded {len(df)} schools from dataset")
print(f"  Columns: {df.shape[1]}")
print()

# Load model and feature names
try:
    model = joblib.load(model_path)
    print(f"✓ Loaded RF validator model")
except Exception as e:
    print(f"✗ Failed to load model: {e}")
    exit(1)

try:
    feature_names = joblib.load(features_path)
    print(f"✓ Loaded feature names ({len(feature_names)} features)")
except Exception as e:
    print(f"✗ Failed to load feature names: {e}")
    exit(1)

print()
print("-" * 80)
print("MODEL PREDICTIONS & VALIDATION SUCCESS RATES")
print("-" * 80)
print()

# ─────────────────────────────────────────────────────────────────
# PREPARE FEATURES
# ─────────────────────────────────────────────────────────────────

# Ensure all required features exist
missing_features = [f for f in feature_names if f not in df.columns]
if missing_features:
    print(f"⚠ Warning: Missing features: {missing_features}")

# Select only available features that model expects
available_features = [f for f in feature_names if f in df.columns]
X = df[available_features].fillna(0)

print(f"Using {len(available_features)} features for prediction")
print()

# ─────────────────────────────────────────────────────────────────
# RUN PREDICTIONS & CALCULATE SUCCESS RATES
# ─────────────────────────────────────────────────────────────────

try:
    # Get predictions (1 = passes validation, 0 = fails)
    predictions = model.predict(X)
    
    # Get prediction probabilities
    probabilities = model.predict_proba(X)
    
    # Create results dataframe
    results = pd.DataFrame({
        'pseudocode': df['pseudocode'].values,
        'school_level': df.get('school_level', 'Unknown').values,
        'total_students': df.get('total_students', 0).values,
        'total_tch': df.get('total_tch', 0).values,
        'risk_score': df.get('risk_score', 0).values,
        'risk_level': df.get('risk_level', 'Unknown').values,
        'validation_label': df.get('validation_label', 0).values,
        'prediction': predictions,
        'confidence': probabilities[:, 1],  # Probability of passing
    })
    
    # Calculate validation success (1 = PASS, 0 = FAIL)
    results['is_valid'] = (results['validation_label'] == 1).astype(int)
    results['prediction_correct'] = (results['prediction'] == results['is_valid']).astype(int)
    
    print(f"✓ Generated predictions for {len(results)} schools")
    print()
    
except Exception as e:
    print(f"✗ Prediction failed: {e}")
    exit(1)

# ─────────────────────────────────────────────────────────────────
# ANALYZE BY SCHOOL & FIND TOP PERFORMERS
# ─────────────────────────────────────────────────────────────────

# Calculate overall statistics
total_valid = results['is_valid'].sum()
total_invalid = (1 - results['is_valid']).sum()
accurate_predictions = results['prediction_correct'].sum()
model_accuracy = (accurate_predictions / len(results)) * 100

print("OVERALL STATISTICS:")
print(f"  Total Schools: {len(results)}")
print(f"  Valid (Pass Norms): {total_valid} ({total_valid/len(results)*100:.1f}%)")
print(f"  Invalid (Fail Norms): {total_invalid} ({total_invalid/len(results)*100:.1f}%)")
print(f"  Model Accuracy: {model_accuracy:.2f}%")
print()

# ─────────────────────────────────────────────────────────────────
# TOP PERFORMERS (HIGHEST VALIDATION SUCCESS RATE)
# ─────────────────────────────────────────────────────────────────

print("=" * 80)
print("TOP 15 SCHOOLS WITH HIGHEST VALIDATION SUCCESS RATES")
print("=" * 80)
print()

# Sort by validation success (is_valid), then by confidence
top_schools = results[results['is_valid'] == 1].sort_values(
    by=['confidence'], ascending=False
).head(15)

if len(top_schools) > 0:
    print(f"{'Rank':<6} {'School ID':<15} {'Level':<10} {'Students':<12} {'Teachers':<10} {'Risk Score':<12} {'Confidence':<12}")
    print("-" * 85)
    
    for idx, (i, row) in enumerate(top_schools.iterrows(), 1):
        print(f"{idx:<6} {str(row['pseudocode']):<15} {str(row['school_level']):<10} "
              f"{int(row['total_students']):<12} {int(row['total_tch']):<10} "
              f"{row['risk_score']:<12.2f} {row['confidence']:<12.4f}")
    
    print()
    print("✓ HIGHEST SUCCESS RATE SCHOOL:")
    best = top_schools.iloc[0]
    print(f"  School ID: {best['pseudocode']}")
    print(f"  Level: {best['school_level']}")
    print(f"  Students: {int(best['total_students'])}")
    print(f"  Teachers: {int(best['total_tch'])}")
    print(f"  Risk Score: {best['risk_score']:.2f}")
    print(f"  Validation Success Confidence: {best['confidence']:.4f} ({best['confidence']*100:.2f}%)")
    print(f"  Risk Level: {best['risk_level']}")
else:
    print("⚠ No valid schools found")

print()

# ─────────────────────────────────────────────────────────────────
# SCHOOLS FAILING VALIDATION (NEEDS IMPROVEMENT)
# ─────────────────────────────────────────────────────────────────

print("=" * 80)
print("TOP 10 SCHOOLS FAILING VALIDATION (NEEDS INFRASTRUCTURE IMPROVEMENT)")
print("=" * 80)
print()

failing_schools = results[results['is_valid'] == 0].sort_values(
    by=['confidence'], ascending=True
).head(10)

if len(failing_schools) > 0:
    print(f"{'Rank':<6} {'School ID':<15} {'Level':<10} {'Students':<12} {'Teachers':<10} {'Risk Score':<12} {'Confidence':<12}")
    print("-" * 85)
    
    for idx, (i, row) in enumerate(failing_schools.iterrows(), 1):
        print(f"{idx:<6} {str(row['pseudocode']):<15} {str(row['school_level']):<10} "
              f"{int(row['total_students']):<12} {int(row['total_tch']):<10} "
              f"{row['risk_score']:<12.2f} {row['confidence']:<12.4f}")
else:
    print("✓ All schools pass validation!")

print()

# ─────────────────────────────────────────────────────────────────
# RISK DISTRIBUTION
# ─────────────────────────────────────────────────────────────────

print("=" * 80)
print("VALIDATION SUCCESS BY RISK LEVEL")
print("=" * 80)
print()

risk_analysis = results.groupby('risk_level').agg({
    'is_valid': ['sum', 'count', 'mean'],
    'risk_score': 'mean',
    'confidence': 'mean'
}).round(3)

print(risk_analysis)
print()

# ─────────────────────────────────────────────────────────────────
# SCHOOL LEVEL ANALYSIS
# ─────────────────────────────────────────────────────────────────

print("=" * 80)
print("VALIDATION SUCCESS BY SCHOOL LEVEL")
print("=" * 80)
print()

level_analysis = results.groupby('school_level').agg({
    'is_valid': ['sum', 'count', 'mean'],
    'risk_score': 'mean',
    'total_students': 'mean'
}).round(3)

print(level_analysis)
print()

print("=" * 80)
print("ANALYSIS COMPLETE")
print("=" * 80)
