import json
from flask import request, render_template, Response
from typing import Any

from models.admin import WordList
from frontend.views.base_view import BaseView
from frontend.core_api import CoreApi
from frontend.log import logger
from frontend.config import Config
from frontend.data_persistence import DataPersistenceLayer
from frontend.auth import auth_required
from frontend.filters import render_count
from frontend.views.admin_views.admin_mixin import AdminMixin


class WordListView(AdminMixin, BaseView):
    model = WordList
    icon = "chat-bubble-bottom-center-text"
    _index = 170

    @classmethod
    def import_view(cls, error=None):
        return render_template(f"{cls.model_name().lower()}/{cls.model_name().lower()}_import.html", error=error)

    @classmethod
    def import_post_view(cls):
        word_lists = request.files.get("file")
        if not word_lists:
            return cls.import_view("No file or organization provided")
        data = word_lists.read()
        data = json.loads(data)
        data = json.dumps(data["data"])

        response = CoreApi().import_word_lists(json.loads(data))

        if not response:
            error = "Failed to import word lists"
            return cls.import_view(error)

        DataPersistenceLayer().invalidate_cache_by_object(WordList)
        return Response(status=200, headers={"HX-Refresh": "true"})

    @classmethod
    @auth_required()
    def export_view(cls):
        word_list_ids = request.args.getlist("ids")
        core_resp = CoreApi().export_word_lists({"ids": word_list_ids})

        if not core_resp:
            logger.warning(f"Failed to fetch word lists from: {Config.TARANIS_CORE_URL}")
            return f"Failed to fetch word lists from: {Config.TARANIS_CORE_URL}", 500

        return CoreApi.stream_proxy(core_resp, "word_lists_export.json")

    @classmethod
    @auth_required()
    def load_default_word_lists(cls):
        response = CoreApi().load_default_word_lists()
        if not response:
            logger.error("Failed to load default word lists")
            return render_template("notification/index.html", notification={"message": "Failed to load default word lists", "error": True})

        core_response = CoreApi().import_word_lists(response)

        response = cls.get_notification_from_response(core_response)

        DataPersistenceLayer().invalidate_cache_by_object(WordList)
        table, table_response = cls.render_list()
        if table_response == 200:
            response += table
        return response, core_response.status_code

    @classmethod
    @auth_required()
    def update_word_lists(cls, word_list_id: int | None = None):
        core_response = CoreApi().update_word_lists(word_list_id)
        response = cls.get_notification_from_response(core_response)

        DataPersistenceLayer().invalidate_cache_by_object(WordList)
        table, table_response = cls.render_list()
        if table_response == 200:
            response += table
        return response, core_response.status_code

    @classmethod
    def get_columns(cls) -> list[dict[str, Any]]:
        return [
            {"title": "Name", "field": "name", "sortable": True, "renderer": None},
            {"title": "Description", "field": "description", "sortable": True, "renderer": None},
            {
                "title": "Words",
                "field": "entries",
                "sortable": False,
                "renderer": render_count,
                "render_args": {"field": "entries"},
            },
        ]
