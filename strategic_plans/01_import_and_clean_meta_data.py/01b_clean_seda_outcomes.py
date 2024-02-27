# %%
import pandas as pd
import random

from strategic_plans.library import start

NATIONAL_DIR = (
    start.HOME_DIR + "Library/CloudStorage/Dropbox/Active/Research/national_data/data/"
)

RAW_SEDA = NATIONAL_DIR + "raw_from_SEDA/"
RAW_CCD = NATIONAL_DIR + "raw_from_CCD/"

CLEAN_DIR = start.MAIN_DIR + "data/clean/"
codebook = pd.read_excel(start.MAIN_DIR + "data/seda_codebook.xlsx")
codebook = codebook[~codebook.seda4_1_outcomes.isnull()]
rename_dict = dict(zip(codebook["seda4_1_outcomes"], codebook["new_name"]))
# %%
seda = pd.read_csv(RAW_SEDA + "seda_geodist_long_cs_4.1.csv")
seda = seda.rename(columns=rename_dict)
seda = seda[list(rename_dict.values())]
seda.sample()


# %%
outcomes = [col for col in seda.columns if "mean" in col]

# %% Average across grades
seda_subject_year = (
    seda[
        [
            "district_id",
            "district_name",
            "year",
            "test_subject",
        ]
        + outcomes
    ]
    .groupby(["district_id", "district_name", "test_subject", "year"])
    .mean()
).reset_index()

# %%

df_reading = seda_subject_year[seda_subject_year.test_subject == "rla"]
rla_columns = [col.replace("_subject", "_rla") for col in outcomes]
df_reading[rla_columns] = df_reading[outcomes]
df_reading = df_reading.drop(outcomes, axis=1)
df_reading = df_reading[["district_id", "year"] + rla_columns]
df_reading.sample()

df_math = seda_subject_year[seda_subject_year.test_subject == "mth"]
math_columns = [col.replace("_subject", "_math") for col in outcomes]
df_math[math_columns] = df_math[outcomes]
df_math = df_math.drop(outcomes, axis=1)
df_math = df_math[["district_id", "year"] + math_columns]
df_math.sample()


# %%

df = df_math.merge(
    df_reading,
    left_on=["district_id", "year"],
    right_on=["district_id", "year"],
    how="left",
)


df["test_math_wbgap_mean"] = df.test_math_white_mean - df.test_math_black_mean
df["test_rla_wbgap_mean"] = df.test_rla_white_mean - df.test_rla_black_mean

df = df[df.year == 2018]
df = df.rename(columns={"district_id": "leaid"})
# %%

df.to_csv(start.DATA_DIR + "clean/2018_seda_outcomes.csv", index=False)

# %% Wide

# years = [2018, 2017, 2016, 2015, 2014, 2013, 2012, 2011, 2010, 2009]
# for year in years:
#     temp_df = df[df.year == year]
#     temp_df = temp_df.set_index("district_id")
#     temp_df = temp_df.add_suffix("_" + str(year))
#     if year == 2018:
#         wide_df = temp_df
#     if year != 2018:
#         wide_df = wide_df.merge(temp_df, left_index=True, right_index=True, how="outer")

# # %%
# # Create math df

# # %%

# wide_df.to_csv(CLEAN_DIR + "prepandemic_outcomes_wide.csv")

# # %%
