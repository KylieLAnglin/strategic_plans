import * as pdfjsLib from "/static/vendor/pdfjs/pdf.min.mjs";

pdfjsLib.GlobalWorkerOptions.workerSrc = "/static/vendor/pdfjs/pdf.worker.min.mjs";

// ------------------------------------------------------------------ state

let documents = [];
let codes = [];
let excerpts = [];            // excerpts for the open document
let currentDoc = null;
let pdfDoc = null;
let scale = 1.25;
let pages = [];               // per-page render state
let pageObserver = null;
let renderGeneration = 0;     // bumped on doc change / zoom to cancel stale renders

let editor = null;            // {mode:'new'|'edit', excerptId, codeIds:Set, pending}
let selectedExcerptId = null;
let expandedCodes = new Set();
let activeTab = "documents";
let selectedCodeId = null;    // code selected in the Codebook tab

let anchorTarget = null;      // unanchored excerpt being manually anchored
let anchorSelection = null;
let searchMatches = [];
let searchMatchIndex = -1;
let docTextCache = null;      // per-page extracted text for search

const $ = (id) => document.getElementById(id);

// ------------------------------------------------------------------ api

async function api(path, options = {}) {
  if (options.body !== undefined) {
    options.headers = { "Content-Type": "application/json" };
    options.body = JSON.stringify(options.body);
  }
  const response = await fetch(path, options);
  if (!response.ok) {
    const detail = await response.json().catch(() => ({}));
    throw new Error(detail.error || `${response.status} ${response.statusText}`);
  }
  return response.json();
}

// ------------------------------------------------------------------ documents panel

async function refreshDocuments() {
  documents = await api("/api/documents");
  renderDocumentList();
  const unanchoredTotal = documents.reduce((n, d) => n + (d.unanchored_count || 0), 0);
  $("unanchored-count").textContent = unanchoredTotal ? `(${unanchoredTotal})` : "";
}

function renderDocumentList() {
  const filterText = $("doc-filter").value.toLowerCase();
  const statusFilter = document.querySelector("#status-chips .chip.active").dataset.status;
  const sampleOnly = $("sample-only").checked;
  const list = $("doc-list");
  list.innerHTML = "";
  for (const doc of documents) {
    if (sampleOnly && !doc.in_sample) continue;
    if (filterText && !doc.media_title.toLowerCase().includes(filterText)) continue;
    if (statusFilter !== "all" && doc.coding_status !== statusFilter) continue;
    const item = document.createElement("li");
    if (currentDoc && doc.id === currentDoc.id) item.classList.add("active");

    const dot = document.createElement("span");
    dot.className = `status-dot ${doc.coding_status}`;
    dot.title = `Status: ${doc.coding_status} (click to change)`;
    dot.onclick = async (event) => {
      event.stopPropagation();
      const order = ["not_started", "in_progress", "complete"];
      const next = order[(order.indexOf(doc.coding_status) + 1) % order.length];
      await api(`/api/documents/${doc.id}`, { method: "PATCH", body: { coding_status: next } });
      refreshDocuments();
    };

    const name = document.createElement("span");
    name.className = "doc-name";
    name.textContent = doc.media_title;
    name.title = doc.media_title;

    item.append(dot, name);
    if (!doc.pdf_filename) {
      const missing = document.createElement("span");
      missing.className = "doc-missing";
      missing.textContent = "no PDF";
      item.append(missing);
    }
    if (doc.excerpt_count) {
      const count = document.createElement("span");
      count.className = "doc-count";
      count.textContent = doc.excerpt_count;
      item.append(count);
    }
    if (doc.unanchored_count) {
      const badge = document.createElement("span");
      badge.className = "doc-badge";
      badge.textContent = doc.unanchored_count;
      badge.title = `${doc.unanchored_count} unanchored excerpt(s)`;
      item.append(badge);
    }
    item.onclick = () => openDocument(doc);
    list.append(item);
  }
}

// ------------------------------------------------------------------ pdf viewer

async function openDocument(doc) {
  if (!doc.pdf_filename) {
    const filename = prompt(
      `No PDF is linked to "${doc.media_title}".\n` +
      "Enter the exact filename inside final_pdfs/ to link it:"
    );
    if (!filename) return;
    await api(`/api/documents/${doc.id}`, { method: "PATCH", body: { pdf_filename: filename } });
    doc.pdf_filename = filename;
    refreshDocuments();
  }
  cancelEditor();
  exitAnchorMode();
  currentDoc = doc;
  selectedExcerptId = null;
  docTextCache = null;
  $("current-doc-title").textContent = doc.media_title;
  $("viewer-empty").classList.add("hidden");
  renderDocumentList();

  renderGeneration += 1;
  const generation = renderGeneration;
  const viewer = $("viewer");
  viewer.innerHTML = "";
  pages = [];
  if (pageObserver) pageObserver.disconnect();

  [excerpts, pdfDoc] = await Promise.all([
    api(`/api/documents/${doc.id}/excerpts`),
    pdfjsLib.getDocument(`/api/documents/${doc.id}/pdf`).promise,
  ]);
  if (generation !== renderGeneration) return;
  renderExcerptList();
  renderDocLevelBar();

  // Pre-compute page sizes (scale 1) so the scrollbar is stable before rendering
  const firstPage = await pdfDoc.getPage(1);
  const defaultSize = firstPage.getViewport({ scale: 1 });
  pageObserver = new IntersectionObserver(onPageIntersect, {
    root: viewer, rootMargin: "600px 0px",
  });
  for (let i = 0; i < pdfDoc.numPages; i++) {
    const container = document.createElement("div");
    container.className = "page";
    container.dataset.pageIndex = i;
    container.style.width = `${defaultSize.width * scale}px`;
    container.style.height = `${defaultSize.height * scale}px`;
    viewer.append(container);
    pages.push({
      container, rendered: false, rendering: false,
      items: null, textDivs: null, cumOffsets: null, pageText: null,
    });
    pageObserver.observe(container);
  }
}

function onPageIntersect(entries) {
  for (const entry of entries) {
    if (!entry.isIntersecting) continue;
    const pageIndex = Number(entry.target.dataset.pageIndex);
    renderPage(pageIndex);
  }
}

