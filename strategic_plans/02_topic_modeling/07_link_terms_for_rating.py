# %%
import pandas as pd
from strategic_plans.library import start, topic_modeling
import os

df = pd.read_csv(start.RESULTS_DIR + "sample_doc_topic_prevalence_tfidf.csv")

# %%
folders = os.listdir(start.RESULTS_DIR + "topic_models/")
folders = [folder for folder in folders if folder != ".DS_Store"]

topic_dfs = []
for folder in folders:
    model_id = int(folder.split("model")[1].split("topic")[0])
    wide_topic_df = pd.read_csv(
        start.RESULTS_DIR + "topic_models/" + folder + "/topics.csv"
    )

    long_topic_df = wide_topic_df.melt(var_name="variable", value_name="value")

    # Extract topic number and column type (word or probability)
    long_topic_df["topic_number"] = (
        long_topic_df["variable"].str.extract(r"(\d+)").astype(int)
    )
    long_topic_df["col_type"] = long_topic_df["variable"].str.extract(r"([a-zA-Z]+)")

    word_df = long_topic_df[["topic_number", "value", "col_type"]]
    word_df = word_df[word_df["col_type"] == "Word"]
    word_df = word_df.rename(columns={"value": "word"})
    word_df = word_df.drop(columns="col_type")

    word_df = word_df.sort_values(by="topic_number")
    word_df["word_rank"] = word_df.groupby("topic_number").cumcount() + 1

    prob_df = long_topic_df[["topic_number", "value", "col_type"]]
    prob_df = prob_df[prob_df["col_type"] == "Prob"]
    prob_df = prob_df.rename(columns={"value": "prob"})
    prob_df = prob_df.drop(columns="col_type")
    prob_df = prob_df.sort_values(by="topic_number")
    prob_df["word_rank"] = prob_df.groupby("topic_number").cumcount() + 1

    topic_df = word_df.merge(prob_df, on=["topic_number", "word_rank"])
    topic_df["model_id"] = model_id
    topic_df = topic_df[["model_id", "topic_number", "word_rank", "word", "prob"]]
    topic_dfs.append(topic_df)

# %%

big_topic_df = pd.concat(topic_dfs)
big_topic_df = big_topic_df[["model_id", "topic_number", "word", "word_rank"]]

# now long to wide with word1 word2 word3 word4 word5 columns
big_topic_df = big_topic_df.pivot(
    index=["model_id", "topic_number"], columns="word_rank", values="word"
)
big_topic_df.columns = [f"word_{i}" for i in range(1, 11)]
big_topic_df = big_topic_df.reset_index()


# %%

# %%
df = df.merge(big_topic_df, on=["model_id", "topic_number"])

# %%

sort_columns = [
    "document_order",
    "model_id",
    "prevalence",
    "topic_number",
]
df = df.sort_values(by=sort_columns, ascending=False)
df.to_excel(
    start.DATA_DIR + "clean/sample_doc_topic_prevalence_with_words.xlsx", index=False
)


# %%
