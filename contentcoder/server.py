"""ContentCoder server.

Run with:  python server.py
Then open  http://127.0.0.1:8321
"""

import csv
import json
import os
import re
import sqlite3
import subprocess
import sys
from datetime import date

from flask import Flask, g, jsonify, request, send_file, send_from_directory

import config

app = Flask(__name__, static_folder="static", static_url_path="/static")

SCHEMA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "schema.sql")

CODE_SNAPSHOT_FIELDS = [
    "title",
    "description",
    "parent_id",
    "weighted",
    "weight_min",
    "weight_max",
    "weight_default",
    "is_category",
]


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(config.DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(_exception):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    os.makedirs(config.DATA_DIR, exist_ok=True)
    os.makedirs(config.EXPORT_DIR, exist_ok=True)
    connection = sqlite3.connect(config.DB_PATH)
    with open(SCHEMA_PATH) as schema_file:
        connection.executescript(schema_file.read())
    # Migrations for databases created before these columns existed
    for migration in (
        "ALTER TABLE documents ADD COLUMN in_sample INTEGER NOT NULL DEFAULT 0",
        "ALTER TABLE codes ADD COLUMN is_category INTEGER NOT NULL DEFAULT 0",
    ):
        try:
            connection.execute(migration)
        except sqlite3.OperationalError:
            pass  # column already present
    connection.commit()
    connection.close()


def code_snapshot(db, code_id):
    """JSON snapshot of a code row for the code_history audit log."""
    row = db.execute("SELECT * FROM codes WHERE id = ?", (code_id,)).fetchone()
    if row is None:
        return None
    return json.dumps({field: row[field] for field in CODE_SNAPSHOT_FIELDS})


def record_code_history(db, action, code_id, old_values, new_values):
    db.execute(
        "INSERT INTO code_history (action, code_id, old_values, new_values) VALUES (?, ?, ?, ?)",
        (action, code_id, old_values, new_values),
    )


def document_key(name):
    """Normalized key for matching filenames/titles to sample metadata:
    lowercase, all punctuation runs collapsed to single spaces."""
    stem = re.sub(r"\.(pdf|csv)$", "", name, flags=re.IGNORECASE).lower()
    return re.sub(r"[^a-z0-9]+", " ", stem).strip()


def mark_sample_documents(db):
    """Flag documents that belong to the qual coding sample (include_qual)."""
    sample_keys = set()
    csv.field_size_limit(sys.maxsize)  # the metadata CSV carries full plan text
    with open(config.SAMPLE_METADATA_CSV, newline="") as metadata_file:
        for row in csv.DictReader(metadata_file):
            if row.get("include_qual") in ("1", "1.0"):
                for column in ("pdf_name", "revised_name", "filename"):
                    if row.get(column):
                        sample_keys.add(document_key(row[column]))
    flagged = 0
    for doc in db.execute("SELECT id, pdf_filename, media_title FROM documents"):
        name = doc["pdf_filename"] or doc["media_title"]
        in_sample = 1 if document_key(name) in sample_keys else 0
        db.execute("UPDATE documents SET in_sample = ? WHERE id = ?", (in_sample, doc["id"]))
        flagged += in_sample
    return flagged


# ---------------------------------------------------------------- pages

@app.get("/")
def index():
    return send_from_directory("static", "index.html")


# ---------------------------------------------------------------- documents

@app.get("/api/documents")
def list_documents():
    rows = get_db().execute(
        """
        SELECT d.id, d.pdf_filename, d.media_title, d.coding_status, d.in_sample,
               COUNT(e.id) AS excerpt_count,
               SUM(CASE WHEN e.anchor_status = 'unanchored' THEN 1 ELSE 0 END) AS unanchored_count
        FROM documents d
        LEFT JOIN excerpts e ON e.document_id = d.id
        GROUP BY d.id
        ORDER BY d.media_title COLLATE NOCASE
        """
    ).fetchall()
    return jsonify([dict(row) for row in rows])


@app.post("/api/documents/scan")
def scan_documents():
    db = get_db()
    known_filenames = {
        row["pdf_filename"]
        for row in db.execute(
            "SELECT pdf_filename FROM documents WHERE pdf_filename IS NOT NULL"
        )
    }
    disk_filenames = sorted(
        name for name in os.listdir(config.PDF_DIR) if name.lower().endswith(".pdf")
    )
    added = 0
    for filename in disk_filenames:
        if filename in known_filenames:
            continue
        # A document imported from Dedoose may share this media_title even
        # though its pdf_filename was unresolved; attach rather than duplicate.
        existing = db.execute(
            "SELECT id FROM documents WHERE media_title = ? AND pdf_filename IS NULL",
            (filename,),
        ).fetchone()
        if existing:
            db.execute(
                "UPDATE documents SET pdf_filename = ? WHERE id = ?",
                (filename, existing["id"]),
            )
        else:
            db.execute(
                "INSERT INTO documents (pdf_filename, media_title) VALUES (?, ?)",
                (filename, filename),
            )
        added += 1
    in_sample_count = mark_sample_documents(db)
    db.commit()
    return jsonify(
        {"added": added, "total_on_disk": len(disk_filenames), "in_sample": in_sample_count}
    )


@app.patch("/api/documents/<int:document_id>")
def update_document(document_id):
    payload = request.get_json()
    db = get_db()
    if "coding_status" in payload:
        db.execute(
            "UPDATE documents SET coding_status = ? WHERE id = ?",
            (payload["coding_status"], document_id),
        )
    if "pdf_filename" in payload:
        db.execute(
            "UPDATE documents SET pdf_filename = ? WHERE id = ?",
            (payload["pdf_filename"], document_id),
        )
    db.commit()
    return jsonify({"ok": True})


@app.get("/api/documents/<int:document_id>/pdf")
def document_pdf(document_id):
    row = get_db().execute(
        "SELECT pdf_filename FROM documents WHERE id = ?", (document_id,)
    ).fetchone()
    if row is None or row["pdf_filename"] is None:
        return jsonify({"error": "no PDF file for this document"}), 404
    return send_file(os.path.join(config.PDF_DIR, row["pdf_filename"]))


@app.get("/api/documents/<int:document_id>/excerpts")
def document_excerpts(document_id):
    db = get_db()
    excerpt_rows = db.execute(
        "SELECT * FROM excerpts WHERE document_id = ? ORDER BY page_number, char_start",
        (document_id,),
    ).fetchall()
    excerpts = {row["id"]: {**dict(row), "rects": [], "code_ids": []} for row in excerpt_rows}
    if excerpts:
        placeholders = ",".join("?" * len(excerpts))
        rect_rows = db.execute(
            f"SELECT * FROM excerpt_rects WHERE excerpt_id IN ({placeholders}) ORDER BY rect_order",
            list(excerpts),
        ).fetchall()
        for rect in rect_rows:
            excerpts[rect["excerpt_id"]]["rects"].append(
                {
                    "page_number": rect["page_number"],
                    "x0": rect["x0"],
                    "y0": rect["y0"],
                    "x1": rect["x1"],
                    "y1": rect["y1"],
                }
            )
        code_rows = db.execute(
            f"SELECT excerpt_id, code_id FROM excerpt_codes WHERE excerpt_id IN ({placeholders})",
            list(excerpts),
        ).fetchall()
        for link in code_rows:
            excerpts[link["excerpt_id"]]["code_ids"].append(link["code_id"])
    return jsonify(list(excerpts.values()))


# ---------------------------------------------------------------- excerpts

def replace_excerpt_codes(db, excerpt_id, code_ids):
    db.execute("DELETE FROM excerpt_codes WHERE excerpt_id = ?", (excerpt_id,))
    for code_id in code_ids:
        # Categories are display-only groupings and can never be applied
        db.execute(
            """
            INSERT INTO excerpt_codes (excerpt_id, code_id, weight)
            SELECT ?, id, weight_default FROM codes WHERE id = ? AND is_category = 0
            """,
            (excerpt_id, code_id),
        )


def replace_excerpt_rects(db, excerpt_id, rects):
    db.execute("DELETE FROM excerpt_rects WHERE excerpt_id = ?", (excerpt_id,))
    for order, rect in enumerate(rects):
        db.execute(
            """
            INSERT INTO excerpt_rects (excerpt_id, page_number, x0, y0, x1, y1, rect_order)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                excerpt_id,
                rect["page_number"],
                rect["x0"],
                rect["y0"],
                rect["x1"],
                rect["y1"],
                order,
            ),
        )


@app.post("/api/excerpts")
def create_excerpt():
    payload = request.get_json()
    db = get_db()
    cursor = db.execute(
        """
        INSERT INTO excerpts
            (document_id, page_number, char_start, char_end, excerpt_text,
             excerpt_creator, created_date, anchor_status, source)
        VALUES (?, ?, ?, ?, ?, ?, ?, 'anchored', 'app')
        """,
        (
            payload["document_id"],
            payload["page_number"],
            payload["char_start"],
            payload["char_end"],
            payload["excerpt_text"],
            config.EXCERPT_CREATOR,
            date.today().isoformat(),
        ),
    )
    excerpt_id = cursor.lastrowid
    replace_excerpt_rects(db, excerpt_id, payload.get("rects", []))
    replace_excerpt_codes(db, excerpt_id, payload.get("code_ids", []))
    db.execute(
        """
        UPDATE documents SET coding_status = 'in_progress'
        WHERE id = ? AND coding_status = 'not_started'
        """,
        (payload["document_id"],),
    )
    db.commit()
    return jsonify({"id": excerpt_id})


@app.patch("/api/excerpts/<int:excerpt_id>")
def update_excerpt(excerpt_id):
    payload = request.get_json()
    db = get_db()
    if "code_ids" in payload:
        replace_excerpt_codes(db, excerpt_id, payload["code_ids"])
    if "rects" in payload:
        # Anchoring an unanchored excerpt (manual anchoring UI)
        replace_excerpt_rects(db, excerpt_id, payload["rects"])
        db.execute(
            """
            UPDATE excerpts
            SET anchor_status = 'anchored', page_number = ?, char_start = ?, char_end = ?
            WHERE id = ?
            """,
            (
                payload["page_number"],
                payload.get("char_start"),
                payload.get("char_end"),
                excerpt_id,
            ),
        )
        if payload.get("excerpt_text"):
            db.execute(
                "UPDATE excerpts SET excerpt_text = ? WHERE id = ?",
                (payload["excerpt_text"], excerpt_id),
            )
    if payload.get("anchor_status") == "document_level":
        db.execute(
            "UPDATE excerpts SET anchor_status = 'document_level' WHERE id = ?",
            (excerpt_id,),
        )
    db.commit()
    return jsonify({"ok": True})


@app.delete("/api/excerpts/<int:excerpt_id>")
def delete_excerpt(excerpt_id):
    db = get_db()
    db.execute("DELETE FROM excerpts WHERE id = ?", (excerpt_id,))
    db.commit()
    return jsonify({"ok": True})


@app.get("/api/unanchored")
def list_unanchored():
    rows = get_db().execute(
        """
        SELECT e.id, e.document_id, e.excerpt_text, e.dedoose_range, e.match_quality,
               d.media_title, d.pdf_filename,
               (SELECT GROUP_CONCAT(c.title, ', ')
                FROM excerpt_codes ec JOIN codes c ON c.id = ec.code_id
                WHERE ec.excerpt_id = e.id) AS code_titles
        FROM excerpts e
        JOIN documents d ON d.id = e.document_id
        WHERE e.anchor_status = 'unanchored'
        ORDER BY d.media_title COLLATE NOCASE, e.id
        """
    ).fetchall()
    return jsonify([dict(row) for row in rows])


# ---------------------------------------------------------------- codes

@app.get("/api/codes")
def list_codes():
    rows = get_db().execute(
        """
        SELECT c.*, (SELECT COUNT(*) FROM excerpt_codes ec WHERE ec.code_id = c.id) AS applications
        FROM codes c ORDER BY c.title COLLATE NOCASE
        """
    ).fetchall()
    return jsonify([dict(row) for row in rows])


@app.post("/api/codes")
def create_code():
    payload = request.get_json()
    db = get_db()
    cursor = db.execute(
        """
        INSERT INTO codes (parent_id, title, description, weighted, weight_min,
                           weight_max, weight_default, is_category)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            payload.get("parent_id"),
            payload["title"].strip(),
            payload.get("description", "").strip(),
            payload.get("weighted", 1),
            payload.get("weight_min", 0),
            payload.get("weight_max", 3),
            payload.get("weight_default", 0),
            1 if payload.get("is_category") else 0,
        ),
    )
    code_id = cursor.lastrowid
    record_code_history(db, "create", code_id, None, code_snapshot(db, code_id))
    db.commit()
    return jsonify({"id": code_id})


