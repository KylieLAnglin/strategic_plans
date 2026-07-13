"""One-shot import of legacy Dedoose exports into ContentCoder.

Reads the codebook and excerpts xlsx exports pinned in config.py, reconciles
code titles between them, matches Dedoose media titles to local PDFs, and
re-anchors each excerpt onto its PDF by fuzzy text matching so historical
highlights render in the app.

Usage:
    python import_dedoose.py            # real import
    python import_dedoose.py --dry-run  # report only, nothing written
"""

import csv
import json
import os
import re
import sqlite3
import sys
from datetime import datetime

import fitz  # pymupdf
import pandas as pd

import config
from anchoring import anchor_excerpt, load_page_words, normalize_with_map

# Codes renamed in Dedoose between the codebook export (8/2) and the excerpts
# export (8/6). Maps the excerpt-export leaf title -> codebook Title (after
# the codebook's "'-'" mangling is fixed). The excerpt-export title wins and
# is written to the codes table, since the analysis crosswalk validates
# against excerpt-export column names. Verified against code_crosswalk.xlsx
# dedoose_title values and codebook descriptions.
MANUAL_TITLE_ALIASES = {
    "21st Century Skills": "Non-cognitive and marketable skills",
    "College and Career Preparation": "College Acceptance and Success",
    "Preserve Local Culture and Language": "Preserve local culture and history",
    "SEL (Social and Emotional Learning)": "SEL (social emotional learning)",
    "ZZ DELETE Family and Community": "Family and Community",
    "ZZ DELETE NEW Community Connection and Buy-in": "NEW Community Connection and Buy-in",
    "ZZ MERGE Community Economic Development": "Community Economic Development",
}


def normalize_title(title):
    cleaned = title.replace("'-'", "-").lower()
    return re.sub(r"[^a-z0-9]+", "", cleaned)



def filename_key(name):
    stem = re.sub(r"\.pdf$", "", name, flags=re.IGNORECASE).lower()
    return re.sub(r"[\s_\-]+", " ", stem).strip()






def parse_excerpt_date(raw_value):
    if pd.isna(raw_value):
        return None
    text = str(raw_value).strip()
    for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%m/%d/%y"):
        try:
            return datetime.strptime(text.split(" ")[0], fmt).date().isoformat()
        except ValueError:
            continue
    return None


def build_code_paths(codebook_df):
    """Full backslash path for each code id, root -> leaf."""
    titles = codebook_df["Title"].to_dict()
    parents = codebook_df["Parent Id"].to_dict()
    paths = {}
    for code_id in codebook_df.index:
        parts = []
        cursor = code_id
        while cursor is not None and not pd.isna(cursor):
            parts.append(titles[int(cursor)])
            cursor = parents[int(cursor)]
        paths[code_id] = "\\".join(reversed(parts))
    return paths


