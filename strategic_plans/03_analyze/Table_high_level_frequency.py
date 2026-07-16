# %%
"""
  - Purpose: Level-1 code counts and proportions across plans
  - Key operations:
    - Counts plans applying each level-1 code (level1_*_applied columns
      created in 02_import_codes.py from the ContentCoder codebook hierarchy)
    - Attaches level-1 code titles and member codes from the codebook
      export (pinned in library/start.py)
    - Outputs: results/high_level_frequency.xlsx
"""
import pandas as pd
from strategic_plans.library import start

# %% Load data and the codebook export
df = pd.read_csv(start.DATA_DIR + "clean/plans_codes.csv")
codebook_df = pd.read_csv(start.LATEST_CODEBOOK)

level1_codebook = codebook_df[codebook_df.level == 1]
member_codebook = codebook_df[(codebook_df.is_category == 0) & (codebook_df.level > 1)]

number_plans = df.leaid.nunique()
level1_columns = [col for col in df.columns if col.startswith("level1_") and col.endswith("_applied")]
print(f"{number_plans} plans, {len(level1_columns)} level-1 codes")

# %% Count plans applying each level-1 code
for level1_column in level1_columns:
    df[level1_column] = pd.to_numeric(df[level1_column], errors="coerce").fillna(0)

high_level_count = pd.DataFrame({"level1_column": level1_columns})
high_level_count["count_plans"] = high_level_count.level1_column.map(
    df[level1_columns].sum()
)
high_level_count["proportion"] = high_level_count.count_plans / number_plans
high_level_count["all_districts_rank"] = high_level_count.count_plans.rank(
    ascending=False, method="min"
)

# %% Attach level-1 code titles and member codes from the codebook export
high_level_count = high_level_count.merge(
    level1_codebook[["level1_column", "code_title"]].rename(
        columns={"code_title": "level1_code"}
    ),
    on="level1_column",
)

# Member codes are the applicable codes nested anywhere under the level-1
# node (the node's own applications count toward it but are not listed)
member_codes = member_codebook.groupby("level1_column").code_title.apply(
    lambda names: "; ".join(sorted(names))
)
high_level_count["member_codes"] = high_level_count.level1_column.map(member_codes).fillna("")
high_level_count["number_member_codes"] = (
    high_level_count.level1_column.map(member_codebook.level1_column.value_counts())
    .fillna(0)
    .astype(int)
)

high_level_count = high_level_count.sort_values(by="count_plans", ascending=False)

# %% Export
high_level_count[
    ["level1_code", "count_plans", "proportion", "all_districts_rank", "number_member_codes", "member_codes"]
].to_excel(start.RESULTS_DIR + "high_level_frequency.xlsx", index=False)
print(high_level_count[["level1_code", "count_plans", "proportion"]].to_string(index=False))

# %%
