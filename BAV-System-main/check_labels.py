"""
Examine validation label distribution in the dataset
"""
import pandas as pd

df = pd.read_csv("app/data/final_dataset.csv")

print("=" * 80)
print("VALIDATION LABEL DISTRIBUTION")
print("=" * 80)
print()

print("Value Counts:")
print(df['validation_label'].value_counts().sort_index())
print()

print("Percentage Distribution:")
print(df['validation_label'].value_counts(normalize=True).sort_index() * 100)
print()

print(f"Total Records: {len(df)}")
print(f"Valid (1): {(df['validation_label'] == 1).sum()}")
print(f"Invalid (0): {(df['validation_label'] == 0).sum()}")
print()

print("Risk Level Distribution:")
print(df['risk_level'].value_counts())
print()

print("School Level Distribution:")
print(df['school_level'].value_counts())
print()

# Show schools with infrastructure gaps
print("Schools with infrastructure_gap:")
infrastructure_gap = df['infrastructure_gap'].value_counts().sort_index()
print(infrastructure_gap.head(10))
print()

# Check for any valid schools
if (df['validation_label'] == 1).any():
    print("✓ Found some valid schools!")
    valid_schools = df[df['validation_label'] == 1].head(5)
    print("\nFirst 5 Valid Schools:")
    print(valid_schools[['pseudocode', 'school_level', 'total_students', 'total_tch', 'risk_score', 'risk_level']])
else:
    print("✗ No valid schools in dataset - all labeled as invalid")
    print("\nThis means the validation norms are either:")
    print("  1. Very strict - no school meets all requirements")
    print("  2. The dataset is pre-filtered to show only failing schools")
    print("  3. The validation criteria haven't been met by any school yet")
