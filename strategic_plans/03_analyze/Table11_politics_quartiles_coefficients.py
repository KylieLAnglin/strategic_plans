# %%
import pandas as pd
import numpy as np
from strategic_plans.library import start
import statsmodels.formula.api as smf
from statsmodels.stats.multitest import multipletests
from openpyxl import Workbook
from openpyxl.styles import Font

# %%
# Load the data
top_topics_df = pd.read_excel(start.RESULTS_DIR + 'top_topics.xlsx')
merge_df = pd.read_excel(start.DATA_DIR + "clean/sample_inclusion_with_topics_and_codes.xlsx")

print(f"Analyzing {len(top_topics_df)} topics")
print(f"Number of districts: {len(merge_df)}")

print(f"Number of states: {merge_df['state'].nunique()}")

# Scale percentage variable to 0-100 scale if needed
merge_df["district_pct_trump"] = merge_df["district_pct_trump"] * 100

# %%
# Create quartiles based on district_pct_trump
merge_df['politics_quartile'] = pd.qcut(merge_df['district_pct_trump'], 
                                       q=4, labels=['Q1', 'Q2', 'Q3', 'Q4'])

# Print quartile ranges
print("\nPolitical Quartiles (% Trump Vote):")
quartile_stats = merge_df.groupby('politics_quartile')['district_pct_trump'].agg(['min', 'max', 'mean', 'count'])
for quartile in ['Q1', 'Q2', 'Q3', 'Q4']:
    stats = quartile_stats.loc[quartile]
    print(f"{quartile}: {stats['min']:.1f}% - {stats['max']:.1f}% (mean: {stats['mean']:.1f}%, n={stats['count']})")

# %%
# Create combined Academic Achievement topic (Topic_9 + Topic_16)
merge_df['Academic_Achievement'] = merge_df['Topic_9'] + merge_df['Topic_16']

# Add Academic Achievement to top_topics_df
academic_achievement_row = pd.DataFrame({
    'Topic ID': ['Academic_Achievement'],
    'Topic Code': ['Academic Achievement']
})
top_topics_df = pd.concat([top_topics_df, academic_achievement_row], ignore_index=True)

# %%
# Define topic groups in the specified order: Academic, Non-Academic, Family, Mechanisms
TOPIC_GROUPS = [
    ("Academic Topics", ["Topic_1", "Topic_8", "Academic_Achievement"]),
    ("Non-Academic Outcomes", ["Topic_3", "Topic_5", "Topic_12", "Topic_14"]),
    ("Family and Community", ["Topic_17", "Topic_20"]),
    ("Mechanisms", ["Topic_0", "Topic_22", "Topic_15"])
]

# Flatten topic list in the desired order
ordered_topics = [t for _, topics in TOPIC_GROUPS for t in topics]

# %%
# Create results workbook
wb = Workbook()
ws = wb.active
ws.title = "Politics Coefficients (State FE)"

# Set up headers (Q1 is reference group, so we show Q1 mean, Q2, Q3, Q4 coefficients)
headers = ["Topic", "Q1 Mean", "Q2", "Q3", "Q4", "Unadj P-value", "Adj P-value"]
for col, header in enumerate(headers, 1):
    ws.cell(row=1, column=col, value=header)
    ws.cell(row=1, column=col).font = Font(bold=True)

# %%
# Prepare to store results and p-values for BH correction
p_values = []
topic_results = []
quartile_levels = ["Q2", "Q3", "Q4"]  # Q1 is reference

# First pass: collect all p-values and coefficients using state fixed effects regression
for topic_code in ordered_topics:
    topic_row = top_topics_df[top_topics_df['Topic ID'] == topic_code]
    topic_id = topic_row.iloc[0]['Topic ID']
    topic_name = topic_row.iloc[0]['Topic Code']

    # Calculate mean prevalence for reference group (Q1)
    q1_data = merge_df[merge_df['politics_quartile'] == 'Q1']
    q1_mean = q1_data[topic_id].mean()
    
    # Run regression with state fixed effects (Q1 is reference category by default)
    formula = f"{topic_id} ~ C(politics_quartile) + C(state) + improvement_plan + form_plan + word_count"
    model = smf.ols(formula, data=merge_df, missing='drop').fit()
    
    # Extract coefficients and standard errors for non-reference categories
    coefficients = {}
    std_errors = {}
    for level in quartile_levels:
        param_name = f"C(politics_quartile)[T.{level}]"
        coeff = model.params[param_name]
        std_err = model.bse[param_name]
        coefficients[level] = coeff
        std_errors[level] = std_err
    
    # F-test for quartile coefficients
    quartile_params = [param for param in model.params.index if 'politics_quartile' in param]
    f_test = model.f_test([param for param in quartile_params])
    p_value = f_test.pvalue
    print(f"Topic {topic_code} State FE F-statistic: {f_test.fvalue:.3f}, P-value: {p_value:.4f}")
    
    p_values.append(p_value)

    # Store results for second pass
    topic_results.append({
        'topic_code': topic_code,
        'topic_name': topic_name,
        'q1_mean': q1_mean,
        'coefficients': coefficients,
        'std_errors': std_errors,
        'p_value': p_value
    })

