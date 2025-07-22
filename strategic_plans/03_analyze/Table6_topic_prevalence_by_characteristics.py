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

# Load topic prevalence data (grouped by district)
doc_topics_df = pd.read_excel(start.DATA_DIR + 'final_model/topic_model/doc_topics_grouped.xlsx')
# district_mapping = {
#       "Academy School District No": "ACADEMY SCHOOL DISTRICT NO. 20 IN THE COUNTY OF EL PASO AN",
#       "ALEXANDRIA CITY PBLC SCHS": "ALEXANDRIA COMMUNITY SCHOOL CORP",
#       "Archbold-Area Local": "ARCHBOLD-AREA LOCAL SCHOOL DISTRICT",
#       "ARLINGTON CO PBLC SCHS": "ARLINGTON COUNTY PUBLIC SCHOOLS",
#       "Aurora Joint District No": "AURORA JOINT DISTRICT NO. 28 IN THE COUNTY OF ARAPAHOE A",
#       "BUFFALO CITY SCHOOL DISTRICT": "BUFFALO CITY SD",
#       "Cannon County": "CANNON COUNTY SCHOOL SYSTEM",
#       "Clear Creek School District No": "CLEAR CREEK SCHOOL DISTRICT NO. RE-1 IN THE COUNTY OF ",
#       "Colorado Springs School District No": "COLORADO SPRINGS SCHOOLDISTRICT NO. 11 IN THE COUNTY ",
#       "CRS1020D": "COLORADO RIVER UNION HIGH SCHOOL DISTRICT",
#       "DeSmet Elem": "DESMET ELEMENTARY SCHOOL DISTRICT",
#       "DICKENSON CO PBLC SCHS": "DICKENSON COUNTY PUBLIC SCHOOLS",
#       "Englewood School District No": "ENGLEWOOD SCHOOL DISTRICT NO. 1 IN THE COUNTY OF ARAPAH",
#       "Fayette Public Schools": "FAYETTE COUNTY BOARD OF EDUCATION",
#       "Flagstaff Unified District (4192)": "FLAGSTAFF UNIFIED SCHOOL DISTRICT",
#       "FORT PLAIN CENTRAL SCHOOL DISTRICT": "FORT PLAIN CSD",
#       "Glenwood City School District": "GLENWOOD CITY SCHOOL DISTRICT",
#       "GOUVERNEUR CENTRAL SCHOOL DISTRICT": "GOUVERNEUR CSD",
#       "GreeleySchool District No": "GREELEY SCHOOL DISTRICT NO. 6 IN THE COUNTY OF WELD AN",
#       "HALDANE CENTRAL SCHOOL DISTRICT": "HALDANE CSD",
#       "HAMPTON CITY PBLC SCHS": "HAMPTON CITY PUBLIC SCHOOLS",
#       "HARPURSVILLE CENTRAL SCHOOL DISTRICT": "HARPURSVILLE CSD",
#       "Jackson Grammar": "JACKSON COUNTY SCHOOL DISTRICT",
#       "Liberty Elementary District (4266)": "LIBERTY ELEMENTARY SCHOOL DISTRICT",
#       "LOWVILLE ACADEMY & CENTRAL SCHOOL DISTRICT": "LOWVILLE ACADEMY & CSD",
#       "MALONE CENTRAL SCHOOL DISTRICT": "MALONE CSD",
#       "MANASSAS CITY PBLC SCHS": "MANASSAS CITY PUBLIC SCHOOLS",
#       "Manitou Springs School District No": "MANITOU SPRINGS SCHOOL DISTRICT NO. 14 IN THE COUNTY ",
#       "MEADOWS VALLEY DISTRICT": "MEADOWS VALLEY SCHOOL DISTRICT NO. 11",
#       "Mesa County Valley School District No": "MESA COUNTY VALLEY SCHOOL DISTRICT NO. 51 IN THE COUN",
#       "Nadaburg Unified School District (4252)": "NADABURG UNIFIED SCHOOL DISTRICT",
#       "Newton Conover City Schools": "NEWTON CONOVER CITY SCHOOLS",
#       "PAGE CO PBLC SCHS": "PAGE COUNTY PUBLIC SCHOOLS",
#       "Peotone CUSD 207U": "PEOTONE COMMUNITY UNIT SCHOOL DISTRICT 207U",
#       "PLATTE CO": "PLATTE COUNTY SCHOOL SYSTEM",
#       "Pueblo School District No": "PUEBLO SCHOOL DISTRICT NO. 60 IN THE COUNTY OF PUEBLO",
#       "Reedsville School District": "REEDSVILLE SCHOOL DISTRICT",
#       "RENICK R-V": "RENICK R-V SCHOOL DISTRICT",
#       "Richmond Elementary": "RICHMOND ELEMENTARY SCHOOL DISTRICT",
#       "ROANOKE CITY PBLC SCHS": "ROANOKE CITY PUBLIC SCHOOLS",
#       "ROCHESTER CITY SCHOOL DISTRICT": "ROCHESTER CSD",
#       "ROCHESTER PUBLIC SCHOOL DISTRICT": "ROCHESTER PUBLIC SCHOOL DISTRICT ISD 535",
#       "RSU 17": "REGIONAL SCHOOL UNIT 17",
#       "RSU 17_MSAD 17": "REGIONAL SCHOOL UNIT 17/MSAD 17",
#       "RSU 80": "REGIONAL SCHOOL UNIT 80",
#       "RSU 80_MSAD 04": "REGIONAL SCHOOL UNIT 80/MSAD 04",
#       "Salem Public Schools": "SALEM PUBLIC SCHOOL DISTRICT 24J",
#       "San Jacinto": "SAN JACINTO UNIFIED SCHOOL DISTRICT",
#       "School District No": "SCHOOL DISTRICT NO. 1 IN THE COUNTY OF DENVER AND CITY",
#       "SOUTHERN BOONE CO": "SOUTHERN BOONE COUNTY R-I SCHOOL DISTRICT",
#       "ST": "ST. HELENA UNIFIED SCHOOL DISTRICT",
#       "SYRACUSE CITY SCHOOL DISTRICT": "SYRACUSE CSD",
#       "TACONIC HILLS CENTRAL SCHOOL DISTRICT": "TACONIC HILLS CSD",
#       "TROY CITY SCHOOL DISTRICT": "TROY CITY SCHOOL DISTRICT",
#       "Ventnor City School District": "VENTNOR CITY SCHOOL DISTRICT"
#   }
# doc_topics_df["district"] = doc_topics_df["district"].replace(district_mapping)
doc_topics_df["district"] = doc_topics_df["district"].str.lower()
# Load district characteristics
char_df = pd.read_csv(start.DATA_DIR + 'clean/stratified_sample_characteristics.csv')
char_df["district"] = char_df["district"].str.lower()


# %%
# Merge prevalence data with district characteristics
merge_df = doc_topics_df.merge(char_df, on = "district", how='outer', indicator=True)
merge_df._merge.value_counts() # left_only a problem. right only includes districts without plans
# %%
merge_df[merge_df._merge == "left_only"].to_csv(start.RESULTS_DIR + 'left_only_districts_topics.csv', index=False)
merge_df[merge_df._merge == "right_only"].to_csv(start.RESULTS_DIR + 'right_only_districts_sample.csv', index=False)
merge_df = merge_df[merge_df._merge == "both"]
print(f"Merged data has {len(merge_df)} districts")

# %%
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

# Rename int columns to "Topic_" + int
for col in merge_df.columns:
    if str(col) in map(str, range(0, 100)):
        merge_df.rename(columns={col: f"Topic_{col}"}, inplace=True)
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