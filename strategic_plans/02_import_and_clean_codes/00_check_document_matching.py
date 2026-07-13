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
import re
from strategic_plans.library import start
import numpy as np

# %%
meta_data_df = pd.read_csv(start.MAIN_DIR + "data/clean/plans_meta_data_full.csv")
meta_data_df = meta_data_df[meta_data_df.include_qual == 1]

# %%
# ContentCoder export: one row per excerpt x applied code; pinned in start.py
code_df = pd.read_csv(start.LATEST_APPLIED_CODES)
code_df["media_title"].nunique()  # More media titles than sample: we coded some not in our sample

# %%
code_df = code_df[["media_title", "date_coded", "excerpt_creator"]]
code_df = code_df.rename(columns={"excerpt_creator": "coder"})
code_df.sample()

# %%
code_df = code_df.drop_duplicates()
# %%
coders = ["mikayla.clemens", "JuliaOas", "kylielanglin"]
code_df = code_df[code_df.coder.isin(coders)]

# %%
code_df = code_df[["media_title"]].drop_duplicates()
code_df["lea"] = code_df.media_title.str.replace(".pdf", "")
# %%
df = meta_data_df.merge(
    code_df,
    left_on="pdf_name",
    right_on="lea",
    how="outer",
    indicator="_merge_qual",
)

# %%
df._merge_qual.value_counts()

# %%
# In sample but never coded (should be empty)
df[df._merge_qual == "left_only"]
# %%
# Coded but not in the sample (pilot/practice/out-of-sample codings)
df[["media_title"]][df._merge_qual == "right_only"]
# %%
SEARCH = "HICKMAN"

code_df[
    [
        "media_title",
    ]
][code_df.media_title.str.contains(SEARCH, case=False)]


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
# %%
