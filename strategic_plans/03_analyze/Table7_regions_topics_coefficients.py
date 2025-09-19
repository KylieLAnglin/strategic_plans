# %%
import pandas as pd
import numpy as np
from strategic_plans.library import start
import statsmodels.formula.api as smf
from statsmodels.stats.multitest import multipletests
from openpyxl import Workbook
from openpyxl.styles import Font

# ---------------- Config ----------------
NORMALIZED = True  # <-- flip this to False to run raw prevalence version

# ---------------- Helpers ----------------
def starify(p):
    return f"{p:.2f}" + ("***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else "")

def topic_label(topic_code, top_df):
    base = topic_code.replace("_norm", "")
    return top_df.loc[top_df['Topic ID'] == base, 'Topic Code'].iloc[0]

# ---------------- Load data ----------------
top_topics_df = pd.read_excel(start.RESULTS_DIR + 'top_topics.xlsx')
merge_df = pd.read_excel(start.DATA_DIR + "clean/sample_inclusion_with_topics_and_codes.xlsx")
merge_df = merge_df[merge_df.state != "PA"]  # Exclude PA

# ---------------- Topic construction ----------------
if NORMALIZED:
    merge_df['Academic_Achievement_norm'] = merge_df['Topic_9_norm'] + merge_df['Topic_16_norm']
    top_topics_df = pd.concat([
        top_topics_df,
        pd.DataFrame({'Topic ID': ['Academic_Achievement'], 'Topic Code': ['Academic Achievement']})
    ], ignore_index=True)
    TOPIC_GROUPS = [
        ("Academic Topics", ["Topic_1_norm", "Topic_8_norm", "Academic_Achievement_norm"]),
        ("Non-Academic Outcomes", ["Topic_3_norm", "Topic_5_norm", "Topic_12_norm", "Topic_14_norm"]),
        ("Family and Community", ["Topic_17_norm", "Topic_20_norm"]),
        ("Mechanisms", ["Topic_0_norm", "Topic_22_norm"])
    ]
else:
    merge_df['Academic_Achievement'] = merge_df['Topic_9'] + merge_df['Topic_16']
    top_topics_df = pd.concat([
        top_topics_df,
        pd.DataFrame({'Topic ID': ['Academic_Achievement'], 'Topic Code': ['Academic Achievement']})
    ], ignore_index=True)
    TOPIC_GROUPS = [
        ("Academic Topics", ["Topic_1", "Topic_8", "Academic_Achievement"]),
        ("Non-Academic Outcomes", ["Topic_3", "Topic_5", "Topic_12", "Topic_14"]),
        ("Family and Community", ["Topic_17", "Topic_20"]),
        ("Mechanisms", ["Topic_0", "Topic_22"])
    ]

ordered_topics = [t for _, topics in TOPIC_GROUPS for t in topics]

print(f"Analyzing {len(top_topics_df)} topics")
print(f"Number of districts: {len(merge_df)}")
print(f"Number of states: {merge_df['state'].nunique()}")

# ---------------- Region variable (NE reference) ----------------
merge_df['region_cat'] = 'northeast'
merge_df.loc[merge_df['midwest'] == 1, 'region_cat'] = 'midwest'
merge_df.loc[merge_df['west'] == 1, 'region_cat'] = 'west'
merge_df.loc[merge_df['south'] == 1, 'region_cat'] = 'south'
region_levels = ["midwest", "west", "south"]

# ---------------- Workbook ----------------
wb = Workbook()
ws = wb.active
ws.title = "Regional Coefficients (State FE)"
headers = ["Topic", "Northeast Mean", "Midwest", "West", "South", "Unadj P-value", "Adj P-value"]
for col, header in enumerate(headers, 1):
    ws.cell(row=1, column=col, value=header).font = Font(bold=True)

# ---------------- Regressions ----------------
p_values = []
topic_results = []

for topic_code in ordered_topics:
    topic_name = topic_label(topic_code, top_topics_df)

    formula = f"{topic_code} ~ C(region_cat, Treatment(reference='northeast')) + improvement_plan + form_plan + word_count"
    model = smf.ols(formula, data=merge_df, missing='drop').fit()

    northeast_mean = merge_df.loc[merge_df['region_cat'] == 'northeast', topic_code].mean()

    coefficients = {lvl: model.params.get(f"C(region_cat, Treatment(reference='northeast'))[T.{lvl}]", np.nan)
                    for lvl in region_levels}
    std_errors = {lvl: model.bse.get(f"C(region_cat, Treatment(reference='northeast'))[T.{lvl}]", np.nan)
                  for lvl in region_levels}

    f_test = model.f_test(
        "C(region_cat, Treatment(reference='northeast'))[T.midwest] = 0, "
        "C(region_cat, Treatment(reference='northeast'))[T.west] = 0, "
        "C(region_cat, Treatment(reference='northeast'))[T.south] = 0"
    )
    p_value = float(f_test.pvalue)

    p_values.append(p_value)
    topic_results.append((topic_name, northeast_mean, coefficients, std_errors, p_value))

# ---------------- Adjust p-values ----------------
_, adj_p_values, _, _ = multipletests(p_values, method='fdr_bh')

# ---------------- Write to Excel ----------------
row = 2
for i, (topic_name, northeast_mean, coefficients, std_errors, p_value) in enumerate(topic_results):
    ws.cell(row=row, column=1, value=topic_name)
    ws.cell(row=row, column=2, value=f"{northeast_mean:.2f}")
    ws.cell(row=row, column=3, value=f"{coefficients['midwest']:.2f}")
    ws.cell(row=row, column=4, value=f"{coefficients['west']:.2f}")
    ws.cell(row=row, column=5, value=f"{coefficients['south']:.2f}")
    ws.cell(row=row, column=6, value=starify(p_value))
    ws.cell(row=row, column=7, value=starify(adj_p_values[i]))

    row += 1
    ws.cell(row=row, column=3, value=f"({std_errors['midwest']:.2f})")
    ws.cell(row=row, column=4, value=f"({std_errors['west']:.2f})")
    ws.cell(row=row, column=5, value=f"({std_errors['south']:.2f})")
    row += 1

# ---------------- Group separators ----------------
current_row = 2
for group_name, topics in TOPIC_GROUPS:
    ws.insert_rows(current_row)
    ws.cell(row=current_row, column=1, value=group_name).font = Font(bold=True, italic=True)
    current_row += 1 + (len(topics) * 2)

# ---------------- Notes & Save ----------------
ws.cell(row=current_row + 1, column=1, value="Note: Northeast is the reference category").font = Font(italic=True)
if NORMALIZED:
    ws.cell(row=current_row + 2, column=1, value="Prevalence values normalized by sum of included topics").font = Font(italic=True)

output_path = start.RESULTS_DIR + 'Table7_regions_topics_coefficients.xlsx'
wb.save(output_path)
print(f"\nTable exported to {output_path}")