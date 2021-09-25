from flask_restful import Resource
from publishers import send_results


class SendToFTP(Resource):

    # @auth_required('ASSESS_ACCESS')
    def get(self):
        return send_results.send_to_ftp()


def initialize(api):
    api.add_resource(SendToFTP, "/api/publishers/ftp")
