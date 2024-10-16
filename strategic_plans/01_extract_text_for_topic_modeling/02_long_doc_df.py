# %%
import os
import numpy as np
import pandas as pd
import string
import re
from tqdm import tqdm

from strategic_plans.library import start

# %%
PATH = start.DATA_DIR + "raw/strategic_plan_csvs/"

meta_data_df = pd.read_csv(start.DATA_DIR + "clean/meta_data_df.csv")

# %%
filenames = os.listdir(PATH)
filenames = [filename for filename in filenames if filename.endswith(".csv")]
print(len(filenames))
len(set(filenames))
# %%

files = []
for filename in tqdm(filenames):
    temp_df = pd.read_csv(PATH + filename, header=0, sep="|")
    temp_df.text = temp_df.text.fillna(" ")
    temp_df.leaid = temp_df.district.fillna(value=0)
    temp_df["pages"] = temp_df.page.max() + 1
    temp_df["text"] = temp_df["text"].astype(str)
    temp_df = (
        temp_df.groupby(["district", "pages"])["text"].apply(" ".join).reset_index()
    )
    temp_df["filename"] = filename
    files.append(temp_df)

# %%
doc_df = pd.concat(files, axis=0, ignore_index=True)

# %%
print(len(files))
print(doc_df.filename.nunique())
# %%

# one_row_per_doc = doc_df[["district", "ocr"]].drop_duplicates()
# doc_df = doc_df.merge(
#     one_row_per_doc[["district", "ocr"]],
#     how="right",
#     on=["district", "ocr"],
# )
# doc_df.text = doc_df.text.fillna("")

# %%

# lower case
doc_df["text_clean"] = [text.lower() for text in doc_df.text]

# remove all punctuation
doc_df["text_clean"] = [
    text.translate(str.maketrans("", "", string.punctuation))
    for text in doc_df.text_clean
]


# create a function to check if a string contains an alphanumeric character
def contains_alphanumeric(string):
    return bool(re.search(r"\w", string))


# apply the function to the 'col1' column and create a new column 'contains_alphanumeric'
doc_df["contains_alphanumeric"] = doc_df["text"].apply(contains_alphanumeric)

doc_df["failed_parse"] = np.where(doc_df.contains_alphanumeric == 0, 1, 0)
doc_df["text_lower"] = doc_df.text_clean.str.lower()  # already did this
# %%
# doc_df = pd.read_csv(start.DATA_DIR + "clean/documents_df.csv", sep="|")
doc_df.to_csv(start.DATA_DIR + "clean/documents_df.csv", sep="|", index=False)

check_pages = doc_df.sort_values(by="pages", ascending=False)
check_pages[["district", "pages"]].to_excel(
    start.MAIN_DIR + "pages_to_check.xlsx", index=False
)

# %%
