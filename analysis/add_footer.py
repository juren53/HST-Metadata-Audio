"""
Adds a footer to a .docx file:
  left:  filename (e.g. PROCESS_NOTES.docx)
  right: Page X of Y

Usage:  python add_footer.py <file.docx>
"""

import sys
from pathlib import Path
from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt, Inches


def _rpr(size_pt):
    """Return a <w:rPr> element with font size set."""
    rpr = OxmlElement("w:rPr")
    for tag in ("w:sz", "w:szCs"):
        el = OxmlElement(tag)
        el.set(qn("w:val"), str(size_pt * 2))  # half-points
        rpr.append(el)
    return rpr


def _text_run(text, size_pt=9):
    r = OxmlElement("w:r")
    r.append(_rpr(size_pt))
    t = OxmlElement("w:t")
    t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    t.text = text
    r.append(t)
    return r


def _tab_run():
    r = OxmlElement("w:r")
    r.append(OxmlElement("w:tab"))
    return r


def _field_run(instr, size_pt=9):
    """Return list of three <w:r> elements forming a simple Word field."""
    begin = OxmlElement("w:r")
    begin.append(_rpr(size_pt))
    fc1 = OxmlElement("w:fldChar")
    fc1.set(qn("w:fldCharType"), "begin")
    begin.append(fc1)

    instr_r = OxmlElement("w:r")
    instr_r.append(_rpr(size_pt))
    it = OxmlElement("w:instrText")
    it.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    it.text = f" {instr} "
    instr_r.append(it)

    end = OxmlElement("w:r")
    end.append(_rpr(size_pt))
    fc2 = OxmlElement("w:fldChar")
    fc2.set(qn("w:fldCharType"), "end")
    end.append(fc2)

    return [begin, instr_r, end]


def add_footer(docx_path: Path):
    doc = Document(str(docx_path))
    section = doc.sections[0]
    section.different_first_page_header_footer = False
    footer = section.footer

    # Remove any existing footer paragraphs
    for para in list(footer.paragraphs):
        para._p.getparent().remove(para._p)

    # Create a new paragraph
    p = OxmlElement("w:p")

    # Paragraph properties: right-aligned tab stop at 6.5 in (9360 twips)
    pPr = OxmlElement("w:pPr")
    tabs = OxmlElement("w:tabs")
    tab = OxmlElement("w:tab")
    tab.set(qn("w:val"), "right")
    tab.set(qn("w:pos"), "9360")
    tabs.append(tab)
    pPr.append(tabs)
    # Use "Footer" style if it exists
    pStyle = OxmlElement("w:pStyle")
    pStyle.set(qn("w:val"), "Footer")
    pPr.insert(0, pStyle)
    p.append(pPr)

    # Left: filename
    p.append(_text_run(docx_path.name))

    # Tab to right
    p.append(_tab_run())

    # Right: "Page " PAGE " of " NUMPAGES
    p.append(_text_run("Page "))
    for r in _field_run("PAGE"):
        p.append(r)
    p.append(_text_run(" of "))
    for r in _field_run("NUMPAGES"):
        p.append(r)

    footer._element.append(p)
    doc.save(str(docx_path))
    print(f"Footer added to {docx_path.name}")


if __name__ == "__main__":
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent / "PROCESS_NOTES.docx"
    add_footer(path)
