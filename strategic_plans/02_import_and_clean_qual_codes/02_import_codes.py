# %%
"""
  - Purpose: Main code processing and hierarchical code creation
  - Key operations:
    - Imports both excerpts and codes export files from Dedoose
    - Creates codebook dictionary from code structure
    - Processes and cleans code column names (removes spaces, special
  characters)
    - Aggregates codes at district level using groupby().max()
    - Implements hierarchical coding: Makes parent codes True when child
  codes are True
    - Converts boolean codes to binary (0/1) format
    - Outputs: plans_codes.csv (final coded dataset)
"""
import pandas as pd
import re
from strategic_plans.library import start
import numpy as np

# %% Load metadata
# Read document metadata that links districts to Dedoose documents
meta_data_df = pd.read_csv(start.MAIN_DIR + "data/clean/dedoose_doc_df.csv")

# %% Load Dedoose exports
# Import the latest Dedoose chart excerpts (contains actual coded data)
# FILENAME = "DedooseChartExcerpts_2025_7_21_1137.xlsx"
# FILENAME = "DedooseChartExcerpts_2025_8_2_713.xlsx"
FILENAME = "DedooseChartExcerpts_2025_8_6_853.xlsx"
code_df = pd.read_excel(start.MAIN_DIR + "data/raw/Dedoose Exports/" + FILENAME)
print(f"Number of unique media titles in code data: {code_df['Media Title'].nunique()}")

# Import the codebook (contains code definitions and hierarchy)
# FILENAME = "DedooseCodesExport_2025_7_21_1132.xlsx"
FILENAME = "DedooseCodesExport_2025_8_2_721.xlsx"
print(f"Number of unique codes in codebook: {len(pd.read_excel(start.MAIN_DIR + 'data/raw/Dedoose Exports/' + FILENAME))}")

codebook_df = pd.read_excel(start.MAIN_DIR + "data/raw/Dedoose Exports/" + FILENAME)

# %% Process codebook for clean code names
# Define patterns to standardize code names (spaces, punctuation, etc. become underscores)
# Include apostrophes, parentheses, and other special characters that might appear in code titles
patterns = [r"\s+", r"-", r",+", r"_+", r"/+", r"\\", r"'", r"\(", r"\)", r"&", r"\.", r":", r";"]
regex_pattern = "|".join(patterns)

# Create clean, standardized code names from titles
codebook_df["code"] = codebook_df.Title.str.replace(regex_pattern, "_", regex=True)
# Remove multiple consecutive underscores and leading/trailing underscores
codebook_df["code"] = codebook_df["code"].str.replace("_+", "_", regex=True)
codebook_df["code"] = codebook_df["code"].str.strip("_")
codebook_df["code"] = codebook_df.code.str.lower()
codebook_df = codebook_df.set_index("Id")

# Debug: Print some examples of code cleaning
print("Examples of code name cleaning:")
for i, (idx, row) in enumerate(codebook_df.head(10).iterrows()):
    print(f"  {row.get('Title', 'N/A')} -> {row['code']}")
    if i >= 5:  # Limit output
        break
# %% Prepare code data
# Prepare media names by removing .pdf extension
code_df["media_name"] = code_df["Media Title"].str.replace(".pdf", "")

# Extract code columns and prepare for merge
# Keep only media name and actual code columns (those starting with 'Code:')
code_df = code_df[["media_name"] + [col for col in code_df.columns if "Code:" in col]]

# %% Merge metadata with code data
# Standardize names for matching (replace hyphens with underscores)
meta_data_df["dedoose_name"] = meta_data_df["revised_name"].str.replace("-", "_")

# Merge metadata with coded data
long_df = meta_data_df.merge(
    code_df,
    left_on="dedoose_name",
    right_on="media_name",
    indicator="_merge_qual",
    how="outer",
)

# %% Filter to complete qualitative coding sample
# Keep only districts that completed qualitative coding and are included in analysis
long_df = long_df[long_df.complete_qual == 1]
long_df = long_df[long_df.include_qual == 1]


# %% Clean column names
# Standardize column names: remove 'Code: ' prefix and convert to lowercase
long_df.columns = [col.replace("Code: ", "code_").lower() for col in long_df.columns]

# Apply regex pattern to clean all column names consistently (same as codebook cleaning)
compiled_pattern = re.compile(regex_pattern)
long_df.columns = [
    compiled_pattern.sub("_", col) for col in long_df.columns
]

# Remove multiple consecutive underscores and leading/trailing underscores from column names
long_df.columns = [
    re.sub("_+", "_", col).strip("_") for col in long_df.columns
]

