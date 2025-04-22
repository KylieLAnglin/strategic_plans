# %%
import pandas as pd
from library import start

# %%
docs = pd.read_csv(start.PATH + "data/clean/documents_df.csv", delimiter="|")
docs = docs[["district", "pages", "ocr"]]
sample_docs = docs.sample(25, random_state=12)

sample_docs.to_csv(start.PATH + "data/clean/sample_documents.csv", index=False)
# %%

final_docs = pd.read_excel(start.PATH + "data/clean/sample_documents_final.xlsx")
final_docs = final_docs[final_docs["keep"] == 1]
final_docs = final_docs.head(10)
final_docs["document_order"] = final_docs.index + 1
final_docs = final_docs[["district", "pages", "document_order"]]
final_docs.to_csv(start.PATH + "data/clean/sample_documents_final.csv", index=False)

# %%
