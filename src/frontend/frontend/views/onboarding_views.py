from flask import Response, render_template
from flask.views import MethodView
from models.admin import Settings

from frontend.auth import admin_required
from frontend.data_persistence import DataPersistenceLayer
from frontend.log import logger
from frontend.onboarding import ADMIN_ADVANCED_TOUR_ID, ADMIN_WELCOME_TOUR_ID


class OnboardingPromptView(MethodView):
    @admin_required()
    def get(self):
        settings = DataPersistenceLayer().get_first(Settings)
        if not settings:
            return Response(status=204)

        completed_tours = settings.settings.completed_onboarding_tours or {}
        if completed_tours.get(ADMIN_WELCOME_TOUR_ID):
            logger.debug("Admin has already completed the welcome tour. No need to show onboarding prompt.")
            return Response(status=204)

        return render_template(
            "onboarding/admin_prompt.html",
            welcome_tour_id=ADMIN_WELCOME_TOUR_ID,
            advanced_tour_id=ADMIN_ADVANCED_TOUR_ID,
            advanced_completed=bool(completed_tours.get(ADMIN_ADVANCED_TOUR_ID)),
            current_settings=settings.settings,
        ), 200
