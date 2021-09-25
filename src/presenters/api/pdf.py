from flask import request
from flask_restful import Resource
from presenters import create_pdf


class BinaryData(Resource):

    # @auth_required('ASSESS_ACCESS')
    def get(self):
        return create_pdf.create_binary_data()


class CreatePdf(Resource):

    # @auth_required('ASSESS_ACCESS')
    def get(self):
        return create_pdf.generate_pdf()


def initialize(api):
    api.add_resource(BinaryData, "/api/presenters/data")
    api.add_resource(CreatePdf, "/api/presenters/pdf")
