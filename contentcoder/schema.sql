CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY,
    pdf_filename TEXT UNIQUE,            -- file in PDF_DIR; NULL if imported doc's PDF is unresolved
    media_title TEXT UNIQUE NOT NULL,    -- exact title used in exports (verbatim Dedoose title for imports)
    resource_creator TEXT,
    resource_date TEXT,                  -- 'M/D/YYYY' string, passed through to export
    coding_status TEXT NOT NULL DEFAULT 'not_started'
        CHECK (coding_status IN ('not_started', 'in_progress', 'complete')),
    in_sample INTEGER NOT NULL DEFAULT 0   -- 1 = in the qual coding sample (include_qual)
);

CREATE TABLE IF NOT EXISTS codes (
    id INTEGER PRIMARY KEY,              -- Dedoose Ids preserved on import
    parent_id INTEGER REFERENCES codes(id),
    title TEXT NOT NULL,
    display_name TEXT,                   -- table-ready name for analysis output
    description TEXT NOT NULL DEFAULT '',
    weighted INTEGER NOT NULL DEFAULT 1,
    weight_min REAL NOT NULL DEFAULT 0,
    weight_max REAL NOT NULL DEFAULT 3,
    weight_default REAL NOT NULL DEFAULT 0,
    -- Categories organize the tree for display/analysis only: they cannot be
    -- applied to excerpts and are excluded from export column paths, so the
    -- hierarchy can be rearranged without changing the Dedoose export format.
    is_category INTEGER NOT NULL DEFAULT 0
);

-- Append-only audit log: every codebook change is archived here.
CREATE TABLE IF NOT EXISTS code_history (
    id INTEGER PRIMARY KEY,
    changed_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    action TEXT NOT NULL CHECK (action IN ('create', 'update', 'delete')),
    code_id INTEGER NOT NULL,
    old_values TEXT,                     -- JSON snapshot before the change (NULL for create)
    new_values TEXT                      -- JSON snapshot after the change (NULL for delete)
);

CREATE TABLE IF NOT EXISTS excerpts (
    id INTEGER PRIMARY KEY,
    document_id INTEGER NOT NULL REFERENCES documents(id),
    page_number INTEGER,                 -- 1-based; NULL for document-level excerpts
    char_start INTEGER,
    char_end INTEGER,
    excerpt_text TEXT,
    excerpt_creator TEXT NOT NULL,
    created_date TEXT NOT NULL,          -- ISO 'YYYY-MM-DD'; formatted M/D/YYYY at export
    anchor_status TEXT NOT NULL DEFAULT 'anchored'
        CHECK (anchor_status IN ('anchored', 'unanchored', 'document_level')),
    match_quality REAL,                  -- 100 = exact import match; fuzzy score otherwise; NULL for app-native
    source TEXT NOT NULL DEFAULT 'app' CHECK (source IN ('app', 'dedoose')),
    dedoose_range TEXT                   -- original 'Page N: a-b' verbatim, exported as-is for imports
);
CREATE INDEX IF NOT EXISTS idx_excerpts_document ON excerpts(document_id);

-- Highlight geometry in unscaled PDF points, top-left origin (shared
-- convention between pymupdf and pdf.js viewport at scale 1).
CREATE TABLE IF NOT EXISTS excerpt_rects (
    id INTEGER PRIMARY KEY,
    excerpt_id INTEGER NOT NULL REFERENCES excerpts(id) ON DELETE CASCADE,
    page_number INTEGER NOT NULL,
    x0 REAL NOT NULL,
    y0 REAL NOT NULL,
    x1 REAL NOT NULL,
    y1 REAL NOT NULL,
    rect_order INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_rects_excerpt ON excerpt_rects(excerpt_id);

-- LLM-assisted review: jobs submit Message Batches; findings await human
-- accept/reject in the Review tab. Nothing changes coding data until accepted.
CREATE TABLE IF NOT EXISTS review_jobs (
    id INTEGER PRIMARY KEY,
    kind TEXT NOT NULL CHECK (kind IN ('missing', 'audit')),
    code_id INTEGER,                     -- legacy (batch-era single-code jobs)
    code_ids TEXT,                       -- JSON list of code ids for this run
    completed_count INTEGER NOT NULL DEFAULT 0,
    pid INTEGER,                         -- runner process id (for cancel)
    model TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'running', 'done', 'error')),
    batch_id TEXT,
    request_count INTEGER,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    completed_at TEXT,
    error TEXT
);

CREATE TABLE IF NOT EXISTS review_findings (
    id INTEGER PRIMARY KEY,
    job_id INTEGER NOT NULL REFERENCES review_jobs(id) ON DELETE CASCADE,
    kind TEXT NOT NULL CHECK (kind IN ('missing', 'audit')),
    code_id INTEGER NOT NULL,
    document_id INTEGER NOT NULL,
    excerpt_id INTEGER,                  -- audit: the excerpt reviewed
    proposed_text TEXT,                  -- missing: verbatim quote from the plan
    page_hint INTEGER,
    verdict TEXT,
    rationale TEXT,
    confidence TEXT,
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'accepted', 'rejected'))
);
CREATE INDEX IF NOT EXISTS idx_findings_status ON review_findings(status);

CREATE TABLE IF NOT EXISTS excerpt_codes (
    excerpt_id INTEGER NOT NULL REFERENCES excerpts(id) ON DELETE CASCADE,
    code_id INTEGER NOT NULL REFERENCES codes(id),
    weight REAL,                         -- legacy Dedoose weight on import; code weight_default for new
    PRIMARY KEY (excerpt_id, code_id)
);
