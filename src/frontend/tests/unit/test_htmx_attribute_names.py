import re
from pathlib import Path


# htmx 4 silently ignores these htmx 2 attribute names. hx-disable is valid in both versions, so it cannot be checked by name.
HTMX2_ATTRIBUTE_REPLACEMENTS = {
    "hx-disabled-elt": "hx-disable",
    "hx-vars": "hx-vals with a js: prefix",
    "hx-params": "an htmx:config:request listener",
    "hx-prompt": "the hx-prompt extension",
    "hx-ext": "nothing; including the extension script is enough",
    "hx-disinherit": "nothing; inheritance is explicit via :inherited",
    "hx-inherit": "the :inherited modifier on individual attributes",
    "hx-request": "hx-config",
}

HTMX2_ATTRIBUTE_PATTERN = re.compile(
    r"(?<![\w-])(?:data-)?(" + "|".join(re.escape(name) for name in HTMX2_ATTRIBUTE_REPLACEMENTS) + r")(?![\w-])"
)

FRONTEND_ROOT = Path(__file__).resolve().parents[2]

SCANNED_FILES = (
    (FRONTEND_ROOT / "frontend/templates", "**/*.html"),
    (FRONTEND_ROOT / "frontend/static/js", "*.js"),
)


def test_frontend_uses_htmx4_attribute_names():
    violations: list[str] = []

    for directory, pattern in SCANNED_FILES:
        paths = sorted(directory.glob(pattern))
        assert paths, f"No files matching {pattern} found in {directory}; the htmx attribute check would pass without scanning anything"
        for path in paths:
            for line_number, line in enumerate(path.read_text().splitlines(), start=1):
                for match in HTMX2_ATTRIBUTE_PATTERN.finditer(line):
                    name = match.group(1)
                    violations.append(
                        f"{path.relative_to(FRONTEND_ROOT)}:{line_number} uses htmx 2 attribute {name}; "
                        f"use {HTMX2_ATTRIBUTE_REPLACEMENTS[name]}"
                    )

    assert not violations, "\n".join(violations)
