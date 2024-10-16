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

## pip install layoutparser # Install the base layoutparser library with
# pip install "layoutparser[layoutmodels]" # Install DL layout model toolkit
# pip install "layoutparser[ocr]" # Install OCR toolkit
# conda install -c conda-forge poppler

DOWNLOAD_PATH = start.MAIN_DIR + "downloaded_pdfs/"
CSV_PATH = start.DATA_DIR + "raw/strategic_plan_csvs/"

# %%
list_documents = [f.name for f in os.scandir(DOWNLOAD_PATH)]

# %% Create dataset of document meta-data

documents = []
for document in list_documents:
    new_document = {}
    new_document["original_document_name"] = document
    try:
        new_document["district"] = document.split("_")[0]
        new_document["year"] = document.split("_")[1].split(".")[0]
    except:
        new_document["district"] = document.split(".")[0]
        new_document["year"] = "Unknown"
    documents.append(new_document)
meta_data_df = pd.DataFrame(documents)

# %% Identify document types
meta_data_df["file_type"] = meta_data_df.original_document_name.str[-4:]

meta_data_df = meta_data_df[
    meta_data_df.file_type.isin([".pdf", ".doc", "docx", ".rtf", ".png"])
]

meta_data_df["filepath"] = DOWNLOAD_PATH + meta_data_df.original_document_name


# %% Get list of completed documents
list_completed_documents = [
    f.name.replace(".csv", "") for f in os.scandir(CSV_PATH) if f.name.endswith(".csv")
]
meta_data_df["document_csv_created"] = np.where(
    meta_data_df.district.isin(list_completed_documents), 1, 0
)

# %% Only extract new documents (and/or sample)
docs_to_extract = meta_data_df[meta_data_df.document_csv_created == 0]

# %%
meta_data_dict = docs_to_extract.to_dict("records")
# %%

meta_data_df.to_csv(start.DATA_DIR + "clean/meta_data_df.csv")
# %%

for document in tqdm(meta_data_dict):
    doc_df = parse_pdfs.generate_pdf_df(document["filepath"])
    doc_df["district"] = document["district"]
    doc_df["original_document_name"] = document["original_document_name"]

    columns_to_move = [
        "district",
        "original_document_name",
    ]
    doc_df = doc_df[
        columns_to_move + [col for col in doc_df.columns if col not in columns_to_move]
    ]

    doc_df.text = doc_df.text.fillna("")

    # remove extra white space
    doc_df["text"] = [text.strip() for text in doc_df.text]
    doc_df["text"] = [text.replace("\t", "") for text in doc_df.text]

    # remove non ascii characters
    doc_df["text"] = [
        "".join(filter(lambda x: x in PRINTABLE, text)) for text in doc_df.text
    ]

    doc_df["text"] = [
        text.encode(encoding="ascii", errors="ignore").decode() for text in doc_df.text
    ]

    # remove | - it serves as our separator
    doc_df["text"] = [text.replace("|", " ") for text in doc_df.text]

    doc_df.to_csv(
        CSV_PATH + document["district"] + ".csv",
        sep="|",
        encoding="ascii",
        index=False,
    )

# %%

# %%