@app.patch("/api/codes/<int:code_id>")
def update_code(code_id):
    payload = request.get_json()
    db = get_db()
    old_values = code_snapshot(db, code_id)
    if old_values is None:
        return jsonify({"error": "code not found"}), 404
    if "parent_id" in payload and payload["parent_id"] is not None:
        # Reject moves that would create a cycle (new parent is the code
        # itself or one of its descendants)
        ancestor_id = payload["parent_id"]
        while ancestor_id is not None:
            if ancestor_id == code_id:
                return jsonify({"error": "cannot move a code under its own descendant"}), 409
            row = db.execute(
                "SELECT parent_id FROM codes WHERE id = ?", (ancestor_id,)
            ).fetchone()
            ancestor_id = row["parent_id"] if row else None
    for field in ["title", "description", "parent_id"]:
        if field in payload:
            db.execute(
                f"UPDATE codes SET {field} = ? WHERE id = ?", (payload[field], code_id)
            )
    record_code_history(db, "update", code_id, old_values, code_snapshot(db, code_id))
    db.commit()
    return jsonify({"ok": True})


@app.delete("/api/codes/<int:code_id>")
def delete_code(code_id):
    db = get_db()
    child_count = db.execute(
        "SELECT COUNT(*) AS n FROM codes WHERE parent_id = ?", (code_id,)
    ).fetchone()["n"]
    application_count = db.execute(
        "SELECT COUNT(*) AS n FROM excerpt_codes WHERE code_id = ?", (code_id,)
    ).fetchone()["n"]
    if child_count or application_count:
        return (
            jsonify(
                {
                    "error": f"code has {child_count} child code(s) and "
                    f"{application_count} application(s); remove those first"
                }
            ),
            409,
        )
    old_values = code_snapshot(db, code_id)
    db.execute("DELETE FROM codes WHERE id = ?", (code_id,))
    record_code_history(db, "delete", code_id, old_values, None)
    db.commit()
    return jsonify({"ok": True})


