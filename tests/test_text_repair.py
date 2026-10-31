"""Tests for rag/text_repair.py.

PURPOSE: prove the broken-font repair turns garbled annual-report text back
into correct numbers. The inputs are real strings extracted from the TCS
FY25 report; the expected outputs were read from page images.
"""

from rag.text_repair import repair_text


def test_broken_digits_from_pymupdf_and_pypdf():
    # TCS revenue and other income, PDF page 181 / 230.
    assert repair_text("2,55,32ϰ") == "2,55,324"
    assert repair_text("ϰ,ϰ22") == "4,422"
    # All ten digit glyphs, U+03EC..U+03F5 -> 0..9.
    assert repair_text("ϬϭϮϯϰϱϲϳϴϵ") == "0123456789"


def test_broken_digits_from_pdfplumber():
    # Same revenue row as pdfplumber prints it.
    assert repair_text("Revenue from operations 12 2,55,32(cid:1008) 2,(cid:1008)0,893") == (
        "Revenue from operations 12 2,55,324 2,40,893"
    )


def test_broken_punctuation_and_rupee():
    assert repair_text("EPS ༤13ϰ͘1ϵ") == "EPS ₹134.19"
    assert repair_text("margin of 2ϰ.3й") == "margin of 24.3%"
    assert repair_text("(` crore)") == "(₹ crore)"


def test_unknown_cid_codes_are_kept_visible():
    # Codes we haven't verified stay as they are, so quality checks still see them.
    assert repair_text("x(cid:449)y") == "x(cid:449)y"


def test_ligatures_become_plain_letters():
    # "ﬁ" is one character; without this, searching "identification" misses it.
    assert repair_text("Risk identiﬁcation") == "Risk identification"


def test_clean_text_is_unchanged():
    text = "Revenue from operations 1,62,990 (23.6) ₹43 per share"
    assert repair_text(text) == text
