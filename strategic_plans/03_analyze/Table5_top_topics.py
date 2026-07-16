# %%
import pandas as pd
import numpy as np
from strategic_plans.library import start

# ------------------ Load inputs ------------------
# Topic naming (with human labels, parent codes, and top words)
topic_naming_path = start.DATA_DIR + 'final_model/topic_naming_named.xlsx'
topic_naming_df = pd.read_excel(topic_naming_path)

# Rename word columns 0..9 -> Word 1..10 and the id column
word_cols_raw = [i for i in range(10)]
topic_naming_df = topic_naming_df.rename(columns={c: f'Word {i+1}' for i, c in enumerate(word_cols_raw)})
topic_naming_df = topic_naming_df.rename(columns={'Unnamed: 0': 'topic_id'})  # e.g., "Topic_0"

# Document-topic prevalence (grouped by district/plan)
doc_topics_path = start.DATA_DIR + 'final_model/topic_model/doc_topics_grouped.xlsx'
doc_topics_df = pd.read_excel(doc_topics_path)

# The topic columns arrive as strings "0".."22"; rename to "Topic 0".."Topic 22" to align to naming (with a space)
topic_cols = [str(i) for i in range(23)]  # adjust if your model has a different # of topics
doc_topics_df = doc_topics_df.rename(columns={c: f"Topic {int(c)}" for c in topic_cols})

# ------------------ Identify included topics ------------------
# Topic curation (inclusion, merges) is chosen in the ContentCoder app and
# lands here through its topics export (contentcoder/export_topics.py)
assert {'include_in_analysis', 'merged_into'} <= set(topic_naming_df.columns), (
    "topic_naming_named.xlsx predates the app's topics export; "
    "run contentcoder/export_topics.py to regenerate it"
)

# topic_naming_df['topic_id'] uses underscores: "Topic_0". Convert to space-form to match doc_topics_df columns.
topic_naming_df['topic_id_space'] = topic_naming_df['topic_id'].str.replace("_", " ", regex=False)

# Fold merged topics into their canonical topic (prevalences sum) and drop the
# source columns so nothing below can use pre-merge values
merged_topics_meta = topic_naming_df[
    topic_naming_df['merged_into'].notna() & (topic_naming_df['merged_into'] != '')
]
for _, merged_topic in merged_topics_meta.iterrows():
    target_col = merged_topic['merged_into'].replace("_", " ")
    source_col = merged_topic['topic_id_space']
    doc_topics_df[target_col] = doc_topics_df[target_col] + doc_topics_df[source_col]
    doc_topics_df = doc_topics_df.drop(columns=[source_col])

included_topics_meta = topic_naming_df[
    (topic_naming_df['include_in_analysis'] == 1)
    & ~topic_naming_df['topic_id'].isin(merged_topics_meta['topic_id'])
].copy()

# Keep only topics present in doc_topics_df
included_topic_cols = [t for t in included_topics_meta['topic_id_space'].tolist() if t in doc_topics_df.columns]

# ------------------ Row-normalize to proportion of INCLUDED topics ------------------
# For each row/document, compute the sum across included topics, then divide each included topic by that sum.
# This yields per-row proportions that sum to 1 over INCLUDED topics (rows with zero-sum become NaN).
included_values = doc_topics_df[included_topic_cols].apply(pd.to_numeric, errors='coerce')
row_sums = included_values.sum(axis=1)

# Avoid division by zero: where sum==0, keep NaNs
normalized = included_values.div(row_sums.replace(0, np.nan), axis=0)

# ------------------ Aggregate normalized prevalence per topic ------------------
# Compute mean, 25th percentile, and 75th percentile of normalized prevalence across documents.
topic_summary = []
for col in included_topic_cols:
    col_series = pd.to_numeric(normalized[col], errors='coerce').dropna()
    if col_series.empty:
        avg = p25 = p75 = np.nan
    else:
        avg = col_series.mean()
        p25 = col_series.quantile(0.25)
        p75 = col_series.quantile(0.75)

    # Convert back to underscore id to merge with naming
    topic_id_under = col.replace(" ", "_")
    topic_summary.append({
        'topic_id': topic_id_under,
        'avg_norm_prevalence': avg,
        'p25_norm_prevalence': p25,
        'p75_norm_prevalence': p75
    })

summary_df = pd.DataFrame(topic_summary)

# ------------------ Merge with names / codes / words ------------------
table_df = summary_df.merge(topic_naming_df, on='topic_id', how='left')

# Filter again for safety (keep only included topics)
table_df = table_df[table_df['topic_id'].isin(included_topics_meta['topic_id'])]

# Sort by decreasing normalized average prevalence
table_df = table_df.sort_values('avg_norm_prevalence', ascending=False)

# Columns to include in the final table
word_cols = [f'Word {i+1}' for i in range(10)]
available_word_cols = [c for c in word_cols if c in table_df.columns]

final_cols = (
    ['topic_id', 'code', 'parent_code',
     'avg_norm_prevalence', 'p25_norm_prevalence', 'p75_norm_prevalence']
    + available_word_cols
)
final_table = table_df[final_cols].copy()

# Nicely rename for output
final_table = final_table.rename(columns={
    'topic_id': 'Topic ID',
    'code': 'Topic Code',
    'parent_code': 'Parent Code',
    'avg_norm_prevalence': 'Average Normalized Prevalence',
    'p25_norm_prevalence': '25th Percentile (Normalized)',
    'p75_norm_prevalence': '75th Percentile (Normalized)',
})

# Optional: round to two decimals (keep as proportions 0–1; use *100 if you prefer percentages)
for c in ['Average Normalized Prevalence', '25th Percentile (Normalized)', '75th Percentile (Normalized)']:
    final_table[c] = final_table[c].round(4)

# ------------------ Export ------------------
output_path = start.RESULTS_DIR + 'top_topics_normalized_to_included.xlsx'
final_table.to_excel(output_path, index=False)

print(f"Exported normalized table to {output_path}")
print(f"Included topics: {len(included_topic_cols)} / total topics in file: {len(doc_topics_df.columns)}")
print(final_table.head(10)[['Topic Code', 'Average Normalized Prevalence',
                            '25th Percentile (Normalized)', '75th Percentile (Normalized)']].to_string(index=False))