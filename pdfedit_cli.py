#!/usr/bin/env python3
"""Headless PDFedit workflows.

The GUI remains the default application.  This module exposes the same
document engine for repeatable pipelines and server/CI environments:

    python pdfedit_cli.py merge a.pdf b.pdf -o merged.pdf
    python pdfedit_cli.py split input.pdf -o pages
    python pdfedit_cli.py redact input.pdf -o safe.pdf --page 1 --text secret
"""

from __future__ import annotations

import argparse
import json
import os
import runpy
import sys
import time
from pathlib import Path

import fitz

from PDFedit import PDFDocument, OCREngine


def parse_page_range(spec: str, page_count: int) -> list[int]:
    """Parse 1-based page expressions such as ``1-3,7`` into zero-based rows."""
    if not spec or spec.strip().lower() == "all":
        return list(range(page_count))
    pages: list[int] = []
    for part in spec.split(","):
        token = part.strip()
        if not token:
            continue
        if "-" in token:
            start_text, end_text = token.split("-", 1)
            start = int(start_text) if start_text else 1
            end = int(end_text) if end_text else page_count
            if start > end:
                start, end = end, start
            values = range(start, end + 1)
        else:
            values = [int(token)]
        for page in values:
            if page < 1 or page > page_count:
                raise ValueError(f"page {page} is outside 1-{page_count}")
            if page - 1 not in pages:
                pages.append(page - 1)
    if not pages:
        raise ValueError("page range did not contain any pages")
    return pages


def open_document(path: str) -> PDFDocument:
    document = PDFDocument()
    if not document.open(path):
        raise RuntimeError(document.last_error or f"unable to open {path}")
    return document


def save_or_raise(document: PDFDocument, output: str) -> None:
    if not document.save(output):
        raise RuntimeError(document.last_error or f"unable to save {output}")


def command_merge(args: argparse.Namespace) -> int:
    result = fitz.open()
    try:
        for input_path in args.inputs:
            source = fitz.open(input_path)
            try:
                result.insert_pdf(source)
            finally:
                source.close()
        result.save(args.output, garbage=4, deflate=True, clean=True)
        return 0
    finally:
        result.close()


def command_split(args: argparse.Namespace) -> int:
    document = open_document(args.input)
    try:
        pages = parse_page_range(args.pages, document.page_count) if args.pages else None
        os.makedirs(args.output, exist_ok=True)
        files = document.split_pages(args.output, pages, prefix=args.prefix)
        if not files:
            raise RuntimeError(document.last_error or "no pages were written")
        for path in files:
            print(path)
        return 0
    finally:
        document.close()


def command_extract(args: argparse.Namespace) -> int:
    document = open_document(args.input)
    try:
        pages = parse_page_range(args.pages, document.page_count)
        extracted = document.extract_pages(pages, args.output)
        if extracted is None:
            raise RuntimeError(document.last_error or "unable to extract pages")
        extracted.close()
        return 0
    finally:
        document.close()


def command_ocr(args: argparse.Namespace) -> int:
    document = open_document(args.input)
    try:
        available, reason = OCREngine.is_available()
        if not available:
            raise RuntimeError(reason)

        def progress(message, percent):
            print(f"{percent:3d}% {message}", file=sys.stderr)

        success, count = OCREngine.make_searchable(document, callback=progress)
        if not success and not count:
            raise RuntimeError(document.last_error or "OCR did not produce searchable text")
        save_or_raise(document, args.output)
        print(f"OCR processed {count} page(s)")
        return 0
    finally:
        document.close()


def command_redact(args: argparse.Namespace) -> int:
    document = open_document(args.input)
    try:
        pages = parse_page_range(args.pages, document.page_count) if args.pages else [args.page - 1]
        if any(page < 0 or page >= document.page_count for page in pages):
            raise ValueError(f"page is outside 1-{document.page_count}")
        count = 0
        if args.rect:
            if len(args.rect) != 4:
                raise ValueError("--rect requires x0 y0 x1 y1")
            for page in pages:
                count += int(document.redact_area(page, args.rect))
        if args.text:
            for page in pages:
                count += document.redact_text(page, args.text)
        if not count:
            raise RuntimeError("no redaction target matched")
        save_or_raise(document, args.output)
        print(f"Applied {count} redaction(s)")
        return 0
    finally:
        document.close()


