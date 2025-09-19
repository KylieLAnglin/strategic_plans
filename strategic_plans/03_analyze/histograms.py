# %%
import os
import re
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from strategic_plans.library import start

# ------------------ Load & prep ------------------
top_topics_df = pd.read_excel(start.RESULTS_DIR + 'top_topics.xlsx')
merge_df = pd.read_excel(start.DATA_DIR + "clean/sample_inclusion_with_topics_and_codes.xlsx")
merge_df = merge_df[merge_df.state != "PA"]  # Exclude PA for now

# Create combined Academic Achievement topic (Topic_9 + Topic_16)
merge_df['Academic_Achievement'] = merge_df['Topic_9'] + merge_df['Topic_16']

# Add Academic Achievement to top_topics_df if not present
if not (top_topics_df['Topic ID'] == 'Academic_Achievement').any():
    academic_achievement_row = pd.DataFrame({
        'Topic ID': ['Academic_Achievement'],
        'Topic Code': ['Academic Achievement']
    })
    top_topics_df = pd.concat([top_topics_df, academic_achievement_row], ignore_index=True)

# ------------------ Ordered topics ------------------
TOPIC_GROUPS = [
    ("Academic Topics", ["Topic_1", "Topic_8", "Academic_Achievement"]),
    ("Non-Academic Outcomes", ["Topic_3", "Topic_5", "Topic_12", "Topic_14"]),
    ("Family and Community", ["Topic_17", "Topic_20"]),
    ("Mechanisms", ["Topic_0", "Topic_22"]),
]
ordered_topics = [t for _, topics in TOPIC_GROUPS for t in topics]

# Map from Topic ID -> human label (fallback to ID if missing)
id_to_label = dict(zip(top_topics_df['Topic ID'], top_topics_df['Topic Code']))
def topic_label(tid: str) -> str:
    return id_to_label.get(tid, tid)

# ------------------ Output dir ------------------
out_dir = os.path.join(start.RESULTS_DIR, "topic_histograms")
os.makedirs(out_dir, exist_ok=True)

# ------------------ Helpers ------------------
def safe_filename(s: str) -> str:
    s = re.sub(r"[^\w\-\. ]+", "_", s)
    return re.sub(r"\s+", "_", s).strip("_")

# If your topic columns are proportions (0–1), these bins are sensible.
# If they are counts, adjust `bins` accordingly (e.g., bins=30).
bins = np.linspace(0, 1, 21)

# ------------------ Plot histograms ------------------
print(f"Saving histograms to: {out_dir}")
for topic_id in ordered_topics:
    if topic_id not in merge_df.columns:
        print(f"Skipping {topic_id} (column not found).")
        continue

    data = pd.to_numeric(merge_df[topic_id], errors='coerce').dropna()
    if data.empty:
        print(f"Skipping {topic_id} (no non-missing values).")
        continue

    label = topic_label(topic_id)

    plt.figure(figsize=(6, 4))
    # If your variable is binary {0,1}, you can switch to bins=[-0.5,0.5,1.5] for clearer bars.
    plt.hist(data, bins=bins, edgecolor='black')
    plt.title(f"{label}")
    plt.xlabel("Prevalence")
    plt.ylabel("Number of Districts")
    plt.tight_layout()

    base = safe_filename(f"hist_{topic_id}_{label}")
    png_path = os.path.join(out_dir, f"{base}.png")
    pdf_path = os.path.join(out_dir, f"{base}.pdf")
    plt.savefig(png_path, dpi=300)
    plt.savefig(pdf_path)
    plt.close()
print("Done.")