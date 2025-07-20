# %%
import pandas as pd
import os
from tqdm import tqdm
from strategic_plans.library import start, topic_modeling
import gensim
from gensim.models.coherencemodel import CoherenceModel
from gensim.models.ldamodel import LdaModel
from gensim.corpora.dictionary import Dictionary
import pickle

# Final model settings
FINAL_SETTINGS = {
    "max_df": 0.4,
    "chunk": 150,
    "min_df": 10,
    "diy_gram": 1,  # Yes DIY grams
    "tribigram": 0,  # No bigrams or trigrams
    "stem": 0,      # No stemming
    "remove_stop": 1,
    "topic": 23
}


# Model training parameters
PASSES = 10  # More passes for final model
WORDS_TO_VIEW = 15  # More words to view in topics
SEED = 4205

# File paths
output_dir = start.DATA_DIR + "final_model/"
INPUT_CHUNK_DF = output_dir + "final_token_dfs_w_chunks.pkl"
model_output_dir = output_dir + "topic_model/"
os.makedirs(model_output_dir, exist_ok=True)

print("=== Final Topic Model Training ===")
print("Final model settings:")
for key, value in FINAL_SETTINGS.items():
    print(f"  {key}: {value}")

# %%
print("Loading final chunked dataframe...")
text_df = pd.read_pickle(INPUT_CHUNK_DF)
print(f"Loaded {len(text_df)} document chunks")

# %%
print("Preparing data for topic modeling...")

# Create dictionary and corpus
docs = list(text_df.tokens)
print(f"Processing {len(docs)} token lists...")

dictionary = Dictionary(docs)
print(f"Initial dictionary size: {len(dictionary)}")

# Apply max_df filtering
dictionary.filter_extremes(no_above=FINAL_SETTINGS["max_df"])
print(f"Dictionary size after max_df={FINAL_SETTINGS['max_df']} filtering: {len(dictionary)}")

# Create corpus
corpus = [dictionary.doc2bow(doc) for doc in docs]
print(f"Created corpus with {len(corpus)} documents")

# %%
print(f"Training LDA model with {FINAL_SETTINGS['topic']} topics...")

lda = gensim.models.LdaModel(
    corpus,
    id2word=dictionary,
    num_topics=FINAL_SETTINGS["topic"],
    passes=PASSES,
    random_state=SEED,
    per_word_topics=True,
    alpha='auto',  # Learn alpha
    eta='auto'     # Learn eta
)

print("Model training completed!")

# %%
print("Computing coherence scores...")

# C_v coherence
cv_score = CoherenceModel(
    model=lda,
    corpus=corpus,
    texts=docs,
    dictionary=dictionary,
    coherence="c_v",
    processes=1,
).get_coherence()

# UMass coherence
umass_score = CoherenceModel(
    model=lda,
    corpus=corpus,
    texts=docs,
    dictionary=dictionary,
    coherence="u_mass",
    processes=1,
).get_coherence()

print(f"C_v coherence score: {cv_score:.4f}")
print(f"UMass coherence score: {umass_score:.4f}")

# %%
print("Creating topic output files...")

# Create topic tables using the library function
topic_modeling.create_topic_tables(
    lda=lda,
    corpus=corpus,
    dictionary=dictionary,
    docs_df=text_df,
    num_topics=FINAL_SETTINGS["topic"],
    folder_path=model_output_dir,
    num_words_to_view=WORDS_TO_VIEW,
)

print(f"Topic tables saved to: {model_output_dir}")

# %%
print("Saving model and metadata...")

# Save the trained model
lda.save(model_output_dir + "final_lda_model")
dictionary.save(model_output_dir + "final_dictionary")

# Save model metadata
model_metadata = {
    "settings": FINAL_SETTINGS,
    "training_params": {
        "passes": PASSES,
        "seed": SEED,
        "alpha": "auto",
        "eta": "auto"
    },
    "performance": {
        "cv_coherence": cv_score,
        "umass_coherence": umass_score
    },
    "data_stats": {
        "num_documents": len(text_df),
        "num_chunks": len(corpus),
        "dictionary_size": len(dictionary)
    }
}

metadata_df = pd.DataFrame([model_metadata])
metadata_df.to_json(model_output_dir + "model_metadata.json", orient="records", indent=2)

