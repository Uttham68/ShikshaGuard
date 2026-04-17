import pandas as pd
import numpy as np
import os

print("Script started")
def create_pipeline():


    
    print("Pipeline running")
    # ----------------------------
    # 1. LOAD DATA
    # ----------------------------
    base_path = "app/data"

    try:
        teachers = pd.read_csv(f"{base_path}/teachers.csv")
        enrollment = pd.read_csv(f"{base_path}/enrollment.csv")
        infra = pd.read_csv(f"{base_path}/facilities.csv")
    except FileNotFoundError as e:
        print(f"❌ Error loading files: {e}")
        return

    # ----------------------------
    # 2. CLEAN COLUMN NAMES + TYPES
    # ----------------------------
    teachers.columns = teachers.columns.str.strip()
    enrollment.columns = enrollment.columns.str.strip()
    infra.columns = infra.columns.str.strip()

    teachers["pseudocode"] = teachers["pseudocode"].astype(str)
    enrollment["pseudocode"] = enrollment["pseudocode"].astype(str)
    infra["pseudocode"] = infra["pseudocode"].astype(str)

    # ----------------------------
    # 3. AGGREGATE ENROLLMENT
    # ----------------------------
    student_cols = [
        col for col in enrollment.columns
        if col.endswith('_b') or col.endswith('_g')
    ]

    enrollment_agg = (
        enrollment
        .groupby("pseudocode")[student_cols]
        .sum()
        .reset_index()
    )

    enrollment_agg["total_students"] = enrollment_agg[student_cols].sum(axis=1)

    # ----------------------------
    # 4. CLEAN INFRASTRUCTURE
    # ----------------------------
    infra_cols = [
        "electricity_availability",
        "library_availability",
        "playground_available",
        "internet"
    ]

    for col in infra_cols:
        if col in infra.columns:
            infra[f"{col}_norm"] = np.where(infra[col] == 1, 1, 0)
        else:
            print(f"⚠️ Warning: {col} not found. Filling with 0.")
            infra[f"{col}_norm"] = 0

    # Weighted infra score
    infra["infra_score"] = (
        infra["electricity_availability_norm"] * 2 +
        infra["internet_norm"] * 2 +
        infra["library_availability_norm"] * 1 +
        infra["playground_available_norm"] * 1
    )

    # Remove duplicates
    teachers = teachers.drop_duplicates(subset=["pseudocode"])
    infra = infra.drop_duplicates(subset=["pseudocode"])

    # ----------------------------
    # 5. MERGE DATA
    # ----------------------------
    df = teachers.merge(enrollment_agg, on="pseudocode", how="inner")
    df = df.merge(infra, on="pseudocode", how="inner")

    if df.empty:
        print("❌ Merge failed: dataset is empty. Check pseudocode alignment.")
        return

    # ----------------------------
    # 6. FEATURE ENGINEERING
    # ----------------------------
    df["total_tch"] = df["total_tch"].fillna(0)

    safe_teachers = np.where(df["total_tch"] <= 0, 1, df["total_tch"])
    df["student_teacher_ratio"] = (df["total_students"] / safe_teachers).round(2)

    df["required_classrooms"] = np.ceil(df["total_students"] / 40).astype(int)

    if "total_class_rooms" in df.columns:
        # FIX: Handle NaNs before arithmetic to prevent ValueError on .astype(int)
        df["total_class_rooms"] = df["total_class_rooms"].fillna(0)
        
        df["classroom_deficit"] = df["required_classrooms"] - df["total_class_rooms"]
        df["classroom_deficit"] = np.where(df["classroom_deficit"] < 0, 0, df["classroom_deficit"])
        df["classroom_deficit"] = df["classroom_deficit"].astype(int)

    # ----------------------------
    # 7. VALIDATION LOGIC
    # ----------------------------
    def validate(row):
        if row["infra_score"] < 2:
            return "Rejected"
        elif row["student_teacher_ratio"] > 40:
            return "Flagged"
        else:
            return "Accepted"

    df["validation"] = df.apply(validate, axis=1)

    # ----------------------------
    # 8. DEBUG CHECKS
    # ----------------------------
    print("\n🔍 Data Quality Check (Missing Values):")
    missing_data = df.isnull().sum()
    missing_data = missing_data[missing_data > 0]
    
    if missing_data.empty:
        print("No missing values found in the merged dataset.")
    else:
        print(missing_data)
        
    print(f"\nDataset Shape: {df.shape}")

  # ----------------------------
    # 9. SAVE DATASET
    # ----------------------------
    os.makedirs(base_path, exist_ok=True)
    output_path = f"{base_path}/final_dataset.csv"

    df.to_csv(output_path, index=False)

    print(f"\n✅ Final dataset saved at: {output_path}")
    
    # FIX: Dynamically build the print columns to prevent KeyError
    print_cols = [
        "pseudocode",
        "total_students",
        "total_tch",
        "student_teacher_ratio",
        "infra_score",
        "validation"
    ]
    
    if "classroom_deficit" in df.columns:
        print_cols.insert(-1, "classroom_deficit") # Insert right before validation


    print(df[print_cols].head())

if __name__ == "__main__":
    create_pipeline()