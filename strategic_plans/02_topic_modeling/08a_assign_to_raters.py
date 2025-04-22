# %%
import numpy as np
import pandas as pd
from library import start

models = pd.read_csv(start.DATA_DIR + "clean/sample_models_coherence.csv")

# assign first 17 models to K, next 17 to J, remaining to C
models["coder"] = np.where(models.index < 17, "K", "J")
models["coder"] = np.where(models.index > 33, "C", models["coder"])
models.coder.value_counts()
# %%
df = pd.read_excel(start.DATA_DIR + "clean/sample_doc_topic_prevalence_with_words.xlsx")
df = df.merge(models[["model_id", "coder"]], on="model_id")

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
    start.DATA_DIR + "clean/sample_doc_topic_prevalence_with_words_K.xlsx", index=False
)
j_df.to_excel(
    start.DATA_DIR + "clean/sample_doc_topic_prevalence_with_words_J.xlsx", index=False
)
c_df.to_excel(
    start.DATA_DIR + "clean/sample_doc_topic_prevalence_with_words_C.xlsx", index=False
)
