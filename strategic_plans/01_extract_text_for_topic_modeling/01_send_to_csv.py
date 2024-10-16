import os
import re
import random
import pandas as pd
import numpy as np
from tqdm import tqdm
import layoutparser as lp
import string

from strategic_plans.library import start
from strategic_plans.library import parse_pdfs

# %%

meta_data_df = start.DATA_DIR + "clean/meta_data_df.csv"
# %%
