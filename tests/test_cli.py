import fitz

from pdfedit_cli import main, parse_page_range


def make_pdf(path, texts):
    document = fitz.open()
    for text in texts:
        page = document.new_page(width=300, height=200)
        page.insert_text((30, 60), text, fontsize=14)
    document.save(path)
    document.close()


def test_parse_page_range_supports_ranges_and_open_ends():
    assert parse_page_range("1-3,5", 5) == [0, 1, 2, 4]
    assert parse_page_range("2-", 4) == [1, 2, 3]


def test_cli_merge_extract_and_redact(tmp_path):
    first = tmp_path / "first.pdf"
    second = tmp_path / "second.pdf"
    merged = tmp_path / "merged.pdf"
    extracted = tmp_path / "extracted.pdf"
    redacted = tmp_path / "redacted.pdf"
    make_pdf(first, ["keep secret"])
    make_pdf(second, ["second"])

    assert main(["merge", str(first), str(second), "-o", str(merged)]) == 0
    assert main(["extract", str(merged), "-o", str(extracted), "--pages", "2,1"]) == 0
    assert main(["redact", str(merged), "-o", str(redacted), "--page", "1", "--text", "secret"]) == 0

    document = fitz.open(extracted)
    assert [page.get_text().strip() for page in document] == ["second", "keep secret"]
    document.close()
    document = fitz.open(redacted)
    assert "secret" not in document[0].get_text()
    document.close()


def test_cli_script_recipe(tmp_path):
    source = tmp_path / "source.pdf"
    output = tmp_path / "output.pdf"
    recipe = tmp_path / "recipe.py"
    make_pdf(source, ["one", "two"])
    recipe.write_text(
        "actions = [{'operation': 'add_bates_numbers', 'prefix': 'DOC-', 'start': 1, 'digits': 3}]\n",
        encoding="utf-8",
    )

    assert main(["script", str(recipe), str(source), "-o", str(output)]) == 0
    document = fitz.open(output)
    assert "DOC-001" in document[0].get_text()
    document.close()

