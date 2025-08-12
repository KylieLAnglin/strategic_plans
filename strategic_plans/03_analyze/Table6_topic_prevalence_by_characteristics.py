# %%
import pandas as pd
import numpy as np
from strategic_plans.library import start
import statsmodels.formula.api as smf
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment

# %%
# Load the top topics to analyze
top_topics_df = pd.read_excel(start.RESULTS_DIR + 'top_topics.xlsx')
print(f"Analyzing {len(top_topics_df)} topics")

# %%

merge_df = pd.read_excel(start.DATA_DIR + "clean/sample_inclusion_with_topics_and_codes.xlsx")
# Define district characteristics to analyze
CHARACTERISTICS = [
    "northeast", "midwest", "west", "south",  # Geography (south is reference)
    "urban", "suburb", "town", "rural",     # Urbanicity (rural is reference) 
    "enrollment_in_thousands",       # District size
    "percent_race_black_hispanic",   # Student demographics
    "percent_race_white",
    "percent_frl",                     # Socioeconomic status
    "mean_test_score",                 # Academic achievement
    "adults_w_ba",                     # Community education
    "medinc_1000",                     # Community income
]

# Scale percentage variables if needed
for var in ["percent_race_black_hispanic", "percent_race_white", "percent_frl"]:
    merge_df[var] = merge_df[var] * 100
merge_df["medinc_1000"] = merge_df["medinc_1000"] / 1000


# Scale enrollment to thousands if needed
merge_df["enrollment_in_thousands"] = merge_df["enrollment_in_thousands"] / 1000


# %%
# Create results workbook
wb = Workbook()
ws = wb.active
ws.title = "Topic Prevalence by Characteristics"

# Set up header
ws['A1'] = "District Characteristic"
ws['A1'].font = Font(bold=True)

# Add topic codes as column headers
col = 2
for _, topic_row in top_topics_df.iterrows():
    topic_code = topic_row['Topic Code']
    ws.cell(row=1, column=col, value=topic_code)
    ws.cell(row=1, column=col).font = Font(bold=True)
    col += 1

# %%
# Run regressions for each topic
row = 2
for char in CHARACTERISTICS:
    # Add characteristic name to first column
    ws.cell(row=row, column=1, value=char)
    ws.cell(row=row, column=1).font = Font(bold=True)
    
    col = 2
    for _, topic_row in top_topics_df.iterrows():
        topic_id = topic_row['Topic ID']
        topic_code = topic_row['Topic Code']
        
        # Simple regression: topic prevalence ~ characteristic
        formula = f"{topic_id} ~ {char}"
        mod = smf.ols(formula=formula, data=merge_df)
        result = mod.fit()
        
        # Extract coefficient, p-value, and standard error
        coef = result.params[char]
        p_val = result.pvalues[char]
        se = result.bse[char]
        
        # Format coefficient with significance stars
        if p_val < 0.001:
            coef_str = f"{coef:.3f}***"
        elif p_val < 0.01:
            coef_str = f"{coef:.3f}**"
        elif p_val < 0.05:
            coef_str = f"{coef:.3f}*"
        else:
            coef_str = f"{coef:.3f}"
        
        # Format standard error
        se_str = f"({se:.3f})"
        
        # Add coefficient to current row
        ws.cell(row=row, column=col, value=coef_str)
        
        # Add standard error to next row
        ws.cell(row=row+1, column=col, value=se_str)
        

        col += 1
    
    # Move to next characteristic (skip one row for standard errors)
    row += 2


# Save results
output_path = start.RESULTS_DIR + 'Table6_topic_prevalence_by_characteristics.xlsx'
wb.save(output_path)

print(f"Table 6 exported to {output_path}")
print("Analysis complete!")

# %%
# Print summary statistics
print("\nSummary Statistics:")
print(f"Number of districts analyzed: {len(merge_df)}")
print(f"Number of topics analyzed: {len(top_topics_df)}")
print(f"Number of characteristics tested: {len(CHARACTERISTICS)}")