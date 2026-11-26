from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

from flask import g, render_template, request, url_for
from flask.typing import ResponseReturnValue
from models.admin import Settings
from models.llm import DECISIONS_FORMATS, LLM_API_FORMATS, LLM_FEATURES, OPENROUTER_DECISIONS_URL, resolve_format_base_url

from frontend.core_api import CoreApi
from frontend.data_persistence import DataPersistenceLayer
from frontend.i18n import get_timezone_options, select_timezone
from frontend.log import logger
from frontend.utils.form_data_parser import parse_formdata
from frontend.views.admin_views.admin_base_view import AdminBaseView


class SettingsView(AdminBaseView):
    model = Settings
    htmx_list_template = "settings/index.html"
    htmx_update_template = "settings/index.html"
    default_template = "settings/index.html"
    base_route = "admin_settings.settings"
    edit_route = "admin_settings.settings"
    _read_only = True
    _index = 190

    @classmethod
    def get_extra_context(cls, base_context: dict) -> dict:
        dpl = DataPersistenceLayer()
        base_context["_is_admin"] = cls._is_admin
        base_context["settings"] = dpl.get_first(Settings)
        base_context["llm_features"] = LLM_FEATURES
        base_context["llm_api_formats"] = LLM_API_FORMATS
        base_context["openrouter_decisions_url"] = OPENROUTER_DECISIONS_URL
        base_context["llm_form"] = getattr(g, "llm_form", None)
        base_context["llm_editing_endpoint"] = getattr(g, "llm_editing_endpoint", None)
        base_context["timezone_options"] = get_timezone_options()
        base_context["export_timezone"] = select_timezone()
        base_context["export_max_datetime"] = datetime.now(ZoneInfo(base_context["export_timezone"])).strftime("%Y-%m-%dT%H:%M")
        base_context["frontend_actions"] = [
            {
                "label": "Invalidate Cache",
                "url": url_for("base.invalidate_cache"),
            }
        ]
        return base_context

    @classmethod
    def model_plural_name(cls) -> str:
        """Returns the plural name of the model class."""
        return f"{cls.model._model_name}"

    @classmethod
    def export_stories(cls):
        params = request.args.copy()
        timezone = ZoneInfo(select_timezone())
        try:
            for field in ("timefrom", "timeto"):
                if value := params.get(field):
                    local_time = datetime.fromisoformat(value)
                    if local_time.tzinfo is None:
                        zoned_time = local_time.replace(tzinfo=timezone)
                        if (
                            zoned_time.astimezone(UTC).astimezone(timezone).replace(tzinfo=None) != local_time
                            or zoned_time.utcoffset() != zoned_time.replace(fold=1).utcoffset()
                        ):
                            raise ValueError("Nonexistent or ambiguous local time")
                        local_time = zoned_time
                    params[field] = local_time.astimezone(UTC).isoformat()
        except ValueError:
            notification = cls.render_response_notification(
                {"error": "Enter valid dates in your profile timezone. Avoid times skipped or repeated by daylight saving changes."}
            )
            view, _ = cls.static_view()
            return notification + view, 400
        return cls.settings_action(f"/settings/export-stories?{urlencode(list(params.items(multi=True)))}")

    @classmethod
    def settings_action(cls, action_url, method="download"):
        logger.debug(f"Calling settings action: {action_url}")

        if action_url.startswith("/settings/llm-endpoints") and method == "post":
            return cls.llm_endpoint_action(action_url)

        if method == "download":
            response = CoreApi().api_download(action_url)
            if not response.ok:
                logger.error(f"Failed to download file from {action_url}: {response.status_code} - {response.text}")
                notification = cls.get_notification_from_response(response)
                static_view, _ = cls.static_view()
                notification += static_view
                return notification, response.status_code
            download = CoreApi.stream_proxy(response, "stories_export.json")
            download.headers["Cache-Control"] = "no-store"
            return download

        if method == "patch" or (request.form and action_url == "/settings/settings"):
            payload = parse_formdata(request.form) if request.form else None
            if payload and "onboarding_enabled" in payload.get("settings", {}):
                payload["settings"]["onboarding_enabled"] = payload["settings"]["onboarding_enabled"].lower() == "true"
            response = CoreApi().api_patch(action_url, json_data=payload)
            if response.ok:
                DataPersistenceLayer().invalidate_model_cache_locally(Settings)
            notification = cls.get_notification_from_response(response)
            static_view, static_response = cls.static_view()
            notification += static_view
            return notification, response.status_code if not response.ok else static_response

        if request.form:
            response, error = cls.process_form_data(object_id="0")
            message = response.get("message") if response else error
            notification = render_template("notification/index.html", notification={"message": message, "error": bool(error)})
        else:
            response = CoreApi().api_post(action_url)
            notification = cls.get_notification_from_response(response)

        static_view, static_response = cls.static_view()
        notification += static_view
        return notification, static_response

    @classmethod
    def llm_model_suggestions(cls):
        base_url = request.args.get("base_url", "").strip().rstrip("/")
        params: dict[str, str] = {
            api_format: request.args.get(f"api_formats[{api_format}][base_url]", "").strip() or base_url
            for api_format in LLM_API_FORMATS
            if api_format not in DECISIONS_FORMATS
        }
        decisions_format = request.args.get("decisions[api_format]", "systemone")
        decisions_url = request.args.get("decisions[base_url]", "").strip()
        if decisions_format == "openrouter":
            decisions_format = "systemone"
            decisions_url = OPENROUTER_DECISIONS_URL
        if decisions_format in DECISIONS_FORMATS:
            try:
                params[decisions_format] = resolve_format_base_url(base_url, decisions_format, decisions_url)
            except ValueError:
                # Unsaved URLs can still be incomplete or malformed.
                params[decisions_format] = ""
        params["processing_mode"] = request.args.get("processing_mode", "realtime")

        # Core owns the public catalog cache. The browser supplies unsaved URLs for this form.
        suggestions = CoreApi().api_get("/settings/llm-model-suggestions", params=params) or {}
        return render_template(
            "settings/llm_model_suggestions.html",
            field_prefix=f"llm-{request.args.get('endpoint_id', '')}",
            suggestions={
                "responses": suggestions.get("responses", []),
                "chat_completions": suggestions.get("chat_completions", []),
                "decisions": suggestions.get(decisions_format, []),
            },
        )

    @classmethod
    def llm_endpoint_action(cls, action_url):
        payload = parse_formdata(request.form)
        if decisions := payload.pop("decisions", None):
            api_format = decisions.pop("api_format", "systemone")
            if api_format == "openrouter":
                api_format = "systemone"
                decisions["base_url"] = OPENROUTER_DECISIONS_URL
            payload.setdefault("api_formats", {})[api_format] = decisions
        submitted_formats = payload.get("api_formats")
        if "api_formats" in payload:
            payload["api_formats"] = {
                api_format: {key: value for key, value in config.items() if key != "enabled"}
                for api_format, config in payload["api_formats"].items()
                if config.get("enabled") == "true"
            }
        response = CoreApi().api_post(action_url, json_data=payload)
        notification = cls.get_notification_from_response(response)
        if response.ok:
            DataPersistenceLayer().invalidate_model_cache_locally(Settings)
        elif not action_url.endswith("/delete"):
            g.llm_editing_endpoint = action_url.removeprefix("/settings/llm-endpoints").strip("/")
            g.llm_form = {key: value for key, value in payload.items() if key not in {"api_key", "api_key_clear", "csrf_token"}}
            if submitted_formats is not None:
                g.llm_form["api_formats"] = {
                    api_format: {**config, "enabled": config.get("enabled") == "true"} for api_format, config in submitted_formats.items()
                }
            if "enabled" in request.form:
                g.llm_form["enabled"] = request.form["enabled"].lower() == "true"
        view, _ = cls.static_view()
        return notification + view, response.status_code

    def get(self, **kwargs: Any) -> ResponseReturnValue:
        return self.static_view()
