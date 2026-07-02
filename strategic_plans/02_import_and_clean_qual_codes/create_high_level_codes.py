# %%
"""
  - NOTE: One-time script, superseded by code_crosswalk.xlsx (in this folder).
    The worksheet this created was filled in by hand and folded into the
    crosswalk, which is now the codebook of record. To change top-level
    assignments, display names, or inclusion, edit code_crosswalk.xlsx directly
    and rerun 02_import_codes.py.
  - Purpose: Create a worksheet for assigning top-level codes to the analyzed codes
  - Key operations:
    - Loads plans_codes.csv and identifies the analyzed code columns
      (excludes title columns and student subgroup codes)
    - Pulls each code's title from the dataset and its description from the
      Dedoose codebook export
    - Outputs: high_level_codes.xlsx with an empty top_level_code column
      to be filled in by hand (aiming for roughly 5-10 top-level codes)
"""
import pandas as pd
from strategic_plans.library import start

# %% Load coded dataset and codebook
df = pd.read_csv(start.DATA_DIR + "clean/plans_codes.csv")

# Combine the two most recent codebook exports: some codes were renamed in
# Dedoose after 7/15, so no single export contains every analyzed code under
# the title used in plans_codes.csv
CODEBOOK_FILENAMES = [
    "DedooseCodesExport_2025_8_2_721.xlsx",
    "DedooseCodesExport_2025_7_15_1538.xlsx",
]
codebook_exports = []
for codebook_filename in CODEBOOK_FILENAMES:
    export_df = pd.read_excel(start.DATA_DIR + "raw/Dedoose Exports/" + codebook_filename)
    export_df = export_df.rename(
        columns={"Title": "code_title", "Description": "code_description"}
    )
    codebook_exports.append(export_df[["code_title", "code_description"]])
codebook_df = pd.concat(codebook_exports).drop_duplicates(
    subset="code_title", keep="first"
)

# Clean codebook titles the same way column names were cleaned in
# 02_import_codes.py so cleaned column names can be matched to the codebook
patterns = [r"\s+", r"-", r",+", r"_+", r"/+", r"\\", r"'", r"\(", r"\)", r"&", r"\.", r":", r";"]
regex_pattern = "|".join(patterns)
codebook_df["clean_code_title"] = codebook_df["code_title"].str.replace(regex_pattern, "_", regex=True)
codebook_df["clean_code_title"] = codebook_df["clean_code_title"].str.replace("_+", "_", regex=True)
codebook_df["clean_code_title"] = codebook_df["clean_code_title"].str.strip("_")
codebook_df["clean_code_title"] = codebook_df["clean_code_title"].str.lower()

# %% Identify analyzed code columns
# Same filtering as Table2_3_top_priorities.py: applied columns only,
# excluding title columns and student subgroup codes
code_columns = [
    col for col in df.columns if "applied" in col and not col.endswith("_title")
]
code_columns = [col for col in code_columns if "student_subgroups" not in col]

print(f"Found {len(code_columns)} code columns")

# %% Build worksheet with titles and descriptions
# Codes renamed in Dedoose after the last codebook export, mapped back to
# their title in the codebook exports above
RENAMED_CODE_TITLES = {
    "code_21st_century_skills_applied": "21st century/marketable skills",
    "code_college_and_career_preparation_applied": "College Acceptance and Success",
    "code_preserve_local_culture_and_language_applied": "Preserve local culture and history",
    "code_sel_social_and_emotional_learning_applied": "SEL (social emotional learning)",
}

worksheet_rows = []
for code_column in code_columns:
    # Prefer the display title stored in the dataset's title column
    title_column = code_column + "_title"
    if title_column in df.columns and not df[title_column].dropna().empty:
        code_title = df[title_column].dropna().iloc[0]
    else:
        code_title = ""

    # First try an exact title match in the codebook
    codebook_match = codebook_df[codebook_df["code_title"] == code_title]

    # Then try the manual mapping for renamed codes
    if codebook_match.empty and code_column in RENAMED_CODE_TITLES:
        codebook_match = codebook_df[
            codebook_df["code_title"] == RENAMED_CODE_TITLES[code_column]
        ]

    # Finally match on cleaned code names, trying progressively shorter
    # suffixes to handle hierarchical prefixes (same approach as
    # Table2_3_top_priorities.py); strip pandas duplicate-column suffixes
    if codebook_match.empty:
        clean_goal = code_column.replace("code_", "").replace("_applied", "")
        clean_goal = clean_goal.split(".")[0]
        goal_parts = clean_goal.split("_")
        for i in range(len(goal_parts)):
            suffix = "_".join(goal_parts[i:])
            codebook_match = codebook_df[codebook_df["clean_code_title"] == suffix]
            if not codebook_match.empty:
                break

    if not codebook_match.empty:
        code_description = codebook_match.iloc[0]["code_description"]
        if code_title == "":
            code_title = codebook_match.iloc[0]["code_title"]
    else:
        code_description = ""
        print(f"Warning: No codebook description found for: {code_column}")

    worksheet_rows.append(
        {
            "code_column": code_column,
            "code_title": code_title,
            "code_description": code_description,
        }
    )

high_level_codes_df = pd.DataFrame(worksheet_rows)
high_level_codes_df = high_level_codes_df.sort_values(by="code_title")

# Empty column to be filled in by hand with top-level codes
high_level_codes_df["top_level_code"] = ""

# %% Export
output_path = start.DATA_DIR + "clean/high_level_codes.xlsx"
high_level_codes_df.to_excel(output_path, index=False)
print(f"Worksheet saved to: {output_path}")
print(f"{len(high_level_codes_df)} codes ready for top-level assignment")

# %%
