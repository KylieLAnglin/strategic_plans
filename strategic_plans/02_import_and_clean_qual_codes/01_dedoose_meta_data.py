# %%
import pandas as pd
import re
from strategic_plans.library import start
import numpy as np

# %%
meta_data_df = pd.read_csv(start.MAIN_DIR + "data/clean/plans_meta_data_full.csv")
meta_data_df = meta_data_df[meta_data_df.include_qual == 1]
# %%
# Excerpts → Select all → Export, named DedooseChartExport
FILENAME = "DedooseChartExcerpts_2024_11_12_822.xlsx"
code_df = pd.read_excel(start.MAIN_DIR + "data/raw/Dedoose Exports/" + FILENAME)
code_df["Media Title"].nunique()
code_df = code_df.rename(
    columns={
        "Media Title": "media_title",
        "Excerpt Date": "date_coded",
        "Excerpt Creator": "coder",
    }
)
coders = ["mikayla.clemens", "JuliaOas", "kylielanglin"]
code_df = code_df[code_df.coder.isin(coders)]
code_df["lea"] = code_df.media_title.str.replace(".pdf", "")

# %%
doc_df = code_df[["media_title", "date_coded", "coder", "lea"]].drop_duplicates()
doc_df = doc_df.drop_duplicates(subset="lea")

# %%

dedoose_doc_df = meta_data_df.merge(
    doc_df,
    left_on="pdf_name",
    right_on="lea",
    how="outer",
    indicator="_merge_qual",
)

# %%
dedoose_doc_df._merge_qual.value_counts()

# %%
dedoose_doc_df = dedoose_doc_df[dedoose_doc_df._merge_qual == "both"]
dedoose_doc_df = dedoose_doc_df.drop(
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
    ]
)

dedoose_doc_df.to_csv(start.MAIN_DIR + "data/clean/dedoose_doc_df.csv", index=False)
