# %%
import os
import re
import numpy as np
import pandas as pd
from tqdm import tqdm

from strategic_plans.library import start

# ------------------ SETUP ------------------

CSV_PATH = start.DATA_DIR + "raw/strategic_plan_csvs/"
META_DATA_PATH = start.DATA_DIR + "/clean/meta_data_df.csv"

EXPORT_DOCUMENTS_PATH = start.DATA_DIR + "clean/documents_df.csv"
EXPORT_PAGES_TO_CHECK_PATH = start.MAIN_DIR + "pages_to_check.xlsx"
EXPORT_FULL_META_DATA_PATH = start.MAIN_DIR + "data/clean/plans_meta_data_full.csv"

# %%
# ------------------ LOAD DATA ------------------

meta_data_df = pd.read_csv(META_DATA_PATH)
# meta_data_df = pd.read_csv('/Users/kylie.anglin/Library/CloudStorage/OneDrive-UniversityofConnecticut/strategic_plans/data copy/clean/meta_data_df.csv')
# %%
filenames = os.listdir(CSV_PATH)
filenames = [filename for filename in filenames if filename.endswith(".csv")]
print(f'Number of CSV files: {len(filenames)}')

# %%
# ------------------ COLLAPSE EACH DOCUMENT TO ONE ROW ------------------

files = []
for filename in tqdm(filenames):
    temp_df = pd.read_csv(CSV_PATH + filename, header=0, sep="|")
    temp_df["text"] = temp_df["text"].fillna(" ")
    temp_df["leaid"] = temp_df["district"].fillna(value=0)
    temp_df["pages"] = temp_df["page"].max() + 1
    temp_df["text"] = temp_df["text"].astype(str)
    temp_df = (
        temp_df.groupby(["district", "pages", "ocr"])["text"]
        .apply(" ".join)
        .reset_index()
    )
    temp_df["filename"] = filename
    files.append(temp_df)

# %%
doc_df = pd.concat(files, axis=0, ignore_index=True)

# %%
print(len(files))
print(doc_df.filename.nunique())

# %%
one_row_per_doc = doc_df[["district", "ocr"]].drop_duplicates()

# %%
# ------------------ FLAG FAILED PARSES ------------------

doc_df["contains_alphanumeric"] = [
    bool(re.search(r"\w", text)) for text in doc_df["text"]
]
doc_df["failed_parse"] = np.where(doc_df.contains_alphanumeric == 0, 1, 0)

# %%
# ------------------ EXPORT DOCUMENTS ------------------

doc_df.to_csv(EXPORT_DOCUMENTS_PATH, sep="|", index=False)

check_pages = doc_df.sort_values(by="pages", ascending=False)
check_pages[["district", "pages"]].to_excel(EXPORT_PAGES_TO_CHECK_PATH, index=False)

doc_df = doc_df.drop(columns=["contains_alphanumeric"])

# %%
# ------------------ MERGE WITH META-DATA ------------------

big_meta_df = meta_data_df.drop(columns="district").merge(
    doc_df,
    left_on="revised_name",
    right_on="district",
    how="left",
    indicator="_merge_meta",
)


# %%
# ------------------ EXPORT ------------------

big_meta_df.to_csv(EXPORT_FULL_META_DATA_PATH)

print(f"Saved: {EXPORT_DOCUMENTS_PATH}")
print(f"Saved: {EXPORT_PAGES_TO_CHECK_PATH}")
print(f"Saved: {EXPORT_FULL_META_DATA_PATH}")

# %%
