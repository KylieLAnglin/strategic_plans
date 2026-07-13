# ContentCoder configuration. All paths live here so the app can be
# relocated by editing this single file.

ONEDRIVE_DIR = (
    "/Users/kylie.anglin/Library/CloudStorage/OneDrive-UniversityofConnecticut/"
    "Documents - strategic_plans/"
)

DATA_DIR = ONEDRIVE_DIR + "data/contentcoder/"
DB_PATH = DATA_DIR + "contentcoder.db"
EXPORT_DIR = DATA_DIR + "exports/"

PDF_DIR = ONEDRIVE_DIR + "final_pdfs/"

# Legacy Dedoose exports used by import_dedoose.py
DEDOOSE_EXCERPTS_XLSX = (
    ONEDRIVE_DIR + "data/raw/Dedoose Exports/DedooseChartExcerpts_2025_8_6_853.xlsx"
)
DEDOOSE_CODEBOOK_XLSX = (
    ONEDRIVE_DIR + "data/raw/Dedoose Exports/DedooseCodesExport_2025_8_2_721.xlsx"
)
# Used to match Dedoose media titles to local PDF filenames during import
DOC_METADATA_CSV = ONEDRIVE_DIR + "data/clean/dedoose_doc_df.csv"

# Defines the qual coding sample (include_qual == 1); documents are flagged
# in_sample on scan and the app shows only sample documents by default
SAMPLE_METADATA_CSV = ONEDRIVE_DIR + "data/clean/plans_meta_data_full.csv"

# Written on every new excerpt (matches the Dedoose account name so exports
# filter cleanly in the existing pipeline)
EXCERPT_CREATOR = "kylielanglin"

HOST = "127.0.0.1"
PORT = 8321
