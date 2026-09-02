"""
Phase 1 - Course Dataset Preprocessing

Input:
    data/raw/courses_1500_raw.csv

Outputs:
    data/processed/courses_clean.csv
    data/processed/courses_canonical.csv
    data/processed/course_features.csv
    data/reports/phase1_data_quality_report.json
"""

from pathlib import Path
import json
import re
import pandas as pd


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
RAW_FILE = BASE_DIR / "raw" / "courses_1500_raw.csv"

PROCESSED_DIR = BASE_DIR / "processed"
REPORTS_DIR = BASE_DIR / "reports"

CLEAN_FILE = PROCESSED_DIR / "courses_clean.csv"
CANONICAL_FILE = PROCESSED_DIR / "courses_canonical.csv"
FEATURE_FILE = PROCESSED_DIR / "course_features.csv"
REPORT_FILE = REPORTS_DIR / "phase1_data_quality_report.json"


# ============================================================
# HELPERS
# ============================================================

def clean_text(value):
    """Normalize general text fields."""

    if pd.isna(value):
        return ""

    value = str(value)

    # Normalize whitespace
    value = re.sub(r"\s+", " ", value)

    return value.strip()


def normalize_title(value):
    """Create a normalized title for duplicate detection."""

    value = clean_text(value).lower()

    # Normalize punctuation
    value = re.sub(r"[^\w\s]", " ", value)

    # Normalize whitespace
    value = re.sub(r"\s+", " ", value)

    return value.strip()


def normalize_category(value):
    """Normalize category values."""

    value = clean_text(value)

    category_map = {
        "IT & Software": "IT & Software",
        "Information Technology": "Information Technology",
        "Computer Science": "Computer Science",
        "Data Science": "Data Science",
        "Business": "Business",
    }

    return category_map.get(value, value)


def normalize_level(value):
    """Normalize course level."""

    value = clean_text(value)

    level_map = {
        "Beginner": "Beginner",
        "Intermediate": "Intermediate",
        "Advanced": "Advanced",
        "Mixed": "Mixed",
    }

    return level_map.get(value, value)


def build_course_text(row):
    """
    Create the textual representation used later by TF-IDF.
    """

    parts = [
        f"Title: {row['title']}",
        f"Platform: {row['platform']}",
        f"Category: {row['category']}",
        f"Level: {row['level']}",
        f"Instructor: {row['instructor']}",
        f"Learning Product: {row['learning_product']}",
        f"Skills: {row['skills']}",
    ]

    return " | ".join(parts)


# ============================================================
# LOAD DATA
# ============================================================

print("=" * 70)
print("PHASE 1 - COURSE DATASET PREPROCESSING")
print("=" * 70)

if not RAW_FILE.exists():
    raise FileNotFoundError(f"Raw dataset not found: {RAW_FILE}")

df = pd.read_csv(RAW_FILE)

print(f"\nLoaded rows: {len(df)}")
print(f"Columns: {list(df.columns)}")


# ============================================================
# REQUIRED COLUMNS
# ============================================================

required_columns = [
    "course_id",
    "title",
    "platform",
    "category",
    "instructor",
    "learning_product",
    "level",
    "duration",
    "skills",
    "rating",
    "reviews",
    "data_source",
    "url",
]

missing_columns = [
    col for col in required_columns
    if col not in df.columns
]

if missing_columns:
    raise ValueError(
        f"Missing required columns: {missing_columns}"
    )


# ============================================================
# CLEAN TEXT FIELDS
# ============================================================

text_columns = [
    "title",
    "platform",
    "category",
    "instructor",
    "learning_product",
    "level",
    "duration",
    "skills",
    "data_source",
    "url",
]

for column in text_columns:
    df[column] = df[column].apply(clean_text)


# ============================================================
# NORMALIZATION
# ============================================================

df["title_norm"] = df["title"].apply(normalize_title)

df["category"] = df["category"].apply(normalize_category)

df["level"] = df["level"].apply(normalize_level)


# ============================================================
# NUMERIC FIELDS
# ============================================================

df["course_id"] = pd.to_numeric(
    df["course_id"],
    errors="coerce"
).astype("Int64")

df["rating"] = pd.to_numeric(
    df["rating"],
    errors="coerce"
)

df["reviews"] = pd.to_numeric(
    df["reviews"],
    errors="coerce"
)

# Rating 0 means "unrated" for this dataset,
# rather than a genuine zero-star rating.
df["rating_known"] = df["rating"] > 0

df["rating_clean"] = df["rating"].where(
    df["rating"] > 0,
    pd.NA
)

# Reviews below zero are invalid.
df.loc[df["reviews"] < 0, "reviews"] = pd.NA


# ============================================================
# DUPLICATE GROUP IDENTIFICATION
# ============================================================

df["duplicate_title_platform"] = df.duplicated(
    ["title_norm", "platform"],
    keep=False
)

df["duplicate_title_platform_level"] = df.duplicated(
    ["title_norm", "platform", "level"],
    keep=False
)


# ============================================================
# CANONICAL GROUP
# ============================================================

