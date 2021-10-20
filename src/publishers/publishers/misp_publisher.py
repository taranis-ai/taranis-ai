import json
from base64 import b64decode

import urllib3
from pymisp import ExpandedPyMISP, MISPEvent

from publishers.base_publisher import BasePublisher
from taranisng.schema.parameter import Parameter, ParameterType


class MISPPublisher(BasePublisher):
    type = "MISP_PUBLISHER"
    name = "MISP Publisher"
    description = "Publisher for publishing in MISP"

    parameters = [
        Parameter(0, "MISP_URL", "MISP url", "MISP server https url", ParameterType.STRING),
        Parameter(0, "MISP_API_KEY", "MISP API key", "User MISP API key", ParameterType.STRING)
    ]

    parameters.extend(BasePublisher.parameters)

    def publish(self, publisher_input):

        try:
            misp_url = publisher_input.parameter_values_map['MISP_URL']
            misp_key = publisher_input.parameter_values_map['MISP_API_KEY']
            misp_verifycert = False

            data = publisher_input.data[:]
            bytes_data = b64decode(data, validate=True)

            event_json = json.loads(bytes_data)

            urllib3.disable_warnings()

            misp = ExpandedPyMISP(misp_url, misp_key, misp_verifycert)

            event = MISPEvent()
            event.load(event_json)
            misp.add_event(event)
        except Exception as error:
            BasePublisher.print_exception(self, error)
