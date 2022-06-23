from schema.presenter import PresenterSchema
from managers import log_manager
import json, datetime

class BasePresenter:
    type = "BASE_PRESENTER"
    name = "Base Presenter"
    description = "Base abstract type for all presenters"

    parameters = []

    def get_info(self):
        info_schema = PresenterSchema()
        return info_schema.dump(self)

    def print_exception(self, error):
        log_manager.log_debug_trace("[{0}] {1}".format(self.name, error))

    @staticmethod
    def generate_input_data(presenter_input):
        class InputDataObject:
            def json_default(value):
                if isinstance(value, datetime.date):
                    return dict(year=value.year, month=value.month, day=value.day)
                else:
                    return value.__dict__
            def toJSON(self):
                return json.dumps(self, default=InputDataObject.json_default, sort_keys=True, indent=4)

            def __init__(self):
                attribute_map = dict()
                for attribute_group in presenter_input.report_type.attribute_groups:
                    for attribute_group_item in attribute_group.attribute_group_items:
                        attribute_map[attribute_group_item.id] = attribute_group_item

                self.report_items = list()
                for report in presenter_input.reports:
                    class ReportItemObject:
                        def toJSON(self):
                            return json.dumps(self, default=InputDataObject.json_default, sort_keys=True, indent=4)
                        def __init__(self, report_item):
                            self.name = report_item.title
                            self.name_prefix = report_item.title_prefix
                            self.type = presenter_input.report_type.title

                            self.news_items = list()
                            for news_item_aggregate in report_item.news_item_aggregates:
                                for news_item in news_item_aggregate['news_items']:
                                    self.news_items.append(news_item['news_item_data'])

                            class AttributesObject:
                                def toJSON(self):
                                    return json.dumps(self, default=InputDataObject.json_default, sort_keys=True, indent=4)

                            self.attrs = AttributesObject()

                            for attribute in report_item.attributes:
                                if attribute.value is not None:
                                    attr_type = attribute_map[attribute.attribute_group_item_id]
                                    attr_key = attr_type.title.lower().replace(" ", "_")
                                    if hasattr(self.attrs, attr_key):
                                        if attribute_map[attribute.attribute_group_item_id].max_occurrence > 1:
                                            attr = getattr(self.attrs, attr_key)
                                            attr.append(attribute.value)
                                    else:
                                        if attribute_map[attribute.attribute_group_item_id].max_occurrence == 1:
                                            setattr(self.attrs, attr_key, attribute.value)
                                        else:
                                            setattr(self.attrs, attr_key, [attribute.value])

                    self.report_items.append(ReportItemObject(report))

        data = InputDataObject()
        data_json = data.toJSON()
        log_manager.log_info("=== TEMPLATING FROM THE FOLLOWING INPUT ===\n" + data_json)
        data_obj = json.loads(data_json)
        return data_obj

    def generate(self, presenter_input):
        pass