async function renderPage(pageIndex) {
  const pageState = pages[pageIndex];
  if (!pageState || pageState.rendered || pageState.rendering) return;
  pageState.rendering = true;
  const generation = renderGeneration;

  const page = await pdfDoc.getPage(pageIndex + 1);
  if (generation !== renderGeneration) return;
  const viewport = page.getViewport({ scale });
  const container = pageState.container;
  container.innerHTML = "";
  container.style.width = `${viewport.width}px`;
  container.style.height = `${viewport.height}px`;
  container.style.setProperty("--scale-factor", scale);

  const canvas = document.createElement("canvas");
  const outputScale = window.devicePixelRatio || 1;
  canvas.width = Math.floor(viewport.width * outputScale);
  canvas.height = Math.floor(viewport.height * outputScale);
  canvas.style.width = `${viewport.width}px`;
  canvas.style.height = `${viewport.height}px`;
  container.append(canvas);

  const highlightLayer = document.createElement("div");
  highlightLayer.className = "hl-layer";
  container.append(highlightLayer);

  const textLayerDiv = document.createElement("div");
  textLayerDiv.className = "textLayer";
  container.append(textLayerDiv);

  await page.render({
    canvasContext: canvas.getContext("2d"),
    viewport,
    transform: outputScale !== 1 ? [outputScale, 0, 0, outputScale, 0, 0] : null,
  }).promise;
  if (generation !== renderGeneration) return;

  const textContent = await page.getTextContent();
  const textLayer = new pdfjsLib.TextLayer({
    textContentSource: textContent,
    container: textLayerDiv,
    viewport,
  });
  await textLayer.render();
  if (generation !== renderGeneration) return;

  // Build the page text and a char offset for every text div, so DOM
  // selections can be mapped to stable character positions.
  const items = textContent.items;
  const textDivs = textLayer.textDivs;
  const cumOffsets = [];
  let pageText = "";
  for (const item of items) {
    cumOffsets.push(pageText.length);
    pageText += item.str;
    if (item.hasEOL) pageText += "\n";
  }
  Object.assign(pageState, {
    rendered: true, rendering: false, items, textDivs, cumOffsets, pageText,
  });
  drawPageHighlights(pageIndex);
}

function setScale(newScale) {
  scale = Math.min(3, Math.max(0.5, newScale));
  $("zoom-level").textContent = `${Math.round(scale * 100)}%`;
  if (!pdfDoc) return;
  renderGeneration += 1;
  for (const pageState of pages) {
    pageState.container.innerHTML = "";
    pageState.rendered = false;
    pageState.rendering = false;
  }
  // Resize placeholders using page 1's base size; exact per-page sizes are
  // corrected when each page renders
  pdfDoc.getPage(1).then((firstPage) => {
    const base = firstPage.getViewport({ scale: 1 });
    for (const pageState of pages) {
      pageState.container.style.width = `${base.width * scale}px`;
      pageState.container.style.height = `${base.height * scale}px`;
      pageObserver.unobserve(pageState.container);
      pageObserver.observe(pageState.container);
    }
  });
}

// ------------------------------------------------------------------ highlights

function drawPageHighlights(pageIndex) {
  const pageState = pages[pageIndex];
  if (!pageState || !pageState.rendered) return;
  const layer = pageState.container.querySelector(".hl-layer");
  if (!layer) return;
  layer.innerHTML = "";
  const labelEntries = [];
  for (const excerpt of excerpts) {
    let firstRectTop = null;
    for (const rect of excerpt.rects) {
      if (rect.page_number !== pageIndex + 1) continue;
      const highlight = document.createElement("div");
      highlight.className = "hl";
      if (excerpt.id === selectedExcerptId) highlight.classList.add("selected");
      positionRect(highlight, rect);
      highlight.title = excerptCodeTitles(excerpt).join(", ");
      highlight.onclick = () => selectExcerpt(excerpt.id, false);
      layer.append(highlight);
      if (firstRectTop === null || rect.y0 < firstRectTop) firstRectTop = rect.y0;
    }
    if (firstRectTop !== null) {
      labelEntries.push({ excerpt, top: firstRectTop * scale });
    }
  }
  // Margin labels: each highlight's codes shown as a small tag in the right
  // margin, vertically aligned with the highlight (nudged down on collision).
  pageState.container.querySelectorAll(".hl-label").forEach((n) => n.remove());
  labelEntries.sort((a, b) => a.top - b.top);
  let lastLabelBottom = -Infinity;
  for (const entry of labelEntries) {
    const label = document.createElement("div");
    label.className = "hl-label";
    if (entry.excerpt.id === selectedExcerptId) label.classList.add("selected");
    const codeTitles = excerptCodeTitles(entry.excerpt).join(", ") || "(no codes)";
    label.textContent = codeTitles;
    label.title = codeTitles + "\n\n" + (entry.excerpt.excerpt_text || "").slice(0, 300);
    const labelTop = Math.max(entry.top, lastLabelBottom + 2);
    label.style.top = `${labelTop}px`;
    lastLabelBottom = labelTop + 16;
    label.onclick = () => selectExcerpt(entry.excerpt.id, false);
    pageState.container.append(label);
  }
  // Unanchored excerpts with a known page (e.g. from Dedoose's page hint)
  // get a sticky note in the page margin so their codes stay visible even
  // though no text region could be highlighted. Notes live on the page
  // container (not the highlight layer) so they paint and click above the
  // text layer.
  pageState.container.querySelectorAll(".page-note").forEach((n) => n.remove());
  let noteOffset = 8;
  for (const excerpt of excerpts) {
    if (excerpt.anchor_status !== "unanchored") continue;
    if (excerpt.page_number !== pageIndex + 1 || excerpt.rects.length) continue;
    const note = document.createElement("div");
    note.className = "page-note";
    if (excerpt.id === selectedExcerptId) note.classList.add("selected");
    note.style.top = `${noteOffset}px`;
    noteOffset += 30;
    const codeTitles = excerptCodeTitles(excerpt).join(", ") || "(no codes)";
    note.textContent = `⚠ ${codeTitles}`;
    note.title =
      `Unanchored excerpt — codes apply to this page but no text region ` +
      `could be matched.\n\n"${(excerpt.excerpt_text || "").slice(0, 300)}"`;
    note.onclick = () => selectExcerpt(excerpt.id, false);
    pageState.container.append(note);
  }
  if (editor && editor.pending && editor.pending.pageNumber === pageIndex + 1) {
    for (const rect of editor.pending.rects) {
      const pendingDiv = document.createElement("div");
      pendingDiv.className = "hl pending";
      positionRect(pendingDiv, rect);
      layer.append(pendingDiv);
    }
  }
}

function positionRect(element, rect) {
  element.style.left = `${rect.x0 * scale}px`;
  element.style.top = `${rect.y0 * scale}px`;
  element.style.width = `${(rect.x1 - rect.x0) * scale}px`;
  element.style.height = `${(rect.y1 - rect.y0) * scale}px`;
}

function redrawAllHighlights() {
  for (let i = 0; i < pages.length; i++) drawPageHighlights(i);
}

