"""Tests for src/render.py. Needs Playwright with Chromium installed."""

import struct

import pytest

from src.render import (
    check_fonts,
    load_styles,
    open_browser_page,
    render_documents,
    show,
)


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


def fonts_used(browser_page, selector):
    """Ask Chromium which fonts it actually used to draw the text of one element."""
    cdp = browser_page.context.new_cdp_session(browser_page)
    cdp.send("DOM.enable")
    cdp.send("CSS.enable")
    root = cdp.send("DOM.getDocument")["root"]["nodeId"]
    node = cdp.send("DOM.querySelector", {"nodeId": root, "selector": selector})
    fonts = cdp.send("CSS.getPlatformFontsForNode", {"nodeId": node["nodeId"]})
    return {(f["familyName"], f["isCustomFont"]) for f in fonts["fonts"]}


def test_requested_font_is_used():
    config = load_styles()
    style = config["styles"]["plain"]
    with open_browser_page(config) as browser_page:
        show(browser_page, "A title", "Body text, 95% CI 0.38 – 0.55.", style, config)
        for selector in ["h1", "p"]:
            assert fonts_used(browser_page, selector) == {("Noto Serif", True)}


def test_symbols_use_bundled_fallback_fonts():
    config = load_styles()
    style = config["styles"]["plain"]
    text = "Dose ≥ 5 mg, p ≤ 0.05, ∼ 3 h → ■ ☆"
    with open_browser_page(config) as browser_page:
        show(browser_page, "A title", text, style, config)
        used = fonts_used(browser_page, "p")
    assert ("Noto Serif", True) in used
    for family, is_bundled in used:
        assert is_bundled and family in config["fonts"], (family, used)


def test_font_check_fails_without_bundled_font():
    config = load_styles()
    style = config["styles"]["plain"]
    with open_browser_page(config) as browser_page:
        browser_page.set_content('<p style="font-family: serif">no @font-face</p>')
        with pytest.raises(RuntimeError, match="did not load"):
            check_fonts(browser_page, style, config)
