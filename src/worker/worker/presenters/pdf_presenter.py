from weasyprint import HTML

from .base_presenter import BasePresenter


class PDFPresenter(BasePresenter):
    type = "PDF_PRESENTER"
    name = "PDF Presenter"
    description = "Presenter for generating PDF documents"

    def generate(self, product, template) -> str | bytes:
        try:
            output_text = super().generate(product, template)

            html = HTML(string=output_text)

            if data := html.write_pdf(target=None):
                return data

            raise ValueError("PDF generation failed: No data returned")

        except Exception as error:
            BasePresenter.print_exception(self, error)
            raise ValueError(f"PDF generation failed: {error}") from error
