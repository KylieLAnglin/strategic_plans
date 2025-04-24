# %%
import pandas as pd
from tqdm import tqdm

from strategic_plans.library import start, clean_text, diy_grams


SAMPLE = False
SEED = 653
# %%
parameters = pd.read_csv(start.DATA_DIR + "hyperparameters_models.csv")

# %%
if SAMPLE:
    parameters = parameters.sample(25, random_state=SEED)
parameters_dicts = parameters.to_dict(orient="records")

# %%
documents_df = pd.read_csv(start.DATA_DIR + "clean/documents_df.csv", delimiter="|")
if SAMPLE:
    documents_df = documents_df.sample(50, random_state=SEED)
documents_df.head(1)

# %%
print("Handling basic cleaning")
documents_df["text_clean"] = documents_df.text.apply(
    lambda text: clean_text.basic_clean(
        text,
        remove_urls=True,
        remove_unusual=True,
        remove_numbers=True,
        remove_single_letters=False,
        remove_months=False,
    )
)
documents_df = documents_df[~documents_df.isnull()]
documents_df.head(10)

# %%
# Determine tokens to keep for min_df
tokens_to_keep_5 = clean_text.get_token_list(documents_df["text_clean"], min_df=5)
tokens_to_keep_20 = clean_text.get_token_list(documents_df["text_clean"], min_df=20)

# Determine phrases
grams = clean_text.generate_list_of_grams(
    documents_df=documents_df, text_col="text_clean"
)
# %%
original_characters = [gram.replace("_", " ") for gram in grams]

# %%

# Prepare long-format records
records = []
for param in tqdm(parameters_dicts, desc="Generating parameter-document combinations"):
    for _, doc in documents_df.iterrows():
        record = {
            "remove_stop": param["remove_stop"],
            "diy_gram": param["diy_gram"],
            "stem": param["stem"],
            "tribigram": param["tribigram"],
            "min_df": param["min_df"],
            "chunk": param["chunk"],
            "decision_id": param["decision_id"],
            "district": doc["district"],
            "text": doc["text_clean"],
        }
        records.append(record)

# Convert to DataFrame
processed_docs_df = pd.DataFrame(records)

# Optional: reorder columns
column_order = [
    "remove_stop",
    "diy_gram",
    "stem",
    "tribigram",
    "min_df",
    "chunk",
    "decision_id",
    "district",
    "text",
]
processed_docs_df = processed_docs_df[column_order]

print(f"Final document count: {len(processed_docs_df)}")

# %%
# DIY gram
print("Handling DIY grams")
for idx, row in tqdm(processed_docs_df.iterrows()):
    if row["diy_gram"]:
        processed_docs_df.at[idx, "text"] = diy_grams.add_grams(
            processed_docs_df.iloc[idx]["text"]
        )
processed_docs_df.sample(5)

# %%
# tribigram
print("Handling tribigrams")
for original, gram in tqdm(zip(original_characters, grams)):
    processed_docs_df.loc[processed_docs_df.tribigram == 1, "text"] = (
        processed_docs_df.loc[processed_docs_df.tribigram == 1, "text"].str.replace(
            original, gram
        )
    )
processed_docs_df.sample(5)

# %%
print("Handling stopwords")
for idx, row in processed_docs_df.iterrows():
    if row["remove_stop"] == True:  # Check if stop is True
        print("here")
        processed_docs_df.at[idx, "text"] = clean_text.remove_stopwords(row["text"])
        print(processed_docs_df.at[idx, "text"])
        stop
processed_docs_df.sample(5)
# %%

# %%
print("Handling stemming")
for idx, row in processed_docs_df.iterrows():
    if row["stem"] == True:  # Check if stem is True
        processed_docs_df.at[idx, "text"] = clean_text.lemmatize_text(row["text"])
processed_docs_df.sample(5)

# %%
print("Handling min_df 5")
for idx, row in processed_docs_df.iterrows():
    if row["min_df"] == 5:
        processed_docs_df.at[idx, "text"] = clean_text.remove_infrequent_tokens(
            row["text"], tokens_to_keep_5
        )

# Handling min_df == 20
print("Handling min_df 20")
for idx, row in processed_docs_df.iterrows():
    if row["min_df"] == 20:
        processed_docs_df.at[idx, "text"] = clean_text.remove_infrequent_tokens(
            row["text"], tokens_to_keep_20
        )

# %%

# %%
processed_docs_df.to_pickle(start.PATH + "data/clean/text_dfs_temp.pkl")
# %%
