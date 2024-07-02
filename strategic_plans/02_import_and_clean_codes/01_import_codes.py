# %%
import pandas as pd
import re
from strategic_plans.library import start
import numpy as np

# %%
meta_data_df = pd.read_csv(start.MAIN_DIR + "data/clean/plans_meta_data_full.csv")
# %%
FILENAME = "DedooseChartExcerpts_2024_3_1_1532.xlsx"
code_df = pd.read_excel(start.MAIN_DIR + "data/raw/Dedoose Exports/" + FILENAME)

# %%
codebook_df = pd.read_excel(
    start.MAIN_DIR + "data/raw/DedooseCodesExport_2023_11_10_1356.xlsx"
)

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


# %%


long_df = meta_data_df.merge(
    code_df, left_on="dedoose_name", right_on="Media Title", indicator=True
)
long_df = long_df[long_df.plan_complete == 1]

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

df.to_csv(start.MAIN_DIR + "data/clean/plans_codes.csv")
# %%
top_priority_df = df.replace({1: 0, 2: 0, 3: 1})
top_priority_df[[col for col in top_priority_df if "code_" in col]].sum().sort_values(
    ascending=False
)
# %%