df["canonical_key"] = (
    df["title_norm"]
    + "||"
    + df["platform"].str.lower()
)

# Each identical title/platform combination belongs
# to one canonical course group.
df["canonical_course_id"] = (
    df.groupby("canonical_key", sort=False)
    .ngroup()
    + 1
)


# ============================================================
# COURSE TEXT FOR RECOMMENDATION
# ============================================================

df["course_text"] = df.apply(
    build_course_text,
    axis=1
)


# ============================================================
# SAVE CLEAN DATA
# ============================================================

PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

df.to_csv(
    CLEAN_FILE,
    index=False
)

print(f"\nSaved clean dataset:")
print(CLEAN_FILE)


# ============================================================
# BUILD CANONICAL DATASET
# ============================================================

# Preserve the first course record while combining
# category information from duplicate title/platform groups.

canonical_rows = []

for canonical_key, group in df.groupby(
    "canonical_key",
    sort=False
):

    first = group.iloc[0].copy()

    categories = sorted(
        set(
            value
            for value in group["category"]
            if value
        )
    )

    skills = sorted(
        set(
            value.strip()
            for value in group["skills"]
            if value
        )
    )

    first["category"] = " | ".join(categories)

    first["skills"] = " | ".join(skills)

    first["source_course_ids"] = ",".join(
        str(x)
        for x in group["course_id"]
    )

    first["source_row_count"] = len(group)

    first["course_text"] = build_course_text(first)

    canonical_rows.append(first)


canonical_df = pd.DataFrame(canonical_rows)

canonical_df.to_csv(
    CANONICAL_FILE,
    index=False
)

print(f"Saved canonical dataset:")
print(CANONICAL_FILE)


# ============================================================
# FEATURE DATASET
# ============================================================

feature_columns = [
    "course_id",
    "canonical_course_id",
    "title",
    "platform",
    "category",
    "level",
    "skills",
    "course_text",
]

features_df = df[feature_columns].copy()

features_df.to_csv(
    FEATURE_FILE,
    index=False
)

print(f"Saved feature dataset:")
print(FEATURE_FILE)


# ============================================================
# DATA QUALITY REPORT
# ============================================================

zero_rating_count = int(
    ((df["rating"] == 0) | (df["rating"].isna())).sum()
)

zero_review_count = int(
    ((df["reviews"] == 0) | (df["reviews"].isna())).sum()
)

report = {
    "phase": "Phase 1 - Dataset Engineering",

    "dataset": {
        "rows": int(len(df)),
        "columns": int(len(df.columns)),
    },

    "platform_counts": {
        str(k): int(v)
        for k, v in df["platform"]
        .value_counts()
        .to_dict()
        .items()
    },

    "unique_course_ids": int(
        df["course_id"].nunique()
    ),

    "duplicate_course_ids": int(
        df["course_id"].duplicated().sum()
    ),

    "duplicate_title_platform_rows": int(
        df["duplicate_title_platform"].sum()
    ),

    "duplicate_title_platform_level_rows": int(
        df["duplicate_title_platform_level"].sum()
    ),

    "canonical_course_count": int(
        canonical_df["canonical_course_id"].nunique()
    ),

    "missing_values": {
        str(k): int(v)
        for k, v in df.isna().sum().to_dict().items()
    },

    "url_missing": int(
        df["url"].eq("").sum()
    ),

    "rating": {
        "zero_or_missing": zero_rating_count,
        "minimum": float(df["rating"].min()),
        "maximum": float(df["rating"].max()),
        "mean": float(df["rating"].mean()),
    },

    "reviews": {
        "zero_or_missing": zero_review_count,
        "minimum": int(df["reviews"].min()),
        "maximum": int(df["reviews"].max()),
    },

    "learning_product_counts": {
        str(k): int(v)
        for k, v in df["learning_product"]
        .value_counts()
        .to_dict()
        .items()
    },

    "output_files": {
        "clean": str(CLEAN_FILE),
        "canonical": str(CANONICAL_FILE),
        "features": str(FEATURE_FILE),
    },
}

with open(
    REPORT_FILE,
    "w",
    encoding="utf-8"
) as f:
    json.dump(
        report,
        f,
        indent=2,
        ensure_ascii=False
    )

print("\nSaved quality report:")
print(REPORT_FILE)


# ============================================================
# SUMMARY
# ============================================================

print("\n" + "=" * 70)
print("PHASE 1 PREPROCESSING COMPLETE")
print("=" * 70)

print(f"Original courses       : {len(df)}")
print(f"Canonical courses      : {len(canonical_df)}")
print(
    f"Duplicate title groups : "
    f"{df['canonical_key'].nunique()}"
)

print(
    f"Zero/unrated courses   : "
    f"{zero_rating_count}"
)

print(
    f"Missing URLs           : "
    f"{df['url'].eq('').sum()}"
)

print("\nOutputs:")
print(f"1. {CLEAN_FILE}")
print(f"2. {CANONICAL_FILE}")
print(f"3. {FEATURE_FILE}")
print(f"4. {REPORT_FILE}")