@app.get("/api/codes/<int:code_id>/excerpts")
def code_excerpts(code_id):
    """All excerpts carrying this code across all documents. For a category,
    aggregates the excerpts of every descendant code."""
    rows = get_db().execute(
        """
        WITH RECURSIVE subtree(id) AS (
            SELECT id FROM codes WHERE id = ?
            UNION ALL
            SELECT c.id FROM codes c JOIN subtree s ON c.parent_id = s.id
        )
        SELECT DISTINCT e.id, e.document_id, e.page_number, e.excerpt_text,
               e.anchor_status, e.dedoose_range, d.media_title, d.in_sample,
               (SELECT GROUP_CONCAT(c2.title, ', ')
                FROM excerpt_codes ec2 JOIN codes c2 ON c2.id = ec2.code_id
                WHERE ec2.excerpt_id = e.id AND ec2.code_id NOT IN (SELECT id FROM subtree)
               ) AS other_code_titles
        FROM excerpts e
        JOIN excerpt_codes ec ON ec.excerpt_id = e.id AND ec.code_id IN (SELECT id FROM subtree)
        JOIN documents d ON d.id = e.document_id
        ORDER BY d.media_title COLLATE NOCASE, e.page_number, e.id
        """,
        (code_id,),
    ).fetchall()
    return jsonify([dict(row) for row in rows])


@app.get("/api/codes/<int:code_id>/history")
def single_code_history(code_id):
    rows = get_db().execute(
        "SELECT * FROM code_history WHERE code_id = ? ORDER BY id DESC", (code_id,)
    ).fetchall()
    return jsonify([dict(row) for row in rows])


@app.get("/api/codes/history")
def code_history_log():
    rows = get_db().execute(
        "SELECT * FROM code_history ORDER BY id DESC"
    ).fetchall()
    return jsonify([dict(row) for row in rows])


# ---------------------------------------------------------------- export

@app.post("/api/export")
def run_export():
    script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "export_dedoose.py")
    result = subprocess.run(
        [sys.executable, script_path], capture_output=True, text=True
    )
    if result.returncode != 0:
        return jsonify({"error": result.stderr[-2000:]}), 500
    return jsonify({"output": result.stdout})


if __name__ == "__main__":
    init_db()
    print(f"ContentCoder running at http://{config.HOST}:{config.PORT}")
    app.run(host=config.HOST, port=config.PORT, debug=False)
