"""
Identify schools with worst performance that need rebuilding
"""
import pandas as pd
import joblib
from pathlib import Path

# Load data and model
df = pd.read_csv("app/data/final_dataset.csv")
model = joblib.load("app/models/artifacts/rf_validator.joblib")
feature_names = joblib.load("app/models/artifacts/feature_names.joblib")

print("=" * 100)
print("SCHOOLS REQUIRING INFRASTRUCTURE REBUILDING - WORST PERFORMANCE ANALYSIS")
print("=" * 100)
print()

# Prepare features and predictions
available_features = [f for f in feature_names if f in df.columns]
X = df[available_features].fillna(0)
predictions = model.predict(X)
probabilities = model.predict_proba(X)

# Get Accept class index
accept_idx = list(model.classes_).index('Accept') if 'Accept' in model.classes_ else 0

# Create results
results = pd.DataFrame({
    'pseudocode': df['pseudocode'].values,
    'school_level': df.get('school_level', 'Unknown').values,
    'total_students': df.get('total_students', 0).values,
    'total_tch': df.get('total_tch', 0).values,
    'ptr': df.get('ptr', 0).values,
    'infrastructure_gap': df.get('infrastructure_gap', 0).values,
    'eligible_grant_norm': df.get('eligible_grant_norm', 0).values,
    'classrooms_total': df.get('classrooms_total', 0).values,
    'classrooms_pucca': df.get('classrooms_pucca', 0).values,
    'classrooms_good': df.get('classrooms_good', 0).values,
    'has_girls_toilet': df.get('has_girls_toilet', 0).values,
    'has_boys_toilet': df.get('has_boys_toilet', 0).values,
    'has_electricity': df.get('has_electricity', 0).values,
    'has_internet': df.get('has_internet', 0).values,
    'has_library': df.get('has_library', 0).values,
    'has_playground': df.get('has_playground', 0).values,
    'risk_score': df.get('risk_score', 0).values,
    'risk_level': df.get('risk_level', 'Unknown').values,
    'actual_label': df.get('validation_label', 'Unknown').values,
    'predicted_label': predictions,
    'accept_confidence': probabilities[:, accept_idx],
})

print("=" * 100)
print("REJECTED SCHOOLS (WORST CATEGORY) - SORTED BY RISK SCORE & INFRASTRUCTURE GAPS")
print("=" * 100)
print()

# Get REJECTED schools
rejected = results[results['actual_label'] == 'Reject'].sort_values(
    by=['infrastructure_gap', 'risk_score'], ascending=[False, False]
).head(15)

print(f"Total REJECTED Schools: {len(results[results['actual_label'] == 'Reject'])}")
print()
print(f"{'Rank':<6} {'School ID':<15} {'Level':<12} {'Students':<10} {'Teachers':<10} {'Inf.Gap':<10} {'Risk':<8} {'Classrooms':<12} {'Accept %':<10}")
print("-" * 100)

for idx, (i, row) in enumerate(rejected.iterrows(), 1):
    print(f"{idx:<6} {str(row['pseudocode']):<15} {str(row['school_level']):<12} "
          f"{int(row['total_students']):<10} {int(row['total_tch']):<10} "
          f"{int(row['infrastructure_gap']):<10} {str(row['risk_level']):<8} "
          f"{int(row['classrooms_total']):<12} {row['accept_confidence']*100:>8.2f}%")

print()
print("=" * 100)
print("🔴 WORST PERFORMING SCHOOL (NEEDS COMPLETE REBUILDING)")
print("=" * 100)
print()

if len(rejected) > 0:
    worst = rejected.iloc[0]
    
    print(f"School ID: {worst['pseudocode']}")
    print(f"School Level: {worst['school_level']}")
    print(f"Validation Status: {worst['actual_label']} ❌")
    print(f"Model Accept Confidence: {worst['accept_confidence']*100:.2f}% (Very Low)")
    print()
    print("CRITICAL ISSUES:")
    print(f"  • Risk Score: {worst['risk_score']:.2f} ({worst['risk_level']}) ⚠️ CRITICAL")
    print(f"  • Infrastructure Gaps: {int(worst['infrastructure_gap'])} issues ⚠️ SEVERE")
    print()
    print("INFRASTRUCTURE STATUS:")
    print(f"  • Total Students: {int(worst['total_students'])}")
    print(f"  • Total Teachers: {int(worst['total_tch'])}")
    print(f"  • Teacher-Student Ratio: 1:{worst['ptr']:.1f} {'✓' if worst['ptr'] < 40 else '❌'}")
    print(f"  • Total Classrooms: {int(worst['classrooms_total'])} (Pucca: {int(worst['classrooms_pucca'])}, Good: {int(worst['classrooms_good'])})")
    print(f"  • Electricity: {'✓ YES' if worst['has_electricity'] else '❌ NO'}")
    print(f"  • Internet: {'✓ YES' if worst['has_internet'] else '❌ NO'}")
    print(f"  • Girls Toilet: {'✓ YES' if worst['has_girls_toilet'] else '❌ NO'}")
    print(f"  • Boys Toilet: {'✓ YES' if worst['has_boys_toilet'] else '❌ NO'}")
    print(f"  • Library: {'✓ YES' if worst['has_library'] else '❌ NO'}")
    print(f"  • Playground: {'✓ YES' if worst['has_playground'] else '❌ NO'}")
    print(f"  • Eligible for Grant: {worst['eligible_grant_norm']:.2f}")
    print()

