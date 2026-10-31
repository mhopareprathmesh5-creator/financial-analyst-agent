"""Build tiny real PDF files in memory, for tests.

PURPOSE: tests of the real PDF reading path (pdfplumber) need actual PDF
bytes. Instead of committing PDF files, this writes the smallest valid PDF
by hand: one line of text per page, in the standard Helvetica font.

A PDF is a list of numbered "objects" (catalog, page list, font, pages,
page contents) followed by an "xref" table giving each object's byte
position, which is why the offsets are tracked below.
"""


def make_pdf(pages: list[str]) -> bytes:
    """Return PDF bytes with one page per string. "" makes a blank page.

    Keep texts to plain ASCII without parentheses or backslashes: those have
    special meaning inside a PDF text command.
    """
    n = len(pages)
    objects = [
        "<< /Type /Catalog /Pages 2 0 R >>",  # object 1: document root
        # object 2: the page list; page i is object 4 + 2i
        f"<< /Type /Pages /Kids [{' '.join(f'{4 + 2 * i} 0 R' for i in range(n))}] /Count {n} >>",
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",  # object 3: font
    ]
    for i, text in enumerate(pages):
        # "BT ... ET" = begin/end text; draw `text` at 72pt from left, 720pt from bottom.
        content = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET" if text else ""
        objects.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            f"/Resources << /Font << /F1 3 0 R >> >> /Contents {5 + 2 * i} 0 R >>"
        )
        objects.append(f"<< /Length {len(content)} >>\nstream\n{content}\nendstream")

    out = b"%PDF-1.4\n"
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{number} 0 obj\n{body}\nendobj\n".encode()

    xref_position = len(out)
    out += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
    for offset in offsets:
        out += f"{offset:010d} 00000 n \n".encode()
    out += (
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref_position}\n%%EOF\n"
    ).encode()
    return out
