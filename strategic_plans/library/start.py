USER_DIR = "/Users/kla21002/"
USER_DIR = "/Users/kylie.anglin/"

MAIN_DIR = (
    USER_DIR
    + "Library/CloudStorage/OneDrive-UniversityofConnecticut/Documents - strategic_plans/"
)

DATA_DIR = MAIN_DIR + "data/"
RESULTS_DIR = MAIN_DIR + "results/"


NATIONAL_DIR = USER_DIR + "Library/CloudStorage/Dropbox/Research/national_data/data/"

# Current ContentCoder exports — update these two lines (only) after a new
# export from the app's Export tab (files are dated applied_codes_YYYY_MM_DD)
CONTENTCODER_EXPORT_DIR = DATA_DIR + "contentcoder/exports/"
LATEST_APPLIED_CODES = CONTENTCODER_EXPORT_DIR + "applied_codes_2026_07_13.csv"
LATEST_CODEBOOK = CONTENTCODER_EXPORT_DIR + "codebook_2026_07_13.csv"

# Legacy Dedoose exports (pre-ContentCoder; kept for archival reference only)
LATEST_CHART_EXPORT = DATA_DIR + "raw/Dedoose Exports/DedooseChartExcerpts_2025_8_6_853.xlsx"
LATEST_CODEBOOK_EXPORT = DATA_DIR + "raw/Dedoose Exports/DedooseCodesExport_2025_8_2_721.xlsx"

# Codebook of record: one row per code with display names, top-level codes,
# and inclusion decisions; lives in the git repo because it records analytic
# decisions, not data
CODE_DIR = USER_DIR + "strategic_plans/strategic_plans/"
CROSSWALK_FILE = CODE_DIR + "02_import_and_clean_qual_codes/code_crosswalk.xlsx"
