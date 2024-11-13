# %%
import pandas as pd
import re
from strategic_plans.library import start
import numpy as np

# %%
meta_data_df = pd.read_csv(start.MAIN_DIR + "data/clean/dedoose_doc_df.csv")

# %%
# Excerpts → Select all → Export, named DedooseChartExport
FILENAME = "DedooseChartExcerpts_2024_11_12_822.xlsx"
code_df = pd.read_excel(start.MAIN_DIR + "data/raw/Dedoose Exports/" + FILENAME)
code_df["Media Title"].nunique()
# %%
FILENAME = "DedooseCodesExport_2024_11_11_1434.xlsx"
codebook_df = pd.read_excel(start.MAIN_DIR + "data/raw/Dedoose Exports/" + FILENAME)

# %%
patterns = ["\s+", "-", ",+", "_+", "/+", "_", r"\\"]
regex_pattern = "|".join(patterns)

codebook_df["code"] = codebook_df.Title.str.replace(regex_pattern, "_", regex=True)
codebook_df["code"] = codebook_df.code.str.lower()
codebook_df = codebook_df.set_index("Id")
codebook_dict = {}
for num in codebook_df.index:
    code = codebook_df.loc[num]["code"]
    parent = codebook_df.loc[num]["Parent Id"]
    if parent > 0:
        codebook_dict[code] = {"id": num, "index": num, "parent_id": parent}
    else:
        codebook_dict[code] = {"id": num, "index": num, "parent_id": 0}

code_df["media_name"] = code_df["Media Title"].str.replace(".pdf", "")

# %%
code_df = code_df[["media_name"] + [col for col in code_df.columns if "Code:" in col]]

# %%
meta_data_df["dedoose_name"] = meta_data_df["revised_name"].str.replace("-", "_")
long_df = meta_data_df.merge(
    code_df,
    left_on="dedoose_name",
    right_on="media_name",
    indicator="_merge_qual",
    how="outer",
)
# %%
long_df = long_df[long_df.complete_qual == 1]
long_df = long_df[long_df.include_qual == 1]
# %%
# %%
long_df.columns = [col.replace("Code: ", "code_").lower() for col in long_df.columns]

compiled_pattern = re.compile(regex_pattern)
long_df.columns = [
    compiled_pattern.sub("_", compiled_pattern.sub("_", col)) for col in long_df.columns
]
long_df.sample()


# %%
codes = [col for col in long_df.columns if "code" in col]

df = long_df[["leaid"] + codes].groupby("leaid").max()

# %% Hierarchical codes
df["code_academic_achievement_and_proficiency_applied"] = np.where(
    df.code_academic_achievement_and_proficiency_ap_courses_and_testing_applied == True,
    True,
    df.code_academic_achievement_and_proficiency_applied,
)
df["code_academic_achievement_and_proficiency_applied"] = np.where(
    df.code_academic_achievement_and_proficiency_different_level_learners_applied
    == True,
    True,
    df.code_academic_achievement_and_proficiency_applied,
)

# df = df[[col for col in df.columns if "weight" not in col]]
df = df[[col for col in df.columns if "range" not in col]]

# %%
df_final = meta_data_df.merge(
    df, left_on="leaid", right_index=True, how="left", indicator="_merge"
)
# replace NaN with 0 in columns with "weight" in the name
df_final[[col for col in df_final if "weight" in col]] = df_final[
    [col for col in df_final if "weight" in col]
].fillna(0)

# Replace TRUE with 1 and FALSE with 0 in columns with "applied" in the name
df_final[[col for col in df_final if "applied" in col]] = df_final[
    [col for col in df_final if "applied" in col]
].replace({True: 1, False: 0})


df_final[[col for col in df_final if "applied" in col]] = df_final[
    [col for col in df_final if "applied" in col]
].fillna(0)
# %%
# df_final = df_final.replace({1: 0, 2: 0, 3: 1})
df_final = df_final.drop(
    columns=[
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
    ]
)


df_final.to_csv(start.MAIN_DIR + "data/clean/plans_codes.csv", index=False)
# %%

# %%
