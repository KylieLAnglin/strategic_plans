# %%
import pandas as pd
import numpy as np
from strategic_plans.library import start

# %%
# Load topic naming data with codes
topic_naming_path = start.DATA_DIR + 'final_model/topic_naming_named.xlsx'
topic_naming_df = pd.read_excel(topic_naming_path)

# rename 0-9 columns to Word 1-10
word_cols = [i for i in range(10)]
rename_dict = {col: f'Word {i+1}' for i, col in enumerate(word_cols)}
topic_naming_df = topic_naming_df.rename(columns=rename_dict)
topic_naming_df = topic_naming_df.rename(columns={'Unnamed: 0': 'topic_id'})

# Load document-topic prevalence data (grouped by district/strategic plan)
doc_topics_path = start.DATA_DIR + 'final_model/topic_model/doc_topics_grouped.xlsx'
doc_topics_df = pd.read_excel(doc_topics_path)

# rename 0-22 columns to Topic 0-22
topic_cols = [str(i) for i in range(23)]
rename_dict = {col: f'Topic {int(col)}' for col in topic_cols}
doc_topics_df = doc_topics_df.rename(columns=rename_dict)

# %%
# Calculate average prevalence, 25th percentile, and 75th percentile
topic_prevalence = []

for topic_id in topic_naming_df['topic_id']:
    topic_id_space = topic_id.replace("_", " ")
    if topic_id_space not in doc_topics_df.columns:
        continue

    col = pd.to_numeric(doc_topics_df[topic_id_space], errors='coerce').dropna()

    avg_prevalence = col.mean()
    p25_prevalence = col.quantile(0.25)
    p75_prevalence = col.quantile(0.75)

    topic_prevalence.append({
        'topic_id': topic_id_space.replace(" ", "_"),
        'avg_prevalence': avg_prevalence,
        'p25_prevalence': p25_prevalence,
        'p75_prevalence': p75_prevalence
    })

prevalence_df = pd.DataFrame(topic_prevalence)

# %%
# Merge with topic naming data
table_df = prevalence_df.merge(topic_naming_df, on='topic_id', how='left')

# Filter out excluded parent codes
excluded_parent_codes = ["Uninterpretable", "Document Details"]
table_df = table_df[~table_df['parent_code'].isin(excluded_parent_codes)]

# Sort by decreasing prevalence
table_df = table_df.sort_values('avg_prevalence', ascending=False)

# Select and rename columns for final table
word_cols = [f'Word {i+1}' for i in range(10)]
available_word_cols = [col for col in word_cols if col in table_df.columns]

columns_to_include = [
    'topic_id', 'code', 'parent_code',
    'avg_prevalence', 'p25_prevalence', 'p75_prevalence'
] + available_word_cols

final_table = table_df[columns_to_include].copy()

rename_dict = {
    'topic_id': 'Topic ID',
    'code': 'Topic Code',
    'parent_code': 'Parent Code',
    'avg_prevalence': 'Average Prevalence',
    'p25_prevalence': '25th Percentile',
    'p75_prevalence': '75th Percentile'
}
final_table = final_table.rename(columns=rename_dict)

# Round numeric columns
for col in ['Average Prevalence', '25th Percentile', '75th Percentile']:
    final_table[col] = final_table[col].round(2)

# %%
# Export table
output_path = start.RESULTS_DIR + 'top_topics.xlsx'
final_table.to_excel(output_path, index=False)

print(f"Table 5 exported to {output_path}")
print(f"Number of topics included: {len(final_table)}")
print("Top 5 topics by prevalence (with 25th/75th percentiles):")
print(final_table.head()[['Topic Code', 'Average Prevalence', '25th Percentile', '75th Percentile']].to_string(index=False))
# %%
