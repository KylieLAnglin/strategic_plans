# %%
import pandas as pd
import os
from tqdm import tqdm

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
sample_models = df.sample(75, random_state=1)
# stratify by topic and chunk size
# sample_models = (
#     df.groupby(["topic", "chunk"])
#     .apply(lambda x: x.sample(3, random_state=2))
#     .reset_index(drop=True)
# )
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

# list files in the data/clean directory
files = os.listdir(start.DATA_DIR + "clean/")
files = [file for file in files if file.startswith("text_dfs_w_chunks_group")]

# append to long dataframe
# dfs = []
# for file in files:
#     group = file.split("_")[-1].split(".")[0]
#     df = pd.read_pickle(start.DATA_DIR + "clean/" + file)
#     df = df.drop(["distict", "text", "chunk_number", "word_count", "tokens"], axis=1)
#     df["group"] = group
#     dfs.append(df)
# text_dfs = pd.concat(dfs, ignore_index=True)
# # %%
# text_dfs["text_group"] = text_dfs["group"].astype(int)
# text_dfs = text_dfs.drop("group", axis=1)
# model_parameters = text_dfs.groupby(["decision_id", "text_group"]).mean().reset_index()

# Create mapping without loading full pickle files
decision_to_group = {}
for file in tqdm(files):
    group = file.split("_")[-1].split(".")[0]
    # Load only the columns we need
    df = pd.read_pickle(start.DATA_DIR + "clean/" + file)[["decision_id"]]
    unique_decision_ids = df["decision_id"].unique()
    
    for decision_id in unique_decision_ids:
        decision_to_group[decision_id] = int(group)

# Convert to DataFrame
model_parameters = pd.DataFrame(
    list(decision_to_group.items()), 
    columns=["decision_id", "text_group"]
)

sample_models_final = sample_models.merge(
    model_parameters[["decision_id", "text_group"]],
    how="left",
    indicator=True,
    left_on=["decision_id"],
    right_on=["decision_id"],
)

# %%


sample_models_final = sample_models_final.sort_values(
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
sample_models_final.to_csv(start.DATA_DIR + "clean/sample_models.csv", index=False)
