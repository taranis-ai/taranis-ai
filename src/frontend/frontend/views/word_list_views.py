import json
from flask import request, render_template, Response

from models.admin import WordList
from frontend.views.base_view import BaseView
from frontend.core_api import CoreApi
from frontend.log import logger
from frontend.config import Config
from frontend.data_persistence import DataPersistenceLayer
from frontend.auth import auth_required


class WordListView(BaseView):
    model = WordList
    icon = "chat-bubble-bottom-center-text"
    _index = 170

    form_fields = {
        "name": {},
        "description": {},
        "link": {},
        "include": {},
        "exclude": {},
        "tagging": {},
    }

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
        core_resp = CoreApi().export_word_lists(word_list_ids)

        if not core_resp:
            logger.debug(f"Failed to fetch word lists from: {Config.TARANIS_CORE_URL}")
            return f"Failed to fetch word lists from: {Config.TARANIS_CORE_URL}", 500

        return CoreApi.stream_proxy(core_resp, "word_lists_export.json")

    @classmethod
    @auth_required()
    def load_default_word_lists(cls):
        response = CoreApi().load_default_word_lists()
        if not response:
            logger.error("Failed to load default word lists")
            return render_template("notification/index.html", notification={"message": "Failed to load default word lists", "error": True})

        response = CoreApi().import_word_lists(response)

        if not response.ok:
            error = response.json().get("error", "Unknown error")
            error_message = f"Failed to import default word lists: {error}"
            logger.error(error_message)
            return render_template("notification/index.html", notification={"message": error_message, "error": True})

        DataPersistenceLayer().invalidate_cache_by_object(WordList)
        items = DataPersistenceLayer().get_objects(cls.model)
        return render_template(cls.get_list_template(), **cls.get_view_context(items))
