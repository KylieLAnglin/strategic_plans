# %%
import pandas as pd

from strategic_plans.library import start

# ------------------ SETUP ------------------

MERGED_PATH = start.MAIN_DIR + "data/clean/seda_ccd_full.csv"
EXPORT_SAMPLE_PATH = start.DATA_DIR + "clean/stratified_sample.csv"

NUM_DISTRICTS_PER_STRATUM = 10

# %%
# ------------------ LOAD DATA ------------------

df = pd.read_csv(MERGED_PATH)

# %%
# ------------------ EXCLUSIONS ------------------

df = df[df.district_status == "Open"]
df = df[df.district_type.str.contains("Regular public school district")]
df = df[df.district_no_grades == "No"]
df = df[df.operational_schools > 0]

# %%
df = df[df._merge_academics == "both"]

# %%
# ------------------ CREATE STRATA ------------------

df = df.dropna(subset=["locale", "census_division"])
df["strata_string"] = df.census_division + " " + df.locale
df = df[df.strata_string != "nan"]

# %%
# ------------------ KEEP FIRST TEN WITHIN STRATA ------------------

df = df.sort_values(by=["strata_string", "random_number"])
grouped = df.groupby("strata_string")
df["strata_sample"] = grouped.cumcount() < NUM_DISTRICTS_PER_STRATUM
df = df[df.strata_sample == True]

# %%
# ------------------ CLEAN AND EXPORT ------------------

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
        "perblk",
        "test_rla_all_mean",
        "test_math_all_mean",
    ]
]

df = df.sort_values(by=["census_division", "locale"])
df.to_csv(EXPORT_SAMPLE_PATH, index=False)

print(f"Saved: {EXPORT_SAMPLE_PATH}")

# %%
