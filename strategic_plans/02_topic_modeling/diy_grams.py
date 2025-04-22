# %%
import pandas as pd

# %%

j_bgrams = pd.read_excel("diy_ngram_list_clean.xlsx")
# Convert the relevant column (e.g., 'diy_ngrams') to a Python list
diy_bigrams = j_bgrams["diy_ngrams"].dropna().tolist()  # Drop any empty row
diy_bigrams


diy_bigrams = [
    str(bigram).strip().replace(" ", "_")
    for bigram in diy_bigrams
    if isinstance(bigram, str)
]

print(diy_bigrams)

old_terms = [
    bigram.replace("_", " ") for bigram in diy_bigrams
]  # Convert underscores to spaces
new_terms = diy_bigrams


def add_grams(text):
    for old_term, new_term in zip(old_terms, new_terms):
        text = text.replace(old_term, new_term)  # Perform the replacement on the string
    return text
