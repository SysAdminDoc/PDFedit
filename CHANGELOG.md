# Changelog

All notable changes to PDFedit will be documented in this file.

## [v0.2.0] - 2026-08-09

- Added: Headless document APIs for safe redaction saves, page extraction and reordering, form fields, attachments, Markdown export, and PDF comparison.
- Added: Headless CLI commands for merge, split, OCR, redaction, watermarking, comparison, encryption, signatures, recipes, and folder watching.
- Added: Multi-page thumbnail selection and drag transfer, named-destination-aware extraction, image replacement, bookmark editing, form fields, attachments, comparison, signatures, and expanded watermark/export dialogs.
- Added: Font-aware editing, pressure-sensitive drawing, compression presets, font reports, repair copies, display-only dark preview, permission controls, touch-friendly controls, text-to-speech, XFA reads, and signature verification.

## [v0.1.0] - %Y->- (HEAD -> main, origin/main, origin/HEAD)

- Added: Add screenshot to README
- Added: Add screenshot to README
- Added: Add screenshot to README
- docs: expand README with quick start, usage examples, and feature details
- Added: Add comprehensive README
- Changed: Update and rename pdf_editor_pro_v2.py to PDFedit.py
- Changed: Update pdf_editor_pro_v2.py
- Changed: Update pdf_editor_pro_v2.py
- Added: Add files via upload

## Roadmap archive — 2026-08-10 — ROADMAP.md

<details>
<summary>Original roadmap snapshot</summary>

```markdown
# PDFedit Roadmap

Focused PyQt6 PDF editor for local view, rearrange, merge, split, and annotate workflows. Roadmap prioritizes depth over breadth — beat web tools at round-trip fidelity and OCR.

## Planned Features

### Page & Document

### Editing

### OCR & Content

### Batch & CLI

## Competitive Research
- **PDFsam Basic** — strong split/merge, weak editor. Lesson: PDFedit should fold their feature set in and go further on annotation.
- **Stirling PDF** — self-hosted web toolbox; broad feature list. Lesson: mirror their 40+ operations as menu items — batch redact, compress, repair.
- **PDF24 Creator (Windows)** — consumer tool with printer driver and compression. Lesson: ship a virtual printer so any app can PDF-to-PDFedit.
- **Xournal++** — gold standard for handwritten annotation on tablets. Lesson: add a pen-pressure layer with proper stylus input.

## Nice-to-Haves

## Open-Source Research (Round 2)

### Related OSS Projects
- https://github.com/JakubMelka/PDF4QT — Qt/C++ PDF editor, PDF 2.0 spec coverage, annotations + forms + redaction. Relicensed MIT in 2025.
- https://github.com/BBC-Esq/PyQt6-PDF-Viewer — Minimal PyQt6 viewer, clean embedding reference.
- https://github.com/Axel-Erfurt/Qt5PDFViewer — PyQt5 + pdf.js/QtWebEngine hybrid.
- https://github.com/ksharindam/gospel-pdf-viewer — Poppler-backed fast PyQt5 viewer.
- https://github.com/pymupdf/PyMuPDF — fitz bindings; the canonical Python PDF edit/annotate backend.
- https://github.com/rudi-q/leed_pdf_viewer — SvelteKit/Tauri annotation tool, strong pen/tablet UX.
- https://github.com/py-pdf/pypdf — Pure-Python PDF manipulation (merge/split/metadata).
- https://github.com/pikepdf/pikepdf — qpdf-based Python lib, best for structural edits and linearization.

### Features to Borrow

### Patterns & Architectures Worth Studying
- **PyMuPDF as single backend for render+edit+annotate** — avoids the fitz/poppler split other projects suffer.
- **pdf.js embed via QtWebEngine for render parity with browsers** (Axel-Erfurt) — fallback when native render diverges.
- **Command-layer/MVC** (PDF4QT) — every edit is a reversible Command object; enables free undo/redo across annotate+structure.
- **Tauri + WebCanvas for drawing UX** (leed_pdf_viewer) — worth studying as a post-PyQt migration target.
```

</details>
