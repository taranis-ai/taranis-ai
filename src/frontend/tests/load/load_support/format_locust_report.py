from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

BYTES_COLUMN_TITLE = "Average size (bytes)"
KILOBYTES_COLUMN_TITLE = "Average size (KB)"
BYTES_PER_KILOBYTE = 1024
TEMPLATE_ARGS_PATTERN = re.compile(
    r"(window\.templateArgs\s*=\s*)(\{.*?\})(\s*\n\s*window\.theme\s*=)",
    re.DOTALL,
)


def _to_kilobytes(value: Any) -> Any:
    if isinstance(value, bool) or not isinstance(value, int | float):
        return value
    return value / BYTES_PER_KILOBYTE


def _convert_template_args_to_kilobytes(
    template_args: dict[str, Any],
) -> dict[str, Any]:
    for row in template_args.get("requests_statistics", []):
        if isinstance(row, dict) and "avg_content_length" in row:
            row["avg_content_length"] = _to_kilobytes(row["avg_content_length"])
    return template_args


def convert_report_html_to_kilobytes(html: str) -> str:
    if BYTES_COLUMN_TITLE not in html:
        return html

    match = TEMPLATE_ARGS_PATTERN.search(html)
    if match is None:
        raise ValueError("Could not find Locust template arguments in HTML report")

    template_args = json.loads(match.group(2))
    template_args = _convert_template_args_to_kilobytes(template_args)
    converted_args = json.dumps(template_args, separators=(",", ":"))

    html = TEMPLATE_ARGS_PATTERN.sub(
        lambda current_match: f"{current_match.group(1)}{converted_args}{current_match.group(3)}",
        html,
        count=1,
    )
    return html.replace(BYTES_COLUMN_TITLE, KILOBYTES_COLUMN_TITLE)


def format_report_file(report_path: Path) -> None:
    html = report_path.read_text(encoding="utf-8")
    report_path.write_text(convert_report_html_to_kilobytes(html), encoding="utf-8")


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(
            "Usage: python -m tests.load.load_support.format_locust_report <locust-report.html>",
            file=sys.stderr,
        )
        return 1

    format_report_file(Path(argv[1]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
