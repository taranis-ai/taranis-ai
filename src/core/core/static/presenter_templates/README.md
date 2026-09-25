# Data Folder Management

This system facilitates the handling of presenter templates, including synchronization, addition, retrieval, and deletion of templates stored in a specific directory designated by the Config.DATA_FOLDER configuration.


## Presenter Templates Synchronization
The sync_presenter_templates_to_data method synchronizes presenter templates from a source directory (typically a folder inside your venv) to a destination directory within the Config.DATA_FOLDER. This synchronization process includes:

1. Source and Destination Paths: Identifies the source (static/presenter_templates) and destination (Config.DATA_FOLDER/presenter_templates) paths.
1. Hash File Management: Reads and updates a JSON file (template_hashes.json) that stores the hashes of the templates. This file is used to track changes to the templates.
1. File Copy and Hash Update: Copies each template from the source to the destination if it does not exist in the destination or if its content has changed (detected via hash comparison). Updates the hash file accordingly.

## Analyst HTML in story summaries

Analysts with permission to edit Stories may write HTML in a Story summary. Product template authors can include that formatting in generated HTML products. For example, an analyst can enter `<strong>Confirmed</strong> by two sources`, and an HTML presenter template can render it with:

```jinja2
{% for story in data.report_items[0].stories %}
<div class="story-summary">{{ story.summary }}</div>
{% endfor %}
```

The rendered product then contains the `<strong>` element. Templates that apply `|e` to the summary instead display the tags as text; choose that only when plain text is wanted. Do not strip or escape every summary as a general rule, because this HTML is an intended analyst feature. Keep values from other sources, such as news item content and URLs, in their appropriate escaped or validated context.

The Assess Story card escapes summary text when displaying it in the application. Product formatting is controlled separately by the chosen presenter template.

`ImmutableSandboxedEnvironment` restricts what server-side Jinja expressions can do; it does not sanitize HTML or make every rendered product safe. The product preview uses a sandboxed iframe. Published products are served with a separate sandbox Content Security Policy and `nosniff` header. These browser boundaries are separate from the Jinja sandbox. Template path and sandbox hardening is tracked in [#780](https://github.com/taranis-ai/taranis-ai/pull/780).
