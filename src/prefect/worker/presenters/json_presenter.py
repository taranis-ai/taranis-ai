from .base_presenter import BasePresenter


class JSONPresenter(BasePresenter):
    type = "JSON_PRESENTER"
    name = "JSON Presenter"
    description = "Presenter for generating JSON files"

    def generate(self, product, template) -> dict[str, bytes | str]:
        return super().generate(product, template)
