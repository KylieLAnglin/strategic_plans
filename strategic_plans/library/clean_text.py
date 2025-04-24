# %%
import re
import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from nltk.stem.wordnet import WordNetLemmatizer
from sklearn.feature_extraction.text import CountVectorizer
from gensim.models import Phrases
from gensim.models.phrases import Phraser, ENGLISH_CONNECTOR_WORDS

# Initialize the lemmatizer
lemmatizer = WordNetLemmatizer()


def basic_clean(
    text,
    remove_urls=True,
    remove_unusual=True,
    remove_numbers=True,
    remove_single_letters=True,
    remove_months=True,
):
    text = text.lower()

    if remove_urls:
        text = re.sub(r"http\S+", "", text)
        text = re.sub(r"www\S+", "", text)

    text = re.sub(r"[^\w\s]", " ", text)  # remove punctuation

    tokens = word_tokenize(text)

    # Remove if not token with alphabetic characters only
    if remove_unusual:
        tokens = [word for word in tokens if re.match("^[A-Za-z]+$", word)]

    if remove_numbers:
        tokens = [word for word in tokens if not word.isdigit()]

    if remove_single_letters:
        tokens = [token for token in tokens if len(token) > 1 or token == "a"]

    if remove_months:
        months = {
            "january",
            "february",
            "march",
            "april",
            "may",
            "june",
            "july",
            "august",
            "september",
            "october",
            "november",
            "december",
            "jan",
            "feb",
            "mar",
            "apr",
            "jun",
            "jul",
            "aug",
            "sep",
            "oct",
            "nov",
            "dec",
        }
        tokens = [token for token in tokens if token not in months]

    string = " ".join(tokens)
    return string


def get_token_list(text_col, min_df):
    print("Getting tokens list")
    vectorizer = CountVectorizer(min_df=int(min_df))
    X = vectorizer.fit_transform(text_col)
    tokens = vectorizer.get_feature_names_out()
    print(f"Number of tokens: {len(tokens)}")
    return tokens


def apply_remove_infrequent_tokens(df, text_col, token_list):
    df[text_col] = df[text_col].apply(
        lambda text: remove_infrequent_tokens(text, token_list)
    )
    return df


def remove_infrequent_tokens(text, token_list):
    token_set = set(token_list)
    tokens = word_tokenize(text)
    tokens = [word for word in tokens if word in token_set]
    return " ".join(tokens)


def remove_stopwords(text, languages=("english",), custom_stopwords=None):
    stop_words = set()
    for lang in languages:
        stop_words = stop_words.union(set(stopwords.words(lang)))
    if custom_stopwords:
        stop_words = stop_words.union(custom_stopwords)
    tokens = word_tokenize(text)
    tokens = [word for word in tokens if word not in stop_words]
    return " ".join(tokens)


def lemmatize_text(text):
    tokens = word_tokenize(text)
    tokens = [lemmatizer.lemmatize(word) for word in tokens]
    return " ".join(tokens)


# def clean_text(
#     text,
#     remove_stopwords=False,
#     languages=("english",),  # Tuple of languages to handle
#     combine_month_year=True,
#     custom_stopwords=None,
#     remove_numbers=True,
#     remove_unusual=True,
#     remove_single_letters=True,
#     lemmatize=False,
#     remove_months=False,
#     remove_urls=True,
#     remove_repeated_characters=False,
#     apply_min_df=False,  # Whether to filter tokens by document frequency
#     min_df=1,  # Minimum document frequency as a proportion or absolute count
#     token_doc_counts=None,  # A dictionary to store token document frequencies
# ):
#     """
#     Clean and tokenize text into words, with optional removal of stopwords (English, Spanish, etc.),
#     numeric tokens, unusual words, and single-letter tokens.

#     Args:
#         text (str): The input text to be cleaned and tokenized.
#         remove_stopwords (bool): Whether to remove stopwords. Default is True.
#         languages (tuple): Languages for stopwords. Default is ('english',).
#         custom_stopwords (set): Optional set of custom stopwords to remove.
#         remove_numbers (bool): Whether to remove numeric tokens. Default is True.
#         remove_unusual (bool): Whether to remove unusual words. Default is True.
#         remove_single_letters (bool): Whether to remove single-letter tokens. Default is True.

#     Returns:
#         list: A list of cleaned and tokenized words.
#     """
#     # Step 1: Lowercase the text
#     text = text.lower()

#     # Step 2: Remove punctuation and special characters
#     text = re.sub(r"[^\w\s]", "", text)

#     if combine_month_year:
#         # Regular expression to match a month followed by a year
#         month_year_pattern = r"\b(january|february|march|april|may|june|july|august|september|october|november|december)\s(\d{4})\b"
#         # Replace matched patterns with the month and year combined with an underscore
#         text = re.sub(month_year_pattern, r"\1_\2", text, flags=re.IGNORECASE)

#     # Step 3: Tokenize the text
#     tokens = word_tokenize(text)

#     # Step 4: Remove stopwords (if enabled)
#     if remove_stopwords:
#         stop_words = set()
#         for lang in languages:
#             stop_words = stop_words.union(set(stopwords.words(lang)))
#         if custom_stopwords:
#             stop_words = stop_words.union(custom_stopwords)
#         tokens = [word for word in tokens if word not in stop_words]

#     # Step 5: Remove numeric tokens (if enabled)
#     if remove_numbers:
#         tokens = [word for word in tokens if not word.isdigit()]

#     # Step 6: Remove unusual words (if enabled)
#     if remove_unusual:
#         tokens = [word for word in tokens if re.match("^[A-Za-z]+$", word)]

#     # Step 7: Remove single-letter tokens (if enabled)
#     if remove_single_letters:
#         tokens = [token for token in tokens if len(token) > 2]

#     if remove_months:
#         months = {
#             "january",
#             "february",
#             "march",
#             "april",
#             "may",
#             "june",
#             "july",
#             "august",
#             "september",
#             "october",
#             "november",
#             "december",
#             "jan",
#             "feb",
#             "mar",
#             "apr",
#             "jun",
#             "jul",
#             "aug",
#             "sep",
#             "oct",
#             "nov",
#             "dec",
#         }
#         tokens = [token for token in tokens if token not in months]

#     if remove_urls:
#         tokens = [
#             token
#             for token in tokens
#             if not (token.startswith("http") or token.startswith("www"))
#         ]

#     string = " ".join(tokens)
#     return string


# %%


def generate_list_of_grams(documents_df, text_col):

    texts = documents_df[text_col].astype(str).apply(lambda x: x.split())

    bigram = Phrases(
        texts, min_count=75, threshold=30, connector_words=ENGLISH_CONNECTOR_WORDS
    )
    bigram_phraser = Phraser(bigram)

    trigram = Phrases(
        bigram[texts],
        min_count=75,
        threshold=30,
        connector_words=ENGLISH_CONNECTOR_WORDS,
    )
    trigram_phraser = Phraser(trigram)

    grams = sorted(list(trigram_phraser.phrasegrams.keys()))

    return grams


# %%
