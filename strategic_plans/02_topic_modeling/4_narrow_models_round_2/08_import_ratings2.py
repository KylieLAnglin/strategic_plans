# %%
# %%
import numpy as np
import pandas as pd
from strategic_plans.library import start

# %%
df_topics = pd.read_excel(start.DATA_DIR + "narrow_models_round_2/sample_doc_topic_prevalence_with_words_rated.xlsx")

# %%
df = df_topics.groupby(["model_id", "district"]).mean(numeric_only=True).reset_index()
df = df.sort_values(by="document_order", ascending=False)

df = df[df.model_quality.notna()]
# %%
# Calculate mean model quality by topic column
topic_df = df.groupby(["topic"]).agg(
    {
        "model_quality": ["mean", "max", "var"],
    }
)
topic_df.columns = [
    "model_quality_mean",
    "model_quality_max",
    "model_quality_var",
]
topic_df = topic_df.reset_index()
topic_df = topic_df.sort_values(by=["model_quality_mean"], ascending=False)
# %%
chunk_df = df.groupby(["chunk"]).agg(
    {
        "model_quality": ["mean", "max", "var"],
    }
)
chunk_df.columns = [
    "model_quality_mean",
    "model_quality_max",
    "model_quality_var",
]
chunk_df = chunk_df.reset_index()
chunk_df = chunk_df.sort_values(by=["model_quality_mean"], ascending=False)


# %%
diygram_df = df.groupby(["diy_gram"]).agg(
    {
        "model_quality": ["mean", "max", "var"],
    }
)

diygram_df.columns = [

    "model_quality_mean",
    "model_quality_max",
    "model_quality_var",
]
diygram_df = diygram_df.reset_index()
diygram_df = diygram_df.sort_values(by=["model_quality_mean"], ascending=False)

# %%
maxdf_df = df.groupby(["max_df"]).agg(
    {
        "model_quality": ["mean", "max", "var"],
    }
)
maxdf_df.columns = [
    "model_quality_mean",
    "model_quality_max",
    "model_quality_var",
]
maxdf_df = maxdf_df.reset_index()
maxdf_df = maxdf_df.sort_values(by=["model_quality_mean"], ascending=False)

# %%
mindf_df = df.groupby(["min_df"]).agg(
    {
        "model_quality": ["mean", "max", "var"],
    }
)
mindf_df.columns = [
    "model_quality_mean",
    "model_quality_max",
    "model_quality_var",
]
mindf_df = mindf_df.reset_index()
mindf_df = mindf_df.sort_values(by=["model_quality_mean"], ascending=False)

# %%
stem_df = df.groupby(["stem"]).agg(
    {
        "model_quality": ["mean", "max", "var"],
    }
)
stem_df.columns = [

    "model_quality_mean",
    "model_quality_max",
    "model_quality_var",
]
stem_df = stem_df.reset_index()
stem_df = stem_df.sort_values(by=["model_quality_mean"], ascending=False)

# %%
tribigram_df = df.groupby(["tribigram"]).agg(
    {
        "model_quality": ["mean", "max", "var"],
    }
)
tribigram_df.columns = [

    "model_quality_mean",
    "model_quality_max",
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
    "topic",
    "tribigram",
]


def get_explained_variance(df, decision):
    total_variance = df["model_quality"].var()

    # within group variance is not explained by the decision
    within_variance = df.groupby(decision)["model_quality"].var().sum()

    means = df.groupby(decision)["model_quality"].mean()

    # Number of observations per group
    counts = df.groupby(decision)["model_quality"].count()

    # Grand mean
    grand_mean = df["model_quality"].mean()

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
