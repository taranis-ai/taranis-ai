from schema.presenter import PresenterSchema


class BasePresenter:
    type = "BASE_PRESENTER"
    name = "Base Presenter"
    description = "Base abstract type for all presenters"

    parameters = []

    def get_info(self):
        info_schema = PresenterSchema()
        return info_schema.dump(self)

    def print_exception(self, error):
        print('Presenter name: ' + self.name)
        if str(error).startswith('b'):
            print('ERROR: ' + str(error)[2:-1])
        else:
            print('ERROR: ' + str(error))

    @staticmethod
    def generate_input_data(presenter_input):
        class InputDataObject:
            def __init__(self):
                attribute_map = dict()
                for attribute_group in presenter_input.report_type.attribute_groups:
                    for attribute_group_item in attribute_group.attribute_group_items:
                        attribute_map[attribute_group_item.id] = attribute_group_item

                self.report_items = list()
                for report in presenter_input.reports:
                    class ReportItemObject:
                        def __init__(self, report_item):
                            self.name = report_item.title
                            self.name_prefix = report_item.title_prefix
                            self.type = presenter_input.report_type.title

                            self.news_items = list()
                            for news_item_aggregate in report_item.news_item_aggregates:
                                for news_item in news_item_aggregate['news_items']:
                                    self.news_items.append(news_item['news_item_data'])

                            class AttributesObject:
                                pass

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

        return InputDataObject()

    def generate(self, presenter_input):
        pass
