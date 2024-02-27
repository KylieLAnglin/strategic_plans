# %%
import pandas as pd
import re
from strategic_plans.library import start
import numpy as np

# %%
df = pd.read_excel(
    start.MAIN_DIR + "plan_pdf_organization_Dec.'23.xlsx", sheet_name="Jan. Update"
)
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
df.head()

# %%
strata_df = pd.read_csv(
    start.DATA_DIR + "clean/stratified_sample.csv",
)
strata_df
# %%
# df = df[df.plan_complete == 1]
df = df.merge(strata_df, left_on="leaid", right_on="leaid", how="left", indicator=True)
# %%
df._merge.value_counts()
# %%
df = df.sort_values(by=["locale", "plan_assigned", "random_number"], ascending=False)
df

# %%
df = df[df.plan_assigned != 5]
# %%
df["plan_assigned"] = np.where(df.plan_assigned == 1, 1, 0)

# %%
df["priority"] = df.groupby("locale").cumcount() < 10
df["priority"] = df["priority"].astype(int)
# %%
df["need_to_code"] = np.where((df.priority == 1) & (df.plan_assigned == 0), 1, 0)
df = df[
    [
        "leaid",
        "random_number",
        "lea_name",
        "dedoose_name",
        "need_to_code",
        "plan_complete",
        "coder1_assignment",
        "priority",
    ]
]

df = df.sort_values(
    by=["need_to_code", "plan_complete", "coder1_assignment", "random_number"],
    ascending=False,
)
df.to_excel(start.MAIN_DIR + "priority_plans.xlsx")

# %%
df.need_to_code.value_counts()
# %%
