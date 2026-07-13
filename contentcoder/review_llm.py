"""LLM-assisted coding review via live (non-batch) Anthropic API calls.

Two pipelines, both producing human-verified findings in the Review tab:
  missing  Read every in-sample plan missing at least one of the selected
           codes ONCE, assessing all selected codes in that single reading,
           and propose verbatim passages (recall check).
  audit    Re-read each excerpt carrying a selected code against the code's
           definition and flag applications that do not fit (precision check).

Requests run in parallel (config.REVIEW_CONCURRENCY) and findings are written
to the database as each one completes, so the Review tab fills up live.

Usage:
    python review_llm.py --kind missing --code-ids 2,33 [--dry-run]
    python review_llm.py --kind audit --code-ids 2
    python review_llm.py --job-id 7          # run an existing job row
"""

import argparse
import json
import sqlite3
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

import fitz

import config

CONFIDENCE = {"type": "string", "enum": ["high", "medium", "low"]}

MISSING_SYSTEM_TEMPLATE = """You are assisting a qualitative researcher who codes school district strategic plans. Your job is to check whether a plan contains passages that should carry specific codes but were missed by human coders.

The codes to assess:
{code_blocks}

Rules:
- Only propose passages that genuinely match a code's definition, including any restrictions it states (e.g. "only code if..." clauses).
- Quotes must be VERBATIM, copied exactly from the document text, 10-60 words, from a single page. Use the [[page N]] markers to report the page number.
- Report the matching code's title in the "code" field exactly as written above.
- A human researcher reviews every proposal; when a passage is borderline, include it with confidence "low" rather than silently dropping it.
- If nothing in the document matches any code, return an empty passages list.
- Propose at most 5 passages per code (the strongest ones)."""

AUDIT_SYSTEM_TEMPLATE = """You are assisting a qualitative researcher who codes school district strategic plans. Your job is to check whether an excerpt that human coders tagged with a code actually fits the code's definition.

The code:
Title: {title}
Definition: {definition}

Rules:
- Judge only against the definition, including any restrictions it states.
- fits=false means the excerpt does NOT belong under this code.
- Excerpts are short fragments extracted from PDFs; tolerate OCR noise and truncation, and judge the substance.
- When genuinely uncertain, lean toward fits=true with confidence "low" (the researcher reviews all flags)."""

AUDIT_SCHEMA = {
    "type": "object",
    "properties": {
        "fits": {"type": "boolean"},
        "rationale": {"type": "string"},
        "confidence": CONFIDENCE,
    },
    "required": ["fits", "rationale", "confidence"],
    "additionalProperties": False,
}


