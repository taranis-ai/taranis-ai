from flask import Response, render_template
from flask.views import MethodView
from flask_jwt_extended import current_user

from frontend.auth import auth_required
from frontend.log import logger
from frontend.onboarding import pending_onboarding_tasks_for_template


class OnboardingPromptView(MethodView):
    @auth_required()
    def get(self):
        pending_tasks = pending_onboarding_tasks_for_template(current_user)
        if not pending_tasks:
            logger.debug("User has no pending onboarding tasks.")
            return Response(status=204)

        return render_template("onboarding/prompt.html", pending_onboarding_tasks=pending_tasks), 200
