new_terms = []
for term in old_terms:
	new_term = term.str.replace(" ", "_")
	new_terms.append(new_term)


# must have removed punctuation (replace with " ") and lower cased
for old, new in zip(old_terms, new_terms):
	df["text_clean"] = df.text.str.replace(old_term, new_term)
