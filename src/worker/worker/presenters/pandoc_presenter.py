import pypandoc
import tempfile

from .base_presenter import BasePresenter


class PANDOCPresenter(BasePresenter):
    type = "PANDOC_PRESENTER"
    name = "pandoc Presenter"
    description = "Presenter for generating .odt, .doc & .docx documents"

    def generate(self, product, template, parameters: dict[str, str] | None = None) -> str | bytes:
        if parameters is None:
            parameters = {}

        from_format = parameters.get("CONVERT_FROM")
        to_format = parameters.get("CONVERT_TO")
        if from_format is None:
            raise ValueError("No CONVERT_FROM parameter was set in ProductType")

        if to_format is None:
            raise ValueError("No CONVERT_TO parameter was set in ProductType")

        try:
            output_text = super().generate(product, template, parameters)

            with tempfile.NamedTemporaryFile(suffix=f".{to_format}") as tmp:
                pypandoc.convert_text(output_text, to_format, format=from_format, outputfile=tmp.name)
                tmp.seek(0)
                data = tmp.read()

            if data:
                return data
            raise ValueError("Could not convert template to docx")

        except Exception as error:
            BasePresenter.print_exception(self, error)
            raise ValueError(f"Document generation failed: {error}") from error
