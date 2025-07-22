# %%
import pandas as pd
import numpy as np

from strategic_plans.library import start

# %%
INPUT_SAMPLE_DF = start.DATA_DIR + "clean/stratified_sample_characteristics.csv"
INPUT_TEXT_DF = start.DATA_DIR + "clean/plans_meta_data_full.csv"
INPUT_CODE_DF = start.DATA_DIR + "clean/plans_codes.csv"
INPUT_TOPIC_DF = start.DATA_DIR + "final_model/topic_model/doc_topics_grouped.xlsx"
INPUT_CSV_META_DATA_DF = start.DATA_DIR + "clean/meta_data_df.csv"
INPUT_SAMPLE_INCLUSION_DF = start.DATA_DIR + "sample_inclusion.xlsx"
sample_df = pd.read_csv(INPUT_SAMPLE_DF) # merge options: leaid, district (all caps)
text_df = pd.read_csv(INPUT_TEXT_DF) # merge options: leaid, lea_name (mixed caps), pdf_name (mixed_caps)
code_df = pd.read_csv(INPUT_CODE_DF) # merge options: leaid, lea_name (mixed caps), dedoose_name (mixed caps)
topic_df = pd.read_excel(INPUT_TOPIC_DF) # merge options: district (mixed caps)
meta_data_df = pd.read_csv(INPUT_CSV_META_DATA_DF) # merge options: leaid, lea_name, pdf_name (nothing new?)
sample_inclusion_df = pd.read_excel(INPUT_SAMPLE_INCLUSION_DF) # merge options: leaid, lea_name, pdf_name



# %% Clean topic df
# add "topic_" prefix to column names other than district
topic_df.columns = ["district"] + [f"topic_{col}" for col in topic_df.columns[1:]]
topic_df.sample()
# %%
# # Try merging text_temp_df with topic_df on lea_name and district
# temp_df = text_df.merge(topic_df, left_on="lea_name", right_on="district", how="outer", indicator="_merge_text_models")
# temp_df._merge_text_models.value_counts()  # Check merge results
# # 55 only in topic_df (very strange)
# # 45 only in text_df (also strange)
# # How were topic models created?
# # In 01_extract_document_meta_data_and_text.py, district is simply the pdf name less the ".pdf"
# # %%
# temp_df = text_df.merge(topic_df, left_on="pdf_name", right_on="district", how="outer", indicator="_merge_text_models")
# temp_df._merge_text_models.value_counts()  # Check merge results
# # 64 only in topic_df (we may have downloaded plans before finalizing the sample. Maybe this isn't a problem.)
# # 54 only in text_df 
# # There's a final_pdfs folder!
# # %%

# temp_df = sample_inclusion_df.merge(topic_df, left_on="revised_name", right_on="district", how="outer", indicator="_merge_sample_topic")
# temp_df._merge_sample_topic.value_counts()  # Check merge results
# # AHA! 46 only in topic_df. 450 only in sample_inclusion_df (no plan)
# only_in_topic = temp_df[temp_df._merge_sample_topic == "right_only"]["district"].unique()
# print("Districts only in topic_df:", only_in_topic)

# # %%
# temp_df = sample_df.merge(code_df, on = "leaid", how='outer', indicator="_merge_sample_code")
# temp_df._merge_sample_code.value_counts()  # Check merge results
# %%
# sample topic overlap
topic_sample = sample_inclusion_df.merge(topic_df, left_on="revised_name", right_on="district", how="inner")
# keep leaid and topic columns
topic_sample = topic_sample[["leaid"] + [col for col in topic_sample.columns if col.startswith("topic_")]]

# sample code overlap
code_sample = sample_df.merge(code_df, on = "leaid", how='inner')
code_columns = [col for col in code_sample.columns if "applied" in col]
code_columns = [col for col in code_columns if "title" not in col]  # remove title columns
# keep leaid and code columns
code_sample = code_sample[["leaid"] + code_columns]

df = sample_df.merge(topic_sample, on="leaid", how='left', indicator="_merge_sample_topic")
df = df.merge(code_sample, on="leaid", how='left', indicator="_merge_sample_code")

df["in_model_sample"] = np.where(df._merge_sample_topic == "both", 1, 0)
df["in_human_sample"] = np.where(df._merge_sample_code == "both", 1, 0)
df = df.drop(columns=["_merge_sample_topic", "_merge_sample_code"])

df.sample()

# count if in both model and human sample
in_both = df[(df.in_model_sample == 1) & (df.in_human_sample == 1)]
print(f"Number of districts in both model and human sample: {len(in_both)}")
print(f"Number of districts in model sample only: {len(df[df.in_model_sample == 1]) - len(in_both)}")
print(f"Number of districts in human sample only: {len(df[df.in_human_sample == 1]) - len(in_both)}")
print(f"Number of districts not in model sample: {len(df) - len(df[df.in_model_sample == 1])}")

df.to_excel(start.DATA_DIR + "clean/sample_inclusion_with_topics_and_codes.xlsx", index=False)