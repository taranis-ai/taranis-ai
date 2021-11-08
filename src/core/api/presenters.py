from flask_restful import Resource
from flask import request

from managers import presenters_manager
from managers.auth_manager import auth_required
from model import presenters_node
from model.permission import Permission


class AddPresentersNode(Resource):

    @auth_required('CONFIG_PRESENTERS_NODE_CREATE')
    def post(self):
        return '', presenters_manager.add_presenters_node(request.json)


class PresentersNodes(Resource):

    @auth_required('CONFIG_PRESENTERS_NODE_ACCESS')
    def get(self):
        search = None
        if 'search' in request.args and request.args['search']:
            search = request.args['search']
        return presenters_node.PresentersNode.get_all_json(search)


class PresentersNode(Resource):

    @auth_required('CONFIG_PRESENTERS_NODE_UPDATE')
    def put(self, id):
        presenters_manager.update_presenters_node(id, request.json)

    @auth_required('CONFIG_PRESENTERS_NODE_DELETE')
    def delete(self, id):
        return presenters_node.PresentersNode.delete(id)


def initialize(api):
    api.add_resource(PresentersNodes, "/api/presenters/nodes")
    api.add_resource(AddPresentersNode, "/api/presenters/nodes/add")
    api.add_resource(PresentersNode, "/api/presenters/node/<id>")

    Permission.add("CONFIG_PRESENTERS_NODE_ACCESS", "Config presenters nodes access",
                   "Access to presenters nodes configuration")
    Permission.add("CONFIG_PRESENTERS_NODE_CREATE", "Config presenters node create",
                   "Create presenters node configuration")
    Permission.add("CONFIG_PRESENTERS_NODE_UPDATE", "Config presenters node update",
                   "Update presenters node configuration")
    Permission.add("CONFIG_PRESENTERS_NODE_DELETE", "Config presenters node delete",
                   "Delete presenters node configuration")
