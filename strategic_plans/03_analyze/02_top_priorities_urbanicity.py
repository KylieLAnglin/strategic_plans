# %%
import pandas as pd
from strategic_plans.library import start


# %%

df = pd.read_csv(start.MAIN_DIR + "data/clean/plans_codes.csv")
meta_data = pd.read_csv(start.MAIN_DIR + "data/clean/plans_meta_data_full.csv")
df = df.merge(meta_data, on="leaid")


goal_count = pd.read_excel(start.MAIN_DIR + "results/goal_count.xlsx", index_col="goal")
# %%
codes = [col for col in df.columns if "applied" in col]

# %%

# %%
for geo in ["urban", "suburb", "town", "rural"]:
    temp_df = df[df[geo] > 0]
    temp_goal_count = pd.DataFrame(temp_df[codes].sum()).reset_index()
    temp_goal_count = temp_goal_count.rename(
        columns={"index": "goal", 0: "count_plans"}
    )
    temp_goal_count = temp_goal_count.set_index("goal")
    temp_goal_count = temp_goal_count.sort_values(by="count_plans", ascending=False)
    temp_goal_count[geo + "_proportion"] = temp_goal_count.count_plans / len(temp_df)
    temp_goal_count[geo + "_districts_rank"] = temp_goal_count.count_plans.rank(
        ascending=False, method="min"
    )
    temp_goal_count = temp_goal_count.rename(
        columns={"count_plans": geo + "count_plans"}
    )
    goal_count = goal_count.merge(temp_goal_count, left_index=True, right_index=True)

goal_count
# %%
goal_count[[col for col in goal_count if "rank" in col]]
# %%
for geo in ["urban", "suburb", "town", "rural"]:
    goal_count[geo + "_change_rank"] = (
        goal_count.all_districts_rank - goal_count[geo + "_districts_rank"]
    )
    goal_count[geo + "_abs_change_rank"] = abs(goal_count[geo + "_change_rank"])

    goal_count[geo + "_change_proportion"] = (
        goal_count.proportion - goal_count[geo + "_proportion"]
    )
    goal_count[geo + "_abs_change_proportion"] = abs(
        goal_count[geo + "_change_proportion"]
    )

goal_count[[col for col in goal_count if "rank" in col]]


# %%
def sort_by_urbanicity(geo, goal_count_df):
    new_df = goal_count_df.sort_values(
        by=geo + "_abs_change_proportion", ascending=False
    )
    new_df = new_df[
        [
            geo + "_change_proportion",
            "proportion",
            geo + "_proportion",
            "all_districts_rank",
            geo + "_districts_rank",
        ]
    ]
    return new_df


urban_df = sort_by_urbanicity("urban", goal_count)
suburb_df = sort_by_urbanicity("suburb", goal_count)
town_df = sort_by_urbanicity("town", goal_count)
rural_df = sort_by_urbanicity("rural", goal_count)

with pd.ExcelWriter(
    start.MAIN_DIR + "results/goal_proportions_urbanicity.xlsx"
) as writer:
    urban_df.to_excel(writer, sheet_name="urban")
    suburb_df.to_excel(writer, sheet_name="suburb")
    town_df.to_excel(writer, sheet_name="town")
    rural_df.to_excel(writer, sheet_name="rural")
# %%
# %%
