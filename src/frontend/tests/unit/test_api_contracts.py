import re

import pytest
from flask import Flask
from models.frontend_api import OPERATIONS

from frontend.router import base


@pytest.mark.parametrize("prefix", ["/", "/taranis/"])
def test_structured_frontend_routes_have_executable_contracts(prefix):
    app = Flask(__name__)
    app.config["APPLICATION_ROOT"] = prefix
    base.init(app)
    found = set()
    for rule in app.url_map.iter_rules():
        path = "/" + rule.rule.removeprefix(prefix)
        path = re.sub(r"<(?:[^:<>]+:)?([^<>]+)>", r"{\1}", path)
        view = app.view_functions[rule.endpoint]
        for method in rule.methods - {"HEAD", "OPTIONS"}:
            operation = next((op for op in OPERATIONS if op.match(method, path) is not None), None)
            if operation is None:
                continue
            handler = getattr(getattr(view, "view_class", None), method.lower(), view)
            assert getattr(handler, "api_request_validated", False), (method, path)
            operation.parameters.model_json_schema()
            if operation.body:
                operation.body.json_schema()
            for response in operation.responses.values():
                response.body.json_schema()
            found.add((method, path))
    assert found == {(op.method, op.path) for op in OPERATIONS}
