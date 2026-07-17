# %%
import pandas as pd
import numpy as np
from strategic_plans.library import start
from scipy.stats import f_oneway
from statsmodels.stats.multitest import multipletests
from openpyxl import Workbook
from openpyxl.styles import Font

# %%
# Load the data
top_topics_df = pd.read_excel(start.RESULTS_DIR + 'top_topics.xlsx')
merge_df = pd.read_excel(start.DATA_DIR + "clean/sample_inclusion_with_topics_and_codes.xlsx")

print(f"Analyzing {len(top_topics_df)} topics")
print(f"Number of districts: {len(merge_df)}")

# Scale income to thousands if needed (assuming it's already scaled based on the variable name)
merge_df["medinc_1000"] = merge_df["medinc_1000"] / 1000

# %%
# Create quartiles based on medinc_1000
merge_df['income_quartile'] = pd.qcut(merge_df['medinc_1000'], 
                                     q=4, labels=['Q1', 'Q2', 'Q3', 'Q4'])

# Print quartile ranges in full dollars
print("\nIncome Quartiles (in $):")
quartile_stats = merge_df.groupby('income_quartile')['medinc_1000'].agg(['min', 'max', 'mean', 'count'])
for quartile in ['Q1', 'Q2', 'Q3', 'Q4']:
    stats = quartile_stats.loc[quartile]
    min_dollars = stats['min'] * 1000
    max_dollars = stats['max'] * 1000
    mean_dollars = stats['mean'] * 1000
    print(f"{quartile}: ${min_dollars:,.0f} - ${max_dollars:,.0f} "
          f"(mean: ${mean_dollars:,.0f}, n={stats['count']})")
# %%
# Grouping, names, inclusion, and merges are all chosen in the ContentCoder app
# and flow here through top_topics.xlsx (see Table5b). Groups follow the app's
# LDA-tab order (Group Order); topics within a group are ordered by prevalence.
top_topics_df = top_topics_df.sort_values(
    ["Group Order", "Average Prevalence"], ascending=[True, False]
)
TOPIC_GROUPS = []
for group_name, group_rows in top_topics_df.groupby("Parent Code", sort=False):
    members = list(group_rows["Topic ID"])
    TOPIC_GROUPS.append((group_name, members))

ordered_topics = [topic for _, topics in TOPIC_GROUPS for topic in topics]

# %%
# Create results workbook
wb = Workbook()
ws = wb.active
ws.title = "Income Quartiles Topic Analysis"

# Set up headers
headers = ["Topic", "Q1", "Q2", "Q3", "Q4", "Adj P-value"]
for col, header in enumerate(headers, 1):
    ws.cell(row=1, column=col, value=header)
    ws.cell(row=1, column=col).font = Font(bold=True)

# %%
# Prepare to store long-form results and p-values for BH correction
all_topic_groups = []
p_values = []
topic_results = []
quartile_labels = ['Q1', 'Q2', 'Q3', 'Q4']

# First pass: collect all p-values
for topic_code in ordered_topics:
    topic_row = top_topics_df[top_topics_df['Topic ID'] == topic_code]
    if len(topic_row) == 0:
        print(f"Warning: Topic {topic_code} not found in top_topics.xlsx")
        continue
    
    topic_id = topic_row.iloc[0]['Topic ID']
    topic_name = topic_row.iloc[0]['Topic Code']

    # Dictionary to store raw values by quartile
    quartile_data_dict = {}

    for quartile in quartile_labels:
        group_df = merge_df[merge_df['income_quartile'] == quartile]
        values = group_df[topic_id].values if len(group_df) > 0 else np.array([])
        quartile_data_dict[quartile] = values

    # Calculate means and standard deviations
    means = {}
    stds = {}
    for quartile in quartile_labels:
        vals = quartile_data_dict[quartile]
        mean_val = np.nan if len(vals) == 0 else np.nanmean(vals)
        std_val = np.nan if len(vals) == 0 else np.nanstd(vals, ddof=1)
        means[quartile] = mean_val
        stds[quartile] = std_val

    # Perform ANOVA
    valid_groups = [
        pd.Series(vals).dropna().values
        for vals in quartile_data_dict.values()
        if pd.Series(vals).dropna().shape[0] > 0
    ]
    
    if len(valid_groups) >= 2:
        f_stat, p_value = f_oneway(*valid_groups)
        print(f"Topic {topic_code} ANOVA F-statistic: {f_stat:.3f}, P-value: {p_value:.4f}")
        p_values.append(p_value)
    else:
        p_value = np.nan
        p_values.append(np.nan)

    # Store results for second pass
    topic_results.append({
        'topic_code': topic_code,
        'topic_name': topic_name,
        'means': means,
        'stds': stds,
        'p_value': p_value
    })

    # Build long-form DataFrame for this topic
    topic_long_df = pd.DataFrame([
        {"quartile": q, "value": v, "topic": topic_code}
        for q, vals in quartile_data_dict.items()
        for v in vals
    ])
    all_topic_groups.append(topic_long_df)

