# %%
"""
  - Purpose: Goal counts and proportions across plans (Tables 2-3)
  - Key operations:
    - Counts plans applying each goal code, using the ContentCoder codebook
      export (pinned in library/start.py) for display names, descriptions,
      and level-1 groupings
    - Counts use each goal's own level aggregate column, so codes nested
      under a goal roll up into it
    - Level-1 code counts live in Table_high_level_frequency.py
    - Outputs: results/goal_count.xlsx
"""
import pandas as pd
from strategic_plans.library import start

# %% Load data and the codebook export
df = pd.read_csv(start.DATA_DIR + "clean/plans_codes.csv")
codebook_df = pd.read_csv(start.LATEST_CODEBOOK)
applicable_codebook = codebook_df[codebook_df.is_category == 0]

# Goal codes are the applicable codes directly under a level-1 category,
# plus standalone root codes. Parent codes with their own code children
# (e.g. Student Subgroups) and the sub-codes nested under them are not goals.
parent_is_category = codebook_df.set_index("code_id")["is_category"]
goal_codebook = applicable_codebook[
    applicable_codebook.parent_id.map(parent_is_category).fillna(0).astype(bool)
    | (applicable_codebook.parent_id.isna() & (applicable_codebook.has_child_codes == 0))
].copy()

# Each goal is counted through its own level aggregate column (equal to the
# code's own column unless codes are nested under it)
goal_codebook["goal_column"] = goal_codebook.apply(
    lambda row: row[f"level{int(row.level)}_column"], axis=1
)

# Codes deliberately dropped from the dataset (e.g. Other/Unknown) have no
# column in plans_codes.csv and are excluded from the table
dropped_goals = goal_codebook[~goal_codebook.goal_column.isin(df.columns)]
for _, dropped_row in dropped_goals.iterrows():
    print(f"Skipping goal code with no data column: {dropped_row.code_title}")
goal_codebook = goal_codebook[goal_codebook.goal_column.isin(df.columns)]

number_plans = df.leaid.nunique()
print(f"{number_plans} plans, {len(goal_codebook)} goal codes")

# %% Goal-level counts
goal_count = goal_codebook[
    ["code_column", "goal_column", "code_title", "level1_title", "description"]
].copy()
goal_count = goal_count.rename(columns={"description": "code_description"})

# Show level-1 groupings by their code titles from the app's Codebook tab,
# blank for goals that sit at level 1 themselves
goal_count["level1_code"] = goal_count.level1_title.mask(goal_codebook.level == 1, "")

for goal_column in goal_count.goal_column:
    df[goal_column] = pd.to_numeric(df[goal_column], errors="coerce").fillna(0)

goal_count["count_plans"] = goal_count.goal_column.map(df[goal_count.goal_column].sum())
goal_count["proportion"] = goal_count.count_plans / number_plans
goal_count["all_districts_rank"] = goal_count.count_plans.rank(
    ascending=False, method="min"
)
goal_count = goal_count.sort_values(by="count_plans", ascending=False)
goal_count = goal_count.set_index("code_column")

goal_count[
    ["code_title", "count_plans", "proportion", "all_districts_rank", "level1_code", "code_description"]
].to_excel(start.RESULTS_DIR + "goal_count.xlsx")
print(goal_count[["code_title", "count_plans", "proportion"]].head(15).to_string())

# %% List 5 example documents with a goal of interest
goal_of_interest = "code_providing_community_and_parent_resources_applied"
goal_docs = df[df[goal_of_interest] > 0].sample(5)
print(f"Documents with goal '{goal_of_interest}':")
for index, row in goal_docs.iterrows():
    print(f"  LEAID: {row['leaid']}, Title: {row.get('lea_name', 'No title')}, State: {row.get('state', 'No state')}")

# %%