// ------------------------------------------------------------------ selection capture

function pageIndexOfNode(node) {
  const element = node.nodeType === Node.TEXT_NODE ? node.parentElement : node;
  const pageContainer = element && element.closest(".page");
  return pageContainer ? Number(pageContainer.dataset.pageIndex) : -1;
}

function charOffsetAt(pageIndex, node, offsetInNode) {
  const pageState = pages[pageIndex];
  if (!pageState || !pageState.rendered) return null;
  const element = node.nodeType === Node.TEXT_NODE ? node.parentElement : node;
  const span = element && element.closest(".textLayer > span, .textLayer span");
  if (!span) return null;
  const divIndex = pageState.textDivs.indexOf(span);
  if (divIndex === -1) return null;
  return pageState.cumOffsets[divIndex] + offsetInNode;
}

function mergeLineRects(rects) {
  const sorted = rects
    .filter((r) => r.x1 - r.x0 > 0.5 && r.y1 - r.y0 > 0.5)
    .sort((a, b) => a.y0 - b.y0 || a.x0 - b.x0);
  const merged = [];
  for (const rect of sorted) {
    const last = merged[merged.length - 1];
    if (last) {
      const verticalOverlap =
        Math.min(last.y1, rect.y1) - Math.max(last.y0, rect.y0);
      const sameLine = verticalOverlap > 0.5 * Math.min(last.y1 - last.y0, rect.y1 - rect.y0);
      if (sameLine && rect.x0 <= last.x1 + 4) {
        last.x1 = Math.max(last.x1, rect.x1);
        last.y0 = Math.min(last.y0, rect.y0);
        last.y1 = Math.max(last.y1, rect.y1);
        continue;
      }
    }
    merged.push({ ...rect });
  }
  return merged;
}

function captureSelection() {
  const selection = window.getSelection();
  if (!selection.rangeCount || selection.isCollapsed) return null;
  const range = selection.getRangeAt(0);
  const startPage = pageIndexOfNode(range.startContainer);
  const endPage = pageIndexOfNode(range.endContainer);
  if (startPage === -1 || endPage === -1) return null;
  if (startPage !== endPage) {
    alert("Please select text within a single page (multi-page excerpts: create one per page).");
    return null;
  }
  const charStart = charOffsetAt(startPage, range.startContainer, range.startOffset);
  const charEnd = charOffsetAt(endPage, range.endContainer, range.endOffset);
  if (charStart === null || charEnd === null || charEnd <= charStart) return null;

  const pageState = pages[startPage];
  const containerBounds = pageState.container.getBoundingClientRect();
  const clientRects = Array.from(range.getClientRects()).map((r) => ({
    x0: (r.left - containerBounds.left) / scale,
    y0: (r.top - containerBounds.top) / scale,
    x1: (r.right - containerBounds.left) / scale,
    y1: (r.bottom - containerBounds.top) / scale,
  }));
  const rects = mergeLineRects(clientRects).map((r) => ({
    ...r, page_number: startPage + 1,
  }));
  return {
    pageNumber: startPage + 1,
    charStart,
    charEnd,
    text: pageState.pageText.slice(charStart, charEnd),
    rects,
  };
}

function onViewerMouseUp() {
  const captured = captureSelection();
  if (!captured) return;
  window.getSelection().removeAllRanges();
  if (anchorTarget) {
    anchorSelection = captured;
    $("anchor-save").disabled = false;
    redrawAllHighlights();
    const pageState = pages[captured.pageNumber - 1];
    const layer = pageState.container.querySelector(".hl-layer");
    for (const rect of captured.rects) {
      const pendingDiv = document.createElement("div");
      pendingDiv.className = "hl pending";
      positionRect(pendingDiv, rect);
      layer.append(pendingDiv);
    }
    return;
  }
  openEditor({ mode: "new", excerptId: null, codeIds: new Set(), pending: captured });
}

// ------------------------------------------------------------------ excerpt editor

function openEditor(editorState) {
  editor = editorState;
  $("excerpt-editor").classList.remove("hidden");
  $("editor-heading").textContent =
    editor.mode === "new" ? "New excerpt — click codes to apply" : "Edit excerpt codes";
  $("editor-text").textContent =
    editor.mode === "new"
      ? editor.pending.text
      : (excerpts.find((e) => e.id === editor.excerptId) || {}).excerpt_text || "(no text)";
  $("btn-delete-excerpt").classList.toggle("hidden", editor.mode === "new");
  renderEditorChips();
  renderCodeTrees();
  redrawAllHighlights();
}

function renderEditorChips() {
  const chips = $("editor-codes");
  chips.innerHTML = "";
  for (const codeId of editor.codeIds) {
    const code = codes.find((c) => c.id === codeId);
    if (!code) continue;
    const chip = document.createElement("span");
    chip.className = "code-chip";
    chip.textContent = code.title;
    chips.append(chip);
  }
  if (!editor.codeIds.size) {
    chips.innerHTML = '<span style="color:#999;font-size:12px">no codes yet</span>';
  }
}

async function saveEditor() {
  if (!editor) return;
  if (!editor.codeIds.size && !confirm("Save excerpt with no codes?")) return;
  if (editor.mode === "new") {
    const pending = editor.pending;
    await api("/api/excerpts", {
      method: "POST",
      body: {
        document_id: currentDoc.id,
        page_number: pending.pageNumber,
        char_start: pending.charStart,
        char_end: pending.charEnd,
        excerpt_text: pending.text,
        rects: pending.rects,
        code_ids: [...editor.codeIds],
      },
    });
  } else {
    await api(`/api/excerpts/${editor.excerptId}`, {
      method: "PATCH",
      body: { code_ids: [...editor.codeIds] },
    });
  }
  editor = null;
  $("excerpt-editor").classList.add("hidden");
  await reloadExcerpts();
  refreshDocuments();
  refreshCodes();
}

function cancelEditor() {
  editor = null;
  selectedExcerptId = null;
  $("excerpt-editor").classList.add("hidden");
  redrawAllHighlights();
  renderCodeTrees();
  renderExcerptList();
}

async function deleteCurrentExcerpt() {
  if (!editor || editor.mode !== "edit") return;
  if (!confirm("Delete this excerpt and its code applications?")) return;
  await api(`/api/excerpts/${editor.excerptId}`, { method: "DELETE" });
  cancelEditor();
  await reloadExcerpts();
  refreshDocuments();
  refreshCodes();
}

async function reloadExcerpts() {
  if (!currentDoc) return;
  excerpts = await api(`/api/documents/${currentDoc.id}/excerpts`);
  renderExcerptList();
  renderDocLevelBar();
  redrawAllHighlights();
}

