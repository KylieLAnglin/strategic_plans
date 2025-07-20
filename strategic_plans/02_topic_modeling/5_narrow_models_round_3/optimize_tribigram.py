# %%
import pandas as pd
import os
import numpy as np
from tqdm import tqdm
from strategic_plans.library import start, topic_modeling,clean_text, diy_grams
import gensim
from gensim.models.coherencemodel import CoherenceModel
from gensim.models.ldamodel import LdaModel
from gensim.corpora.dictionary import Dictionary
from gensim.models.phrases import Phrases, Phraser, ENGLISH_CONNECTOR_WORDS
import pickle

# Configuration for flexible parameter testing
# Change PARAMETER_TO_TEST to test different parameters
PARAMETER_TO_TEST = "tribigram"  # Options: "max_df", "tribigram", "stem", "chunk", "min_df", etc.

# Base settings from round 2
base_settings = {
    "topic": 23,
    "chunk": 150,
    "diy_gram": 0,
    "max_df": 0.4,
    "min_df": 5,
    "stem": 0,
    "tribigram": 1,
    "remove_stop": 1
}

# Parameter options to test
parameter_options = {
    "max_df": [0.3, 0.4, 0.5, 0.6, 0.7],
    "tribigram": [0, 1],
    "stem": [0, 1],
    "diy_gram": [0, 1],
    "remove_stop": [0, 1],
    "chunk": [100, 125, 150, 175, 200],
    "min_df": [5, 10, 15]
}

# Get current parameter values to test
current_parameter_values = parameter_options[PARAMETER_TO_TEST]

def generate_flexible_grams(documents_df, text_col, min_count=10, threshold=10, max_vocab_size=40000):
    """
    Generate bigrams and trigrams with flexible parameters
    
    Args:
        documents_df: DataFrame containing text data
        text_col: Column name containing text
        min_count: Minimum frequency for phrases (default: 10, much lower than original 75)
        threshold: Scoring threshold for phrase detection (default: 10, lower than original 30)
        max_vocab_size: Maximum vocabulary size to prevent memory issues
    
    Returns:
        List of detected phrases (bigrams and trigrams)
    """
    print(f"Generating grams with min_count={min_count}, threshold={threshold}")
    
    texts = documents_df[text_col].astype(str).apply(lambda x: x.split())
    
    # Generate bigrams with more permissive parameters
    bigram = Phrases(
        texts, 
        min_count=min_count, 
        threshold=threshold, 
        connector_words=ENGLISH_CONNECTOR_WORDS,
        max_vocab_size=max_vocab_size
    )
    bigram_phraser = Phraser(bigram)
    
    # Generate trigrams from bigram-processed texts
    trigram = Phrases(
        bigram_phraser[texts],
        min_count=min_count,
        threshold=threshold,
        connector_words=ENGLISH_CONNECTOR_WORDS,
        max_vocab_size=max_vocab_size
    )
    trigram_phraser = Phraser(trigram)
    
    # Get all detected phrases
    grams = sorted(list(trigram_phraser.phrasegrams.keys()))
    
    print(f"Generated {len(grams)} total grams")
    
    # Separate bigrams and trigrams for analysis
    bigrams = [gram for gram in grams if gram.count('_') == 1]
    trigrams = [gram for gram in grams if gram.count('_') == 2]
    
    print(f"  - {len(bigrams)} bigrams")
    print(f"  - {len(trigrams)} trigrams")
    
    return grams

def generate_model_id(param_dict, test_parameter):
    """Generate a unique model_id based on the parameter being tested"""
    if test_parameter == "max_df":
        return f"maxdf_{param_dict['max_df']}"
    elif test_parameter == "tribigram":
        return f"tribigram_{param_dict['tribigram']}"
    elif test_parameter == "stem":
        return f"stem_{param_dict['stem']}"
    elif test_parameter == "diy_gram":
        return f"diy_gram_{param_dict['diy_gram']}"
    elif test_parameter == "remove_stop":
        return f"remove_stop_{param_dict['remove_stop']}"
    elif test_parameter == "chunk":
        return f"chunk_{param_dict['chunk']}"
    elif test_parameter == "min_df":
        return f"min_df_{param_dict['min_df']}"
    else:
        return f"param_{param_dict[test_parameter]}"

