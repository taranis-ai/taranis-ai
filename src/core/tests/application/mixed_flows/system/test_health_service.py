import pytest

from core.service import health


@pytest.mark.parametrize(
    ("manual_exists", "product_type_exists", "expected"),
    [
        (True, True, "up"),
        (False, True, "down"),
        (True, False, "down"),
        (False, False, "down"),
    ],
)
def test_check_seed_data(monkeypatch, manual_exists, product_type_exists, expected):
    monkeypatch.setattr("core.model.osint_source.OSINTSource.get_by_key", lambda key: object() if manual_exists else None)
    monkeypatch.setattr("core.model.product_type.ProductType.get_first", lambda query: object() if product_type_exists else None)

    assert health.check_seed_data() == expected


def test_endpoint_health_lifecycle(client, auth_header, api_header, app, db_persistent_session, redis_client):
    from copy import deepcopy

    from rq import Worker
    from rq.job import Job

    from core.model.bot import Bot
    from core.model.settings import Settings
    from core.service.endpoint_health import read_state

    session = db_persistent_session
    with app.app_context():
        original_settings = deepcopy(Settings.get_settings_entry().settings)
        original_bots = {bot.id: bot.enabled for bot in session.query(Bot).all()}
        # Isolate configured endpoints while exercising real persistence and RQ dispatch.
        session.query(Bot).update({Bot.enabled: False})
        Settings.get_settings_entry().settings = Settings.with_defaults({})
        session.commit()
        worker = Worker(["misc"], connection=redis_client)
        worker.register_birth()

        try:
            endpoint = {"name": "Health test", "base_url": "https://model.example/v1", "api_key": "private-health-key"}
            response = client.post("/api/settings/llm-endpoints", json=endpoint, headers=auth_header)
            assert response.status_code == 200
            endpoint_id = response.json["id"]
            state = read_state("llm", endpoint_id)
            jobs = [Job.fetch(job_id, connection=redis_client) for job_id in app.extensions["rq"].get_queue("misc").job_ids]
            job = next(job for job in jobs if job.func_name == "worker.endpoint_health.check_endpoint" and job.args[1] == endpoint_id)
            assert job.retry_intervals == [10, 30, 120, 300]
            assert "private-health-key" not in str(job.args)
            route = f"/api/worker/endpoint-health/llm/{endpoint_id}"
            assert client.get(route).status_code == 401
            snapshot = client.get(route, query_string={"check_id": state["check_id"]}, headers=api_header)
            assert snapshot.headers["Cache-Control"] == "no-store"
            assert snapshot.json["config"]["api_key"] == endpoint["api_key"]
            assert client.get("/api/health").json["services"]["worker_endpoints"] == "down"

            result = {"check_id": state["check_id"], "healthy": False}
            assert client.post(route, json=result, headers=api_header).json == {"accepted": True}
            public = client.get("/api/settings/settings", headers=auth_header)
            assert "private-health-key" not in public.text
            assert public.json["items"][0]["settings"]["llm_endpoints"][endpoint_id]["health"]["status"] == "down"
            assert client.get("/api/health").status_code == 503

            response = client.post(
                "/api/config/bots",
                json={"name": "Summary health", "type": "summary_bot", "parameters": {"LLM_ENDPOINT": endpoint_id}},
                headers=auth_header,
            )
            assert response.status_code == 201
            bot_id = response.json["id"]
            assert client.get(f"/api/config/bots/{bot_id}", headers=auth_header).json["endpoint_health"]["status"] == "down"
            failures = client.get("/api/config/bots?state=failure", headers=auth_header).json["items"]
            assert bot_id in {bot["id"] for bot in failures}

            result["healthy"] = True
            assert client.post(route, json=result, headers=api_header).json == {"accepted": True}
            assert client.get("/api/health").status_code == 200
            assert client.get(f"/api/config/bots/{bot_id}", headers=auth_header).json["endpoint_health"]["status"] == "up"
            # Startup rechecks and edits each invalidate results from older check runs.
            app.extensions["rq"].post_init()
            assert read_state("llm", endpoint_id)["check_id"] != state["check_id"]
            assert client.post(route, json=result, headers=api_header).json == {"accepted": False}
            assert client.get(route, query_string={"check_id": state["check_id"]}, headers=api_header).json == {"skip": True}
            assert (
                client.post(f"/api/settings/llm-endpoints/{endpoint_id}", json={"model": "new-model"}, headers=auth_header).status_code == 200
            )
            current = read_state("llm", endpoint_id)
            assert current["status"] == "pending"
            assert client.post(route, json={"check_id": current["check_id"], "healthy": True}, headers=api_header).json["accepted"]

            for bot_type in ("nlp_bot", "sentiment_analysis_bot", "cybersec_classifier_bot"):
                response = client.post(
                    "/api/config/bots",
                    json={"name": bot_type, "type": bot_type, "parameters": {"LLM_ENDPOINT": endpoint_id}},
                    headers=auth_header,
                )
                assert response.status_code == 201
                shared_bot_id = response.json["id"]
                shared_route = f"/api/config/bots/{shared_bot_id}"
                assert client.get(shared_route, headers=auth_header).json["endpoint_health"]["status"] == "up"
                assert read_state("bot", shared_bot_id) == {}
                client.patch(shared_route, json={"enabled": False}, headers=auth_header)
                assert client.get(shared_route, headers=auth_header).json["endpoint_health"] is None
        finally:
            for bot in session.query(Bot).all():
                if bot.id not in original_bots:
                    Bot.delete(bot.id)
                else:
                    bot.enabled = original_bots[bot.id]
            Settings.get_settings_entry().settings = original_settings
            session.commit()
            worker.register_death()


@pytest.mark.parametrize("failed_service", ["worker_endpoints", "database", "seed_data", "broker", "workers"])
def test_core_process_probe_keeps_endpoint_failures_repairable(monkeypatch, failed_service):
    import json

    import requests

    from core.healthcheck import main

    services = dict.fromkeys(("database", "seed_data", "broker", "workers", "worker_endpoints"), "up")
    services[failed_service] = "down"
    response = requests.Response()
    response.status_code = 503
    response._content = json.dumps({"healthy": False, "services": services}).encode()
    monkeypatch.setattr("core.healthcheck.requests.get", lambda *args, **kwargs: response)
    assert main() == (0 if failed_service == "worker_endpoints" else 1)
