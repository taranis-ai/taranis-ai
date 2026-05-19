import datetime
from pathlib import Path

import jinja2
from flask import Flask
from werkzeug.utils import secure_filename

example_product = {
    "id": 1,
    "mime_type": "application/pdf",
    "report_items": [
        {
            "id": "1",
            "title": "😮 Test Report 😮",
            "created": "2024-03-20T12:29:22.944963",
            "last_updated": "2024-03-20T12:29:22.944971",
            "completed": True,
            "user_id": 1,
            "attributes": {
                "Data": {
                    "date": "1.1.1970",
                    "timeframe": "1.1.1970 - 19.1.2038",
                    "news": "1",
                    "vulnerabilities": "2,3",
                }
            },
            "stories": [
                {
                    "id": "1",
                    "title": "This is the first news item Title",
                    "description": "",
                    "created": "2024-02-20T08:20:09",
                    "read": False,
                    "important": False,
                    "likes": 0,
                    "dislikes": 0,
                    "relevance": 0,
                    "comments": "",
                    "summary": "",
                    "news_items": [
                        {
                            "id": "a0e322c5-220a-4002-8c02-57b95e33f646",
                            "title": "😉",
                            "author": "THE BEST AUTHOR",
                            "source": "http://testsource",
                            "link": "https://testsource/2024/02/20/",
                            "content": " 😉 😉 😉 ",
                            "collected": "2024-03-20T12:29:39.119037",
                            "published": "2024-02-20T08:20:09",
                            "updated": "2024-03-20T12:09:49.719305",
                            "attributes": [],
                        }
                    ],
                    "tags": [],
                },
                {
                    "id": "2",
                    "title": "This is the second 😈",
                    "description": "",
                    "created": "2024-02-20T08:20:09",
                    "read": False,
                    "important": False,
                    "likes": 0,
                    "dislikes": 0,
                    "relevance": 0,
                    "comments": "",
                    "summary": "",
                    "news_items": [
                        {
                            "id": "a0e322c5-220a-4002-8c02-57b95e33f646",
                            "title": "😈",
                            "author": "THE BEST AUTHOR",
                            "source": "http://testsource",
                            "link": "https://testsource/2024/04/20/",
                            "content": " 😈 😈 😈 ",
                            "collected": "2024-03-20T12:29:39.119037",
                            "published": "2024-02-20T08:20:09",
                            "updated": "2024-03-20T12:09:49.719305",
                            "attributes": [],
                        }
                    ],
                    "tags": [],
                },
                {
                    "id": "3",
                    "title": "This is the third 😎",
                    "description": "",
                    "created": "2024-02-20T08:20:09",
                    "read": False,
                    "important": False,
                    "likes": 0,
                    "dislikes": 0,
                    "relevance": 0,
                    "comments": "",
                    "summary": "",
                    "news_items": [
                        {
                            "id": "a0e322c5-220a-4002-8c02-57b95e33f646",
                            "title": "😎",
                            "author": "THE BEST AUTHOR",
                            "source": "http://testsource",
                            "link": "https://testsource/2024/03/30/",
                            "content": " 😎 😎 😎 ",
                            "collected": "2024-03-20T12:29:39.119037",
                            "published": "2024-02-20T08:20:09",
                            "updated": "2024-03-20T12:09:49.719305",
                            "attributes": [],
                        }
                    ],
                    "tags": [],
                },
            ],
        }
    ],
}


app = Flask(__name__)


def _resolve_template_path(template_path: str) -> Path:
    template_name = secure_filename(template_path)
    if not template_name or template_name != template_path:
        raise ValueError("Invalid template path")
    base_path = Path.cwd().resolve()
    resolved_path = (base_path / template_name).resolve(strict=True)
    if resolved_path.parent != base_path:
        raise ValueError("Invalid template path")
    return resolved_path


@app.route("/", defaults={"template_path": "template.html"})
@app.route("/<path:template_path>")
def render(template_path):
    try:
        template = _resolve_template_path(template_path).read_text(encoding="utf-8")
    except ValueError:
        return {"error": "Invalid template path"}, 400
    except FileNotFoundError:
        return {"error": "Template file not found."}, 404
    except Exception:
        return {"error": "Unable to read template file"}, 500
    return generate(example_product, template)


def generate(product, template, parameters: dict[str, str] | None = None) -> dict[str, bytes | str]:
    if parameters is None:
        parameters = {}

    try:
        env = jinja2.Environment(autoescape=False)
        tmpl = env.from_string(template)
        product["current_date"] = datetime.datetime.now().strftime("%Y-%m-%d")

        return tmpl.render(data=product).encode("utf-8")
    except Exception:
        return {"error": "Template rendering failed"}


if __name__ == "__main__":
    app.run(port=5000, extra_files=["template.html"])
