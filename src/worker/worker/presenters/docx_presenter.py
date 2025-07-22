import pypandoc
import tempfile

from .base_presenter import BasePresenter


class DOCXPresenter(BasePresenter):
    type = "DOCX_PRESENTER"
    name = "Docx Presenter"
    description = "Presenter for generating DOCX documents"

    def generate(self, product, template) -> str | bytes:
        try:
            output_text = super().generate(product, template)

            with tempfile.NamedTemporaryFile(suffix=".docx") as tmp:
                pypandoc.convert_text(output_text, "docx", format="html", outputfile=tmp.name)
                tmp.seek(0)
                data = tmp.read()

            if data:
                return data
            raise ValueError("Could not convert template to docx")

        except Exception as error:
            BasePresenter.print_exception(self, error)
            raise ValueError(f"DOCX generation failed: {error}") from error
