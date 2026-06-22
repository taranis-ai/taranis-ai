from __future__ import annotations

import csv
import json
from pathlib import Path

from tests.load.load_support.summarize_stats import load_page_rows, write_outputs


def test_load_page_rows_filters_and_sorts_page_metrics(tmp_path: Path) -> None:
    stats_path = tmp_path / "locust_stats.csv"
    markdown_path = tmp_path / "ux-timings-summary.md"
    json_path = tmp_path / "ux-timings-summary.json"

    fieldnames = [
        "Type",
        "Name",
        "Request Count",
        "Failure Count",
        "Median Response Time",
        "Average Response Time",
        "Min Response Time",
        "Max Response Time",
        "Average Content Size",
        "Requests/s",
        "Failures/s",
        "50%",
        "66%",
        "75%",
        "80%",
        "90%",
        "95%",
        "98%",
        "99%",
        "99.9%",
        "99.99%",
        "100%",
    ]

    rows = [
        {
            "Type": "TASK",
            "Name": "FrontendBrowserUser.dashboard_flow",
            "Request Count": "2",
            "Failure Count": "0",
            "Median Response Time": "400",
            "Average Response Time": "410",
            "Min Response Time": "390",
            "Max Response Time": "430",
            "Average Content Size": "0",
            "Requests/s": "0.1",
            "Failures/s": "0.0",
            "50%": "400",
            "66%": "430",
            "75%": "430",
            "80%": "430",
            "90%": "430",
            "95%": "430",
            "98%": "430",
            "99%": "430",
            "99.9%": "430",
            "99.99%": "430",
            "100%": "430",
        },
        {
            "Type": "PAGE",
            "Name": "dashboard:ready",
            "Request Count": "4",
            "Failure Count": "0",
            "Median Response Time": "50",
            "Average Response Time": "55",
            "Min Response Time": "40",
            "Max Response Time": "85",
            "Average Content Size": "0",
            "Requests/s": "0.2",
            "Failures/s": "0.0",
            "50%": "48",
            "66%": "48",
            "75%": "85",
            "80%": "85",
            "90%": "85",
            "95%": "85",
            "98%": "85",
            "99%": "85",
            "99.9%": "85",
            "99.99%": "85",
            "100%": "85",
        },
        {
            "Type": "PAGE",
            "Name": "assess:ready",
            "Request Count": "2",
            "Failure Count": "1",
            "Median Response Time": "390",
            "Average Response Time": "290",
            "Min Response Time": "180",
            "Max Response Time": "400",
            "Average Content Size": "0",
            "Requests/s": "0.1",
            "Failures/s": "0.01",
            "50%": "400",
            "66%": "400",
            "75%": "400",
            "80%": "400",
            "90%": "400",
            "95%": "400",
            "98%": "400",
            "99%": "400",
            "99.9%": "400",
            "99.99%": "400",
            "100%": "400",
        },
    ]

    with stats_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    summary_rows = load_page_rows(stats_path)

    assert [row["name"] for row in summary_rows] == ["assess:ready", "dashboard:ready"]

    markdown = write_outputs(summary_rows, markdown_path, json_path)

    assert "Sorted by `p95` descending" in markdown
    assert "| assess:ready | 2 | 1 |" in markdown
    assert markdown_path.exists()

    json_rows = json.loads(json_path.read_text(encoding="utf-8"))
    assert json_rows[0]["name"] == "assess:ready"
    assert json_rows[1]["name"] == "dashboard:ready"
