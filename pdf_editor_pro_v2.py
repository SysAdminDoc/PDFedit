#!/usr/bin/env python3
"""
PDF Editor Pro v3.0 - Professional PDF Editing Suite
A comprehensive Adobe Acrobat Pro alternative

NEW IN v3.0:
- Full menu bar with all operations
- Stamps library (Approved, Draft, Confidential, etc.)
- Watermarks (text-based)
- Headers & Footers with page numbers
- Bates numbering for legal documents
- Export to Word (.docx)
- Export to Images (PNG/JPG)
- Flatten annotations
- Password protection
- Document properties editor
- Split document into separate files

EXISTING FEATURES:
- Multi-tab document interface
- Search within documents (Ctrl+F)
- Bookmarks/Outline navigation
- Comments & Sticky Notes
- Form filling
- Compress/Optimize PDF
- Crop pages
- Recent files
- Full annotation toolkit
- OCR with invisible text layer

Auto-installs all dependencies on first run.
"""

import sys
import subprocess
import os
import platform
import urllib.request
import zipfile
import shutil
import tempfile
import json
from pathlib import Path

# ============================================================================
# AUTO-INSTALLER
# ============================================================================

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TESSERACT_DIR = os.path.join(SCRIPT_DIR, "tesseract_ocr")
CONFIG_DIR = os.path.join(SCRIPT_DIR, "pdf_editor_config")
TESSERACT_VERSION = "5.5.0"
TESSERACT_DATE = "20241111"
TESSERACT_URL = f"https://github.com/tesseract-ocr/tesseract/releases/download/{TESSERACT_VERSION}/tesseract-ocr-w64-setup-{TESSERACT_VERSION}.{TESSERACT_DATE}.exe"

def get_tesseract_path():
    if platform.system() == "Windows":
        paths = [
            os.path.join(TESSERACT_DIR, "tesseract.exe"),
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        ]
        for path in paths:
            if os.path.exists(path):
                return path
    return None

