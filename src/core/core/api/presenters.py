from flask_restx import Resource, Namespace
from flask import request

from core.managers import presenters_manager
from core.managers.auth_manager import auth_required
from core.model import presenters_node


class PresentersNode(Resource):
    @auth_required("CONFIG_PRESENTERS_NODE_ACCESS")
    def get(self):
        search = request.args.get(key="search", default=None)
        return presenters_node.PresentersNode.get_all_json(search)

    @auth_required("CONFIG_PRESENTERS_NODE_CREATE")
    def post(self):
        return "", presenters_node.PresentersNode.add(request.json)

    @auth_required("CONFIG_PRESENTERS_NODE_UPDATE")
    def put(self, id):
        presenters_manager.update_presenters_node(id, request.json)

    @auth_required("CONFIG_PRESENTERS_NODE_DELETE")
    def delete(self, id):
        return presenters_node.PresentersNode.delete(id)


def initialize(api):
    namespace = Namespace("presenters", description="Presenters related operations", path="/api/v1/presenters")
    namespace.add_resource(PresentersNode, "/nodes", "/node", "/node/<id>")
    api.add_namespace(namespace)
