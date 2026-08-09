import fitz
from pypdf import PdfReader, PdfWriter
from PIL import Image

from PDFedit import PDFDocument


def make_pdf(path, page_texts):
    doc = fitz.open()
    for text in page_texts:
        page = doc.new_page(width=300, height=200)
        page.insert_text((30, 60), text, fontsize=14)
    doc.set_toc([[1, "First", 1], [1, "Second", 2]] if len(page_texts) > 1 else [])
    doc.save(path)
    doc.close()


def test_extract_pages_retargets_outline(tmp_path):
    source = tmp_path / "source.pdf"
    make_pdf(source, ["one", "two", "three"])
    document = PDFDocument()
    assert document.open(str(source))

    extracted = document.extract_pages([2, 0])

    assert extracted is not None
    assert extracted.page_count == 2
    assert extracted.get_text(0).strip() == "three"
    assert extracted.get_text(1).strip() == "one"
    assert extracted.get_bookmarks() == [(1, "First", 1)]
    extracted.close()
    document.close()


def test_extract_pages_retargets_named_destinations(tmp_path):
    source = tmp_path / "named-source.pdf"
    make_pdf(source, ["one", "two", "three"])
    reader = PdfReader(str(source))
    writer = PdfWriter()
    writer.clone_document_from_reader(reader)
    writer.add_named_destination("third-page", 2)
    with source.open("wb") as handle:
        writer.write(handle)

    document = PDFDocument()
    assert document.open(str(source))
    assert document.get_named_destinations() == {"third-page": 2}
    extracted = document.extract_pages([2, 0])
    assert extracted is not None
    assert extracted.get_named_destinations() == {"third-page": 0}
    extracted.close()
    document.close()


def test_move_pages_preserves_group_order_and_bookmarks(tmp_path):
    source = tmp_path / "source.pdf"
    make_pdf(source, ["one", "two", "three"])
    document = PDFDocument()
    assert document.open(str(source))

    assert document.move_pages([2], 0)

    assert [document.get_text(i).strip() for i in range(3)] == ["three", "one", "two"]
    assert document.get_bookmarks() == [(1, "First", 1), (1, "Second", 2)]
    document.close()


def test_redaction_forces_full_save_and_removes_text(tmp_path):
    source = tmp_path / "source.pdf"
    make_pdf(source, ["keep secret"])
    document = PDFDocument()
    assert document.open(str(source))

    assert document.redact_text(0, "secret") == 1
    assert document.requires_full_save
    assert document.save()
    assert not document.requires_full_save
    document.close()

    reopened = PDFDocument()
    assert reopened.open(str(source))
    assert "secret" not in reopened.get_text(0)
    assert "keep" in reopened.get_text(0)
    reopened.close()


def test_forms_attachments_markdown_and_compare(tmp_path):
    source = tmp_path / "source.pdf"
    changed = tmp_path / "changed.pdf"
    attachment = tmp_path / "note.txt"
    markdown = tmp_path / "export.md"
    attachment.write_text("attached", encoding="utf-8")
    make_pdf(source, ["original"])
    make_pdf(changed, ["changed"])

    document = PDFDocument()
    assert document.open(str(source))
    assert document.add_form_field(0, "name", (20, 90, 180, 115))
    assert document.set_form_field(0, "name", "Ada")
    assert document.add_attachment(str(attachment), description="Test file")
    assert document.list_attachments()[0]["name"] == "note.txt"
    assert document.export_markdown(str(markdown))
    assert "# source.pdf" in markdown.read_text(encoding="utf-8")
    comparison = document.compare(str(changed))
    assert comparison["changed_pages"] == [0]
    document.close()


def test_font_aware_edit_watermark_and_pressure_stroke(tmp_path):
    source = tmp_path / "source.pdf"
    output = tmp_path / "output.pdf"
    watermark = tmp_path / "watermark.png"
    make_pdf(source, ["old text"])
    Image.new("RGBA", (20, 20), (255, 0, 0, 128)).save(watermark)

    document = PDFDocument()
    assert document.open(str(source))
    block = document.get_text_blocks(0)[0]
    assert document.edit_text(0, block.rect, block.text, "new text",
                              font_size=block.font_size, color=block.color,
                              font_name=block.font_name)
    assert document.add_watermark(image_path=str(watermark), opacity=0.5, pages=[0])
    document.add_freehand(0, [(20, 120, 0.2), (40, 125, 1.5), (70, 120, 0.8)])
    assert document.save(str(output))
    document.close()

    reopened = PDFDocument()
    assert reopened.open(str(output))
    assert "new text" in reopened.get_text(0)
    assert "old text" not in reopened.get_text(0)
    reopened.close()


def test_compression_protection_and_font_report(tmp_path):
    source = tmp_path / "source.pdf"
    compressed = tmp_path / "compressed.pdf"
    protected = tmp_path / "protected.pdf"
    make_pdf(source, ["protected"])
    document = PDFDocument()
    assert document.open(str(source))
    assert document.font_report()
    assert document.compress(str(compressed), preset="web")
    assert document.protect(str(protected), "secret")
    document.close()

    encrypted = fitz.open(str(protected))
    assert encrypted.needs_pass
    assert encrypted.authenticate("secret")
    encrypted.close()
