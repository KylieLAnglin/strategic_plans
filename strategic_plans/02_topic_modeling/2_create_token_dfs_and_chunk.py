# %%
import pandas as pd
import start
import pickle
import numpy as np
from tqdm import tqdm

SAMPLE = False
SEED = 653

with open(start.PATH + "data/clean/text_dfs.pkl", "rb") as file:
    docs = pickle.load(file)


# %% Create groups of docs to prevent kernel from crashing

# Group rows by decision_id for later topic modeling
grouped_docs = [group for _, group in docs.groupby("decision_id")]

# Distribute grouped docs into 10 balanced partitions by iterating through and adding to the smallest group
balanced_groups = [[] for _ in range(10)]
group_sizes = [0] * 10

for group in grouped_docs:
    smallest_group_index = np.argmin(group_sizes)
    balanced_groups[smallest_group_index].append(group)
    group_sizes[smallest_group_index] += len(group)

final_groups = [pd.concat(group, ignore_index=True) for group in balanced_groups]


# %%
def split_text(text, split=100):
    words = text.split()
    chunks = [words[i : i + split] for i in range(0, len(words), split)]
    return chunks


for idx, group_df in enumerate(final_groups):
    print(f"Processing group {idx + 1} of {len(final_groups)}...")

    new_rows = []
    for row in tqdm(group_df.itertuples(index=False), total=len(group_df)):
        if row.chunk < 1:
            new_rows.append(
                {
                    "decision_id": row.decision_id,
                    "stop": row.stop,
                    "diy_gram": row.diy_gram,
                    "stem": row.stem,
                    "tibigram": row.tribigram,
                    "min_df": row.min_df,
                    "chunk": row.chunk,
                    # "topics": row.topics,
                    "decision_id": row.decision_id,
                    "distict": row.district,
                    "text": row.text,
                    "chunk_number": None,
                }
            )
        else:
            chunks = split_text(row.text, split=int(row.chunk))
            for i, chunk in enumerate(chunks):
                new_rows.append(
                    {
                        "decision_id": row.decision_id,
                        "stop": row.stop,
                        "diy_gram": row.diy_gram,
                        "stem": row.stem,
                        "tibigram": row.tribigram,
                        "min_df": row.min_df,
                        "chunk": row.chunk,
                        # "topics": row.topics,
                        "decision_id": row.decision_id,
                        "distict": row.district,
                        "text": " ".join(chunk),
                        "chunk_number": i + 1,
                    }
                )

    new_group_df = pd.DataFrame(new_rows)
    new_group_df.reset_index(drop=True, inplace=True)

    print("Getting word count....")
    new_group_df["word_count"] = new_group_df["text"].apply(lambda x: len(x.split()))

    print("Getting tokens....")
    new_group_df["tokens"] = new_group_df["text"].apply(lambda x: x.split())

    output_path = start.PATH + f"data/clean/text_dfs_w_chunks_group_{idx + 1}.pkl"
    new_group_df.to_pickle(output_path)
    print(f"Group {idx + 1} saved successfully with {len(new_group_df)} rows.")

print("All groups processed and saved.")
