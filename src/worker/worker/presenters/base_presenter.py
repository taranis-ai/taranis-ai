from worker.log import logger
import jinja2
import datetime


class BasePresenter:
    type = "BASE_PRESENTER"
    name = "Base Presenter"
    description = "Base abstract type for all presenters"

    def print_exception(self, error):
        logger.exception(f"[{self.name}] {error}")

    def generate(self, product: dict, template: str, parameters: dict[str, str] | None = None) -> str | bytes:
        if parameters is None:
            parameters = {}

        env = jinja2.Environment(
            autoescape=False,
            trim_blocks=True,
            lstrip_blocks=True,
            keep_trailing_newline=True,
            newline_sequence="\n",
            undefined=jinja2.StrictUndefined,
        )
        tmpl = env.from_string(template)
        product["current_date"] = datetime.datetime.now().strftime("%Y-%m-%d")

        return tmpl.render(data=product)
