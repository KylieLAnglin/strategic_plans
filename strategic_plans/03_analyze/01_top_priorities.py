# %%
import pandas as pd
from strategic_plans.library import start


# %%

df = pd.read_csv(start.MAIN_DIR + "data/clean/plans_codes.csv")

# %%
codes = [col for col in df.columns if "applied" in col]

# %%

goal_count = pd.DataFrame(df[codes].sum()).reset_index()
goal_count = goal_count.rename(columns={"index": "goal", 0: "count"})
goal_count = goal_count.sort_values(by="count", ascending=False)
goal_count.to_excel(start.MAIN_DIR + "results/goal_count.xlsx", index=False)
# %%
