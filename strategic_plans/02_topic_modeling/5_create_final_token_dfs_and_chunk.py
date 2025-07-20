# %%
import pandas as pd
import os
from tqdm import tqdm
from strategic_plans.library import start
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


# File paths
output_dir = start.DATA_DIR + "final_model/"
INPUT_TEXT_DF = output_dir + "final_text_dfs.pkl"
OUTPUT_CHUNK_DF = output_dir + "final_token_dfs_w_chunks.pkl"

print("Loading processed text dataframe...")
with open(INPUT_TEXT_DF, "rb") as file:
    docs = pickle.load(file)

print(f"Loaded {len(docs)} processed documents")

# %%
def split_text(text, split=100):
    """Split text into chunks of specified word count"""
    words = text.split()
    chunks = [words[i : i + split] for i in range(0, len(words), split)]
    return chunks

print(f"Processing documents into {FINAL_SETTINGS['chunk']}-word chunks...")

new_rows = []
for row in tqdm(docs.itertuples(index=False), total=len(docs), desc="Chunking documents"):
    chunks = split_text(row.text, split=int(row.chunk))
    for i, chunk in enumerate(chunks):
        new_rows.append(
            {
                "max_df": row.max_df,
                "chunk": row.chunk,
                "min_df": row.min_df,
                "diy_gram": row.diy_gram,
                "tribigram": row.tribigram,
                "stem": row.stem,
                "remove_stop": row.remove_stop,
                "topic": row.topic,
                "district": row.district,
                "text": " ".join(chunk),
                "chunk_number": i + 1,
            }
        )

new_docs_df = pd.DataFrame(new_rows)
new_docs_df.reset_index(drop=True, inplace=True)

print(f"Created {len(new_docs_df)} document chunks")

# %%
print("Getting word count for each chunk...")
new_docs_df["word_count"] = new_docs_df["text"].apply(lambda x: len(x.split()))

print("Converting text to tokens...")
new_docs_df["tokens"] = new_docs_df["text"].apply(lambda x: x.split())

# %%
# Check final token statistics
print("\n=== Final Token Statistics ===")
print(f"Total chunks: {len(new_docs_df)}")
print(f"Average words per chunk: {new_docs_df['word_count'].mean():.1f}")
print(f"Min words per chunk: {new_docs_df['word_count'].min()}")
print(f"Max words per chunk: {new_docs_df['word_count'].max()}")

# Check for DIY grams in final tokens
if FINAL_SETTINGS["diy_gram"] == 1:
    sample_tokens = new_docs_df["tokens"].iloc[0]
    diy_gram_tokens = [token for token in sample_tokens if "_" in token and not token.replace("_", "").isdigit()]
    print(f"\nDIY gram check - Found {len(diy_gram_tokens)} DIY gram tokens in first chunk")
    if diy_gram_tokens:
        print(f"Sample DIY gram tokens: {diy_gram_tokens[:10]}")

# %%
# Create document IDs for topic modeling
print("Creating document IDs...")
new_docs_df["doc_id"] = (
    new_docs_df.district + "_chunk" + new_docs_df.chunk.astype(int).astype(str) + "_" + new_docs_df.chunk_number.astype(str)
)

# %%
# Sample of final data
print("\n=== Sample Final Data ===")
print("Columns:", new_docs_df.columns.tolist())
print(f"Sample tokens from first chunk: {new_docs_df['tokens'].iloc[0][:20]}")
print(f"Sample doc_id: {new_docs_df['doc_id'].iloc[0]}")

# %%
# Save final chunked dataframe
new_docs_df.to_pickle(OUTPUT_CHUNK_DF)
print(f"\nFinal chunked dataframe saved to: {OUTPUT_CHUNK_DF}")
print(f"Total chunks ready for topic modeling: {len(new_docs_df)}")

# %%
# Create summary statistics file
summary_stats = {
    "total_documents": len(docs),
    "total_chunks": len(new_docs_df),
    "avg_chunks_per_doc": len(new_docs_df) / len(docs),
    "avg_words_per_chunk": new_docs_df['word_count'].mean(),
    "settings": FINAL_SETTINGS
}

summary_df = pd.DataFrame([summary_stats])
summary_df.to_csv(output_dir + "final_preprocessing_summary.csv", index=False)
print(f"Summary statistics saved to: {output_dir}final_preprocessing_summary.csv")

# %%