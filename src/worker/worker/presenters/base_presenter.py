import datetime
from html import escape

import jinja2
from jinja2.sandbox import ImmutableSandboxedEnvironment

from worker.log import logger


class BasePresenter:
    type = "BASE_PRESENTER"
    name = "Base Presenter"
    description = "Base abstract type for all presenters"

    def print_exception(self, error):
        logger.exception(f"[{self.name}] {error}")

    def generate(self, product: dict, template: str | None, parameters: dict[str, str] | None = None) -> str | bytes | None:
        if parameters is None:
            parameters = {}

        if not template:
            self.print_exception("No template provided")
            raise ValueError("No template provided to BasePresenter.generate()")

        env = ImmutableSandboxedEnvironment(
            autoescape=False,
            trim_blocks=True,
            lstrip_blocks=True,
            keep_trailing_newline=True,
            newline_sequence="\n",
            undefined=jinja2.StrictUndefined,
        )
        tmpl = env.from_string(template)
        product["current_date"] = datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%d")

        rendered = tmpl.render(data=product)
        if self.type in {"PDF_PRESENTER", "HTML_PRESENTER"}:
            figures = []
            for report in product.get("report_items", []):
                for figure in report.get("figures", []):
                    src, alt, caption, url, credit = (escape(figure[k], quote=True) for k in ("src", "alt", "caption", "url", "credit"))
                    figures.append(
                        f'<figure style="break-inside:avoid"><img style="max-width:100%;max-height:70vh" src="{src}" alt="{alt}">'
                        f'<figcaption>{caption} <a href="{url}">{credit}</a></figcaption></figure>'
                    )
            if figures:
                index = rendered.lower().rfind("</body>")
                index = index if index >= 0 else len(rendered)
                rendered = rendered[:index] + "".join(figures) + rendered[index:]
        return rendered
