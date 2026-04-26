# PDFedit Roadmap

Focused PyQt6 PDF editor for local view, rearrange, merge, split, and annotate workflows. Roadmap prioritizes depth over breadth — beat web tools at round-trip fidelity and OCR.

## Planned Features

### Page & Document
- Thumbnail multi-select with shift/ctrl range and drag-move across documents
- Page extraction to new document (retain bookmarks + named destinations)
- Page numbering / Bates numbering overlay with font + position presets
- Header/footer templates with `{page}` `{total}` `{date}` tokens
- Watermark tool (text + image, per-page or range, opacity + rotation)

### Editing
- Text edit in place — detect font, re-embed, preserve kerning where possible
- Image replace/insert with bounding box drag
- Redaction tool (black-box + text removal, not just cover) with re-save guard
- Form field editor (AcroForm): add text, checkbox, radio, signature fields
- Digital signature with PKCS#12 cert + visible signature appearance

### OCR & Content
- OCR via Tesseract (via `pytesseract`) — searchable PDF output
- Export text-only / markdown / docx conversions
- Bookmark / outline editor with drag tree
- Attachments panel (add/extract embedded files)
- Compare two PDFs with side-by-side diff highlighting

### Batch & CLI
- Headless CLI: `pdfedit merge a.pdf b.pdf -o c.pdf`, split, ocr, redact
- Folder watch mode (auto-process drops)
- Scriptable actions (Python recipe file) for repeated pipelines

## Competitive Research
- **PDFsam Basic** — strong split/merge, weak editor. Lesson: PDFedit should fold their feature set in and go further on annotation.
- **Stirling PDF** — self-hosted web toolbox; broad feature list. Lesson: mirror their 40+ operations as menu items — batch redact, compress, repair.
- **PDF24 Creator (Windows)** — consumer tool with printer driver and compression. Lesson: ship a virtual printer so any app can PDF-to-PDFedit.
- **Xournal++** — gold standard for handwritten annotation on tablets. Lesson: add a pen-pressure layer with proper stylus input.

## Nice-to-Haves
- Compression presets (web / print / archive) using ghostscript or pikepdf
- Embed / strip fonts tool with subset report
- PDF repair mode for damaged xref tables
- Dark mode preview that doesn't alter source rendering
- Password + permissions editor (open password, print/edit/copy flags)
- Touch-friendly annotation layout for convertible laptops

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
- Redaction with irreversible pixel burn + structural text removal (PDF4QT).
- Document comparison / diff between two PDFs (PDF4QT).
- Text-to-speech reader mode (PDF4QT).
- Form-filling (AcroForm + XFA read) (PDF4QT + PyMuPDF).
- Signature verification + optional signing via pyhanko (pikepdf integration path).
- Natural-pen annotation with tablet pressure (leed_pdf_viewer).
- File attachment management inside PDFs (PDF4QT).
- Page manipulator CLI companion alongside the GUI (PDF4QT ships one).

### Patterns & Architectures Worth Studying
- **PyMuPDF as single backend for render+edit+annotate** — avoids the fitz/poppler split other projects suffer.
- **pdf.js embed via QtWebEngine for render parity with browsers** (Axel-Erfurt) — fallback when native render diverges.
- **Command-layer/MVC** (PDF4QT) — every edit is a reversible Command object; enables free undo/redo across annotate+structure.
- **Tauri + WebCanvas for drawing UX** (leed_pdf_viewer) — worth studying as a post-PyQt migration target.