// Document-level excerpts (e.g. codes applied to scanned PDFs in Dedoose,
// which have no text or page) are pinned above the viewer so they are
// always visible while reading the PDF.
function renderDocLevelBar() {
  const documentLevelExcerpts = excerpts.filter((e) => e.anchor_status === "document_level");
  const bar = $("doc-level-bar");
  const chips = $("doc-level-chips");
  chips.innerHTML = "";
  if (!documentLevelExcerpts.length) {
    bar.classList.add("hidden");
    return;
  }
  bar.classList.remove("hidden");
  for (const excerpt of documentLevelExcerpts) {
    for (const title of excerptCodeTitles(excerpt)) {
      const chip = document.createElement("span");
      chip.className = "code-chip doc-level-chip";
      chip.textContent = title;
      chip.title = "Document-level code (click to edit its excerpt)";
      chip.onclick = () => selectExcerpt(excerpt.id, false);
      chips.append(chip);
    }
  }
}

// ------------------------------------------------------------------ excerpt list

function excerptCodeTitles(excerpt) {
  return excerpt.code_ids
    .map((codeId) => (codes.find((c) => c.id === codeId) || {}).title)
    .filter(Boolean);
}

function renderExcerptList() {
  const list = $("excerpt-list");
  list.innerHTML = "";
  $("excerpt-count").textContent = excerpts.length ? `(${excerpts.length})` : "";
  for (const excerpt of excerpts) {
    const item = document.createElement("li");
    if (excerpt.id === selectedExcerptId) item.classList.add("active");
    const codeLine = document.createElement("span");
    codeLine.className = "excerpt-code-line";
    for (const title of excerptCodeTitles(excerpt)) {
      const chip = document.createElement("span");
      chip.className = "code-chip";
      chip.textContent = title;
      codeLine.append(chip);
    }
    if (!codeLine.childElementCount) codeLine.textContent = "(no codes)";
    const snippet = document.createElement("span");
    snippet.className = "excerpt-snippet";
    const pageLabel = excerpt.page_number ? `p.${excerpt.page_number}: ` : "(document-level) ";
    snippet.textContent = pageLabel + (excerpt.excerpt_text || "").slice(0, 110);
    item.append(codeLine, snippet);
    if (excerpt.anchor_status === "unanchored") {
      const flag = document.createElement("span");
      flag.className = "excerpt-unanchored";
      flag.textContent = " ⚠ unanchored";
      item.append(flag);
    }
    item.onclick = () => selectExcerpt(excerpt.id, true);
    list.append(item);
  }
}

function selectExcerpt(excerptId, scrollTo) {
  selectedExcerptId = excerptId;
  const excerpt = excerpts.find((e) => e.id === excerptId);
  renderExcerptList();
  openEditor({ mode: "edit", excerptId, codeIds: new Set(excerpt.code_ids), pending: null });
  if (scrollTo && excerpt.rects.length) {
    const firstRect = excerpt.rects[0];
    const pageState = pages[firstRect.page_number - 1];
    if (pageState) {
      pageState.container.scrollIntoView({ block: "start" });
      $("viewer").scrollTop += firstRect.y0 * scale - 120;
    }
  }
}

// ------------------------------------------------------------------ codebook tree

async function refreshCodes() {
  codes = await api("/api/codes");
  if (selectedCodeId && !codes.some((c) => c.id === selectedCodeId)) {
    selectedCodeId = null;
    $("code-excerpts-title").textContent = "Click a code to see its excerpts";
    $("code-excerpt-list").innerHTML = "";
    $("code-definition").classList.add("hidden");
  }
  renderCodeTrees();
  if (selectedCodeId) selectCodebookCode(selectedCodeId);
}

function buildCodeTree(treeRoot, mode) {
  // mode 'pick': rows toggle codes on the open excerpt editor.
  // mode 'manage': rows select a code to browse its excerpts; CRUD shown.
  treeRoot.innerHTML = "";
  const byParent = new Map();
  for (const code of codes) {
    const key = code.parent_id || 0;
    if (!byParent.has(key)) byParent.set(key, []);
    byParent.get(key).push(code);
  }
  const buildLevel = (parentKey, targetList) => {
    for (const code of byParent.get(parentKey) || []) {
      const item = document.createElement("li");
      const row = document.createElement("div");
      row.className = "code-row";
      if (code.is_category) row.classList.add("category");
      if (mode === "pick" && editor && editor.codeIds.has(code.id)) row.classList.add("applied");
      if (mode === "manage" && code.id === selectedCodeId) row.classList.add("selected-code");

      const hasChildren = byParent.has(code.id);
      const toggle = document.createElement("span");
      toggle.className = "code-toggle";
      toggle.textContent = hasChildren ? (expandedCodes.has(code.id) ? "▾" : "▸") : "";
      toggle.onclick = (event) => {
        event.stopPropagation();
        expandedCodes.has(code.id) ? expandedCodes.delete(code.id) : expandedCodes.add(code.id);
        renderCodeTrees();
      };

      const title = document.createElement("span");
      title.className = "code-title";
      title.textContent = code.title;
      title.title = code.description || code.title;

      const apps = document.createElement("span");
      apps.className = "code-apps";
      apps.textContent = code.applications || "";

      row.append(toggle, title, apps);

      if (mode === "manage") {
        const actions = document.createElement("span");
        actions.className = "code-actions";
        const addChild = document.createElement("button");
        addChild.textContent = "＋";
        addChild.title = "Add child code";
        addChild.onclick = (event) => { event.stopPropagation(); createCode(code.id); };
        const edit = document.createElement("button");
        edit.textContent = "✎";
        edit.title = "Rename code (edit its definition in the right panel)";
        edit.onclick = (event) => { event.stopPropagation(); editCode(code); };
        const remove = document.createElement("button");
        remove.textContent = "🗑";
        remove.title = "Delete code";
        remove.onclick = (event) => { event.stopPropagation(); deleteCode(code); };
        actions.append(addChild, edit, remove);
        row.append(actions);
        row.onclick = () => selectCodebookCode(code.id);
        // Drag-and-drop re-parenting (archived via code_history on the server)
        row.draggable = true;
        row.ondragstart = (event) => {
          event.dataTransfer.setData("text/code-id", String(code.id));
          event.dataTransfer.effectAllowed = "move";
        };
        row.ondragover = (event) => {
          event.preventDefault();
          row.classList.add("drop-target");
        };
        row.ondragleave = () => row.classList.remove("drop-target");
        row.ondrop = (event) => {
          event.preventDefault();
          row.classList.remove("drop-target");
          const draggedId = Number(event.dataTransfer.getData("text/code-id"));
          if (draggedId && draggedId !== code.id) moveCode(draggedId, code.id);
        };
      } else if (code.is_category) {
        // Categories cannot be applied to excerpts; clicking just expands
        row.onclick = () => {
          expandedCodes.has(code.id) ? expandedCodes.delete(code.id) : expandedCodes.add(code.id);
          renderCodeTrees();
        };
      } else {
        row.onclick = () => toggleCodeOnEditor(code.id);
      }
      item.append(row);

      if (hasChildren && expandedCodes.has(code.id)) {
        const childList = document.createElement("ul");
        buildLevel(code.id, childList);
        item.append(childList);
      }
      targetList.append(item);
    }
  };
  buildLevel(0, treeRoot);
}

