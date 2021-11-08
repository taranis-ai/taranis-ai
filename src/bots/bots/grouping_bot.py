import json
import re

from .base_bot import BaseBot
from schema.parameter import Parameter, ParameterType
from remote.core_api import CoreApi


class GroupingBot(BaseBot):
    type = "GROUPING_BOT"
    name = "Grouping Bot"
    description = "Bot for grouping news items into aggregates"

    parameters = [Parameter(0, "SOURCE_GROUP", "Source Group", "OSINT Source group to inspect", ParameterType.STRING),
                  Parameter(0, "REGULAR_EXPRESSION", "Regular Expression", "Regular expression for items matching",
                            ParameterType.STRING)
                  ]

    parameters.extend(BaseBot.parameters)

    def execute(self, preset):

        try:
            source_group = preset.parameter_values['SOURCE_GROUP']
            regexp = preset.parameter_values['REGULAR_EXPRESSION']
            interval = preset.parameter_values['REFRESH_INTERVAL']

            limit = BaseBot.history(interval)

            data = CoreApi.get_news_items_aggregate(source_group, limit)
            data = json.loads(data)

            if data:

                data_findings = []

                for aggregate in data:

                    findings = []

                    for news_item in aggregate['news_items']:

                        content = news_item['news_item_data']['content']

                        analyzed_content = ''.join(content).split()
                        analyzed_content = [item.replace('.', '') if item.endswith('.') else item
                                            for item in analyzed_content]
                        analyzed_content = [item.replace(',', '') if item.endswith(',') else item
                                            for item in analyzed_content]

                        analyzed_content = set(analyzed_content)

                        for element in analyzed_content:

                            finding = re.search("(" + regexp + ")", element)

                            if finding:
                                finding = [news_item['id'], finding.group(1)]
                                findings.append(finding)

                    # NEXT PART OF CODE IS FOR FINDINGS IN ONE AGGREGATE
                    # IT WILL GROUP NEWS_ITEMS TOGETHER FROM ONE AGGREGATE

                    if findings:

                        grouped_ids = []
                        values = {}

                        for k, val in findings:

                            if val in values:

                                grouped = [x for x in grouped_ids if len(x) != 1]
                                x_flat = [k for sublist in grouped for k in sublist]

                                if str(k) not in x_flat:
                                    grouped_ids[values[val]].extend(str(k))

                            else:
                                grouped_ids.append([str(k)])
                                values[val] = len(values)

                        grouped_ids = [x for x in grouped_ids if len(x) != 1]

                        marker_set = set()
                        corrected_grouped_ids = []

                        for sublist in grouped_ids:
                            for element in sublist:
                                if element not in marker_set:
                                    marker_set.add(element)
                                else:
                                    break
                            else:
                                corrected_grouped_ids.append(sublist)

                        for sublist in corrected_grouped_ids:

                            items = []

                            for element in sublist:
                                item = {
                                    'type': 'ITEM',
                                    'id': int(element)
                                }
                                items.append(item)

                            data = {
                                'action': 'GROUP',
                                'items': items
                            }
                            CoreApi.news_items_grouping(data)

                # NEXT PART OF CODE IS FOR FINDINGS IN ALL AGGREGATES
                # IT WILL GROUP NEWS_ITEMS TOGETHER FROM VARIOUS AGGREGATES

                #     data_findings.append(findings)
                #
                # data_findings = [item for sublist in data_findings for item in sublist]
                #
                # if data_findings:
                #
                #     grouped_ids = []
                #     values = {}
                #
                #     for k, val in data_findings:
                #
                #         if val in values:
                #
                #             grouped = [x for x in grouped_ids if len(x) != 1]
                #             x_flat = [k for sublist in grouped for k in sublist]
                #
                #             if str(k) not in x_flat:
                #
                #                 grouped_ids[values[val]].extend(str(k))
                #
                #         else:
                #             grouped_ids.append([str(k)])
                #             values[val] = len(values)
                #
                #     grouped_ids = [x for x in grouped_ids if len(x) != 1]
                #
                #     marker_set = set()
                #     corrected_grouped_ids = []
                #
                #     for sublist in grouped_ids:
                #         for element in sublist:
                #             if element not in marker_set:
                #                 marker_set.add(element)
                #             else:
                #                 break
                #         else:
                #             corrected_grouped_ids.append(sublist)
                #
                #     for sublist in corrected_grouped_ids:
                #
                #         items = []
                #
                #         for element in sublist:
                #
                #             item = {
                #                 'type': 'ITEM',
                #                 'id': int(element)
                #             }
                #             items.append(item)
                #
                #         data = {
                #             'action': 'GROUP',
                #             'items': items
                #         }
                #         CoreApi.news_items_grouping(data)

        except Exception as error:
            BaseBot.print_exception(preset, error)

    def execute_on_event(self, preset, event_type, data):
        try:
            source_group = preset.parameter_values['SOURCE_GROUP']
            regexp = preset.parameter_values['REGULAR_EXPRESSION']

        except Exception as error:
            BaseBot.print_exception(preset, error)
