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

# LLM-assisted review (Review tab). The API key is read from
# ~/.anthropic_api_key (chmod 600, outside the git repo) unless
# ANTHROPIC_API_KEY is already set. Batch pricing = 50% of standard.
import os as _os

_key_file = _os.path.expanduser("~/.anthropic_api_key")
if "ANTHROPIC_API_KEY" not in _os.environ and _os.path.exists(_key_file):
    with open(_key_file) as _f:
        _os.environ["ANTHROPIC_API_KEY"] = _f.read().strip()

REVIEW_MODEL = "claude-sonnet-5"
REVIEW_PRICE_PER_MTOK_INPUT = 2.00    # Sonnet 5 intro pricing through 2026-08
REVIEW_PRICE_PER_MTOK_OUTPUT = 10.00
REVIEW_MAX_CODES_PER_RUN = 3          # plans are read once per run, so up to
                                      # this many codes share one reading
REVIEW_CONCURRENCY = 4                # parallel live API requests
REVIEW_EXCERPT_CREATOR = "assisted"
