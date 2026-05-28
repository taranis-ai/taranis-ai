from flask import Response, render_template
from flask.views import MethodView

from frontend.auth import admin_required
from frontend.log import logger
from frontend.onboarding import get_admin_onboarding_context, needs_admin_onboarding


class OnboardingPromptView(MethodView):
    @admin_required()
    def get(self):
        onboarding_context = get_admin_onboarding_context()
        if not onboarding_context:
            return Response(status=204)

        if not needs_admin_onboarding(onboarding_context):
            logger.debug("Admin has already completed onboarding tours. No need to show onboarding prompt.")
            return Response(status=204)

        return render_template("onboarding/admin_prompt.html", admin_onboarding=onboarding_context), 200
