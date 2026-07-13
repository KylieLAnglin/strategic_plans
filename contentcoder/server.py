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
    "display_name",
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
        "ALTER TABLE review_jobs ADD COLUMN code_ids TEXT",
        "ALTER TABLE review_jobs ADD COLUMN completed_count INTEGER NOT NULL DEFAULT 0",
        "ALTER TABLE review_jobs ADD COLUMN pid INTEGER",
        "ALTER TABLE codes ADD COLUMN display_name TEXT",
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
    for field in ["title", "display_name", "description", "parent_id"]:
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

# ---------------------------------------------------------------- LLM review

@app.post("/api/review/run")
def review_run():
    payload = request.get_json()
    db = get_db()
    running = db.execute(
        "SELECT id FROM review_jobs WHERE status IN ('pending','running')"
    ).fetchone()
    if running:
        return jsonify({"error": f"job {running['id']} is still running"}), 409
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return (
            jsonify({"error": "ANTHROPIC_API_KEY is not set in the server's environment. "
                              "Set it and restart the server (see README)."}),
            400,
        )
    code_ids = payload.get("code_ids") or []
    if not 1 <= len(code_ids) <= config.REVIEW_MAX_CODES_PER_RUN:
        return jsonify({"error": f"select 1-{config.REVIEW_MAX_CODES_PER_RUN} codes"}), 400
    cursor = db.execute(
        "INSERT INTO review_jobs (kind, code_ids, model) VALUES (?,?,?)",
        (payload["kind"], json.dumps(code_ids), payload.get("model", config.REVIEW_MODEL)),
    )
    db.commit()
    job_id = cursor.lastrowid
    script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "review_llm.py")
    log_path = os.path.join(config.DATA_DIR, f"review_job_{job_id}.log")
    with open(log_path, "a") as log_file:
        process = subprocess.Popen(
            [sys.executable, script_path, "--job-id", str(job_id)],
            stdout=log_file, stderr=log_file, start_new_session=True,
        )
    db.execute("UPDATE review_jobs SET pid = ? WHERE id = ?", (process.pid, job_id))
    db.commit()
    return jsonify({"job_id": job_id})


@app.post("/api/review/jobs/<int:job_id>/cancel")
def review_cancel(job_id):
    import signal

    db = get_db()
    job = db.execute("SELECT * FROM review_jobs WHERE id = ?", (job_id,)).fetchone()
    if job is None or job["status"] not in ("pending", "running"):
        return jsonify({"error": "job is not running"}), 409
    if job["pid"]:
        try:
            os.kill(job["pid"], signal.SIGTERM)
        except ProcessLookupError:
            pass
    db.execute(
        "UPDATE review_jobs SET status='error', error='cancelled by user', "
        "completed_at=datetime('now','localtime') WHERE id=?",
        (job_id,),
    )
    db.commit()
    return jsonify({"ok": True})


@app.get("/api/review/jobs")
def review_jobs():
    db = get_db()
    rows = db.execute(
        """
        SELECT j.*,
               (SELECT COUNT(*) FROM review_findings f
                WHERE f.job_id = j.id AND f.status = 'pending') AS pending_findings
        FROM review_jobs j ORDER BY j.id DESC LIMIT 30
        """
    ).fetchall()
    jobs = []
    for row in rows:
        job = dict(row)
        ids = json.loads(job["code_ids"]) if job["code_ids"] else (
            [job["code_id"]] if job["code_id"] else []
        )
        titles = [
            title for (title,) in db.execute(
                f"SELECT title FROM codes WHERE id IN ({','.join('?' * len(ids))})", ids
            )
        ] if ids else []
        job["code_titles"] = ", ".join(titles) if titles else "all codes"
        jobs.append(job)
    return jsonify(jobs)


