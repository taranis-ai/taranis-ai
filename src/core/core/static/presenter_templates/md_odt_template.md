---
title: Sample Report - {{ data.current_date }}
---

## Report Items

{% for report_item in data.report_items %}
### {{ report_item.title }}

- {% for key, value in report_item.attributes.items() %}
  **{{ key }}:** {{ value }}
  {% endfor %}

### Stories

{% for story in report_item.stories %}
#### {{ story.title }}

{% for news_item in story.news_items %}
##### {{ news_item.title }}

{{ news_item.content }}

{{ news_item.link }}

---

{% endfor %}
{% endfor %}
{% endfor %}