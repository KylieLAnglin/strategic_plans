"""One-time OCR pass over sample PDFs with little or no extractable text.

Finds in-sample PDFs whose text layer is missing or sparse, backs up the
originals to final_pdfs_originals/, and runs ocrmypdf (--skip-text: only
image pages are OCRed, existing text and page geometry are preserved, so
stored highlight rects stay valid).

Usage:
    python ocr_pdfs.py            # in-sample documents only
    python ocr_pdfs.py --all      # every PDF in final_pdfs/
    python ocr_pdfs.py --dry-run  # report candidates, change nothing
"""

import os
import shutil
import sqlite3
import subprocess
import sys

import fitz

import config

MIN_CHARS_PER_PAGE = 300
BACKUP_DIR = os.path.join(os.path.dirname(config.PDF_DIR.rstrip("/")), "final_pdfs_originals")


def main():
    dry_run = "--dry-run" in sys.argv
    include_all = "--all" in sys.argv

    connection = sqlite3.connect(config.DB_PATH)
    connection.row_factory = sqlite3.Row
    if include_all:
        filenames = sorted(
            n for n in os.listdir(config.PDF_DIR) if n.lower().endswith(".pdf")
        )
    else:
        filenames = [
            row["pdf_filename"]
            for row in connection.execute(
                "SELECT pdf_filename FROM documents WHERE in_sample = 1 "
                "AND pdf_filename IS NOT NULL ORDER BY pdf_filename"
            )
        ]
    connection.close()

    candidates = []
    for filename in filenames:
        path = os.path.join(config.PDF_DIR, filename)
        document = fitz.open(path)
        chars = sum(len(page.get_text()) for page in document)
        pages = document.page_count
        document.close()
        if chars / max(pages, 1) < MIN_CHARS_PER_PAGE:
            candidates.append((filename, pages, chars))

    print(f"Scanned {len(filenames)} PDFs; {len(candidates)} need OCR:")
    for filename, pages, chars in candidates:
        print(f"  {filename}: {pages} page(s), {chars} extractable chars")
    if dry_run or not candidates:
        return

    os.makedirs(BACKUP_DIR, exist_ok=True)
    for filename, pages, chars_before in candidates:
        source_path = os.path.join(config.PDF_DIR, filename)
        backup_path = os.path.join(BACKUP_DIR, filename)
        if not os.path.exists(backup_path):
            shutil.copy2(source_path, backup_path)

        temp_path = source_path + ".ocr.tmp.pdf"
        result = subprocess.run(
            ["ocrmypdf", "--skip-text", "--quiet", source_path, temp_path],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            print(f"  FAILED {filename}: {result.stderr.strip()[-300:]}")
            if os.path.exists(temp_path):
                os.remove(temp_path)
            continue
        os.replace(temp_path, source_path)

        document = fitz.open(source_path)
        chars_after = sum(len(page.get_text()) for page in document)
        document.close()
        print(f"  OCR'd {filename}: {chars_before} -> {chars_after} chars")

    print(f"\nOriginals backed up to {BACKUP_DIR}")


if __name__ == "__main__":
    main()
