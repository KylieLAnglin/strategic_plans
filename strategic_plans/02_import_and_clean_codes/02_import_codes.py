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
    - Cleans code paths into column names (removes spaces, special characters)
    - Creates top-level code columns from the ContentCoder codebook hierarchy
  (category groupings are editable in the app's Codebook tab and flow
  through here on the next export)
    - Outputs: plans_codes.csv (final coded dataset)
"""
import pandas as pd
import re
from strategic_plans.library import start
import numpy as np

# %% Load metadata
# Read document metadata that links districts to coded documents
# (built by 01_document_metadata.py)
meta_data_df = pd.read_csv(start.MAIN_DIR + "data/clean/contentcoder_doc_df.csv")

# %% Load ContentCoder exports
# One row per excerpt x applied code; current export files are pinned in library/start.py
applied_df = pd.read_csv(start.LATEST_APPLIED_CODES)
print(f"Number of unique media titles in code data: {applied_df['media_title'].nunique()}")

# The codebook (definitions, hierarchy, and top-level category groupings)
codebook_df = pd.read_csv(start.LATEST_CODEBOOK)
codebook_df = codebook_df[codebook_df.is_category == 0]
print(f"Number of unique codes in codebook: {len(codebook_df)}")

# Import the crosswalk: maps each analyzed code column to its display name
# and type (goal vs subgroup); still the record of display-name decisions
crosswalk_df = pd.read_excel(start.CROSSWALK_FILE)

# %% Process codebook for clean code names
# Define patterns to standardize code names (spaces, punctuation, etc. become underscores)
patterns = [r"\s+", r"-", r",+", r"_+", r"/+", r"\\", r"'", r"\(", r"\)", r"&", r"\.", r":", r";"]
regex_pattern = "|".join(patterns)

# Create clean, standardized code column names from code paths (the
# non-category hierarchy path, e.g. 'Student Subgroups\At-Risk', so child
# codes keep their parent-prefixed column names)
codebook_df["code_column"] = (
    "code_"
    + codebook_df.code_path.str.replace(regex_pattern, "_", regex=True)
    .str.replace("_+", "_", regex=True)
    .str.strip("_")
    .str.lower()
    + "_applied"
)

print("Examples of code name cleaning:")
for _, row in codebook_df.head(6).iterrows():
    print(f"  {row.code_path} -> {row.code_column}")

# %% Build document-level code indicators from the long applied-codes file
# Prepare media names by removing .pdf extension
applied_df["media_name"] = applied_df["media_title"].str.replace(".pdf", "")
applied_df = applied_df.merge(
    codebook_df[["code_id", "code_column"]], on="code_id", how="left"
)
assert applied_df.code_column.notna().all(), "applied code missing from codebook export"

# One row per document, one column per code, 1 if any excerpt in the document has it
code_df = (
    applied_df.assign(applied=1)
    .pivot_table(index="media_name", columns="code_column", values="applied", aggfunc="max")
    .reset_index()
)

# Codes never applied still need columns (crosswalk validation demands completeness)
for code_column in codebook_df.code_column:
    if code_column not in code_df.columns:
        code_df[code_column] = 0

# %% Merge metadata with code data
meta_data_df["media_name"] = meta_data_df["media_title"].str.replace(".pdf", "")

long_df = meta_data_df.merge(
    code_df,
    on="media_name",
    indicator="_merge_qual",
    how="outer",
)

# %% Filter to complete qualitative coding sample
# Keep only districts that completed qualitative coding and are included in analysis
long_df = long_df[long_df.complete_qual == 1]
long_df = long_df[long_df.include_qual == 1]

print(f"After filtering, {long_df.leaid.nunique()} districts with qualitative coding data")

# %% Aggregate code columns at the district level
codes = [col for col in long_df.columns if "code_" in col and "applied" in col]
print(f"Found {len(codes)} code columns to process")

# Aggregate codes at district level using max (if any document has code=1, district gets 1)
df = long_df[["leaid"] + codes].groupby("leaid").max()
print(f"Aggregated data for {len(df)} districts")

# %% Merge with metadata and clean final dataset
df_final = meta_data_df.merge(
    df, left_on="leaid", right_index=True, how="left", indicator="_merge"
)

print(f"Final merge: {(df_final._merge == 'both').sum()} districts with codes, {(df_final._merge == 'left_only').sum()} without codes")

# Convert to binary (0/1) and fill districts without any codes
applied_cols = [col for col in df_final.columns if "applied" in col]
df_final[applied_cols] = df_final[applied_cols].replace({True: 1, False: 0})
df_final[applied_cols] = df_final[applied_cols].fillna(0).astype(int)
print(f"Converted {len(applied_cols)} applied columns to binary format")

# %%
# Address problem with parent and community codes
# The Dedoose-era corrections (archived CSV) are folded into the live columns
# by taking the max: the corrections captured recoding done outside Dedoose;
# new recoding now happens directly in ContentCoder, so as ZZ excerpts get
# reassigned in the app these columns absorb them automatically.

PARENT_CODE_FILE = start.DATA_DIR + "clean/plans_codes_previous_parent_and_community.csv"
KEEP_COLUMNS = ["leaid", "code_family_and_community_community_connection_and_buy_in_applied", "code_family_and_community_parent_communication_and_involvement_applied"]

correct_parent_codes = pd.read_csv(PARENT_CODE_FILE)
correct_parent_codes = correct_parent_codes[KEEP_COLUMNS]

df_final = df_final.merge(correct_parent_codes, on="leaid", how="left")

df_final["code_community_connection_and_buy_in_applied"] = np.where(
    df_final["code_family_and_community_community_connection_and_buy_in_applied"].fillna(0) == 1,
    1,
    df_final["code_community_connection_and_buy_in_applied"],
)
df_final["code_parent_communication_and_involvement_applied"] = np.where(
    df_final["code_family_and_community_parent_communication_and_involvement_applied"].fillna(0) == 1,
    1,
    df_final["code_parent_communication_and_involvement_applied"],
)
df_final = df_final.drop(columns=KEEP_COLUMNS[1:])

# The ZZ archive codes (ZZ DELETE / ZZ MERGE) were reviewed, reassigned to
# real codes in ContentCoder (2026-07-13, archived in the app's code history),
# and deleted from the codebook, so no zz columns exist anymore.
CODES_TO_REMOVE = ["code_other_unknown_applied"]

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
    "media_name",         # Used only for merging
]


df_final = df_final.drop(columns=columns_to_drop, errors="ignore")
# %% Validate code columns against the crosswalk
# Every applied code column must have a crosswalk row and vice versa; failing
# loudly here catches renames/additions in the codebook the day they appear
code_columns = [col for col in df_final.columns if "code_" in col and "applied" in col]

duplicated_columns = df_final.columns[df_final.columns.duplicated()].tolist()
assert not duplicated_columns, f"Duplicate columns in final dataset: {duplicated_columns}"

columns_missing_from_crosswalk = sorted(set(code_columns) - set(crosswalk_df.code_column))
crosswalk_rows_missing_from_data = sorted(set(crosswalk_df.code_column) - set(code_columns))
assert not columns_missing_from_crosswalk, (
    f"Code columns with no crosswalk row (new or renamed code in ContentCoder? "
    f"add to {start.CROSSWALK_FILE}): {columns_missing_from_crosswalk}"
)
assert not crosswalk_rows_missing_from_data, (
    f"Crosswalk rows with no matching code column (code removed or renamed "
    f"in ContentCoder?): {crosswalk_rows_missing_from_data}"
)
print(f"Crosswalk validation passed: {len(code_columns)} code columns all matched")

# %% Add code titles for reference
# Titles come from the crosswalk so they survive renames in the codebook
crosswalk_titles = crosswalk_df.set_index("code_column")["dedoose_title"]
for code_col in code_columns:
    df_final[code_col + "_title"] = crosswalk_titles[code_col]
print(f"Added titles for {len(code_columns)} code columns")

# %% Create top-level code columns from the ContentCoder codebook hierarchy
# A district gets a top-level code if any member code applied. Membership is
# the category grouping in the app's Codebook tab (editable, archived), so
# rearranging the hierarchy there changes these columns on the next export.
top_level_codebook = codebook_df[codebook_df.top_level_code.notna() & (codebook_df.top_level_code != "")]

for top_level_code in top_level_codebook.top_level_code.unique():
    member_columns = top_level_codebook[
        top_level_codebook.top_level_code == top_level_code
    ].code_column.tolist()
    member_columns = [col for col in member_columns if col in df_final.columns]

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