PASSES = 5
WORDS_TO_VIEW = 10
SEED = 4205
# Create output directory based on parameter being tested
output_dir = start.DATA_DIR + f"narrow_models_round_3/optimize_{PARAMETER_TO_TEST}/"
os.makedirs(output_dir, exist_ok=True)

OUTPUT_TEXT_DF = output_dir + f"{PARAMETER_TO_TEST}_text_dfs.pkl"
OUTPUT_CHUNK_DF = output_dir + f"{PARAMETER_TO_TEST}_text_dfs_w_chunks.pkl"
# all_parameters = pd.read_csv(start.DATA_DIR + "hyperparameters_models.csv")

# %%
# Generate models for the selected parameter
all_combos = []
for param_value in current_parameter_values:
    combo = base_settings.copy()
    combo[PARAMETER_TO_TEST] = param_value
    combo["model_id"] = generate_model_id(combo, PARAMETER_TO_TEST)
    all_combos.append(combo)

parameters = pd.DataFrame(all_combos)
print(f"Testing parameter: {PARAMETER_TO_TEST}")
print(f"Values to test: {current_parameter_values}")
print(f"Generated {len(parameters)} parameter combinations")


####
# Create text_dfs and and clean
####

parameters_dicts = parameters.to_dict(orient="records")
documents_df = pd.read_csv(start.DATA_DIR + "clean/documents_df.csv", delimiter="|")

# %%
print("Handling basic cleaning")
documents_df["text_clean"] = documents_df.text.apply(
    lambda text: clean_text.basic_clean(
        text,
        remove_urls=True,
        remove_unusual=False,
        remove_numbers=False,
        remove_single_letters=False,
        remove_months=False,
    )
)

documents_df = documents_df[~documents_df.isnull()]

# Use flexible gram generation with lower thresholds to get more bigrams/trigrams
# You can adjust these parameters:
# - min_count: how many times a phrase must appear (lower = more phrases)
# - threshold: scoring threshold for phrase detection (lower = more permissive)
grams = generate_flexible_grams(
    documents_df=documents_df, 
    text_col="text_clean",
    min_count=5,    # Much lower than original 75
    threshold=5     # Much lower than original 30
)
original_characters = [gram.replace("_", " ") for gram in grams]

print(f"First 10 grams: {grams[:10]}")
print(f"First 10 original characters: {original_characters[:10]}")

# Prepare long-format records
records = []
for param in tqdm(parameters_dicts, desc="Generating parameter-document combinations"):
    for _, doc in documents_df.iterrows():
        record = {
            "model_id": param["model_id"],
            "remove_stop": param["remove_stop"],
            "diy_gram": param["diy_gram"],
            "stem": param["stem"],
            "tribigram": param["tribigram"],
            "min_df": param["min_df"],
            "chunk": param["chunk"],
            "max_df": param["max_df"],
            "district": doc["district"],
            "text": doc["text_clean"],
        }
        records.append(record)

processed_docs_df = pd.DataFrame(records)

column_order = [
    "model_id",
    "remove_stop",
    "diy_gram",
    "stem",
    "tribigram",
    "min_df",
    "max_df",
    "chunk",
    "district",
    "text",
]
processed_docs_df = processed_docs_df[column_order]

print(f"Final document count: {len(processed_docs_df)}")

print("Handling DIY grams")
for idx, row in tqdm(processed_docs_df.iterrows()):
    if row["diy_gram"]:
        processed_docs_df.at[idx, "text"] = diy_grams.add_grams(
            processed_docs_df.iloc[idx]["text"]
        )

