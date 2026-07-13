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
4. **Export** writes `DedooseChartExcerpts_{ts}.xlsx` + `DedooseCodesExport_{ts}.xlsx`
   plus a timestamped `.db` backup.

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

## Notes

- The SQLite DB lives on OneDrive: keep the default journal mode (do NOT
  enable WAL — its sidecar files sync badly on cloud storage). Exports include
  a DB backup for extra safety.
- Excerpt weights are not exposed in the UI (applied-only coding), but the
  export writes Dedoose's Weight columns (legacy imported weights preserved,
  new applications get the code's default) for format compatibility.
- `media_title` on imported documents keeps the verbatim Dedoose title even
  when it differs from the local filename — the downstream merge depends on it.
