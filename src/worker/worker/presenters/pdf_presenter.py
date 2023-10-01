from weasyprint import HTML

from .base_presenter import BasePresenter


class PDFPresenter(BasePresenter):
    type = "PDF_PRESENTER"
    name = "PDF Presenter"
    description = "Presenter for generating PDF documents"

    def generate(self, presenter_input, template) -> dict[str, str | bytes]:
        try:
            output_text = super().generate(presenter_input, template)

            html = HTML(string=output_text["data"])

            if data := html.write_pdf(target=None):
                return {"mime_type": "application/pdf", "data": data}

            return {"error": "Could not generate PDF"}

        except Exception as error:
            BasePresenter.print_exception(self, error)
            return {"error": str(error)}
