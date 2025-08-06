# %%
# DELETE?
import pandas as pd
import re
from strategic_plans.library import start
import numpy as np

# %%
meta_data_df = pd.read_csv(start.MAIN_DIR + "data/clean/plans_meta_data_full.csv")
meta_data_df = meta_data_df[meta_data_df.include_qual == 1]
# %%
# Excerpts → Select all → Export, named DedooseChartExport
# FILENAME = "DedooseChartExcerpts_2024_11_12_822.xlsx"
# FILENAME = "DedooseChartExcerpts_2025_7_21_1137.xlsx"
# FILENAME = "DedooseChartExcerpts_2025_8_2_713.xlsx"
FILENAME = "DedooseChartExcerpts_2025_8_6_853.xlsx"
code_df = pd.read_excel(start.MAIN_DIR + "data/raw/Dedoose Exports/" + FILENAME)
code_df["Media Title"].nunique() # Why 222 media titles? Should be 104. (We coded some not in our sample)


# %%
code_df = code_df[["Media Title", "Excerpt Date", "Excerpt Creator"]]
code_df = code_df.rename(
    columns={
        "Media Title": "media_title",
        "Excerpt Date": "date_coded",
        "Excerpt Creator": "coder",
    }
)
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
df[df._merge_qual == "left_only"]
# %%
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
# %%
