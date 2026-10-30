"""Explicit production workflows; discovering a route never invents a success case."""

import json
from dataclasses import dataclass, field, replace
from pathlib import Path

from tests.performance.orm.dataset import article, identifier


@dataclass(frozen=True)
class Scenario:
    id: str
    rule: str
    method: str = "GET"
    url: str = ""
    auth: str = "user"
    body: object = None
    status: int = 200
    changes_state: bool = False
    requires: tuple[str, ...] = ()
    operation: str = "http"
    batch: int = 0
    variant: str = "normal"
    paged: bool = False
    profile_status: dict[str, int] = field(default_factory=dict)
    transport: str = ""
    request_headers: dict = field(default_factory=dict)


def scenarios():
    cases = []
    for name, url in {
        "assess.stories": "/api/assess/stories",
        "assess.filters": "/api/assess/filter-lists",
        "assess.tags": "/api/assess/taglist",
        "assess.news": "/api/assess/news-items",
        "assess.sources": "/api/assess/osint-sources-list",
        "assess.groups": "/api/assess/osint-source-group-list",
        "assess.bookmarks": "/api/assess/bookmarks",
        "assess.review": "/api/assess/analyst-review/snapshot",
        "assess.connectors": "/api/assess/connectors",
        "assess.proposals": "/api/assess/connectors/proposals",
        "analyze.reports": "/api/analyze/report-items",
        "analyze.types": "/api/analyze/report-types",
        "publish.products": "/api/publish/products",
        "publish.types": "/api/publish/product-types",
        "publish.choices": "/api/publish/product-choices",
        "publish.type-choices": "/api/publish/product-type-choices",
        "publish.presets": "/api/publish/publisher-presets",
        "assets.list": "/api/assets",
        "assets.groups": "/api/asset-groups",
        "assets.cti": "/api/assets/cti",
        "dashboard.summary": "/api/dashboard",
        "dashboard.names": "/api/dashboard/cluster-names",
        "dashboard.trending": "/api/dashboard/trending-clusters",
        "dashboard.stories": "/api/dashboard/story-clusters",
        "tasks.user": "/api/tasks/user",
    }.items():
        auth = "admin" if name.startswith("assets.") or name in {"assess.connectors", "assess.proposals"} else "user"
        cases.append(
            Scenario(
                name,
                url,
                url=url,
                auth=auth,
                paged=name
                in {
                    "assess.stories",
                    "assess.news",
                    "assess.bookmarks",
                    "analyze.reports",
                    "publish.products",
                    "assets.list",
                    "assets.groups",
                },
            )
        )
    for resource in (
        "acls",
        "attributes",
        "bots",
        "organizations",
        "osint-sources",
        "osint-source-groups",
        "permissions",
        "product-types",
        "templates",
        "publishers-presets",
        "report-item-types",
        "roles",
        "users",
        "word-lists",
        "connectors",
    ):
        url = f"/api/config/{resource}"
        cases.append(Scenario(f"config.{resource}", url, url=url, auth="admin", paged=resource not in {"permissions", "templates"}))
    for resource in ("osint-sources", "bots", "word-lists"):
        url = f"/api/worker/{resource}"
        cases.append(Scenario(f"worker.{resource}", url, url=url, auth="worker"))
    cases.extend(
        [
            Scenario("tasks.history", "/api/tasks", url="/api/tasks", auth="worker"),
            Scenario("tasks.runs", "/api/tasks/runs", url="/api/tasks/runs", auth="worker"),
            Scenario("assess.story", "/api/assess/stories/<string:story_id>", url="/api/assess/stories/{story_id}", requires=("story_id",)),
            Scenario(
                "assess.story-cti",
                "/api/assess/stories/<string:story_id>/cti",
                url="/api/assess/stories/{story_id}/cti",
                requires=("story_id",),
            ),
            Scenario(
                "assess.news-detail",
                "/api/assess/news-items/<string:item_id>",
                url="/api/assess/news-items/{news_item_id}",
                requires=("news_item_id",),
            ),
            Scenario(
                "assess.revisions",
                "/api/assess/stories/<string:story_id>/revisions",
                url="/api/assess/stories/{story_id}/revisions",
                requires=("story_id",),
            ),
            Scenario(
                "assess.export", "/api/assess/stories/export", url="/api/assess/stories/export?story_ids={story_id}", requires=("story_id",)
            ),
            Scenario(
                "analyze.report",
                "/api/analyze/report-items/<string:report_item_id>",
                url="/api/analyze/report-items/{report_item_id}",
                requires=("report_item_id",),
            ),
            Scenario(
                "analyze.editor",
                "/api/analyze/report-editors/<string:report_item_id>",
                url="/api/analyze/report-editors/{report_item_id}",
                requires=("report_item_id",),
            ),
            Scenario(
                "analyze.revisions",
                "/api/analyze/report-items/<string:report_item_id>/revisions",
                url="/api/analyze/report-items/{report_item_id}/revisions",
                requires=("report_item_id",),
            ),
            Scenario(
                "publish.detail",
                "/api/publish/products/<string:product_id>",
                url="/api/publish/products/{product_id}",
                requires=("product_id",),
            ),
            Scenario("assets.detail", "/api/assets/<string:asset_id>", url="/api/assets/{asset_id}", auth="admin", requires=("asset_id",)),
            Scenario("worker.source", "/api/worker/osint-sources/<string:source_id>", url="/api/worker/osint-sources/manual", auth="worker"),
            Scenario(
                "worker.report",
                "/api/worker/report-items/<string:report_id>",
                url="/api/worker/report-items/{report_item_id}",
                auth="worker",
                requires=("report_item_id",),
            ),
            Scenario(
                "config.organization-create",
                "/api/config/organizations",
                "POST",
                "/api/config/organizations",
                "admin",
                {"id": identifier("new-org"), "name": "ORM created organization"},
                201,
                True,
            ),
            Scenario(
                "config.organization-update",
                "/api/config/organizations/<string:organization_id>",
                "PUT",
                "/api/config/organizations/{organization_id}",
                "admin",
                {"name": "ORM renamed organization"},
                200,
                True,
                ("organization_id",),
            ),
            Scenario(
                "config.organization-delete",
                "/api/config/organizations/<string:organization_id>",
                "DELETE",
                "/api/config/organizations/{deletable_org_id}",
                "admin",
                changes_state=True,
                requires=("deletable_org_id",),
            ),
            Scenario(
                "worker.task-result",
                "/api/tasks",
                "POST",
                "/api/tasks",
                "worker",
                {"id": "orm-result", "status": "SUCCESS", "task": "profile", "result": {"message": "profile", "data": {}}},
                status=200,
                changes_state=True,
            ),
            Scenario(
                "worker.cleanup",
                "/api/worker/tasks/history/cleanup",
                "POST",
                "/api/worker/tasks/history/cleanup",
                "worker",
                changes_state=True,
            ),
            Scenario("serialization.story", "core.model.story.Story.to_dict", operation="serialize-story", requires=("story_id",)),
            Scenario(
                "serialization.report",
                "core.model.report_item.ReportItem.to_detail_dict",
                operation="serialize-report",
                requires=("report_item_id",),
            ),
            Scenario("startup.existing", "core.create_app", operation="startup", changes_state=True),
            Scenario("cli.roles", "core.cli.set_roles_command", operation="cli-roles", changes_state=True),
            Scenario("cli.password", "core.cli.set_password_command", operation="cli-password", changes_state=True),
            Scenario(
                "housekeeping.cleanup-token-blacklist",
                "core.managers.auth_manager.cleanup_token_blacklist",
                operation="housekeeping-token-cleanup",
                changes_state=True,
            ),
        ]
    )
    for size in (1, 10, 100, 1000):
        cases.append(
            Scenario(
                f"worker.ingest-{size}",
                "/api/worker/news-items",
                "POST",
                "/api/worker/news-items",
                "worker",
                [{**article(index, prefix="ingest"), "osint_source_id": "{collector_id}"} for index in range(size)],
                changes_state=True,
                batch=size,
            )
        )
    cases.extend(
        [
            Scenario("assess.no-result", "/api/assess/stories", url="/api/assess/stories?search=absent-profile-phrase", variant="no-result"),
            Scenario(
                "assess.invalid", "/api/assess/stories", "POST", "/api/assess/stories", body={"story_ids": [1]}, status=400, variant="invalid"
            ),
            Scenario("worker.invalid", "/api/worker/news-items", "POST", "/api/worker/news-items", "worker", {}, 400, variant="invalid"),
            Scenario(
                "assess.missing",
                "/api/assess/stories/<string:story_id>",
                url="/api/assess/stories/{missing}",
                status=404,
                variant="no-result",
            ),
            Scenario(
                "assess.rollback",
                "/api/assess/stories",
                "POST",
                "/api/assess/stories",
                body={"story_ids": ["{story_id}", "{missing}"], "payload": {"read": True}},
                status=404,
                changes_state=True,
                requires=("story_id",),
                variant="rollback",
            ),
        ]
    )
    for specification in json.loads(Path(__file__).with_name("scenarios-v1.json").read_text()):
        specification["requires"] = tuple(specification.get("requires", ()))
        cases.append(Scenario(**specification))
    # Authentication failures are distinct scenarios, never substitutes for normal reads/writes.
    cases.extend(
        replace(
            case,
            id=f"{case.id}.denied",
            auth="none",
            status=403 if case.id == "realtime.connect" else 401,
            variant="denied",
            changes_state=False,
        )
        for case in list(cases)
        if case.operation == "http" and case.auth != "none" and not case.requires and case.variant == "normal" and not case.batch
    )
    return cases


