from __future__ import annotations

import json
import re

from tests.load.load_support.format_locust_report import convert_report_html_to_kilobytes


def _extract_template_args(html: str) -> dict[str, object]:
    match = re.search(
        r"window\.templateArgs\s*=\s*(\{.*?\})\s*\n\s*window\.theme\s*=",
        html,
        re.DOTALL,
    )
    assert match is not None
    return json.loads(match.group(1))


def test_convert_report_html_to_kilobytes_updates_average_size_column() -> None:
    html = """
<script type="module">
const requestColumns = [{key:"avgContentLength",title:"Average size (bytes)",round:2}];
</script>
<body>
<script>
window.templateArgs = {"is_report":true,"requests_statistics":[{"name":"dashboard:ready","avg_content_length":1536},{"name":"login:ready","avg_content_length":512},{"name":"aggregated"}]}
window.theme = "light"
</script>
</body>
"""

    converted = convert_report_html_to_kilobytes(html)

    assert "Average size (KB)" in converted
    assert "Average size (bytes)" not in converted

    template_args = _extract_template_args(converted)
    requests_statistics = template_args["requests_statistics"]
    assert requests_statistics[0]["avg_content_length"] == 1.5
    assert requests_statistics[1]["avg_content_length"] == 0.5
    assert "avg_content_length" not in requests_statistics[2]


def test_convert_report_html_to_kilobytes_is_idempotent_after_label_update() -> None:
    html = """
<script type="module">
const requestColumns = [{key:"avgContentLength",title:"Average size (KB)",round:2}];
</script>
<script>
window.templateArgs = {"is_report":true,"requests_statistics":[{"name":"dashboard:ready","avg_content_length":1.5}]}
window.theme = "light"
</script>
"""

    assert convert_report_html_to_kilobytes(html) == html
