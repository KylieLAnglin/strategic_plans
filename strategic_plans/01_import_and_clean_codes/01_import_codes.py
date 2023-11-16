# %%
import pandas as pd
import re
from strategic_plans.library import start

# %%
code_df = pd.read_excel(start.MAIN_DIR + "data/raw/Dedoose Media_2023_11_10_1332.xls")
code_df["district"] = (
    code_df["Title"].str.rsplit("_", 1).str[0].str.replace(".pdf", "", regex=False)
)

codebook_df = pd.read_excel(
    start.MAIN_DIR + "data/raw/DedooseCodesExport_2023_11_10_1356.xlsx"
)
# List of patterns to be replaced with an underscore
patterns = ["\s+", "-", ",+", "_+", "/+", "_"]

# Joining the patterns into a single regex pattern
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
characteristic_df = pd.read_csv(start.DATA_DIR + "clean/seda_ccd_covariates_2018.csv")

df = characteristic_df.merge(
    code_df, left_on="lea_name", right_on="district", indicator=True
)

# %%
# %%
df.columns = [col.replace("Code: ", "code_").lower() for col in df.columns]

compiled_pattern = re.compile(regex_pattern)
df.columns = [
    compiled_pattern.sub("_", compiled_pattern.sub("_", col)) for col in df.columns
]
df.sample()
# %%
top_priority_df = df.replace({1: 0, 2: 0, 3: 1})
top_priority_df[[col for col in top_priority_df if "code_" in col]].sum().sort_values(
    ascending=False
)
# %%
