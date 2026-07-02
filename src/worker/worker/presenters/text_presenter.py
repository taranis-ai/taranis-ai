from .base_presenter import BasePresenter


class TextPresenter(BasePresenter):
    type = "TEXT_PRESENTER"
    name = "TEXT Presenter"
    description = "Presenter for generating text documents"

    def generate(self, product: dict, template: str | None, parameters: dict[str, str] | None = None) -> str | bytes | None:
        if parameters is None:
            parameters = {}
        return super().generate(product, template, parameters)
