# %%
import pandas as pd
from school_boards.library import start

# %%
doc_df = pd.read_csv(start.DATA_DIR + "clean/documents_df.csv", sep="|")
doc_df.text_clean = doc_df.text_clean.fillna("")

# %%
nan_docs = []
for document_id, text in zip(doc_df.document_id, doc_df.text_clean):
    with open(
        start.DATA_DIR + "raw/minutes_txts/" + document_id + ".txt", "w+"
    ) as text_file:
        text_file.write(text)
    if " nan " in text:
        nan_docs.append(document_id)
