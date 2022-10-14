from flask_restful import Resource
from flask_jwt_extended import jwt_required
from flask import send_from_directory
from core.config import Config
from core.managers.log_manager import logger


class OpenAPI(Resource):
    @jwt_required()
    def get(self):
        try:
            return send_from_directory(Config.OpenAPI, "openapi3_0.yaml")
        except Exception:
            logger.log_debug_trace(f"ERROR: Loading openapi3_0.yaml from: {Config.OpenAPI}")
            return "OpenAPI file not found", 404


def initialize(api):
    api.add_resource(OpenAPI, "/api/v1/openapi", "/api/openapi.yaml", "/api/v1/openapi.yaml", "/api/openapi.yml", "/api/v1/openapi.yml")
