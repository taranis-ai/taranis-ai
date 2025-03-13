from .base_presenter import BasePresenter


class TextPresenter(BasePresenter):
    type = "TEXT_PRESENTER"
    name = "TEXT Presenter"
    description = "Presenter for generating text documents"

    def generate(self, product, template) -> dict[str, bytes | str]:
        return super().generate(product, template)
