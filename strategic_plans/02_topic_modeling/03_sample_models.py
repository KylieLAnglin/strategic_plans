# %%
import pandas as pd
import os
from strategic_plans.library import start

combos = pd.read_csv(start.DATA_DIR + "hyperparameters_models.csv")

MAX_DFS = [1.0, 0.9, 0.7, 0.5]
TOPICS = [10, 20, 30, 40, 50]

all_combos = []
for max_df in MAX_DFS:
    for topic in TOPICS:
        new_combo = combos.copy()
        new_combo["max_df"] = max_df
        new_combo["topic"] = topic
        all_combos.append(new_combo)
df = pd.concat(all_combos, ignore_index=True)

# rename index to model_id
df["model_id"] = df.index

# %%

df = df[
    [
        "model_id",
        "decision_id",
        "topic",
        "chunk",
        "min_df",
        "max_df",
        "remove_stop",
        "diy_gram",
        "tribigram",
        "stem",
    ]
]
df.head()

# %%
# stratify by topc
# sample_models = (
#     df.groupby(["topic"])
#     .apply(lambda x: x.sample(10, random_state=1))
#     .reset_index(drop=True)
# )
# no stratification
# sample_models = df.sample(50, random_state=1)
# stratify by topic and chunk size
sample_models = (
    df.groupby(["topic", "chunk"])
    .apply(lambda x: x.sample(3, random_state=1))
    .reset_index(drop=True)
)
sample_models = sample_models.sort_values(
    by=[
        "topic",
        "chunk",
        "min_df",
        "max_df",
        "remove_stop",
        "diy_gram",
        "tribigram",
        "stem",
    ]
)
sample_models.to_csv(start.DATA_DIR + "clean/sample_models.csv", index=False)

# %%
