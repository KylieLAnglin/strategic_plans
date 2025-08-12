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
# Create combined Academic Achievement topic (Topic_9 + Topic_16)
merge_df['Academic_Achievement'] = merge_df['Topic_9'] + merge_df['Topic_16']

# Add Academic Achievement to top_topics_df
academic_achievement_row = pd.DataFrame({
    'Topic ID': ['Academic_Achievement'],
    'Topic Code': ['Academic Achievement']
})
top_topics_df = pd.concat([top_topics_df, academic_achievement_row], ignore_index=True)

# %%
# Define topic groups for different tables
TOPIC_GROUPS = {
    "Table6_Academic_Topics": ["Topic_1", "Topic_8", "Academic_Achievement"],
    "Table7_Non_Academic_Outcomes": ["Topic_3", "Topic_5", "Topic_12", "Topic_14"],
    "Table8_Family_Community": ["Topic_17", "Topic_20"],
    "Table9_Mechanisms": ["Topic_0", "Topic_22", "Topic_15"]
}

def create_topic_table(topic_codes, table_name):
    # Filter top_topics_df for the specified topics
    filtered_topics = top_topics_df[top_topics_df['Topic ID'].isin(topic_codes)]
    
    if len(filtered_topics) == 0:
        print(f"Warning: No topics found for {table_name}")
        return
    
    # Create workbook for this table
    wb = Workbook()
    ws = wb.active
    ws.title = table_name
    
    # Set up header
    ws['A1'] = "District Characteristic"
    ws['A1'].font = Font(bold=True)
    
    # Add topic codes as column headers
    col = 2
    for _, topic_row in filtered_topics.iterrows():
        topic_code = topic_row['Topic Code']
        ws.cell(row=1, column=col, value=topic_code)
        ws.cell(row=1, column=col).font = Font(bold=True)
        col += 1
    
    # Run regressions for each topic
    row = 2
    for char in CHARACTERISTICS:
        # Add characteristic name to first column
        ws.cell(row=row, column=1, value=char)
        ws.cell(row=row, column=1).font = Font(bold=True)
        
        col = 2
        for _, topic_row in filtered_topics.iterrows():
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
    output_path = start.RESULTS_DIR + f'{table_name}_topic_prevalence_by_characteristics.xlsx'
    wb.save(output_path)
    
    print(f"{table_name} exported to {output_path}")
    return len(filtered_topics)

# %%
# Create all four tables
total_topics_analyzed = 0
for table_name, topic_codes in TOPIC_GROUPS.items():
    print(f"\nCreating {table_name} with topics: {', '.join(topic_codes)}")
    topics_count = create_topic_table(topic_codes, table_name)
    if topics_count:
        total_topics_analyzed += topics_count

print("\nAll tables created successfully!")

# %%
# Print summary statistics
print("\nSummary Statistics:")
print(f"Number of districts analyzed: {len(merge_df)}")
print(f"Total topics analyzed across all tables: {total_topics_analyzed}")
print(f"Number of characteristics tested: {len(CHARACTERISTICS)}")
print(f"Tables created: {len(TOPIC_GROUPS)}")