# %%
"""
  - Purpose: Main code processing and hierarchical code creation
  - Source: ContentCoder exports (applied_codes_{date}.csv + codebook_{date}.csv),
  pinned in library/start.py. The Dedoose exports were imported into
  ContentCoder once (seeding); ContentCoder is now the source of record.
  - Key operations:
    - Imports the applied-codes file (one row per excerpt x applied code)
    - Builds document-level code indicators, then aggregates codes at the
  district level using groupby().max()
    - Takes variable names (code_column, level1/2/3_column), table-ready
  code titles, and level groupings directly from the codebook export, so
  renaming or reorganizing codes in the app's Codebook tab flows through
  here on the next export (no crosswalk file needed)
    - Outputs: plans_codes.csv (final coded dataset)
"""
import pandas as pd

from strategic_plans.library import start

# %%
# ------------------ SETUP ------------------
META_DATA_PATH = start.MAIN_DIR + "data/clean/contentcoder_doc_df.csv"
OUTPUT_PATH = start.MAIN_DIR + "data/clean/plans_codes.csv"

NUM_EXAMPLE_CODE_NAMES = 6

CODES_TO_REMOVE = ["code_other_unknown_applied"]

COLUMNS_TO_DROP = [
    "pdf_name",
    "revised_name",
    "original_document_name",
    "district_x",
    "filepath",
    "plan_downloaded",
    "include_ml",
    "complete_qual",
    "include_qual",
    "document_csv_created",
    "pdf_downloaded",
    "district_y",
    "text",
    "filename",
    "contains_alphanumeric",
    "failed_parse",
    "_merge_meta",
    "media_title",
    "media_name",
]

# %%
# ------------------ LOAD METADATA ------------------
meta_data_df = pd.read_csv(META_DATA_PATH)

# %%
# ------------------ LOAD CONTENTCODER EXPORTS ------------------
applied_df = pd.read_csv(start.LATEST_APPLIED_CODES)
print(f"Number of unique media titles in code data: {applied_df['media_title'].nunique()}")

codebook_df = pd.read_csv(start.LATEST_CODEBOOK)
codebook_df = codebook_df[codebook_df.is_category == 0]
print(f"Number of unique codes in codebook: {len(codebook_df)}")

print("Examples of code column names from the codebook export:")
for _, row in codebook_df.head(NUM_EXAMPLE_CODE_NAMES).iterrows():
    print(f"  {row.code_path} -> {row.code_column}")

# %%
# ------------------ BUILD DOCUMENT-LEVEL CODE INDICATORS ------------------
applied_df["media_name"] = applied_df["media_title"].str.replace(".pdf", "")
applied_df = applied_df.merge(
    codebook_df[["code_id", "code_column"]], on="code_id", how="left"
)

code_df = (
    applied_df.assign(applied=1)
    .pivot_table(index="media_name", columns="code_column", values="applied", aggfunc="max")
    .reset_index()
)

for code_column in codebook_df.code_column:
    if code_column not in code_df.columns:
        code_df[code_column] = 0

# %%
# ------------------ MERGE METADATA WITH CODE DATA ------------------
meta_data_df["media_name"] = meta_data_df["media_title"].str.replace(".pdf", "")

long_df = meta_data_df.merge(
    code_df,
    on="media_name",
    indicator="_merge_qual",
    how="outer",
)

# %%
# ------------------ FILTER TO COMPLETE QUALITATIVE CODING SAMPLE ------------------
long_df = long_df[long_df.complete_qual == 1]
long_df = long_df[long_df.include_qual == 1]

print(f"After filtering, {long_df.leaid.nunique()} districts with qualitative coding data")

# %%
# ------------------ AGGREGATE CODE COLUMNS AT THE DISTRICT LEVEL ------------------
codes = [col for col in long_df.columns if "code_" in col and "applied" in col]
print(f"Found {len(codes)} code columns to process")

df = long_df[["leaid"] + codes].groupby("leaid").max()
print(f"Aggregated data for {len(df)} districts")

# %%
# ------------------ MERGE WITH METADATA AND CLEAN ------------------
df_final = meta_data_df.merge(
    df, left_on="leaid", right_index=True, how="left", indicator="_merge"
)

print(f"Final merge: {(df_final._merge == 'both').sum()} districts with codes, {(df_final._merge == 'left_only').sum()} without codes")

applied_cols = [col for col in df_final.columns if "applied" in col]
df_final[applied_cols] = df_final[applied_cols].replace({True: 1, False: 0})
df_final[applied_cols] = df_final[applied_cols].fillna(0).astype(int)
print(f"Converted {len(applied_cols)} applied columns to binary format")

df_final = df_final.drop(columns=CODES_TO_REMOVE, errors="ignore")
df_final = df_final.drop(columns=COLUMNS_TO_DROP, errors="ignore")

# %%
# ------------------ WARN ON STALE-EXPORT MISMATCH ------------------
code_columns = [col for col in df_final.columns if "code_" in col and "applied" in col]

expected_code_columns = set(codebook_df.code_column) - set(CODES_TO_REMOVE)
columns_missing_from_codebook = sorted(set(code_columns) - expected_code_columns)
codebook_rows_missing_from_data = sorted(expected_code_columns - set(code_columns))
if columns_missing_from_codebook:
    print(f"WARNING: code columns with no codebook row (stale codebook export?): {columns_missing_from_codebook}")
if codebook_rows_missing_from_data:
    print(f"WARNING: codebook rows with no matching code column (stale applied-codes export?): {codebook_rows_missing_from_data}")

# %%
# ------------------ ADD CODE TITLES FOR REFERENCE ------------------
codebook_titles = codebook_df.set_index("code_column")["code_title"]
for code_col in code_columns:
    df_final[code_col + "_title"] = codebook_titles[code_col]
print(f"Added titles for {len(code_columns)} code columns")

# %%
# ------------------ CREATE LEVEL AGGREGATE COLUMNS ------------------
level_count = len([col for col in codebook_df.columns if col.startswith("level") and col.endswith("_column")])
print(f"Codebook export supports {level_count} levels")

for level_number in range(1, level_count + 1):
    level_column_assignments = codebook_df[f"level{level_number}_column"]
    for level_column in sorted(level_column_assignments.dropna().unique()):
        member_columns = codebook_df.loc[
            level_column_assignments == level_column, "code_column"
        ].tolist()
        member_columns = [col for col in member_columns if col in df_final.columns]
        if not member_columns:
            print(f"{level_column}: no member codes with data, skipped")
            continue
        df_final[level_column] = df_final[member_columns].max(axis=1)
        print(
            f"{level_column}: {int(df_final[level_column].sum())} districts "
            f"({len(member_columns)} member codes)"
        )

# %%
# ------------------ SANITY-CHECK COUNTS AGAINST THE PREVIOUS DATASET ------------------
previous_df = pd.read_csv(OUTPUT_PATH)
for code_col in code_columns:
    if code_col in previous_df.columns:
        previous_count = pd.to_numeric(previous_df[code_col], errors="coerce").fillna(0).sum()
        new_count = df_final[code_col].sum()
        if previous_count != new_count:
            print(f"Count changed for {code_col}: {int(previous_count)} -> {int(new_count)}")

# %%
# ------------------ SAVE ------------------
df_final.to_csv(OUTPUT_PATH, index=False)
print(f"Saved: {OUTPUT_PATH}")
print(f"Dataset shape: {df_final.shape[0]} districts × {df_final.shape[1]} columns")
