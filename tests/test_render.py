"""Tests for src/render.py. Needs Playwright with Chromium installed."""

import struct

from src.render import render_documents


def png_size(path):
    """Read width and height from a PNG header."""
    with open(path, "rb") as f:
        header = f.read(24)
    return struct.unpack(">II", header[16:24])


def test_png_is_page_size(tmp_path):
    docs = {"d1": {"title": "A title", "text": "Short body text."}}
    render_documents(docs, "plain", tmp_path)
    assert png_size(tmp_path / "d1.png") == (1024, 1366)


def test_long_document_is_truncated_at_a_word(tmp_path):
    text = "word " * 5000
    docs = {"long": {"title": "Long", "text": text}}
    cut = render_documents(docs, "plain", tmp_path)

    assert len(cut) == 1
    doc_id, original, kept = cut[0]
    assert (doc_id, original) == ("long", len(text))
    assert 0 < kept < original
    assert text[:kept].endswith("word")  # cut at a word end, text unchanged
