# %%
import pandas as pd
import numpy as np
from strategic_plans.library import start


# %%

df = pd.read_csv(start.MAIN_DIR + "data/clean/plans_codes.csv")
# meta_data = pd.read_csv(start.MAIN_DIR + "data/clean/plans_meta_data_full.csv")
# df = df.merge(meta_data, on="leaid")
codebook_df = pd.read_excel(start.DATA_DIR + "raw/Dedoose Exports/DedooseCodesExport_2025_7_15_1538.xlsx")

codebook_df = codebook_df.rename(columns={"Id": "code_id", "Parent Id": "parent_id", "Title": "code_title", "Description": "code_description"})
codebook_df["parent_id"] = np.where(codebook_df["parent_id"].isnull(), codebook_df.code_id, codebook_df["parent_id"])

# %%
codes = [col for col in df.columns if "applied" in col]

# %%
goal_count = pd.DataFrame(df[codes].sum()).reset_index()
goal_count = goal_count.rename(columns={"index": "goal", 0: "count_plans"})
goal_count = goal_count.sort_values(by="count_plans", ascending=False)
goal_count = goal_count.set_index("goal")

number_plans = df.leaid.nunique()
goal_count["proportion"] = goal_count.count_plans / number_plans
goal_count["all_districts_rank"] = goal_count.count_plans.rank(
    ascending=False, method="min"
)

# Create a mapping from goal names to code definitions
goal_to_code_mapping = {}
for goal in goal_count.index:
    clean_goal = goal.replace("code_", "").replace("_applied", "")
    for _, row in codebook_df.iterrows():
        clean_title = row['code_title'].lower().replace(" ", "_").replace("-", "_").replace(",", "").replace("/", "_").replace("&", "and")
        if clean_goal == clean_title:
            goal_to_code_mapping[goal] = row['code_description']
            break

# Add code definitions to the goal_count dataframe
goal_count['goal_definition'] = goal_count.index.map(goal_to_code_mapping)

goal_count.to_excel(start.MAIN_DIR + "results/goal_count.xlsx")
# %%

# %%
