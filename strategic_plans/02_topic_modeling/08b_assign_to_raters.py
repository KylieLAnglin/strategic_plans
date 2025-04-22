# %%
import numpy as np
import pandas as pd
from library import start

models = pd.read_csv(start.DATA_DIR + "clean/sample_models_coherence_update.csv")
len(models)

# %%
docs = pd.read_csv(start.PATH + "data/clean/sample_documents_final.csv")
docs = docs.head(9)
# assign first three docs to K, next three to J, remaining to C
docs["coder"] = np.where(docs.index < 3, "K", "J")
docs["coder"] = np.where(docs.index > 5, "C", docs["coder"])
docs.coder.value_counts()
# %%
# assign first 17 models to K, next 17 to J, remaining to C
# %%
df = pd.read_excel(
    start.DATA_DIR + "clean/sample_doc_topic_prevalence_with_words_update.xlsx"
)
df = df.merge(docs[["district", "coder"]], on="district")

# %%
sort_columns = [
    "document_order",
    "model_id",
    "prevalence",
    "topic_number",
]
df = df.sort_values(by=sort_columns, ascending=False)
# %%
k_df = df[df["coder"] == "K"]
j_df = df[df["coder"] == "J"]
c_df = df[df["coder"] == "C"]

k_df.to_excel(
    start.DATA_DIR + "clean/sample_doc_topic_prevalence_with_words_K_update.xlsx",
    index=False,
)
j_df.to_excel(
    start.DATA_DIR + "clean/sample_doc_topic_prevalence_with_words_J_update.xlsx",
    index=False,
)
c_df.to_excel(
    start.DATA_DIR + "clean/sample_doc_topic_prevalence_with_words_C_update.xlsx",
    index=False,
)
