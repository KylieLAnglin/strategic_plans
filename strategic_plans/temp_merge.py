# %%

import pandas as pd
import os

# %%
df_sample = pd.read_excel(
    "/Users/kla21002/Library/CloudStorage/OneDrive-SharedLibraries-UniversityofConnecticut/strategic_plans - Documents/data/sample_inclusion.xlsx"
)
df_sample = df_sample[df_sample.leaid.notnull()]
df_sample_w_plans = df_sample[df_sample.plan_downloaded == 1]
# %%
directory = "/Users/kla21002/Library/CloudStorage/OneDrive-SharedLibraries-UniversityofConnecticut/strategic_plans - Documents/downloaded_pdfs"
files = [f for f in os.listdir(directory) if f.endswith(".pdf")]

# %%
df_plans = pd.DataFrame(files, columns=["file_name"])
df_plans["lea_name"] = df_plans.file_name.str.replace(".pdf", "")
# %%

df = df_sample.merge(df_plans, on="lea_name", how="outer", indicator="_merge_plans")
df = df_sample.merge(
    df_plans,
    left_on="revised_name",
    right_on="lea_name",
    how="outer",
    indicator="_merge_plans",
)
df._merge_plans.value_counts()
