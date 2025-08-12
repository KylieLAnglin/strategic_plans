# %%
import re

import pandas as pd
import numpy as np
from strategic_plans.library import start


# %%

df = pd.read_csv(start.MAIN_DIR + "data/clean/plans_codes.csv")
codebook_df = pd.read_excel(start.DATA_DIR + "raw/Dedoose Exports/DedooseCodesExport_2025_8_2_721.xlsx")

codebook_df = codebook_df.rename(columns={"Id": "code_id", "Parent Id": "parent_id", "Title": "code_title", "Description": "code_description"})
codebook_df["parent_id"] = np.where(codebook_df["parent_id"].isnull(), codebook_df.code_id, codebook_df["parent_id"])

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

# Debug: Check what title columns exist
title_cols = [col for col in df.columns if col.endswith("_title")]
print(f"Found {len(title_cols)} title columns")

# Add code titles from the existing title columns in the dataset
subgroup_count['code_title'] = None
missing_titles = []

for subgroup in subgroup_count.index:
    title_col = subgroup + '_title'
    if title_col in df.columns:
        # Get the first non-null title value for this code
        title_value = df[title_col].dropna().iloc[0] if not df[title_col].dropna().empty else None
        subgroup_count.loc[subgroup, 'code_title'] = title_value
    else:
        # For hierarchical codes, try to find the child code title
        # Extract different possible suffixes to match against
        subgroup_parts = subgroup.replace("code_", "").replace("_applied", "").split("_")
        
        found = False
        # Try progressively shorter suffixes from the end
        for i in range(len(subgroup_parts)):
            suffix = "_".join(subgroup_parts[i:])
            potential_title_col = f"code_{suffix}_applied_title"
            
            if potential_title_col in df.columns:
                title_value = df[potential_title_col].dropna().iloc[0] if not df[potential_title_col].dropna().empty else None
                subgroup_count.loc[subgroup, 'code_title'] = title_value
                found = True
                break
        
        if not found:
            missing_titles.append(subgroup)

print(f"Missing titles for {len(missing_titles)} subgroups:")
for missing in missing_titles[:10]:  # Show first 10
    print(f"  {missing}")

# For subgroups with null titles, try to get titles from the codebook as fallback
# Create the same clean code mapping as in 02_import_codes.py
patterns = ["\s+", "-", ",+", "_+", "/+", r"\\", "'", r"\(", r"\)", "&", r"\.", ":", ";"]
regex_pattern = "|".join(patterns)

codebook_df["clean_code_title"] = codebook_df["code_title"].str.replace(regex_pattern, "_", regex=True)
codebook_df["clean_code_title"] = codebook_df["clean_code_title"].str.replace("_+", "_", regex=True)
codebook_df["clean_code_title"] = codebook_df["clean_code_title"].str.strip("_")
codebook_df["clean_code_title"] = codebook_df["clean_code_title"].str.lower()

# Add code_description column
subgroup_count['code_description'] = None

# Fill in missing titles and descriptions from codebook
for subgroup in subgroup_count.index:
    if pd.isnull(subgroup_count.loc[subgroup, 'code_title']) or subgroup_count.loc[subgroup, 'code_title'] == '':
        # Extract the core code name (remove code_ prefix and _applied suffix)
        clean_subgroup = subgroup.replace("code_", "").replace("_applied", "")
        
        # For hierarchical codes, try matching different parts
        subgroup_parts = clean_subgroup.split("_")
        
        # Try matching progressively shorter suffixes
        for i in range(len(subgroup_parts)):
            suffix = "_".join(subgroup_parts[i:])
            match = codebook_df[codebook_df['clean_code_title'] == suffix]
            
            if not match.empty:
                subgroup_count.loc[subgroup, 'code_title'] = match.iloc[0]['code_title']
                subgroup_count.loc[subgroup, 'code_description'] = match.iloc[0]['code_description']
                print(f"Found title from codebook for {subgroup}: {match.iloc[0]['code_title']}")
                break
    else:
        # Even if title exists, try to get description
        clean_subgroup = subgroup.replace("code_", "").replace("_applied", "")
        subgroup_parts = clean_subgroup.split("_")
        
        for i in range(len(subgroup_parts)):
            suffix = "_".join(subgroup_parts[i:])
            match = codebook_df[codebook_df['clean_code_title'] == suffix]
            
            if not match.empty:
                subgroup_count.loc[subgroup, 'code_description'] = match.iloc[0]['code_description']
                break

# Final check
null_titles = subgroup_count[subgroup_count['code_title'].isnull()].index.tolist()
print(f"\nStill missing titles: {len(null_titles)}")
for missing in null_titles[:5]:
    print(f"  {missing}")

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
        elif "parent_communication_and_involvement" in orig_col:
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
subgroup_count[["code_title", "code_description", "count_plans", "proportion", "all_districts_rank"]].to_excel(start.MAIN_DIR + "results/subgroup_counts.xlsx")
print(f"\nExported subgroup counts to: {start.MAIN_DIR}results/subgroup_counts.xlsx")
print(f"Dataset shape: {subgroup_count.shape[0]} subgroups × {subgroup_count.shape[1]} columns")

# %%