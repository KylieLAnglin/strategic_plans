# %%
import os

import pandas as pd
import string

import gensim
from gensim.models.coherencemodel import CoherenceModel
from gensim.models.ldamodel import LdaModel
from gensim.models.hdpmodel import HdpModel
from gensim.models import Phrases
from gensim.corpora.dictionary import Dictionary
from numpy import array
from tqdm import tqdm
from library import start
from library import topic_modeling

base_path = start.PATH + "results/"

# %%
PASSES = 5
WORDS_TO_VIEW = 10
SEED = 4205

models = pd.read_csv(start.DATA_DIR + "clean/sample_models_update.csv")

# %%

# models as a list of dictionaries
models_list = models.to_dict(orient="records")

model = models_list[0]
# %%
coherences_cv = []
coherences_umass = []
for model in models_list:

    # Set model name and export location
    print(model)
    model_name = (
        "model"
        + str(model["model_id"])
        + "topic"
        + str(model["topic"])
        + "_decision"
        + str(int(model["decision_id"]))
    )
    print(model_name)
    newpath = start.RESULTS_DIR + "topic_models/" + model_name + "/"
    if not os.path.exists(newpath):
        os.makedirs(newpath)

    # Import text matching processing decision in model
    group_num = model["text_group"]
    text_df = pd.read_pickle(
        start.PATH + f"data/clean/text_dfs_w_chunks_group_{group_num}.pkl"
    )
    text_df = text_df[(text_df["decision_id"] == model["decision_id"])]

    text_df["doc_id"] = (
        text_df.distict + "_chunk" + text_df.chunk.astype(int).astype(str)
    )

    # Create dictionary and corpus
    docs = list(text_df.tokens)
    dictionary = Dictionary(docs)
    print(len(dictionary))

    dictionary.filter_extremes(no_above=model["max_df"])
    print(len(dictionary))
    corpus = [dictionary.doc2bow(doc) for doc in docs]

    lda = gensim.models.LdaModel(
        corpus,
        id2word=dictionary,
        num_topics=model["topic"],
        passes=PASSES,
        random_state=SEED,
        per_word_topics=True,
    )

    cv_score = CoherenceModel(
        model=lda,
        corpus=corpus,
        texts=docs,
        dictionary=dictionary,
        coherence="c_v",
        processes=1,
    ).get_coherence()

    umass_score = CoherenceModel(
        model=lda,
        corpus=corpus,
        texts=docs,
        dictionary=dictionary,
        coherence="u_mass",
        processes=1,
    ).get_coherence()

    model["cv_score"] = cv_score
    model["umass_score"] = umass_score

    topic_modeling.create_topic_tables(
        lda=lda,
        corpus=corpus,
        dictionary=dictionary,
        docs_df=text_df,
        num_topics=model["topic"],
        folder_path=newpath,
        num_words_to_view=WORDS_TO_VIEW,
    )


models_df = pd.DataFrame(models_list)
models_df.to_csv(
    start.DATA_DIR + "clean/sample_models_coherence_update.csv", index=False
)
# %%
