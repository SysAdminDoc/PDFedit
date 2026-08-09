import fitz

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
