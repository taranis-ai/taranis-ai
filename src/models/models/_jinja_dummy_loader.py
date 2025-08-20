from jinja2 import BaseLoader


class DummyLoader(BaseLoader):
    """A loader that returns an empty template for any requested name.

    This allows validating templates using {% include %} or {% extends %}
    without requiring actual template files on disk.
    Intended for runtime validation only; not test data.
    """

    def get_source(self, environment, template):  # type: ignore[override]
        return "", template, lambda: True
