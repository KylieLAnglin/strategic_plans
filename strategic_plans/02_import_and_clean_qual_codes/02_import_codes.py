# %%
"""
  - Purpose: Main code processing and hierarchical code creation
  - Key operations:
    - Imports both excerpts and codes export files from Dedoose
    - Creates codebook dictionary from code structure
    - Processes and cleans code column names (removes spaces, special
  characters)
    - Aggregates codes at district level using groupby().max()
    - Implements hierarchical coding: Makes parent codes True when child
  codes are True
    - Converts boolean codes to binary (0/1) format
    - Outputs: plans_codes.csv (final coded dataset)
"""
import pandas as pd
import re
from strategic_plans.library import start
import numpy as np

# %% Load metadata
# Read document metadata that links districts to Dedoose documents
meta_data_df = pd.read_csv(start.MAIN_DIR + "data/clean/dedoose_doc_df.csv")

# %% Load Dedoose exports
# Import the latest Dedoose chart excerpts (contains actual coded data);
# current export files are pinned in library/start.py
code_df = pd.read_excel(start.LATEST_CHART_EXPORT)
print(f"Number of unique media titles in code data: {code_df['Media Title'].nunique()}")

# Import the codebook (contains code definitions and hierarchy)
codebook_df = pd.read_excel(start.LATEST_CODEBOOK_EXPORT)
print(f"Number of unique codes in codebook: {len(codebook_df)}")

# Import the crosswalk: the codebook of record mapping each analyzed code
# column to its display name, top-level code, and type (goal vs subgroup)
crosswalk_df = pd.read_excel(start.CROSSWALK_FILE)

# %% Process codebook for clean code names
# Define patterns to standardize code names (spaces, punctuation, etc. become underscores)
# Include apostrophes, parentheses, and other special characters that might appear in code titles
patterns = [r"\s+", r"-", r",+", r"_+", r"/+", r"\\", r"'", r"\(", r"\)", r"&", r"\.", r":", r";"]
regex_pattern = "|".join(patterns)

# Create clean, standardized code names from titles
codebook_df["code"] = codebook_df.Title.str.replace(regex_pattern, "_", regex=True)
# Remove multiple consecutive underscores and leading/trailing underscores
codebook_df["code"] = codebook_df["code"].str.replace("_+", "_", regex=True)
codebook_df["code"] = codebook_df["code"].str.strip("_")
codebook_df["code"] = codebook_df.code.str.lower()
codebook_df = codebook_df.set_index("Id")

print("Examples of code name cleaning:")
for i, (idx, row) in enumerate(codebook_df.head(10).iterrows()):
    print(f"  {row.get('Title', 'N/A')} -> {row['code']}")
    if i >= 5:  # Limit output
        break
# %% Prepare code data
# Prepare media names by removing .pdf extension
code_df["media_name"] = code_df["Media Title"].str.replace(".pdf", "")

# Extract code columns and prepare for merge
# Keep only media name and actual code columns (those starting with 'Code:')
code_df = code_df[["media_name"] + [col for col in code_df.columns if "Code:" in col]]

# %% Merge metadata with code data
# Standardize names for matching (replace hyphens with underscores)
meta_data_df["dedoose_name"] = meta_data_df["revised_name"].str.replace("-", "_")

# Merge metadata with coded data
long_df = meta_data_df.merge(
    code_df,
    left_on="dedoose_name",
    right_on="media_name",
    indicator="_merge_qual",
    how="outer",
)

# %% Filter to complete qualitative coding sample
# Keep only districts that completed qualitative coding and are included in analysis
long_df = long_df[long_df.complete_qual == 1]
long_df = long_df[long_df.include_qual == 1]

print(f"After filtering, {long_df.leaid.nunique()} districts with qualitative coding data")

# %% Clean column names
# Standardize column names: remove 'Code: ' prefix and convert to lowercase
long_df.columns = [col.replace("Code: ", "code_").lower() for col in long_df.columns]

# Apply regex pattern to clean all column names consistently (same as codebook cleaning)
compiled_pattern = re.compile(regex_pattern)
long_df.columns = [
    compiled_pattern.sub("_", col) for col in long_df.columns
]

# Remove multiple consecutive underscores and leading/trailing underscores from column names
long_df.columns = [
    re.sub("_+", "_", col).strip("_") for col in long_df.columns
]

print("Column name cleaning complete.")
print(f"Sample cleaned column names: {[col for col in long_df.columns if 'code_' in col][:5]}")


# %% Identify and aggregate code columns
# Extract all code columns that indicate whether a code was applied
codes = [col for col in long_df.columns if "code_" in col and "applied" in col]
print(f"Found {len(codes)} code columns to process")

# Aggregate codes at district level using max (if any excerpt has code=1, district gets 1)
df = long_df[["leaid"] + codes].groupby("leaid").max()
print(f"Aggregated data for {len(df)} districts")


# %% Merge with metadata and clean final dataset
# Merge aggregated codes back with metadata
df_final = meta_data_df.merge(
    df, left_on="leaid", right_index=True, how="left", indicator="_merge"
)

print(f"Final merge: {(df_final._merge == 'both').sum()} districts with codes, {(df_final._merge == 'left_only').sum()} without codes")

# Convert boolean values to binary (0/1) for applied columns
applied_cols = [col for col in df_final.columns if "applied" in col]

# Replace TRUE/FALSE with 1/0
df_final[applied_cols] = df_final[applied_cols].replace({True: 1, False: 0})

# Fill any remaining NaN values with 0 (districts without any codes)
df_final[applied_cols] = df_final[applied_cols].fillna(0)
print(f"Converted {len(applied_cols)} applied columns to binary format")

# %%
# Address problem with parent and community codes

