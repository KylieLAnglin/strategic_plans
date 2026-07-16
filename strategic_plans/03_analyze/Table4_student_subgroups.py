# %%
import pandas as pd
from strategic_plans.library import start


# %%

df = pd.read_csv(start.MAIN_DIR + "data/clean/plans_codes.csv")

# The ContentCoder codebook export is the codebook of record: its code_column
# and levelN_column values are exactly the column names in plans_codes.csv, so
# titles and descriptions map directly (no Dedoose-era fuzzy matching needed)
codebook_df = pd.read_csv(start.LATEST_CODEBOOK)

# %%
# Filter to student_subgroups codes and special cases (exclude title columns)
codes = [col for col in df.columns if "applied" in col and not col.endswith("_title")]
# Keep codes with "student_subgroups" in the name
subgroup_codes = [col for col in codes if "student_subgroups" in col]
# Also include "different level learners" as it's conceptually a student subgroup
special_subgroup_codes = ["code_academic_achievement_and_proficiency_different_level_learners_applied"]
subgroup_codes.extend([col for col in special_subgroup_codes if col in codes])

print(f"Found {len(subgroup_codes)} student subgroups codes:")
for code in subgroup_codes:
    print(f"  {code}")

# Ensure all code columns are numeric before summing
for col in subgroup_codes:
    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

# %%
subgroup_count = pd.DataFrame(df[subgroup_codes].sum()).reset_index()
subgroup_count = subgroup_count.rename(columns={"index": "subgroup", 0: "count_plans"})

# Ensure count_plans is numeric before sorting
subgroup_count["count_plans"] = pd.to_numeric(subgroup_count["count_plans"], errors='coerce')

subgroup_count = subgroup_count.sort_values(by="count_plans", ascending=False)
subgroup_count = subgroup_count.set_index("subgroup")

number_plans = df.leaid.nunique()
subgroup_count["proportion"] = subgroup_count.count_plans / number_plans
subgroup_count["all_districts_rank"] = subgroup_count.count_plans.rank(
    ascending=False, method="min"
)

# %%
# Address problem with parent and community codes (same as in 02_import_codes.py)

PARENT_CODE_FILE = start.DATA_DIR + "clean/plans_codes_previous_parent_and_community.csv"
correct_parent_codes = pd.read_csv(PARENT_CODE_FILE)

KEEP_COLUMNS = ["leaid", "code_family_and_community_community_connection_and_buy_in_applied", "code_family_and_community_parent_communication_and_involvement_applied"]

# Check if any of the parent/community codes are in our subgroup analysis
parent_community_subgroup_codes = [col for col in subgroup_codes if any(keep_col.replace("leaid", "").strip(", ") in col for keep_col in KEEP_COLUMNS[1:])]
if parent_community_subgroup_codes:
    print(f"Found parent/community codes in subgroup analysis: {parent_community_subgroup_codes}")
    
    # Apply the same corrections as in 02_import_codes.py
    df_with_corrections = df.merge(correct_parent_codes[KEEP_COLUMNS], on="leaid", how="left")
    
    # Update any affected subgroup codes
    for orig_col in parent_community_subgroup_codes:
        if "community_connection_and_buy_in" in orig_col:
            correct_col = "code_family_and_community_community_connection_and_buy_in_applied"
            if correct_col in df_with_corrections.columns:
                df[orig_col] = df_with_corrections[correct_col].fillna(0)
        elif "family_communication_and_involvement" in orig_col:
            correct_col = "code_family_and_community_parent_communication_and_involvement_applied"
            if correct_col in df_with_corrections.columns:
                df[orig_col] = df_with_corrections[correct_col].fillna(0)
    
    # Recalculate subgroup counts with corrected data
    subgroup_count = pd.DataFrame(df[subgroup_codes].sum()).reset_index()
    subgroup_count = subgroup_count.rename(columns={"index": "subgroup", 0: "count_plans"})
    subgroup_count["count_plans"] = pd.to_numeric(subgroup_count["count_plans"], errors='coerce')
    subgroup_count = subgroup_count.sort_values(by="count_plans", ascending=False)
    subgroup_count = subgroup_count.set_index("subgroup")
    
    number_plans = df.leaid.nunique()
    subgroup_count["proportion"] = subgroup_count.count_plans / number_plans
    subgroup_count["all_districts_rank"] = subgroup_count.count_plans.rank(ascending=False, method="min")
    
    print("Recalculated subgroup counts with parent/community code corrections")

# %%
# Map titles and descriptions from the codebook export. A subgroup column is
# either a per-code column (code_column) or a node's aggregate column (the
# levelN_column at its own depth), both named by the export itself.
title_by_column = {}
description_by_column = {}
for _, codebook_row in codebook_df.iterrows():
    own_level_column = codebook_row[f"level{int(codebook_row.level)}_column"]
    for column_name in (codebook_row.code_column, own_level_column):
        if isinstance(column_name, str) and column_name:
            title_by_column[column_name] = codebook_row.code_title
            description_by_column[column_name] = codebook_row.description

subgroup_count["code_title"] = [title_by_column.get(subgroup) for subgroup in subgroup_count.index]
subgroup_count["code_description"] = [description_by_column.get(subgroup) for subgroup in subgroup_count.index]

missing_titles = [subgroup for subgroup in subgroup_count.index if subgroup not in title_by_column]
assert not missing_titles, (
    f"Subgroup columns missing from the codebook export (stale export? "
    f"re-export from the app and update library/start.py): {missing_titles}"
)

# %%
subgroup_count[["code_title", "code_description", "count_plans", "proportion", "all_districts_rank"]].to_excel(start.MAIN_DIR + "results/subgroup_counts.xlsx")
print(f"\nExported subgroup counts to: {start.MAIN_DIR}results/subgroup_counts.xlsx")
print(f"Dataset shape: {subgroup_count.shape[0]} subgroups × {subgroup_count.shape[1]} columns")

# %%