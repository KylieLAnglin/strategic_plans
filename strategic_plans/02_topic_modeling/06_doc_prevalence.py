# %%
import pandas as pd
import numpy as np
import os
from library import start

docs = pd.read_csv(start.DATA_DIR + "clean/sample_documents_final.csv")
districts = list(docs["district"].unique())
models = pd.read_csv(start.DATA_DIR + "clean/sample_models_coherence.csv")

# %%
# Take mean prevalence of each topic for each district across chunks
folders = os.listdir(start.RESULTS_DIR + "topic_models/")
folders = [folder for folder in folders if folder != ".DS_Store"]
folder = folders[0]
for folder in folders:
    df = pd.read_csv(start.RESULTS_DIR + "topic_models/" + folder + "/doc_topics.csv")

    # split doc_id into distinct and chunk
    df[["district", "chunk", "empty"]] = df["doc_id"].str.split("_", expand=True)
    df_grouped = df.groupby(["district"]).mean().reset_index()
    df_grouped.to_excel(
        start.RESULTS_DIR + "topic_models/" + folder + "/doc_topics_grouped.xlsx",
        index=False,
    )

# %%
# Identify top five topics for each model for each district
topic_prevalence_dfs = []
for folder in folders:
    # import topics from one model for all docs
    wide_df = pd.read_excel(
        start.RESULTS_DIR + "topic_models/" + folder + "/doc_topics_grouped.xlsx"
    )
    # limit to sample docs
    wide_df = wide_df[wide_df["district"].isin(districts)]
    wide_df = wide_df.drop("index", axis=1)

    # make long with col for topic_number and prevalence
    long_df = pd.melt(
        wide_df, id_vars="district", var_name="topic_number", value_name="prevalence"
    )
    # sort values within district by prevalence
    long_df = long_df.sort_values(by=["district", "prevalence"], ascending=False)

    # Keep 5 rows with highest prevalence within district
    long_df = long_df.groupby("district").head(5)
    # extract numbers immediately following "model" in folder name
    model_id = int(folder.split("model")[1].split("topic")[0])
    long_df["model_id"] = model_id

    # merge with model parameters
    long_df = pd.merge(long_df, models, on="model_id")

    topic_prevalence_dfs.append(long_df)

topic_prevalence_df = pd.concat(topic_prevalence_dfs, ignore_index=True)
final_df = topic_prevalence_df.merge(docs, on="district")
final_df = final_df.sort_values(
    by=[
        "document_order",
        "model_id",
        "prevalence",
        "topic_number",
    ],
    ascending=False,
)

first_columns = [
    "district",
    "document_order",
    "model_id",
    "decision_id",
    "topic_number",
    "prevalence",
    "cv_score",
    "umass_score",
]

final_df = final_df[first_columns + list(final_df.columns.difference(first_columns))]

final_df.to_csv(start.RESULTS_DIR + "sample_doc_topic_prevalence.csv", index=False)
# %%
