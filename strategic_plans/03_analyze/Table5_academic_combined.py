# %%
import pandas as pd
import numpy as np
from strategic_plans.library import start

# ------------------ Load inputs ------------------
topic_naming_path = start.DATA_DIR + 'final_model/topic_naming_named.xlsx'
topic_naming_df = pd.read_excel(topic_naming_path)

# Rename word columns 0..9 -> Word 1..10 and the id column
word_cols_raw = [i for i in range(10)]
topic_naming_df = topic_naming_df.rename(columns={c: f'Word {i+1}' for i, c in enumerate(word_cols_raw)})
topic_naming_df = topic_naming_df.rename(columns={'Unnamed: 0': 'topic_id'})

# Document-topic prevalence (grouped by district/plan)
doc_topics_path = start.DATA_DIR + 'final_model/topic_model/doc_topics_grouped.xlsx'
doc_topics_df = pd.read_excel(doc_topics_path)

# Rename topic columns
topic_cols = [str(i) for i in range(23)]
doc_topics_df = doc_topics_df.rename(columns={c: f"Topic {int(c)}" for c in topic_cols})

# ------------------ Identify included topics ------------------
excluded_parent_codes = {"Uninterpretable", "Document Details"}
topic_naming_df['topic_id_space'] = topic_naming_df['topic_id'].str.replace("_", " ", regex=False)
included_topics_meta = topic_naming_df[~topic_naming_df['parent_code'].isin(excluded_parent_codes)].copy()
included_topic_cols = [t for t in included_topics_meta['topic_id_space'].tolist() if t in doc_topics_df.columns]

# ------------------ Row-normalize to proportion of INCLUDED topics ------------------
included_values = doc_topics_df[included_topic_cols].apply(pd.to_numeric, errors='coerce')
row_sums = included_values.sum(axis=1)
normalized = included_values.div(row_sums.replace(0, np.nan), axis=0)

# ------------------ Create Academic Achievement combined topic ------------------
# Add combined academic achievement (Topic 9 + Topic 16)
normalized['Academic Achievement'] = normalized['Topic 9'] + normalized['Topic 16']

# Calculate prevalence statistics for Academic Achievement
academic_series = normalized['Academic Achievement'].dropna()
academic_stats = {
    'topic_id': 'Academic_Achievement',
    'avg_norm_prevalence': academic_series.mean(),
    'p25_norm_prevalence': academic_series.quantile(0.25),
    'p75_norm_prevalence': academic_series.quantile(0.75)
}

# Get individual topic stats for Topic 9 and Topic 16 for word display
topic_9_meta = topic_naming_df[topic_naming_df['topic_id'] == 'Topic_9'].iloc[0]
topic_16_meta = topic_naming_df[topic_naming_df['topic_id'] == 'Topic_16'].iloc[0]

# Create combined words (first 5 from each topic)
word_cols = [f'Word {i+1}' for i in range(10)]
topic_9_words = [topic_9_meta[col] for col in word_cols[:5] if col in topic_9_meta]
topic_16_words = [topic_16_meta[col] for col in word_cols[:5] if col in topic_16_meta]

# Create final table
final_table = pd.DataFrame({
    'Topic ID': ['Academic_Achievement'],
    'Topic Code': ['Academic Achievement (Topic 9 + Topic 16)'],
    'Parent Code': ['Academic'],
    'Average Normalized Prevalence': [academic_stats['avg_norm_prevalence']],
    '25th Percentile (Normalized)': [academic_stats['p25_norm_prevalence']],
    '75th Percentile (Normalized)': [academic_stats['p75_norm_prevalence']],
    'Topic 9 Code': [topic_9_meta['code']],
    'Topic 16 Code': [topic_16_meta['code']]
})

# Add word columns
for i, word in enumerate(topic_9_words + topic_16_words, 1):
    final_table[f'Word {i}'] = word

# Round numeric columns
for col in ['Average Normalized Prevalence', '25th Percentile (Normalized)', '75th Percentile (Normalized)']:
    final_table[col] = final_table[col].round(4)

# ------------------ Export ------------------
output_path = start.RESULTS_DIR + 'top_topics_one_academic.xlsx'
final_table.to_excel(output_path, index=False)

print(f"Exported academic achievement stats to {output_path}")
print(f"Average normalized prevalence: {academic_stats['avg_norm_prevalence']:.4f}")
print(f"25th percentile: {academic_stats['p25_norm_prevalence']:.4f}")
print(f"75th percentile: {academic_stats['p75_norm_prevalence']:.4f}")
print(f"Individual topics combined:")
print(f"  Topic 9: {topic_9_meta['code']}")
print(f"  Topic 16: {topic_16_meta['code']}")