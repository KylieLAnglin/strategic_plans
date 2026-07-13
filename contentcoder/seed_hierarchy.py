"""One-time: build the initial codebook hierarchy from code_crosswalk.xlsx.

Creates one display-only category per top_level_code in the crosswalk and
moves each goal code under its category. Categories are never exported, so
the Dedoose export format is unchanged. Every move is archived in
code_history. Safe to re-run: existing categories are reused and codes
already in place are skipped.
"""

import json
import re
import sqlite3

import pandas as pd

import config

CROSSWALK_XLSX = (
    "/Users/kylie.anglin/strategic_plans/strategic_plans/"
    "02_import_and_clean_qual_codes/code_crosswalk.xlsx"
)

# Same cleaning as 02_import_codes.py so titles map onto crosswalk code_columns
CLEAN_PATTERN = re.compile(
    r"\s+|-|,+|_+|/+|\\|'|\(|\)|&|\.|:|;"
)


def code_column_for_title(title):
    cleaned = CLEAN_PATTERN.sub("_", "code_" + title.lower() + "_applied")
    return re.sub("_+", "_", cleaned).strip("_")


def snapshot(row):
    return json.dumps(
        {
            "title": row["title"],
            "description": row["description"],
            "parent_id": row["parent_id"],
            "weighted": row["weighted"],
            "weight_min": row["weight_min"],
            "weight_max": row["weight_max"],
            "weight_default": row["weight_default"],
            "is_category": row["is_category"],
        }
    )


def main():
    crosswalk_df = pd.read_excel(CROSSWALK_XLSX)
    goal_rows = crosswalk_df[crosswalk_df.code_type == "goal"]

    connection = sqlite3.connect(config.DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")

    code_rows = connection.execute("SELECT * FROM codes").fetchall()
    column_to_code = {code_column_for_title(row["title"]): row for row in code_rows}
    category_ids = {
        row["title"]: row["id"] for row in code_rows if row["is_category"]
    }

    moved = 0
    unmatched = []
    for top_level_title in goal_rows.top_level_code.unique():
        if top_level_title not in category_ids:
            cursor = connection.execute(
                "INSERT INTO codes (title, description, is_category, weighted) "
                "VALUES (?, ?, 1, 0)",
                (top_level_title, f"Category (from code_crosswalk top_level_code)"),
            )
            category_ids[top_level_title] = cursor.lastrowid
            new_row = connection.execute(
                "SELECT * FROM codes WHERE id = ?", (cursor.lastrowid,)
            ).fetchone()
            connection.execute(
                "INSERT INTO code_history (action, code_id, old_values, new_values) "
                "VALUES ('create', ?, NULL, ?)",
                (cursor.lastrowid, snapshot(new_row)),
            )
            print(f"created category: {top_level_title}")

        member_rows = goal_rows[goal_rows.top_level_code == top_level_title]
        for _, crosswalk_row in member_rows.iterrows():
            code_row = column_to_code.get(crosswalk_row.code_column)
            if code_row is None:
                unmatched.append(crosswalk_row.code_column)
                continue
            target_parent = category_ids[top_level_title]
            if code_row["parent_id"] == target_parent:
                continue
            old = snapshot(code_row)
            connection.execute(
                "UPDATE codes SET parent_id = ? WHERE id = ?",
                (target_parent, code_row["id"]),
            )
            updated = connection.execute(
                "SELECT * FROM codes WHERE id = ?", (code_row["id"],)
            ).fetchone()
            connection.execute(
                "INSERT INTO code_history (action, code_id, old_values, new_values) "
                "VALUES ('update', ?, ?, ?)",
                (code_row["id"], old, snapshot(updated)),
            )
            print(f"  {code_row['title']} -> {top_level_title}")
            moved += 1

    if unmatched:
        print("\nWARNING crosswalk columns with no matching code (not moved):")
        for column in unmatched:
            print(f"  {column}")

    connection.commit()
    connection.close()
    print(f"\n{moved} codes moved under {len(category_ids)} categories.")


if __name__ == "__main__":
    main()
