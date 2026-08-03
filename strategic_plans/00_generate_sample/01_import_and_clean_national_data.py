# %%
import pandas as pd
import random
from strategic_plans.library import start

# ------------------ SETUP ------------------

RAW_SEDA_DIR = start.NATIONAL_DIR + "raw_from_SEDA/"
RAW_CCD_DIR = start.NATIONAL_DIR + "raw_from_CCD/"
CLEAN_DIR = start.NATIONAL_DIR + "clean/"

EXPORT_COVARIATES_PATH = start.DATA_DIR + "clean/seda_ccd_covariates_2018.csv"

RANDOM_NUMBER_MAX = 1000000
NUM_ROWS_TO_INSPECT = 10
ANALYSIS_YEAR = 2018

# %%
# ------------------ LOAD DATA ------------------

seda = pd.read_csv(RAW_SEDA_DIR + "seda_cov_geodist_poolyr_4.1.csv")
ccd = pd.read_csv(RAW_CCD_DIR + "nonfiscal_district_2122_directory.csv")
regions = pd.read_csv(start.NATIONAL_DIR + "us census bureau regions and divisions.csv")
states = pd.read_csv(start.NATIONAL_DIR + "states.csv")

# %%
# ------------------ CLEAN SEDA ------------------

seda["leaid"] = seda.sedalea.fillna(0)
seda["leaid"] = seda.leaid.astype(int)

seda = seda.rename(columns={"fips": "fips_seda"})
seda["fips_seda"] = seda.fips_seda.fillna(0)
seda["fips_seda"] = seda.fips_seda.astype(int)

seda["sedaleaname"] = seda.sedaleaname.fillna("")

# %%
# ------------------ CLEAN CCD ------------------

ccd["leaid"] = ccd.LEAID.fillna(0)
ccd["leaid"] = ccd.leaid.astype(int)

ccd["fips"] = ccd.FIPST.fillna(0)
ccd["fips"] = ccd.fips.astype(int)

# %%
# ------------------ MERGE SEDA AND CCD ------------------

df = ccd.merge(seda, left_on="leaid", right_on="leaid", how="outer", indicator="_merge")
df._merge.value_counts()

df[df._merge == "right_only"]["sedaleaname"].sample(NUM_ROWS_TO_INSPECT)
df[df._merge == "right_only"]["LEA_NAME"].sample(NUM_ROWS_TO_INSPECT)

# %%
df = df[df._merge == "both"].drop("_merge", axis=1)

# %%
# ------------------ CLEAN AND SELECT COLUMNS ------------------

df["zip_code"] = df.MZIP.astype(int)
df["year"] = df.year.astype(int)
df["locale"] = df[[col for col in df.columns if "locale_" in col]].idxmax(axis=1)
df["urbanicity"] = df["locale"].str.extract("_(.*?)_")

columns = {
    "LEA_NAME": "lea_name",
    "ST": "state",
    "MCITY": "city",
    "SY_STATUS_TEXT": "district_status",
    "LEA_TYPE_TEXT": "district_type",
    "NOGRADES": "district_no_grades",
    "OPERATIONAL_SCHOOLS": "operational_schools",
    "year": "year",
    "locale": "locale",
    "urbanicity": "urbanicity",
    "zip_code": "zip_code",
    "leaid": "leaid",
    "perasn": "perasn",
    "perblk": "perblk",
    "perhsp": "perhsp",
    "perfrl": "perfrl",
    "perell": "perell",
    "lninc50all": "lninc50all",
}

df = df.rename(columns=columns)

# %%
columns_to_drop = [col for col in df.columns if col not in columns.values()]
df.drop(columns=columns_to_drop, inplace=True)

# %%
# ------------------ MERGE REGIONS AND STATE NAMES ------------------

df = df.merge(regions, how="left", left_on="state", right_on="State Code")
df = df.rename(columns={"Region": "census_region", "Division": "census_division"})
df.drop(columns=["State", "State Code"], inplace=True)

# %%
states = states.rename(columns={"State": "state_name", "Abbreviation": "state_fips"})
df = df.merge(states, how="left", left_on="state", right_on="state_fips")

# %%
# ------------------ ADD RANDOM ASSIGNMENT ------------------

df["randomization_string"] = df.leaid.astype(str)

random_numbers = []
for randomization_string in df.randomization_string:
    seed = int.from_bytes(randomization_string.encode(), "little")
    random.seed(seed)
    random_numbers.append(random.randint(1, RANDOM_NUMBER_MAX))

df["random_number"] = random_numbers
df.drop("randomization_string", axis=1)

# %%
# ------------------ EXPORT ------------------

df = df[df.year == ANALYSIS_YEAR]
df.to_csv(EXPORT_COVARIATES_PATH, index=False)

print(f"Saved: {EXPORT_COVARIATES_PATH}")

# %%