function renderCodeTrees() {
  buildCodeTree($("manage-code-tree"), "manage");
  if (editor) buildCodeTree($("editor-code-tree"), "pick");
  const categoryCount = codes.filter((c) => c.is_category).length;
  const codeCount = codes.length - categoryCount;
  $("codebook-counts").textContent = `${categoryCount} top-level categories · ${codeCount} codes`;
}

// ------------------------------------------------------------------ codebook tab

async function selectCodebookCode(codeId) {
  selectedCodeId = codeId;
  renderCodeTrees();
  const code = codes.find((c) => c.id === codeId);
  $("code-definition").classList.remove("hidden");
  $("code-display-name").textContent = code.display_name || `${code.title} (same as code title)`;
  $("code-def-text").textContent = code.description || "(no definition written)";
  $("code-def-editor").classList.add("hidden");
  $("code-def-row").classList.remove("hidden");
  $("code-display-line").classList.toggle("hidden", Boolean(code.is_category));
  $("code-history-list").classList.add("hidden");
  $("btn-code-history").textContent = "History ▾";
  const rows = await api(`/api/codes/${codeId}/excerpts`);
  if (selectedCodeId !== codeId) return;
  $("code-excerpts-title").textContent =
    `${code.title} — ${rows.length} excerpt(s) in ${new Set(rows.map((r) => r.document_id)).size} document(s)`;
  const list = $("code-excerpt-list");
  list.innerHTML = "";
  for (const row of rows) {
    const item = document.createElement("li");
    const docLine = document.createElement("span");
    docLine.className = "code-excerpt-doc";
    const pageLabel = row.page_number ? ` — p.${row.page_number}` : " — document-level";
    docLine.textContent = row.media_title + pageLabel;
    const snippet = document.createElement("span");
    snippet.className = "excerpt-snippet";
    snippet.textContent = (row.excerpt_text || "(no text)").slice(0, 260);
    item.append(docLine, snippet);
    if (row.other_code_titles) {
      const others = document.createElement("span");
      others.className = "excerpt-meta";
      others.textContent = "also coded: " + row.other_code_titles;
      item.append(others);
    }
    item.title = "Open in the document view";
    item.onclick = () => openExcerptFromCodebook(row);
    list.append(item);
  }
}

async function toggleCodeHistory() {
  const historyList = $("code-history-list");
  if (!historyList.classList.contains("hidden")) {
    historyList.classList.add("hidden");
    $("btn-code-history").textContent = "History ▾";
    return;
  }
  if (!selectedCodeId) return;
  const rows = await api(`/api/codes/${selectedCodeId}/history`);
  historyList.innerHTML = "";
  const fieldLabels = { title: "title", description: "definition", parent_id: "parent" };
  for (const row of rows) {
    const oldValues = row.old_values ? JSON.parse(row.old_values) : null;
    const newValues = row.new_values ? JSON.parse(row.new_values) : null;
    let changeText;
    if (row.action === "create") {
      changeText = `created — definition: ${newValues.description || "(none)"}`;
    } else if (row.action === "delete") {
      changeText = "deleted";
    } else {
      const changes = [];
      for (const field of Object.keys(fieldLabels)) {
        if (oldValues[field] !== newValues[field]) {
          changes.push(
            `${fieldLabels[field]}: “${oldValues[field] ?? "(none)"}” → “${newValues[field] ?? "(none)"}”`
          );
        }
      }
      changeText = changes.join("; ") || "no definition fields changed";
    }
    const item = document.createElement("li");
    const stamp = document.createElement("span");
    stamp.className = "history-stamp";
    stamp.textContent = row.changed_at;
    const detail = document.createElement("span");
    detail.textContent = changeText;
    item.append(stamp, detail);
    historyList.append(item);
  }
  if (!rows.length) {
    historyList.innerHTML = "<li>No recorded changes.</li>";
  }
  historyList.classList.remove("hidden");
  $("btn-code-history").textContent = "History ▴";
}

async function openExcerptFromCodebook(row) {
  const doc = documents.find((d) => d.id === row.document_id);
  if (!doc) return;
  switchTab("documents");
  if (!currentDoc || currentDoc.id !== doc.id) await openDocument(doc);
  selectExcerpt(row.id, true);
}

// ------------------------------------------------------------------ tabs

function switchTab(tabName) {
  activeTab = tabName;
  document.querySelectorAll("#tabs .tab").forEach((tabButton) => {
    tabButton.classList.toggle("active", tabButton.dataset.tab === tabName);
  });
  $("layout").classList.toggle("hidden", tabName !== "documents");
  $("codebook-layout").classList.toggle("hidden", tabName !== "codebook");
  $("export-layout").classList.toggle("hidden", tabName !== "export");
  $("review-layout").classList.toggle("hidden", tabName !== "review");
  // Viewer controls only make sense on the Documents tab
  for (const id of ["btn-zoom-in", "btn-zoom-out", "zoom-level", "current-doc-title"]) {
    $(id).classList.toggle("hidden", tabName !== "documents");
  }
  if (tabName === "export") refreshExportFiles();
  if (tabName === "review") refreshReviewTab();
}

// ------------------------------------------------------------------ review tab

let reviewPollTimer = null;

const REVIEW_MAX_CODES = 3;

function selectedReviewCodeIds() {
  return Array.from(
    document.querySelectorAll("#review-code-checks input:checked")
  ).map((box) => Number(box.value));
}

async function refreshReviewTab() {
  // Populate the code checkbox list (non-category codes), keeping selections
  const container = $("review-code-checks");
  const previouslyChecked = new Set(selectedReviewCodeIds());
  container.innerHTML = "";
  for (const code of codes.filter((c) => !c.is_category)) {
    const label = document.createElement("label");
    label.className = "review-code-check";
    const box = document.createElement("input");
    box.type = "checkbox";
    box.value = code.id;
    box.checked = previouslyChecked.has(code.id);
    box.addEventListener("change", () => {
      // Cap the selection at REVIEW_MAX_CODES
      if (selectedReviewCodeIds().length > REVIEW_MAX_CODES) {
        box.checked = false;
        return;
      }
      refreshReviewEstimate();
    });
    label.append(box, document.createTextNode(" " + code.title));
    container.append(label);
  }
  await Promise.all([refreshReviewEstimate(), refreshReviewJobs(), refreshReviewFindings()]);
}

