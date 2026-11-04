"""Render each document as HTML in a visual style and screenshot it at a fixed page size.

The document text is HTML-escaped but never changed. If it does not fit on one page,
the body is cut after the last word that fits, and the cut is recorded.

Fonts come from assets/fonts/ and are embedded in the page with @font-face, so rendering
never depends on the fonts installed on the machine. If a font fails to load, rendering
stops with an error instead of silently falling back to a system font.
"""

import base64
import csv
import html
import re
from contextlib import contextmanager
from functools import lru_cache
from pathlib import Path

import yaml
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "configs" / "styles.yaml"

TEMPLATE = """<!doctype html>
<html>
<head>
<meta charset="utf-8">
<style>
{font_faces}
  html, body {{ margin: 0; }}
  body {{
    box-sizing: border-box;
    width: {width}px;
    padding: {margin}px;
    font-family: {font_stack};
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

# Loads each wanted font (CSS shorthand like 'bold 16px "Noto Serif"'), then checks all
# are in use. document.fonts.check() alone is not enough: it also returns true when no
# @font-face with that name exists, so we first require load() to return a face.
CHECK_FONTS_JS = """async (wanted) => {
  for (const font of wanted) {
    const faces = await document.fonts.load(font);
    if (faces.length === 0) return false;
  }
  await document.fonts.ready;
  return wanted.every((font) => document.fonts.check(font));
}"""


def load_styles(path=CONFIG_PATH):
    """Read configs/styles.yaml."""
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


@lru_cache
def font_as_base64(path):
    """Read a font file once and return it base64-encoded."""
    return base64.b64encode(Path(path).read_bytes()).decode("ascii")


def font_families(style, config):
    """The style's font followed by the shared fallback fonts, in CSS order."""
    return [style["font"]] + config["fallback_fonts"]


def font_face_css(families, config):
    """Return @font-face rules for every bundled face (regular, bold) of the families."""
    rules = []
    for family in families:
        files = config["fonts"][family]
        for weight, key in [("normal", "regular"), ("bold", "bold")]:
            if key not in files:
                continue
            data = font_as_base64(ROOT / config["fonts_dir"] / files[key])
            rules.append(
                f'  @font-face {{ font-family: "{family}"; font-weight: {weight}; '
                f'src: url(data:font/ttf;base64,{data}) format("truetype"); }}'
            )
    return "\n".join(rules)


def build_html(title, text, style, config):
    """Fill the template with one document in one style. Title and text are escaped."""
    page = config["page"]
    families = font_families(style, config)
    return TEMPLATE.format(
        font_faces=font_face_css(families, config),
        font_stack=", ".join(f'"{family}"' for family in families),
        width=page["width_px"],
        margin=page["margin_px"],
        font_size=style["font_size_px"],
        text_color=style["text_color"],
        background_color=style["background_color"],
        heading_color=style["heading_color"],
        title=html.escape(title),
        text=html.escape(text),
    )


def check_fonts(browser_page, style, config):
    """Raise RuntimeError unless every bundled face for the style is loaded in the page."""
    size = style["font_size_px"]
    wanted = []
    for family in font_families(style, config):
        wanted.append(f'{size}px "{family}"')
        if "bold" in config["fonts"][family]:
            wanted.append(f'bold {size}px "{family}"')
    if not browser_page.evaluate(CHECK_FONTS_JS, wanted):
        raise RuntimeError(f"Fonts {wanted} did not load; refusing to fall back.")


def show(browser_page, title, text, style, config):
    """Load one document into the page and wait until its fonts are in use."""
    browser_page.set_content(build_html(title, text, style, config))
    check_fonts(browser_page, style, config)


def fits(browser_page, title, text, style, config):
    """True if the document fits within the page height."""
    show(browser_page, title, text, style, config)
    height = browser_page.evaluate("document.documentElement.scrollHeight")
    return height <= config["page"]["height_px"]


def fit_text(browser_page, title, text, style, config):
    """Return the longest prefix of text, ending at a word, that fits on the page.

    The prefix is cut from the original string, so its characters are unchanged.
    """
    if fits(browser_page, title, text, style, config):
        return text

    word_ends = [m.end() for m in re.finditer(r"\S+", text)]
    lo, hi = 0, len(word_ends)  # binary search on the number of words kept
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if fits(browser_page, title, text[: word_ends[mid - 1]], style, config):
            lo = mid
        else:
            hi = mid - 1
    if lo == 0:
        raise ValueError("Title alone does not fit on the page.")
    return text[: word_ends[lo - 1]]


@contextmanager
def open_browser_page(config):
    """Yield a Chromium page with the viewport set to the page size."""
    page = config["page"]
    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            yield browser.new_page(
                viewport={"width": page["width_px"], "height": page["height_px"]},
                device_scale_factor=1,
            )
        finally:
            browser.close()


def render_documents(docs, style_name, out_dir, config_path=CONFIG_PATH):
    """Render {doc_id: {"title", "text"}} in one style to out_dir/<doc_id>.png.

    Truncated documents are listed in out_dir/truncations.csv.
    Returns a list of (doc_id, original_chars, kept_chars) for truncated documents.
    """
    config = load_styles(config_path)
    style = config["styles"][style_name]
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    truncations = []
    with open_browser_page(config) as browser_page:
        for doc_id, doc in docs.items():
            text = fit_text(browser_page, doc["title"], doc["text"], style, config)
            if len(text) < len(doc["text"]):
                truncations.append((doc_id, len(doc["text"]), len(text)))
            show(browser_page, doc["title"], text, style, config)
            browser_page.screenshot(path=out_dir / f"{doc_id}.png")

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