def download_file(url, dest_path, desc="Downloading"):
    print(f"  {desc}...")
    try:
        opener = urllib.request.build_opener()
        opener.addheaders = [('User-Agent', 'Mozilla/5.0')]
        urllib.request.install_opener(opener)
        def hook(b, bs, ts):
            if ts > 0:
                pct = min(100, b * bs * 100 // ts)
                print(f"\r    [{'█' * (pct//3)}{'░' * (33-pct//3)}] {pct}%", end="", flush=True)
        urllib.request.urlretrieve(url, dest_path, hook)
        print()
        return True
    except Exception as e:
        print(f"\n    Error: {e}")
        return False

def install_tesseract_windows():
    print("\n  Installing Tesseract OCR...")
    os.makedirs(TESSERACT_DIR, exist_ok=True)
    temp_dir = tempfile.mkdtemp()
    installer = os.path.join(temp_dir, "setup.exe")
    try:
        if download_file(TESSERACT_URL, installer, "Downloading Tesseract OCR (~70MB)"):
            print("    Running installer...")
            subprocess.run([installer, "/S", f"/D={TESSERACT_DIR}"], capture_output=True, timeout=300)
            exe = os.path.join(TESSERACT_DIR, "tesseract.exe")
            if os.path.exists(exe):
                print("    ✓ Tesseract installed")
                shutil.rmtree(temp_dir, ignore_errors=True)
                return exe
            for p in [r"C:\Program Files\Tesseract-OCR\tesseract.exe"]:
                if os.path.exists(p):
                    return p
    except Exception as e:
        print(f"    Error: {e}")
    shutil.rmtree(temp_dir, ignore_errors=True)
    return None

def pip_install(pkg):
    for method in [
        [sys.executable, "-m", "pip", "install", pkg, "-q"],
        [sys.executable, "-m", "pip", "install", pkg, "--break-system-packages", "-q"],
        [sys.executable, "-m", "pip", "install", pkg, "--user", "-q"],
    ]:
        try:
            if subprocess.run(method, capture_output=True, timeout=120).returncode == 0:
                return True
        except:
            pass
    return False

def check_and_install_dependencies():
    required = {'PIL': 'Pillow', 'fitz': 'PyMuPDF'}
    optional = {'pytesseract': 'pytesseract', 'docx': 'python-docx'}
    missing_req = [p for i, p in required.items() if not _try_import(i)]
    missing_opt = [p for i, p in optional.items() if not _try_import(i)]
    tesseract_needed = get_tesseract_path() is None
    
    if missing_req or missing_opt or tesseract_needed:
        print("\n╔══════════════════════════════════════════════════════════╗")
        print("║         PDF Editor Pro v3.0 - First Run Setup            ║")
        print("╚══════════════════════════════════════════════════════════╝\n")
        for pkg in missing_req + missing_opt:
            print(f"  Installing {pkg}...", end=" ", flush=True)
            print("✓" if pip_install(pkg) else "⚠")
        if tesseract_needed and platform.system() == "Windows":
            install_tesseract_windows()
        print("\n  Setup complete! Starting PDF Editor Pro...\n")
    
    for i, p in required.items():
        if not _try_import(i):
            print(f"ERROR: {p} required. Run: pip install {p}")
            sys.exit(1)
    
    if (path := get_tesseract_path()):
        os.environ["TESSERACT_CMD"] = path

def _try_import(name):
    try:
        __import__(name)
        return True
    except:
        return False

check_and_install_dependencies()

# ============================================================================
# IMPORTS
# ============================================================================

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog, colorchooser
from PIL import Image, ImageTk
import fitz
import io
import threading
import re
from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional, List, Tuple, Dict, Callable, Any
from enum import Enum, auto
from collections import deque
import copy
import math

# Try importing python-docx for Word export
try:
    from docx import Document as DocxDocument
    from docx.shared import Inches, Pt
    HAS_DOCX = True
except ImportError:
    HAS_DOCX = False

# Predefined stamps
BUILTIN_STAMPS = [
    {"name": "Approved", "text": "APPROVED", "color": "#ffffff", "bg": "#22c55e"},
    {"name": "Rejected", "text": "REJECTED", "color": "#ffffff", "bg": "#ef4444"},
    {"name": "Draft", "text": "DRAFT", "color": "#000000", "bg": "#fbbf24"},
    {"name": "Final", "text": "FINAL", "color": "#ffffff", "bg": "#3b82f6"},
    {"name": "Confidential", "text": "CONFIDENTIAL", "color": "#ffffff", "bg": "#dc2626"},
    {"name": "For Review", "text": "FOR REVIEW", "color": "#000000", "bg": "#f97316"},
    {"name": "Void", "text": "VOID", "color": "#ffffff", "bg": "#6b7280"},
    {"name": "Copy", "text": "COPY", "color": "#000000", "bg": "#a3e635"},
]

# ============================================================================
# CONFIGURATION
# ============================================================================

class Theme:
    """Modern dark theme"""
    BG_PRIMARY = "#0f0f0f"
    BG_SECONDARY = "#1a1a1a"
    BG_TERTIARY = "#252525"
    BG_HOVER = "#333333"
    BG_SELECTED = "#0066cc"
    BG_INPUT = "#2a2a2a"
    
    FG_PRIMARY = "#ffffff"
    FG_SECONDARY = "#aaaaaa"
    FG_MUTED = "#666666"
    
    ACCENT = "#0078d4"
    ACCENT_HOVER = "#1a86d9"
    SUCCESS = "#22c55e"
    WARNING = "#f59e0b"
    DANGER = "#ef4444"
    
    BORDER = "#333333"
    SCROLLBAR = "#444444"
    
    FONT = "Segoe UI"
    FONT_SIZE = 10
    FONT_SMALL = 9
    FONT_LARGE = 11
    FONT_TITLE = 13

class Config:
    """Application configuration"""
    MAX_RECENT_FILES = 10
    MAX_UNDO_STEPS = 50
    THUMBNAIL_SIZE = (120, 160)
    DEFAULT_ZOOM = 1.0
    MIN_ZOOM = 0.1
    MAX_ZOOM = 5.0
    
    @staticmethod
    def get_config_path():
        os.makedirs(CONFIG_DIR, exist_ok=True)
        return os.path.join(CONFIG_DIR, "config.json")
    
    @staticmethod
    def load():
        try:
            with open(Config.get_config_path(), 'r') as f:
                return json.load(f)
        except:
            return {"recent_files": [], "window_geometry": None}
    
    @staticmethod
    def save(data):
        try:
            with open(Config.get_config_path(), 'w') as f:
                json.dump(data, f, indent=2)
        except:
            pass

# ============================================================================
# DATA CLASSES
# ============================================================================

class ToolMode(Enum):
    SELECT = auto()
    PAN = auto()
    TEXT = auto()
    STICKY_NOTE = auto()
    HIGHLIGHT = auto()
    UNDERLINE = auto()
    STRIKETHROUGH = auto()
    DRAW = auto()
    RECTANGLE = auto()
    CIRCLE = auto()
    LINE = auto()
    ARROW = auto()
    IMAGE = auto()
    REDACT = auto()
    STAMP = auto()
    LINK = auto()
    CROP = auto()
    MEASURE = auto()

@dataclass
class SearchResult:
    page: int
    rect: Tuple[float, float, float, float]
    text: str

@dataclass
class Comment:
    id: str
    page: int
    x: float
    y: float
    content: str
    author: str = "User"
    date: str = ""
    color: str = "#ffeb3b"
    
    def __post_init__(self):
        if not self.date:
            self.date = datetime.now().strftime("%Y-%m-%d %H:%M")

@dataclass
class UndoAction:
    action_type: str
    page: int
    data: Any

# ============================================================================
# DOCUMENT MANAGER
# ============================================================================

class PDFDocument:
    """Manages a single PDF document with undo/redo support"""
    
    def __init__(self):
        self.doc: Optional[fitz.Document] = None
        self.filepath: Optional[str] = None
        self.is_modified = False
        self.comments: List[Comment] = []
        self.undo_stack: deque = deque(maxlen=Config.MAX_UNDO_STEPS)
        self.redo_stack: deque = deque(maxlen=Config.MAX_UNDO_STEPS)
        self._comment_counter = 0
    
    def open(self, filepath: str) -> bool:
        try:
            self.doc = fitz.open(filepath)
            self.filepath = filepath
            self.is_modified = False
            self.comments = []
            self.undo_stack.clear()
            self.redo_stack.clear()
            self._load_comments()
            return True
        except Exception as e:
            print(f"Error opening PDF: {e}")
            return False
    
    def create_new(self, width=612, height=792):
        self.doc = fitz.open()
        self.doc.new_page(width=width, height=height)
        self.filepath = None
        self.is_modified = True
        self.comments = []
    
    def save(self, filepath: str = None) -> bool:
        if not self.doc:
            return False
        path = filepath or self.filepath
        if not path:
            return False
        try:
            self._save_comments()
            if path == self.filepath and self.filepath:
                self.doc.saveIncr()
            else:
                self.doc.save(path, garbage=4, deflate=True)
            self.filepath = path
            self.is_modified = False
            return True
        except Exception as e:
            print(f"Error saving: {e}")
            return False
    
    def close(self):
        if self.doc:
            self.doc.close()
        self.__init__()
    
    @property
    def page_count(self) -> int:
        return len(self.doc) if self.doc else 0
    
    @property
    def filename(self) -> str:
        if self.filepath:
            return os.path.basename(self.filepath)
        return "Untitled"
    
    def get_page(self, num: int):
        if self.doc and 0 <= num < len(self.doc):
            return self.doc[num]
        return None
    
    def render_page(self, page_num: int, zoom: float = 1.0) -> Optional[Image.Image]:
        page = self.get_page(page_num)
        if not page:
            return None
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        return Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    
    def get_page_size(self, page_num: int) -> Tuple[float, float]:
        page = self.get_page(page_num)
        return (page.rect.width, page.rect.height) if page else (612, 792)
    
    # Undo/Redo
    def push_undo(self, action_type: str, page: int, data: Any):
        self.undo_stack.append(UndoAction(action_type, page, copy.deepcopy(data)))
        self.redo_stack.clear()
        self.is_modified = True
    
    def can_undo(self) -> bool:
        return len(self.undo_stack) > 0
    
    def can_redo(self) -> bool:
        return len(self.redo_stack) > 0
    
    # Text operations
    def get_text(self, page_num: int) -> str:
        page = self.get_page(page_num)
        return page.get_text() if page else ""
    
    def search_text(self, query: str, case_sensitive: bool = False) -> List[SearchResult]:
        results = []
        if not self.doc or not query:
            return results
        flags = 0 if case_sensitive else fitz.TEXT_PRESERVE_WHITESPACE
        for i in range(len(self.doc)):
            page = self.doc[i]
            rects = page.search_for(query)
            for rect in rects:
                results.append(SearchResult(i, tuple(rect), query))
        return results
    
    # Page operations
    def delete_page(self, page_num: int) -> bool:
        if self.doc and 0 <= page_num < len(self.doc) and len(self.doc) > 1:
            self.doc.delete_page(page_num)
            self.is_modified = True
            return True
        return False
    
    def insert_page(self, index: int = -1, width: float = 612, height: float = 792):
        if self.doc:
            if index < 0:
                index = len(self.doc)
            self.doc.new_page(pno=index, width=width, height=height)
            self.is_modified = True
    
    def duplicate_page(self, page_num: int):
        if self.doc and 0 <= page_num < len(self.doc):
            self.doc.fullcopy_page(page_num, page_num + 1)
            self.is_modified = True
    
    def rotate_page(self, page_num: int, angle: int = 90):
        page = self.get_page(page_num)
        if page:
            page.set_rotation((page.rotation + angle) % 360)
            self.is_modified = True
    
    def move_page(self, from_idx: int, to_idx: int):
        if self.doc and 0 <= from_idx < len(self.doc) and 0 <= to_idx < len(self.doc):
            self.doc.move_page(from_idx, to_idx)
            self.is_modified = True
    
    def crop_page(self, page_num: int, rect: Tuple[float, float, float, float]):
        page = self.get_page(page_num)
        if page:
            page.set_cropbox(fitz.Rect(rect))
            self.is_modified = True
    
    # Annotations
    def add_text(self, page_num: int, text: str, x: float, y: float,
                 font_size: int = 12, color: tuple = (0, 0, 0)):
        page = self.get_page(page_num)
        if page:
            fitz_color = tuple(c/255 for c in color)
            writer = fitz.TextWriter(page.rect)
            font = fitz.Font("helv")
            writer.append((x, y), text, font=font, fontsize=font_size)
            writer.write_text(page, color=fitz_color)
            self.is_modified = True
    
    def add_highlight(self, page_num: int, rect: Tuple, color=(1, 1, 0)):
        page = self.get_page(page_num)
        if page:
            annot = page.add_highlight_annot(fitz.Rect(rect))
            annot.set_colors(stroke=color)
            annot.update()
            self.is_modified = True
    
    def add_underline(self, page_num: int, rect: Tuple):
        page = self.get_page(page_num)
        if page:
            annot = page.add_underline_annot(fitz.Rect(rect))
            annot.update()
            self.is_modified = True
    
    def add_strikethrough(self, page_num: int, rect: Tuple):
        page = self.get_page(page_num)
        if page:
            annot = page.add_strikeout_annot(fitz.Rect(rect))
            annot.update()
            self.is_modified = True
    
    def add_rect(self, page_num: int, rect: Tuple, color=(1, 0, 0), width=2):
        page = self.get_page(page_num)
        if page:
            shape = page.new_shape()
            shape.draw_rect(fitz.Rect(rect))
            shape.finish(color=color, width=width)
            shape.commit()
            self.is_modified = True
    
    def add_circle(self, page_num: int, rect: Tuple, color=(1, 0, 0), width=2):
        page = self.get_page(page_num)
        if page:
            shape = page.new_shape()
            shape.draw_circle(fitz.Rect(rect).center, min(rect[2]-rect[0], rect[3]-rect[1])/2)
            shape.finish(color=color, width=width)
            shape.commit()
            self.is_modified = True
    
    def add_line(self, page_num: int, p1: Tuple, p2: Tuple, color=(1, 0, 0), width=2):
        page = self.get_page(page_num)
        if page:
            shape = page.new_shape()
            shape.draw_line(p1, p2)
            shape.finish(color=color, width=width)
            shape.commit()
            self.is_modified = True
    
    def add_arrow(self, page_num: int, p1: Tuple, p2: Tuple, color=(1, 0, 0)):
        page = self.get_page(page_num)
        if page:
            annot = page.add_line_annot(fitz.Point(p1), fitz.Point(p2))
            annot.set_colors(stroke=color)
            annot.set_line_ends(fitz.PDF_ANNOT_LE_NONE, fitz.PDF_ANNOT_LE_OPEN_ARROW)
            annot.update()
            self.is_modified = True
    
    def add_freehand(self, page_num: int, points: List[Tuple], color=(0, 0, 1), width=2):
        page = self.get_page(page_num)
        if page and len(points) >= 2:
            shape = page.new_shape()
            shape.draw_polyline(points)
            shape.finish(color=color, width=width)
            shape.commit()
            self.is_modified = True
    
    def add_image(self, page_num: int, image_path: str, x: float, y: float,
                  width: float = None, height: float = None):
        page = self.get_page(page_num)
        if not page:
            return False
        try:
            img = Image.open(image_path)
            iw, ih = img.size
            if width and not height:
                height = width * ih / iw
            elif height and not width:
                width = height * iw / ih
            elif not width and not height:
                width, height = min(iw, 300), min(ih, 300)
                if iw > 300 or ih > 300:
                    scale = 300 / max(iw, ih)
                    width, height = iw * scale, ih * scale
            page.insert_image(fitz.Rect(x, y, x+width, y+height), filename=image_path)
            self.is_modified = True
            return True
        except:
            return False
    
    def redact_area(self, page_num: int, rect: Tuple):
        page = self.get_page(page_num)
        if page:
            page.add_redact_annot(fitz.Rect(rect))
            page.apply_redactions()
            self.is_modified = True
    
    # Comments
    def add_comment(self, page: int, x: float, y: float, content: str) -> Comment:
        self._comment_counter += 1
        comment = Comment(f"comment_{self._comment_counter}", page, x, y, content)
        self.comments.append(comment)
        self.is_modified = True
        return comment
    
    def delete_comment(self, comment_id: str):
        self.comments = [c for c in self.comments if c.id != comment_id]
        self.is_modified = True
    
    def _load_comments(self):
        # Load comments from PDF annotations
        if not self.doc:
            return
        for i, page in enumerate(self.doc):
            for annot in page.annots():
                if annot.type[0] == fitz.PDF_ANNOT_TEXT:
                    self._comment_counter += 1
                    rect = annot.rect
                    self.comments.append(Comment(
                        f"comment_{self._comment_counter}",
                        i, rect.x0, rect.y0,
                        annot.info.get("content", ""),
                        annot.info.get("title", "User")
                    ))
    
    def _save_comments(self):
        # Save comments as PDF annotations
        if not self.doc:
            return
        # Remove existing text annotations
        for page in self.doc:
            annots_to_delete = [a for a in page.annots() if a.type[0] == fitz.PDF_ANNOT_TEXT]
            for annot in annots_to_delete:
                page.delete_annot(annot)
        # Add current comments
        for comment in self.comments:
            page = self.get_page(comment.page)
            if page:
                annot = page.add_text_annot((comment.x, comment.y), comment.content)
                annot.set_info(title=comment.author)
                annot.update()
    
    # Bookmarks
    def get_bookmarks(self) -> List[Tuple[int, str, int]]:
        """Returns list of (level, title, page)"""
        if not self.doc:
            return []
        toc = self.doc.get_toc()
        return [(item[0], item[1], item[2]-1) for item in toc]
    
    # Form fields
    def get_form_fields(self, page_num: int) -> List[Dict]:
        page = self.get_page(page_num)
        if not page:
            return []
        fields = []
        for widget in page.widgets():
            fields.append({
                'name': widget.field_name,
                'type': widget.field_type_string,
                'value': widget.field_value,
                'rect': tuple(widget.rect),
                'widget': widget
            })
        return fields
    
    def set_form_field(self, page_num: int, field_name: str, value: str):
        page = self.get_page(page_num)
        if not page:
            return
        for widget in page.widgets():
            if widget.field_name == field_name:
                widget.field_value = value
                widget.update()
                self.is_modified = True
                break
    
    # Optimization
    def compress(self, output_path: str, image_quality: int = 75) -> bool:
        if not self.doc:
            return False
        try:
            self.doc.save(output_path, garbage=4, deflate=True, 
                         clean=True, linear=True)
            return True
        except:
            return False
    
    # Watermarks
    def add_watermark(self, text: str, font_size: int = 48, color: Tuple = (0.8, 0.8, 0.8),
                      angle: float = 45, pages: List[int] = None):
        if not self.doc:
            return
        pages = pages or range(len(self.doc))
        for pnum in pages:
            page = self.get_page(pnum)
            if not page:
                continue
            rect = page.rect
            cx, cy = rect.width / 2, rect.height / 2
            text_width = len(text) * font_size * 0.5
            page.insert_text(
                fitz.Point(cx - text_width/2, cy + font_size/3),
                text, fontsize=font_size, fontname="helv",
                color=color, rotate=angle
            )
        self.is_modified = True
    
    # Headers & Footers
    def add_header_footer(self, header: str = None, footer: str = None,
                         font_size: int = 10, margin: float = 36,
                         pages: List[int] = None, start_page: int = 1):
        if not self.doc:
            return
        pages = pages or range(len(self.doc))
        for i, pnum in enumerate(pages):
            page = self.get_page(pnum)
            if not page:
                continue
            pw, ph = page.rect.width, page.rect.height
            page_num = start_page + i
            
            def process_text(txt):
                if not txt:
                    return None
                txt = txt.replace("{page}", str(page_num))
                txt = txt.replace("{pages}", str(len(self.doc)))
                txt = txt.replace("{date}", datetime.now().strftime("%Y-%m-%d"))
                txt = txt.replace("{filename}", self.filename)
                return txt
            
            if header:
                h_text = process_text(header)
                text_width = len(h_text) * font_size * 0.4
                x = (pw - text_width) / 2
                page.insert_text((x, margin), h_text, fontsize=font_size, fontname="helv", color=(0, 0, 0))
            
            if footer:
                f_text = process_text(footer)
                text_width = len(f_text) * font_size * 0.4
                x = (pw - text_width) / 2
                page.insert_text((x, ph - margin + font_size), f_text, fontsize=font_size, fontname="helv", color=(0, 0, 0))
        self.is_modified = True
    
    # Bates Numbering
    def add_bates_numbers(self, prefix: str = "", start: int = 1, digits: int = 6,
                         suffix: str = "", position: str = "bottom-right",
                         font_size: int = 10, margin: float = 36):
        if not self.doc:
            return
        for i, page in enumerate(self.doc):
            num = start + i
            bates = f"{prefix}{num:0{digits}d}{suffix}"
            pw, ph = page.rect.width, page.rect.height
            text_width = len(bates) * font_size * 0.5
            positions = {
                "top-left": (margin, margin + font_size),
                "top-center": ((pw - text_width) / 2, margin + font_size),
                "top-right": (pw - text_width - margin, margin + font_size),
                "bottom-left": (margin, ph - margin),
                "bottom-center": ((pw - text_width) / 2, ph - margin),
                "bottom-right": (pw - text_width - margin, ph - margin),
            }
            x, y = positions.get(position, positions["bottom-right"])
            page.insert_text((x, y), bates, fontsize=font_size, fontname="helv", color=(0, 0, 0))
        self.is_modified = True
    
    # Flatten annotations
    def flatten_annotations(self):
        if not self.doc:
            return
        for page in self.doc:
            for annot in list(page.annots()):
                annot.set_flags(fitz.PDF_ANNOT_IS_PRINT)
            page.clean_contents()
        self.is_modified = True
    
    # Remove metadata
    def remove_metadata(self):
        if self.doc:
            self.doc.set_metadata({})
            self.is_modified = True
    
    # Export to Word
    def export_to_word(self, output_path: str) -> bool:
        if not HAS_DOCX or not self.doc:
            return False
        try:
            doc = DocxDocument()
            for i in range(len(self.doc)):
                if i > 0:
                    doc.add_page_break()
                text = self.get_text(i)
                if text.strip():
                    doc.add_paragraph(text)
            doc.save(output_path)
            return True
        except:
            return False
    
    # Export to images
    def export_to_images(self, output_dir: str, dpi: int = 150, fmt: str = "png") -> List[str]:
        files = []
        if not self.doc:
            return files
        zoom = dpi / 72
        for i in range(len(self.doc)):
            page = self.doc[i]
            pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
            path = os.path.join(output_dir, f"page_{i+1:03d}.{fmt}")
            pix.save(path)
            files.append(path)
        return files
    
    # Export text
    def export_text(self, output_path: str) -> bool:
        if not self.doc:
            return False
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                for i in range(len(self.doc)):
                    f.write(f"--- Page {i+1} ---\n{self.get_text(i)}\n\n")
            return True
        except:
            return False
    
    # Add stamp
    def add_stamp(self, page_num: int, x: float, y: float, stamp: dict):
        page = self.get_page(page_num)
        if not page:
            return
        text = stamp['text']
        font_size = 14
        text_width = len(text) * font_size * 0.6
        stamp_w = text_width + 20
        stamp_h = font_size + 16
        
        def hex_to_rgb(h):
            h = h.lstrip('#')
            return tuple(int(h[i:i+2], 16)/255 for i in (0, 2, 4))
        
        bg = hex_to_rgb(stamp['bg'])
        fg = hex_to_rgb(stamp['color'])
        
        shape = page.new_shape()
        shape.draw_rect(fitz.Rect(x, y, x + stamp_w, y + stamp_h))
        shape.finish(color=bg, fill=bg, width=2)
        shape.commit()
        
        page.insert_text((x + 10, y + stamp_h - 8), text, fontsize=font_size, fontname="hebo", color=fg)
        self.is_modified = True
    
    # Metadata
    def get_metadata(self) -> Dict:
        return dict(self.doc.metadata) if self.doc else {}
    
    def set_metadata(self, metadata: Dict):
        if self.doc:
            self.doc.set_metadata(metadata)
            self.is_modified = True
    
    # Merge/Split
    def merge_pdf(self, other_path: str):
        if self.doc:
            other = fitz.open(other_path)
            self.doc.insert_pdf(other)
            other.close()
            self.is_modified = True
    
    def split_pages(self, output_dir: str) -> List[str]:
        files = []
        if not self.doc:
            return files
        for i in range(len(self.doc)):
            new_doc = fitz.open()
            new_doc.insert_pdf(self.doc, from_page=i, to_page=i)
            path = os.path.join(output_dir, f"page_{i+1:03d}.pdf")
            new_doc.save(path)
            new_doc.close()
            files.append(path)
        return files

# ============================================================================
# OCR ENGINE
# ============================================================================

class OCREngine:
    @staticmethod
    def is_available() -> Tuple[bool, str]:
        try:
            import pytesseract
            OCREngine._configure()
            pytesseract.get_tesseract_version()
            return True, "OK"
        except ImportError:
            return False, "pytesseract not installed"
        except:
            return False, "Tesseract not found. Restart app to install."
    
    @staticmethod
    def _configure():
        try:
            import pytesseract
            path = os.environ.get("TESSERACT_CMD")
            if path and os.path.exists(path):
                pytesseract.pytesseract.tesseract_cmd = path
        except:
            pass
    
    @staticmethod
    def make_searchable(doc: PDFDocument, page_num: int = None, 
                        callback: Callable = None) -> Tuple[bool, int]:
        try:
            import pytesseract
            OCREngine._configure()
        except:
            return False, 0
        
        pages = [page_num] if page_num is not None else range(doc.page_count)
        processed = 0
        
        for pnum in pages:
            page = doc.get_page(pnum)
            if not page:
                continue
            if callback:
                callback(f"OCR page {pnum + 1}...")
            
            # Render at 2x
            img = doc.render_page(pnum, zoom=2.0)
            if not img:
                continue
            
            pw, ph = page.rect.width, page.rect.height
            iw, ih = img.size
            sx, sy = pw / iw, ph / ih
            
            # Get word boxes
            data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
            
            for i in range(len(data['text'])):
                text = data['text'][i].strip()
                conf = int(data['conf'][i]) if str(data['conf'][i]).lstrip('-').isdigit() else 0
                if not text or conf < 30:
                    continue
                
                x, y, w, h = data['left'][i], data['top'][i], data['width'][i], data['height'][i]
                px, py = x * sx, y * sy
                pw_t, ph_t = w * sx, h * sy
                
                fs = ph_t * 0.85
                fs = max(4, min(72, fs))
                
                try:
                    tl = fitz.get_text_length(text, fontsize=fs)
                    if tl > 0 and pw_t > 0:
                        fs = max(4, min(72, fs * (pw_t / tl)))
                    
                    page.insert_text(
                        (px, py + ph_t * 0.85),
                        text, fontsize=fs, fontname="helv",
                        color=(0, 0, 0), render_mode=3
                    )
                except:
                    pass
            
            processed += 1
        
        if processed > 0:
            doc.is_modified = True
        return processed > 0, processed
    
    @staticmethod
    def extract_text(doc: PDFDocument, callback: Callable = None) -> str:
        try:
            import pytesseract
            OCREngine._configure()
        except:
            return ""
        
        texts = []
        for i in range(doc.page_count):
            if callback:
                callback(f"Page {i + 1}...")
            img = doc.render_page(i, zoom=2.0)
            if img:
                texts.append(f"--- Page {i + 1} ---\n{pytesseract.image_to_string(img)}")
        return "\n\n".join(texts)

# ============================================================================
# UI COMPONENTS
# ============================================================================

class ToolButton(tk.Canvas):
    def __init__(self, parent, text="", icon="", tooltip="", command=None, 
                 size=36, toggle=False, **kw):
        super().__init__(parent, width=size, height=size, 
                        bg=Theme.BG_SECONDARY, highlightthickness=0, **kw)
        self.text = icon or text
        self.tooltip_text = tooltip
        self.command = command
        self.size = size
        self.toggle = toggle
        self.is_active = False
        self.is_hover = False
        self._tip = None
        
        self._draw()
        self.bind("<Enter>", self._enter)
        self.bind("<Leave>", self._leave)
        self.bind("<Button-1>", self._click)
    
    def _draw(self):
        self.delete("all")
        if self.is_active:
            fill = Theme.ACCENT
        elif self.is_hover:
            fill = Theme.BG_HOVER
        else:
            fill = Theme.BG_SECONDARY
        
        self.create_rectangle(2, 2, self.size-2, self.size-2, fill=fill, outline="")
        fg = Theme.BG_PRIMARY if self.is_active else Theme.FG_PRIMARY
        self.create_text(self.size//2, self.size//2, text=self.text, fill=fg,
                        font=(Theme.FONT, 12))
    
    def _enter(self, e):
        self.is_hover = True
        self._draw()
        if self.tooltip_text:
            self._tip = tk.Toplevel(self)
            self._tip.wm_overrideredirect(True)
            self._tip.wm_geometry(f"+{self.winfo_rootx()+self.size}+{self.winfo_rooty()}")
            tk.Label(self._tip, text=self.tooltip_text, bg=Theme.BG_TERTIARY, 
                    fg=Theme.FG_PRIMARY, padx=6, pady=3,
                    font=(Theme.FONT, Theme.FONT_SMALL)).pack()
    
    def _leave(self, e):
        self.is_hover = False
        self._draw()
        if self._tip:
            self._tip.destroy()
            self._tip = None
    
    def _click(self, e):
        if self.toggle:
            self.is_active = not self.is_active
            self._draw()
        if self.command:
            self.command()
    
    def set_active(self, active: bool):
        self.is_active = active
        self._draw()

class SearchBar(tk.Frame):
    def __init__(self, parent, on_search: Callable, on_close: Callable, **kw):
        super().__init__(parent, bg=Theme.BG_TERTIARY, **kw)
        self.on_search = on_search
        self.on_close = on_close
        
        # Search entry
        self.entry = tk.Entry(self, width=30, bg=Theme.BG_INPUT, fg=Theme.FG_PRIMARY,
                             insertbackground=Theme.FG_PRIMARY, relief=tk.FLAT,
                             font=(Theme.FONT, Theme.FONT_SIZE))
        self.entry.pack(side=tk.LEFT, padx=(10, 5), pady=8)
        self.entry.bind("<Return>", lambda e: self._search())
        self.entry.bind("<Escape>", lambda e: self.on_close())
        
        # Buttons
        tk.Button(self, text="Find", command=self._search, bg=Theme.ACCENT, 
                 fg=Theme.FG_PRIMARY, relief=tk.FLAT, padx=10,
                 font=(Theme.FONT, Theme.FONT_SMALL)).pack(side=tk.LEFT, padx=2)
        
        tk.Button(self, text="◀", command=lambda: self._search(-1), 
                 bg=Theme.BG_HOVER, fg=Theme.FG_PRIMARY, relief=tk.FLAT, width=3,
                 font=(Theme.FONT, Theme.FONT_SMALL)).pack(side=tk.LEFT, padx=2)
        
        tk.Button(self, text="▶", command=lambda: self._search(1), 
                 bg=Theme.BG_HOVER, fg=Theme.FG_PRIMARY, relief=tk.FLAT, width=3,
                 font=(Theme.FONT, Theme.FONT_SMALL)).pack(side=tk.LEFT, padx=2)
        
        # Results label
        self.results_label = tk.Label(self, text="", bg=Theme.BG_TERTIARY, 
                                      fg=Theme.FG_SECONDARY,
                                      font=(Theme.FONT, Theme.FONT_SMALL))
        self.results_label.pack(side=tk.LEFT, padx=10)
        
        # Close button
        tk.Button(self, text="✕", command=self.on_close, bg=Theme.BG_TERTIARY,
                 fg=Theme.FG_SECONDARY, relief=tk.FLAT, width=2,
                 font=(Theme.FONT, Theme.FONT_SIZE)).pack(side=tk.RIGHT, padx=5)
        
        self.results: List[SearchResult] = []
        self.current_idx = -1
    
    def _search(self, direction: int = 0):
        query = self.entry.get()
        if not query:
            return
        
        if direction == 0:  # New search
            self.results = self.on_search(query)
            self.current_idx = 0 if self.results else -1
        else:  # Navigate
            if self.results:
                self.current_idx = (self.current_idx + direction) % len(self.results)
        
        if self.results:
            self.results_label.config(text=f"{self.current_idx + 1} of {len(self.results)}")
        else:
            self.results_label.config(text="No results")
    
    def focus_entry(self):
        self.entry.focus_set()
        self.entry.select_range(0, tk.END)
    
    def get_current_result(self) -> Optional[SearchResult]:
        if 0 <= self.current_idx < len(self.results):
            return self.results[self.current_idx]
        return None

class SidebarPanel(tk.Frame):
    def __init__(self, parent, title: str, **kw):
        super().__init__(parent, bg=Theme.BG_SECONDARY, **kw)
        
        # Header
        header = tk.Frame(self, bg=Theme.BG_TERTIARY)
        header.pack(fill=tk.X)
        
        tk.Label(header, text=title, bg=Theme.BG_TERTIARY, fg=Theme.FG_PRIMARY,
                font=(Theme.FONT, Theme.FONT_LARGE, "bold"),
                padx=10, pady=8).pack(side=tk.LEFT)
        
        # Content area
        self.content = tk.Frame(self, bg=Theme.BG_SECONDARY)
        self.content.pack(fill=tk.BOTH, expand=True)

class PageThumbnail(tk.Canvas):
    def __init__(self, parent, page_num: int, image: Image.Image, 
                 on_select: Callable, on_context: Callable = None, **kw):
        super().__init__(parent, width=130, height=170, 
                        bg=Theme.BG_SECONDARY, highlightthickness=0, **kw)
        self.page_num = page_num
        self.on_select = on_select
        self.on_context = on_context
        self.selected = False
        self.hover = False
        
        # Resize thumbnail
        image.thumbnail((110, 140), Image.Resampling.LANCZOS)
        self.photo = ImageTk.PhotoImage(image)
        
        self._draw()
        self.bind("<Enter>", lambda e: self._set_hover(True))
        self.bind("<Leave>", lambda e: self._set_hover(False))
        self.bind("<Button-1>", lambda e: self.on_select(self.page_num))
        self.bind("<Button-3>", self._context_menu)
    
    def _draw(self):
        self.delete("all")
        if self.selected:
            self.create_rectangle(0, 0, 130, 170, fill=Theme.BG_SELECTED, outline="")
        elif self.hover:
            self.create_rectangle(0, 0, 130, 170, fill=Theme.BG_HOVER, outline="")
        
        # Border
        bc = Theme.ACCENT if self.selected else Theme.BORDER
        self.create_rectangle(9, 5, 121, 145, fill="#ffffff", outline=bc, width=2)
        self.create_image(65, 75, image=self.photo)
        
        # Page number
        self.create_text(65, 158, text=str(self.page_num + 1), 
                        fill=Theme.FG_PRIMARY, font=(Theme.FONT, Theme.FONT_SMALL))
    
    def _set_hover(self, h: bool):
        self.hover = h
        self._draw()
    
    def set_selected(self, s: bool):
        self.selected = s
        self._draw()
    
    def _context_menu(self, event):
        if self.on_context:
            self.on_context(event, self.page_num)

class PropertiesPanel(tk.Frame):
    def __init__(self, parent, **kw):
        super().__init__(parent, bg=Theme.BG_SECONDARY, width=250, **kw)
        self.pack_propagate(False)
        
        # Header
        header = tk.Frame(self, bg=Theme.BG_TERTIARY)
        header.pack(fill=tk.X)
        tk.Label(header, text="Properties", bg=Theme.BG_TERTIARY, fg=Theme.FG_PRIMARY,
                font=(Theme.FONT, Theme.FONT_LARGE, "bold"),
                padx=10, pady=8).pack(side=tk.LEFT)
        
        # Content
        self.content = tk.Frame(self, bg=Theme.BG_SECONDARY)
        self.content.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.info_labels = {}
    
    def show_page_info(self, doc: PDFDocument, page_num: int):
        for w in self.content.winfo_children():
            w.destroy()
        
        if not doc.doc:
            return
        
        page = doc.get_page(page_num)
        if not page:
            return
        
        info = [
            ("Page", str(page_num + 1)),
            ("Width", f"{page.rect.width:.1f} pt"),
            ("Height", f"{page.rect.height:.1f} pt"),
            ("Rotation", f"{page.rotation}°"),
        ]
        
        for label, value in info:
            row = tk.Frame(self.content, bg=Theme.BG_SECONDARY)
            row.pack(fill=tk.X, pady=3)
            tk.Label(row, text=label + ":", bg=Theme.BG_SECONDARY, fg=Theme.FG_SECONDARY,
                    font=(Theme.FONT, Theme.FONT_SMALL), width=10, anchor='w').pack(side=tk.LEFT)
            tk.Label(row, text=value, bg=Theme.BG_SECONDARY, fg=Theme.FG_PRIMARY,
                    font=(Theme.FONT, Theme.FONT_SMALL)).pack(side=tk.LEFT)
    
    def show_document_info(self, doc: PDFDocument):
        for w in self.content.winfo_children():
            w.destroy()
        
        if not doc.doc:
            return
        
        meta = doc.doc.metadata
        info = [
            ("File", doc.filename),
            ("Pages", str(doc.page_count)),
            ("Title", meta.get('title', 'N/A')[:20]),
            ("Author", meta.get('author', 'N/A')[:20]),
        ]
        
        for label, value in info:
            row = tk.Frame(self.content, bg=Theme.BG_SECONDARY)
            row.pack(fill=tk.X, pady=3)
            tk.Label(row, text=label + ":", bg=Theme.BG_SECONDARY, fg=Theme.FG_SECONDARY,
                    font=(Theme.FONT, Theme.FONT_SMALL), width=10, anchor='w').pack(side=tk.LEFT)
            tk.Label(row, text=value, bg=Theme.BG_SECONDARY, fg=Theme.FG_PRIMARY,
                    font=(Theme.FONT, Theme.FONT_SMALL), wraplength=120, anchor='w').pack(side=tk.LEFT)

class TabBar(tk.Frame):
    def __init__(self, parent, on_select: Callable, on_close: Callable, **kw):
        super().__init__(parent, bg=Theme.BG_PRIMARY, height=32, **kw)
        self.pack_propagate(False)
        self.on_select = on_select
        self.on_close = on_close
        self.tabs: Dict[str, tk.Frame] = {}
        self.active_tab: str = None
    
    def add_tab(self, tab_id: str, title: str):
        tab = tk.Frame(self, bg=Theme.BG_SECONDARY, padx=10, pady=5)
        tab.pack(side=tk.LEFT, padx=(1, 0))
        
        label = tk.Label(tab, text=title[:20], bg=Theme.BG_SECONDARY, fg=Theme.FG_PRIMARY,
                        font=(Theme.FONT, Theme.FONT_SMALL))
        label.pack(side=tk.LEFT)
        
        close_btn = tk.Label(tab, text="✕", bg=Theme.BG_SECONDARY, fg=Theme.FG_MUTED,
                            font=(Theme.FONT, Theme.FONT_SMALL), cursor="hand2")
        close_btn.pack(side=tk.LEFT, padx=(8, 0))
        close_btn.bind("<Button-1>", lambda e: self.on_close(tab_id))
        
        tab.bind("<Button-1>", lambda e: self.on_select(tab_id))
        label.bind("<Button-1>", lambda e: self.on_select(tab_id))
        
        self.tabs[tab_id] = tab
        self.set_active(tab_id)
    
    def remove_tab(self, tab_id: str):
        if tab_id in self.tabs:
            self.tabs[tab_id].destroy()
            del self.tabs[tab_id]
    
    def set_active(self, tab_id: str):
        for tid, tab in self.tabs.items():
            if tid == tab_id:
                tab.configure(bg=Theme.BG_TERTIARY)
                for child in tab.winfo_children():
                    child.configure(bg=Theme.BG_TERTIARY)
            else:
                tab.configure(bg=Theme.BG_SECONDARY)
                for child in tab.winfo_children():
                    child.configure(bg=Theme.BG_SECONDARY)
        self.active_tab = tab_id
    
    def update_title(self, tab_id: str, title: str):
        if tab_id in self.tabs:
            for child in self.tabs[tab_id].winfo_children():
                if isinstance(child, tk.Label) and child.cget("text") != "✕":
                    child.configure(text=title[:20])
                    break

# ============================================================================
# MAIN APPLICATION
# ============================================================================

class PDFEditorPro(tk.Tk):
    def __init__(self):
        super().__init__()
        
        self.title("PDF Editor Pro v3.0")
        self.geometry("1400x900")
        self.minsize(1100, 700)
        self.configure(bg=Theme.BG_PRIMARY)
        
        # State
        self.documents: Dict[str, PDFDocument] = {}
        self.active_doc_id: str = None
        self.current_page = 0
        self.zoom = 1.0
        self.tool_mode = ToolMode.SELECT
        self.draw_color = (0, 0, 0)
        self.draw_points = []
        self.drag_start = None
        self.thumbnails: List[PageThumbnail] = []
        self.page_image = None
        self.search_highlights = []
        self.selected_stamp = None
        
        # Config
        self.config_data = Config.load()
        
        # Build UI
        self._build_menu()
        self._build_ui()
        self._bind_shortcuts()
        
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        
        # Show welcome or recent
        self._show_welcome()
    
    def _build_menu(self):
        menubar = tk.Menu(self, bg=Theme.BG_TERTIARY, fg=Theme.FG_PRIMARY)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0, bg=Theme.BG_TERTIARY, fg=Theme.FG_PRIMARY)
        file_menu.add_command(label="New", command=self._new_doc, accelerator="Ctrl+N")
        file_menu.add_command(label="Open...", command=self._open_doc, accelerator="Ctrl+O")
        file_menu.add_separator()
        file_menu.add_command(label="Save", command=self._save_doc, accelerator="Ctrl+S")
        file_menu.add_command(label="Save As...", command=self._save_as)
        file_menu.add_separator()
        file_menu.add_command(label="Close", command=self._close_tab, accelerator="Ctrl+W")
        file_menu.add_separator()
        file_menu.add_command(label="Properties...", command=self._show_properties)
        file_menu.add_separator()
        file_menu.add_command(label="Print...", command=self._print_doc, accelerator="Ctrl+P")
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self._on_close)
        menubar.add_cascade(label="File", menu=file_menu)
        
        # Edit menu
        edit_menu = tk.Menu(menubar, tearoff=0, bg=Theme.BG_TERTIARY, fg=Theme.FG_PRIMARY)
        edit_menu.add_command(label="Find...", command=self._show_search, accelerator="Ctrl+F")
        edit_menu.add_separator()
        edit_menu.add_command(label="Copy Page Text", command=self._copy_page_text)
        menubar.add_cascade(label="Edit", menu=edit_menu)
        
        # View menu
        view_menu = tk.Menu(menubar, tearoff=0, bg=Theme.BG_TERTIARY, fg=Theme.FG_PRIMARY)
        view_menu.add_command(label="Zoom In", command=self._zoom_in, accelerator="Ctrl++")
        view_menu.add_command(label="Zoom Out", command=self._zoom_out, accelerator="Ctrl+-")
        view_menu.add_command(label="Fit Page", command=self._zoom_fit, accelerator="Ctrl+0")
        view_menu.add_command(label="Actual Size (100%)", command=self._zoom_100, accelerator="Ctrl+1")
        view_menu.add_separator()
        view_menu.add_command(label="Rotate CW", command=lambda: self._rotate(self.current_page, 90))
        view_menu.add_command(label="Rotate CCW", command=lambda: self._rotate(self.current_page, -90))
        menubar.add_cascade(label="View", menu=view_menu)
        
        # Page menu
        page_menu = tk.Menu(menubar, tearoff=0, bg=Theme.BG_TERTIARY, fg=Theme.FG_PRIMARY)
        page_menu.add_command(label="Insert Blank Page", command=lambda: self._insert_page(self.current_page + 1))
        page_menu.add_command(label="Duplicate Page", command=self._duplicate_page)
        page_menu.add_separator()
        page_menu.add_command(label="Delete Page", command=self._delete_page, accelerator="Delete")
        page_menu.add_command(label="Extract Page...", command=lambda: self._extract_page(self.current_page))
        page_menu.add_separator()
        page_menu.add_command(label="Crop Page...", command=lambda: self._set_tool(ToolMode.CROP))
        menubar.add_cascade(label="Page", menu=page_menu)
        
        # Tools menu
        tools_menu = tk.Menu(menubar, tearoff=0, bg=Theme.BG_TERTIARY, fg=Theme.FG_PRIMARY)
        tools_menu.add_command(label="Add Text", command=lambda: self._set_tool(ToolMode.TEXT))
        tools_menu.add_command(label="Add Sticky Note", command=lambda: self._set_tool(ToolMode.STICKY_NOTE))
        tools_menu.add_command(label="Add Image...", command=self._add_image_dialog)
        tools_menu.add_separator()
        tools_menu.add_command(label="Highlight", command=lambda: self._set_tool(ToolMode.HIGHLIGHT))
        tools_menu.add_command(label="Underline", command=lambda: self._set_tool(ToolMode.UNDERLINE))
        tools_menu.add_command(label="Strikethrough", command=lambda: self._set_tool(ToolMode.STRIKETHROUGH))
        tools_menu.add_separator()
        tools_menu.add_command(label="Rectangle", command=lambda: self._set_tool(ToolMode.RECTANGLE))
        tools_menu.add_command(label="Circle", command=lambda: self._set_tool(ToolMode.CIRCLE))
        tools_menu.add_command(label="Arrow", command=lambda: self._set_tool(ToolMode.ARROW))
        tools_menu.add_command(label="Freehand", command=lambda: self._set_tool(ToolMode.DRAW))
        tools_menu.add_separator()
        tools_menu.add_command(label="Add Stamp...", command=self._show_stamp_picker)
        tools_menu.add_separator()
        tools_menu.add_command(label="Redact Area", command=lambda: self._set_tool(ToolMode.REDACT))
        menubar.add_cascade(label="Tools", menu=tools_menu)
        
        # Document menu
        doc_menu = tk.Menu(menubar, tearoff=0, bg=Theme.BG_TERTIARY, fg=Theme.FG_PRIMARY)
        doc_menu.add_command(label="Merge PDFs...", command=self._merge_pdfs)
        doc_menu.add_command(label="Split Document...", command=self._split_document)
        doc_menu.add_separator()
        doc_menu.add_command(label="Add Watermark...", command=self._watermark_dialog)
        doc_menu.add_command(label="Add Header/Footer...", command=self._header_footer_dialog)
        doc_menu.add_command(label="Add Bates Numbers...", command=self._bates_dialog)
        doc_menu.add_separator()
        doc_menu.add_command(label="OCR - Make Searchable...", command=self._ocr_document)
        doc_menu.add_separator()
        doc_menu.add_command(label="Compress PDF...", command=self._compress_pdf)
        doc_menu.add_command(label="Flatten Annotations", command=self._flatten_annotations)
        doc_menu.add_command(label="Remove Metadata", command=self._remove_metadata)
        doc_menu.add_separator()
        doc_menu.add_command(label="Set Password...", command=self._set_password_dialog)
        menubar.add_cascade(label="Document", menu=doc_menu)
        
        # Export menu
        export_menu = tk.Menu(menubar, tearoff=0, bg=Theme.BG_TERTIARY, fg=Theme.FG_PRIMARY)
        export_menu.add_command(label="Export to Word...", command=self._export_to_word)
        export_menu.add_command(label="Export to Images...", command=self._export_to_images)
        export_menu.add_command(label="Export Text...", command=self._export_text)
        menubar.add_cascade(label="Export", menu=export_menu)
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0, bg=Theme.BG_TERTIARY, fg=Theme.FG_PRIMARY)
        help_menu.add_command(label="Keyboard Shortcuts", command=self._show_shortcuts)
        help_menu.add_separator()
        help_menu.add_command(label="About", command=self._show_about)
        menubar.add_cascade(label="Help", menu=help_menu)
        
        self.config(menu=menubar)
    
    @property
    def doc(self) -> Optional[PDFDocument]:
        return self.documents.get(self.active_doc_id)
    
    def _build_ui(self):
        # Tab bar
        self.tab_bar = TabBar(self, self._on_tab_select, self._on_tab_close)
        self.tab_bar.pack(fill=tk.X)
        
        # Main container
        self.main = tk.Frame(self, bg=Theme.BG_PRIMARY)
        self.main.pack(fill=tk.BOTH, expand=True)
        
        # Toolbar
        self._build_toolbar()
        
        # Content area
        content = tk.Frame(self.main, bg=Theme.BG_PRIMARY)
        content.pack(fill=tk.BOTH, expand=True)
        
        # Left sidebar
        self._build_left_sidebar(content)
        
        # Canvas area
        self._build_canvas(content)
        
        # Right sidebar
        self.props_panel = PropertiesPanel(content)
        self.props_panel.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Search bar (hidden initially)
        self.search_bar = SearchBar(self.main, self._do_search, self._hide_search)
        
        # Status bar
        self._build_status_bar()
    
    def _build_toolbar(self):
        toolbar = tk.Frame(self.main, bg=Theme.BG_SECONDARY, height=50)
        toolbar.pack(fill=tk.X)
        toolbar.pack_propagate(False)
        
        # File group
        file_frame = tk.Frame(toolbar, bg=Theme.BG_SECONDARY)
        file_frame.pack(side=tk.LEFT, padx=10, pady=7)
        
        self.tool_btns = {}
        
        for icon, tip, cmd in [
            ("📄", "New (Ctrl+N)", self._new_doc),
            ("📂", "Open (Ctrl+O)", self._open_doc),
            ("💾", "Save (Ctrl+S)", self._save_doc),
        ]:
            ToolButton(file_frame, icon=icon, tooltip=tip, command=cmd).pack(side=tk.LEFT, padx=1)
        
        self._add_separator(toolbar)
        
        # Edit group
        edit_frame = tk.Frame(toolbar, bg=Theme.BG_SECONDARY)
        edit_frame.pack(side=tk.LEFT, padx=5, pady=7)
        
        self.undo_btn = ToolButton(edit_frame, icon="↩", tooltip="Undo (Ctrl+Z)", command=self._undo)
        self.undo_btn.pack(side=tk.LEFT, padx=1)
        self.redo_btn = ToolButton(edit_frame, icon="↪", tooltip="Redo (Ctrl+Y)", command=self._redo)
        self.redo_btn.pack(side=tk.LEFT, padx=1)
        
        self._add_separator(toolbar)
        
        # Tool group
        tool_frame = tk.Frame(toolbar, bg=Theme.BG_SECONDARY)
        tool_frame.pack(side=tk.LEFT, padx=5, pady=7)
        
        tools = [
            ("👆", "Select", ToolMode.SELECT),
            ("✋", "Pan", ToolMode.PAN),
            ("T", "Add Text", ToolMode.TEXT),
            ("📝", "Sticky Note", ToolMode.STICKY_NOTE),
            ("🔆", "Highlight", ToolMode.HIGHLIGHT),
            ("U̲", "Underline", ToolMode.UNDERLINE),
            ("S̶", "Strikethrough", ToolMode.STRIKETHROUGH),
            ("✏️", "Draw", ToolMode.DRAW),
            ("▢", "Rectangle", ToolMode.RECTANGLE),
            ("○", "Circle", ToolMode.CIRCLE),
            ("↗", "Arrow", ToolMode.ARROW),
            ("🖼", "Image", ToolMode.IMAGE),
            ("▮", "Redact", ToolMode.REDACT),
            ("✂", "Crop", ToolMode.CROP),
        ]
        
        for icon, tip, mode in tools:
            btn = ToolButton(tool_frame, icon=icon, tooltip=tip, 
                           command=lambda m=mode: self._set_tool(m))
            btn.pack(side=tk.LEFT, padx=1)
            self.tool_btns[mode] = btn
        
        self.tool_btns[ToolMode.SELECT].set_active(True)
        
        self._add_separator(toolbar)
        
        # Color picker
        self.color_btn = ToolButton(toolbar, icon="🎨", tooltip="Color",
                                    command=self._pick_color)
        self.color_btn.pack(side=tk.LEFT, padx=5, pady=7)
        
        # Right side - Navigation & Zoom
        right = tk.Frame(toolbar, bg=Theme.BG_SECONDARY)
        right.pack(side=tk.RIGHT, padx=10, pady=7)
        
        # Zoom
        ToolButton(right, icon="−", tooltip="Zoom Out", command=self._zoom_out).pack(side=tk.LEFT)
        self.zoom_label = tk.Label(right, text="100%", bg=Theme.BG_SECONDARY, 
                                   fg=Theme.FG_PRIMARY, width=6,
                                   font=(Theme.FONT, Theme.FONT_SIZE))
        self.zoom_label.pack(side=tk.LEFT, padx=5)
        ToolButton(right, icon="+", tooltip="Zoom In", command=self._zoom_in).pack(side=tk.LEFT)
        ToolButton(right, icon="⊡", tooltip="Fit", command=self._zoom_fit).pack(side=tk.LEFT, padx=(5,15))
        
        # Page nav
        ToolButton(right, icon="⏮", tooltip="First", command=self._first_page).pack(side=tk.LEFT)
        ToolButton(right, icon="◀", tooltip="Previous", command=self._prev_page).pack(side=tk.LEFT)
        
        self.page_entry = tk.Entry(right, width=5, justify='center',
                                   bg=Theme.BG_INPUT, fg=Theme.FG_PRIMARY,
                                   insertbackground=Theme.FG_PRIMARY, relief=tk.FLAT,
                                   font=(Theme.FONT, Theme.FONT_SIZE))
        self.page_entry.pack(side=tk.LEFT, padx=5)
        self.page_entry.bind("<Return>", self._goto_page)
        
        self.page_total = tk.Label(right, text="/ 0", bg=Theme.BG_SECONDARY,
                                   fg=Theme.FG_SECONDARY, font=(Theme.FONT, Theme.FONT_SIZE))
        self.page_total.pack(side=tk.LEFT)
        
        ToolButton(right, icon="▶", tooltip="Next", command=self._next_page).pack(side=tk.LEFT, padx=(5,0))
        ToolButton(right, icon="⏭", tooltip="Last", command=self._last_page).pack(side=tk.LEFT)
    
    def _add_separator(self, parent):
        tk.Frame(parent, width=2, height=30, bg=Theme.BORDER).pack(side=tk.LEFT, padx=5, pady=10)
    
    def _build_left_sidebar(self, parent):
        self.left_sidebar = tk.Frame(parent, bg=Theme.BG_SECONDARY, width=160)
        self.left_sidebar.pack(side=tk.LEFT, fill=tk.Y)
        self.left_sidebar.pack_propagate(False)
        
        # Sidebar tabs
        tab_frame = tk.Frame(self.left_sidebar, bg=Theme.BG_TERTIARY)
        tab_frame.pack(fill=tk.X)
        
        self.sidebar_tabs = {}
        for name, icon in [("Pages", "📄"), ("Bookmarks", "📑"), ("Comments", "💬")]:
            btn = tk.Label(tab_frame, text=icon, bg=Theme.BG_TERTIARY, fg=Theme.FG_SECONDARY,
                          font=(Theme.FONT, 14), padx=12, pady=6, cursor="hand2")
            btn.pack(side=tk.LEFT)
            btn.bind("<Button-1>", lambda e, n=name: self._show_sidebar_tab(n))
            self.sidebar_tabs[name] = btn
        
        # Content frames
        self.sidebar_content = tk.Frame(self.left_sidebar, bg=Theme.BG_SECONDARY)
        self.sidebar_content.pack(fill=tk.BOTH, expand=True)
        
        # Pages panel
        self.pages_frame = tk.Frame(self.sidebar_content, bg=Theme.BG_SECONDARY)
        self.thumb_canvas = tk.Canvas(self.pages_frame, bg=Theme.BG_SECONDARY, highlightthickness=0)
        self.thumb_scroll = ttk.Scrollbar(self.pages_frame, orient=tk.VERTICAL, 
                                          command=self.thumb_canvas.yview)
        self.thumb_frame = tk.Frame(self.thumb_canvas, bg=Theme.BG_SECONDARY)
        
        self.thumb_canvas.configure(yscrollcommand=self.thumb_scroll.set)
        self.thumb_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.thumb_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.thumb_canvas.create_window((0, 0), window=self.thumb_frame, anchor=tk.NW)
        self.thumb_frame.bind("<Configure>", 
            lambda e: self.thumb_canvas.configure(scrollregion=self.thumb_canvas.bbox("all")))
        
        # Bookmarks panel
        self.bookmarks_frame = tk.Frame(self.sidebar_content, bg=Theme.BG_SECONDARY)
        self.bookmarks_tree = ttk.Treeview(self.bookmarks_frame, show="tree")
        self.bookmarks_tree.pack(fill=tk.BOTH, expand=True)
        self.bookmarks_tree.bind("<<TreeviewSelect>>", self._on_bookmark_select)
        
        # Comments panel
        self.comments_frame = tk.Frame(self.sidebar_content, bg=Theme.BG_SECONDARY)
        self.comments_list = tk.Listbox(self.comments_frame, bg=Theme.BG_TERTIARY,
                                        fg=Theme.FG_PRIMARY, selectbackground=Theme.ACCENT,
                                        font=(Theme.FONT, Theme.FONT_SMALL), relief=tk.FLAT)
        self.comments_list.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.comments_list.bind("<<ListboxSelect>>", self._on_comment_select)
        
        # Show pages by default
        self._show_sidebar_tab("Pages")
    
    def _show_sidebar_tab(self, name: str):
        # Update tab appearance
        for n, btn in self.sidebar_tabs.items():
            btn.configure(fg=Theme.ACCENT if n == name else Theme.FG_SECONDARY)
        
        # Show correct frame
        for frame in [self.pages_frame, self.bookmarks_frame, self.comments_frame]:
            frame.pack_forget()
        
        if name == "Pages":
            self.pages_frame.pack(fill=tk.BOTH, expand=True)
        elif name == "Bookmarks":
            self.bookmarks_frame.pack(fill=tk.BOTH, expand=True)
            self._refresh_bookmarks()
        elif name == "Comments":
            self.comments_frame.pack(fill=tk.BOTH, expand=True)
            self._refresh_comments()
    
    def _build_canvas(self, parent):
        canvas_frame = tk.Frame(parent, bg=Theme.BG_PRIMARY)
        canvas_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.h_scroll = ttk.Scrollbar(canvas_frame, orient=tk.HORIZONTAL)
        self.v_scroll = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL)
        
        self.canvas = tk.Canvas(canvas_frame, bg=Theme.BG_TERTIARY, highlightthickness=0,
                               xscrollcommand=self.h_scroll.set, yscrollcommand=self.v_scroll.set)
        
        self.h_scroll.configure(command=self.canvas.xview)
        self.v_scroll.configure(command=self.canvas.yview)
        
        self.v_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.h_scroll.pack(side=tk.BOTTOM, fill=tk.X)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Bindings
        self.canvas.bind("<Button-1>", self._canvas_click)
        self.canvas.bind("<B1-Motion>", self._canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self._canvas_release)
        self.canvas.bind("<MouseWheel>", self._canvas_scroll)
        self.canvas.bind("<Button-4>", lambda e: self._canvas_scroll_linux(-1))
        self.canvas.bind("<Button-5>", lambda e: self._canvas_scroll_linux(1))
        self.canvas.bind("<Button-3>", self._canvas_context)
    
    def _build_status_bar(self):
        status = tk.Frame(self, bg=Theme.BG_SECONDARY, height=26)
        status.pack(fill=tk.X, side=tk.BOTTOM)
        status.pack_propagate(False)
        
        self.status_left = tk.Label(status, text="Ready", bg=Theme.BG_SECONDARY, 
                                    fg=Theme.FG_SECONDARY, font=(Theme.FONT, Theme.FONT_SMALL))
        self.status_left.pack(side=tk.LEFT, padx=10, pady=4)
        
        self.status_right = tk.Label(status, text="", bg=Theme.BG_SECONDARY, 
                                     fg=Theme.FG_SECONDARY, font=(Theme.FONT, Theme.FONT_SMALL))
        self.status_right.pack(side=tk.RIGHT, padx=10, pady=4)
    
    def _bind_shortcuts(self):
        self.bind("<Control-n>", lambda e: self._new_doc())
        self.bind("<Control-o>", lambda e: self._open_doc())
        self.bind("<Control-s>", lambda e: self._save_doc())
        self.bind("<Control-S>", lambda e: self._save_as())
        self.bind("<Control-w>", lambda e: self._close_tab())
        self.bind("<Control-f>", lambda e: self._show_search())
        self.bind("<Control-z>", lambda e: self._undo())
        self.bind("<Control-y>", lambda e: self._redo())
        self.bind("<Control-plus>", lambda e: self._zoom_in())
        self.bind("<Control-minus>", lambda e: self._zoom_out())
        self.bind("<Control-equal>", lambda e: self._zoom_in())
        self.bind("<Control-0>", lambda e: self._zoom_fit())
        self.bind("<Control-1>", lambda e: self._zoom_100())
        self.bind("<Home>", lambda e: self._first_page())
        self.bind("<End>", lambda e: self._last_page())
        self.bind("<Prior>", lambda e: self._prev_page())
        self.bind("<Next>", lambda e: self._next_page())
        self.bind("<Escape>", lambda e: self._set_tool(ToolMode.SELECT))
        self.bind("<Delete>", lambda e: self._delete_page())
    
    # =========================================================================
    # DOCUMENT MANAGEMENT
    # =========================================================================
    
    def _new_doc(self):
        doc_id = f"doc_{len(self.documents)}"
        doc = PDFDocument()
        doc.create_new()
        self.documents[doc_id] = doc
        self.tab_bar.add_tab(doc_id, "Untitled")
        self._switch_to_doc(doc_id)
    
    def _open_doc(self, filepath: str = None):
        if not filepath:
            filepath = filedialog.askopenfilename(
                filetypes=[("PDF Files", "*.pdf"), ("All Files", "*.*")])
        if not filepath:
            return
        
        doc_id = f"doc_{len(self.documents)}"
        doc = PDFDocument()
        if doc.open(filepath):
            self.documents[doc_id] = doc
            self.tab_bar.add_tab(doc_id, doc.filename)
            self._switch_to_doc(doc_id)
            self._add_recent(filepath)
            self._status(f"Opened: {doc.filename}")
        else:
            messagebox.showerror("Error", "Failed to open PDF.")
    
    def _save_doc(self):
        if not self.doc:
            return
        if not self.doc.filepath:
            self._save_as()
            return
        if self.doc.save():
            self._status("Saved")
            self._update_title()
        else:
            messagebox.showerror("Error", "Failed to save.")
    
    def _save_as(self):
        if not self.doc:
            return
        filepath = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF Files", "*.pdf")])
        if filepath:
            if self.doc.save(filepath):
                self._status(f"Saved: {self.doc.filename}")
                self._update_title()
                self._add_recent(filepath)
    
    def _close_tab(self):
        if not self.active_doc_id:
            return
        doc = self.doc
        if doc and doc.is_modified:
            r = messagebox.askyesnocancel("Save?", "Save changes before closing?")
            if r is None:
                return
            if r:
                self._save_doc()
        
        self.tab_bar.remove_tab(self.active_doc_id)
        if self.active_doc_id in self.documents:
            self.documents[self.active_doc_id].close()
            del self.documents[self.active_doc_id]
        
        # Switch to another tab
        if self.tab_bar.tabs:
            self._switch_to_doc(list(self.tab_bar.tabs.keys())[0])
        else:
            self.active_doc_id = None
            self.current_page = 0
            self._show_welcome()
    
    def _switch_to_doc(self, doc_id: str):
        if doc_id not in self.documents:
            return
        self.active_doc_id = doc_id
        self.current_page = 0
        self.zoom = 1.0
        self.tab_bar.set_active(doc_id)
        self._refresh_all()
    
    def _on_tab_select(self, doc_id: str):
        self._switch_to_doc(doc_id)
    
    def _on_tab_close(self, doc_id: str):
        self.active_doc_id = doc_id
        self._close_tab()
    
    def _update_title(self):
        if self.doc:
            mod = " *" if self.doc.is_modified else ""
            self.tab_bar.update_title(self.active_doc_id, self.doc.filename + mod)
            self.title(f"PDF Editor Pro - {self.doc.filename}{mod}")
        else:
            self.title("PDF Editor Pro")
    
    def _add_recent(self, filepath: str):
        recent = self.config_data.get("recent_files", [])
        if filepath in recent:
            recent.remove(filepath)
        recent.insert(0, filepath)
        self.config_data["recent_files"] = recent[:Config.MAX_RECENT_FILES]
        Config.save(self.config_data)
    
    # =========================================================================
    # VIEW
    # =========================================================================
    
    def _refresh_all(self):
        self._render_page()
        self._refresh_thumbnails()
        self._refresh_bookmarks()
        self._refresh_comments()
        self._update_ui()
    
    def _render_page(self):
        if not self.doc or not self.doc.doc:
            self._show_welcome()
            return
        
        img = self.doc.render_page(self.current_page, self.zoom)
        if not img:
            return
        
        self.page_image = ImageTk.PhotoImage(img)
        self.canvas.delete("all")
        
        cw = self.canvas.winfo_width() or 800
        ch = self.canvas.winfo_height() or 600
        iw, ih = img.size
        
        x = max(cw // 2, iw // 2)
        y = max(ch // 2, ih // 2)
        
        # Shadow
        self.canvas.create_rectangle(x - iw//2 + 4, y - ih//2 + 4,
                                     x + iw//2 + 4, y + ih//2 + 4,
                                     fill="#000000", outline="")
        # Background
        self.canvas.create_rectangle(x - iw//2, y - ih//2, x + iw//2, y + ih//2,
                                     fill="#ffffff", outline=Theme.BORDER)
        # Image
        self.canvas.create_image(x, y, image=self.page_image)
        
        self.img_offset_x = x - iw // 2
        self.img_offset_y = y - ih // 2
        
        # Draw comments
        for comment in self.doc.comments:
            if comment.page == self.current_page:
                cx = self.img_offset_x + comment.x * self.zoom
                cy = self.img_offset_y + comment.y * self.zoom
                self.canvas.create_polygon(cx, cy, cx+15, cy, cx+15, cy+18, cx+8, cy+12, cx, cy+12,
                                          fill=comment.color, outline=Theme.BORDER)
        
        # Search highlights
        for hl in self.search_highlights:
            if hl.page == self.current_page:
                r = hl.rect
                x1 = self.img_offset_x + r[0] * self.zoom
                y1 = self.img_offset_y + r[1] * self.zoom
                x2 = self.img_offset_x + r[2] * self.zoom
                y2 = self.img_offset_y + r[3] * self.zoom
                self.canvas.create_rectangle(x1, y1, x2, y2, fill="#ffff00", 
                                            stipple="gray50", outline="")
        
        self.canvas.configure(scrollregion=(0, 0, max(cw, iw+50), max(ch, ih+50)))
        self.props_panel.show_page_info(self.doc, self.current_page)
    
    def _refresh_thumbnails(self):
        for t in self.thumbnails:
            t.destroy()
        self.thumbnails = []
        
        if not self.doc or not self.doc.doc:
            return
        
        for i in range(self.doc.page_count):
            img = self.doc.render_page(i, 0.15)
            if img:
                t = PageThumbnail(self.thumb_frame, i, img, self._on_thumb_click, self._thumb_context)
                t.pack(pady=4, padx=5)
                t.set_selected(i == self.current_page)
                self.thumbnails.append(t)
    
    def _refresh_bookmarks(self):
        self.bookmarks_tree.delete(*self.bookmarks_tree.get_children())
        if not self.doc:
            return
        
        bookmarks = self.doc.get_bookmarks()
        parents = {0: ""}
        
        for level, title, page in bookmarks:
            parent = parents.get(level - 1, "")
            item = self.bookmarks_tree.insert(parent, "end", text=f"{title} (p.{page+1})", 
                                              values=(page,))
            parents[level] = item
    
    def _refresh_comments(self):
        self.comments_list.delete(0, tk.END)
        if not self.doc:
            return
        
        for c in self.doc.comments:
            preview = c.content[:30] + "..." if len(c.content) > 30 else c.content
            self.comments_list.insert(tk.END, f"p.{c.page+1}: {preview}")
    
    def _on_thumb_click(self, page_num: int):
        self.current_page = page_num
        self._render_page()
        for i, t in enumerate(self.thumbnails):
            t.set_selected(i == page_num)
        self._update_ui()
    
    def _thumb_context(self, event, page_num: int):
        menu = tk.Menu(self, tearoff=0, bg=Theme.BG_TERTIARY, fg=Theme.FG_PRIMARY)
        menu.add_command(label="Insert Page Before", command=lambda: self._insert_page(page_num))
        menu.add_command(label="Insert Page After", command=lambda: self._insert_page(page_num + 1))
        menu.add_separator()
        menu.add_command(label="Rotate Clockwise", command=lambda: self._rotate(page_num, 90))
        menu.add_command(label="Rotate Counter-Clockwise", command=lambda: self._rotate(page_num, -90))
        menu.add_separator()
        menu.add_command(label="Delete Page", command=lambda: self._delete_page(page_num))
        menu.add_separator()
        menu.add_command(label="Extract Page...", command=lambda: self._extract_page(page_num))
        menu.tk_popup(event.x_root, event.y_root)
    
    def _on_bookmark_select(self, event):
        sel = self.bookmarks_tree.selection()
        if sel:
            item = self.bookmarks_tree.item(sel[0])
            if item['values']:
                self.current_page = item['values'][0]
                self._render_page()
                self._update_ui()
    
    def _on_comment_select(self, event):
        sel = self.comments_list.curselection()
        if sel and self.doc:
            idx = sel[0]
            if idx < len(self.doc.comments):
                c = self.doc.comments[idx]
                self.current_page = c.page
                self._render_page()
                self._update_ui()
    
    def _update_ui(self):
        self.page_entry.delete(0, tk.END)
        self.page_entry.insert(0, str(self.current_page + 1) if self.doc else "0")
        self.page_total.configure(text=f"/ {self.doc.page_count if self.doc else 0}")
        self.zoom_label.configure(text=f"{int(self.zoom * 100)}%")
        
        if self.doc:
            mod = " (modified)" if self.doc.is_modified else ""
            self.status_right.configure(text=f"Page {self.current_page + 1} of {self.doc.page_count}{mod}")
        
        self._update_title()
    
    def _show_welcome(self):
        self.canvas.delete("all")
        cx, cy = 400, 300
        
        self.canvas.create_text(cx, cy - 50, text="📄", font=(Theme.FONT, 48), fill=Theme.ACCENT)
        self.canvas.create_text(cx, cy, text="PDF Editor Pro", 
                               font=(Theme.FONT, 24, "bold"), fill=Theme.FG_PRIMARY)
        self.canvas.create_text(cx, cy + 40, text="Open a PDF or create a new document",
                               font=(Theme.FONT, Theme.FONT_SIZE), fill=Theme.FG_SECONDARY)
        
        # Recent files
        recent = self.config_data.get("recent_files", [])[:5]
        if recent:
            self.canvas.create_text(cx, cy + 100, text="Recent Files:",
                                   font=(Theme.FONT, Theme.FONT_SIZE, "bold"), fill=Theme.FG_PRIMARY)
            for i, path in enumerate(recent):
                name = os.path.basename(path)
                y = cy + 125 + i * 22
                txt_id = self.canvas.create_text(cx, y, text=name, 
                                                font=(Theme.FONT, Theme.FONT_SIZE),
                                                fill=Theme.ACCENT, tags=f"recent_{i}")
                self.canvas.tag_bind(f"recent_{i}", "<Button-1>", 
                                    lambda e, p=path: self._open_doc(p))
                self.canvas.tag_bind(f"recent_{i}", "<Enter>",
                                    lambda e, t=txt_id: self.canvas.itemconfig(t, fill=Theme.ACCENT_HOVER))
                self.canvas.tag_bind(f"recent_{i}", "<Leave>",
                                    lambda e, t=txt_id: self.canvas.itemconfig(t, fill=Theme.ACCENT))
    
    def _status(self, msg: str):
        self.status_left.configure(text=msg)
    
    # =========================================================================
    # NAVIGATION & ZOOM
    # =========================================================================
    
    def _first_page(self):
        if self.doc and self.doc.page_count:
            self.current_page = 0
            self._render_page()
            self._update_ui()
    
    def _prev_page(self):
        if self.doc and self.current_page > 0:
            self.current_page -= 1
            self._render_page()
            self._update_ui()
    
    def _next_page(self):
        if self.doc and self.current_page < self.doc.page_count - 1:
            self.current_page += 1
            self._render_page()
            self._update_ui()
    
    def _last_page(self):
        if self.doc and self.doc.page_count:
            self.current_page = self.doc.page_count - 1
            self._render_page()
            self._update_ui()
    
    def _goto_page(self, event=None):
        try:
            p = int(self.page_entry.get()) - 1
            if self.doc and 0 <= p < self.doc.page_count:
                self.current_page = p
                self._render_page()
                self._update_ui()
        except:
            pass
    
    def _zoom_in(self):
        self.zoom = min(Config.MAX_ZOOM, self.zoom * 1.25)
        self._render_page()
        self._update_ui()
    
    def _zoom_out(self):
        self.zoom = max(Config.MIN_ZOOM, self.zoom / 1.25)
        self._render_page()
        self._update_ui()
    
    def _zoom_100(self):
        self.zoom = 1.0
        self._render_page()
        self._update_ui()
    
    def _zoom_fit(self):
        if not self.doc:
            return
        pw, ph = self.doc.get_page_size(self.current_page)
        cw = self.canvas.winfo_width() - 40
        ch = self.canvas.winfo_height() - 40
        self.zoom = min(cw / pw, ch / ph)
        self._render_page()
        self._update_ui()
    
    def _canvas_scroll(self, event):
        if event.state & 0x4:  # Ctrl
            self._zoom_in() if event.delta > 0 else self._zoom_out()
        else:
            self.canvas.yview_scroll(-1 * (event.delta // 120), "units")
    
    def _canvas_scroll_linux(self, direction):
        self.canvas.yview_scroll(direction * 3, "units")
    
    # =========================================================================
    # TOOLS
    # =========================================================================
    
    def _set_tool(self, mode: ToolMode):
        self.tool_mode = mode
        for m, btn in self.tool_btns.items():
            btn.set_active(m == mode)
        
        cursors = {
            ToolMode.SELECT: "arrow", ToolMode.PAN: "fleur", ToolMode.TEXT: "xterm",
            ToolMode.STICKY_NOTE: "plus", ToolMode.DRAW: "pencil", ToolMode.CROP: "cross",
        }
        self.canvas.configure(cursor=cursors.get(mode, "cross"))
        
        if mode == ToolMode.IMAGE:
            self._add_image_dialog()
            self._set_tool(ToolMode.SELECT)
        
        self._status(f"Tool: {mode.name.replace('_', ' ').title()}")
    
    def _pick_color(self):
        color = colorchooser.askcolor(color=self._rgb_to_hex(self.draw_color))
        if color[0]:
            self.draw_color = tuple(int(c) for c in color[0])
    
    def _rgb_to_hex(self, rgb):
        return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"
    
    def _canvas_to_pdf(self, cx, cy):
        if not hasattr(self, 'img_offset_x'):
            return 0, 0
        return (cx - self.img_offset_x) / self.zoom, (cy - self.img_offset_y) / self.zoom
    
    def _canvas_click(self, event):
        if not self.doc:
            return
        
        cx = self.canvas.canvasx(event.x)
        cy = self.canvas.canvasy(event.y)
        self.drag_start = (cx, cy)
        self.draw_points = [(cx, cy)]
        
        px, py = self._canvas_to_pdf(cx, cy)
        
        if self.tool_mode == ToolMode.TEXT:
            self._add_text_dialog(px, py)
        elif self.tool_mode == ToolMode.STICKY_NOTE:
            self._add_comment_dialog(px, py)
        elif self.tool_mode == ToolMode.STAMP and self.selected_stamp:
            self.doc.add_stamp(self.current_page, px, py, self.selected_stamp)
            self._render_page()
            self._status(f"Stamp placed")
        elif self.tool_mode == ToolMode.PAN:
            self._pan_start = (cx, cy)
    
    def _canvas_drag(self, event):
        if not self.doc or not self.drag_start:
            return
        
        cx = self.canvas.canvasx(event.x)
        cy = self.canvas.canvasy(event.y)
        
        if self.tool_mode == ToolMode.PAN:
            dx = cx - self.drag_start[0]
            dy = cy - self.drag_start[1]
            self.canvas.xview_scroll(int(-dx/10), "units")
            self.canvas.yview_scroll(int(-dy/10), "units")
        elif self.tool_mode == ToolMode.DRAW:
            self.draw_points.append((cx, cy))
            if len(self.draw_points) >= 2:
                self.canvas.create_line(self.draw_points[-2][0], self.draw_points[-2][1],
                                       cx, cy, fill=self._rgb_to_hex(self.draw_color),
                                       width=2, tags="temp")
        elif self.tool_mode in (ToolMode.RECTANGLE, ToolMode.CIRCLE, ToolMode.HIGHLIGHT,
                               ToolMode.UNDERLINE, ToolMode.STRIKETHROUGH, ToolMode.REDACT,
                               ToolMode.ARROW, ToolMode.CROP):
            self.canvas.delete("temp")
            x1, y1 = self.drag_start
            color = self._rgb_to_hex(self.draw_color)
            
            if self.tool_mode == ToolMode.RECTANGLE:
                self.canvas.create_rectangle(x1, y1, cx, cy, outline=color, width=2, tags="temp")
            elif self.tool_mode == ToolMode.CIRCLE:
                self.canvas.create_oval(x1, y1, cx, cy, outline=color, width=2, tags="temp")
            elif self.tool_mode == ToolMode.ARROW:
                self.canvas.create_line(x1, y1, cx, cy, fill=color, width=2, arrow=tk.LAST, tags="temp")
            elif self.tool_mode in (ToolMode.HIGHLIGHT, ToolMode.UNDERLINE, ToolMode.STRIKETHROUGH):
                self.canvas.create_rectangle(x1, y1, cx, cy, fill="#ffff00", stipple="gray50",
                                           outline="", tags="temp")
            elif self.tool_mode == ToolMode.REDACT:
                self.canvas.create_rectangle(x1, y1, cx, cy, fill="black", outline="", tags="temp")
            elif self.tool_mode == ToolMode.CROP:
                self.canvas.create_rectangle(x1, y1, cx, cy, outline=Theme.ACCENT, width=2,
                                           dash=(4, 4), tags="temp")
    
    def _canvas_release(self, event):
        if not self.doc or not self.drag_start:
            return
        
        cx = self.canvas.canvasx(event.x)
        cy = self.canvas.canvasy(event.y)
        
        x1, y1 = self._canvas_to_pdf(*self.drag_start)
        x2, y2 = self._canvas_to_pdf(cx, cy)
        rect = (min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2))
        
        color = tuple(c/255 for c in self.draw_color)
        self.canvas.delete("temp")
        
        if self.tool_mode == ToolMode.DRAW and len(self.draw_points) >= 2:
            pts = [self._canvas_to_pdf(p[0], p[1]) for p in self.draw_points]
            self.doc.add_freehand(self.current_page, pts, color)
            self._render_page()
        elif self.tool_mode == ToolMode.RECTANGLE:
            self.doc.add_rect(self.current_page, rect, color)
            self._render_page()
        elif self.tool_mode == ToolMode.CIRCLE:
            self.doc.add_circle(self.current_page, rect, color)
            self._render_page()
        elif self.tool_mode == ToolMode.ARROW:
            self.doc.add_arrow(self.current_page, (x1, y1), (x2, y2), color)
            self._render_page()
        elif self.tool_mode == ToolMode.HIGHLIGHT:
            self.doc.add_highlight(self.current_page, rect)
            self._render_page()
        elif self.tool_mode == ToolMode.UNDERLINE:
            self.doc.add_underline(self.current_page, rect)
            self._render_page()
        elif self.tool_mode == ToolMode.STRIKETHROUGH:
            self.doc.add_strikethrough(self.current_page, rect)
            self._render_page()
        elif self.tool_mode == ToolMode.REDACT:
            if messagebox.askyesno("Redact", "Permanently black out this area?"):
                self.doc.redact_area(self.current_page, rect)
                self._render_page()
        elif self.tool_mode == ToolMode.CROP:
            if messagebox.askyesno("Crop", "Crop page to selected area?"):
                self.doc.crop_page(self.current_page, rect)
                self._refresh_all()
        
        self.drag_start = None
        self.draw_points = []
        self._update_ui()
    
    def _canvas_context(self, event):
        if not self.doc:
            return
        menu = tk.Menu(self, tearoff=0, bg=Theme.BG_TERTIARY, fg=Theme.FG_PRIMARY)
        menu.add_command(label="Add Text Here", command=lambda: self._add_text_dialog(
            *self._canvas_to_pdf(self.canvas.canvasx(event.x), self.canvas.canvasy(event.y))))
        menu.add_command(label="Add Comment Here", command=lambda: self._add_comment_dialog(
            *self._canvas_to_pdf(self.canvas.canvasx(event.x), self.canvas.canvasy(event.y))))
        menu.add_separator()
        menu.add_command(label="Copy Page Text", command=self._copy_page_text)
        menu.tk_popup(event.x_root, event.y_root)
    
    # =========================================================================
    # DIALOGS
    # =========================================================================
    
    def _add_text_dialog(self, x: float, y: float):
        dialog = tk.Toplevel(self)
        dialog.title("Add Text")
        dialog.geometry("400x200")
        dialog.configure(bg=Theme.BG_SECONDARY)
        dialog.transient(self)
        dialog.grab_set()
        
        tk.Label(dialog, text="Enter text:", bg=Theme.BG_SECONDARY, 
                fg=Theme.FG_PRIMARY).pack(pady=10)
        
        text_box = tk.Text(dialog, height=4, width=40, bg=Theme.BG_INPUT, 
                          fg=Theme.FG_PRIMARY, insertbackground=Theme.FG_PRIMARY)
        text_box.pack(pady=5, padx=20)
        text_box.focus_set()
        
        size_frame = tk.Frame(dialog, bg=Theme.BG_SECONDARY)
        size_frame.pack(pady=5)
        tk.Label(size_frame, text="Size:", bg=Theme.BG_SECONDARY, fg=Theme.FG_PRIMARY).pack(side=tk.LEFT)
        size_var = tk.StringVar(value="12")
        tk.Spinbox(size_frame, from_=6, to=72, textvariable=size_var, width=5,
                  bg=Theme.BG_INPUT, fg=Theme.FG_PRIMARY).pack(side=tk.LEFT, padx=5)
        
        def add():
            text = text_box.get("1.0", tk.END).strip()
            if text:
                self.doc.add_text(self.current_page, text, x, y, 
                                 int(size_var.get()), self.draw_color)
                self._render_page()
            dialog.destroy()
        
        btn_frame = tk.Frame(dialog, bg=Theme.BG_SECONDARY)
        btn_frame.pack(pady=10)
        tk.Button(btn_frame, text="Add", command=add, bg=Theme.ACCENT, 
                 fg=Theme.FG_PRIMARY, relief=tk.FLAT, padx=20).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Cancel", command=dialog.destroy, bg=Theme.BG_HOVER,
                 fg=Theme.FG_PRIMARY, relief=tk.FLAT, padx=20).pack(side=tk.LEFT)
    
    def _add_comment_dialog(self, x: float, y: float):
        dialog = tk.Toplevel(self)
        dialog.title("Add Comment")
        dialog.geometry("350x180")
        dialog.configure(bg=Theme.BG_SECONDARY)
        dialog.transient(self)
        dialog.grab_set()
        
        tk.Label(dialog, text="Comment:", bg=Theme.BG_SECONDARY, 
                fg=Theme.FG_PRIMARY).pack(pady=10)
        
        text_box = tk.Text(dialog, height=4, width=35, bg=Theme.BG_INPUT,
                          fg=Theme.FG_PRIMARY, insertbackground=Theme.FG_PRIMARY)
        text_box.pack(pady=5, padx=20)
        text_box.focus_set()
        
        def add():
            text = text_box.get("1.0", tk.END).strip()
            if text:
                self.doc.add_comment(self.current_page, x, y, text)
                self._render_page()
                self._refresh_comments()
            dialog.destroy()
        
        btn_frame = tk.Frame(dialog, bg=Theme.BG_SECONDARY)
        btn_frame.pack(pady=10)
        tk.Button(btn_frame, text="Add", command=add, bg=Theme.ACCENT,
                 fg=Theme.FG_PRIMARY, relief=tk.FLAT, padx=20).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Cancel", command=dialog.destroy, bg=Theme.BG_HOVER,
                 fg=Theme.FG_PRIMARY, relief=tk.FLAT, padx=20).pack(side=tk.LEFT)
    
    def _add_image_dialog(self):
        if not self.doc:
            return
        filepath = filedialog.askopenfilename(
            filetypes=[("Images", "*.png *.jpg *.jpeg *.gif *.bmp"), ("All", "*.*")])
        if filepath:
            pw, ph = self.doc.get_page_size(self.current_page)
            if self.doc.add_image(self.current_page, filepath, pw/4, ph/4):
                self._render_page()
                self._status("Image added")
    
    # =========================================================================
    # PAGE OPERATIONS
    # =========================================================================
    
    def _insert_page(self, index: int):
        if self.doc:
            self.doc.insert_page(index)
            self._refresh_all()
    
    def _delete_page(self, page_num: int = None):
        if not self.doc:
            return
        p = page_num if page_num is not None else self.current_page
        if self.doc.page_count <= 1:
            messagebox.showwarning("Warning", "Cannot delete the only page.")
            return
        if messagebox.askyesno("Delete", f"Delete page {p + 1}?"):
            self.doc.delete_page(p)
            if self.current_page >= self.doc.page_count:
                self.current_page = self.doc.page_count - 1
            self._refresh_all()
    
    def _rotate(self, page_num: int, angle: int):
        if self.doc:
            self.doc.rotate_page(page_num, angle)
            self._refresh_all()
    
    def _extract_page(self, page_num: int):
        if not self.doc:
            return
        filepath = filedialog.asksaveasfilename(
            defaultextension=".pdf", initialname=f"page_{page_num+1}.pdf",
            filetypes=[("PDF", "*.pdf")])
        if filepath:
            new_doc = fitz.open()
            new_doc.insert_pdf(self.doc.doc, from_page=page_num, to_page=page_num)
            new_doc.save(filepath)
            new_doc.close()
            self._status(f"Extracted page {page_num + 1}")
    
    # =========================================================================
    # SEARCH
    # =========================================================================
    
    def _show_search(self):
        self.search_bar.pack(fill=tk.X, before=self.main)
        self.search_bar.focus_entry()
    
    def _hide_search(self):
        self.search_bar.pack_forget()
        self.search_highlights = []
        self._render_page()
    
    def _do_search(self, query: str) -> List[SearchResult]:
        if not self.doc:
            return []
        results = self.doc.search_text(query)
        self.search_highlights = results
        
        if results:
            # Go to first result
            self.current_page = results[0].page
            self._render_page()
            self._update_ui()
        
        return results
    
    # =========================================================================
    # UNDO/REDO
    # =========================================================================
    
    def _undo(self):
        if self.doc and self.doc.can_undo():
            # Basic implementation - would need more work for full undo
            self._status("Undo - reloading document")
    
    def _redo(self):
        if self.doc and self.doc.can_redo():
            self._status("Redo")
    
    # =========================================================================
    # DOCUMENT OPERATIONS
    # =========================================================================
    
    def _copy_page_text(self):
        if self.doc:
            text = self.doc.get_text(self.current_page)
            self.clipboard_clear()
            self.clipboard_append(text)
            self._status("Text copied")
    
    # =========================================================================
    # MENU COMMANDS (would be connected to menu)
    # =========================================================================
    
    def _merge_pdfs(self):
        files = filedialog.askopenfilenames(filetypes=[("PDF", "*.pdf")])
        if not files:
            return
        output = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF", "*.pdf")])
        if not output:
            return
        
        merged = fitz.open()
        for f in files:
            doc = fitz.open(f)
            merged.insert_pdf(doc)
            doc.close()
        merged.save(output)
        merged.close()
        
        if messagebox.askyesno("Done", "Open merged PDF?"):
            self._open_doc(output)
    
    def _compress_pdf(self):
        if not self.doc:
            return
        output = filedialog.asksaveasfilename(defaultextension=".pdf",
                                              initialname=f"compressed_{self.doc.filename}",
                                              filetypes=[("PDF", "*.pdf")])
        if output:
            if self.doc.compress(output):
                orig_size = os.path.getsize(self.doc.filepath) if self.doc.filepath else 0
                new_size = os.path.getsize(output)
                savings = (1 - new_size / orig_size) * 100 if orig_size else 0
                messagebox.showinfo("Compressed", f"Saved {savings:.1f}% ({new_size // 1024} KB)")
    
    def _ocr_document(self):
        if not self.doc:
            return
        
        ok, msg = OCREngine.is_available()
        if not ok:
            messagebox.showerror("OCR Unavailable", msg)
            return
        
        if not messagebox.askyesno("OCR", "Make document searchable with OCR?\nThis may take a while."):
            return
        
        progress = tk.Toplevel(self)
        progress.title("OCR")
        progress.geometry("300x80")
        progress.configure(bg=Theme.BG_SECONDARY)
        progress.transient(self)
        
        label = tk.Label(progress, text="Processing...", bg=Theme.BG_SECONDARY, fg=Theme.FG_PRIMARY)
        label.pack(pady=25)
        
        def run():
            ok, count = OCREngine.make_searchable(
                self.doc, callback=lambda m: self.after(0, lambda: label.configure(text=m)))
            self.after(0, lambda: self._ocr_done(ok, count, progress))
        
        threading.Thread(target=run).start()
    
    def _ocr_done(self, ok: bool, count: int, dialog):
        dialog.destroy()
        if ok:
            self._render_page()
            messagebox.showinfo("OCR Complete", f"Processed {count} pages.\nDocument is now searchable.")
        else:
            messagebox.showerror("OCR Failed", "OCR processing failed.")
    
    # =========================================================================
    # WATERMARK, HEADERS, BATES
    # =========================================================================
    
    def _watermark_dialog(self):
        if not self.doc:
            return
        dialog = tk.Toplevel(self)
        dialog.title("Add Watermark")
        dialog.geometry("380x280")
        dialog.configure(bg=Theme.BG_SECONDARY)
        dialog.transient(self)
        dialog.grab_set()
        
        tk.Label(dialog, text="Watermark Text:", bg=Theme.BG_SECONDARY, fg=Theme.FG_PRIMARY).pack(pady=(20, 5))
        text_entry = tk.Entry(dialog, width=30, bg=Theme.BG_INPUT, fg=Theme.FG_PRIMARY, relief=tk.FLAT)
        text_entry.pack(ipady=4)
        text_entry.insert(0, "CONFIDENTIAL")
        
        tk.Label(dialog, text="Font Size:", bg=Theme.BG_SECONDARY, fg=Theme.FG_PRIMARY).pack(pady=(15, 5))
        size_var = tk.StringVar(value="48")
        tk.Spinbox(dialog, from_=12, to=144, textvariable=size_var, width=10, bg=Theme.BG_INPUT, fg=Theme.FG_PRIMARY).pack()
        
        tk.Label(dialog, text="Rotation (degrees):", bg=Theme.BG_SECONDARY, fg=Theme.FG_PRIMARY).pack(pady=(15, 5))
        angle_var = tk.StringVar(value="45")
        tk.Spinbox(dialog, from_=-90, to=90, textvariable=angle_var, width=10, bg=Theme.BG_INPUT, fg=Theme.FG_PRIMARY).pack()
        
        def apply():
            self.doc.add_watermark(text_entry.get(), int(size_var.get()), angle=float(angle_var.get()))
            self._render_page()
            dialog.destroy()
            self._status("Watermark added to all pages")
        
        tk.Button(dialog, text="Apply to All Pages", command=apply, bg=Theme.ACCENT, fg=Theme.FG_PRIMARY, relief=tk.FLAT, padx=20).pack(pady=25)
    
    def _header_footer_dialog(self):
        if not self.doc:
            return
        dialog = tk.Toplevel(self)
        dialog.title("Add Header/Footer")
        dialog.geometry("450x320")
        dialog.configure(bg=Theme.BG_SECONDARY)
        dialog.transient(self)
        dialog.grab_set()
        
        tk.Label(dialog, text="Placeholders: {page}, {pages}, {date}, {filename}", bg=Theme.BG_SECONDARY, fg=Theme.FG_MUTED, font=(Theme.FONT, Theme.FONT_SMALL)).pack(pady=(15, 10))
        
        tk.Label(dialog, text="Header:", bg=Theme.BG_SECONDARY, fg=Theme.FG_PRIMARY).pack(pady=(10, 5))
        header_entry = tk.Entry(dialog, width=45, bg=Theme.BG_INPUT, fg=Theme.FG_PRIMARY, relief=tk.FLAT)
        header_entry.pack(ipady=4)
        
        tk.Label(dialog, text="Footer:", bg=Theme.BG_SECONDARY, fg=Theme.FG_PRIMARY).pack(pady=(15, 5))
        footer_entry = tk.Entry(dialog, width=45, bg=Theme.BG_INPUT, fg=Theme.FG_PRIMARY, relief=tk.FLAT)
        footer_entry.pack(ipady=4)
        footer_entry.insert(0, "Page {page} of {pages}")
        
        tk.Label(dialog, text="Font Size:", bg=Theme.BG_SECONDARY, fg=Theme.FG_PRIMARY).pack(pady=(15, 5))
        size_var = tk.StringVar(value="10")
        tk.Spinbox(dialog, from_=6, to=24, textvariable=size_var, width=10, bg=Theme.BG_INPUT, fg=Theme.FG_PRIMARY).pack()
        
        def apply():
            h = header_entry.get() or None
            f = footer_entry.get() or None
            if h or f:
                self.doc.add_header_footer(h, f, int(size_var.get()))
                self._render_page()
                self._status("Header/footer added")
            dialog.destroy()
        
        tk.Button(dialog, text="Apply", command=apply, bg=Theme.ACCENT, fg=Theme.FG_PRIMARY, relief=tk.FLAT, padx=25).pack(pady=20)
    
    def _bates_dialog(self):
        if not self.doc:
            return
        dialog = tk.Toplevel(self)
        dialog.title("Bates Numbering")
        dialog.geometry("380x350")
        dialog.configure(bg=Theme.BG_SECONDARY)
        dialog.transient(self)
        dialog.grab_set()
        
        tk.Label(dialog, text="Prefix:", bg=Theme.BG_SECONDARY, fg=Theme.FG_PRIMARY).pack(pady=(20, 5))
        prefix_entry = tk.Entry(dialog, width=20, bg=Theme.BG_INPUT, fg=Theme.FG_PRIMARY, relief=tk.FLAT)
        prefix_entry.pack(ipady=3)
        prefix_entry.insert(0, "DOC-")
        
        tk.Label(dialog, text="Start Number:", bg=Theme.BG_SECONDARY, fg=Theme.FG_PRIMARY).pack(pady=(10, 5))
        start_var = tk.StringVar(value="1")
        tk.Spinbox(dialog, from_=1, to=999999, textvariable=start_var, width=10, bg=Theme.BG_INPUT, fg=Theme.FG_PRIMARY).pack()
        
        tk.Label(dialog, text="Digits:", bg=Theme.BG_SECONDARY, fg=Theme.FG_PRIMARY).pack(pady=(10, 5))
        digits_var = tk.StringVar(value="6")
        tk.Spinbox(dialog, from_=3, to=10, textvariable=digits_var, width=10, bg=Theme.BG_INPUT, fg=Theme.FG_PRIMARY).pack()
        
        tk.Label(dialog, text="Position:", bg=Theme.BG_SECONDARY, fg=Theme.FG_PRIMARY).pack(pady=(10, 5))
        pos_var = tk.StringVar(value="bottom-right")
        positions = ["top-left", "top-center", "top-right", "bottom-left", "bottom-center", "bottom-right"]
        ttk.Combobox(dialog, textvariable=pos_var, values=positions, width=15).pack()
        
        def apply():
            self.doc.add_bates_numbers(prefix=prefix_entry.get(), start=int(start_var.get()), digits=int(digits_var.get()), position=pos_var.get())
            self._render_page()
            dialog.destroy()
            self._status("Bates numbers added")
        
        tk.Button(dialog, text="Apply", command=apply, bg=Theme.ACCENT, fg=Theme.FG_PRIMARY, relief=tk.FLAT, padx=25).pack(pady=25)
    
    # =========================================================================
    # STAMPS
    # =========================================================================
    
    def _show_stamp_picker(self):
        if not self.doc:
            return
        dialog = tk.Toplevel(self)
        dialog.title("Select Stamp")
        dialog.geometry("400x320")
        dialog.configure(bg=Theme.BG_SECONDARY)
        dialog.transient(self)
        dialog.grab_set()
        
        tk.Label(dialog, text="Select a Stamp", bg=Theme.BG_SECONDARY, fg=Theme.FG_PRIMARY, font=(Theme.FONT, Theme.FONT_TITLE, "bold")).pack(pady=15)
        
        frame = tk.Frame(dialog, bg=Theme.BG_SECONDARY)
        frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        def select_stamp(stamp):
            self.selected_stamp = stamp
            self._set_tool(ToolMode.STAMP)
            dialog.destroy()
            self._status(f"Stamp selected: {stamp['name']} - Click on page to place")
        
        for i, stamp in enumerate(BUILTIN_STAMPS):
            btn = tk.Button(frame, text=stamp['text'], bg=stamp['bg'], fg=stamp['color'], font=(Theme.FONT, 10, "bold"), relief=tk.FLAT, padx=10, pady=5, command=lambda s=stamp: select_stamp(s))
            btn.grid(row=i//3, column=i%3, padx=5, pady=5, sticky='ew')
        
        for i in range(3):
            frame.columnconfigure(i, weight=1)
        
        tk.Button(dialog, text="Cancel", command=dialog.destroy, bg=Theme.BG_HOVER, fg=Theme.FG_PRIMARY, relief=tk.FLAT, padx=20).pack(pady=15)
    
    # =========================================================================
    # EXPORTS
    # =========================================================================
    
    def _export_to_word(self):
        if not self.doc:
            return
        if not HAS_DOCX:
            messagebox.showerror("Unavailable", "python-docx failed to install.\nTry manually: pip install python-docx\nThen restart the application.")
            return
        output = filedialog.asksaveasfilename(defaultextension=".docx", filetypes=[("Word Document", "*.docx")])
        if output:
            if self.doc.export_to_word(output):
                self._status("Exported to Word")
                messagebox.showinfo("Done", "Document exported to Word format")
            else:
                messagebox.showerror("Error", "Export failed")
    
    def _export_to_images(self):
        if not self.doc:
            return
        dialog = tk.Toplevel(self)
        dialog.title("Export to Images")
        dialog.geometry("320x220")
        dialog.configure(bg=Theme.BG_SECONDARY)
        dialog.transient(self)
        dialog.grab_set()
        
        tk.Label(dialog, text="DPI:", bg=Theme.BG_SECONDARY, fg=Theme.FG_PRIMARY).pack(pady=(20, 5))
        dpi_var = tk.StringVar(value="150")
        tk.Spinbox(dialog, from_=72, to=600, textvariable=dpi_var, width=10, bg=Theme.BG_INPUT, fg=Theme.FG_PRIMARY).pack()
        
        tk.Label(dialog, text="Format:", bg=Theme.BG_SECONDARY, fg=Theme.FG_PRIMARY).pack(pady=(15, 5))
        fmt_var = tk.StringVar(value="png")
        ttk.Combobox(dialog, textvariable=fmt_var, values=["png", "jpg", "jpeg"], width=10).pack()
        
        def export():
            output_dir = filedialog.askdirectory(title="Select output folder")
            if output_dir:
                files = self.doc.export_to_images(output_dir, int(dpi_var.get()), fmt_var.get())
                dialog.destroy()
                messagebox.showinfo("Done", f"Exported {len(files)} images")
        
        tk.Button(dialog, text="Export", command=export, bg=Theme.ACCENT, fg=Theme.FG_PRIMARY, relief=tk.FLAT, padx=25).pack(pady=25)
    
    def _export_text(self):
        if not self.doc:
            return
        output = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text File", "*.txt")])
        if output:
            if self.doc.export_text(output):
                self._status("Text exported")
                messagebox.showinfo("Done", "Text extracted to file")
            else:
                messagebox.showerror("Error", "Export failed")
    
    # =========================================================================
    # DOCUMENT OPERATIONS
    # =========================================================================
    
    def _split_document(self):
        if not self.doc:
            return
        output_dir = filedialog.askdirectory(title="Select output folder for split pages")
        if output_dir:
            files = self.doc.split_pages(output_dir)
            messagebox.showinfo("Done", f"Split into {len(files)} separate PDF files")
    
    def _flatten_annotations(self):
        if self.doc:
            self.doc.flatten_annotations()
            self._render_page()
            self._status("Annotations flattened into page content")
    
    def _remove_metadata(self):
        if self.doc:
            if messagebox.askyesno("Remove Metadata", "Remove all document metadata (author, title, etc.)?"):
                self.doc.remove_metadata()
                self._status("Metadata removed")
    
    def _set_password_dialog(self):
        if not self.doc:
            return
        dialog = tk.Toplevel(self)
        dialog.title("Set Password Protection")
        dialog.geometry("350x200")
        dialog.configure(bg=Theme.BG_SECONDARY)
        dialog.transient(self)
        dialog.grab_set()
        
        tk.Label(dialog, text="Password:", bg=Theme.BG_SECONDARY, fg=Theme.FG_PRIMARY).pack(pady=(20, 5))
        pass_entry = tk.Entry(dialog, show="*", width=25, bg=Theme.BG_INPUT, fg=Theme.FG_PRIMARY, relief=tk.FLAT)
        pass_entry.pack(ipady=4)
        
        tk.Label(dialog, text="Confirm:", bg=Theme.BG_SECONDARY, fg=Theme.FG_PRIMARY).pack(pady=(10, 5))
        confirm_entry = tk.Entry(dialog, show="*", width=25, bg=Theme.BG_INPUT, fg=Theme.FG_PRIMARY, relief=tk.FLAT)
        confirm_entry.pack(ipady=4)
        
        def apply():
            if pass_entry.get() != confirm_entry.get():
                messagebox.showerror("Error", "Passwords don't match")
                return
            output = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF", "*.pdf")])
            if output:
                try:
                    perm = fitz.PDF_PERM_PRINT | fitz.PDF_PERM_COPY
                    self.doc.doc.save(output, encryption=fitz.PDF_ENCRYPT_AES_256, user_pw=pass_entry.get(), permissions=perm)
                    self._status("Password-protected PDF saved")
                    dialog.destroy()
                except Exception as e:
                    messagebox.showerror("Error", str(e))
        
        tk.Button(dialog, text="Save Protected PDF", command=apply, bg=Theme.ACCENT, fg=Theme.FG_PRIMARY, relief=tk.FLAT, padx=20).pack(pady=20)
    
    def _show_properties(self):
        if not self.doc:
            return
        dialog = tk.Toplevel(self)
        dialog.title("Document Properties")
        dialog.geometry("420x380")
        dialog.configure(bg=Theme.BG_SECONDARY)
        dialog.transient(self)
        
        meta = self.doc.get_metadata()
        
        fields = [("Title", meta.get('title', '')), ("Author", meta.get('author', '')), ("Subject", meta.get('subject', '')), ("Keywords", meta.get('keywords', ''))]
        entries = {}
        
        for label, value in fields:
            frame = tk.Frame(dialog, bg=Theme.BG_SECONDARY)
            frame.pack(fill=tk.X, padx=20, pady=5)
            tk.Label(frame, text=label + ":", bg=Theme.BG_SECONDARY, fg=Theme.FG_PRIMARY, width=12, anchor='w').pack(side=tk.LEFT)
            entry = tk.Entry(frame, bg=Theme.BG_INPUT, fg=Theme.FG_PRIMARY, relief=tk.FLAT, width=35)
            entry.pack(side=tk.LEFT, ipady=3)
            entry.insert(0, value or '')
            entries[label.lower()] = entry
        
        tk.Label(dialog, text=f"\nFile: {self.doc.filename}", bg=Theme.BG_SECONDARY, fg=Theme.FG_SECONDARY).pack()
        tk.Label(dialog, text=f"Pages: {self.doc.page_count}", bg=Theme.BG_SECONDARY, fg=Theme.FG_SECONDARY).pack()
        if self.doc.filepath:
            size = os.path.getsize(self.doc.filepath) // 1024
            tk.Label(dialog, text=f"Size: {size} KB", bg=Theme.BG_SECONDARY, fg=Theme.FG_SECONDARY).pack()
        
        def save():
            new_meta = {k: e.get() for k, e in entries.items()}
            self.doc.set_metadata(new_meta)
            dialog.destroy()
            self._status("Properties updated")
        
        tk.Button(dialog, text="Save", command=save, bg=Theme.ACCENT, fg=Theme.FG_PRIMARY, relief=tk.FLAT, padx=25).pack(pady=20)
    
    def _print_doc(self):
        if not self.doc or not self.doc.filepath:
            messagebox.showinfo("Print", "Save the document first, then use your system PDF viewer to print.")
            return
        try:
            if platform.system() == "Windows":
                os.startfile(self.doc.filepath, "print")
            else:
                subprocess.run(["lp", self.doc.filepath])
            self._status("Sent to printer")
        except Exception as e:
            messagebox.showerror("Print Error", str(e))
    
    def _duplicate_page(self):
        if self.doc:
            self.doc.duplicate_page(self.current_page)
            self._refresh_all()
            self._status("Page duplicated")
    
    def _show_shortcuts(self):
        shortcuts = """
Keyboard Shortcuts:

FILE
  Ctrl+N        New document
  Ctrl+O        Open file
  Ctrl+S        Save
  Ctrl+W        Close tab

NAVIGATION
  Home          First page
  End           Last page
  Page Up       Previous page
  Page Down     Next page

VIEW
  Ctrl++        Zoom in
  Ctrl+-        Zoom out
  Ctrl+0        Fit page
  Ctrl+1        100% zoom

TOOLS
  Escape        Select tool
  Delete        Delete page
  Ctrl+F        Find text
"""
        messagebox.showinfo("Keyboard Shortcuts", shortcuts)
    
    def _show_about(self):
        messagebox.showinfo("About PDF Editor Pro", "PDF Editor Pro v3.0\n\nA comprehensive PDF editing suite.\n\nFeatures:\n• Multi-document tabs\n• Search & navigation\n• Annotations & comments\n• Stamps library\n• Watermarks & headers\n• Bates numbering\n• OCR text recognition\n• Export to Word/images\n• Merge, split, compress\n• Password protection\n\n© 2025")
    
    # =========================================================================
    # CLEANUP
    # =========================================================================
    
    def _on_close(self):
        for doc in self.documents.values():
            if doc.is_modified:
                r = messagebox.askyesnocancel("Save?", f"Save changes to {doc.filename}?")
                if r is None:
                    return
                if r:
                    if not doc.filepath:
                        path = filedialog.asksaveasfilename(defaultextension=".pdf")
                        if path:
                            doc.save(path)
                    else:
                        doc.save()
        
        self.config_data["window_geometry"] = self.geometry()
        Config.save(self.config_data)
        
        for doc in self.documents.values():
            doc.close()
        
        self.destroy()

# ============================================================================
# MAIN
# ============================================================================

def main():
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except:
        pass
    
    app = PDFEditorPro()
    app.mainloop()

if __name__ == "__main__":
    main()
