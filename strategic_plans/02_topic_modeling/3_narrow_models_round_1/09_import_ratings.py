# %%
# %%
import numpy as np
import pandas as pd
from library import start

# %%
df_C = pd.read_excel(start.MAIN_DIR + "sample_doc_topic_prevalence_with_words_C.xlsx")
df_C["coder"] = "C"
df_J = pd.read_excel(start.MAIN_DIR + "sample_doc_topic_prevalence_with_words_J.xlsx")
df_J["coder"] = "J"
df_K = pd.read_excel(start.MAIN_DIR + "sample_doc_topic_prevalence_with_words_K.xlsx")
df_K["coder"] = "K"

models = pd.read_csv(start.DATA_DIR + "clean/sample_models_coherence.csv")

# %%

df = pd.concat([df_C, df_J, df_K], ignore_index=True)
df = df[
    [
        "district",
        "document_order",
        "model_id",
        "decision_id",
        "topic_number",
        "chunk",
        "diy_gram",
        "max_df",
        "min_df",
        "stem",
        "stop",
        "topic",
        "tribigram",
        "coder",
        "topic_quality",
        "model_quality",
    ]
]
# take mean and max of topic quality and model quality

model_df = df.groupby(["model_id"]).agg(
    {
        "topic_quality": ["mean", "max", "var"],
        "model_quality": ["mean", "max", "var"],
    }
)
model_df.columns = [
    "topic_quality_mean",
    "topic_quality_max",
    "model_quality_mean",
    "model_quality_max",
    "topic_quality_var",
    "model_quality_var",
]
model_df = model_df.reset_index()

model_df = model_df.sort_values(by=["topic_quality_mean"], ascending=False)

model_df.to_excel(start.RESULTS_DIR + "model_quality_phase1.xlsx", index=False)

# %%
# Calculate mean topic quality by topic column
topic_df = df.groupby(["topic"]).agg(
    {
        "topic_quality": ["mean", "max", "var"],
        "model_quality": ["mean", "max", "var"],
    }
)
topic_df.columns = [
    "topic_quality_mean",
    "topic_quality_max",
    "model_quality_mean",
    "model_quality_max",
    "topic_quality_var",
    "model_quality_var",
]
topic_df = topic_df.reset_index()
topic_df = topic_df.sort_values(by=["topic_quality_mean"], ascending=False)
# %%

chunk_df = df.groupby(["chunk"]).agg(
    {
        "topic_quality": ["mean", "max", "var"],
        "model_quality": ["mean", "max", "var"],
    }
)
chunk_df.columns = [
    "topic_quality_mean",
    "topic_quality_max",
    "model_quality_mean",
    "model_quality_max",
    "topic_quality_var",
    "model_quality_var",
]
chunk_df = chunk_df.reset_index()
chunk_df = chunk_df.sort_values(by=["model_quality_mean"], ascending=False)


# %%
diygram_df = df.groupby(["diy_gram"]).agg(
    {
        "topic_quality": ["mean", "max", "var"],
        "model_quality": ["mean", "max", "var"],
    }
)
diygram_df.columns = [
    "topic_quality_mean",
    "topic_quality_max",
    "model_quality_mean",
    "model_quality_max",
    "topic_quality_var",
    "model_quality_var",
]
diygram_df = diygram_df.reset_index()
diygram_df = diygram_df.sort_values(by=["model_quality_mean"], ascending=False)

# %%
maxdf_df = df.groupby(["max_df"]).agg(
    {
        "topic_quality": ["mean", "max", "var"],
        "model_quality": ["mean", "max", "var"],
    }
)
maxdf_df.columns = [
    "topic_quality_mean",
    "topic_quality_max",
    "model_quality_mean",
    "model_quality_max",
    "topic_quality_var",
    "model_quality_var",
]
maxdf_df = maxdf_df.reset_index()
maxdf_df = maxdf_df.sort_values(by=["model_quality_mean"], ascending=False)

# %%
mindf_df = df.groupby(["min_df"]).agg(
    {
        "topic_quality": ["mean", "max", "var"],
        "model_quality": ["mean", "max", "var"],
    }
)
mindf_df.columns = [
    "topic_quality_mean",
    "topic_quality_max",
    "model_quality_mean",
    "model_quality_max",
    "topic_quality_var",
    "model_quality_var",
]
mindf_df = mindf_df.reset_index()
mindf_df = mindf_df.sort_values(by=["model_quality_mean"], ascending=False)

