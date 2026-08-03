# %%
import numpy as np
import pandas as pd

from strategic_plans.library import start

# ------------------ SETUP ------------------

SAMPLE_PATH = start.DATA_DIR + "clean/stratified_sample.csv"
VOTESHARE_PATH = start.DATA_DIR + "clean/district_vote_share.dta"
CCD_PATH = start.DATA_DIR + "clean/district_demo_ach_file_v3.dta"

EXPORT_CHARACTERISTICS_PATH = (
    start.DATA_DIR + "clean/stratified_sample_characteristics.csv"
)

# %%
# ------------------ LOAD DATA ------------------

sample_df = pd.read_csv(SAMPLE_PATH)
sample_df["state"] = sample_df.state.apply(lambda x: x.upper())
sample_df["district"] = sample_df.lea_name.apply(lambda x: x.upper())
sample_df = sample_df.drop_duplicates(subset=["state", "district"], keep="first")
sample_df = sample_df[["leaid", "state", "district"]]

# %%
voteshare_df = pd.read_stata(VOTESHARE_PATH)
ccd_df = pd.read_stata(CCD_PATH)

# %%
# ------------------ MERGE SAMPLE AND CCD ------------------

df = sample_df.merge(
    ccd_df, left_on="leaid", right_on="leaid", how="left", indicator="_merge_ccd"
)

# %%
# ------------------ REGION ------------------

df["northeast"] = df["fips_geo"].isin([9, 23, 25, 33, 44, 50, 34, 36, 42])

midwest_states_1 = [18, 17, 26, 39, 55, 19, 20, 27]
midwest_states_2 = [29, 31, 38, 46]
df["midwest"] = df["fips_geo"].isin(midwest_states_1) | df["fips_geo"].isin(
    midwest_states_2
)

south_states_1 = [10, 11, 12, 13, 24, 37, 45, 51, 54]
south_states_2 = [1, 21, 28, 47, 5, 22, 40, 48]
df["south"] = df["fips_geo"].isin(south_states_1) | df["fips_geo"].isin(south_states_2)

west_states_1 = [4, 8, 16, 35, 30, 49]
west_states_2 = [32, 56, 2, 6, 15, 41, 53]
df["west"] = df["fips_geo"].isin(west_states_1) | df["fips_geo"].isin(west_states_2)

for region in ["northeast", "midwest", "south", "west"]:
    df[region] = np.where(df[region] == True, 1, 0)

# %%
# ------------------ URBANICITY ------------------

df["urbanicity"] = df[["urban", "suburb", "town", "rural"]].idxmax(axis=1)
urbanicity_indicators = pd.get_dummies(df["urbanicity"])
df = df.drop(["urban", "suburb", "town", "rural"], axis=1)
df = pd.concat([df, urbanicity_indicators], axis=1)

# %%
# ------------------ RENAME AND GENERATE CHARACTERISTICS ------------------

df["enrollment_in_thousands"] = df.tot_enroll

df["percent_race_white"] = df.perwht
df["percent_race_black"] = df.perblk
df["percent_hispanic"] = df.perhsp
df["percent_race_black_hispanic"] = df.perhsp + df.perblk
df["percent_race_other"] = df.perasn + df.pernam

df["percent_frl"] = df.perfrl

df["log_income"] = df.lninc50all

df["unemployment"] = df.unempall

df["trump_voteshare"] = df.district_pct_trump
df["competitive"] = np.where(
    (df.district_pct_trump > 0.45) & (df.district_pct_trump < 0.55), 1, 0
)

df["adults_w_ba"] = df.baplusall
df["mean_test_score"] = df.agg_all
df["medinc"] = np.exp(df["lninc50all"])
df["medinc_1000"] = df["medinc"] / 1000

binary_characteristics = [
    "northeast",
    "midwest",
    "south",
    "west",
    "urban",
    "suburb",
    "town",
    "rural",
]
for characteristic in binary_characteristics:
    df[characteristic] = np.where(
        df[characteristic] == True, 1, np.where(df[characteristic] == False, 0, np.nan)
    )

characteristics = [
    "state",
    "district",
    "northeast",
    "midwest",
    "south",
    "west",
    "urban",
    "suburb",
    "town",
    "rural",
    "enrollment_in_thousands",
    "percent_race_black_hispanic",
    "percent_race_other",
    "percent_race_white",
    "mean_test_score",
    "percent_frl",
    "adults_w_ba",
    "medinc_1000",
    "district_pct_trump",
    "competitive",
]

df = df.set_index("leaid")
df = df[characteristics]

# %%
# ------------------ CREATE INDICATORS ------------------

df["blue"] = df["district_pct_trump"] < 0.45
df["purple"] = (df["district_pct_trump"] >= 0.45) & (df["district_pct_trump"] < 0.56)
df["red"] = df["district_pct_trump"] >= 0.56

df["district_politics"] = np.where(
    df["blue"], "blue", np.where(df["purple"], "purple", "red")
)

df["whiteq4"] = pd.qcut(df["percent_race_white"], 4, labels=False) + 1

df["geo"] = np.where(
    df["northeast"],
    "northeast",
    np.where(df["midwest"], "midwest", np.where(df["south"], "south", "west")),
)
df["urganicity"] = np.where(
    df["urban"],
    "urban",
    np.where(df["suburb"], "suburb", np.where(df["town"], "town", "rural")),
)

# %%
# ------------------ EXPORT ------------------

df.to_csv(EXPORT_CHARACTERISTICS_PATH)

print(f"Saved: {EXPORT_CHARACTERISTICS_PATH}")

# %%
