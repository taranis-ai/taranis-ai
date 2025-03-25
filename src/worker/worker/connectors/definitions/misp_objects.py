from pymisp import InvalidMISPObject, MISPObject

from worker.log import logger


class BaseMispObject(MISPObject):
    def __init__(self, parameters: dict, template: str, strict: bool = True, **kwargs):
        super().__init__(name=template, strict=strict, **kwargs)
        self._parameters = parameters
        self.generate_attributes()

    def generate_attributes(self):
        """Contains the logic where all the values of the object are gathered"""
        if not self._definition or not hasattr(self, "_parameters") or not self._definition.get("attributes"):
            return
        logger.debug(f"{self._definition=}")
        for object_relation in self._definition["attributes"]:
            logger.debug(f"{object_relation=}")
            value = self._parameters.pop(object_relation)
            # if not value:
            #     logger.debug(f"Skipping object_relation={object_relation} as value is empty or None")
            #     continue
            if isinstance(value, dict):
                self.add_attribute(object_relation, **value)
            elif isinstance(value, list):
                self.add_attributes(object_relation, *value)
            else:
                # Assume it is the value only
                self.add_attribute(object_relation, value=value)
        if self._strict and self._known_template and self._parameters:
            raise InvalidMISPObject(
                f"Some object relations are unknown in the template and could not be attached: {', '.join(self._parameters)}"
            )
