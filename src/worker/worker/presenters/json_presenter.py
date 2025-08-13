from .base_presenter import BasePresenter


class JSONPresenter(BasePresenter):
    type = "JSON_PRESENTER"
    name = "JSON Presenter"
    description = "Presenter for generating JSON files"

    def generate(self, product: dict, template: str, parameters: dict[str, str] | None = None) -> bytes | str:
        if parameters is None:
            parameters = {}
        return super().generate(product, template, parameters)