def main():
    dry_run = "--dry-run" in sys.argv
    print(f"{'DRY RUN — ' if dry_run else ''}Importing Dedoose exports into ContentCoder\n")

    connection = sqlite3.connect(config.DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")

    existing_codes = connection.execute("SELECT COUNT(*) AS n FROM codes").fetchone()["n"]
    existing_dedoose = connection.execute(
        "SELECT COUNT(*) AS n FROM excerpts WHERE source = 'dedoose'"
    ).fetchone()["n"]
    if existing_codes or existing_dedoose:
        sys.exit(
            f"Aborting: database already has {existing_codes} codes and "
            f"{existing_dedoose} imported excerpts. Import runs once against a "
            f"fresh codebook; delete {config.DB_PATH} (or the imported rows) first."
        )

    # ------------------------------------------------------------ codebook
    codebook_df = pd.read_excel(config.DEDOOSE_CODEBOOK_XLSX)
    codebook_df["Title"] = codebook_df["Title"].str.replace("'-'", "-", regex=False)
    codebook_df = codebook_df.set_index("Id")
    print(f"Codebook: {len(codebook_df)} codes")

    # ------------------------------------------------------------ excerpts + reconciliation
    excerpts_df = pd.read_excel(config.DEDOOSE_EXCERPTS_XLSX)
    applied_columns = [c for c in excerpts_df.columns if c.startswith("Code: ") and c.endswith(" Applied")]
    excerpt_code_paths = [c[len("Code: "):-len(" Applied")] for c in applied_columns]
    print(f"Excerpts: {len(excerpts_df)} rows, {len(excerpt_code_paths)} code columns")

    codebook_paths = build_code_paths(codebook_df)
    normalized_codebook = {}
    for code_id, path in codebook_paths.items():
        normalized_codebook.setdefault(normalize_title(path), code_id)
    # Leaf-only lookup as fallback (paths in the export always include parents)
    normalized_leaves = {}
    for code_id in codebook_df.index:
        normalized_leaves.setdefault(normalize_title(codebook_df.loc[code_id, "Title"]), code_id)

    path_to_code_id = {}
    unmatched_paths = []
    for path in excerpt_code_paths:
        leaf = path.split("\\")[-1]
        code_id = normalized_codebook.get(normalize_title(path))
        if code_id is None:
            code_id = normalized_leaves.get(normalize_title(leaf))
        if code_id is None and leaf in MANUAL_TITLE_ALIASES:
            code_id = normalized_leaves.get(normalize_title(MANUAL_TITLE_ALIASES[leaf]))
        if code_id is None:
            unmatched_paths.append(path)
        else:
            path_to_code_id[path] = code_id

    if unmatched_paths:
        print("\nUNMATCHED excerpt code columns (add to MANUAL_TITLE_ALIASES):")
        for path in unmatched_paths:
            print(f"  excerpt column: {path!r}")
        print("\nCodebook titles not used by any excerpt column:")
        used_ids = set(path_to_code_id.values())
        for code_id in codebook_df.index:
            if code_id not in used_ids:
                print(f"  codebook: {codebook_paths[code_id]!r}")
        sys.exit("Aborting: reconcile code titles first (nothing was written).")

    # Codebook codes with no excerpt column were merged/deleted in Dedoose
    # between the two export dates (their applications live in other columns
    # of the newer excerpts export). Importing them would add export columns
    # the analysis crosswalk does not know, so they are skipped.
    used_code_ids = set(path_to_code_id.values())
    skipped_code_ids = [cid for cid in codebook_df.index if cid not in used_code_ids]
    for skipped_id in skipped_code_ids:
        children = codebook_df[codebook_df["Parent Id"] == skipped_id].index
        active_children = [c for c in children if c in used_code_ids]
        assert not active_children, (
            f"cannot skip code {skipped_id} ({codebook_df.loc[skipped_id, 'Title']!r}): "
            f"it is the parent of imported code(s) {active_children}"
        )
        print(
            f"  skipping codebook code {skipped_id} "
            f"{codebook_df.loc[skipped_id, 'Title']!r} "
            f"(merged/deleted in Dedoose before the excerpts export)"
        )
    codebook_df = codebook_df.drop(index=skipped_code_ids)

    duplicate_targets = len(path_to_code_id) - len(set(path_to_code_id.values()))
    assert duplicate_targets == 0, "two excerpt columns mapped to the same code"

    # Rename codebook titles where the excerpt export (newer) differs
    renamed = 0
    for path, code_id in path_to_code_id.items():
        excerpt_leaf = path.split("\\")[-1]
        if codebook_df.loc[code_id, "Title"] != excerpt_leaf:
            print(f"  renaming code {code_id}: {codebook_df.loc[code_id, 'Title']!r} -> {excerpt_leaf!r}")
            codebook_df.loc[code_id, "Title"] = excerpt_leaf
            renamed += 1
    print(f"Reconciliation clean ({renamed} title(s) updated to excerpt-export names)\n")

    # Insert codes (preserving Dedoose ids) + history
    for code_id, row in codebook_df.iterrows():
        parent_id = None if pd.isna(row["Parent Id"]) else int(row["Parent Id"])
        values = (
            int(code_id),
            parent_id,
            row["Title"],
            "" if pd.isna(row["Description"]) else str(row["Description"]),
            int(bool(row["Weighted"])),
            float(row["Weight Minimum"]) if not pd.isna(row["Weight Minimum"]) else 0.0,
            float(row["Weight Maximum"]) if not pd.isna(row["Weight Maximum"]) else 3.0,
            float(row["Weight Default"]) if not pd.isna(row["Weight Default"]) else 0.0,
        )
        connection.execute(
            """INSERT INTO codes (id, parent_id, title, description, weighted,
               weight_min, weight_max, weight_default) VALUES (?,?,?,?,?,?,?,?)""",
            values,
        )
        snapshot = json.dumps(
            {
                "title": values[2], "description": values[3], "parent_id": parent_id,
                "weighted": values[4], "weight_min": values[5],
                "weight_max": values[6], "weight_default": values[7],
            }
        )
        connection.execute(
            "INSERT INTO code_history (action, code_id, old_values, new_values) "
            "VALUES ('create', ?, NULL, ?)",
            (int(code_id), snapshot),
        )

    # ------------------------------------------------------------ document matching
    pdf_files = [n for n in os.listdir(config.PDF_DIR) if n.lower().endswith(".pdf")]
    pdf_by_exact = {name: name for name in pdf_files}
    pdf_by_key = {}
    for name in pdf_files:
        pdf_by_key.setdefault(filename_key(name), name)

    metadata_lookup = {}
    if os.path.exists(config.DOC_METADATA_CSV):
        metadata_df = pd.read_csv(config.DOC_METADATA_CSV)
        for _, row in metadata_df.iterrows():
            media_title = row.get("media_title")
            if pd.isna(media_title):
                continue
            candidates = [
                row.get(col)
                for col in ("pdf_name", "revised_name", "original_document_name", "filename")
                if col in metadata_df.columns and not pd.isna(row.get(col))
            ]
            metadata_lookup[str(media_title)] = [str(c) for c in candidates]

    def resolve_pdf(media_title):
        if media_title in pdf_by_exact:
            return media_title
        key = filename_key(media_title)
        if key in pdf_by_key:
            return pdf_by_key[key]
        for candidate in metadata_lookup.get(media_title, []):
            candidate_name = candidate if candidate.lower().endswith(".pdf") else candidate + ".pdf"
            if candidate_name in pdf_by_exact:
                return candidate_name
            candidate_key = filename_key(candidate_name)
            if candidate_key in pdf_by_key:
                return pdf_by_key[candidate_key]
        return None

    media_titles = excerpts_df["Media Title"].dropna().unique()
    document_ids = {}
    unresolved_titles = []
    for media_title in sorted(media_titles):
        first_row = excerpts_df[excerpts_df["Media Title"] == media_title].iloc[0]
        resource_creator = None if pd.isna(first_row.get("Resource Creator")) else str(first_row["Resource Creator"])
        resource_date = None if pd.isna(first_row.get("Resource Date")) else str(first_row["Resource Date"])
        resolved_filename = resolve_pdf(media_title)
        if resolved_filename:
            existing = connection.execute(
                "SELECT id FROM documents WHERE pdf_filename = ?", (resolved_filename,)
            ).fetchone()
            if existing:
                connection.execute(
                    """UPDATE documents SET media_title = ?, resource_creator = ?,
                       resource_date = ?, coding_status = 'in_progress' WHERE id = ?""",
                    (media_title, resource_creator, resource_date, existing["id"]),
                )
                document_ids[media_title] = existing["id"]
                continue
        else:
            unresolved_titles.append(media_title)
        cursor = connection.execute(
            """INSERT INTO documents (pdf_filename, media_title, resource_creator,
               resource_date, coding_status) VALUES (?, ?, ?, ?, 'in_progress')""",
            (resolved_filename, media_title, resource_creator, resource_date),
        )
        document_ids[media_title] = cursor.lastrowid

    print(
        f"Documents: {len(media_titles)} media titles, "
        f"{len(media_titles) - len(unresolved_titles)} matched to PDFs, "
        f"{len(unresolved_titles)} unresolved"
    )

    # ------------------------------------------------------------ excerpt rows + anchoring
    weight_columns = {
        path: f"Code: {path} Weight" for path in excerpt_code_paths
        if f"Code: {path} Weight" in excerpts_df.columns
    }
    page_hint_pattern = re.compile(r"Page\s+(\d+)\s*:")

    report_rows = []
    status_counts = {}
    excerpts_df = excerpts_df.sort_values("Media Title", kind="stable")

    current_pdf_title = None
    fitz_document = None
    page_cache = {}

    for xlsx_index, row in excerpts_df.iterrows():
        media_title = row["Media Title"]
        if pd.isna(media_title):
            continue
        document_id = document_ids[media_title]
        excerpt_text = None if pd.isna(row.get("Excerpt Copy")) else str(row["Excerpt Copy"])
        dedoose_range = None if pd.isna(row.get("Excerpt Range")) else str(row["Excerpt Range"])
        creator = "" if pd.isna(row.get("Excerpt Creator")) else str(row["Excerpt Creator"])
        created_date = parse_excerpt_date(row.get("Excerpt Date")) or "1970-01-01"

        hinted_page = None
        if dedoose_range:
            hint_match = page_hint_pattern.search(dedoose_range)
            if hint_match:
                hinted_page = int(hint_match.group(1))

        pdf_row = connection.execute(
            "SELECT pdf_filename FROM documents WHERE id = ?", (document_id,)
        ).fetchone()
        pdf_filename = pdf_row["pdf_filename"]

        anchor_result = None
        if excerpt_text is None:
            status = "document_level"
        elif pdf_filename is None:
            status = "pdf_unresolved"
        else:
            if media_title != current_pdf_title:
                if fitz_document is not None:
                    fitz_document.close()
                fitz_document = fitz.open(os.path.join(config.PDF_DIR, pdf_filename))
                page_cache = {}
                current_pdf_title = media_title
            anchor_result = anchor_excerpt(fitz_document, page_cache, excerpt_text, hinted_page)
            if anchor_result and anchor_result["matched"]:
                status = "exact" if anchor_result["score"] >= 100 else "fuzzy"
            else:
                status = "unanchored"

        anchor_status = {
            "document_level": "document_level",
            "pdf_unresolved": "unanchored",
            "unanchored": "unanchored",
            "exact": "anchored",
            "fuzzy": "anchored",
        }[status]

        cursor = connection.execute(
            """INSERT INTO excerpts (document_id, page_number, char_start, char_end,
               excerpt_text, excerpt_creator, created_date, anchor_status,
               match_quality, source, dedoose_range)
               VALUES (?,?,?,?,?,?,?,?,?, 'dedoose', ?)""",
            (
                document_id,
                anchor_result["page_number"] if anchor_result and anchor_result["matched"] else hinted_page,
                anchor_result["char_start"] if anchor_result and anchor_result["matched"] else None,
                anchor_result["char_end"] if anchor_result and anchor_result["matched"] else None,
                excerpt_text,
                creator,
                created_date,
                anchor_status,
                anchor_result["score"] if anchor_result else None,
                dedoose_range,
            ),
        )
        excerpt_id = cursor.lastrowid

        if anchor_result and anchor_result["matched"]:
            for order, rect in enumerate(anchor_result["rects"]):
                connection.execute(
                    """INSERT INTO excerpt_rects (excerpt_id, page_number, x0, y0, x1, y1, rect_order)
                       VALUES (?,?,?,?,?,?,?)""",
                    (excerpt_id, rect["page_number"], rect["x0"], rect["y0"], rect["x1"], rect["y1"], order),
                )

        for path, code_id in path_to_code_id.items():
            applied_value = row.get(f"Code: {path} Applied")
            if applied_value is True or applied_value == 1:
                weight_value = row.get(weight_columns.get(path, ""), None)
                weight = None if weight_value is None or pd.isna(weight_value) else float(weight_value)
                connection.execute(
                    "INSERT OR IGNORE INTO excerpt_codes (excerpt_id, code_id, weight) VALUES (?,?,?)",
                    (excerpt_id, code_id, weight),
                )

        status_counts[status] = status_counts.get(status, 0) + 1
        report_rows.append(
            {
                "media_title": media_title,
                "xlsx_row": xlsx_index,
                "excerpt_id": excerpt_id,
                "status": status,
                "match_quality": anchor_result["score"] if anchor_result else "",
                "hinted_page": hinted_page or "",
                "matched_page": anchor_result["page_number"] if anchor_result and anchor_result["matched"] else "",
            }
        )
        total_done = len(report_rows)
        if total_done % 500 == 0:
            print(f"  ...{total_done}/{len(excerpts_df)} excerpts processed")

    if fitz_document is not None:
        fitz_document.close()

    # ------------------------------------------------------------ report
    os.makedirs(config.DATA_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = os.path.join(config.DATA_DIR, f"import_report_{timestamp}.csv")
    with open(report_path, "w", newline="") as report_file:
        writer = csv.DictWriter(report_file, fieldnames=list(report_rows[0].keys()))
        writer.writeheader()
        writer.writerows(report_rows)

    print("\nImport summary:")
    for status, count in sorted(status_counts.items()):
        print(f"  {status:>16}: {count}")
    if unresolved_titles:
        print(f"\nMedia titles with no matching PDF ({len(unresolved_titles)}):")
        for title in unresolved_titles:
            print(f"  {title}")
    print(f"\nReport: {report_path}")

    if dry_run:
        connection.rollback()
        print("\nDRY RUN — database not modified.")
    else:
        connection.commit()
        print("\nImport committed.")
    connection.close()


if __name__ == "__main__":
    main()
