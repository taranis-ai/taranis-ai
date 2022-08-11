from flask_restful import Resource
from flask import request

from core.managers import presenters_manager
from core.managers.auth_manager import auth_required
from core.model import presenters_node


class AddPresentersNode(Resource):
    @auth_required("CONFIG_PRESENTERS_NODE_CREATE")
    def post(self):
        return "", presenters_manager.add_presenters_node(request.json)


class PresentersNodes(Resource):
    @auth_required("CONFIG_PRESENTERS_NODE_ACCESS")
    def get(self):
        search = None
        if "search" in request.args and request.args["search"]:
            search = request.args["search"]
        return presenters_node.PresentersNode.get_all_json(search)


class PresentersNode(Resource):
    @auth_required("CONFIG_PRESENTERS_NODE_UPDATE")
    def put(self, id):
        presenters_manager.update_presenters_node(id, request.json)

    @auth_required("CONFIG_PRESENTERS_NODE_DELETE")
    def delete(self, id):
        return presenters_node.PresentersNode.delete(id)


def initialize(api):
    api.add_resource(PresentersNodes, "/api/presenters/nodes")
    api.add_resource(AddPresentersNode, "/api/presenters/nodes/add")
    api.add_resource(PresentersNode, "/api/presenters/node/<id>")
