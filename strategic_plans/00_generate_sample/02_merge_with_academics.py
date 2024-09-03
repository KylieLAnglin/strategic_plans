# %%
import pandas as pd
import re
from strategic_plans.library import start
import numpy as np
from openpyxl import load_workbook

# %%

covars = pd.read_csv(start.DATA_DIR + "clean/seda_ccd_covariates_2018.csv")
academics = pd.read_csv(start.DATA_DIR + "clean/2018_seda_outcomes.csv")
academics = academics[academics.test_math_all_mean.notnull()]


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

# %%
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
    # "sedaleaname",
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

df[columns_to_keep].to_csv(start.MAIN_DIR + "data/clean/seda_ccd_full.csv", index=False)
# %%
