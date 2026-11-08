"""Check local Markdown/HTML links and SVG syntax without network requests."""

from __future__ import annotations

import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit
from xml.etree import ElementTree

from markdown_it import MarkdownIt

ROOT = Path(__file__).resolve().parents[2]


class HtmlLinks(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[str] = []

    def handle_starttag(self, tag, attrs):
        for name, value in attrs:
            if value and ((tag == "a" and name == "href") or
                          (tag == "img" and name == "src")):
                self.links.append(value)


def token_links(tokens):
    for token in tokens:
        if token.type == "link_open":
            yield token.attrGet("href")
        elif token.type == "image":
            yield token.attrGet("src")
        elif token.type in ("html_inline", "html_block"):
            parser = HtmlLinks()
            parser.feed(token.content)
            yield from parser.links
        if token.children:
            yield from token_links(token.children)


def main() -> int:
    parser = MarkdownIt("commonmark", {"html": True}).enable("table")
    files = sorted(ROOT.glob("*.md"))
    for folder in ("docs", "examples", ".github"):
        files.extend(sorted((ROOT / folder).rglob("*.md")))
    # macOS can store file metadata in separate ._ files on external drives.
    files = [path for path in files if not path.name.startswith("._")]
    errors = []
    checked = 0
    for path in files:
        for href in token_links(parser.parse(path.read_text(encoding="utf-8"))):
            if not href:
                continue
            link = urlsplit(href)
            if link.scheme or link.netloc or not link.path:
                continue
            target = (path.parent / unquote(link.path)).resolve()
            checked += 1
            if not target.is_relative_to(ROOT) or not target.exists():
                errors.append(f"{path.relative_to(ROOT)}: broken local link {href}")
    figures = sorted(
        path for path in (ROOT / "docs").rglob("*.svg") if not path.name.startswith("._")
    )
    for path in figures:
        try:
            ElementTree.parse(path)
        except ElementTree.ParseError as error:
            errors.append(f"{path.relative_to(ROOT)}: {error}")
    for error in errors:
        print(error, file=sys.stderr)
    print(f"Checked {len(files)} Markdown files, {checked} local links, {len(figures)} SVGs.")
    return bool(errors)


if __name__ == "__main__":
    raise SystemExit(main())
