from unittest.mock import Mock

import pytest
from flask import Flask, Response, make_response
from models.task import TaskSubmission

from core.config import Config
from core.managers import api_manager, auth_manager
from core.service.task import TaskService


@pytest.fixture(params=["/", "/taranis/"])
def contract_app(request, monkeypatch):
    monkeypatch.setattr(Config, "APPLICATION_ROOT", request.param)
    monkeypatch.setattr("core.api.auth.Config.APPLICATION_ROOT", request.param)
    application = Flask(__name__)
    application.config.from_object(Config)
    auth_manager.initialize(application)
    api_manager.initialize(application)
    return application


def test_task_contract_enforces_auth_then_input_and_output(contract_app, monkeypatch, api_header):
    save = Mock(return_value=({"id": "job", "result": {"message": "Done"}, "status": "SUCCESS"}, 200))
    monkeypatch.setattr(TaskService, "save_task_result", save)
    client = contract_app.test_client()
    url = f"{Config.APPLICATION_ROOT}api/tasks"

    assert client.post(url, json=[]).status_code == 401
    assert client.post(url, json=[], headers=api_header).status_code == 400
    save.assert_not_called()
    response = client.post(url, json={"id": "job", "result": {"message": "Done"}, "status": "SUCCESS"}, headers=api_header)
    assert response.status_code == 200
    assert isinstance(save.call_args.args[0], TaskSubmission)

    save.return_value = ({"secret": "must not escape"}, 200)
    response = client.post(url, json={"id": "job", "result": {"message": "Done"}, "status": "SUCCESS"}, headers=api_header)
    assert response.status_code == 500
    assert response.json == {"error": "Internal server error"}
    assert save.call_count == 2

    stream = Response(iter([b'{"private":"must not escape"}']), content_type="application/json")
    close = Mock()
    stream.call_on_close(close)
    save.return_value = stream
    response = client.post(url, json={"id": "job", "result": {"message": "Done"}, "status": "SUCCESS"}, headers=api_header)
    assert response.status_code == 500
    assert response.json == {"error": "Internal server error"}
    close.assert_called_once()


def test_valid_response_retains_headers_cookies_and_head(contract_app):
    def alive():
        response = make_response({"isalive": True})
        response.headers["X-Test"] = "preserved"
        response.set_cookie("first", "one")
        response.set_cookie("second", "two")
        return response

    contract_app.view_functions["isalive"] = alive
    client = contract_app.test_client()
    url = f"{Config.APPLICATION_ROOT}api/isalive"
    response = client.get(url)
    assert response.json == {"isalive": True}
    assert response.headers["X-Test"] == "preserved"
    assert len(response.headers.getlist("Set-Cookie")) == 2
    assert client.head(url).status_code == 200
    assert client.head(url).data == b""


def test_early_jwt_errors_are_validated(contract_app):
    client = contract_app.test_client()
    url = f"{Config.APPLICATION_ROOT}api/auth/refresh"
    response = client.get(url, headers={"Authorization": "Bearer malformed"})
    assert response.status_code == 422
    assert isinstance(response.json["msg"], str)

    contract_app.view_functions["auth.refresh"] = lambda: ({"error": "Unauthorized", "private": "invalid auth error"}, 401)
    response = client.get(url)
    assert response.status_code == 500
    assert response.json == {"error": "Internal server error"}


def test_conditional_downloads_keep_status_headers_and_stream_lifetime(contract_app, tmp_path):
    from flask import send_file

    path = tmp_path / "report.txt"
    path.write_bytes(b"published report")
    contract_app.view_functions["published_reports.published_report"] = lambda product_id: send_file(path, conditional=True)
    client = contract_app.test_client()
    url = f"{Config.APPLICATION_ROOT}reports/product"
    response = client.get(url)
    assert response.status_code == 200
    assert response.data == b"published report"
    assert "report.txt" in response.headers["Content-Disposition"]
    etag = response.headers["ETag"]
    response.close()
    unchanged = client.get(url, headers={"If-None-Match": etag})
    assert unchanged.status_code == 304 and unchanged.data == b""
    unchanged.close()
    partial = client.get(url, headers={"Range": "bytes=0-3"})
    assert partial.status_code == 206 and partial.data == b"publ"
    assert partial.headers["Content-Range"] == "bytes 0-3/16"
    partial.close()
    invalid = client.get(url, headers={"Range": "bytes=100-200"})
    assert invalid.status_code == 416
    assert invalid.json == {"error": "Requested Range Not Satisfiable"}
