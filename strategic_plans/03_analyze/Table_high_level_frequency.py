# %%
"""
  - Purpose: High-level (top-level) code counts and proportions across plans
  - Key operations:
    - Counts plans applying each top-level code (top_*_applied columns
      created in 02_import_codes.py from the crosswalk assignments)
    - Attaches member codes from the crosswalk
      (02_import_and_clean_qual_codes/code_crosswalk.xlsx)
    - Outputs: results/high_level_frequency.xlsx
"""
import pandas as pd
from strategic_plans.library import start

# %% Load data and crosswalk
df = pd.read_csv(start.DATA_DIR + "clean/plans_codes.csv")
crosswalk_df = pd.read_excel(start.CROSSWALK_FILE)

goal_crosswalk = crosswalk_df[crosswalk_df.code_type == "goal"]
number_plans = df.leaid.nunique()
top_level_columns = [col for col in df.columns if col.startswith("top_") and col.endswith("_applied")]
print(f"{number_plans} plans, {len(top_level_columns)} top-level codes")

# %% Count plans applying each top-level code
for top_level_column in top_level_columns:
    df[top_level_column] = pd.to_numeric(df[top_level_column], errors="coerce").fillna(0)

high_level_count = pd.DataFrame({"top_level_column": top_level_columns})
high_level_count["count_plans"] = high_level_count.top_level_column.map(
    df[top_level_columns].sum()
)
high_level_count["proportion"] = high_level_count.count_plans / number_plans
high_level_count["all_districts_rank"] = high_level_count.count_plans.rank(
    ascending=False, method="min"
)

# %% Attach top-level code names and member codes from the crosswalk
# Rebuild the top-level column names with the same cleaning used in
# 02_import_codes.py so the crosswalk names can be matched to the columns
patterns = [r"\s+", r"-", r",+", r"_+", r"/+", r"\\", r"'", r"\(", r"\)", r"&", r"\.", r":", r";", r"\+"]
regex_pattern = "|".join(patterns)
top_level_names = (
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
high_level_count = high_level_count.merge(top_level_names, on="top_level_column")

member_codes = goal_crosswalk.groupby("top_level_code").display_name.apply(
    lambda names: "; ".join(sorted(names))
)
high_level_count["member_codes"] = high_level_count.top_level_code.map(member_codes)
high_level_count["number_member_codes"] = high_level_count.top_level_code.map(
    goal_crosswalk.top_level_code.value_counts()
)

high_level_count = high_level_count.sort_values(by="count_plans", ascending=False)

# %% Export
high_level_count[
    ["top_level_code", "count_plans", "proportion", "all_districts_rank", "number_member_codes", "member_codes"]
].to_excel(start.RESULTS_DIR + "high_level_frequency.xlsx", index=False)
print(high_level_count[["top_level_code", "count_plans", "proportion"]].to_string(index=False))

# %%