@app.get("/api/review/estimate")
def review_estimate():
    kind = request.args.get("kind")
    code_ids = [int(x) for x in request.args.get("code_ids", "").split(",") if x]
    db = get_db()
    if not code_ids:
        return jsonify({"requests": 0, "est_tokens": 0, "est_dollars": 0})
    placeholders = ",".join("?" * len(code_ids))
    if kind == "missing":
        # documents missing at least one selected code (each read once)
        request_count = db.execute(
            f"""SELECT COUNT(*) AS n FROM documents d
                WHERE d.in_sample = 1 AND d.pdf_filename IS NOT NULL
                AND (SELECT COUNT(DISTINCT ec.code_id) FROM excerpt_codes ec
                     JOIN excerpts e ON e.id = ec.excerpt_id
                     WHERE e.document_id = d.id AND ec.code_id IN ({placeholders}))
                    < ?""",
            (*code_ids, len(code_ids)),
        ).fetchone()["n"]
        tokens_per_request, output_per_request = 6000, 300
    else:
        request_count = db.execute(
            f"""SELECT COUNT(*) AS n FROM excerpts e
                JOIN excerpt_codes ec ON ec.excerpt_id = e.id
                    AND ec.code_id IN ({placeholders})
                JOIN documents d ON d.id = e.document_id
                WHERE d.in_sample = 1 AND e.excerpt_text IS NOT NULL""",
            code_ids,
        ).fetchone()["n"]
        tokens_per_request, output_per_request = 500, 150

    tokens = request_count * tokens_per_request
    dollars = (
        tokens / 1e6 * config.REVIEW_PRICE_PER_MTOK_INPUT
        + request_count * output_per_request / 1e6 * config.REVIEW_PRICE_PER_MTOK_OUTPUT
    )
    return jsonify(
        {"requests": request_count, "est_tokens": tokens, "est_dollars": round(dollars, 2)}
    )


@app.get("/api/review/prompt")
def review_prompt():
    """The exact system prompt a run would use, for display in the tab."""
    import review_llm

    kind = request.args.get("kind", "missing")
    code_ids = [int(x) for x in request.args.get("code_ids", "").split(",") if x]
    db = get_db()
    code_rows = db.execute(
        f"SELECT * FROM codes WHERE id IN ({','.join('?' * len(code_ids))})", code_ids
    ).fetchall() if code_ids else []

    if kind == "missing":
        blocks = review_llm.missing_code_blocks(code_rows) if code_rows else (
            "1. Title: {selected code}\n   Definition: {its definition}"
        )
        prompt = review_llm.MISSING_SYSTEM_TEMPLATE.format(code_blocks=blocks)
        per_request = ("Each plan missing at least one selected code is read once; "
                       "its full text (with [[page N]] markers) is the user message. "
                       "Codes a plan already has are left out of that plan's request.")
    else:
        first = code_rows[0] if code_rows else None
        prompt = review_llm.AUDIT_SYSTEM_TEMPLATE.format(
            title=first["title"] if first else "{selected code}",
            definition=(first["description"] or "(no definition)") if first else "{its definition}",
        )
        per_request = "The district name and excerpt text are sent as the user message."
        if len(code_rows) > 1:
            per_request += (" With multiple codes selected, each excerpt is judged "
                            "against its own code's version of this prompt.")
    return jsonify({"system_prompt": prompt, "per_request": per_request,
                    "model": config.REVIEW_MODEL})


@app.get("/api/review/findings")
def review_findings():
    rows = get_db().execute(
        """
        SELECT f.*, c.title AS code_title, d.media_title,
               e.excerpt_text AS current_excerpt_text,
               (SELECT GROUP_CONCAT(c2.title, ', ') FROM excerpt_codes ec2
                JOIN codes c2 ON c2.id = ec2.code_id
                WHERE ec2.excerpt_id = f.excerpt_id) AS excerpt_code_titles
        FROM review_findings f
        JOIN codes c ON c.id = f.code_id
        JOIN documents d ON d.id = f.document_id
        LEFT JOIN excerpts e ON e.id = f.excerpt_id
        WHERE f.status = 'pending'
        ORDER BY c.title COLLATE NOCASE, d.media_title COLLATE NOCASE, f.id
        """
    ).fetchall()
    return jsonify([dict(row) for row in rows])


@app.post("/api/review/findings/<int:finding_id>/reject")
def review_reject(finding_id):
    db = get_db()
    db.execute("UPDATE review_findings SET status='rejected' WHERE id=?", (finding_id,))
    db.commit()
    return jsonify({"ok": True})