print("Handling tribigrams")
tribigram_rows = processed_docs_df[processed_docs_df.tribigram == 1]
print(f"Number of rows with tribigram=1: {len(tribigram_rows)}")

if len(tribigram_rows) > 0:
    sample_text_before = processed_docs_df.loc[processed_docs_df.tribigram == 1, "text"].iloc[0][:200]
    print(f"Sample text before tribigram processing: {sample_text_before}")

for original, gram in tqdm(
    zip(original_characters, grams), total=len(grams), desc="Processing tribigrams"
):
    processed_docs_df.loc[processed_docs_df.tribigram == 1, "text"] = (
        processed_docs_df.loc[processed_docs_df.tribigram == 1, "text"].str.replace(
            original, gram
        )
    )

if len(tribigram_rows) > 0:
    sample_text_after = processed_docs_df.loc[processed_docs_df.tribigram == 1, "text"].iloc[0][:200]
    print(f"Sample text after tribigram processing: {sample_text_after}")
    
    # Check if any tribigrams were actually created
    sample_tokens = sample_text_after.split()
    tribigram_tokens = [token for token in sample_tokens if "_" in token]
    print(f"Found {len(tribigram_tokens)} tokens with underscores (tribigrams)")
    if tribigram_tokens:
        print(f"First 10 tribigram tokens: {tribigram_tokens[:10]}")

# Advanced cleaning
print("Handling advanced cleaning")
processed_docs_df["text"] = processed_docs_df.text.apply(
    lambda text: clean_text.basic_clean(
        text,
        remove_urls=False,
        remove_unusual=False,
        remove_numbers=True,
        remove_single_letters=True,
        remove_months=True,
    )
)
processed_docs_df.sample(5)

print("Handling stopwords")
for idx, row in tqdm(processed_docs_df.iterrows()):
    if row["remove_stop"] == True:  # Check if stop is True
        processed_docs_df.at[idx, "text"] = clean_text.remove_stopwords(row["text"])
processed_docs_df.sample(5)

print("Handling stemming")
for idx, row in tqdm(processed_docs_df.iterrows()):
    if row["stem"] == True:  # Check if stem is True
        processed_docs_df.at[idx, "text"] = clean_text.lemmatize_text(row["text"])
processed_docs_df.sample(5)

# Generate tokens_to_keep AFTER tribigram processing to include tribigrams in the token list
print("Generating token list after tribigram processing...")
# Get sample text after tribigram processing to generate proper token list
sample_texts_after_tribigrams = processed_docs_df[processed_docs_df.tribigram == 1]["text"].tolist()
if not sample_texts_after_tribigrams:
    sample_texts_after_tribigrams = processed_docs_df["text"].tolist()

# Create a temporary dataframe with post-tribigram text for token list generation
temp_df = pd.DataFrame({"text_clean": sample_texts_after_tribigrams})
tokens_to_keep = clean_text.get_token_list(temp_df["text_clean"], min_df=base_settings["min_df"])
print(f"Generated {len(tokens_to_keep)} tokens for min_df={base_settings['min_df']} (including tribigrams)")

# Check if tribigrams are in the token list
tribigram_tokens_in_list = [token for token in tokens_to_keep if "_" in token]
print(f"Found {len(tribigram_tokens_in_list)} tribigram tokens in token list")
if tribigram_tokens_in_list:
    print(f"Sample tribigram tokens in keep list: {tribigram_tokens_in_list[:10]}")

print("Handling min_df filtering")
for idx, row in tqdm(processed_docs_df.iterrows()):
    if row["min_df"] == base_settings["min_df"]:
        processed_docs_df.at[idx, "text"] = clean_text.remove_infrequent_tokens(
            row["text"], tokens_to_keep
        )


processed_docs_df.to_pickle(OUTPUT_TEXT_DF)
# %%
###
# Create token dfs and chunk
###
with open(OUTPUT_TEXT_DF, "rb") as file:
    docs = pickle.load(file)


