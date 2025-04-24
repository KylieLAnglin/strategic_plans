# %%
import pandas as pd
from strategic_plans.library import start
import numpy as np

# %%
df = pd.read_csv(start.MAIN_DIR + "data/clean/plans_codes.csv")

characteristics_df = pd.read_csv(
    start.MAIN_DIR + "data/clean/seda_ccd_covariates_2018.csv"
)

# %%
df = df.merge(characteristics_df, on="leaid")
# drop all cols that end in _y
df = df.loc[:, ~df.columns.str.endswith("_y")]
# rename all cols that end in _x
df = df.rename(columns={col: col.replace("_x", "") for col in df.columns})

# %%
df.sample(5)
df["urban"] = np.where(df.urbanicity == "city", 1, 0)
df["suburb"] = np.where(df.urbanicity == "suburb", 1, 0)
df["town"] = np.where(df.urbanicity == "town", 1, 0)
df["rural"] = np.where(df.urbanicity == "rural", 1, 0)
df.to_csv(start.MAIN_DIR + "data/clean/plans_codes_characteristics.csv", index=False)
# %%
