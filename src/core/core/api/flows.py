"""Prefect Flow Trigger Endpoints"""

from flask import Blueprint, request
from flask.views import MethodView
from prefect.deployments import run_deployment
import asyncio

from core.config import Config
from core.managers.auth_manager import auth_required
from core.log import logger


def run_async(coro):
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


class ConnectorFlow(MethodView):
    """Trigger connector flows via Prefect"""
    
    @auth_required("CONFIG_CONNECTOR_UPDATE")
    def post(self):
        """Trigger connector flow"""
        try:
            data = request.json or {}
            connector_id = data.get("connector_id")
            
            if not connector_id:
                return {"error": "connector_id is required"}, 400
            
            params = {
                "request": {
                    "connector_id": connector_id,
                    "story_ids": data.get("story_ids", [])
                }
            }
            
            fr = run_async(
                run_deployment(
                    name="connector-task-flow/default",
                    parameters=params,
                )
            )
            
            return {
                "flow_run_id": str(fr.id),
                "message": f"Connector with id: {connector_id} scheduled",
                "connector_id": connector_id
            }, 202
            
        except Exception as e:
            logger.exception("Failed to trigger connector flow")
            return {"error": str(e)}, 500


def initialize(app):
    """Register flow endpoints"""
    flows_bp = Blueprint("flows", __name__, url_prefix=f"{Config.APPLICATION_ROOT}api/flows")
    flows_bp.add_url_rule("/connector", view_func=ConnectorFlow.as_view("connector_flow"))
    app.register_blueprint(flows_bp)
    logger.info(" Flows API registered")