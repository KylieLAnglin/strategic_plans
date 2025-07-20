# %%
import pandas as pd
import os
from tqdm import tqdm
from strategic_plans.library import start, clean_text, diy_grams

# Final model settings based on optimization results
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

print("Final model settings:")
for key, value in FINAL_SETTINGS.items():
    print(f"  {key}: {value}")

# Create output directory
output_dir = start.DATA_DIR + "final_model/"
os.makedirs(output_dir, exist_ok=True)

OUTPUT_TEXT_DF = output_dir + "final_text_dfs.pkl"

# %%
# Load and clean documents
documents_df = pd.read_csv(start.DATA_DIR + "clean/documents_df.csv", delimiter="|")

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
print(f"Documents after basic cleaning: {len(documents_df)}")

# %%
# Create records with final settings applied to all documents
records = []
for _, doc in tqdm(documents_df.iterrows(), total=len(documents_df), desc="Preparing documents"):
    record = {
        "max_df": FINAL_SETTINGS["max_df"],
        "chunk": FINAL_SETTINGS["chunk"],
        "min_df": FINAL_SETTINGS["min_df"],
        "diy_gram": FINAL_SETTINGS["diy_gram"],
        "tribigram": FINAL_SETTINGS["tribigram"],
        "stem": FINAL_SETTINGS["stem"],
        "remove_stop": FINAL_SETTINGS["remove_stop"],
        "topic": FINAL_SETTINGS["topic"],
        "district": doc["district"],
        "text": doc["text_clean"],
    }
    records.append(record)

processed_docs_df = pd.DataFrame(records)

column_order = [
    "max_df",
    "chunk", 
    "min_df",
    "diy_gram",
    "tribigram",
    "stem",
    "remove_stop",
    "topic",
    "district",
    "text",
]
processed_docs_df = processed_docs_df[column_order]

print(f"Final document count: {len(processed_docs_df)}")

# %%
# Apply DIY grams
print("Handling DIY grams")
if FINAL_SETTINGS["diy_gram"] == 1:
    sample_text_before = processed_docs_df["text"].iloc[0][:200]
    print(f"Sample text before DIY processing: {sample_text_before}")
    
    for idx, row in tqdm(processed_docs_df.iterrows(), desc="Applying DIY grams"):
        processed_docs_df.at[idx, "text"] = diy_grams.add_grams(row["text"])
    
    sample_text_after = processed_docs_df["text"].iloc[0][:200]
    print(f"Sample text after DIY processing: {sample_text_after}")
    
    # Check for DIY grams
    sample_tokens = sample_text_after.split()
    potential_diy_grams = [token for token in sample_tokens if "_" in token and not token.replace("_", "").isdigit()]
    print(f"Found {len(potential_diy_grams)} potential DIY gram tokens")
    if potential_diy_grams:
        print(f"Sample DIY grams: {potential_diy_grams[:10]}")
else:
    print("Skipping DIY grams (disabled)")

# %%
# No tribigram processing since tribigram = 0
print("Skipping tribigram processing (disabled)")

# %%
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

# %%
# Handle stopwords
print("Handling stopwords")
if FINAL_SETTINGS["remove_stop"] == 1:
    for idx, row in tqdm(processed_docs_df.iterrows(), desc="Removing stopwords"):
        processed_docs_df.at[idx, "text"] = clean_text.remove_stopwords(row["text"])
    print("Stopwords removed")
else:
    print("Skipping stopword removal (disabled)")

# %%
# No stemming since stem = 0
print("Skipping stemming (disabled)")

# %%
# Generate token list and handle min_df filtering
print("Generating token list for min_df filtering...")
tokens_to_keep = clean_text.get_token_list(processed_docs_df["text"], min_df=FINAL_SETTINGS["min_df"])
print(f"Generated {len(tokens_to_keep)} tokens for min_df={FINAL_SETTINGS['min_df']}")

# Check for DIY grams in token list
if FINAL_SETTINGS["diy_gram"] == 1:
    diy_grams_in_tokens = [token for token in tokens_to_keep if "_" in token and not token.replace("_", "").isdigit()]
    print(f"Found {len(diy_grams_in_tokens)} DIY gram tokens in keep list")
    if diy_grams_in_tokens:
        print(f"Sample DIY grams in token list: {diy_grams_in_tokens[:10]}")

print("Handling min_df filtering")
for idx, row in tqdm(processed_docs_df.iterrows(), desc="Applying min_df filter"):
    processed_docs_df.at[idx, "text"] = clean_text.remove_infrequent_tokens(
        row["text"], tokens_to_keep
    )

# %%
# Save final processed text dataframe
processed_docs_df.to_pickle(OUTPUT_TEXT_DF)
print(f"Final text dataframe saved to: {OUTPUT_TEXT_DF}")
print(f"Final processed documents: {len(processed_docs_df)}")

# Sample final output
print("\nSample of final processed text:")
print(processed_docs_df["text"].iloc[0][:300])

# %%