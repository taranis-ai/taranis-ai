from worker.log import logger
import jinja2
import datetime


class BasePresenter:
    type = "BASE_PRESENTER"
    name = "Base Presenter"
    description = "Base abstract type for all presenters"

    def print_exception(self, error):
        logger.log_debug_trace("[{0}] {1}".format(self.name, error))

    def generate(self, presenter_input, template) -> dict[str, bytes | str]:
        try:
            env = jinja2.Environment()
            tmpl = env.from_string(template)
            presenter_input["current_date"] = datetime.datetime.now().strftime("%Y-%m-%d")

            output_text = tmpl.render(data=presenter_input).encode("utf-8")

            return {"mime_type": presenter_input["mime_type"], "data": output_text}
        except Exception as error:
            BasePresenter.print_exception(self, error)
            return {"error": str(error)}