print("Column name cleaning complete.")
print(f"Sample cleaned column names: {[col for col in long_df.columns if 'code_' in col][:5]}")


# %% Identify and aggregate code columns
# Extract all code columns that indicate whether a code was applied
codes = [col for col in long_df.columns if "code_" in col and "applied" in col]
print(f"Found {len(codes)} code columns to process")

# Aggregate codes at district level using max (if any excerpt has code=1, district gets 1)
df = long_df[["leaid"] + codes].groupby("leaid").max()
print(f"Aggregated data for {len(df)} districts")


# %% Merge with metadata and clean final dataset
# Merge aggregated codes back with metadata
df_final = meta_data_df.merge(
    df, left_on="leaid", right_index=True, how="left", indicator="_merge"
)

print(f"Final merge: {(df_final._merge == 'both').sum()} districts with codes, {(df_final._merge == 'left_only').sum()} without codes")

# Convert boolean values to binary (0/1) for applied columns
applied_cols = [col for col in df_final.columns if "applied" in col]

# Replace TRUE/FALSE with 1/0
df_final[applied_cols] = df_final[applied_cols].replace({True: 1, False: 0})

# Fill any remaining NaN values with 0 (districts without any codes)
df_final[applied_cols] = df_final[applied_cols].fillna(0)
print(f"Converted {len(applied_cols)} applied columns to binary format")

# %%
# Address problem with parent and community codes

PARENT_CODE_FILE = start.DATA_DIR + "clean/plans_codes_previous_parent_and_community.csv"
correct_parent_codes = pd.read_csv(PARENT_CODE_FILE)


KEEP_COLUMNS = ["leaid", "code_family_and_community_community_connection_and_buy_in_applied", "code_family_and_community_parent_communication_and_involvement_applied"]
# Merge correct parent codes back into final dataset
df_final = df_final.merge(correct_parent_codes[KEEP_COLUMNS], on="leaid", how="left")
df_final = df_final.rename(
    columns={
        "code_family_and_community_community_connection_and_buy_in_applied": "code_community_connection_and_buy_in_applied",
        "code_family_and_community_parent_communication_and_involvement_applied": "code_parent_communication_and_involvement_applied",
    }
)


df_final["code_community_connection_and_buy_in_applied"] = np.where(df_final["code_zz_merge_community_economic_development_applied"] == 1, 1, df_final["code_community_connection_and_buy_in_applied"])
CODES_TO_REMOVE = ["code_zz_delete_family_and_community_applied", "code_zz_delete_new_community_connection_and_buy_in_applied", "code_parent_communication_and_involvement_applied", "code_zz_merge_community_economic_development_applied", "code_other_unknown_applied", "code_old_community_connection_and_buy_in_applied"]

df_final = df_final.drop(columns=CODES_TO_REMOVE, errors="ignore")

# %% Clean up final dataset
# Remove columns that are no longer needed for analysis
columns_to_drop = [
    "pdf_name",           # Redundant filename info
    "revised_name",       # Used only for merging
    "original_document_name",
    "district_x",         # Merge conflict
    "filepath",           
    "plan_downloaded",    
    "include_ml",
    "complete_qual", 
    "include_qual",
    "document_csv_created",
    "pdf_downloaded",
    "district_y",         # Merge conflict
    "text",               # Full text not needed
    "filename",
    "contains_alphanumeric",
    "failed_parse",
    "_merge_meta",        
    "media_title",
]


df_final = df_final.drop(columns=columns_to_drop, errors="ignore")
# %%
# Add code titles for reference
# Add human-readable titles for each code column to aid interpretation
print("Adding code titles for reference...")
code_columns = [col for col in df_final.columns if "code_" in col]

for code_col in code_columns:
    # Extract the clean code name (remove 'code_' prefix and '_applied' suffix)
    code_name = code_col.replace("code_", "").replace("_applied", "")
    
    # Find matching code in codebook
    match = codebook_df[codebook_df["code"] == code_name]
    
    if not match.empty:
        title = match["Title"].values[0]
        df_final[code_col + "_title"] = title
    else:
        print(f"Warning: No title found for code: {code_name}")
        df_final[code_col + "_title"] = ""

print(f"Added titles for {len(code_columns)} code columns")

# Save final dataset
output_path = start.MAIN_DIR + "data/clean/plans_codes.csv"
df_final.to_csv(output_path, index=False)
print(f"Final dataset saved to: {output_path}")
print(f"Dataset shape: {df_final.shape[0]} districts × {df_final.shape[1]} columns")


# %%

# %%
