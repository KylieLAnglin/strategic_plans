# ContentCoder

A single-user local web app for qualitative content analysis of PDFs — a
Dedoose replacement. Highlight text in a PDF, apply hierarchical codes, and
export data in the exact Dedoose export formats so the existing analysis
pipeline (`strategic_plans/02_import_and_clean_qual_codes/`) works unchanged.

## Run

```bash
cd contentcoder
python server.py
# open http://127.0.0.1:8321
```

Dependencies (all in the `strategic_plans` conda env): `pip install -r requirements.txt`

## Where things live

- **App code**: this folder (self-contained; edit only `config.py` to relocate).
- **Database**: `Documents - strategic_plans/data/contentcoder/contentcoder.db` (OneDrive).
- **PDFs**: read from `Documents - strategic_plans/final_pdfs/`.
- **Exports**: written to `data/contentcoder/exports/` with Dedoose-style names;
  pin the newest pair in `strategic_plans/library/start.py` exactly as with real
  Dedoose exports.

## Workflow

1. **Scan PDFs** (topbar) registers new files from `final_pdfs/`.
2. Click a document, select text on a page, click codes in the right-hand tree,
   **Save**. The document flips to *in progress*; click its status dot to cycle
   to *complete*.
3. Codebook: ＋ adds codes (＋ on a code row adds a child), ✎ edits, 🗑 deletes
   (refused while a code has children or applications). **Every codebook change
   is archived** in the `code_history` table and exported as a "Change History"
   sheet in the codebook export.
4. The **Export tab** writes the analysis files the pipeline consumes:
   `applied_codes_{date}.csv` (one row per excerpt × applied code) and
   `codebook_{date}.csv` (full codebook incl. category hierarchy and
   `top_level_code`), plus the codebook change archive and a `.db` backup.
   After exporting, pin the new date in `library/start.py`
   (`LATEST_APPLIED_CODES` / `LATEST_CODEBOOK`). A legacy Dedoose-format
   export is also available on the same tab for archival.
5. **Hierarchy**: the Codebook tab supports drag-and-drop re-parenting.
   Purple CATEGORY rows are display/analysis groupings (seeded once from
   `code_crosswalk.xlsx` by `seed_hierarchy.py`): they define the `top_*`
   columns in the analysis but are never applied to excerpts. Every move is
   archived in `code_history`.

## One-time Dedoose migration

```bash
python import_dedoose.py --dry-run   # report only
python import_dedoose.py             # real import
python export_dedoose.py --verify-against "<path to original DedooseChartExcerpts xlsx>"
```

The import reconciles code renames between the two Dedoose export dates
(`MANUAL_TITLE_ALIASES` at the top of `import_dedoose.py`), matches media
titles to local PDFs, and re-anchors each excerpt by fuzzy text matching
(threshold 85). Unmatched excerpts land in the **Unanchored** queue (topbar):
pick one, search the PDF, select the correct text, **Anchor to selection** —
or **Mark document-level**.

## LLM-assisted review (Review tab)

The **Review** tab runs two AI quality checks via the Anthropic API
(Message Batches, model set in `config.py` as `REVIEW_MODEL`):

- **Find missing plans**: for a chosen code, Claude reads every in-sample plan
  *without* that code and proposes verbatim passages that appear to warrant it.
- **Audit existing excerpts**: Claude re-reads each excerpt carrying the code
  against its definition and flags applications that don't fit.

Everything is a proposal: findings queue up in the tab and change nothing
until you Accept (which creates a properly-anchored excerpt with
`excerpt_creator = "claude-assisted"`, or removes a code) or Reject. Costs are
estimated before each run (typically well under $1 per code).

**Setup (one-time):** get an Anthropic API key (platform.claude.com → API keys,
billing required), then launch the server with the key in its environment,
e.g. add `export ANTHROPIC_API_KEY=sk-ant-...` to `~/.zshenv` or to
`LaunchContentCoder.command` before the server start line.

`ocr_pdfs.py` (one-time, already run) added OCR text layers to scanned sample
PDFs so both the LLM and the in-app text selection can read them; originals
are in `final_pdfs_originals/`.

## Notes

- The SQLite DB lives on OneDrive: keep the default journal mode (do NOT
  enable WAL — its sidecar files sync badly on cloud storage). Exports include
  a DB backup for extra safety.
- Excerpt weights are not exposed in the UI (applied-only coding), but the
  export writes Dedoose's Weight columns (legacy imported weights preserved,
  new applications get the code's default) for format compatibility.
- `media_title` on imported documents keeps the verbatim Dedoose title even
  when it differs from the local filename — the downstream merge depends on it.
