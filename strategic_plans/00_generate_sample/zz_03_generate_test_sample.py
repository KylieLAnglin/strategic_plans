# %%
import pandas as pd

from strategic_plans.library import start

df = pd.read_csv(start.MAIN_DIR + "data/clean/seda_ccd_full.csv")

# %% Exclusions
df = df[df.district_status == "Open"]
df = df[df.district_type.str.contains("Regular public school district")]
df = df[df.district_no_grades == "No"]
df = df[df.operational_schools > 0]

# %%
df = df[df._merge_academics == "both"]

# %% Create strata
df = df.dropna(subset=["urbanicity", "census_division"])
df["strata_string"] = df.census_division + " " + df.urbanicity
df = df[df.strata_string != "nan"]

# %% Keep first ten within strata
df = df.sort_values(by=["strata_string", "random_number"])
grouped = df.groupby("strata_string")
df["strata_sample"] = grouped.cumcount() < 20
df = df[df.strata_sample == True]

# %% Clean and export
df = df[
    [
        "strata_string",
        "leaid",
        "state",
        "lea_name",
        "city",
        "locale",
        "urbanicity",
        "census_division",
        "random_number",
        "perblk",
        "test_rla_all_mean",
        "test_math_all_mean",
    ]
]

df = df.sort_values(by=["census_division", "urbanicity"])
df.to_csv(
    start.DATA_DIR + "clean/stratified_sample_new.csv",
    index=False,
)
# %%
