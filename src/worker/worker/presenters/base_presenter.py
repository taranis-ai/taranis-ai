from worker.log import logger
import jinja2
import datetime


class BasePresenter:
    type = "BASE_PRESENTER"
    name = "Base Presenter"
    description = "Base abstract type for all presenters"

    def print_exception(self, error):
        logger.exception(f"[{self.name}] {error}")

    def generate(self, product, template) -> str | bytes:
        env = jinja2.Environment(autoescape=False)
        tmpl = env.from_string(template)
        product["current_date"] = datetime.datetime.now().strftime("%Y-%m-%d")

        return tmpl.render(data=product)