PARENT_CODE_FILE = start.DATA_DIR + "clean/plans_codes_previous_parent_and_community.csv"
KEEP_COLUMNS = ["leaid", "code_family_and_community_community_connection_and_buy_in_applied", "code_family_and_community_parent_communication_and_involvement_applied"]

correct_parent_codes = pd.read_csv(PARENT_CODE_FILE)
correct_parent_codes = correct_parent_codes[KEEP_COLUMNS]

# Drop the residual column from the current export before the rename below
# recreates it, otherwise the dataset ends up with two columns of the same
# name; the residual (11 districts) is a subset of the corrected column (67)
df_final = df_final.drop(
    columns=["code_parent_communication_and_involvement_applied"], errors="ignore"
)

# Merge correct parent codes back into final dataset
df_final = df_final.merge(correct_parent_codes[KEEP_COLUMNS], on="leaid", how="left")
df_final = df_final.rename(
    columns={
        "code_family_and_community_community_connection_and_buy_in_applied": "code_community_connection_and_buy_in_applied",
        "code_family_and_community_parent_communication_and_involvement_applied": "code_parent_communication_and_involvement_applied",
    }
)

# "code_parent_communication_and_involvement_applied" delete?

df_final["code_community_connection_and_buy_in_applied"] = np.where(df_final["code_zz_merge_community_economic_development_applied"] == 1, 1, df_final["code_community_connection_and_buy_in_applied"])
CODES_TO_REMOVE = ["code_zz_delete_family_and_community_applied", 
                   "code_zz_delete_new_community_connection_and_buy_in_applied", 
                   "code_zz_merge_community_economic_development_applied", 
                   "code_other_unknown_applied", 
                   "code_old_community_connection_and_buy_in_applied"]

df_final = df_final.drop(columns=CODES_TO_REMOVE, errors="ignore")

# %% Clean up final dataset
# Remove columns that are no longer needed for analysis
columns_to_drop = [
    "pdf_name",           # Redundant filename info
    "revised_name",       # Used only for merging
    "original_document_name",
    "district_x",         # Merge conflict
    "filepath",           
    "plan_downloaded",    
    "include_ml",
    "complete_qual", 
    "include_qual",
    "document_csv_created",
    "pdf_downloaded",
    "district_y",         # Merge conflict
    "text",               # Full text not needed
    "filename",
    "contains_alphanumeric",
    "failed_parse",
    "_merge_meta",        
    "media_title",
]


df_final = df_final.drop(columns=columns_to_drop, errors="ignore")
# %% Validate code columns against the crosswalk
# Every applied code column must have a crosswalk row and vice versa; failing
# loudly here catches renames/additions in Dedoose the day they appear
code_columns = [col for col in df_final.columns if "code_" in col and "applied" in col]

duplicated_columns = df_final.columns[df_final.columns.duplicated()].tolist()
assert not duplicated_columns, f"Duplicate columns in final dataset: {duplicated_columns}"

columns_missing_from_crosswalk = sorted(set(code_columns) - set(crosswalk_df.code_column))
crosswalk_rows_missing_from_data = sorted(set(crosswalk_df.code_column) - set(code_columns))
assert not columns_missing_from_crosswalk, (
    f"Code columns with no crosswalk row (new or renamed code in Dedoose? "
    f"add to {start.CROSSWALK_FILE}): {columns_missing_from_crosswalk}"
)
assert not crosswalk_rows_missing_from_data, (
    f"Crosswalk rows with no matching code column (code removed or renamed "
    f"in Dedoose?): {crosswalk_rows_missing_from_data}"
)
print(f"Crosswalk validation passed: {len(code_columns)} code columns all matched")

# %% Add code titles for reference
# Titles come from the crosswalk so they survive renames in Dedoose
crosswalk_titles = crosswalk_df.set_index("code_column")["dedoose_title"]
for code_col in code_columns:
    df_final[code_col + "_title"] = crosswalk_titles[code_col]
print(f"Added titles for {len(code_columns)} code columns")

# %% Create top-level code columns
# A district gets a top-level code if any of its member goal codes applied
goal_crosswalk = crosswalk_df[crosswalk_df.code_type == "goal"]

for top_level_code in goal_crosswalk.top_level_code.unique():
    member_columns = goal_crosswalk[
        goal_crosswalk.top_level_code == top_level_code
    ].code_column.tolist()

    clean_top_level = re.sub(regex_pattern + r"|\+", "_", top_level_code)
    clean_top_level = re.sub("_+", "_", clean_top_level).strip("_").lower()
    top_level_column = "top_" + clean_top_level + "_applied"

    df_final[top_level_column] = df_final[member_columns].max(axis=1)
    print(
        f"{top_level_column}: {int(df_final[top_level_column].sum())} districts "
        f"({len(member_columns)} member codes)"
    )

# %% Sanity-check counts against the previous version of the dataset
previous_path = start.MAIN_DIR + "data/clean/plans_codes.csv"
try:
    previous_df = pd.read_csv(previous_path)
    for code_col in code_columns:
        if code_col in previous_df.columns:
            previous_count = pd.to_numeric(previous_df[code_col], errors="coerce").fillna(0).sum()
            new_count = df_final[code_col].sum()
            if previous_count != new_count:
                print(f"Count changed for {code_col}: {int(previous_count)} -> {int(new_count)}")
except FileNotFoundError:
    print("No previous plans_codes.csv to compare against")

# %% Save final dataset
output_path = start.MAIN_DIR + "data/clean/plans_codes.csv"
df_final.to_csv(output_path, index=False)
print(f"Final dataset saved to: {output_path}")
print(f"Dataset shape: {df_final.shape[0]} districts × {df_final.shape[1]} columns")


# %%

# %%