def split_text(text, split=100):
    words = text.split()
    chunks = [words[i : i + split] for i in range(0, len(words), split)]
    return chunks

print("Processing all docs at once...")

new_rows = []
for row in tqdm(docs.itertuples(index=False), total=len(docs)):
    chunks = split_text(row.text, split=int(row.chunk))
    for i, chunk in enumerate(chunks):
        new_rows.append(
            {
                "model_id": row.model_id,
                "max_df": row.max_df,
                "remove_stop": row.remove_stop,
                "diy_gram": row.diy_gram,
                "stem": row.stem,
                "tribigram": row.tribigram,
                "min_df": row.min_df,
                "chunk": row.chunk,
                "district": row.district,
                "text": " ".join(chunk),
                "chunk_number": i + 1,
            }
        )

new_docs_df = pd.DataFrame(new_rows)
new_docs_df.reset_index(drop=True, inplace=True)

print("Getting word count....")
new_docs_df["word_count"] = new_docs_df["text"].apply(lambda x: len(x.split()))

print("Getting tokens....")
new_docs_df["tokens"] = new_docs_df["text"].apply(lambda x: x.split())

# Check for tribigrams in final tokens
tribigram_docs = new_docs_df[new_docs_df["tribigram"] == 1]
if len(tribigram_docs) > 0:
    sample_tokens = tribigram_docs["tokens"].iloc[0]
    tribigram_tokens = [token for token in sample_tokens if "_" in token]
    print(f"Final tokens check - Found {len(tribigram_tokens)} tribigram tokens in sample")
    if tribigram_tokens:
        print(f"Sample tribigram tokens in final output: {tribigram_tokens[:10]}")
    else:
        print("No tribigram tokens found in final output!")
        print(f"Sample final tokens: {sample_tokens[:20]}")

new_docs_df.to_pickle(OUTPUT_CHUNK_DF)
print(f"All docs processed and saved with {len(new_docs_df)} rows.")

# %%
# Run topic modeling

for model in tqdm(parameters_dicts, desc="Running topic models"):
    # Set model name using model_id
    model_name = f"topic{model['topic']}_{model['model_id']}"
    
    newpath = output_dir + "topic_models/" + model_name + "/"
    os.makedirs(newpath, exist_ok=True)
    
    # Import text
    text_df = pd.read_pickle(
        OUTPUT_CHUNK_DF
    )
    text_df = text_df[(text_df["model_id"] == model["model_id"])]
    
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


# %%
# Generate prevalence file for rating 
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
print(f"Processing {len(folders)} folders: {folders}")
print(f"Current parameter values being tested: {current_parameter_values}")
print(f"Available model_ids in parameters: {list(parameters['model_id'])}")

topic_prevalence_dfs = []
for folder in folders:
    # Extract model_id from folder name (e.g., "topic23_tribigram_1" -> "tribigram_1")
    model_id = folder.split("topic")[1].split("_", 1)[1]
    print(f"Processing folder: {folder} -> model_id: {model_id}")
    
    # Skip folders that don't match current parameter values being tested
    param_value = model_id.split("_")[-1] if "_" in model_id else model_id
    try:
        param_value_int = int(param_value)
        if param_value_int not in current_parameter_values:
            print(f"Skipping folder {folder} (model_id: {model_id}) - not in current test values")
            continue
    except ValueError:
        print(f"Could not parse parameter value from model_id: {model_id}")
        continue
    
    wide_df = pd.read_excel(
        output_dir + "topic_models/" + folder + "/doc_topics_grouped.xlsx"
    )
    wide_df = wide_df[wide_df["district"].isin(districts)]
    
    long_df = pd.melt(
        wide_df, id_vars="district", var_name="topic_number", value_name="prevalence"
    )
    long_df = long_df.sort_values(by=["district", "prevalence"], ascending=False)
    long_df = long_df.groupby("district").head(5)
    
    long_df["model_id"] = model_id
    
    topic_count = int(folder.split("topic")[1].split("_")[0])
    model_params = parameters[parameters["model_id"] == model_id]
    if len(model_params) > 0:
        long_df = pd.merge(long_df, model_params, on="model_id")
        topic_prevalence_dfs.append(long_df)
    else:
        print(f"Warning: No parameters found for model_id {model_id} - skipping")

