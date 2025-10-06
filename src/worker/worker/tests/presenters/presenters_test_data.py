test_template = """
Test Report - {{ data.current_date }}

Report Items:
{% for report_item in data.report_items %}
  {{ report_item.title }}:
      {% for key, value in report_item.attributes.items() %}
        {{ key }}: {{ value }}
      {% endfor %}

  Stories:
    {% for story in report_item.stories %}
    {{ story.title }}:
      {% for news_item in story.news_items %}
        {{ news_item.title }} ({{ news_item.link }}):
          {{ news_item.content }}

      {% endfor %}
    {% endfor %}
{% endfor %}
"""

test_product = {
    "id": "ab063c21-d29a-49ad-ab7a-09f87ff84339",
    "mime_type": "text/plain",
    "title": "A Test Report",
    "type": "text_presenter",
    "type_id": 2,
    "report_items": [
        {
            "title": "The very best report you have ever seen",
            "attributes": {
                "date_group": {
                    "date": "1977-01-01",
                },
                "author_group": {
                    "author": "Jim Jarmuush",
                },
            },
            "stories": [
                {
                    "title": "City Council Approves New Housing Plan",
                    "news_items": [
                        {
                            "title": "Council votes 9-2 for zoning update",
                            "link": "https://example.com/city-housing-plan",
                            "content": "Measure expands affordable units; vote was 9-2.",
                        },
                    ],
                },
                {
                    "title": "Tech Company Announces Quarterly Earnings",
                    "news_items": [
                        {
                            "title": "Q2 revenue rises 12 percent",
                            "link": "https://example.com/tech-q2",
                            "content": "Company raises full-year guidance.",
                        },
                        {
                            "title": "Shares jump after the report",
                            "link": "https://example.com/tech-shares",
                            "content": "Stock up 4 percent in after-hours trading.",
                        },
                    ],
                },
                {
                    "title": "Regional Rail Service Disruption",
                    "news_items": [
                        {
                            "title": "Signal fault delays morning trains",
                            "link": "https://example.com/rail-delays",
                            "content": "Operator advises 20-minute delays on main line.",
                        },
                    ],
                },
                {
                    "title": "Severe Weather Hits Coastal Towns",
                    "news_items": [
                        {
                            "title": "Storm brings heavy rain and wind",
                            "link": "https://example.com/storm",
                            "content": "Flood warnings issued for low-lying areas.",
                        },
                        {
                            "title": "Cleanup crews deployed at first light",
                            "link": "https://example.com/cleanup",
                            "content": "Roads cleared; power restoration underway.",
                        },
                        {
                            "title": "Weekend forecast improves",
                            "link": "https://example.com/forecast",
                            "content": "Skies clearing by Saturday afternoon.",
                        },
                    ],
                },
            ],
        }
    ],
}

rendered_report = """
Test Report - 2025-01-02

Report Items:
  The very best report you have ever seen:
        date_group: {'date': '1977-01-01'}
        author_group: {'author': 'Jim Jarmuush'}

  Stories:
    City Council Approves New Housing Plan:
        Council votes 9-2 for zoning update (https://example.com/city-housing-plan):
          Measure expands affordable units; vote was 9-2.

    Tech Company Announces Quarterly Earnings:
        Q2 revenue rises 12 percent (https://example.com/tech-q2):
          Company raises full-year guidance.

        Shares jump after the report (https://example.com/tech-shares):
          Stock up 4 percent in after-hours trading.

    Regional Rail Service Disruption:
        Signal fault delays morning trains (https://example.com/rail-delays):
          Operator advises 20-minute delays on main line.

    Severe Weather Hits Coastal Towns:
        Storm brings heavy rain and wind (https://example.com/storm):
          Flood warnings issued for low-lying areas.

        Cleanup crews deployed at first light (https://example.com/cleanup):
          Roads cleared; power restoration underway.

        Weekend forecast improves (https://example.com/forecast):
          Skies clearing by Saturday afternoon.
"""


test_stix_product = {
    "id": "2342835f-ffef-4d36-a381-2d7bb0ddd553",
    "mime_type": "application/stix+json",
    "report_items": [
        {
            "attributes": {
                "Identify and Act": {"Affected Systems": "", "IOC": "", "Links": "link2", "Recommendations": ""},
                "Vulnerability": {
                    "CVE": "",
                    "CVSS": "",
                    "Confidentiality": "",
                    "Description": "",
                    "Exposure Date": "",
                    "Impact": "",
                    "Links": "link1",
                    "TLP": "clear",
                    "Update Date": "",
                },
            },
            "completed": False,
            "created": "2025-09-26T14:31:51.329753+02:00",
            "id": "09e63054-309a-459e-9dca-7544749e86dc",
            "last_updated": "2025-09-26T14:31:51.329758+02:00",
            "report_item_type_id": 3,
            "stories": [
                {
                    "attributes": {"TLP": {"key": "TLP", "value": "clear"}},
                    "comments": "",
                    "created": "2025-09-25T14:05:00+02:00",
                    "description": "",
                    "dislikes": 0,
                    "id": "dc4ad103-d5ef-4b9d-be56-fcfdfcdbe10e",
                    "important": False,
                    "last_change": "external",
                    "likes": 0,
                    "links": [],
                    "news_items": [
                        {
                            "author": "Aktuelles aus dem Test",
                            "collected": "2025-09-26T13:39:48.562837+02:00",
                            "content": 'GEMEINSAM.SICHER\nOktober im Zeichen von "Coffee with Cops"\nDer Oktober 2025 steht zur Gänze im Zeichen von "Coffee with Cops".',
                            "hash": "1ea3fbf356ad23d92e851e0d3ed47d0dbd70ab80edcf7ddd49583844957fa070",
                            "id": "d1b68712-4281-4532-88b0-907b3924e938",
                            "language": "",
                            "last_change": "external",
                            "link": "https://www.test.gv.at/news.aspx?id=662B784C67346F56715A493D",
                            "osint_source_id": "3e0b67b0-f634-4a8e-8145-f9486da277b4",
                            "published": "2025-09-25T14:05:00+02:00",
                            "review": "",
                            "source": "https://www.test.gv.at/rss/test_presse.xml",
                            "story_id": "dc4ad103-d5ef-4b9d-be56-fcfdfcdbe10e",
                            "title": 'Oktober im Zeichen von "Coffee with Cops"',
                            "updated": "2025-09-26T13:38:52.714021+02:00",
                        }
                    ],
                    "read": False,
                    "relevance": 0,
                    "summary": "",
                    "tags": {"conclusions": {"name": "conclusions", "tag_type": "report_09e63054-309a-459e-9dca-7544749e86dc"}},
                    "title": 'Oktober im Zeichen von "Coffee with Cops"',
                    "updated": "2025-09-26T13:39:50.588130+02:00",
                }
            ],
            "title": "conclusions",
            "user_id": 1,
        }
    ],
    "title": "Stix product",
    "type": "stix_presenter",
    "type_id": 6,
}
