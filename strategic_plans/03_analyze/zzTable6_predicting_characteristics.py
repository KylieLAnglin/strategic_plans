# %%
import pandas as pd
import numpy as np
from strategic_plans.library import start
import statsmodels.formula.api as smf
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment

# %%
# Load the top topics to analyze
top_topics_df = pd.read_excel(start.RESULTS_DIR + 'top_topics.xlsx')
print(f"Analyzing {len(top_topics_df)} topics")

# %%

merge_df = pd.read_excel(start.DATA_DIR + "clean/sample_inclusion_with_topics_and_codes.xlsx")
# Define district characteristics to analyze
CHARACTERISTICS = [
    "northeast", "midwest", "west", "south",  # Geography (south is reference)
    "urban", "suburb", "town", "rural",     # Urbanicity (rural is reference) 
    "enrollment_in_thousands",       # District size
    "percent_race_black_hispanic",   # Student demographics
    "percent_race_white",
    "percent_frl",                     # Socioeconomic status
    "mean_test_score",                 # Academic achievement
    "adults_w_ba",                     # Community education
    "medinc_1000",                     # Community income
]

# Scale percentage variables if needed
for var in ["percent_race_black_hispanic", "percent_race_white", "percent_frl"]:
    merge_df[var] = merge_df[var] * 100
merge_df["medinc_1000"] = merge_df["medinc_1000"] / 1000


# Scale enrollment to thousands if needed
merge_df["enrollment_in_thousands"] = merge_df["enrollment_in_thousands"] / 1000


TOPIC_GROUPS = {
    "Table6_Academic_Topics": ["Topic_1", "Topic_8", "Topic_9", "Topic_16"],
    "Table7_Non_Academic_Outcomes": ["Topic_3", "Topic_5", "Topic_12", "Topic_14"],
    "Table8_Family_Community": ["Topic_17", "Topic_20"],
    "Table9_Mechanisms": ["Topic_0", "Topic_22", "Topic_15"]
}

# Append list of topics from topic groups keys
TOPICS = []
for group in TOPIC_GROUPS.values():
    TOPICS.extend(group)


# %% Urban
formula = "urban ~ " + " + ".join(TOPICS)
mod = smf.ols(formula=formula, data=merge_df)
result = mod.fit()
result.summary()


formula = "Topic_5 ~ " + "urban"
mod = smf.ols(formula=formula, data=merge_df)
result = mod.fit()
result.summary()


formula = "Topic_15 ~ " + "urban"
mod = smf.ols(formula=formula, data=merge_df)
result = mod.fit()
result.summary()


# %%
# Suburban
formula = "suburb ~ " + " + ".join(TOPICS)
mod = smf.ols(formula=formula, data=merge_df)
result = mod.fit()
result.summary()

formula = "Topic_15 ~ " + "suburb"
mod = smf.ols(formula=formula, data=merge_df)
result = mod.fit()
result.summary()


formula = "Topic_22 ~ " + "suburb"
mod = smf.ols(formula=formula, data=merge_df)
result = mod.fit()
result.summary()
# %%

# Town
formula = "town ~ " + " + ".join(TOPICS)
mod = smf.ols(formula=formula, data=merge_df)
result = mod.fit()
result.summary()

# topic 1
formula = "Topic_1 ~ " + "town"
mod = smf.ols(formula=formula, data=merge_df)
result = mod.fit()
result.summary()