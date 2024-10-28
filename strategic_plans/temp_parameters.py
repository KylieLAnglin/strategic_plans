# %%
import pandas as pd
import itertools

parameters = pd.read_excel(
    "/Users/kla21002/Library/CloudStorage/OneDrive-UniversityofConnecticut/Documents - strategic_plans/hyperparameters_maybe.xlsx",
    sheet_name="Final",
)
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
combinations_df.to_csv(
    "/Users/kla21002/Library/CloudStorage/OneDrive-UniversityofConnecticut/Documents - strategic_plans/hyperparameters_models.csv"
)
# %%
