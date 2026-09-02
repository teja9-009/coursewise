import pandas as pd
from pathlib import Path

DATA_DIR = Path(__file__).parent

coursera_path = DATA_DIR / "Coursera.csv"
udemy_path = DATA_DIR / "Udemy.csv"
output_path = DATA_DIR / "combined_courses.csv"

# Load datasets
coursera = pd.read_csv(coursera_path)
udemy = pd.read_csv(udemy_path)

# Add platform information
coursera["Platform"] = "Coursera"
udemy["Platform"] = "Udemy"

# Standardize important fields
def standardize(df):
    result = pd.DataFrame()

    result["title"] = df["Title"].fillna("").astype(str).str.strip()
    result["platform"] = df["Platform"].fillna("").astype(str).str.strip()
    result["category"] = df["Subject"].fillna("").astype(str).str.strip()
    instructor_col = "Instructor(s)" if "Instructor(s)" in df.columns else "Institution"
    result["instructor"] = df[instructor_col].fillna("").astype(str).str.strip()
    result["learning_product"] = df["Learning Product"].fillna("").astype(str).str.strip()
    result["level"] = df["Level"].fillna("").astype(str).str.strip()
    result["duration"] = df["Duration"].fillna("").astype(str).str.strip()
    result["skills"] = df["Gained Skills"].fillna("").astype(str).str.strip()

    # Convert ratings to numbers
    result["rating"] = (
        df["Rate"]
        .astype(str)
        .str.extract(r"([0-9]+(?:\.[0-9]+)?)")[0]
    )
    result["rating"] = pd.to_numeric(result["rating"], errors="coerce")

    # Convert reviews to numbers
    result["reviews"] = (
        df["Reviews"]
        .astype(str)
        .str.replace(",", "", regex=False)
        .str.extract(r"([0-9]+)")[0]
    )
    result["reviews"] = pd.to_numeric(result["reviews"], errors="coerce")

    # Keep original source field
    result["data_source"] = df["Data_Source"].fillna("").astype(str).str.strip()

    # URL is not present in these datasets, so leave it empty for now
    result["url"] = ""

    return result


coursera_clean = standardize(coursera)
udemy_clean = standardize(udemy)

# Combine both platforms
combined = pd.concat(
    [coursera_clean, udemy_clean],
    ignore_index=True
)

# Keep all source courses.
# We intentionally do not remove duplicate titles because
# different courses can legitimately share the same title.
combined = combined.reset_index(drop=True)

# Add a unique course ID
combined.insert(
    0,
    "course_id",
    range(1, len(combined) + 1)
)

# Save
combined.to_csv(output_path, index=False)

print("=" * 60)
print("COMBINED COURSE DATASET CREATED")
print("=" * 60)
print(f"Coursera courses : {len(coursera_clean)}")
print(f"Udemy courses    : {len(udemy_clean)}")
print(f"Combined courses : {len(combined)}")
print()
print("Platform counts:")
print(combined["platform"].value_counts())
print()
print("Columns:")
print(combined.columns.tolist())
print()
print("Missing values:")
print(combined.isna().sum())
print()
print(f"Saved to: {output_path}")
print("=" * 60)