# %%
# Apply Benjamini-Hochberg correction
rejected, p_adjusted, alpha_sidak, alpha_bonf = multipletests(p_values, method='fdr_bh')
adj_p_values = p_adjusted

# %%
# Second pass: write to Excel with coefficients and adjusted p-values
row = 2
for i, result in enumerate(topic_results):
    # Add topic name to Excel
    ws.cell(row=row, column=1, value=result['topic_name'])
    ws.cell(row=row, column=1).font = Font(bold=False)
    
    # Add Q1 mean prevalence to Excel
    ws.cell(row=row, column=2, value=f"{result['q1_mean']:.2f}")

    # Add coefficients to Excel
    for col_idx, level in enumerate(quartile_levels, 3):
        coeff_val = result['coefficients'][level]
        ws.cell(row=row, column=col_idx, value=f"{coeff_val:.2f}")

    # Add unadjusted p-value
    unadj_p_value = result['p_value']
    if unadj_p_value < 0.001:
        unadj_p_str = f"{unadj_p_value:.3f}***"
    elif unadj_p_value < 0.01:
        unadj_p_str = f"{unadj_p_value:.3f}**"
    elif unadj_p_value < 0.05:
        unadj_p_str = f"{unadj_p_value:.3f}*"
    else:
        unadj_p_str = f"{unadj_p_value:.3f}"
    ws.cell(row=row, column=6, value=unadj_p_str)
    
    # Add adjusted p-value
    adj_p_value = adj_p_values[i]
    if adj_p_value < 0.001:
        adj_p_str = f"{adj_p_value:.3f}***"
    elif adj_p_value < 0.01:
        adj_p_str = f"{adj_p_value:.3f}**"
    elif adj_p_value < 0.05:
        adj_p_str = f"{adj_p_value:.3f}*"
    else:
        adj_p_str = f"{adj_p_value:.3f}"
    ws.cell(row=row, column=7, value=adj_p_str)

    row += 1

    # Add standard errors row in parentheses
    ws.cell(row=row, column=1, value="")
    ws.cell(row=row, column=2, value="")  # Empty cell under Q1 mean
    for col_idx, level in enumerate(quartile_levels, 3):
        std_err_val = result['std_errors'][level]
        ws.cell(row=row, column=col_idx, value=f"({std_err_val:.2f})")
    
    row += 1

# %%
# Add group separators in Excel
current_row = 2
for group_name, topics in TOPIC_GROUPS:
    ws.insert_rows(current_row)
    ws.cell(row=current_row, column=1, value=group_name)
    ws.cell(row=current_row, column=1).font = Font(bold=True, italic=True)
    current_row += 1 + (len(topics) * 2)  # Each topic now takes 2 rows (coefficient + std error)

# %%
# Add note about reference category
ws.cell(row=current_row + 1, column=1, value="Note: Q1 (lowest % Trump vote) is the reference category")
ws.cell(row=current_row + 1, column=1).font = Font(italic=True)

# %%
# Save Excel results
output_path = start.RESULTS_DIR + 'Table11_politics_quartiles_coefficients.xlsx'
wb.save(output_path)
print(f"\nTable exported to {output_path}")

# %%
# Print summary stats
print("\nSummary Statistics:")
print(f"Number of districts analyzed: {len(merge_df)}")
print(f"Number of topics analyzed: {len(ordered_topics)}")
print("Reference category: Q1 (lowest % Trump vote)")
print("Coefficients shown for: Q2, Q3, Q4")

print(f"\nState fixed effects included for {merge_df['state'].nunique()} states")