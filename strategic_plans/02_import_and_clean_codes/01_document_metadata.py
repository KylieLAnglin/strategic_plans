# %%
"""
  - Purpose: Prepares document-level metadata for qualitative coding analysis
  - Source: ContentCoder applied-codes export (pinned in library/start.py)
  - Key operations:
    - Imports plan metadata and filters to qualitative coding sample
  (include_qual == 1)
    - Reads the ContentCoder applied_codes export and takes each document's
  first coded excerpt (by project coders) for date_coded and coder
    - Creates document-level dataset by merging metadata with coding
  information
    - Outputs: contentcoder_doc_df.csv, links district info to media_title,
  date_coded, and coder
"""
import pandas as pd

from strategic_plans.library import start

# %%
# ------------------ SETUP ------------------
META_DATA_PATH = start.MAIN_DIR + "data/clean/plans_meta_data_full.csv"
OUTPUT_PATH = start.MAIN_DIR + "data/clean/contentcoder_doc_df.csv"
CODERS = ["mikayla.clemens", "JuliaOas", "kylielanglin"]

# %%
# ------------------ LOAD METADATA ------------------
meta_data_df = pd.read_csv(META_DATA_PATH)
meta_data_df = meta_data_df[meta_data_df.include_qual == 1]

# %%
# ------------------ LOAD APPLIED CODES ------------------
code_df = pd.read_csv(start.LATEST_APPLIED_CODES)

code_df = code_df.rename(columns={"excerpt_creator": "coder"})
code_df = code_df[code_df.coder.isin(CODERS)]
code_df["lea"] = code_df.media_title.str.replace(".pdf", "")

# Format the ISO date back to the M/D/YYYY style used in the metadata files
date_parts = pd.to_datetime(code_df.date_coded)
code_df["date_coded"] = (
    date_parts.dt.month.astype(str)
    + "/"
    + date_parts.dt.day.astype(str)
    + "/"
    + date_parts.dt.year.astype(str)
)

# %%
# ------------------ BUILD DOCUMENT-LEVEL DATASET ------------------
doc_df = code_df[["media_title", "date_coded", "coder", "lea"]].drop_duplicates()
doc_df = doc_df.drop_duplicates(subset="lea")

contentcoder_doc_df = meta_data_df.merge(
    doc_df,
    left_on="pdf_name",
    right_on="lea",
    how="outer",
    indicator="_merge_qual",
)

contentcoder_doc_df._merge_qual.value_counts()

contentcoder_doc_df = contentcoder_doc_df[contentcoder_doc_df._merge_qual == "both"]
contentcoder_doc_df = contentcoder_doc_df.drop(
    columns=[
        "lea",
        "_merge_qual",
        "Unnamed: 0",
        "need_to_qual",
        "uploaded_dedoose",
        "_merge",
        "note",
        "Unnamed: 21",
        "Unnamed: 22",
    ],
    errors="ignore",
)

# %%
# ------------------ SAVE ------------------
contentcoder_doc_df.to_csv(OUTPUT_PATH, index=False)
print(f"Saved: {OUTPUT_PATH}")
