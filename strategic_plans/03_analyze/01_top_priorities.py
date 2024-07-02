# %%
import pandas as pd
from strategic_plans.library import start


# %%

df = pd.read_csv(start.MAIN_DIR + "data/clean/plans_codes.csv")
meta_data = pd.read_csv(start.MAIN_DIR + "data/clean/plans_meta_data_full.csv")
df = df.merge(meta_data, on="leaid")
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
goal_count.to_excel(start.MAIN_DIR + "results/goal_count.xlsx")
# %%

# %%
