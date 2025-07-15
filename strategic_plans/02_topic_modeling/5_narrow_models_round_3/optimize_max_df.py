# %%
import pandas as pd
import os
import numpy as np
from tqdm import tqdm
from strategic_plans.library import start, topic_modeling
import gensim
from gensim.models.coherencemodel import CoherenceModel
from gensim.models.ldamodel import LdaModel
from gensim.corpora.dictionary import Dictionary

# Base settings from round 2
base_settings = {
    "topic": 23,
    "chunk": 150,
    "diy_gram": 0,
    "max_df": 0.5,
    "min_df": 5,
    "stem": 0,
    "tribigram": 1,
    "decision_id": 118.0,
    "model_id": 6262,
    "remove_stop": 1
}

# max_df options to test
max_df_options = [0.3, 0.4, 0.5, 0.6, 0.7]

PASSES = 5
WORDS_TO_VIEW = 10
SEED = 4205

# %%
# Generate models for max_df parameter
all_combos = []
for max_df_value in max_df_options:
    combo = base_settings.copy()
    combo["max_df"] = max_df_value
    all_combos.append(combo)

df = pd.DataFrame(all_combos)

# Create mapping to text groups
files = os.listdir(start.DATA_DIR + "clean/")
files = [file for file in files if file.startswith("text_dfs_w_chunks_group")]

decision_to_group = {}
for file in tqdm(files):
    group = file.split("_")[-1].split(".")[0]
    df_temp = pd.read_pickle(start.DATA_DIR + "clean/" + file)[["decision_id"]]
    unique_decision_ids = df_temp["decision_id"].unique()
    
    for decision_id in unique_decision_ids:
        decision_to_group[decision_id] = int(group)

model_parameters = pd.DataFrame(
    list(decision_to_group.items()), 
    columns=["decision_id", "text_group"]
)

sample_models_final = df.merge(
    model_parameters[["decision_id", "text_group"]],
    how="left",
    on=["decision_id"]
)

# Create output directory
output_dir = start.DATA_DIR + "narrow_models_round_3/determine_max_df/"
os.makedirs(output_dir, exist_ok=True)

sample_models_final.to_csv(output_dir + "sample_models.csv", index=False)

# %%
# Run topic modeling
models_list = sample_models_final.to_dict(orient="records")

for model in tqdm(models_list):
    # Set model name
    model_name = (
        "model"
        + str(model["model_id"])
        + "topic"
        + str(model["topic"])
        + "_decision"
        + str(int(model["decision_id"]))
        + "_maxdf" + str(model["max_df"])
    )
    
    newpath = output_dir + "topic_models/" + model_name + "/"
    os.makedirs(newpath, exist_ok=True)
    
    # Import text
    group_num = model["text_group"]
    text_df = pd.read_pickle(
        start.DATA_DIR + f"clean/text_dfs_w_chunks_group_{group_num}.pkl"
    )
    text_df = text_df[(text_df["decision_id"] == model["decision_id"])]
    
    text_df["doc_id"] = (
        text_df.district + "_chunk" + text_df.chunk.astype(int).astype(str)
    )
    
    # Create dictionary and corpus
    docs = list(text_df.tokens)
    dictionary = Dictionary(docs)
    
    dictionary.filter_extremes(no_above=model["max_df"])
    corpus = [dictionary.doc2bow(doc) for doc in docs]
    
    lda = gensim.models.LdaModel(
        corpus,
        id2word=dictionary,
        num_topics=model["topic"],
        passes=PASSES,
        random_state=SEED,
        per_word_topics=True,
    )
    
    cv_score = CoherenceModel(
        model=lda,
        corpus=corpus,
        texts=docs,
        dictionary=dictionary,
        coherence="c_v",
        processes=1,
    ).get_coherence()
    
    umass_score = CoherenceModel(
        model=lda,
        corpus=corpus,
        texts=docs,
        dictionary=dictionary,
        coherence="u_mass",
        processes=1,
    ).get_coherence()
    
    model["cv_score"] = cv_score
    model["umass_score"] = umass_score
    
    topic_modeling.create_topic_tables(
        lda=lda,
        corpus=corpus,
        dictionary=dictionary,
        docs_df=text_df,
        num_topics=model["topic"],
        folder_path=newpath,
        num_words_to_view=WORDS_TO_VIEW,
    )

# Save models with coherence scores
models_df_updated = pd.DataFrame(models_list)
models_df_updated.to_csv(output_dir + "sample_models_coherence.csv", index=False)

