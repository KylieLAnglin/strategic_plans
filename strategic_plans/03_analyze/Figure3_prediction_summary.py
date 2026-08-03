# %%
"""
  - Purpose: Figure version of Table 3 (topic variation endpoint contrasts)
  - Key operations:
    - Reads the estimates Table 3 already exported rather than refitting,
      so the figure and the table can never disagree
    - One panel per contrast, sharing a common x-axis in percentage points
    - A text column to the left of each panel gives the reference group's
      mean prevalence, so each difference can be read against its base
    - Topics on the y-axis in the table's order, grouped by parent code
    - Filled markers are significant after Benjamini-Hochberg adjustment
      within a contrast; hollow markers are not
    - No note is drawn on the figure; it belongs in the manuscript caption
  - Outputs: results/Figure3_prediction_summary.png and .pdf
"""
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.transforms import blended_transform_factory
from strategic_plans.library import start

# ------------------ SETUP ------------------
ESTIMATES_PATH = start.RESULTS_DIR + "topic_variation_endpoint_contrasts.xlsx"
TOP_TOPICS_PATH = start.RESULTS_DIR + "top_topics.xlsx"
FIGURE_PATH = start.RESULTS_DIR + "Figure3_prediction_summary.png"
FIGURE_PDF_PATH = start.RESULTS_DIR + "Figure3_prediction_summary.pdf"

ALPHA = 0.05
MARK_COLOR = "#222222"
GRID_COLOR = "#DDDDDD"
REFERENCE_LINE_COLOR = "#999999"

# Right edge of the reference-mean text column, in axes coordinates
MEAN_COLUMN_X = -0.09

# Each panel is headed by the characteristic, then by a head over the mean
# column and a head over the plot itself
PANEL_HEADS = {
    "Rural − Urban": ("Urbanicity", "Urban\nMean", "Rural\nDifference"),
    "South − Northeast": ("Region", "Northeast\nMean", "South\nDifference"),
    "Highest − Lowest Black/Hispanic": (
        "Percent Black/Hispanic", "Q1\nMean", "Q4\nDifference"
    ),
    "Most − Least Republican": (
        "Percent Republican", "Q1\nMean", "Q4\nDifference"
    ),
}

plt.rcParams.update({
    "font.family": "Times New Roman",
    "font.size": 10,
    "axes.linewidth": 0.6,
})

# %%
# ------------------ LOAD DATA ------------------
estimates = pd.read_excel(ESTIMATES_PATH, sheet_name="Underlying Estimates")
top_topics_df = pd.read_excel(TOP_TOPICS_PATH)

contrast_names = list(estimates.contrast.unique())

# %%
# ------------------ ROW LAYOUT ------------------
# Same ordering as the table: groups in the app's LDA-tab order, topics
# within a group by prevalence. Each group gets a header row with no marker.
top_topics_df = top_topics_df.sort_values(
    ["Group Order", "Average Prevalence"], ascending=[True, False]
)

row_labels = []
row_is_header = []
row_topic_names = []

for group_name, group_rows in top_topics_df.groupby("Parent Code", sort=False):
    row_labels.append(group_name)
    row_is_header.append(True)
    row_topic_names.append(None)

    for topic_name in group_rows["Topic Code"]:
        row_labels.append("   " + topic_name)
        row_is_header.append(False)
        row_topic_names.append(topic_name)

# Top of the figure is the first row, so positions count down
row_positions = [len(row_labels) - 1 - index for index in range(len(row_labels))]

# %%
# ------------------ DRAW PANELS ------------------
figure, axes = plt.subplots(
    1,
    len(contrast_names),
    figsize=(12, 6),
    sharex=True,
    sharey=True,
)

for panel_axis, contrast_name in zip(axes, contrast_names):
    contrast_estimates = estimates[estimates.contrast == contrast_name].set_index("topic_name")
    characteristic_head, mean_head, difference_head = PANEL_HEADS[contrast_name]

    # x in axes coordinates, y in data coordinates, so the text column
    # stays put while the rows follow the shared y-axis
    mean_column_transform = blended_transform_factory(
        panel_axis.transAxes, panel_axis.transData
    )

    for row_position, topic_name in zip(row_positions, row_topic_names):
        if topic_name is None:
            continue

        result = contrast_estimates.loc[topic_name]
        is_significant = result.adjusted_p_value < ALPHA

        panel_axis.text(
            MEAN_COLUMN_X,
            row_position,
            f"{result.reference_mean_pp:.1f}",
            transform=mean_column_transform,
            horizontalalignment="right",
            verticalalignment="center",
            fontsize=9,
        )

        panel_axis.plot(
            [result.ci_low_pp, result.ci_high_pp],
            [row_position, row_position],
            color=MARK_COLOR,
            linewidth=1.2,
            solid_capstyle="butt",
            zorder=2,
        )
        panel_axis.plot(
            result.estimate_pp,
            row_position,
            marker="o",
            markersize=6,
            color=MARK_COLOR,
            markerfacecolor=MARK_COLOR if is_significant else "white",
            markeredgewidth=1.2,
            zorder=3,
        )

    panel_axis.axvline(0, color=REFERENCE_LINE_COLOR, linewidth=0.8, zorder=1)

    panel_axis.text(
        0.32, 1.115, characteristic_head,
        transform=panel_axis.transAxes,
        horizontalalignment="center", verticalalignment="bottom",
        fontsize=10,
    )
    panel_axis.text(
        MEAN_COLUMN_X, 1.015, mean_head,
        transform=panel_axis.transAxes,
        horizontalalignment="right", verticalalignment="bottom", fontsize=9,
    )
    panel_axis.text(
        0.5, 1.015, difference_head,
        transform=panel_axis.transAxes,
        horizontalalignment="center", verticalalignment="bottom", fontsize=9,
    )

    panel_axis.set_xlabel("Percentage points")
    panel_axis.set_xticks(range(-10, 15, 5))
    panel_axis.xaxis.grid(True, color=GRID_COLOR, linewidth=0.6)
    panel_axis.yaxis.grid(False)
    panel_axis.set_axisbelow(True)
    panel_axis.tick_params(axis="y", length=0)

    for spine_name in ["top", "right", "left"]:
        panel_axis.spines[spine_name].set_visible(False)

axes[0].set_yticks(row_positions)
axes[0].set_yticklabels(row_labels)
axes[0].set_ylim(-1, len(row_labels))

# Left-aligned so the group headers sit flush and their topics read as
# indented, with room for the reference-mean column between them and the plot
axes[0].tick_params(axis="y", pad=225)

for tick_label, is_header in zip(axes[0].get_yticklabels(), row_is_header):
    tick_label.set_horizontalalignment("left")
    if is_header:
        tick_label.set_fontweight("bold")

figure.tight_layout()
figure.subplots_adjust(wspace=0.38)

# %%
# ------------------ EXPORT ------------------
figure.savefig(FIGURE_PATH, dpi=300)
figure.savefig(FIGURE_PDF_PATH)

print(f"Saved: {FIGURE_PATH}")
print(f"Saved: {FIGURE_PDF_PATH}")

# %%
