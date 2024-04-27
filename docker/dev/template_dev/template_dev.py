from flask import Flask
import jinja2
import datetime

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
                "date": "1.1.1970",
                "timeframe": "1.1.1970 - 19.1.2038",
                "news": "1",
                "vulnerabilities": "2,3",
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


@app.route("/", defaults={"template_path": "template.html"})
@app.route("/<path:template_path>")
def render(template_path):
    try:
        # Attempt to open the specified file; use default if not provided
        template = open(template_path, "r").read()
    except FileNotFoundError:
        return {"error": f"Template file {template_path} not found."}, 404
    except Exception as error:
        return {"error": str(error)}, 500
    return generate(example_product, template)


def generate(product, template) -> dict[str, bytes | str]:
    try:
        env = jinja2.Environment(autoescape=False)
        tmpl = env.from_string(template)
        product["current_date"] = datetime.datetime.now().strftime("%Y-%m-%d")

        return tmpl.render(data=product).encode("utf-8")
    except Exception as error:
        return {"error": str(error)}


if __name__ == "__main__":
    app.run(debug=True, port=5000, extra_files=["template.html"])
