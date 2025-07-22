from html2docx import HTML2Docx
from io import BytesIO

from .base_presenter import BasePresenter


class DOCXPresenter(BasePresenter):
    type = "DOCX_PRESENTER"
    name = "Docx Presenter"
    description = "Presenter for generating DOCX documents"

    def generate(self, product, template) -> str | bytes:
        try:
            output_text = super().generate(product, template)

            parser = DOCXParser()
            parser.feed(output_text.strip())

            buf = BytesIO()
            parser.doc.save(buf)

            if data := buf.getvalue():
                return data
            raise ValueError("DOCX generation failed: No data returned")

        except Exception as error:
            BasePresenter.print_exception(self, error)
            raise ValueError(f"DOCX generation failed: {error}") from error


class DOCXParser(HTML2Docx):
    def __init__(self, title: str = ""):
        super().__init__(title)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            level = int(tag[-1]) - 1
            self.p = self.doc.add_heading(level=level)
            return
        super().handle_starttag(tag, attrs)
