"""Write Dedoose-format export files from the ContentCoder database.

Produces DedooseChartExcerpts_{ts}.xlsx and DedooseCodesExport_{ts}.xlsx in
EXPORT_DIR (plus a timestamped DB backup). The excerpt file matches the
Dedoose chart export column-for-column so the existing analysis pipeline
(02_import_and_clean_qual_codes) consumes it unchanged.

Usage:
    python export_dedoose.py
    python export_dedoose.py --verify-against "<original Dedoose xlsx>"
"""

import os
import shutil
import sqlite3
import sys
from collections import Counter
from datetime import datetime

import pandas as pd

import config


def format_dedoose_date(iso_date):
    parsed = datetime.strptime(iso_date, "%Y-%m-%d")
    return f"{parsed.month}/{parsed.day}/{parsed.year}"


def full_code_paths(code_rows):
    """id -> 'Parent\\Child' export path, and id -> leaf title. Categories are
    display-only hierarchy: they get no path of their own and are skipped when
    building ancestors, so rearranging them never changes export columns."""
    titles = {row["id"]: row["title"] for row in code_rows}
    parents = {row["id"]: row["parent_id"] for row in code_rows}
    categories = {row["id"] for row in code_rows if row["is_category"]}
    paths = {}
    for code_id in titles:
        if code_id in categories:
            continue
        parts = []
        cursor = code_id
        while cursor is not None:
            if cursor not in categories:
                parts.append(titles[cursor])
            cursor = parents[cursor]
        paths[code_id] = "\\".join(reversed(parts))
    return paths, titles


def code_depths(code_rows):
    parents = {row["id"]: row["parent_id"] for row in code_rows}
    depths = {}
    for code_id in parents:
        depth = 0
        cursor = parents[code_id]
        while cursor is not None:
            depth += 1
            cursor = parents[cursor]
        depths[code_id] = depth
    return depths


def load_export_frames(connection):
    code_rows = connection.execute("SELECT * FROM codes").fetchall()
    paths, leaf_titles = full_code_paths(code_rows)
    ordered_code_ids = sorted(paths, key=lambda cid: paths[cid].lower())

    excerpt_rows = connection.execute(
        """
        SELECT e.*, d.media_title, d.resource_creator, d.resource_date
        FROM excerpts e JOIN documents d ON d.id = e.document_id
        ORDER BY d.media_title COLLATE NOCASE, e.id
        """
    ).fetchall()
    code_links = connection.execute(
        "SELECT excerpt_id, code_id, weight FROM excerpt_codes"
    ).fetchall()
    links_by_excerpt = {}
    for link in code_links:
        links_by_excerpt.setdefault(link["excerpt_id"], {})[link["code_id"]] = link["weight"]

    weight_ranges = {
        row["id"]: f"{row['weight_min']:g}-{row['weight_max']:g}" for row in code_rows
    }
    weight_defaults = {row["id"]: row["weight_default"] for row in code_rows}

    excerpt_records = []
    for excerpt in excerpt_rows:
        applied = links_by_excerpt.get(excerpt["id"], {})
        if excerpt["dedoose_range"]:
            excerpt_range = excerpt["dedoose_range"]
        elif excerpt["page_number"] and excerpt["char_start"] is not None:
            excerpt_range = f"Page {excerpt['page_number']}: {excerpt['char_start']}-{excerpt['char_end']}"
        else:
            excerpt_range = None
        record = {
            "Media Title": excerpt["media_title"],
            "Excerpt Range": excerpt_range,
            "Excerpt Creator": excerpt["excerpt_creator"],
            "Excerpt Date": format_dedoose_date(excerpt["created_date"]),
            "Excerpt Copy": excerpt["excerpt_text"],
            "Resource Creator": excerpt["resource_creator"],
            "Resource Date": excerpt["resource_date"],
            "Codes Applied Combined": ", ".join(
                leaf_titles[code_id]
                for code_id in ordered_code_ids
                if code_id in applied
            ),
        }
        for code_id in ordered_code_ids:
            path = paths[code_id]
            is_applied = code_id in applied
            record[f"Code: {path} Applied"] = bool(is_applied)
            record[f"Code: {path} Range"] = weight_ranges[code_id] if is_applied else None
            if is_applied:
                stored_weight = applied[code_id]
                record[f"Code: {path} Weight"] = (
                    stored_weight if stored_weight is not None else weight_defaults[code_id]
                )
            else:
                record[f"Code: {path} Weight"] = None
        excerpt_records.append(record)
    excerpts_frame = pd.DataFrame(excerpt_records)

    application_counts = Counter(link["code_id"] for link in code_links)
    depths = code_depths(code_rows)
    codebook_records = [
        {
            "Id": row["id"],
            "Parent Id": row["parent_id"],
            "Depth": depths[row["id"]],
            "Title": row["title"],
            "Description": row["description"],
            "Weighted": bool(row["weighted"]),
            "Weight Minimum": row["weight_min"],
            "Weight Maximum": row["weight_max"],
            "Weight Default": row["weight_default"],
            "Applications": application_counts.get(row["id"], 0),
            "Category": bool(row["is_category"]),
        }
        for row in sorted(code_rows, key=lambda r: r["id"])
    ]
    codebook_frame = pd.DataFrame(codebook_records)

    history_rows = connection.execute("SELECT * FROM code_history ORDER BY id").fetchall()
    history_frame = pd.DataFrame([dict(row) for row in history_rows])

    return excerpts_frame, codebook_frame, history_frame


