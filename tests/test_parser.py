import pymupdf

from papermind.parser import is_heading, paper_id_for, parse_pdf, split_text


def make_pdf() -> bytes:
    doc = pymupdf.open()
    body = "This sentence discusses the experimental findings in detail. " * 40
    p1 = doc.new_page()
    p1.insert_text((50, 60), "A Tiny Test Paper", fontsize=16)
    p1.insert_text((50, 100), "Abstract", fontsize=12)
    p1.insert_textbox(pymupdf.Rect(50, 110, 550, 300), "We study chunking of papers. " * 10, fontsize=10)
    p1.insert_text((50, 330), "1 Introduction", fontsize=12)
    p1.insert_textbox(pymupdf.Rect(50, 340, 550, 780), body, fontsize=10)
    p2 = doc.new_page()
    p2.insert_text((50, 60), "2 Results", fontsize=12)
    p2.insert_textbox(pymupdf.Rect(50, 70, 550, 500), body, fontsize=10)
    p2.insert_text((50, 520), "References", fontsize=12)
    p2.insert_textbox(pymupdf.Rect(50, 530, 550, 700), "[1] Someone. A cited work. 2020. " * 5, fontsize=10)
    return doc.tobytes()


def test_heading_detection():
    assert is_heading("Abstract")
    assert is_heading("3.1 Training Setup")
    assert not is_heading("This is a normal sentence that ends with a period.")


def test_split_text_overlap_and_bounds():
    text = ("word " * 1000).strip()
    parts = split_text(text, size=300, overlap=50)
    assert len(parts) > 3
    assert all(len(p) <= 300 for _, p in parts)


def test_parse_pdf_sections_pages_and_references():
    data = make_pdf()
    parsed = parse_pdf(data, "tiny.pdf")
    assert parsed.paper_id == paper_id_for(data)
    assert parsed.n_pages == 2
    assert parsed.title
    sections = {c.section for c in parsed.chunks}
    assert "1 Introduction" in sections and "2 Results" in sections
    assert "References" not in sections  # dropped on purpose
    assert {c.page for c in parsed.chunks if c.section == "2 Results"} == {2}
