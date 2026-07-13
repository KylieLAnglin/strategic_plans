"""Shared fuzzy text-anchoring: locate a passage of text in a PDF and return
page rects for highlighting.

Used by import_dedoose.py (re-anchoring legacy Dedoose excerpts) and by the
LLM review pipeline (anchoring accepted passage proposals).
"""

import unicodedata

from rapidfuzz import fuzz

FUZZY_ACCEPT_SCORE = 85


def normalize_with_map(text):
    """Normalize text for matching; returns (normalized, index_map) where
    index_map[i] is the position in the original text of normalized char i."""
    normalized_chars = []
    index_map = []
    previous_was_space = True
    for original_index, char in enumerate(text):
        decomposed = unicodedata.normalize("NFKC", char).lower()
        for piece in decomposed:
            if piece.isalnum():
                normalized_chars.append(piece)
                index_map.append(original_index)
                previous_was_space = False
            elif not previous_was_space:
                normalized_chars.append(" ")
                index_map.append(original_index)
                previous_was_space = True
    while normalized_chars and normalized_chars[-1] == " ":
        normalized_chars.pop()
        index_map.pop()
    return "".join(normalized_chars), index_map


def load_page_words(fitz_document, page_index, cache):
    """Words for one page: (page_string, word_spans, word_rects). Words are
    joined by single spaces; spans index into the joined string."""
    if page_index in cache:
        return cache[page_index]
    words = fitz_document[page_index].get_text("words")
    pieces = []
    word_spans = []
    word_meta = []
    cursor = 0
    for x0, y0, x1, y1, word_text, block_no, line_no, _word_no in words:
        if pieces:
            cursor += 1  # joining space
        pieces.append(word_text)
        word_spans.append((cursor, cursor + len(word_text)))
        word_meta.append((x0, y0, x1, y1, block_no, line_no))
        cursor += len(word_text)
    entry = (" ".join(pieces), word_spans, word_meta)
    cache[page_index] = entry
    return entry


def rects_for_interval(word_spans, word_meta, char_start, char_end, page_number):
    """Rects (one per text line) covering the words that intersect
    [char_start, char_end) in the page string."""
    line_rects = {}
    covered_spans = []
    for (span_start, span_end), (x0, y0, x1, y1, block_no, line_no) in zip(
        word_spans, word_meta
    ):
        if span_end <= char_start or span_start >= char_end:
            continue
        covered_spans.append((span_start, span_end))
        key = (block_no, line_no)
        if key in line_rects:
            rect = line_rects[key]
            line_rects[key] = (
                min(rect[0], x0), min(rect[1], y0), max(rect[2], x1), max(rect[3], y1),
            )
        else:
            line_rects[key] = (x0, y0, x1, y1)
    if not covered_spans:
        return [], None, None
    ordered = [line_rects[key] for key in sorted(line_rects)]
    rects = [
        {"page_number": page_number, "x0": r[0], "y0": r[1], "x1": r[2], "y1": r[3]}
        for r in ordered
    ]
    return rects, min(s for s, _ in covered_spans), max(e for _, e in covered_spans)


def match_on_page(normalized_excerpt, page_entry):
    """Try to locate the excerpt on one page. Returns (score, norm_start,
    norm_end, index_map) or None."""
    page_string, _spans, _meta = page_entry
    normalized_page, index_map = normalize_with_map(page_string)
    if not normalized_page:
        return None
    exact_position = normalized_page.find(normalized_excerpt)
    if exact_position != -1:
        return 100.0, exact_position, exact_position + len(normalized_excerpt), index_map
    alignment = fuzz.partial_ratio_alignment(normalized_excerpt, normalized_page)
    if alignment is None:
        return None
    return alignment.score, alignment.dest_start, alignment.dest_end, index_map


def anchor_excerpt(fitz_document, page_cache, excerpt_text, hinted_page_number):
    """Find the excerpt in the PDF. Returns dict with page_number, rects,
    char_start, char_end, score — or matched=False if below threshold."""
    normalized_excerpt, _ = normalize_with_map(excerpt_text)
    if len(normalized_excerpt) < 4:
        return None
    page_count = fitz_document.page_count

    candidate_indices = []
    if hinted_page_number is not None and 1 <= hinted_page_number <= page_count:
        hinted_index = hinted_page_number - 1
        candidate_indices = [hinted_index, hinted_index - 1, hinted_index + 1]
        candidate_indices = [i for i in candidate_indices if 0 <= i < page_count]
    remaining_indices = [i for i in range(page_count) if i not in candidate_indices]

    best = None  # (score, page_index, norm_start, norm_end, index_map)
    for page_index in candidate_indices + remaining_indices:
        result = match_on_page(normalized_excerpt, load_page_words(fitz_document, page_index, page_cache))
        if result is None:
            continue
        score, norm_start, norm_end, index_map = result
        if best is None or score > best[0]:
            best = (score, page_index, norm_start, norm_end, index_map)
        if score >= 100:
            break
        # If the hinted page already matches well, don't scan the whole doc
        if score >= FUZZY_ACCEPT_SCORE and page_index in candidate_indices:
            break

    if best is None or best[0] < FUZZY_ACCEPT_SCORE:
        return {"score": best[0] if best else 0.0, "matched": False}

    score, page_index, norm_start, norm_end, index_map = best
    page_string, word_spans, word_meta = page_cache[page_index]
    original_start = index_map[norm_start]
    original_end = index_map[min(norm_end, len(index_map)) - 1] + 1
    rects, span_start, span_end = rects_for_interval(
        word_spans, word_meta, original_start, original_end, page_index + 1
    )
    if not rects:
        return {"score": score, "matched": False}
    return {
        "matched": True,
        "score": score,
        "page_number": page_index + 1,
        "rects": rects,
        "char_start": span_start,
        "char_end": span_end,
    }