# %%
# Generate prevalence file for rating (following 06_doc_prevalence2.py pattern)
docs = pd.read_csv(start.DATA_DIR + "clean/sample_documents_final.csv")
districts = list(docs["district"].unique())

folders = os.listdir(output_dir + "topic_models/")
folders = [folder for folder in folders if folder != ".DS_Store"]

# Create doc_topics_grouped files
for folder in folders:
    df = pd.read_csv(output_dir + "topic_models/" + folder + "/doc_topics.csv")
    df[["district", "chunk", "empty"]] = df["doc_id"].str.split("_", expand=True)
    df = df.drop((["chunk", "empty", "text", "index", "doc_id"]), axis=1)
    df_grouped = df.groupby(["district"]).mean().reset_index()
    df_grouped.to_excel(
        output_dir + "topic_models/" + folder + "/doc_topics_grouped.xlsx",
        index=False,
    )

# Create prevalence data
topic_prevalence_dfs = []
for folder in folders:
    wide_df = pd.read_excel(
        output_dir + "topic_models/" + folder + "/doc_topics_grouped.xlsx"
    )
    wide_df = wide_df[wide_df["district"].isin(districts)]
    
    long_df = pd.melt(
        wide_df, id_vars="district", var_name="topic_number", value_name="prevalence"
    )
    long_df = long_df.sort_values(by=["district", "prevalence"], ascending=False)
    long_df = long_df.groupby("district").head(5)
    
    model_id = int(folder.split("model")[1].split("topic")[0])
    long_df["model_id"] = model_id
    
    topic_count = int(folder.split("topic")[1].split("_")[0])
    model_params = models_df_updated[models_df_updated["topic"] == topic_count]
    long_df = pd.merge(long_df, model_params, on="model_id")
    
    topic_prevalence_dfs.append(long_df)

topic_prevalence_df = pd.concat(topic_prevalence_dfs, ignore_index=True)
final_df = topic_prevalence_df.merge(docs, on="district")

# Add topic words (following 07_link_terms_for_rating2.py pattern)
topic_dfs = []
for folder in folders:
    model_id_str = folder.split("model")[1].split("topic")[0]
    model_id = int(round(float(model_id_str)))
    
    topic_count_str = folder.split("model")[1].split("topic")[1].split("_")[0]
    topic_count = int(round(float(topic_count_str)))
    
    max_df_value = folder.split("maxdf")[-1].split("/")[0]
    wide_topic_df = pd.read_csv(
        output_dir + "topic_models/" + folder + "/topics.csv"
    )
    
    long_topic_df = wide_topic_df.melt(var_name="variable", value_name="value")
    
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
    
    topic_df = word_df[word_df["word_rank"] <= 10]
    topic_df["topic"] = topic_count
    topic_df["model_id"] = model_id
    topic_df["max_df"] = max_df_value

    topic_df = topic_df[["model_id", "topic", "topic_number", "word_rank", "word", "max_df"]]
    topic_dfs.append(topic_df)

big_topic_df = pd.concat(topic_dfs)
# problem: variation in big_topic_df is due to max_df but not included 
big_topic_df = big_topic_df.pivot(
    index=["model_id", "topic", "topic_number", "max_df"], columns="word_rank", values="word"
)
big_topic_df.columns = [f"word_{i}" for i in range(1, 11)]
big_topic_df = big_topic_df.reset_index()

final_df["topic_number"] = final_df["topic_number"].astype(int)
big_topic_df["topic_number"] = big_topic_df["topic_number"].astype(int)
final_df["max_df"] = final_df["max_df"].astype(str)
big_topic_df["max_df"] = big_topic_df["max_df"].astype(str)

final_df = final_df.merge(big_topic_df, on=["model_id", "topic", "topic_number", "max_df"], how="left")

# Sort and save for rating

final_df = final_df.sort_values(by=["district", "max_df", "prevalence"], ascending=False)
final_df = final_df.groupby(["district", "max_df"]).head(5)

sort_columns = ["document_order", "max_df", "prevalence"]
final_df = final_df.sort_values(by=sort_columns, ascending=False)
final_df.to_excel(
    output_dir + "sample_doc_topic_prevalence_with_words_rated.xlsx", index=False
)

print("Max_df optimization complete. Rate the models in sample_doc_topic_prevalence_with_words_rated.xlsx")

# %%