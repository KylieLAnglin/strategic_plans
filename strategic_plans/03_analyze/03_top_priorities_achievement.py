# %%
import pandas as pd
import numpy as np
from strategic_plans.library import start


# %%

df = pd.read_csv(start.MAIN_DIR + "data/clean/plans_codes.csv")
meta_data = pd.read_csv(start.MAIN_DIR + "data/clean/plans_meta_data_full.csv")
df = df.merge(meta_data, on="leaid")
df["high_achieving_rla"] = np.where(df.test_rla_all_mean >= 0.20, 1, 0)
df["low_achieving_rla"] = np.where(df.test_rla_all_mean < 0.20, 1, 0)

df["high_achieving_math"] = np.where(df.test_math_all_mean >= 0.20, 1, 0)
df["low_achieving_math"] = np.where(df.test_math_all_mean < 0.20, 1, 0)

df["high_achieving"] = np.where(
    (df.high_achieving_rla == 1) | (df.high_achieving_math == 1), 1, 0
)
df["low_achieving"] = np.where(
    (df.low_achieving_rla == 1) | (df.low_achieving_math == 1), 1, 0
)

goal_count = pd.read_excel(start.MAIN_DIR + "results/goal_count.xlsx", index_col="goal")
# %%
codes = [col for col in df.columns if "applied" in col]

# %%

# %%
for district_group in ["high_achieving", "low_achieving"]:
    temp_df = df[df[district_group] > 0]
    temp_goal_count = pd.DataFrame(temp_df[codes].sum()).reset_index()
    temp_goal_count = temp_goal_count.rename(
        columns={"index": "goal", 0: "count_plans"}
    )
    temp_goal_count = temp_goal_count.set_index("goal")
    temp_goal_count = temp_goal_count.sort_values(by="count_plans", ascending=False)
    temp_goal_count[district_group + "_proportion"] = temp_goal_count.count_plans / len(
        temp_df
    )
    temp_goal_count[district_group + "_districts_rank"] = (
        temp_goal_count.count_plans.rank(ascending=False, method="min")
    )
    temp_goal_count = temp_goal_count.rename(
        columns={"count_plans": district_group + "count_plans"}
    )
    goal_count = goal_count.merge(temp_goal_count, left_index=True, right_index=True)

goal_count
# %%
goal_count[[col for col in goal_count if "rank" in col]]
# %%
for district_group in ["high_achieving", "low_achieving"]:
    goal_count[district_group + "_change_rank"] = (
        goal_count.all_districts_rank - goal_count[district_group + "_districts_rank"]
    )
    goal_count[district_group + "_abs_change_rank"] = abs(
        goal_count[district_group + "_change_rank"]
    )

    goal_count[district_group + "_change_proportion"] = (
        goal_count.proportion - goal_count[district_group + "_proportion"]
    )
    goal_count[district_group + "_abs_change_proportion"] = abs(
        goal_count[district_group + "_change_proportion"]
    )

goal_count[[col for col in goal_count if "rank" in col]]


# %%
def sort_by_group(district_group, goal_count_df):
    new_df = goal_count_df.sort_values(
        by=district_group + "_abs_change_proportion", ascending=False
    )
    new_df = new_df[
        [
            district_group + "_change_proportion",
            "proportion",
            district_group + "_proportion",
            "all_districts_rank",
            district_group + "_districts_rank",
        ]
    ]
    return new_df


high_df = sort_by_group("high_achieving", goal_count)
low_df = sort_by_group("low_achieving", goal_count)


with pd.ExcelWriter(
    start.MAIN_DIR + "results/goal_proportions_achievement.xlsx"
) as writer:
    high_df.to_excel(writer, sheet_name="high_achieving")
    low_df.to_excel(writer, sheet_name="low_achieving")

# %%
# %%