def command_watermark(args: argparse.Namespace) -> int:
    document = open_document(args.input)
    try:
        pages = parse_page_range(args.pages, document.page_count) if args.pages else None
        if not document.add_watermark(text=args.text, image_path=args.image,
                                      pages=pages, font_size=args.font_size,
                                      angle=args.angle, opacity=args.opacity,
                                      scale=args.scale):
            raise RuntimeError(document.last_error or "unable to add watermark")
        save_or_raise(document, args.output)
        return 0
    finally:
        document.close()


def command_header_footer(args: argparse.Namespace) -> int:
    document = open_document(args.input)
    try:
        document.add_header_footer(args.header, args.footer,
                                   font_size=args.font_size, margin=args.margin)
        save_or_raise(document, args.output)
        return 0
    finally:
        document.close()


def command_compare(args: argparse.Namespace) -> int:
    document = open_document(args.input)
    try:
        comparison = document.compare(args.other)
        summary = {
            "changed_pages": [page + 1 for page in comparison.get("changed_pages", [])],
            "added_pages": comparison.get("added_pages", 0),
            "removed_pages": comparison.get("removed_pages", 0),
            "pages": [
                {
                    "page": item["page"] + 1,
                    "text_changed": item["text_changed"],
                    "image_changed": item["image_changed"],
                }
                for item in comparison.get("pages", [])
            ],
        }
        print(json.dumps(summary, indent=2))
        if args.output:
            if not document.create_comparison_pdf(args.other, args.output):
                raise RuntimeError(document.last_error or "unable to create comparison PDF")
        return 0
    finally:
        document.close()


def command_compress(args: argparse.Namespace) -> int:
    document = open_document(args.input)
    try:
        if not document.compress(args.output):
            raise RuntimeError(document.last_error or "unable to compress PDF")
        return 0
    finally:
        document.close()


def command_protect(args: argparse.Namespace) -> int:
    document = open_document(args.input)
    try:
        if not document.protect(args.output, args.user_password, args.owner_password):
            raise RuntimeError(document.last_error or "unable to encrypt PDF")
        return 0
    finally:
        document.close()


def command_sign(args: argparse.Namespace) -> int:
    document = open_document(args.input)
    try:
        if not document.sign(args.output, args.pkcs12, args.password,
                             field_name=args.field, page_num=args.page - 1,
                             rect=args.rect, reason=args.reason,
                             location=args.location):
            raise RuntimeError(document.last_error or "unable to sign PDF")
        return 0
    finally:
        document.close()


def command_repair(args: argparse.Namespace) -> int:
    success, reason = PDFDocument.repair_file(args.input, args.output)
    if not success:
        raise RuntimeError(reason or "unable to repair PDF")
    return 0


def command_attachments(args: argparse.Namespace) -> int:
    document = open_document(args.input)
    try:
        if args.attachment_command == "list":
            print(json.dumps(document.list_attachments(), indent=2))
        elif args.attachment_command == "add":
            if not document.add_attachment(args.file, args.name, args.description):
                raise RuntimeError(document.last_error or "unable to add attachment")
            save_or_raise(document, args.output)
        elif args.attachment_command == "extract":
            if not document.extract_attachment(args.name, args.output):
                raise RuntimeError(document.last_error or "unable to extract attachment")
        elif args.attachment_command == "remove":
            if not document.remove_attachment(args.name):
                raise RuntimeError(document.last_error or "attachment not found")
            save_or_raise(document, args.output)
        return 0
    finally:
        document.close()