# %%
stem_df = df.groupby(["stem"]).agg(
    {
        "topic_quality": ["mean", "max", "var"],
        "model_quality": ["mean", "max", "var"],
    }
)
stem_df.columns = [
    "topic_quality_mean",
    "topic_quality_max",
    "model_quality_mean",
    "model_quality_max",
    "topic_quality_var",
    "model_quality_var",
]
stem_df = stem_df.reset_index()
stem_df = stem_df.sort_values(by=["model_quality_mean"], ascending=False)

# %%
stop_df = df.groupby(["stop"]).agg(
    {
        "topic_quality": ["mean", "max", "var"],
        "model_quality": ["mean", "max", "var"],
    }
)
stop_df.columns = [
    "topic_quality_mean",
    "topic_quality_max",
    "model_quality_mean",
    "model_quality_max",
    "topic_quality_var",
    "model_quality_var",
]
stop_df = stop_df.reset_index()
stop_df = stop_df.sort_values(by=["model_quality_mean"], ascending=False)

# %%
tribigram_df = df.groupby(["tribigram"]).agg(
    {
        "topic_quality": ["mean", "max", "var"],
        "model_quality": ["mean", "max", "var"],
    }
)
tribigram_df.columns = [
    "topic_quality_mean",
    "topic_quality_max",
    "model_quality_mean",
    "model_quality_max",
    "topic_quality_var",
    "model_quality_var",
]
tribigram_df = tribigram_df.reset_index()
tribigram_df = tribigram_df.sort_values(by=["model_quality_mean"], ascending=False)
# %%
DECISIONS = [
    "chunk",
    "diy_gram",
    "max_df",
    "min_df",
    "stem",
    "stop",
    "topic",
    "tribigram",
]


def get_explained_variance(df, decision):
    total_variance = df["topic_quality"].var()

    # within group variance is not explained by the decision
    within_variance = df.groupby(decision)["topic_quality"].var().sum()

    means = df.groupby(decision)["topic_quality"].mean()

    # Number of observations per group
    counts = df.groupby(decision)["topic_quality"].count()

    # Grand mean
    grand_mean = df["topic_quality"].mean()

    # Between-group variance (weighted by group sizes)
    between_group_var = ((counts * (means - grand_mean) ** 2).sum()) / (len(df) - 1)

    explained_variance = (
        within_variance / total_variance
    )  # within group variance is not explained by

    return explained_variance


# Calculate the explained variance for each decision
explained_variance = {}
for decision in DECISIONS:
    explained_variance[decision] = get_explained_variance(df, decision)
explained_variance_df = pd.DataFrame.from_dict(explained_variance, orient="index")
explained_variance_df.columns = ["explained_variance"]
explained_variance_df = explained_variance_df.reset_index()
explained_variance_df.columns = ["decision", "explained_variance"]
explained_variance_df = explained_variance_df.sort_values(
    by=["explained_variance"], ascending=False
)
# %%
julia_df = df[df["coder"] == "J"]
julia_df = julia_df.groupby(["model_id"]).agg(
    {
        "topic_quality": ["mean", "max", "var"],
    }
)
julia_df.columns = [
    "topic_quality_mean",
    "topic_quality_max",
    "topic_quality_var",
]
julia_df = julia_df.reset_index()


julia_df = julia_df.sort_values(by=["topic_quality_mean"], ascending=False)
# %%
good_df = df[df.chunk != 0]
good_df = good_df[good_df.min_df != 20]
good_df = good_df[good_df.stem != 1]
good_df = good_df[good_df.stop != 0]
good_df = good_df[good_df.tribigram != 0]

good_df = good_df.groupby(["model_id"]).agg(
    {
        "topic_quality": ["mean", "max", "var"],
        "model_quality": ["mean", "max", "var"],
    }
)
good_df.columns = [
    "topic_quality_mean",
    "topic_quality_max",
    "model_quality_mean",
    "model_quality_max",
    "topic_quality_var",
    "model_quality_var",
]
good_df = good_df.merge(models, on="model_id")
good_df = good_df.reset_index()
good_df = good_df.sort_values(by=["topic_quality_mean"], ascending=False)
