from .base_presenter import BasePresenter


class JSONPresenter(BasePresenter):
    type = "JSON_PRESENTER"
    name = "JSON Presenter"
    description = "Presenter for generating JSON files"

    def generate(self, product: dict, template: str | None, parameters: dict[str, str] | None = None) -> bytes | str | None:
        if parameters is None:
            parameters = {}
        return super().generate(product, template, parameters)
