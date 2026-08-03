# %%
import pandas as pd

from strategic_plans.library import start

# ------------------ SETUP ------------------

META_DATA_PATH = start.MAIN_DIR + "data/clean/plans_meta_data_full.csv"
APPLIED_CODES_PATH = start.LATEST_APPLIED_CODES

CODERS = ["mikayla.clemens", "JuliaOas", "kylielanglin"]
SEARCH = "HICKMAN"

# %%
# ------------------ LOAD METADATA ------------------

meta_data_df = pd.read_csv(META_DATA_PATH)
meta_data_df = meta_data_df[meta_data_df.include_qual == 1]

# %%
# ------------------ LOAD APPLIED CODES ------------------

code_df = pd.read_csv(APPLIED_CODES_PATH)
code_df["media_title"].nunique()

# %%
document_coder_df = code_df[["media_title", "date_coded", "excerpt_creator"]]
document_coder_df = document_coder_df.rename(columns={"excerpt_creator": "coder"})
document_coder_df.sample()

document_coder_df["coder"] = pd.Categorical(
    document_coder_df.coder, categories=CODERS, ordered=True
)
document_coder_df = document_coder_df.sort_values(by=["media_title", "coder"])

document_coder_df = document_coder_df.drop_duplicates()
document_coder_df = document_coder_df[document_coder_df.coder.isin(CODERS)]

# %%
documents_df = document_coder_df[["media_title"]].drop_duplicates()
documents_df["lea"] = documents_df.media_title.str.replace(".pdf", "")

# %%
# ------------------ MERGE AND REPORT MISMATCHES ------------------

df = meta_data_df.merge(
    documents_df,
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

document_coder_df[["media_title"]][document_coder_df.media_title.str.contains(SEARCH, case=False)]

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
