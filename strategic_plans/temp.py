# %%

import pandas as pd

from library import start

stratified_sample = pd.read_csv(
    "/Users/kla21002/Library/CloudStorage/Dropbox/Active/Research/strategic_plans/data/clean/stratified_sample.csv"
)
stratified_sample

notes = pd.read_excel(
    "/Users/kla21002/Library/CloudStorage/Dropbox/Active/Research/strategic_plans/data/raw/stratified_sample_download_notes.xlsx"
)

df = stratified_sample[
    [
        "strata_string",
        "random_number",
        "leaid",
        "lea_name",
        "state",
        "city",
        "locale",
        "census_division",
    ]
].merge(
    notes[
        [
            "lea_name",
            "plan_available",
            "url",
            "start_year",
            "end_year",
            "previous_plan_available",
            "previous_url",
            "start_year2",
            "end_year3",
            "Notes",
            "Missing Information",
        ]
    ],
    on="lea_name",
    how="left",
    indicator=False,
)
# df._merge.value_counts()
# %%
df = df.sort_values(by="random_number")
df.to_csv(
    "/Users/kla21002/Library/CloudStorage/Dropbox/Active/Research/strategic_plans/data/raw/temp.csv",
    index=False,
)
# %%
