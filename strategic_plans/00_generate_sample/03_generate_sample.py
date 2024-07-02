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
df = df.dropna(subset=["locale", "census_division"])
df["strata_string"] = df.census_division + " " + df.locale
df = df[df.strata_string != "nan"]

# %% Keep first five within strata
df = df.sort_values(by=["strata_string", "random_number"])
grouped = df.groupby("strata_string")
df["strata_sample"] = grouped.cumcount() < 10
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
        "census_division",
        "random_number",
    ]
]

df = df.sort_values(by=["census_division", "locale"])
df.to_csv(
    start.DATA_DIR + "clean/stratified_sample.csv",
    index=False,
)
# %%
