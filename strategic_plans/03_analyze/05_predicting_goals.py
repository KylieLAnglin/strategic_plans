# %%
import pandas as pd
import numpy as np
from strategic_plans.library import start
import statsmodels.api as sm
import statsmodels.formula.api as smf


# %%

df = pd.read_csv(start.MAIN_DIR + "data/clean/plans_codes.csv")
meta_data = pd.read_csv(start.MAIN_DIR + "data/clean/plans_meta_data_full.csv")
df = df.merge(meta_data, on="leaid")

df = df.rename(
    columns={
        "code_soft_skills_sel_(social_emotional_learning)_applied": "code_soft_skills_sel_applied"
    }
)
codes = [col for col in df.columns if "applied" in col]

for code in codes:
    df[code] = np.where(df[code] == True, 1, 0)

df = df.sample(int(len(df) / 2), random_state=26)
# %%
for code in codes:
    mod = smf.ols(formula=code + "~ avgrdall", data=df)
    res = mod.fit()
    pvalue = res.pvalues.loc["avgrdall"]
    if pvalue < 0.05:
        print(code)

# %%
for code in codes:
    mod = smf.ols(formula=code + "~ test_math_all_mean", data=df)
    res = mod.fit()
    pvalue = res.pvalues.loc["test_math_all_mean"]
    if pvalue < 0.05:
        print(res.summary())
        print(code)
# %%
for code in codes:
    mod = smf.ols(formula=code + "~ test_rla_all_mean", data=df)
    res = mod.fit()
    pvalue = res.pvalues.loc["test_rla_all_mean"]
    if pvalue < 0.05:
        print(code)
# %%
for code in codes:
    mod = smf.ols(formula=code + "~ perfrl", data=df)
    res = mod.fit()
    pvalue = res.pvalues.loc["perfrl"]
    if pvalue < 0.05:
        print(code)
df["avgrdall"] = df.avgrdall / 100

# %%
code = "code_facilities_transportation_applied"
char = "avgrdall"
mod = smf.ols(formula=code + "~ " + char, data=df)
res = mod.fit()
print(res.summary())
# %%
