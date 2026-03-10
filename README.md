# PDFedit

![License](https://img.shields.io/badge/license-MIT-blue)
![Language](https://img.shields.io/badge/language-Python-3776AB)
![Type](https://img.shields.io/badge/type-Desktop%20App-brightgreen)
![Python](https://img.shields.io/badge/python-3.8%2B-blue)

A focused PDF editor built with Python and PyQt6. View, rearrange, merge, split, and annotate PDF files with a clean dark-themed desktop interface. No subscription, no cloud upload — runs entirely local.

## Quick Start

```bash
python PDFedit.py
```

Dependencies auto-install on first run. No manual `pip install` needed.

## Features

- **PDF Viewer** — Browse pages with smooth zoom (25%–400%), fit-to-width, and keyboard navigation
- **Page Management** — Drag to reorder pages, rotate pages 90°/180°, delete individual pages
- **Merge** — Combine two or more PDFs into a single document; drag to set page order
- **Split** — Extract a page range or specific pages into a new PDF file
- **Annotations** — Add freehand text overlays, highlight regions, and sticky notes
- **Export** — Save any modified document as a new PDF with full fidelity
- **Dark Theme** — Professional dark-themed interface throughout

## Usage

### Opening a PDF

Drag and drop a PDF onto the window, or use **File → Open**.

### Merging PDFs

1. **File → Merge** to open the merge dialog
2. Add multiple PDF files — drag to reorder
3. Click **Merge** to produce a combined PDF

### Splitting a PDF

1. **File → Split**
2. Enter a page range (e.g. `1-5` or `3,7,12`)
3. Choose output file location and click **Split**

### Reordering Pages

In the page panel on the left, drag page thumbnails to the desired order, then **File → Save As** to write the reordered PDF.

## Requirements

- Python 3.8+
- Windows / macOS / Linux

## License

MIT License
