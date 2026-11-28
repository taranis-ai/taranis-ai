import json
from pathlib import Path

from jinja2.sandbox import ImmutableSandboxedEnvironment


TEMPLATES_DIR = Path(__file__).resolve().parents[2] / "core" / "static" / "presenter_templates"


def _render(name: str, data: dict) -> str:
    env = ImmutableSandboxedEnvironment(autoescape=False)
    template = env.from_string((TEMPLATES_DIR / name).read_text(encoding="utf-8"))
    return template.render(data=data)


def test_cert_at_daily_report_txt_renders_with_cert_report_and_blank_fields():
    full_output = _render(
        "cert_at_daily_report.txt",
        {
            "report_items": [
                {
                    "attributes": {
                        "Data": {
                            "date": "2026-11-27",
                            "timeframe": "24h",
                            "handler": "Alice",
                            "co_handler": "Bob",
                            "news": "story-1",
                            "vulnerabilities": "story-2",
                        }
                    },
                    "stories": [
                        {
                            "id": "story-1",
                            "title": "News Story",
                            "summary": "Summary 1",
                            "news_items": [{"link": "https://news.example.test", "content": "Body 1"}],
                        },
                        {
                            "id": "story-2",
                            "title": "Vuln Story",
                            "summary": "",
                            "news_items": [{"link": "https://vuln.example.test", "content": "Body 2"}],
                        },
                    ],
                }
            ]
        },
    )
    assert "News Story" in full_output
    assert "Vuln Story" in full_output
    assert "https://vuln.example.test" in full_output

    blank_output = _render(
        "cert_at_daily_report.txt",
        {"report_items": [{"attributes": {"Data": {}}, "stories": []}]},
    )
    assert "End-of-Day report" in blank_output


def test_template_disinfo_html_renders_with_disinformation_report_and_blank_fields():
    full_output = _render(
        "template_disinfo.html",
        {
            "title": "Weekly Disinformation",
            "current_date": "2026-11-27",
            "report_items": [
                {
                    "id": "rep-1",
                    "title": "Campaign A",
                    "attributes": {
                        "Summary": {
                            "Title": "Campaign A",
                            "Quote": "Quoted claim",
                            "Reach": "50000",
                            "Date started": "2026-11-20",
                            "Proof": "screenshot.png",
                        }
                    },
                    "stories": [
                        {
                            "title": "Linked Story",
                            "summary": "Details",
                            "news_items": [{"link": "https://source.example.test"}],
                        }
                    ],
                }
            ],
        },
    )
    assert "Weekly Disinformation" in full_output
    assert "Quoted claim" in full_output
    assert "50000" in full_output

    blank_output = _render(
        "template_disinfo.html",
        {"title": "", "report_items": [{"id": "rep-2", "title": "", "attributes": {}, "stories": []}]},
    )
    assert "Disinformation Report" in blank_output


def test_misp_json_produces_valid_json_with_populated_and_blank_fields():
    populated = json.loads(
        _render(
            "misp.json",
            {
                "title": "OSINT Product",
                "report_items": [
                    {
                        "title": "OSINT Report 1",
                        "attributes": {
                            "Summary": {
                                "Threat level": "High",
                                "Summary": 'Alert with "quotes"\nand newline',
                            }
                        },
                        "stories": [
                            {
                                "title": "Story 1",
                                "news_items": [{"link": "https://indicator.example.test"}],
                            }
                        ],
                    }
                ],
            },
        )
    )
    assert populated["threat_level_id"] == "1"
    assert populated["info"] == 'Alert with "quotes"\nand newline'
    assert populated["Attribute"][0]["value"] == "https://indicator.example.test"

    blank = json.loads(
        _render(
            "misp.json",
            {"title": "", "report_items": [{"title": "", "attributes": {"Summary": {}}, "stories": []}]},
        )
    )
    assert blank["threat_level_id"] == "4"
    assert blank["Attribute"] == []

    empty = json.loads(_render("misp.json", {"title": "", "report_items": []}))
    assert empty["Attribute"] == []
