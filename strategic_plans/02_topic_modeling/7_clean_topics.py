# %%
import pandas as pd
import os
from strategic_plans.library import start

# %%
topics_path = start.DATA_DIR + 'final_model/topic_model/topics.csv'
output_path = start.DATA_DIR + 'final_model/topic_naming.xlsx'
doc_topics_path = start.DATA_DIR + 'final_model/topic_model/doc_topics.csv'
docs_path = start.DATA_DIR + 'final_model/final_token_dfs_w_chunks.pkl'
# %%
topics_df = pd.read_csv(topics_path)
word_cols = [col for col in topics_df.columns if col.startswith('Word_')]
topics_df = topics_df[word_cols]
topics_df = topics_df.rename(columns=lambda x: x.replace('Word_', 'Topic_'))
topics_df = topics_df.head(10) # Limit to first 10 words
rename_df = topics_df.T
# %%
rename_df.to_excel(output_path, index=True)

print(f"Topics exported to {output_path}")

# %%
# Find top 5 documents with highest Topic 20 prevalence
print("\n=== Top 5 Documents for Topic 20 ===")

# Load document-topic data
doc_topics_df = pd.read_csv(doc_topics_path)

# Load token data with document text
docs_df = pd.read_pickle(docs_path)
# %%
# Find top 5 documents with highest Topic XX prevalence
TOPIC = '1'

top_topic_docs = doc_topics_df.nlargest(20, TOPIC)[['doc_id', TOPIC]]

print(f"Top 5 documents with highest Topic {TOPIC} prevalence:")
for idx, row in top_topic_docs.iterrows():
    doc_id = row['doc_id']
    prevalence = row[TOPIC]
    # Find matching document in token data
    matching_doc = docs_df[docs_df['doc_id'] == doc_id]
    if not matching_doc.empty:
        doc_text = matching_doc.iloc[0]['text']
        print(f"\nDoc ID: {doc_id}")
        print(f"Topic Prevalence: {prevalence:.4f}")
        print(f"Text Preview: {doc_text[:200]}...")
    else:
        print(f"\nDoc ID: {doc_id} (text not found)")
        print(f"Topic {TOPIC} Prevalence: {prevalence:.4f}")


# %%
