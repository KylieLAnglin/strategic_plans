# %%
import pandas as pd
import random
from strategic_plans.library import start

RAW_SEDA = start.NATIONAL_DIR + "raw_from_SEDA/"
RAW_CCD = start.NATIONAL_DIR + "raw_from_CCD/"

CLEAN_DIR = start.NATIONAL_DIR + "clean/"

# %%
seda = pd.read_csv(RAW_SEDA + "seda_cov_geodist_poolyr_4.1.csv")
ccd = pd.read_csv(RAW_CCD + "nonfiscal_district_2122_directory.csv")
regions = pd.read_csv(start.NATIONAL_DIR + "us census bureau regions and divisions.csv")
states = pd.read_csv(start.NATIONAL_DIR + "states.csv")
# %% Clean SEDA
seda["leaid"] = seda.sedalea.fillna(0)
seda["leaid"] = seda.leaid.astype(int)


seda = seda.rename(columns={"fips": "fips_seda"})
seda["fips_seda"] = seda.fips_seda.fillna(0)
seda["fips_seda"] = seda.fips_seda.astype(int)

seda["sedaleaname"] = seda.sedaleaname.fillna("")

# %% Clean CCD

ccd["leaid"] = ccd.LEAID.fillna(0)
ccd["leaid"] = ccd.leaid.astype(int)

ccd["fips"] = ccd.FIPST.fillna(0)
ccd["fips"] = ccd.fips.astype(int)


# %% Merge SEDA and CCD
df = ccd.merge(seda, left_on="leaid", right_on="leaid", how="outer", indicator="_merge")
df._merge.value_counts()

df[df._merge == "right_only"]["sedaleaname"].sample(10)
df[df._merge == "right_only"]["LEA_NAME"].sample(10)
# %%
df = df[df._merge == "both"].drop("_merge", axis=1)

# %% Clean and select columns

df["zip_code"] = df.MZIP.astype(int)
df["year"] = df.year.astype(int)
df["locale"] = df[[col for col in df.columns if "locale_" in col]].idxmax(axis=1)
df["urbanicity"] = df["locale"].str.extract("_(.*?)_")


columns = {
    "LEA_NAME": "lea_name",
    "ST": "state",
    # "MZIP": "zip_code",
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
# df["zip_code"] = df.zip_code.astype(int)

columns_to_drop = [col for col in df.columns if col not in columns.values()]
df.drop(columns=columns_to_drop, inplace=True)


# %% Clean and generate columns


df = df.merge(regions, how="left", left_on="state", right_on="State Code")
df = df.rename(columns={"Region": "census_region", "Division": "census_division"})
df.drop(columns=["State", "State Code"], inplace=True)

# %%
states = states.rename(columns={"State": "state_name", "Abbreviation": "state_fips"})
df = df.merge(states, how="left", left_on="state", right_on="state_fips")

# %% Create random number

# %% Add random assignment
df["randomization_string"] = df.leaid.astype(str)


def generate_random_number_from_string(string):
    # Set the seed using a string
    seed_str = string
    seed = int.from_bytes(seed_str.encode(), "little")
    random.seed(seed)

    # Generate a random number between 1 and 1000000
    random_num = random.randint(1, 1000000)

    return random_num


df["random_number"] = df.randomization_string.apply(generate_random_number_from_string)
df.drop("randomization_string", axis=1)
# %% Export
df = df[df.year == 2018]
df.to_csv(start.DATA_DIR + "clean/seda_ccd_covariates_2018.csv", index=False)

# %%
