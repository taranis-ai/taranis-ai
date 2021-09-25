from taranisng.schema.presenter import PresenterSchema


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
    def generate_report_data_map(presenter_input):
        attribute_map = dict()
        for attribute_group in presenter_input.report_type.attribute_groups:
            for attribute_group_item in attribute_group.attribute_group_items:
                attribute_map[attribute_group_item.id] = attribute_group_item.title

        report_data_map = list()
        for report in presenter_input.reports:
            value_map = dict()
            report_data_map.append(value_map)
            for attribute in report.attributes:
                if attribute.value is not None:
                    attr_title = attribute_map[attribute.attribute_group_item_id]
                    if attr_title in value_map:
                        value_map[attr_title].append(attribute.value)
                    else:
                        value_map[attr_title] = [attribute.value]

        return report_data_map

    def generate(self, presenter_input):
        pass
