# %%
import pandas as pd

from strategic_plans.library import start

# %%
# ------------------ SETUP ------------------
INPUT_CHARACTERISTICS = start.LATEST_CHARACTERISTICS
EXPORT_PATH = start.RESULTS_DIR + "district_characteristics_summary.xlsx"

# A document counts as coded once any of these questions is answered.
ANSWER_FIELDS = [
    "required_document",
    "any_description",
    "focus_group",
    "survey",
    "committee_size",
    "roles_described",
]
INVOLVED_FIELDS = [
    ("involved_administrators", "Administrators"),
    ("involved_school_board", "School board"),
    ("involved_teachers", "Teachers"),
    ("involved_parents", "Parents"),
    ("involved_community", "Community members"),
    ("involved_students", "Students"),
]

# %%
# ------------------ LOAD DATA ------------------
df = pd.read_excel(INPUT_CHARACTERISTICS)

n_sample = len(df)
coded = df[ANSWER_FIELDS].notna().any(axis=1)
n_coded = int(coded.sum())

coded_df = df[coded]
described_df = df[df["any_description"] == 1]
roles_df = df[df["roles_described"] == 1]

n_described = len(described_df)
n_roles = len(roles_df)


# %%
# ------------------ SUMMARY TABLES ------------------
def labeled_summary(series, denominator, value_labels):
    rows = []
    for raw_value, label in value_labels:
        if raw_value is None:
            count = int(series.isna().sum())
        else:
            count = int((series == raw_value).sum())
        percent = round(100 * count / denominator, 1) if denominator else 0
        rows.append({"Response": label, "Count": count, "Percent": percent})
    return pd.DataFrame(rows)


progress_table = pd.DataFrame(
    [
        {"Measure": "Documents in qualitative sample", "Count": n_sample, "Percent": 100.0},
        {"Measure": "Coded", "Count": n_coded, "Percent": round(100 * n_coded / n_sample, 1)},
        {"Measure": "Describe a planning process", "Count": n_described,
         "Percent": round(100 * n_described / n_sample, 1)},
    ]
)

required_table = labeled_summary(
    coded_df["required_document"], n_coded,
    [("likely_yes", "Likely Yes"), ("likely_no", "Likely No"), (None, "Unanswered")],
)
any_description_table = labeled_summary(
    coded_df["any_description"], n_coded,
    [(1, "Yes"), (0, "No"), (None, "Unanswered")],
)

yes_no_unknown = [("yes", "Yes"), ("no", "No"), ("unknown", "Unknown"), (None, "Blank")]
focus_group_table = labeled_summary(described_df["focus_group"], n_described, yes_no_unknown)
survey_table = labeled_summary(described_df["survey"], n_described, yes_no_unknown)
roles_table = labeled_summary(
    described_df["roles_described"], n_described,
    [(1, "Yes"), (0, "No"), (None, "Blank")],
)
committee_table = labeled_summary(
    described_df["committee_size"], n_described,
    [("not_described", "Not described"), ("under_10", "Under 10"),
     ("10_to_20", "10-20"), ("over_20", "20+"), (None, "Blank")],
)

involvement_table = pd.DataFrame(
    [
        {
            "Group": label,
            "Count": int((roles_df[field] == 1).sum()),
            "Percent": round(100 * int((roles_df[field] == 1).sum()) / n_roles, 1) if n_roles else 0,
        }
        for field, label in INVOLVED_FIELDS
    ]
)

# %%
# ------------------ EXPORT ------------------
blocks = [
    (f"Progress (of {n_sample} sample documents)", progress_table),
    (f"Required document — of coded (n={n_coded})", required_table),
    (f"Any description of planning process — of coded (n={n_coded})", any_description_table),
    (f"Focus group or interviews — of documents describing a process (n={n_described})", focus_group_table),
    (f"Survey — of documents describing a process (n={n_described})", survey_table),
    (f"Roles described — of documents describing a process (n={n_described})", roles_table),
    (f"Committee size — of documents describing a process (n={n_described})", committee_table),
    (f"Who was involved — of documents with roles described (n={n_roles})", involvement_table),
]

with pd.ExcelWriter(EXPORT_PATH, engine="openpyxl") as writer:
    current_row = 0
    for title, table in blocks:
        pd.DataFrame(columns=[title]).to_excel(
            writer, sheet_name="Summary", startrow=current_row, index=False
        )
        table.to_excel(writer, sheet_name="Summary", startrow=current_row + 1, index=False)
        current_row += len(table) + 3

print(f"Saved: {EXPORT_PATH}")