def run_recipe(recipe_path: str, input_path: str, output_path: str) -> None:
    document = open_document(input_path)
    try:
        namespace = runpy.run_path(recipe_path)
        callback = namespace.get("process") or namespace.get("main")
        if callback:
            callback(document)
        else:
            actions = namespace.get("actions", [])
            for action in actions:
                if not isinstance(action, dict) or "operation" not in action:
                    raise ValueError("each recipe action needs an operation")
                operation = action["operation"]
                kwargs = {key: value for key, value in action.items() if key != "operation"}
                method = getattr(document, operation, None)
                if not method:
                    raise ValueError(f"unknown recipe operation: {operation}")
                method(**kwargs)
        save_or_raise(document, output_path)
    finally:
        document.close()


def command_script(args: argparse.Namespace) -> int:
    run_recipe(args.recipe, args.input, args.output)
    return 0


def command_watch(args: argparse.Namespace) -> int:
    try:
        from watchdog.events import FileSystemEventHandler
        from watchdog.observers import Observer
    except ImportError as exc:
        raise RuntimeError("watch mode requires watchdog") from exc

    input_dir = os.path.abspath(args.input_dir)
    output_dir = os.path.abspath(args.output_dir)
    os.makedirs(output_dir, exist_ok=True)
    processed: dict[str, float] = {}

    def process(path: str) -> None:
        if not path.lower().endswith(".pdf") or not os.path.isfile(path):
            return
        timestamp = os.path.getmtime(path)
        if processed.get(path) == timestamp:
            return
        output = os.path.join(output_dir, os.path.basename(path))
        try:
            run_recipe(args.recipe, path, output)
            processed[path] = timestamp
            print(f"Processed {path} -> {output}")
        except Exception as exc:
            print(f"Failed to process {path}: {exc}", file=sys.stderr)

    class Handler(FileSystemEventHandler):
        def on_created(self, event):
            if not event.is_directory:
                process(event.src_path)

        def on_modified(self, event):
            if not event.is_directory:
                process(event.src_path)

    for path in Path(input_dir).glob("*.pdf"):
        if args.process_existing:
            process(str(path))
    observer = Observer()
    observer.schedule(Handler(), input_dir, recursive=False)
    observer.start()
    print(f"Watching {input_dir}; press Ctrl+C to stop")
    try:
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pdfedit", description="Headless PDFedit workflows")
    subparsers = parser.add_subparsers(dest="command", required=True)

    merge = subparsers.add_parser("merge", help="combine PDFs in order")
    merge.add_argument("inputs", nargs="+", metavar="PDF")
    merge.add_argument("-o", "--output", required=True)
    merge.set_defaults(handler=command_merge)

    split = subparsers.add_parser("split", help="write one PDF per selected page")
    split.add_argument("input")
    split.add_argument("-o", "--output", required=True)
    split.add_argument("--pages", help="1-based range, e.g. 1-3,7")
    split.add_argument("--prefix", default="page")
    split.set_defaults(handler=command_split)

    extract = subparsers.add_parser("extract", help="extract selected pages to a new PDF")
    extract.add_argument("input")
    extract.add_argument("-o", "--output", required=True)
    extract.add_argument("--pages", required=True)
    extract.set_defaults(handler=command_extract)

    ocr = subparsers.add_parser("ocr", help="make a scanned PDF searchable")
    ocr.add_argument("input")
    ocr.add_argument("-o", "--output", required=True)
    ocr.set_defaults(handler=command_ocr)

    redact = subparsers.add_parser("redact", help="irreversibly remove text or a rectangle")
    redact.add_argument("input")
    redact.add_argument("-o", "--output", required=True)
    redact.add_argument("--page", type=int, default=1)
    redact.add_argument("--pages")
    redact.add_argument("--text")
    redact.add_argument("--rect", nargs=4, type=float, metavar=("X0", "Y0", "X1", "Y1"))
    redact.set_defaults(handler=command_redact)

    watermark = subparsers.add_parser("watermark", help="apply text or image watermark")
    watermark.add_argument("input")
    watermark.add_argument("-o", "--output", required=True)
    group = watermark.add_mutually_exclusive_group(required=True)
    group.add_argument("--text")
    group.add_argument("--image")
    watermark.add_argument("--pages")
    watermark.add_argument("--font-size", type=float, default=48)
    watermark.add_argument("--angle", type=float, default=45)
    watermark.add_argument("--opacity", type=float, default=0.28)
    watermark.add_argument("--scale", type=float, default=0.6)
    watermark.set_defaults(handler=command_watermark)

    header_footer = subparsers.add_parser("header-footer", help="apply tokenized header/footer text")
    header_footer.add_argument("input")
    header_footer.add_argument("-o", "--output", required=True)
    header_footer.add_argument("--header")
    header_footer.add_argument("--footer")
    header_footer.add_argument("--font-size", type=float, default=10)
    header_footer.add_argument("--margin", type=float, default=36)
    header_footer.set_defaults(handler=command_header_footer)

    compare = subparsers.add_parser("compare", help="report or render side-by-side differences")
    compare.add_argument("input")
    compare.add_argument("other")
    compare.add_argument("-o", "--output", help="optional comparison PDF")
    compare.set_defaults(handler=command_compare)

    for name, handler, help_text in [
        ("compress", command_compress, "rewrite a PDF with compression"),
        ("protect", command_protect, "write an AES-encrypted PDF"),
        ("repair", command_repair, "rewrite a damaged-but-readable PDF"),
    ]:
        command = subparsers.add_parser(name, help=help_text)
        command.add_argument("input")
        command.add_argument("-o", "--output", required=True)
        command.set_defaults(handler=handler)
    protect = subparsers.choices["protect"]
    protect.add_argument("--user-password", required=True)
    protect.add_argument("--owner-password")

    sign = subparsers.add_parser("sign", help="apply a visible PKCS#12 signature")
    sign.add_argument("input")
    sign.add_argument("-o", "--output", required=True)
    sign.add_argument("--pkcs12", required=True)
    sign.add_argument("--password", required=True)
    sign.add_argument("--field", default="Signature")
    sign.add_argument("--page", type=int, default=1)
    sign.add_argument("--rect", nargs=4, type=int, default=(36, 36, 220, 96))
    sign.add_argument("--reason")
    sign.add_argument("--location")
    sign.set_defaults(handler=command_sign)

    attachments = subparsers.add_parser("attachments", help="manage embedded files")
    attachments.add_argument("input")
    attachment_sub = attachments.add_subparsers(dest="attachment_command", required=True)
    attachment_list = attachment_sub.add_parser("list")
    attachment_list.set_defaults(handler=command_attachments)
    attachment_add = attachment_sub.add_parser("add")
    attachment_add.add_argument("file")
    attachment_add.add_argument("-o", "--output", required=True)
    attachment_add.add_argument("--name")
    attachment_add.add_argument("--description", default="")
    attachment_add.set_defaults(handler=command_attachments)
    attachment_extract = attachment_sub.add_parser("extract")
    attachment_extract.add_argument("name")
    attachment_extract.add_argument("-o", "--output", required=True)
    attachment_extract.set_defaults(handler=command_attachments)
    attachment_remove = attachment_sub.add_parser("remove")
    attachment_remove.add_argument("name")
    attachment_remove.add_argument("-o", "--output", required=True)
    attachment_remove.set_defaults(handler=command_attachments)

    script = subparsers.add_parser("script", help="run a Python recipe against one PDF")
    script.add_argument("recipe")
    script.add_argument("input")
    script.add_argument("-o", "--output", required=True)
    script.set_defaults(handler=command_script)

    watch = subparsers.add_parser("watch", help="process PDFs dropped into a folder")
    watch.add_argument("input_dir")
    watch.add_argument("recipe")
    watch.add_argument("-o", "--output-dir", required=True)
    watch.add_argument("--process-existing", action="store_true")
    watch.set_defaults(handler=command_watch)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.handler(args)
    except (OSError, ValueError, RuntimeError) as exc:
        parser.error(str(exc))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