@app.post("/api/review/findings/<int:finding_id>/accept")
def review_accept(finding_id):
    import fitz
    from anchoring import anchor_excerpt

    payload = request.get_json(silent=True) or {}
    db = get_db()
    finding = db.execute(
        "SELECT * FROM review_findings WHERE id = ?", (finding_id,)
    ).fetchone()
    if finding is None:
        return jsonify({"error": "finding not found"}), 404

    if finding["kind"] == "audit":
        action = payload.get("action", "remove_code")
        if action == "delete_excerpt":
            db.execute("DELETE FROM excerpts WHERE id = ?", (finding["excerpt_id"],))
        else:
            db.execute(
                "DELETE FROM excerpt_codes WHERE excerpt_id = ? AND code_id = ?",
                (finding["excerpt_id"], finding["code_id"]),
            )
        db.execute("UPDATE review_findings SET status='accepted' WHERE id=?", (finding_id,))
        db.commit()
        return jsonify({"ok": True})

    # missing: anchor the proposed quote and create a coded excerpt
    document = db.execute(
        "SELECT * FROM documents WHERE id = ?", (finding["document_id"],)
    ).fetchone()
    anchor_result = None
    if document["pdf_filename"]:
        fitz_document = fitz.open(os.path.join(config.PDF_DIR, document["pdf_filename"]))
        anchor_result = anchor_excerpt(
            fitz_document, {}, finding["proposed_text"], finding["page_hint"]
        )
        fitz_document.close()
    matched = bool(anchor_result and anchor_result.get("matched"))
    cursor = db.execute(
        """INSERT INTO excerpts (document_id, page_number, char_start, char_end,
           excerpt_text, excerpt_creator, created_date, anchor_status, match_quality, source)
           VALUES (?,?,?,?,?,?,?,?,?, 'app')""",
        (
            finding["document_id"],
            anchor_result["page_number"] if matched else finding["page_hint"],
            anchor_result["char_start"] if matched else None,
            anchor_result["char_end"] if matched else None,
            finding["proposed_text"],
            config.REVIEW_EXCERPT_CREATOR,
            date.today().isoformat(),
            "anchored" if matched else "unanchored",
            anchor_result["score"] if anchor_result else None,
        ),
    )
    excerpt_id = cursor.lastrowid
    if matched:
        replace_excerpt_rects(db, excerpt_id, anchor_result["rects"])
    replace_excerpt_codes(db, excerpt_id, [finding["code_id"]])
    db.execute("UPDATE review_findings SET status='accepted' WHERE id=?", (finding_id,))
    db.commit()
    return jsonify({"ok": True, "excerpt_id": excerpt_id, "anchored": matched})


@app.post("/api/export")
def run_export():
    """Run an export script: {"kind": "native"} (default) or {"kind": "dedoose"}."""
    payload = request.get_json(silent=True) or {}
    script_name = "export_dedoose.py" if payload.get("kind") == "dedoose" else "export_native.py"
    script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), script_name)
    result = subprocess.run(
        [sys.executable, script_path], capture_output=True, text=True
    )
    if result.returncode != 0:
        return jsonify({"error": result.stderr[-2000:]}), 500
    return jsonify({"output": result.stdout})


@app.get("/api/exports")
def list_exports():
    """Past export files, newest first."""
    entries = []
    if os.path.isdir(config.EXPORT_DIR):
        for name in os.listdir(config.EXPORT_DIR):
            path = os.path.join(config.EXPORT_DIR, name)
            if os.path.isfile(path):
                entries.append(
                    {
                        "name": name,
                        "size": os.path.getsize(path),
                        "modified": os.path.getmtime(path),
                    }
                )
    entries.sort(key=lambda e: e["modified"], reverse=True)
    return jsonify({"export_dir": config.EXPORT_DIR, "files": entries})


if __name__ == "__main__":
    init_db()
    print(f"ContentCoder running at http://{config.HOST}:{config.PORT}")
    app.run(host=config.HOST, port=config.PORT, debug=False)
