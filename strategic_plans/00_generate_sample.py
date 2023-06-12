# %%
import pandas as pd

from library import start

# %%
df = pd.read_csv(start.NATIONAL_DATA + "seda_ccd_covariates_2018.csv")
# %%
# %% Exclusions
df = df[df.SY_STATUS_TEXT == "Open"]
df = df[df.LEA_TYPE_TEXT.str.contains("Regular public school district")]
df = df[df.NOGRADES == "No"]
df = df[df.OPERATIONAL_SCHOOLS > 0]
# %%

df = df.dropna(subset=["locale", "census_division"])
df["strata_string"] = df.census_division + " " + df.locale
df = df[df.strata_string != "nan"]
df = df.sort_values(by=["strata_string", "random_number"])
grouped = df.groupby("strata_string")
df["strata_sample"] = grouped.cumcount() < 5
df = df[df.strata_sample == True]

df = df[["state", "lea_name", "city", "locale", "census_division"]]

df.to_csv(
    start.DATA_DIR + "clean/stratified_sample.csv",
    index=False,
)
# %%
