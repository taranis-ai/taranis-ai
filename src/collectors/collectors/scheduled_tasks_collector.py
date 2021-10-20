import datetime
import hashlib
import os
import random
import string
import uuid

from taranisng.schema.news_item import NewsItemData
from taranisng.schema.parameter import Parameter, ParameterType
from .base_collector import BaseCollector


class ScheduledTasksCollector(BaseCollector):
    type = "SCHEDULED_TASKS_COLLECTOR"
    name = "Scheduled tasks Collector"
    description = "Collector for collecting scheduled tasks"

    parameters = [Parameter(0, "TASK_TITLE", "Task title", "Title of scheduled task", ParameterType.STRING),
                  Parameter(0, "TASK_COMMAND", "Task command", "Command which will be executed", ParameterType.STRING),
                  Parameter(0, "TASK_DESCRIPTION", "Task description", "Description of scheduled task",
                            ParameterType.STRING)
                  ]

    parameters.extend(BaseCollector.parameters)

    def collect(self, source):

        news_items = []
        head, tail = os.path.split(source.parameter_values['TASK_COMMAND'])
        task_title = source.parameter_values['TASK_TITLE']

        try:
            if head == '':
                task_command = source.parameter_values['TASK_COMMAND']
            else:
                task_command = os.popen('.' + source.parameter_values['TASK_COMMAND']).read()

            preview = source.parameter_values['TASK_DESCRIPTION']
            author = ''
            osint_source = 'TaranisNG System'
            link = ''
            content = task_command
            collected = datetime.datetime.now()
            published = datetime.datetime.now()

            letters = string.ascii_lowercase
            random_string = ''.join(random.choice(letters) for i in range(10))

            news_item = NewsItemData(uuid.uuid4(), hashlib.sha256(random_string.encode()).hexdigest(), task_title,
                                     preview, osint_source, link, published, author, collected, content, source.id, [])

            news_items.append(news_item)

            BaseCollector.publish(news_items, source)
        except Exception as error:
            BaseCollector.print_exception(source, error)
