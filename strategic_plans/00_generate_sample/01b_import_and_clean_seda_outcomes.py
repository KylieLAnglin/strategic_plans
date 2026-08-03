# %%
import pandas as pd

from strategic_plans.library import start

# ------------------ SETUP ------------------

RAW_SEDA_DIR = start.NATIONAL_DIR + "raw_from_SEDA/"
RAW_CCD_DIR = start.NATIONAL_DIR + "raw_from_CCD/"
CLEAN_DIR = start.MAIN_DIR + "data/clean/"

CODEBOOK_PATH = start.MAIN_DIR + "data/seda_codebook.xlsx"
EXPORT_OUTCOMES_PATH = start.DATA_DIR + "clean/2018_seda_outcomes.csv"

ANALYSIS_YEAR = 2018

# %%
# ------------------ LOAD DATA ------------------

codebook = pd.read_excel(CODEBOOK_PATH)
codebook = codebook[~codebook.seda4_1_outcomes.isnull()]
rename_dict = dict(zip(codebook["seda4_1_outcomes"], codebook["new_name"]))

# %%
seda = pd.read_csv(RAW_SEDA_DIR + "seda_geodist_long_cs_4.1.csv")
seda = seda.rename(columns=rename_dict)
seda = seda[list(rename_dict.values())]
seda.sample()

# %%
outcomes = [col for col in seda.columns if "mean" in col]

# %%
# ------------------ AVERAGE ACROSS GRADES ------------------

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
# ------------------ SPLIT READING AND MATH ------------------

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
# ------------------ MERGE SUBJECTS AND GENERATE GAPS ------------------

df = df_math.merge(
    df_reading,
    left_on=["district_id", "year"],
    right_on=["district_id", "year"],
    how="left",
)

df["test_math_wbgap_mean"] = df.test_math_white_mean - df.test_math_black_mean
df["test_rla_wbgap_mean"] = df.test_rla_white_mean - df.test_rla_black_mean

df = df[df.year == ANALYSIS_YEAR]
df = df.rename(columns={"district_id": "leaid"})

# %%
# ------------------ EXPORT ------------------

df.to_csv(EXPORT_OUTCOMES_PATH, index=False)

print(f"Saved: {EXPORT_OUTCOMES_PATH}")

# %%
