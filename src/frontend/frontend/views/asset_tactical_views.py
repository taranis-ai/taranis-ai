"""A fictional dependency map for exploring the tactical-view concept."""

from flask import render_template, request

from frontend.auth import auth_required


# Preview data stays local to this page; these IDs are not inventory asset IDs.
HOSTS = {
    "db-01": {"role": "Primary database", "zone": "Production", "x": 30, "y": 80},
    "broker-01": {"role": "Message broker", "zone": "Production", "x": 30, "y": 260},
    "api-01": {"role": "Application API", "zone": "Production", "x": 370, "y": 80},
    "worker-01": {"role": "Background jobs", "zone": "Production", "x": 370, "y": 260},
    "portal-01": {"role": "Customer portal", "zone": "Production", "x": 710, "y": 80},
    "reports-01": {"role": "Reporting service", "zone": "Production", "x": 710, "y": 260},
    "staging-01": {"role": "Isolated test host", "zone": "Staging", "x": 370, "y": 435},
}

DEPENDENCIES = [
    {"provider": "db-01", "consumer": "api-01", "reason": "API requests read and write the primary database."},
    {"provider": "db-01", "consumer": "worker-01", "reason": "Background jobs read and write the primary database."},
    {"provider": "broker-01", "consumer": "worker-01", "reason": "Background jobs receive work from the message broker."},
    {"provider": "api-01", "consumer": "portal-01", "reason": "The customer portal calls the application API."},
    {"provider": "worker-01", "consumer": "reports-01", "reason": "The reporting service consumes background-job results."},
]

SCENARIOS = {
    "database": {
        "title": "Shared database",
        "root": "db-01",
        "description": "Assume the primary database is affected. Explore both dependent application paths.",
        "paths": {
            "api-01": ["db-01", "api-01"],
            "worker-01": ["db-01", "worker-01"],
            "portal-01": ["db-01", "api-01", "portal-01"],
            "reports-01": ["db-01", "worker-01", "reports-01"],
        },
    },
    "queue": {
        "title": "Message broker",
        "root": "broker-01",
        "description": "Assume the message broker is affected. Explore the impact on jobs and their consumers.",
        "paths": {"worker-01": ["broker-01", "worker-01"], "reports-01": ["broker-01", "worker-01", "reports-01"]},
    },
    "staging": {
        "title": "Isolated staging host",
        "root": "staging-01",
        "description": "Assume the staging host is affected. No production host depends on it in this sample map.",
        "paths": {},
    },
}


@auth_required("ASSETS_ACCESS")
def tactical():
    scenario_id = request.args.get("scenario", "database")
    if scenario_id not in SCENARIOS:
        scenario_id = "database"
    scenario = SCENARIOS[scenario_id]
    selected_host = request.args.get("host", scenario["root"])
    if selected_host not in HOSTS:
        selected_host = scenario["root"]
    return render_template(
        "assets/tactical.html",
        hosts=HOSTS,
        dependencies=DEPENDENCIES,
        scenarios=SCENARIOS,
        scenario_id=scenario_id,
        scenario=scenario,
        selected_host=selected_host,
    )
