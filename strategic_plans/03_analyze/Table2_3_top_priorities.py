# %%
"""
  - Purpose: Goal counts and proportions across plans (Tables 2-3)
  - Key operations:
    - Counts plans applying each goal code, using the crosswalk
      (02_import_and_clean_qual_codes/code_crosswalk.xlsx) for display names,
      descriptions, and top-level codes
    - Counts plans applying each top-level code (top_*_applied columns
      created in 02_import_codes.py)
    - Outputs: results/goal_count.xlsx, results/top_level_goal_count.xlsx
"""
import pandas as pd
from strategic_plans.library import start

# %% Load data and crosswalk
df = pd.read_csv(start.DATA_DIR + "clean/plans_codes.csv")
crosswalk_df = pd.read_excel(start.CROSSWALK_FILE)

goal_crosswalk = crosswalk_df[crosswalk_df.code_type == "goal"]
number_plans = df.leaid.nunique()
print(f"{number_plans} plans, {len(goal_crosswalk)} goal codes")

# %% Goal-level counts
goal_count = goal_crosswalk[
    ["code_column", "display_name", "top_level_code", "code_description"]
].copy()
goal_count = goal_count.rename(columns={"display_name": "code_title"})

for goal_column in goal_count.code_column:
    df[goal_column] = pd.to_numeric(df[goal_column], errors="coerce").fillna(0)

goal_count["count_plans"] = goal_count.code_column.map(df[goal_count.code_column].sum())
goal_count["proportion"] = goal_count.count_plans / number_plans
goal_count["all_districts_rank"] = goal_count.count_plans.rank(
    ascending=False, method="min"
)
goal_count = goal_count.sort_values(by="count_plans", ascending=False)
goal_count = goal_count.set_index("code_column")

goal_count[
    ["code_title", "count_plans", "proportion", "all_districts_rank", "top_level_code", "code_description"]
].to_excel(start.RESULTS_DIR + "goal_count.xlsx")
print(goal_count[["code_title", "count_plans", "proportion"]].head(15).to_string())

# %% Top-level code counts
top_level_columns = [col for col in df.columns if col.startswith("top_") and col.endswith("_applied")]

top_level_count = pd.DataFrame({"top_level_column": top_level_columns})
top_level_count["count_plans"] = top_level_count.top_level_column.map(
    df[top_level_columns].sum()
)
top_level_count["proportion"] = top_level_count.count_plans / number_plans

# Attach the top-level code names and member codes from the crosswalk
member_codes = goal_crosswalk.groupby("top_level_code").display_name.apply(
    lambda names: "; ".join(sorted(names))
)
number_member_codes = goal_crosswalk.top_level_code.value_counts()

patterns = [r"\s+", r"-", r",+", r"_+", r"/+", r"\\", r"'", r"\(", r"\)", r"&", r"\.", r":", r";", r"\+"]
regex_pattern = "|".join(patterns)
clean_top_level_names = (
    goal_crosswalk.top_level_code.drop_duplicates()
    .to_frame(name="top_level_code")
    .assign(
        top_level_column=lambda x: "top_"
        + x.top_level_code.str.replace(regex_pattern, "_", regex=True)
        .str.replace("_+", "_", regex=True)
        .str.strip("_")
        .str.lower()
        + "_applied"
    )
)

top_level_count = top_level_count.merge(clean_top_level_names, on="top_level_column")
top_level_count["member_codes"] = top_level_count.top_level_code.map(member_codes)
top_level_count["number_member_codes"] = top_level_count.top_level_code.map(number_member_codes)
top_level_count = top_level_count.sort_values(by="count_plans", ascending=False)

top_level_count[
    ["top_level_code", "count_plans", "proportion", "number_member_codes", "member_codes"]
].to_excel(start.RESULTS_DIR + "top_level_goal_count.xlsx", index=False)
print(top_level_count[["top_level_code", "count_plans", "proportion"]].to_string())

# %% List 5 example documents with a goal of interest
goal_of_interest = "code_providing_community_and_parent_resources_applied"
goal_docs = df[df[goal_of_interest] > 0].sample(5)
print(f"Documents with goal '{goal_of_interest}':")
for index, row in goal_docs.iterrows():
    print(f"  LEAID: {row['leaid']}, Title: {row.get('lea_name', 'No title')}, State: {row.get('state', 'No state')}")

# %%
