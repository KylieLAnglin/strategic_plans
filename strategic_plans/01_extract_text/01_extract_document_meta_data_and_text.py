# %%
import os
import re
import random
import pandas as pd
import numpy as np
from tqdm import tqdm
import layoutparser as lp
import string

from strategic_plans.library import start
from strategic_plans.library import parse_pdfs

PRINTABLE = set(string.printable)
CSV_PATH = start.DATA_DIR + "raw/strategic_plan_csvs/"

## pip install layoutparser # Install the base layoutparser library with
# pip install "layoutparser[layoutmodels]" # Install DL layout model toolkit
# pip install "layoutparser[ocr]" # Install OCR toolkit
# conda install -c conda-forge poppler

# %%

DOWNLOAD_PATH = start.MAIN_DIR + "final_pdfs/"
sample_df = pd.read_excel(start.DATA_DIR + "sample_inclusion.xlsx")

# %% Create dataset of document meta-data from pdf downloads
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


# %% Get list of completed documents
list_completed_documents = [
    f.name.replace(".csv", "") for f in os.scandir(CSV_PATH) if f.name.endswith(".csv")
]
meta_data_df["document_csv_created"] = np.where(
    meta_data_df.district.isin(list_completed_documents), 1, 0
)

# %%
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
df = df.drop(
    columns=[
        "pdf_downloaded",
        "need_to_qual",
        "uploaded_dedoose",
        "_merge",
        "note",
        "Unnamed: 20",
        "Unnamed: 21",
    ]
)
df.to_csv(start.DATA_DIR + "clean/meta_data_df.csv", index=False)
# %%
