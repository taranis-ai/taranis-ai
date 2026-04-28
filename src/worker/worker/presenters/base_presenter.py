import datetime

import jinja2
from jinja2.sandbox import ImmutableSandboxedEnvironment

from worker.log import logger


class BasePresenter:
    type = "BASE_PRESENTER"
    name = "Base Presenter"
    description = "Base abstract type for all presenters"

    def print_exception(self, error):
        logger.exception(f"[{self.name}] {error}")

    def generate(self, product: dict, template: str | None, parameters: dict[str, str] | None = None) -> str | bytes:
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
        product["current_date"] = datetime.datetime.now().strftime("%Y-%m-%d")

        logger.debug(f"[{self.name}] Rendering template with product data: {product} and parameters: {parameters}")
        return tmpl.render(data=product)
