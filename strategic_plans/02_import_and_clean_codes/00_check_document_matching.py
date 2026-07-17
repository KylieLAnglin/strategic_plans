# %%
"""
  - Purpose: Diagnostic for document-to-metadata matching
  - Source: ContentCoder applied-codes export (pinned in library/start.py)
  - Key operations:
    - Imports plan metadata and filters to the qualitative coding sample
  (include_qual == 1)
    - Reads the ContentCoder applied_codes export (one row per excerpt x code)
    - Filters to project coders
    - Merges coded media titles against sample metadata and reports
  left_only / right_only mismatches (in-sample-but-not-coded and
  coded-but-not-in-sample)
    - The SEARCH cell at the bottom looks up a district by name on both sides
"""
import pandas as pd

from strategic_plans.library import start

# %%
# ------------------ SETUP ------------------
META_DATA_PATH = start.MAIN_DIR + "data/clean/plans_meta_data_full.csv"
CODERS = ["mikayla.clemens", "JuliaOas", "kylielanglin"]
SEARCH = "HICKMAN"

# %%
# ------------------ LOAD METADATA ------------------
meta_data_df = pd.read_csv(META_DATA_PATH)
meta_data_df = meta_data_df[meta_data_df.include_qual == 1]

# %%
# ------------------ LOAD APPLIED CODES ------------------
code_df = pd.read_csv(start.LATEST_APPLIED_CODES)
code_df["media_title"].nunique()

# %%
code_df = code_df[["media_title", "date_coded", "excerpt_creator"]]
code_df = code_df.rename(columns={"excerpt_creator": "coder"})
code_df.sample()

# %%
code_df = code_df.drop_duplicates()
code_df = code_df[code_df.coder.isin(CODERS)]

# %%
code_df = code_df[["media_title"]].drop_duplicates()
code_df["lea"] = code_df.media_title.str.replace(".pdf", "")

# %%
# ------------------ MERGE AND REPORT MISMATCHES ------------------
df = meta_data_df.merge(
    code_df,
    left_on="pdf_name",
    right_on="lea",
    how="outer",
    indicator="_merge_qual",
)

df._merge_qual.value_counts()

# %%
# In sample but never coded (should be empty)
df[df._merge_qual == "left_only"]

# %%
# Coded but not in the sample (pilot/practice/out-of-sample codings)
df[["media_title"]][df._merge_qual == "right_only"]

# %%
# ------------------ SEARCH A DISTRICT BY NAME ------------------
code_df[["media_title"]][code_df.media_title.str.contains(SEARCH, case=False)]

# %%
meta_data_df[
    [
        "lea_name",
        "revised_name",
        "original_document_name",
        "district_x",
        "district_y",
        "filename",
    ]
][meta_data_df.lea_name.str.contains(SEARCH, case=False)]
