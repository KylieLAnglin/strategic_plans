# %%
import pandas as pd
import numpy as np
import re
from strategic_plans.library import start

# %%
FILE = "DedooseChartExcerpts_2023_11_11_1222.xlsx"
df = pd.read_excel(start.DATA_DIR + "raw/" + FILE)

df.sample()

# %%
df.columns = [col.replace("Code: ", "code_").lower() for col in df.columns]

# List of characters to be replaced with an underscore
patterns = ["\s+", "-", ",+", "_+", "/+", "_", "\"]
regex_pattern = "|".join(patterns)
compiled_pattern = re.compile(regex_pattern)
df.columns = [
    compiled_pattern.sub("_", compiled_pattern.sub("_", col)) for col in df.columns
]
df = df.drop("codes_applied_combined", axis = 1)
df.sample()

# %%
