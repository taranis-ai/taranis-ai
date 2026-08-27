from html import escape
from typing import Any
from urllib.parse import urlparse


ALLOWED_MARKS = {"bold": ("<strong>", "</strong>"), "italic": ("<em>", "</em>"), "inline_code": ("<code>", "</code>")}
ALLOWED_NODES = {"doc", "paragraph", "heading", "blockquote", "bullet_list", "ordered_list", "list_item", "hard_break", "text"}


def project_rich_text(delta: list[dict[str, Any]]) -> tuple[str, str]:
    html_parts: list[str] = []
    plain_parts: list[str] = []
    for item in delta:
        text = item.get("insert") if isinstance(item, dict) else None
        if not isinstance(text, str):
            continue
        plain_parts.append(text)
        value = escape(text)
        marks = item.get("attributes", {}) if isinstance(item, dict) else {}
        if isinstance(marks, dict):
            if link := marks.get("link"):
                parsed = urlparse(str(link))
                if parsed.scheme in {"http", "https"} and parsed.netloc:
                    value = f'<a href="{escape(str(link), quote=True)}" rel="noreferrer noopener">{value}</a>'
            for mark, (opening, closing) in ALLOWED_MARKS.items():
                if marks.get(mark):
                    value = f"{opening}{value}{closing}"
        html_parts.append(value)
    return "".join(html_parts), "".join(plain_parts)


def project_prosemirror(document: dict[str, Any]) -> tuple[str, str]:
    """Project only the small collaboration schema; unknown nodes are dropped."""

    def node(value: Any) -> tuple[str, str]:
        if not isinstance(value, dict) or value.get("type") not in ALLOWED_NODES:
            return "", ""
        kind = value["type"]
        if kind == "text":
            text = value.get("text") if isinstance(value.get("text"), str) else ""
            html = escape(text)
            for mark in value.get("marks", []):
                name = mark.get("type") if isinstance(mark, dict) else None
                if name == "link":
                    href = mark.get("attrs", {}).get("href") if isinstance(mark, dict) else None
                    parsed = urlparse(str(href))
                    if parsed.scheme in {"http", "https"} and parsed.netloc:
                        html = f'<a href="{escape(str(href), quote=True)}" rel="noreferrer noopener">{html}</a>'
                elif name in ALLOWED_MARKS:
                    opening, closing = ALLOWED_MARKS[name]
                    html = f"{opening}{html}{closing}"
            return html, text
        if kind == "hard_break":
            return "<br>", "\n"
        children = [node(child) for child in value.get("content", [])]
        html, plain = "".join(item[0] for item in children), "".join(item[1] for item in children)
        if kind == "paragraph":
            return f"<p>{html}</p>", f"{plain}\n"
        if kind == "heading":
            level = min(max(int(value.get("attrs", {}).get("level", 1)), 1), 6)
            return f"<h{level}>{html}</h{level}>", f"{plain}\n"
        if kind == "blockquote":
            return f"<blockquote>{html}</blockquote>", plain
        if kind == "bullet_list":
            return f"<ul>{html}</ul>", plain
        if kind == "ordered_list":
            return f"<ol>{html}</ol>", plain
        if kind == "list_item":
            return f"<li>{html}</li>", plain
        return html, plain

    return node(document)
