# %%
import pandas as pd
import itertools
import start
import pickle

import clean_text
import diy_grams
import re
from tqdm import tqdm
from gensim.models import Phrases
from gensim.models.phrases import Phraser
from collections import defaultdict
import numpy as np

SAMPLE = False
SEED = 653
# %%
parameters = pd.read_csv(start.PATH + "data/hyperparameters_models.csv")

# %%
if SAMPLE:
    parameters = parameters.sample(25, random_state=SEED)
parameters_dict = parameters.to_dict(orient="records")

# %%
documents_df = pd.read_csv(start.PATH + "data/clean/documents_df.csv", delimiter="|")
if SAMPLE:
    documents_df = documents_df.sample(50, random_state=SEED)
documents_df.head()

# %%
print("Handling basic cleaning")
documents_df["text_clean"] = documents_df.text.apply(
    clean_text.basic_clean,
    remove_urls=True,
    remove_unusual=True,
    remove_numbers=True,
    remove_single_letters=False,
    remove_months=False,
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
original_characters = [gram.replace("_", " ") for gram in grams]

# %%
processed_docs_df = pd.DataFrame(
    columns=[
        "stop",
        "diy_gram",
        "stem",
        "tribigram",
        "min_df",
        "chunk",
        # "topics",
        "district",
        "text",
    ]
)
for choices in parameters_dict:
    for row in documents_df.index:
        district = documents_df.loc[row]["district"]
        text = documents_df.loc[row]["text_clean"]
        new_row = pd.DataFrame(
            {
                "stop": [choices["stop"]],
                "diy_gram": [choices["diy_gram"]],
                "stem": [choices["stem"]],
                "tribigram": [choices["tribigram"]],
                "min_df": [choices["min_df"]],
                "chunk": choices["chunk"],
                # "topics": choices["topics"],
                "decision_id": choices["decision_id"],
                "district": district,
                "text": text,
            }
        )
        processed_docs_df = pd.concat([processed_docs_df, new_row], ignore_index=True)
processed_docs_df = processed_docs_df[
    [
        "stop",
        "diy_gram",
        "stem",
        "tribigram",
        "min_df",
        "chunk",
        # "topics",
        "decision_id",
        "district",
        "text",
    ]
]
len(processed_docs_df)

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
    if row["stop"] == True:  # Check if stop is True
        processed_docs_df.at[idx, "text"] = clean_text.remove_stopwords(row["text"])


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
processed_docs_df.to_pickle(start.PATH + "data/clean/text_dfs.pkl")
# %%
