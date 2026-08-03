# %%
import os
import pandas as pd
import numpy as np

from strategic_plans.library import start

# ------------------ SETUP ------------------

CSV_PATH = start.DATA_DIR + "raw/strategic_plan_csvs/"
DOWNLOAD_PATH = start.MAIN_DIR + "final_pdfs/"
SAMPLE_INCLUSION_PATH = start.DATA_DIR + "sample_inclusion.xlsx"

EXPORT_META_DATA_PATH = start.DATA_DIR + "clean/meta_data_df.csv"

# %%
# ------------------ LOAD DATA ------------------

sample_df = pd.read_excel(SAMPLE_INCLUSION_PATH)

# %%
# ------------------ CREATE META-DATA FROM PDF DOWNLOADS ------------------

list_documents = [f.name for f in os.scandir(DOWNLOAD_PATH)]

documents = []
for document in list_documents:
    new_document = {}
    new_document["original_document_name"] = document
    new_document["district"] = document.replace(".pdf", "")
    documents.append(new_document)

meta_data_df = pd.DataFrame(documents)
meta_data_df["filepath"] = DOWNLOAD_PATH + meta_data_df.original_document_name

# %%
# ------------------ FLAG COMPLETED DOCUMENTS ------------------

list_completed_documents = [
    f.name.replace(".csv", "") for f in os.scandir(CSV_PATH) if f.name.endswith(".csv")
]
meta_data_df["document_csv_created"] = np.where(
    meta_data_df.district.isin(list_completed_documents), 1, 0
)

# %%
# ------------------ MERGE WITH SAMPLE ------------------

df = sample_df.merge(
    meta_data_df,
    left_on="revised_name",
    right_on="district",
    how="outer",
    indicator="pdf_downloaded",
)

df["pdf_downloaded"] = np.where(df.pdf_downloaded == "both", 1, 0)
df.pdf_downloaded.value_counts()
df = df[df.pdf_downloaded == 1]

# %%
# ------------------ CLEAN AND EXPORT ------------------

df = df.drop(
    columns=[
        "pdf_downloaded",
        "need_to_qual",
        "uploaded_dedoose",
        "_merge",
        "note",
    ]
)
# %%
df.to_csv(EXPORT_META_DATA_PATH, index=False)

print(f"Saved: {EXPORT_META_DATA_PATH}")

# %%