def substitute(value, ids):
    if isinstance(value, str):
        if value.startswith("{") and value.endswith("}") and value[1:-1] in ids:
            return ids[value[1:-1]]
        return value.format_map(ids)
    if isinstance(value, list):
        return [substitute(item, ids) for item in value]
    if isinstance(value, dict):
        return {substitute(key, ids): substitute(item, ids) for key, item in value.items()}
    return value


def invocation(case, environment):
    from core import create_app
    from core.cli import main
    from core.model.report_item import ReportItem
    from core.model.story import Story

    if case.operation == "startup":
        return lambda: create_app()
    if case.operation == "housekeeping-token-cleanup":
        from core.managers.auth_manager import cleanup_token_blacklist

        return lambda: cleanup_token_blacklist(environment.app)
    if case.operation.startswith("cli-"):
        args = ["set-roles", "user", "User"] if case.operation == "cli-roles" else ["set-password", "user", "--password-stdin"]

        def cli():
            result = environment.app.test_cli_runner().invoke(main, args, input="profiling-password\n")
            if result.exit_code:
                raise RuntimeError("CLI profiling invocation failed")
            return result.output

        return cli
    if case.operation.startswith("serialize-"):
        model, key = (Story, "story_id") if case.operation == "serialize-story" else (ReportItem, "report_item_id")
        item = model.get(environment.dataset.ids[key])
        serializer = item.to_dict if case.operation == "serialize-story" else item.to_detail_dict
        # Warm the graph in this session; the collector still reports residual serializer SQL.
        serializer()
        return serializer
    url = substitute(case.url, environment.dataset.ids)
    if case.paged and environment.dataset.profile != "snapshot":
        limit = max(1, environment.dataset.manifest["profiles"][environment.dataset.profile]["roots"])
        url += ("&" if "?" in url else "?") + f"limit={limit}"
    body = substitute(case.body, environment.dataset.ids)
    headers = environment.headers[case.auth]
    client = environment.app.test_client()

    def http():
        request_headers = {**headers, **substitute(case.request_headers, environment.dataset.ids)}
        request_data = None
        content_type = None
        if case.transport == "icon":
            from io import BytesIO

            request_data = {"file": (BytesIO(b"invalid profiling icon"), "profile.png")}
            content_type = "multipart/form-data"
        if case.id == "realtime.connect":
            from core.config import Config

            request_headers["X-Realtime-Proxy-Key"] = Config.CENTRIFUGO_CONNECT_PROXY_SECRET.get_secret_value()
            token = environment.headers["user"]["Authorization"].removeprefix("Bearer ")
            request_headers["Cookie"] = f"{Config.JWT_ACCESS_COOKIE_NAME}={token}"
        response = client.open(url, method=case.method, json=body, data=request_data, content_type=content_type, headers=request_headers)
        response.get_data()  # Include streamed/export payload consumption in the invocation.
        expected = case.profile_status.get(environment.dataset.profile, case.status) if case.variant == "normal" else case.status
        if response.status_code != expected:
            raise AssertionError(f"{case.id}: expected HTTP {expected}, received {response.status_code}")
        return response

    return http