def verify_against(excerpts_frame, original_path):
    """Compare per-document multisets of applied leaf-title sets per excerpt
    against the original Dedoose export."""
    original_df = pd.read_excel(original_path)

    def row_signature(frame_row, applied_columns):
        applied_leaves = frozenset(
            column[len("Code: "):-len(" Applied")].split("\\")[-1]
            for column in applied_columns
            if frame_row[column] is True or frame_row[column] == 1
        )
        return (frame_row["Media Title"], applied_leaves)

    original_applied = [c for c in original_df.columns if c.startswith("Code: ") and c.endswith(" Applied")]
    exported_applied = [c for c in excerpts_frame.columns if c.startswith("Code: ") and c.endswith(" Applied")]

    original_signatures = Counter(
        row_signature(row, original_applied) for _, row in original_df.iterrows()
    )
    exported_signatures = Counter(
        row_signature(row, exported_applied) for _, row in excerpts_frame.iterrows()
    )

    missing_from_export = original_signatures - exported_signatures
    extra_in_export = exported_signatures - original_signatures
    if not missing_from_export and not extra_in_export:
        print(f"VERIFY OK: {sum(original_signatures.values())} excerpt rows match "
              f"{os.path.basename(original_path)} exactly (per-document applied-code sets).")
        return True
    print("VERIFY FAILED:")
    for (media_title, applied_leaves), count in list(missing_from_export.items())[:20]:
        print(f"  missing x{count}: {media_title} :: {sorted(applied_leaves)}")
    for (media_title, applied_leaves), count in list(extra_in_export.items())[:20]:
        print(f"  extra   x{count}: {media_title} :: {sorted(applied_leaves)}")
    remaining = max(0, len(missing_from_export) + len(extra_in_export) - 40)
    if remaining:
        print(f"  ... and {remaining} more differences")
    return False


def main():
    connection = sqlite3.connect(config.DB_PATH)
    connection.row_factory = sqlite3.Row

    excerpts_frame, codebook_frame, history_frame = load_export_frames(connection)
    connection.close()

    if "--verify-against" in sys.argv:
        original_path = sys.argv[sys.argv.index("--verify-against") + 1]
        ok = verify_against(excerpts_frame, original_path)
        if not ok:
            sys.exit(1)

    now = datetime.now()
    timestamp = f"{now.year}_{now.month}_{now.day}_{now.hour}{now.minute:02d}"
    os.makedirs(config.EXPORT_DIR, exist_ok=True)

    excerpts_path = os.path.join(config.EXPORT_DIR, f"DedooseChartExcerpts_{timestamp}.xlsx")
    codebook_path = os.path.join(config.EXPORT_DIR, f"DedooseCodesExport_{timestamp}.xlsx")
    excerpts_frame.to_excel(excerpts_path, index=False)
    with pd.ExcelWriter(codebook_path) as writer:
        codebook_frame.to_excel(writer, sheet_name="Codes", index=False)
        if not history_frame.empty:
            history_frame.to_excel(writer, sheet_name="Change History", index=False)

    backup_path = os.path.join(config.EXPORT_DIR, f"contentcoder_backup_{timestamp}.db")
    shutil.copy2(config.DB_PATH, backup_path)

    print(f"Wrote {excerpts_path}")
    print(f"Wrote {codebook_path}")
    print(f"DB backup {backup_path}")
    print(f"{len(excerpts_frame)} excerpts, {len(codebook_frame)} codes exported.")


if __name__ == "__main__":
    main()
