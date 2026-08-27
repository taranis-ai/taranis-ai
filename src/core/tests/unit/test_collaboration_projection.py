from core.service.collaboration_projection import project_prosemirror, project_rich_text


def test_rich_text_projection_is_allowlisted_and_escaped():
    html, plain = project_rich_text(
        [
            {"insert": "<unsafe>", "attributes": {"bold": True}},
            {"insert": " link", "attributes": {"link": "javascript:alert(1)"}},
            {"insert": " safe", "attributes": {"link": "https://example.test/a?x=1&y=2"}},
        ]
    )
    assert html == '<strong>&lt;unsafe&gt;</strong> link<a href="https://example.test/a?x=1&amp;y=2" rel="noreferrer noopener"> safe</a>'
    assert plain == "<unsafe> link safe"


def test_prosemirror_projection_is_allowlisted_and_escaped():
    html, plain = project_prosemirror(
        {
            "type": "doc",
            "content": [
                {"type": "heading", "attrs": {"level": 2}, "content": [{"type": "text", "text": "<safe>", "marks": [{"type": "bold"}]}]},
                {
                    "type": "paragraph",
                    "content": [{"type": "text", "text": "x", "marks": [{"type": "link", "attrs": {"href": "javascript:alert(1)"}}]}],
                },
            ],
        }
    )
    assert html == "<h2><strong>&lt;safe&gt;</strong></h2><p>x</p>"
    assert plain == "<safe>\nx\n"
