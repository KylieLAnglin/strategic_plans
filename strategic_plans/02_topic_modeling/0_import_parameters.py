# %%
import pandas as pd
import itertools
import start

parameters = pd.read_excel(
    start.PATH + "hyperparameters.xlsx",
    sheet_name="Final",
)
parameters = parameters[parameters["Decision"] != "topics"]
parameters = parameters.set_index("Decision")
parameters_t = parameters.T
# %%
parameters_dict = parameters.to_dict()

decisions = list(parameters.index)

# %%
decisions_dict = {}
for decision in decisions:
    decisions_dict[decision] = list(parameters_t[decision].dropna())
decisions_dict
# %%
combinations = list(itertools.product(*decisions_dict.values()))
combinations_df = pd.DataFrame(combinations, columns=decisions_dict.keys())
combinations_df = combinations_df.reset_index()
combinations_df = combinations_df.rename(columns={"index": "decision_id"})
# %%
combinations_df.to_csv(start.PATH + "data/hyperparameters_models.csv", index=False)
# %%
