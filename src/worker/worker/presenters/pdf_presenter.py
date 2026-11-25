from weasyprint import HTML
from weasyprint.urls import URLFetcher, URLFetcherResponse, URLFetchingError

from .base_presenter import BasePresenter


class _BlockedResource(URLFetcherResponse):
    def read(self, *args, **kwargs):
        # WeasyPrint 70 handles color profile errors while reading the response.
        raise URLFetchingError("PDF resource fetching is disabled")


class _DisabledURLFetcher(URLFetcher):
    def fetch(self, url, headers=None):
        return _BlockedResource("about:blank")


class PDFPresenter(BasePresenter):
    type = "PDF_PRESENTER"
    name = "PDF Presenter"
    description = "Presenter for generating PDF documents"

    @staticmethod
    def _remove_weasyprint_signature(_document, pdf) -> None:
        pdf.info.pop("Producer", None)

    def generate(self, product: dict, template: str | None, parameters: dict[str, str] | None = None) -> str | bytes | None:
        if parameters is None:
            parameters = {}

        output_text = super().generate(product, template, parameters)

        try:
            html = HTML(string=output_text, url_fetcher=_DisabledURLFetcher())
            data = html.write_pdf(target=None, finisher=self._remove_weasyprint_signature)
        except Exception as error:
            BasePresenter.print_exception(self, error)
            raise ValueError("PDF generation failed") from error

        if not data:
            raise ValueError("PDF generation failed: No data returned")

        return data