async function refreshReviewEstimate() {
  const kind = $("review-kind").value;
  const codeIds = selectedReviewCodeIds();
  const query = `kind=${kind}&code_ids=${codeIds.join(",")}`;
  const [estimate, prompt] = await Promise.all([
    api(`/api/review/estimate?${query}`),
    api(`/api/review/prompt?${query}`),
  ]);
  $("review-estimate").textContent = codeIds.length
    ? `${estimate.requests} request(s) · est. ~$${estimate.est_dollars.toFixed(2)} · results stream in live`
    : "Select 1–3 codes";
  $("review-prompt-model").textContent = `Model: ${prompt.model} (system prompt below)`;
  $("review-prompt-text").textContent = prompt.system_prompt;
  $("review-prompt-note").textContent = prompt.per_request;
}

async function refreshReviewJobs() {
  const jobs = await api("/api/review/jobs");
  const list = $("review-job-list");
  list.innerHTML = "";
  let anyRunning = false;
  for (const job of jobs) {
    if (job.status === "running" || job.status === "pending") anyRunning = true;
    const item = document.createElement("li");
    const findings = job.pending_findings ? ` · ${job.pending_findings} pending` : "";
    const progress =
      job.status === "running" && job.request_count
        ? ` (${job.completed_count}/${job.request_count})`
        : job.request_count ? ` (${job.request_count} req)` : "";
    item.textContent =
      `#${job.id} ${job.kind} — ${job.code_titles} — ${job.status}` +
      progress + findings + (job.error ? ` — ${job.error}` : "");
    item.className = `review-job ${job.status}`;
    if (job.status === "running" || job.status === "pending") {
      const cancelButton = document.createElement("button");
      cancelButton.textContent = "Cancel";
      cancelButton.className = "review-cancel";
      cancelButton.onclick = async () => {
        await api(`/api/review/jobs/${job.id}/cancel`, { method: "POST", body: {} });
        refreshReviewJobs();
      };
      item.append(" ", cancelButton);
    }
    list.append(item);
  }
  clearTimeout(reviewPollTimer);
  if (anyRunning && activeTab === "review") {
    reviewPollTimer = setTimeout(() => {
      refreshReviewJobs();
      refreshReviewFindings();
    }, 10000);
  }
}

async function refreshReviewFindings() {
  const findings = await api("/api/review/findings");
  $("review-findings-count").textContent = findings.length ? `(${findings.length})` : "";
  const container = $("review-findings");
  container.innerHTML = "";
  if (!findings.length) {
    container.innerHTML = '<p class="review-note" style="padding:12px">No pending findings.</p>';
    return;
  }
  for (const finding of findings) {
    const card = document.createElement("div");
    card.className = "finding-card";

    const heading = document.createElement("div");
    heading.className = "finding-heading";
    heading.innerHTML =
      `<b>${finding.code_title}</b> — ${finding.media_title}` +
      (finding.page_hint ? ` (p.${finding.page_hint})` : "") +
      ` <span class="confidence ${finding.confidence}">${finding.confidence || ""}</span>`;
    card.append(heading);

    const quote = document.createElement("blockquote");
    quote.textContent =
      finding.kind === "missing" ? finding.proposed_text : finding.current_excerpt_text;
    card.append(quote);

    if (finding.kind === "audit" && finding.excerpt_code_titles) {
      const codesLine = document.createElement("div");
      codesLine.className = "finding-rationale";
      codesLine.textContent = `Currently coded: ${finding.excerpt_code_titles}`;
      card.append(codesLine);
    }

    const rationale = document.createElement("div");
    rationale.className = "finding-rationale";
    rationale.textContent = finding.rationale || "";
    card.append(rationale);

    const buttons = document.createElement("div");
    buttons.className = "finding-buttons";
    if (finding.kind === "missing") {
      buttons.append(
        findingButton("Open in document", () => openFindingInDocument(finding)),
        findingButton("Accept — apply code", () => resolveFinding(finding.id, "accept", {}), "accept"),
        findingButton("Reject", () => resolveFinding(finding.id, "reject"), "reject"),
      );
    } else {
      buttons.append(
        findingButton("Remove code", () => resolveFinding(finding.id, "accept", { action: "remove_code" }), "accept"),
        findingButton("Delete excerpt", () => resolveFinding(finding.id, "accept", { action: "delete_excerpt" }), "danger"),
        findingButton("Keep as coded", () => resolveFinding(finding.id, "reject"), "reject"),
      );
    }
    card.append(buttons);
    container.append(card);
  }
}

function findingButton(label, onClick, styleClass) {
  const button = document.createElement("button");
  button.textContent = label;
  if (styleClass) button.classList.add(styleClass);
  button.onclick = async () => {
    button.disabled = true;
    await onClick();
  };
  return button;
}

async function resolveFinding(findingId, action, body) {
  try {
    await api(`/api/review/findings/${findingId}/${action}`, {
      method: "POST",
      body: body || {},
    });
  } catch (error) {
    alert(error.message);
  }
  await Promise.all([refreshReviewFindings(), refreshDocuments(), refreshCodes()]);
}

async function openFindingInDocument(finding) {
  const doc = documents.find((d) => d.id === finding.document_id);
  if (!doc) return;
  switchTab("documents");
  if (!currentDoc || currentDoc.id !== doc.id) await openDocument(doc);
  // Reuse the anchor-search machinery to flash the quote's location
  $("anchor-bar").classList.remove("hidden");
  $("anchor-excerpt-text").textContent = `“${(finding.proposed_text || "").slice(0, 200)}”`;
  $("anchor-original-range").textContent = finding.page_hint ? `p.${finding.page_hint}` : "";
  $("anchor-save").disabled = true;
  const searchBox = $("anchor-search");
  searchBox.value = (finding.proposed_text || "").split(/\s+/).slice(0, 6).join(" ");
  runAnchorSearch();
}

// ------------------------------------------------------------------ export tab

