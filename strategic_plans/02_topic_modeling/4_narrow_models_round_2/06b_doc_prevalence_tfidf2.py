# %%
import pandas as pd
import numpy as np
import os
from strategic_plans.library import start, topic_modeling

docs = pd.read_csv(start.DATA_DIR + "clean/sample_documents_final.csv")
districts = list(docs["district"].unique())
models = pd.read_csv(start.DATA_DIR + "narrow_models_round_2/sample_models_coherence.csv")

# %%
# Take mean prevalence of each topic for each district across chunks
folders = os.listdir(start.DATA_DIR + "narrow_models_round_2/topic_models/")
folders = [folder for folder in folders if folder != ".DS_Store"]


# %%
topic_prevalence_idfs = []
folder = folders[0]
for folder in folders:
    # import topics from one model for all docs
    wide_df = pd.read_excel(
        start.DATA_DIR + "narrow_models_round_2/topic_models/" + folder + "/doc_topics_grouped.xlsx"
    )
    # wide_df = wide_df.drop(["index"], axis=1)

    # apply tf-idf weighting
    temp_df = wide_df.set_index("district")

    # Extract topic prevalence values
    topic_columns = [col for col in temp_df.columns if col != "district"]
    topic_matrix = temp_df[topic_columns].values

    # Compute wide_df as sum of topic prevalence across all districts
    df_topic = np.sum(topic_matrix, axis=0)

    # Compute Smoothed IDF
    N = temp_df.shape[0]  # Number of districts
    idf = np.log(1 + N / df_topic)

    # Apply TF-IDF weighting
    tfidf_matrix = topic_matrix * idf  # Element-wise multiplication

    # Convert back to DataFrame
    tfidf_df = pd.DataFrame(tfidf_matrix, columns=topic_columns)
    tfidf_df.insert(0, "district", wide_df["district"])  # Add district column back

    # limit to sample docs
    tfidf_df = tfidf_df[tfidf_df["district"].isin(districts)]

    # make long with col for topic_number and prevalence
    long_df = pd.melt(
        tfidf_df, id_vars="district", var_name="topic_number", value_name="prevalence"
    )
    # sort values within district by prevalence
    long_df = long_df.sort_values(by=["district", "prevalence"], ascending=False)

    # Keep 5 rows with highest prevalence within district
    long_df = long_df.groupby("district").head(5)
    # extract numbers immediately following "model" in folder name
    model_id = int(folder.split("model")[1].split("topic")[0])
    long_df["model_id"] = model_id

    # merge with model parameters - match on both model_id and topic count
    topic_count_str = folder.split("topic")[1].split("_")[0]
    topic_count = int(float(topic_count_str))
    model_params = models[models["topic"] == topic_count]
    long_df = pd.merge(long_df, model_params, on="model_id")

    topic_prevalence_idfs.append(long_df)

topic_prevalence_idf = pd.concat(topic_prevalence_idfs, ignore_index=True)
final_df = topic_prevalence_idf.merge(docs, on="district")
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

final_df.to_csv(
    start.DATA_DIR + "narrow_models_round_2/sample_doc_topic_prevalence_tfidf.csv", index=False
)
# %%

# %%
