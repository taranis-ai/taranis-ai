from weasyprint import HTML

from .base_presenter import BasePresenter


class PDFPresenter(BasePresenter):
    type = "PDF_PRESENTER"
    name = "PDF Presenter"
    description = "Presenter for generating PDF documents"

    @staticmethod
    def _remove_weasyprint_signature(_document, pdf) -> None:
        pdf.info.pop("Producer", None)

    def generate(self, product: dict, template: str, parameters: dict[str, str] | None = None) -> str | bytes:
        if parameters is None:
            parameters = {}

        output_text = super().generate(product, template, parameters)

        try:
            html = HTML(string=output_text)
            data = html.write_pdf(target=None, finisher=self._remove_weasyprint_signature)
        except Exception as error:
            BasePresenter.print_exception(self, error)
            raise ValueError(f"PDF generation failed: {error}") from error

        if not data:
            raise ValueError("PDF generation failed: No data returned")

        return data
