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
                "date": "1977-01-01",
                "author": "Jim Jarmuush",
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

        date: 1977-01-01

        author: Jim Jarmuush


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
