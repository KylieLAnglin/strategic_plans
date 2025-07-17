# %%
import pandas as pd

from strategic_plans.library import start, format_tables
import statsmodels.api as sm
import statsmodels.formula.api as smf
from openpyxl import load_workbook
import os
from openpyxl import Workbook
import numpy as np
# %%
codebook_df = pd.read_excel(start.DATA_DIR + "raw/Dedoose Exports/DedooseCodesExport_2025_7_15_1538.xlsx")

codebook_df = codebook_df.rename(columns={"Id": "code_id", "Parent Id": "parent_id", "Title": "code_title", "Description": "code_description"})
codebook_df["parent_id"] = np.where(codebook_df["parent_id"].isnull(), codebook_df.code_id, codebook_df["parent_id"])

# %%
codebook_df.parent_id.nunique()

codebook_df.code_id.nunique()