print()
print("=" * 100)
print("TOP 10 REJECTED SCHOOLS REQUIRING IMMEDIATE REBUILDING PRIORITY")
print("=" * 100)
print()

for rank, (i, row) in enumerate(rejected.head(10).iterrows(), 1):
    print(f"\n{rank}. School ID: {row['pseudocode']}")
    print(f"   Level: {row['school_level']} | Students: {int(row['total_students'])} | Teachers: {int(row['total_tch'])}")
    print(f"   Infrastructure Gaps: {int(row['infrastructure_gap'])} | Risk Score: {row['risk_score']:.2f} ({row['risk_level']})")
    
    # Identify missing infrastructure
    missing = []
    if not row['has_girls_toilet']: missing.append("Girls Toilet")
    if not row['has_boys_toilet']: missing.append("Boys Toilet")
    if not row['has_electricity']: missing.append("Electricity")
    if not row['has_internet']: missing.append("Internet")
    if not row['has_library']: missing.append("Library")
    if not row['has_playground']: missing.append("Playground")
    
    if missing:
        print(f"   Missing: {', '.join(missing)}")
    
    print(f"   Classrooms: {int(row['classrooms_total'])} (Good condition: {int(row['classrooms_good'])})")
    print(f"   → Rebuilding Priority: 🔴 CRITICAL")

print()
print()
print("=" * 100)
print("FLAGGED SCHOOLS (MEDIUM PRIORITY) - HIGHEST RISK AMONG FLAGGED")
print("=" * 100)
print()

# Get FLAGGED schools sorted by risk
flagged = results[results['actual_label'] == 'Flag'].sort_values(
    by=['risk_score', 'infrastructure_gap'], ascending=[False, False]
).head(10)

print(f"Total FLAGGED Schools: {len(results[results['actual_label'] == 'Flag'])}")
print()
print(f"{'Rank':<6} {'School ID':<15} {'Level':<12} {'Students':<10} {'Teachers':<10} {'Inf.Gap':<10} {'Risk':<8} {'Accept %':<10}")
print("-" * 85)

for idx, (i, row) in enumerate(flagged.iterrows(), 1):
    print(f"{idx:<6} {str(row['pseudocode']):<15} {str(row['school_level']):<12} "
          f"{int(row['total_students']):<10} {int(row['total_tch']):<10} "
          f"{int(row['infrastructure_gap']):<10} {str(row['risk_level']):<8} "
          f"{row['accept_confidence']*100:>8.2f}%")

print()
print()
print("=" * 100)
print("REBUILDING PRIORITY SUMMARY")
print("=" * 100)
print()

print("🔴 CRITICAL REBUILD (Rejected - Highest Risk):")
critical = results[(results['actual_label'] == 'Reject') & (results['risk_score'] > 50)].sort_values('risk_score', ascending=False)
print(f"   Count: {len(critical)} schools")
if len(critical) > 0:
    print(f"   Top School: {critical.iloc[0]['pseudocode']} (Risk: {critical.iloc[0]['risk_score']:.2f})")

print()
print("🟠 HIGH PRIORITY (Rejected - Medium Risk):")
high = results[(results['actual_label'] == 'Reject') & (results['risk_score'] <= 50)].sort_values('risk_score', ascending=False)
print(f"   Count: {len(high)} schools")

print()
print("🟡 MEDIUM PRIORITY (Flagged - High Risk):")
medium = results[(results['actual_label'] == 'Flag') & (results['risk_score'] > 30)].sort_values('risk_score', ascending=False)
print(f"   Count: {len(medium)} schools")

print()
print("=" * 100)
print("WHAT NEEDS TO HAPPEN FOR REJECTED SCHOOLS TO GET ACCEPTED:")
print("=" * 100)
print()

print("Based on Top Performer (School 9606892):")
print("✓ Reduce Risk Score to < 10")
print("✓ Install/Repair: Girls toilet, Boys toilet, Electricity, Internet")
print("✓ Build/Maintain: Library, Playground")
print("✓ Improve classroom quality (Pucca + Good condition)")
print("✓ Maintain teacher-student ratio < 1:40")
print("✓ Ensure no infrastructure gaps (target: 0)")
print()
print("Estimated Budget Focus Areas:")
print("  1. Sanitation (Toilets) - HIGH PRIORITY")
print("  2. Utilities (Electricity/Internet) - HIGH PRIORITY")
print("  3. Learning Spaces (Library, Playground) - MEDIUM PRIORITY")
print("  4. Classroom Renovation - MEDIUM PRIORITY")

print()
print("=" * 100)