async function refreshExportFiles() {
  const listing = await api("/api/exports");
  $("export-dir-note").textContent = listing.export_dir;
  const tbody = document.querySelector("#export-file-table tbody");
  tbody.innerHTML = "";
  for (const file of listing.files) {
    const tr = document.createElement("tr");
    const sizeText =
      file.size > 1e6 ? `${(file.size / 1e6).toFixed(1)} MB` : `${Math.round(file.size / 1e3)} KB`;
    const dateText = new Date(file.modified * 1000).toLocaleString();
    for (const text of [file.name, dateText, sizeText]) {
      const td = document.createElement("td");
      td.textContent = text;
      tr.append(td);
    }
    tbody.append(tr);
  }
}

async function runExport(kind, button) {
  button.disabled = true;
  const output = $("export-output");
  output.classList.remove("hidden");
  output.textContent = "Exporting…";
  try {
    const result = await api("/api/export", { method: "POST", body: { kind } });
    output.textContent = result.output;
  } catch (error) {
    output.textContent = `Export failed: ${error.message}`;
  } finally {
    button.disabled = false;
    refreshExportFiles();
  }
}

function toggleCodeOnEditor(codeId) {
  if (!editor) return;
  editor.codeIds.has(codeId) ? editor.codeIds.delete(codeId) : editor.codeIds.add(codeId);
  renderEditorChips();
  renderCodeTrees();
}

async function createCode(parentId, isCategory = false) {
  const kind = isCategory ? "category" : "code";
  const title = prompt(parentId ? `New child ${kind} title:` : `New top-level ${kind} title:`);
  if (!title || !title.trim()) return;
  const description = prompt("Description (optional):") || "";
  await api("/api/codes", {
    method: "POST",
    body: { title, description, parent_id: parentId, is_category: isCategory },
  });
  if (parentId) expandedCodes.add(parentId);
  refreshCodes();
}

async function moveCode(codeId, newParentId) {
  // Client-side cycle guard (the server enforces it too)
  let ancestorId = newParentId;
  while (ancestorId !== null && ancestorId !== undefined) {
    if (ancestorId === codeId) {
      alert("Cannot move a code under its own descendant.");
      return;
    }
    const ancestor = codes.find((c) => c.id === ancestorId);
    ancestorId = ancestor ? ancestor.parent_id : null;
  }
  try {
    await api(`/api/codes/${codeId}`, { method: "PATCH", body: { parent_id: newParentId } });
  } catch (error) {
    alert(error.message);
  }
  if (newParentId) expandedCodes.add(newParentId);
  refreshCodes();
}

async function editCode(code) {
  // Renames only — definitions are edited in the right-hand panel
  const title = prompt("Code title:", code.title);
  if (title === null || !title.trim() || title === code.title) return;
  await api(`/api/codes/${code.id}`, { method: "PATCH", body: { title: title.trim() } });
  refreshCodes();
}

async function deleteCode(code) {
  if (!confirm(`Delete code "${code.title}"?`)) return;
  try {
    await api(`/api/codes/${code.id}`, { method: "DELETE" });
  } catch (error) {
    alert(error.message);
  }
  refreshCodes();
}

// ------------------------------------------------------------------ unanchored queue + manual anchoring

async function openUnanchoredView() {
  const rows = await api("/api/unanchored");
  const tbody = document.querySelector("#unanchored-table tbody");
  tbody.innerHTML = "";
  for (const row of rows) {
    const tr = document.createElement("tr");
    const anchorButton = document.createElement("button");
    anchorButton.textContent = row.pdf_filename ? "Anchor…" : "No PDF linked";
    anchorButton.disabled = !row.pdf_filename;
    anchorButton.onclick = () => startAnchoring(row);
    const cells = [
      row.media_title,
      (row.excerpt_text || "").slice(0, 300),
      row.dedoose_range || "",
      row.code_titles || "",
    ];
    for (const text of cells) {
      const td = document.createElement("td");
      td.textContent = text;
      tr.append(td);
    }
    const actionCell = document.createElement("td");
    actionCell.append(anchorButton);
    tr.append(actionCell);
    tbody.append(tr);
  }
  $("unanchored-view").classList.remove("hidden");
}

async function startAnchoring(unanchoredRow) {
  $("unanchored-view").classList.add("hidden");
  const doc = documents.find((d) => d.id === unanchoredRow.document_id);
  await openDocument(doc);
  anchorTarget = unanchoredRow;
  anchorSelection = null;
  searchMatches = [];
  searchMatchIndex = -1;
  $("anchor-bar").classList.remove("hidden");
  $("anchor-excerpt-text").textContent = `“${(unanchoredRow.excerpt_text || "").slice(0, 200)}”`;
  $("anchor-original-range").textContent = unanchoredRow.dedoose_range || "";
  $("anchor-save").disabled = true;
  const searchBox = $("anchor-search");
  const firstWords = (unanchoredRow.excerpt_text || "").split(/\s+/).slice(0, 5).join(" ");
  searchBox.value = firstWords;
  searchBox.focus();
  runAnchorSearch();
}

function exitAnchorMode() {
  anchorTarget = null;
  anchorSelection = null;
  searchMatches = [];
  searchMatchIndex = -1;
  $("anchor-bar").classList.add("hidden");
  clearSearchFlash();
}

async function buildDocTextCache() {
  if (docTextCache) return docTextCache;
  $("anchor-search-status").textContent = "indexing…";
  docTextCache = [];
  for (let i = 1; i <= pdfDoc.numPages; i++) {
    const page = await pdfDoc.getPage(i);
    const content = await page.getTextContent();
    let pageText = "";
    for (const item of content.items) {
      pageText += item.str;
      if (item.hasEOL) pageText += "\n";
    }
    docTextCache.push(pageText);
  }
  return docTextCache;
}

async function runAnchorSearch() {
  const query = $("anchor-search").value.trim().toLowerCase();
  clearSearchFlash();
  searchMatches = [];
  searchMatchIndex = -1;
  if (!query || !pdfDoc) {
    $("anchor-search-status").textContent = "";
    return;
  }
  const cache = await buildDocTextCache();
  for (let pageIndex = 0; pageIndex < cache.length; pageIndex++) {
    const lowerText = cache[pageIndex].toLowerCase();
    let position = lowerText.indexOf(query);
    while (position !== -1) {
      searchMatches.push({ pageIndex, start: position, length: query.length });
      position = lowerText.indexOf(query, position + 1);
    }
  }
  $("anchor-search-status").textContent = `${searchMatches.length} match(es)`;
  if (searchMatches.length) goToMatch(0);
}

