from flask_restful import Resource
from publishers import send_results


class SendEmail(Resource):

    # @auth_required('ASSESS_ACCESS')
    def get(self):
        return send_results.send_email()


def initialize(api):
    api.add_resource(SendEmail, "/api/publishers/sendemail")
