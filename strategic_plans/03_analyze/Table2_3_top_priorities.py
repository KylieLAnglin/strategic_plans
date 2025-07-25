# %%
import re

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
# Filter to only numeric applied columns (exclude any title columns and specific codes)
codes = [col for col in df.columns if "applied" in col and not col.endswith("_title")]
# Remove specific codes from analysis
codes_to_exclude = [
    "code_teachers_applied", 
    "code_other_unknown_applied",
    "code_academic_achievement_and_proficiency_different_level_learners_applied"  # Exclude from general goals, include in subgroups
]
# Also exclude any codes with "student_subgroups" in the name
codes_to_exclude.extend([col for col in codes if "student_subgroups" in col])
codes = [col for col in codes if col not in codes_to_exclude]

print(f"Excluded codes: {codes_to_exclude}")
print(f"Analyzing {len(codes)} code columns")

# Ensure all code columns are numeric before summing
for col in codes:
    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

# %%
goal_count = pd.DataFrame(df[codes].sum()).reset_index()
goal_count = goal_count.rename(columns={"index": "goal", 0: "count_plans"})

# Ensure count_plans is numeric before sorting
goal_count["count_plans"] = pd.to_numeric(goal_count["count_plans"], errors='coerce')

goal_count = goal_count.sort_values(by="count_plans", ascending=False)
goal_count = goal_count.set_index("goal")

number_plans = df.leaid.nunique()
goal_count["proportion"] = goal_count.count_plans / number_plans
goal_count["all_districts_rank"] = goal_count.count_plans.rank(
    ascending=False, method="min"
)

# Debug: Check what title columns exist
title_cols = [col for col in df.columns if col.endswith("_title")]
print(f"Found {len(title_cols)} title columns")
print("Sample title columns:", title_cols[:10])

# Add code titles from the existing title columns in the dataset
goal_count['code_title'] = None
missing_titles = []

for goal in goal_count.index:
    title_col = goal + '_title'
    if title_col in df.columns:
        # Get the first non-null title value for this code
        title_value = df[title_col].dropna().iloc[0] if not df[title_col].dropna().empty else None
        goal_count.loc[goal, 'code_title'] = title_value
    else:
        # For hierarchical codes, try to find the child code title
        # Extract different possible suffixes to match against
        goal_parts = goal.replace("code_", "").replace("_applied", "").split("_")
        
        found = False
        # Try progressively shorter suffixes from the end
        for i in range(len(goal_parts)):
            suffix = "_".join(goal_parts[i:])
            potential_title_col = f"code_{suffix}_applied_title"
            
            if potential_title_col in df.columns:
                title_value = df[potential_title_col].dropna().iloc[0] if not df[potential_title_col].dropna().empty else None
                goal_count.loc[goal, 'code_title'] = title_value
                found = True
                break
        
        if not found:
            missing_titles.append(goal)

print(f"Missing titles for {len(missing_titles)} goals:")
for missing in missing_titles[:10]:  # Show first 10
    print(f"  {missing}")

# For goals with null titles, try to get titles from the codebook as fallback
# Create the same clean code mapping as in 02_import_codes.py
patterns = ["\s+", "-", ",+", "_+", "/+", r"\\", "'", r"\(", r"\)", "&", r"\.", ":", ";"]
regex_pattern = "|".join(patterns)

codebook_df["clean_code_title"] = codebook_df["code_title"].str.replace(regex_pattern, "_", regex=True)
codebook_df["clean_code_title"] = codebook_df["clean_code_title"].str.replace("_+", "_", regex=True)
codebook_df["clean_code_title"] = codebook_df["clean_code_title"].str.strip("_")
codebook_df["clean_code_title"] = codebook_df["clean_code_title"].str.lower()

# Add code_description column
goal_count['code_description'] = None

# Fill in missing titles and descriptions from codebook
for goal in goal_count.index:
    if pd.isnull(goal_count.loc[goal, 'code_title']) or goal_count.loc[goal, 'code_title'] == '':
        # Extract the core code name (remove code_ prefix and _applied suffix)
        clean_goal = goal.replace("code_", "").replace("_applied", "")
        
        # For hierarchical codes, try matching different parts
        goal_parts = clean_goal.split("_")
        
        # Try matching progressively shorter suffixes
        for i in range(len(goal_parts)):
            suffix = "_".join(goal_parts[i:])
            match = codebook_df[codebook_df['clean_code_title'] == suffix]
            
            if not match.empty:
                goal_count.loc[goal, 'code_title'] = match.iloc[0]['code_title']
                goal_count.loc[goal, 'code_description'] = match.iloc[0]['code_description']
                print(f"Found title from codebook for {goal}: {match.iloc[0]['code_title']}")
                break
    else:
        # Even if title exists, try to get description
        clean_goal = goal.replace("code_", "").replace("_applied", "")
        goal_parts = clean_goal.split("_")
        
        for i in range(len(goal_parts)):
            suffix = "_".join(goal_parts[i:])
            match = codebook_df[codebook_df['clean_code_title'] == suffix]
            
            if not match.empty:
                goal_count.loc[goal, 'code_description'] = match.iloc[0]['code_description']
                break

# Final check
null_titles = goal_count[goal_count['code_title'].isnull()].index.tolist()
print(f"\nStill missing titles: {len(null_titles)}")
for missing in null_titles[:5]:
    print(f"  {missing}")

goal_count[["code_title",  "count_plans", "proportion", "all_districts_rank", "code_description",]].to_excel(start.MAIN_DIR + "results/goal_count.xlsx")
# %%

# %%
# list 5 documents with goal of interest
goal_of_interest = "code_soft_skills_sel_social_emotional_learning_applied"
goal_docs = df[df[goal_of_interest] > 0].sample(5)
print(f"Documents with goal '{goal_of_interest}':")
for index, row in goal_docs.iterrows():
    print(f"  LEAID: {row['leaid']}, Title: {row.get('lea_name', 'No title')}, Year: {row.get('state', 'No state')}")
# %%