# %%
# Apply Benjamini-Hochberg correction
valid_p_indices = [i for i, p in enumerate(p_values) if not np.isnan(p)]
valid_p_values = [p_values[i] for i in valid_p_indices]

if len(valid_p_values) > 0:
    rejected, p_adjusted, alpha_sidak, alpha_bonf = multipletests(valid_p_values, method='fdr_bh')
    
    # Create full adjusted p-values array
    adj_p_values = [np.nan] * len(p_values)
    for i, adj_p in zip(valid_p_indices, p_adjusted):
        adj_p_values[i] = adj_p
else:
    adj_p_values = [np.nan] * len(p_values)

# %%
# Second pass: write to Excel with adjusted p-values
row = 2
for i, result in enumerate(topic_results):
    # Add topic name to Excel
    ws.cell(row=row, column=1, value=result['topic_name'])
    ws.cell(row=row, column=1).font = Font(bold=False)

    # Add means to Excel
    for col_idx, quartile in enumerate(quartile_labels, 2):
        mean_val = result['means'][quartile]
        ws.cell(row=row, column=col_idx,
                value=f"{mean_val:.2f}" if not np.isnan(mean_val) else "N/A")

    # Add adjusted p-value
    adj_p_value = adj_p_values[i]
    if not np.isnan(adj_p_value):
        if adj_p_value < 0.001:
            adj_p_str = f"{adj_p_value:.3f}***"
        elif adj_p_value < 0.01:
            adj_p_str = f"{adj_p_value:.3f}**"
        elif adj_p_value < 0.05:
            adj_p_str = f"{adj_p_value:.3f}*"
        else:
            adj_p_str = f"{adj_p_value:.3f}"
        ws.cell(row=row, column=6, value=adj_p_str)
    else:
        ws.cell(row=row, column=6, value="N/A")

    row += 1

    # Add standard deviation row in brackets
    ws.cell(row=row, column=1, value="")
    for col_idx, quartile in enumerate(quartile_labels, 2):
        std_val = result['stds'][quartile]
        ws.cell(row=row, column=col_idx,
                value=f"[{std_val:.2f}]" if not np.isnan(std_val) else "[N/A]")
    
    row += 1

# %%
# Add group separators in Excel
current_row = 2
for group_name, topics in TOPIC_GROUPS:
    ws.insert_rows(current_row)
    ws.cell(row=current_row, column=1, value=group_name)
    ws.cell(row=current_row, column=1).font = Font(bold=True, italic=True)
    current_row += 1 + (len(topics) * 2)  # Each topic takes 2 rows (mean + std dev)

# %%
# Add sample sizes row at the end
ws.cell(row=current_row + 1, column=1, value="Sample Size (N)")
ws.cell(row=current_row + 1, column=1).font = Font(bold=False)

for col_idx, quartile in enumerate(quartile_labels, 2):
    count = len(merge_df[merge_df['income_quartile'] == quartile])
    ws.cell(row=current_row + 1, column=col_idx, value=str(count))

# %%
# Add characteristic means row
ws.cell(row=current_row + 2, column=1, value="Mean Income ($1000s)")
ws.cell(row=current_row + 2, column=1).font = Font(bold=False)

for col_idx, quartile in enumerate(quartile_labels, 2):
    quartile_data = merge_df[merge_df['income_quartile'] == quartile]
    mean_characteristic = quartile_data['medinc_1000'].mean() * 1000 if len(quartile_data) > 0 else np.nan
    ws.cell(row=current_row + 2, column=col_idx,
            value=f"${mean_characteristic:,.0f}K" if not np.isnan(mean_characteristic) else "N/A")

# %%
# Save Excel results
output_path = start.RESULTS_DIR + 'AppendixB5_income_quartiles.xlsx'
wb.save(output_path)
print(f"\nTable exported to {output_path}")


# %%
# Print summary stats
print("\nSummary Statistics:")
print(f"Number of districts analyzed: {len(merge_df)}")
print(f"Number of topics analyzed: {len(ordered_topics)}")
print("\nQuartile distribution:")
for quartile in quartile_labels:
    count = len(merge_df[merge_df['income_quartile'] == quartile])
    print(f"  {quartile}: {count} districts")