print("Model and metadata saved!")

# %%
print("Creating prevalence data for analysis...")

# Load sample documents for prevalence analysis
docs = pd.read_csv(start.DATA_DIR + "clean/sample_documents_final.csv")
districts = list(docs["district"].unique())
print(f"Processing prevalence for {len(districts)} districts")

# Read doc_topics.csv created by topic_modeling.create_topic_tables
doc_topics_df = pd.read_csv(model_output_dir + "doc_topics.csv")

# Parse doc_id to get district info
doc_topics_df[["district", "chunk_info"]] = doc_topics_df["doc_id"].str.split("_chunk", expand=True)

# Group by district to get average topic prevalence
doc_topics_grouped = doc_topics_df.drop(["chunk_info", "text", "index", "doc_id"], axis=1, errors='ignore')
doc_topics_grouped = doc_topics_grouped.groupby(["district"]).mean().reset_index()

# Save grouped results
doc_topics_grouped.to_excel(
    model_output_dir + "doc_topics_grouped.xlsx",
    index=False,
)

print(f"District-level topic prevalence saved to: {model_output_dir}doc_topics_grouped.xlsx")

# %%
print("Creating final analysis dataframe...")

# Filter to sample districts only
doc_topics_sample = doc_topics_grouped[doc_topics_grouped["district"].isin(districts)]

# Melt to long format for analysis
long_df = pd.melt(
    doc_topics_sample, 
    id_vars="district", 
    var_name="topic_number", 
    value_name="prevalence"
)

# Get top 5 topics per district
long_df = long_df.sort_values(by=["district", "prevalence"], ascending=False)
top_topics_df = long_df.groupby("district").head(5)

# Add district metadata
final_analysis_df = top_topics_df.merge(docs, on="district")

# Read topics.csv for topic words
topics_df = pd.read_csv(model_output_dir + "topics.csv")

# Process topic words
topics_long = topics_df.melt(var_name="variable", value_name="value")
topics_long["topic_number"] = topics_long["variable"].str.extract(r"(\d+)").astype(int)
topics_long["col_type"] = topics_long["variable"].str.extract(r"([a-zA-Z]+)")

word_df = topics_long[topics_long["col_type"] == "Word"][["topic_number", "value"]]
word_df = word_df.rename(columns={"value": "word"})
word_df["word_rank"] = word_df.groupby("topic_number").cumcount() + 1

# Get top 10 words per topic
top_words_df = word_df[word_df["word_rank"] <= 10]
top_words_pivot = top_words_df.pivot(
    index="topic_number", 
    columns="word_rank", 
    values="word"
)
top_words_pivot.columns = [f"word_{i}" for i in range(1, 11)]
top_words_pivot = top_words_pivot.reset_index()

# Merge with analysis dataframe
final_analysis_df["topic_number"] = final_analysis_df["topic_number"].astype(int)
final_analysis_df = final_analysis_df.merge(top_words_pivot, on="topic_number", how="left")

# Sort and save
final_analysis_df = final_analysis_df.sort_values(
    by=["document_order", "prevalence"], 
    ascending=[True, False]
)

final_analysis_df.to_excel(
    model_output_dir + "final_topic_analysis.xlsx", 
    index=False
)

print(f"Final analysis dataframe saved to: {model_output_dir}final_topic_analysis.xlsx")

# %%
print("\n=== Final Model Summary ===")
print(f"Topics: {FINAL_SETTINGS['topic']}")
print(f"Dictionary size: {len(dictionary)}")
print(f"Document chunks: {len(corpus)}")
print(f"C_v coherence: {cv_score:.4f}")
print(f"UMass coherence: {umass_score:.4f}")
print(f"Model saved to: {model_output_dir}")
print("\nFiles created:")
print(f"  - final_lda_model (Gensim LDA model)")
print(f"  - final_dictionary (Gensim Dictionary)")
print(f"  - model_metadata.json (Model settings and performance)")
print(f"  - topics.csv (Topic-word distributions)")
print(f"  - doc_topics.csv (Document-topic distributions)")
print(f"  - doc_topics_grouped.xlsx (District-level topic prevalence)")
print(f"  - final_topic_analysis.xlsx (Ready for analysis/rating)")

print("\n=== Ready for Analysis! ===")

# %%