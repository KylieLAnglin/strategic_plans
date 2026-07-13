"""Write ContentCoder's native analysis exports.

Produces three dated CSVs in EXPORT_DIR (plus a DB backup):
  applied_codes_{YYYY_MM_DD}.csv     one row per excerpt x applied code
  codebook_{YYYY_MM_DD}.csv          full codebook incl. categories/hierarchy
  codebook_history_{YYYY_MM_DD}.csv  the append-only codebook change archive

The analysis pipeline (strategic_plans/02_import_and_clean_qual_codes)
consumes the first two; top-level groupings come from the codebook's
category hierarchy, so reorganizing codes in the app flows through to
analysis on the next export.

Usage: python export_native.py
"""

import os
import shutil
import sqlite3
from collections import Counter
from datetime import datetime

import pandas as pd

import config


def main():
    connection = sqlite3.connect(config.DB_PATH)
    connection.row_factory = sqlite3.Row

    code_rows = connection.execute("SELECT * FROM codes").fetchall()
    titles = {row["id"]: row["title"] for row in code_rows}
    parents = {row["id"]: row["parent_id"] for row in code_rows}
    categories = {row["id"] for row in code_rows if row["is_category"]}

    # Nearest category ancestor = the code's top-level grouping. code_path is
    # the non-category ancestor chain (the basis for analysis column names,
    # matching how Dedoose named columns): 'Student Subgroups\\At-Risk'.
    top_level_of = {}
    depth_of = {}
    path_of = {}
    code_path_of = {}
    for code_id in titles:
        chain = []
        cursor = code_id
        while cursor is not None:
            chain.append(cursor)
            cursor = parents[cursor]
        depth_of[code_id] = len(chain) - 1
        path_of[code_id] = " > ".join(titles[c] for c in reversed(chain))
        code_path_of[code_id] = "\\".join(
            titles[c] for c in reversed(chain) if c not in categories
        )
        ancestor_categories = [c for c in chain[1:] if c in categories]
        top_level_of[code_id] = titles[ancestor_categories[0]] if ancestor_categories else ""

    application_counts = Counter(
        row["code_id"]
        for row in connection.execute("SELECT code_id FROM excerpt_codes")
    )

    codebook_frame = pd.DataFrame(
        [
            {
                "code_id": row["id"],
                "code_title": row["title"],
                "display_name": row["display_name"] or row["title"],
                "code_path": code_path_of[row["id"]],
                "is_category": int(row["is_category"]),
                "parent_id": row["parent_id"],
                "parent_title": titles.get(row["parent_id"], ""),
                "top_level_code": top_level_of[row["id"]],
                "depth": depth_of[row["id"]],
                "full_path": path_of[row["id"]],
                "description": row["description"],
                "applications": application_counts.get(row["id"], 0),
            }
            for row in sorted(code_rows, key=lambda r: (r["is_category"] == 0, path_of[r["id"]].lower()))
        ]
    )

    applied_rows = connection.execute(
        """
        SELECT e.id AS excerpt_id, d.media_title, d.pdf_filename, d.in_sample,
               e.page_number, e.excerpt_text, e.excerpt_creator,
               e.created_date AS date_coded, e.anchor_status,
               ec.code_id
        FROM excerpt_codes ec
        JOIN excerpts e ON e.id = ec.excerpt_id
        JOIN documents d ON d.id = e.document_id
        ORDER BY d.media_title COLLATE NOCASE, e.id, ec.code_id
        """
    ).fetchall()
    applied_frame = pd.DataFrame(
        [
            {
                **dict(row),
                "code_title": titles[row["code_id"]],
                "top_level_code": top_level_of[row["code_id"]],
            }
            for row in applied_rows
        ]
    )

    history_rows = connection.execute("SELECT * FROM code_history ORDER BY id").fetchall()
    history_frame = pd.DataFrame([dict(row) for row in history_rows])
    connection.close()

    date_stamp = datetime.now().strftime("%Y_%m_%d")
    os.makedirs(config.EXPORT_DIR, exist_ok=True)
    applied_path = os.path.join(config.EXPORT_DIR, f"applied_codes_{date_stamp}.csv")
    codebook_path = os.path.join(config.EXPORT_DIR, f"codebook_{date_stamp}.csv")
    history_path = os.path.join(config.EXPORT_DIR, f"codebook_history_{date_stamp}.csv")
    backup_path = os.path.join(config.EXPORT_DIR, f"contentcoder_backup_{date_stamp}.db")

    applied_frame.to_csv(applied_path, index=False)
    codebook_frame.to_csv(codebook_path, index=False)
    history_frame.to_csv(history_path, index=False)
    shutil.copy2(config.DB_PATH, backup_path)

    print(f"Wrote {applied_path} ({len(applied_frame)} code applications)")
    print(f"Wrote {codebook_path} ({len(codebook_frame)} codes)")
    print(f"Wrote {history_path} ({len(history_frame)} archived changes)")
    print(f"DB backup {backup_path}")


if __name__ == "__main__":
    main()
