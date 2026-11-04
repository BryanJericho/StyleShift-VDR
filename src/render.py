"""Render each document as HTML in a visual style and screenshot it at a fixed page size.

The document text is HTML-escaped but never changed. If it does not fit on one page,
the body is cut after the last word that fits, and the cut is recorded.
"""

import csv
import html
import re
from pathlib import Path

import yaml
from playwright.sync_api import sync_playwright

CONFIG_PATH = Path(__file__).resolve().parent.parent / "configs" / "styles.yaml"

TEMPLATE = """<!doctype html>
<html>
<head>
<meta charset="utf-8">
<style>
  html, body {{ margin: 0; }}
  body {{
    box-sizing: border-box;
    width: {width}px;
    padding: {margin}px;
    font-family: "{font}", serif;
    font-size: {font_size}px;
    line-height: 1.5;
    color: {text_color};
    background: {background_color};
  }}
  h1 {{ font-size: 1.5em; margin: 0 0 0.75em 0; color: {heading_color}; }}
  p {{ margin: 0; }}
</style>
</head>
<body>
<h1>{title}</h1>
<p>{text}</p>
</body>
</html>
"""


def load_styles(path=CONFIG_PATH):
    """Read configs/styles.yaml."""
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def build_html(title, text, style, page):
    """Fill the template with one document in one style. Title and text are escaped."""
    return TEMPLATE.format(
        width=page["width_px"],
        margin=page["margin_px"],
        font=style["font"],
        font_size=style["font_size_px"],
        text_color=style["text_color"],
        background_color=style["background_color"],
        heading_color=style["heading_color"],
        title=html.escape(title),
        text=html.escape(text),
    )


def fits(browser_page, title, text, style, page):
    """True if the document fits within the page height."""
    browser_page.set_content(build_html(title, text, style, page))
    height = browser_page.evaluate("document.documentElement.scrollHeight")
    return height <= page["height_px"]


def fit_text(browser_page, title, text, style, page):
    """Return the longest prefix of text, ending at a word, that fits on the page.

    The prefix is cut from the original string, so its characters are unchanged.
    """
    if fits(browser_page, title, text, style, page):
        return text

    word_ends = [m.end() for m in re.finditer(r"\S+", text)]
    lo, hi = 0, len(word_ends)  # binary search on the number of words kept
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if fits(browser_page, title, text[: word_ends[mid - 1]], style, page):
            lo = mid
        else:
            hi = mid - 1
    if lo == 0:
        raise ValueError("Title alone does not fit on the page.")
    return text[: word_ends[lo - 1]]


def render_documents(docs, style_name, out_dir, config_path=CONFIG_PATH):
    """Render {doc_id: {"title", "text"}} in one style to out_dir/<doc_id>.png.

    Truncated documents are listed in out_dir/truncations.csv.
    Returns a list of (doc_id, original_chars, kept_chars) for truncated documents.
    """
    config = load_styles(config_path)
    page = config["page"]
    style = config["styles"][style_name]
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    truncations = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        browser_page = browser.new_page(
            viewport={"width": page["width_px"], "height": page["height_px"]},
            device_scale_factor=1,
        )
        for doc_id, doc in docs.items():
            text = fit_text(browser_page, doc["title"], doc["text"], style, page)
            if len(text) < len(doc["text"]):
                truncations.append((doc_id, len(doc["text"]), len(text)))
            browser_page.set_content(build_html(doc["title"], text, style, page))
            browser_page.screenshot(path=out_dir / f"{doc_id}.png")
        browser.close()

    with open(out_dir / "truncations.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["doc_id", "original_chars", "kept_chars"])
        writer.writerows(truncations)
    return truncations


if __name__ == "__main__":
    from src.data import load_dataset

    corpus, _, _ = load_dataset("nfcorpus")
    preview = dict(list(corpus.items())[:3])
    out = Path("results/renders_preview/plain")
    cut = render_documents(preview, "plain", out)
    print(f"Rendered {len(preview)} documents to {out}; truncated: {cut}")
