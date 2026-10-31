"""Repair text that PDF readers extract wrongly from badly encoded fonts.

PURPOSE: some PDFs (the TCS FY25 annual report is one) use fonts whose
internal "which character is this?" table is wrong. Every PDF reader then
reads the same wrong answer: the digit 4 comes out as "ϰ", 5 as "ϱ", "%" as
"й", and so on. This garbles 247 of the report's 336 pages, including
nearly every number, which makes a financial assistant useless.

The fix is a lookup table from each broken glyph to the character it really
is. Each entry was worked out from context and checked against numbers
read off page images (see experiments/pdf_readers/), e.g.
    "2ϱϱ,32ϰ crore"  ->  "255,324 crore"  (TCS revenue, PDF page 181)

Readers report broken glyphs in two ways, so there are two tables:
    pypdf / PyMuPDF   give a Unicode character, e.g. "ϰ"
    pdfplumber        gives the font's raw code,  e.g. "(cid:1008)"
"""

from __future__ import annotations

import re
import unicodedata

# ---------- Broken glyph (Unicode character) -> real character ----------
# The broken digit glyphs sit in one consecutive Unicode block:
# U+03EC is 0, U+03ED is 1, ... U+03F5 is 9. So digit d is chr(0x03EC + d).
# 0 and 4-9 were observed in the TCS report and checked against page images;
# 1-3 never appeared broken (those digits render normally) and are included
# because they follow the same pattern.
GLYPH_REPAIRS: dict[str, str] = {chr(0x03EC + d): str(d) for d in range(10)}
GLYPH_REPAIRS.update(
    {
        "й": "%",  # й      "margin of 2ϰ.3й" -> "24.3%"
        "͘": ".",  # ͘ (combining dot)     "13ϰ͘1ϵ" -> "134.19"
        "͗": ":",  # ͗      "emissions͗" -> "emissions:"
        "͞": "“",  # ͞      "(͞AGM͟)" -> "(“AGM”)"
        "͟": "”",  # ͟
        "ͻ": "•",  # ͻ      starts bullet-list items
        "༤": "₹",  # ༤      "༤2ϱϱ,32ϰ crore" -> "₹255,324 crore"
    }
)

# ---------- Broken glyph (pdfplumber raw code) -> real character ----------
# Same glyphs as above, as the font codes pdfplumber prints when it can't
# map a glyph: "(cid:1004)" is 0 ... "(cid:1013)" is 9.
CID_REPAIRS: dict[int, str] = {1004 + d: str(d) for d in range(10)}
CID_REPAIRS.update({1081: "%", 856: ".", 855: ":", 862: "“", 863: "”", 891: "•", 3876: "₹"})

_CID = re.compile(r"\(cid:(\d+)\)")


def repair_text(text: str) -> str:
    """Return text with known broken glyphs replaced by the real characters.

    Unknown "(cid:N)" codes are left as they are, so they still show up in
    quality checks instead of being silently hidden.
    """
    # 1. pdfplumber-style raw codes.
    text = _CID.sub(lambda m: CID_REPAIRS.get(int(m.group(1)), m.group(0)), text)

    # 2. Unicode-style broken glyphs. This MUST run before step 4: Unicode
    #    normalisation would turn "ϰ" into the Greek letter "κ", and then
    #    we could no longer recognise it as a broken 4.
    text = text.translate(str.maketrans(GLYPH_REPAIRS))

    # 3. Some PDFs map the rupee sign to a backtick: "(` crore)".
    text = text.replace("`", "₹")

    # 4. NFKC normalisation turns compatibility characters into plain ones:
    #    ligatures ("ﬁ" -> "fi", so "identiﬁcation" becomes searchable),
    #    thin and non-breaking spaces -> normal spaces.
    return unicodedata.normalize("NFKC", text)