topic_prevalence_df = pd.concat(topic_prevalence_dfs, ignore_index=True)
final_df = topic_prevalence_df.merge(docs, on="district")

# Add topic words (following 07_link_terms_for_rating2.py pattern)
topic_dfs = []
for folder in folders:
    # Extract model_id from folder name (e.g., "topic23_tribigram_1" -> "tribigram_1")
    model_id = folder.split("topic")[1].split("_", 1)[1]
    
    # Skip folders that don't match current parameter values being tested
    param_value = model_id.split("_")[-1] if "_" in model_id else model_id
    try:
        param_value_int = int(param_value)
        if param_value_int not in current_parameter_values:
            print(f"Skipping folder {folder} (model_id: {model_id}) in topic words section - not in current test values")
            continue
    except ValueError:
        print(f"Could not parse parameter value from model_id: {model_id} in topic words section")
        continue
    
    topic_count = int(folder.split("topic")[1].split("_")[0])
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
    topic_df[PARAMETER_TO_TEST] = param_value

    topic_df = topic_df[["topic", "topic_number", "word_rank", "word", "model_id", PARAMETER_TO_TEST]]
    topic_dfs.append(topic_df)

big_topic_df = pd.concat(topic_dfs)
big_topic_df = big_topic_df.pivot(
    index=["model_id", "topic", "topic_number", PARAMETER_TO_TEST], columns="word_rank", values="word"
)
big_topic_df.columns = [f"word_{i}" for i in range(1, 11)]
big_topic_df = big_topic_df.reset_index()

final_df["topic_number"] = final_df["topic_number"].astype(int)
big_topic_df["topic_number"] = big_topic_df["topic_number"].astype(int)
final_df[PARAMETER_TO_TEST] = final_df[PARAMETER_TO_TEST].astype(str)
big_topic_df[PARAMETER_TO_TEST] = big_topic_df[PARAMETER_TO_TEST].astype(str)

final_df = final_df.merge(big_topic_df, on=["model_id", "topic", "topic_number", PARAMETER_TO_TEST], how="left")

# Sort and save for rating

final_df = final_df.sort_values(by=["district", PARAMETER_TO_TEST, "prevalence"], ascending=False)
final_df = final_df.groupby(["district", PARAMETER_TO_TEST]).head(5)

sort_columns = ["document_order", PARAMETER_TO_TEST, "prevalence"]
final_df = final_df.sort_values(by=sort_columns, ascending=False)
final_df.to_excel(
    output_dir + f"sample_doc_topic_prevalence_with_words_rated_{PARAMETER_TO_TEST}.xlsx", index=False
)

print(f"{PARAMETER_TO_TEST} optimization complete. Rate the models in sample_doc_topic_prevalence_with_words_rated_{PARAMETER_TO_TEST}.xlsx")

# %%
# %% Import ratings
ratings_df = pd.read_excel(
    output_dir + f"sample_doc_topic_prevalence_with_words_rated_{PARAMETER_TO_TEST}_rated.xlsx"
)
# %%
grouped_df = ratings_df.groupby(["model_id"]).agg(
    {
        "model_quality": ["mean", "max", "var"],
    }
)
grouped_df.columns = [
    "model_quality_mean",
    "model_quality_max",
    "model_quality_var",
]
grouped_df = grouped_df.reset_index()
grouped_df = grouped_df.sort_values(by=["model_quality_mean"], ascending=False)

# %%