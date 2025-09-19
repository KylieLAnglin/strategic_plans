# %%
import os
import pandas as pd
import numpy as np
from strategic_plans.library import start

# ------------------ Config ------------------
N_PER_TOPIC = 5
RANDOM_STATE = 42
EXCLUDED_PARENT_CODES = {"Uninterpretable", "Document Details"}

# ------------------ Load data ------------------
topic_naming_path = os.path.join(start.DATA_DIR, "final_model/topic_naming_named.xlsx")
naming_df = pd.read_excel(topic_naming_path)

# Normalize column names
naming_df = naming_df.rename(columns={"Unnamed: 0": "topic_id"})
naming_df["topic_id_space"] = naming_df["topic_id"].str.replace("_", " ", regex=False)

# Keep included topics
included_meta = naming_df[~naming_df["parent_code"].isin(EXCLUDED_PARENT_CODES)].copy()

# Load segment-level doc-topic matrix
doc_topics_path = os.path.join(start.DATA_DIR, "final_model/topic_model/doc_topics.csv")
doc_df = pd.read_csv(doc_topics_path)

# Identify topic columns
topic_cols = [str(i) for i in range(23)]  # "0".."22"

# ------------------ Sampling ------------------
rows = []
for tcol in topic_cols:
    topic_id = f"Topic_{tcol}"
    if topic_id not in included_meta["topic_id"].values:
        continue

    col = pd.to_numeric(doc_df[tcol], errors="coerce").fillna(0.0)
    cutoff = col.quantile(0.90)

    # Filter to top quartile
    topq = doc_df[col >= cutoff].copy()
    if topq.empty:
        continue

    # Sample up to N_PER_TOPIC
    sample_n = min(N_PER_TOPIC, len(topq))
    sampled = topq.sample(n=sample_n, random_state=RANDOM_STATE)

    # Metadata
    meta = included_meta[included_meta["topic_id"] == topic_id].iloc[0]
    topic_code = meta["code"]
    parent_code = meta["parent_code"]

    for _, r in sampled.iterrows():
        rows.append({
            "Topic ID": topic_id,
            "Topic Name": topic_code,
            "Parent Code": parent_code,
            "Topic Column": tcol,
            "Topic Prevalence": float(r[tcol]),
            "Top-Quartile Cutoff": float(cutoff),
            "doc_id": r["doc_id"],
            "Excerpt": r["text"],
        })

# ------------------ Build table ------------------
out_df = pd.DataFrame(rows)
if not out_df.empty:
    out_df = out_df.sort_values(["Topic Name", "Topic Prevalence"], ascending=[True, False])

# ------------------ Export ------------------
output_path = os.path.join(start.RESULTS_DIR, "topic_top_quartile_random_excerpts.xlsx")
out_df.to_excel(output_path, index=False)

print(f"Exported {len(out_df)} rows to {output_path}")
print("Preview:")
print(out_df.head(10)[["Topic Name", "Parent Code", "doc_id", "Topic Prevalence", "Excerpt"]].to_string(index=False))
# %%
