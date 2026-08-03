# %%
import string
import pandas as pd
from tqdm import tqdm

from strategic_plans.library import start
from strategic_plans.library import parse_pdfs

# ------------------ SETUP ------------------

# pip install layoutparser # Install the base layoutparser library
# pip install "layoutparser[layoutmodels]" # Install DL layout model toolkit
# pip install "layoutparser[ocr]" # Install OCR toolkit
# conda install -c conda-forge poppler

DOWNLOAD_PATH = start.MAIN_DIR + "downloaded_pdfs/"
CSV_PATH = start.DATA_DIR + "raw/strategic_plan_csvs/"
META_DATA_PATH = start.DATA_DIR + "clean/meta_data_df.csv"

PRINTABLE = set(string.printable)

# %%
# ------------------ LOAD DATA ------------------

meta_data_df = pd.read_csv(META_DATA_PATH)

# %%
# ------------------ EXTRACT TEXT TO CSV ------------------

docs_to_extract = meta_data_df[(meta_data_df.document_csv_created == 0)]
meta_data_dict = docs_to_extract.to_dict("records")

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

    # remove | because itserves as our separator
    doc_df["text"] = [text.replace("|", " ") for text in doc_df.text]

    doc_df.to_csv(
        CSV_PATH + document["district"] + ".csv",
        sep="|",
        encoding="ascii",
        index=False,
    )

print(f"Saved {len(meta_data_dict)} document CSVs to: {CSV_PATH}")

# %%
