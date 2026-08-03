# %%
import pandas as pd

from strategic_plans.library import start

# ------------------ SETUP ------------------

COVARIATES_PATH = start.DATA_DIR + "clean/seda_ccd_covariates_2018.csv"
OUTCOMES_PATH = start.DATA_DIR + "clean/2018_seda_outcomes.csv"

EXPORT_MERGED_PATH = start.MAIN_DIR + "data/clean/seda_ccd_full.csv"

# %%
# ------------------ LOAD DATA ------------------

covars = pd.read_csv(COVARIATES_PATH)
academics = pd.read_csv(OUTCOMES_PATH)
academics = academics[academics.test_math_all_mean.notnull()]

# %%
# ------------------ MERGE COVARIATES AND ACADEMICS ------------------

df = covars.merge(
    academics[
        [
            "leaid",
            "test_rla_all_mean",
            "test_math_all_mean",
        ]
    ],
    on="leaid",
    how="left",
    indicator="_merge_academics",
)

# %%
# ------------------ SELECT COLUMNS AND EXPORT ------------------

columns_to_keep = [
    "state",
    "leaid",
    "random_number",
    "lea_name",
    "city",
    "locale",
    "urbanicity",
    "census_division",
    "district_status",
    "district_type",
    "district_no_grades",
    "operational_schools",
    "state_fips",
    "perasn",
    "perblk",
    "perhsp",
    "perfrl",
    "perell",
    "lninc50all",
    "_merge_academics",
    "test_rla_all_mean",
    "test_math_all_mean",
]

df[columns_to_keep].to_csv(EXPORT_MERGED_PATH, index=False)

print(f"Saved: {EXPORT_MERGED_PATH}")

# %%
