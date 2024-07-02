# %%
import pandas as pd
import re
from strategic_plans.library import start
import numpy as np

# %%

df = pd.read_excel(start.MAIN_DIR + "plan_pdf_organization_May'24.xlsx")
# %%
columns = {
    "leadid": "leaid",
    # "random_number": "random_number",
    # "LEA name in *stratified sample* document": "lea_name",
    "Title (in Dedoose!) this list is the format that is downloaded from Dedoose in exporting media": "dedoose_name",
    "For subsample feb.21.2024 Assinged to be coded at least once (0= unassigned, 1= assigned, 5 = orange, not available) ": "plan_assigned",
    "Plan is READY for extraction, done coding (1)   ": "plan_complete",
    "SINGLE CODER's codes to be used for analysis": "use_single_coder",
    "BOTH CODER's codes to be used for analysis ": "use_double_coder",
    "Coder #1": "coder1",
    "Coder #2, and all others ": "coder2",
    "Practice Assigning random coder#1": "coder1_assignment",
}
df = df.rename(columns=columns)
df = df[list(columns.values())]
df = df[df.plan_assigned != 5]  # delete rows without identified plans
df.head()

# %%
strata_df = pd.read_csv(
    start.DATA_DIR + "clean/stratified_sample.csv",
)
strata_df
# %%
# df = df[df.plan_complete == 1]
df = strata_df.merge(df, left_on="leaid", right_on="leaid", how="outer", indicator=True)
df._merge.value_counts()  # two rows without data

# %%
df = df[df._merge != "right_only"]
df["plan_identified"] = np.where(df._merge == "both", 1, 0)

df.plan_identified.value_counts(normalize=True)

# %%
priority_df = pd.read_excel(start.MAIN_DIR + "priority_plans.xlsx")
df = df.merge(
    priority_df[["random_number", "priority"]],
    left_on="random_number",
    right_on="random_number",
    how="outer",
    indicator="_merge_priority",
)
df._merge_priority.value_counts()
df = df[df._merge_priority != "right_only"]
# %%

# %%

# %%
df["need_to_code"] = np.where((df.priority == 1) & (df.plan_assigned == 0), 1, 0)
df = df[
    [
        "leaid",
        "random_number",
        "lea_name",
        "plan_identified",
        "dedoose_name",
        "need_to_code",
        "plan_complete",
        "coder1_assignment",
        "priority",
    ]
]

df.to_csv(start.MAIN_DIR + "data/clean/plans_meta_data.csv")

# %%
df.need_to_code.value_counts()
# %%