def missing_schema(code_titles):
    return {
        "type": "object",
        "properties": {
            "passages": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "code": {"type": "string", "enum": sorted(code_titles)},
                        "page": {"type": "integer"},
                        "quote": {"type": "string"},
                        "rationale": {"type": "string"},
                        "confidence": CONFIDENCE,
                    },
                    "required": ["code", "page", "quote", "rationale", "confidence"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["passages"],
        "additionalProperties": False,
    }


def missing_code_blocks(code_rows):
    return "\n\n".join(
        f"{i + 1}. Title: {code['title']}\n   Definition: {code['description'] or '(no definition)'}"
        for i, code in enumerate(code_rows)
    )


def get_connection():
    connection = sqlite3.connect(config.DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def document_page_text(pdf_filename):
    document = fitz.open(config.PDF_DIR + pdf_filename)
    pieces = []
    for page_index in range(document.page_count):
        pieces.append(f"[[page {page_index + 1}]]\n" + document[page_index].get_text())
    document.close()
    return "\n".join(pieces)


def load_codes(connection, code_ids):
    rows = connection.execute(
        f"SELECT * FROM codes WHERE is_category = 0 AND id IN "
        f"({','.join('?' * len(code_ids))})",
        code_ids,
    ).fetchall()
    if len(rows) != len(code_ids):
        sys.exit(f"Some code ids not found or are categories: {code_ids}")
    if len(rows) > config.REVIEW_MAX_CODES_PER_RUN:
        sys.exit(f"At most {config.REVIEW_MAX_CODES_PER_RUN} codes per run")
    return rows


def build_missing_tasks(connection, code_rows):
    """One task per in-sample document missing >=1 selected code. Each task
    carries only the codes that document is actually missing."""
    tasks = []
    for document in connection.execute(
        "SELECT id, pdf_filename FROM documents "
        "WHERE in_sample = 1 AND pdf_filename IS NOT NULL ORDER BY pdf_filename"
    ).fetchall():
        applied_ids = {
            row["code_id"]
            for row in connection.execute(
                """SELECT DISTINCT ec.code_id FROM excerpt_codes ec
                   JOIN excerpts e ON e.id = ec.excerpt_id
                   WHERE e.document_id = ?""",
                (document["id"],),
            )
        }
        codes_to_check = [c for c in code_rows if c["id"] not in applied_ids]
        if codes_to_check:
            tasks.append({"document": dict(document), "codes": codes_to_check})
    return tasks


def build_audit_tasks(connection, code_rows):
    tasks = []
    for code in code_rows:
        excerpt_rows = connection.execute(
            """SELECT e.id, e.document_id, e.excerpt_text, d.media_title
               FROM excerpts e
               JOIN excerpt_codes ec ON ec.excerpt_id = e.id AND ec.code_id = ?
               JOIN documents d ON d.id = e.document_id
               WHERE d.in_sample = 1 AND e.excerpt_text IS NOT NULL
                 AND NOT EXISTS (SELECT 1 FROM review_findings f
                   WHERE f.kind = 'audit' AND f.excerpt_id = e.id AND f.code_id = ?)
               ORDER BY e.id""",
            (code["id"], code["id"]),
        ).fetchall()
        for excerpt in excerpt_rows:
            tasks.append({"code": dict(code), "excerpt": dict(excerpt)})
    return tasks


def missing_request(task):
    code_rows = task["codes"]
    text = document_page_text(task["document"]["pdf_filename"])
    return {
        "model": config.REVIEW_MODEL,
        # generous: thinking tokens + up to 5 passages/code with rationales
        # all count against this cap; too low truncates the JSON mid-string
        "max_tokens": 8000,
        "system": MISSING_SYSTEM_TEMPLATE.format(code_blocks=missing_code_blocks(code_rows)),
        "output_config": {
            "format": {"type": "json_schema", "schema": missing_schema([c["title"] for c in code_rows])}
        },
        "messages": [{"role": "user", "content": f"Document text:\n\n{text}"}],
    }


def audit_request(task):
    code = task["code"]
    excerpt = task["excerpt"]
    return {
        "model": config.REVIEW_MODEL,
        "max_tokens": 600,
        "system": AUDIT_SYSTEM_TEMPLATE.format(
            title=code["title"], definition=code["description"] or "(no definition)"
        ),
        "output_config": {"format": {"type": "json_schema", "schema": AUDIT_SCHEMA}},
        "messages": [
            {
                "role": "user",
                "content": f"District: {excerpt['media_title']}\n\nExcerpt:\n{excerpt['excerpt_text']}",
            }
        ],
    }


def estimate_tasks(kind, tasks):
    if kind == "missing":
        input_tokens = sum(
            len(document_page_text(t["document"]["pdf_filename"])) / 4 for t in tasks
        )
        output_tokens = len(tasks) * 300
    else:
        input_tokens = sum(len(t["excerpt"]["excerpt_text"]) / 4 + 300 for t in tasks)
        output_tokens = len(tasks) * 150
    dollars = (
        input_tokens / 1e6 * config.REVIEW_PRICE_PER_MTOK_INPUT
        + output_tokens / 1e6 * config.REVIEW_PRICE_PER_MTOK_OUTPUT
    )
    return input_tokens, dollars


def parse_response(message):
    if message.stop_reason == "refusal" or not message.content:
        raise ValueError("model refused or returned no content")
    text = next((b.text for b in message.content if b.type == "text"), None)
    if text is None:
        raise ValueError("no text block in response")
    return json.loads(text)


def run_job(connection, job_id):
    import anthropic

    job = connection.execute("SELECT * FROM review_jobs WHERE id = ?", (job_id,)).fetchone()
    code_ids = json.loads(job["code_ids"]) if job["code_ids"] else [job["code_id"]]
    code_rows = load_codes(connection, code_ids)
    title_to_id = {c["title"]: c["id"] for c in code_rows}

    if job["kind"] == "missing":
        tasks = build_missing_tasks(connection, code_rows)
        make_request = missing_request
    else:
        tasks = build_audit_tasks(connection, code_rows)
        make_request = audit_request

    connection.execute(
        "UPDATE review_jobs SET status='running', request_count=? WHERE id=?",
        (len(tasks), job_id),
    )
    connection.commit()
    if not tasks:
        connection.execute(
            "UPDATE review_jobs SET status='done', completed_at=datetime('now','localtime') WHERE id=?",
            (job_id,),
        )
        connection.commit()
        print("Nothing to review.")
        return

    client = anthropic.Anthropic(max_retries=5)
    write_lock = threading.Lock()
    finding_count = 0
    error_count = 0

    def call_api(task):
        return task, client.messages.create(**make_request(task))

    with ThreadPoolExecutor(max_workers=config.REVIEW_CONCURRENCY) as pool:
        futures = [pool.submit(call_api, task) for task in tasks]
        for future in as_completed(futures):
            try:
                task, message = future.result()
                payload = parse_response(message)
            except Exception as error:
                print(f"request failed: {error}")
                with write_lock:
                    error_count += 1
                    connection.execute(
                        "UPDATE review_jobs SET completed_count = completed_count + 1 WHERE id=?",
                        (job_id,),
                    )
                    connection.commit()
                continue

            with write_lock:
                if job["kind"] == "missing":
                    valid_titles = {c["title"] for c in task["codes"]}
                    for passage in payload.get("passages", []):
                        if passage["code"] not in valid_titles:
                            continue
                        # Re-runs must not duplicate cards for passages already
                        # proposed (whatever their review status)
                        duplicate = connection.execute(
                            """SELECT 1 FROM review_findings
                               WHERE kind='missing' AND code_id=? AND document_id=?
                                 AND proposed_text=?""",
                            (title_to_id[passage["code"]], task["document"]["id"],
                             passage["quote"]),
                        ).fetchone()
                        if duplicate:
                            continue
                        connection.execute(
                            """INSERT INTO review_findings
                               (job_id, kind, code_id, document_id, proposed_text,
                                page_hint, rationale, confidence)
                               VALUES (?,?,?,?,?,?,?,?)""",
                            (
                                job_id, "missing", title_to_id[passage["code"]],
                                task["document"]["id"], passage["quote"], passage["page"],
                                passage["rationale"], passage["confidence"],
                            ),
                        )
                        finding_count += 1
                else:
                    connection.execute(
                        """INSERT INTO review_findings
                           (job_id, kind, code_id, document_id, excerpt_id, verdict,
                            rationale, confidence, status)
                           VALUES (?,?,?,?,?,?,?,?,?)""",
                        (
                            job_id, "audit", task["code"]["id"],
                            task["excerpt"]["document_id"], task["excerpt"]["id"],
                            "does_not_fit" if not payload["fits"] else "fits",
                            payload["rationale"], payload["confidence"],
                            # fits=true rows are the dedupe record only
                            "pending" if not payload["fits"] else "rejected",
                        ),
                    )
                    if not payload["fits"]:
                        finding_count += 1
                connection.execute(
                    "UPDATE review_jobs SET completed_count = completed_count + 1 WHERE id=?",
                    (job_id,),
                )
                connection.commit()

    connection.execute(
        "UPDATE review_jobs SET status='done', completed_at=datetime('now','localtime'), "
        "error=? WHERE id=?",
        (f"{error_count} request(s) failed" if error_count else None, job_id),
    )
    connection.commit()
    print(f"Done: {finding_count} finding(s) to review, {error_count} request error(s).")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--kind", choices=["missing", "audit"])
    parser.add_argument("--code-ids", help="comma-separated code ids (max 3)")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--job-id", type=int)
    arguments = parser.parse_args()

    connection = get_connection()

    if arguments.job_id:
        try:
            run_job(connection, arguments.job_id)
        except Exception as error:
            connection.execute(
                "UPDATE review_jobs SET status='error', error=? WHERE id=?",
                (str(error)[:2000], arguments.job_id),
            )
            connection.commit()
            raise
        return

    if not arguments.kind or not arguments.code_ids:
        parser.error("--kind and --code-ids required (or --job-id)")
    code_ids = [int(x) for x in arguments.code_ids.split(",")]
    code_rows = load_codes(connection, code_ids)

    if arguments.dry_run:
        if arguments.kind == "missing":
            tasks = build_missing_tasks(connection, code_rows)
        else:
            tasks = build_audit_tasks(connection, code_rows)
        input_tokens, dollars = estimate_tasks(arguments.kind, tasks)
        print(f"DRY RUN: {len(tasks)} requests, ~{input_tokens/1000:.0f}k input tokens, "
              f"est. ${dollars:.2f} ({arguments.kind}, {config.REVIEW_MODEL})")
        return

    cursor = connection.execute(
        "INSERT INTO review_jobs (kind, code_ids, model) VALUES (?,?,?)",
        (arguments.kind, json.dumps(code_ids), config.REVIEW_MODEL),
    )
    connection.commit()
    job_id = cursor.lastrowid
    try:
        run_job(connection, job_id)
    except Exception as error:
        connection.execute(
            "UPDATE review_jobs SET status='error', error=? WHERE id=?",
            (str(error)[:2000], job_id),
        )
        connection.commit()
        raise


if __name__ == "__main__":
    main()