async function goToMatch(matchIndex) {
  if (!searchMatches.length) return;
  searchMatchIndex = (matchIndex + searchMatches.length) % searchMatches.length;
  const match = searchMatches[searchMatchIndex];
  $("anchor-search-status").textContent = `${searchMatchIndex + 1} / ${searchMatches.length}`;
  const pageState = pages[match.pageIndex];
  pageState.container.scrollIntoView({ block: "center" });
  await renderPage(match.pageIndex);
  clearSearchFlash();
  // Flash the text spans overlapping the match interval
  const { items, textDivs, cumOffsets } = pageState;
  if (!items) return;
  const matchEnd = match.start + match.length;
  for (let i = 0; i < items.length; i++) {
    const itemStart = cumOffsets[i];
    const itemEnd = itemStart + items[i].str.length;
    if (itemEnd > match.start && itemStart < matchEnd && textDivs[i]) {
      textDivs[i].classList.add("search-flash");
    }
  }
}

function clearSearchFlash() {
  document.querySelectorAll(".search-flash").forEach((el) => el.classList.remove("search-flash"));
}

async function saveAnchor() {
  if (!anchorTarget || !anchorSelection) return;
  await api(`/api/excerpts/${anchorTarget.id}`, {
    method: "PATCH",
    body: {
      page_number: anchorSelection.pageNumber,
      char_start: anchorSelection.charStart,
      char_end: anchorSelection.charEnd,
      rects: anchorSelection.rects,
    },
  });
  exitAnchorMode();
  await reloadExcerpts();
  refreshDocuments();
}

async function markDocumentLevel() {
  if (!anchorTarget) return;
  await api(`/api/excerpts/${anchorTarget.id}`, {
    method: "PATCH",
    body: { anchor_status: "document_level" },
  });
  exitAnchorMode();
  await reloadExcerpts();
  refreshDocuments();
}

// ------------------------------------------------------------------ wiring

document.querySelectorAll("#tabs .tab").forEach((tabButton) => {
  tabButton.onclick = () => switchTab(tabButton.dataset.tab);
});

$("doc-filter").addEventListener("input", renderDocumentList);
$("sample-only").addEventListener("change", renderDocumentList);
document.querySelectorAll("#status-chips .chip").forEach((chip) => {
  chip.onclick = () => {
    document.querySelectorAll("#status-chips .chip").forEach((c) => c.classList.remove("active"));
    chip.classList.add("active");
    renderDocumentList();
  };
});

$("viewer").addEventListener("mouseup", onViewerMouseUp);
$("btn-zoom-in").onclick = () => setScale(scale + 0.25);
$("btn-zoom-out").onclick = () => setScale(scale - 0.25);

$("btn-save-excerpt").onclick = saveEditor;
$("btn-cancel-excerpt").onclick = cancelEditor;
$("btn-delete-excerpt").onclick = deleteCurrentExcerpt;
$("btn-add-root-code").onclick = () => createCode(null);
$("btn-add-root-category").onclick = () => createCode(null, true);
$("btn-code-history").onclick = toggleCodeHistory;

$("btn-expand-all").onclick = () => {
  expandedCodes = new Set(codes.map((c) => c.id));
  renderCodeTrees();
};
$("btn-collapse-all").onclick = () => {
  expandedCodes = new Set();
  renderCodeTrees();
};

$("btn-edit-definition").onclick = () => {
  if (!selectedCodeId) return;
  const code = codes.find((c) => c.id === selectedCodeId);
  $("code-display-input").value = code.display_name || "";
  $("code-display-input").placeholder = code.title;
  $("code-def-textarea").value = code.description || "";
  $("code-def-row").classList.add("hidden");
  $("code-display-line").classList.add("hidden");
  $("code-history-list").classList.add("hidden");
  $("code-def-editor").classList.remove("hidden");
  $("code-def-textarea").focus();
};
$("btn-cancel-definition").onclick = () => {
  $("code-def-editor").classList.add("hidden");
  $("code-def-row").classList.remove("hidden");
};
$("btn-save-definition").onclick = async () => {
  if (!selectedCodeId) return;
  await api(`/api/codes/${selectedCodeId}`, {
    method: "PATCH",
    body: {
      display_name: $("code-display-input").value.trim() || null,
      description: $("code-def-textarea").value.trim(),
    },
  });
  await refreshCodes();  // re-renders the definition panel via selectCodebookCode
};

const rootDropZone = $("root-drop-zone");
rootDropZone.ondragover = (event) => {
  event.preventDefault();
  rootDropZone.classList.add("drop-target");
};
rootDropZone.ondragleave = () => rootDropZone.classList.remove("drop-target");
rootDropZone.ondrop = (event) => {
  event.preventDefault();
  rootDropZone.classList.remove("drop-target");
  const draggedId = Number(event.dataTransfer.getData("text/code-id"));
  if (draggedId) moveCode(draggedId, null);
};

$("btn-scan").onclick = async () => {
  const result = await api("/api/documents/scan", { method: "POST" });
  alert(`Scan complete: ${result.added} new file(s) of ${result.total_on_disk} on disk.`);
  refreshDocuments();
};
$("btn-export-native").onclick = () => runExport("native", $("btn-export-native"));
$("btn-export-dedoose").onclick = () => runExport("dedoose", $("btn-export-dedoose"));

$("review-kind").addEventListener("change", refreshReviewEstimate);
$("btn-review-run").onclick = async () => {
  const kind = $("review-kind").value;
  const codeIds = selectedReviewCodeIds();
  if (!codeIds.length) {
    alert("Select 1-3 codes first.");
    return;
  }
  const scope = codeIds
    .map((id) => codes.find((c) => c.id === id).title)
    .join(", ");
  if (!confirm(`Run the "${kind}" review for: ${scope}?\n${$("review-estimate").textContent}`)) return;
  $("btn-review-run").disabled = true;
  try {
    await api("/api/review/run", { method: "POST", body: { kind, code_ids: codeIds } });
  } catch (error) {
    alert(error.message);
  } finally {
    $("btn-review-run").disabled = false;
    refreshReviewJobs();
  }
};

$("btn-unanchored").onclick = openUnanchoredView;
$("btn-close-unanchored").onclick = () => $("unanchored-view").classList.add("hidden");
$("anchor-search").addEventListener("keydown", (event) => {
  if (event.key === "Enter") runAnchorSearch();
});
$("anchor-prev").onclick = () => goToMatch(searchMatchIndex - 1);
$("anchor-next").onclick = () => goToMatch(searchMatchIndex + 1);
$("anchor-save").onclick = saveAnchor;
$("anchor-doc-level").onclick = markDocumentLevel;
$("anchor-cancel").onclick = exitAnchorMode;

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") {
    if (anchorTarget) exitAnchorMode();
    else cancelEditor();
  }
});

// ------------------------------------------------------------------ start

(async function start() {
  await Promise.all([refreshDocuments(), refreshCodes()]);
  if (!documents.length) {
    await api("/api/documents/scan", { method: "POST" });
    await refreshDocuments();
  }
})();
