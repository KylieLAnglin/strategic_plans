# %%
import pandas as pd
import numpy as np
from strategic_plans.library import start

# %%
# Load topic naming data with codes
topic_naming_path = start.DATA_DIR + 'final_model/topic_naming_named.xlsx'
topic_naming_df = pd.read_excel(topic_naming_path)
# rename 0-9 columns to Word 1-10
word_cols = [i for i in range(10)]  # Word columns are simply '0' through '9'
rename_dict = {col: f'Word {i+1}' for i, col in enumerate(word_cols)}
topic_naming_df = topic_naming_df.rename(columns=rename_dict)
topic_naming_df = topic_naming_df.rename(columns={'Unnamed: 0': 'topic_id'})

# Load document-topic prevalence data (grouped by district/strategic plan)
doc_topics_path = start.DATA_DIR + 'final_model/topic_model/doc_topics_grouped.xlsx'
doc_topics_df = pd.read_excel(doc_topics_path)
# rename 0-22 columns to Topic 1-23
topic_cols = [str(i) for i in range(23)]  # Assuming topics are numbered 0-22
rename_dict = {col: f'Topic {int(col)}' for col in topic_cols}
doc_topics_df = doc_topics_df.rename(columns=rename_dict)
# %%
# Calculate average prevalence for each topic across all documents
topic_prevalence = []

for topic_id in topic_naming_df['topic_id']:
    topic_id = topic_id.replace("_", " ")
    avg_prevalence = doc_topics_df[topic_id].mean()
    topic_prevalence.append({
        'topic_id': topic_id.replace(" ", "_"),
        'avg_prevalence': avg_prevalence
    })

prevalence_df = pd.DataFrame(topic_prevalence)

# %%
# Merge with topic naming data
table_df = prevalence_df.merge(topic_naming_df, left_on='topic_id', right_on='topic_id', how='left')

# Filter out excluded parent codes
excluded_parent_codes = ["Uninterpretable", "Document Details"]
table_df = table_df[~table_df['parent_code'].isin(excluded_parent_codes)]

# Sort by decreasing prevalence
table_df = table_df.sort_values('avg_prevalence', ascending=False)

# Select and rename columns for final table (including top 10 words)
word_cols = [f'Word {i+1}' for i in range(10)]  # Word columns are now named 'Word 1' through 'Word 10'
available_word_cols = [col for col in word_cols if col in table_df.columns]

columns_to_include = ['topic_id', 'code', 'parent_code', 'avg_prevalence'] + available_word_cols
final_table = table_df[columns_to_include].copy()

# Create rename dictionary
rename_dict = {
    'topic_id': 'Topic ID',
    'code': 'Topic Code', 
    'avg_prevalence': 'Average Prevalence',
    'parent_code': 'Parent Code'
}

# Word columns are already properly named, so no need to rename them
final_table = final_table.rename(columns=rename_dict)

# Round Average Prevalence to two decimal places
final_table['Average Prevalence'] = final_table['Average Prevalence'].round(2)

# %%
# Export table
output_path = start.RESULTS_DIR + 'top_topics.xlsx'
final_table.to_excel(output_path, index=False)

print(f"Table 5 exported to {output_path}")
print(f"Number of topics included: {len(final_table)}")
print(f"Top 5 topics by prevalence:")
print(final_table.head()[['Topic Code', 'Average Prevalence']].to_string(index=False))