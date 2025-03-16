import datetime
from worker.types import NewsItem

story_1 = {
    "id": "1",
    "title": "Test Story 1",
    "description": "CVE-2020-1234 - Test Story 1",
    "created": "2023-08-01T17:01:04.801998",
    "read": False,
    "important": False,
    "likes": 0,
    "dislikes": 0,
    "relevance": 0,
    "comments": "",
    "summary": "",
    "osint_source_group_id": "default",
    "news_items": [
        NewsItem(
            hash="a96e88baaff421165e90ac4bb9059971b86f88d5c2abba36d78a1264fb8e9c87",
            title="Test News Item 13",
            review="CVE-2020-1234 - Test Story 1",
            author="",
            web_url="https://url/13",
            language=None,
            content="CVE-2020-1234 - Test Story 1",
            collected_date=datetime.datetime(2023, 8, 1, 17, 1, 4, 802015),
            published_date=datetime.datetime(2023, 8, 1, 17, 1, 4, 801998),
            osint_source_id="78049551-dcef-45bd-a5cd-4fe842c4d5e2",
        )
    ],
    "tags": {
        "CVE-2020-1234": {"name": "CVE-2020-1234", "tag_type": "CVE"},
        "Security": {"name": "Security", "tag_type": "MISC"},
    },
}

story_2 = {
    "id": "2",
    "title": "Test Story 2",
    "description": "Long and random text - bla bla foo bar lorem ipsum",
    "created": "2023-08-01T17:01:04.801934",
    "read": False,
    "important": False,
    "likes": 0,
    "dislikes": 0,
    "relevance": 0,
    "comments": "",
    "summary": "",
    "osint_source_group_id": "default",
    "news_items": [
        NewsItem(
            hash="f4c7b52ecfe6ab612db30e7fa534b470fd11493fc92f30575577b356b2a1abc7",
            title="Test News Item 12",
            review="Long and random text - bla bla foo bar lorem ipsum",
            author="",
            web_url="https://url/12",
            language=None,
            content="Long and random text - bla bla foo bar lorem ipsum",
            collected_date=datetime.datetime(2023, 8, 1, 17, 1, 4, 801951),
            published_date=datetime.datetime(2023, 8, 1, 17, 1, 4, 801934),
            osint_source_id="78049551-dcef-45bd-a5cd-4fe842c4d5e2",
        )
    ],
    "tags": {},
}

story_3 = {
    "id": "3",
    "title": "Test Story Number 3",
    "description": "Cyber Cyber Cyber - Security Security Security",
    "created": "2023-08-01T17:01:04.801870",
    "read": False,
    "important": False,
    "likes": 0,
    "dislikes": 0,
    "relevance": 0,
    "comments": "",
    "summary": "",
    "osint_source_group_id": "default",
    "news_items": [
        NewsItem(
            hash="599fafee5eeb098239c57c78bf5cea6ea52b0e92a1abc9e80964150a3773f135",
            title="Test News Item 11",
            review="Cyber Cyber Cyber - Security Security Security",
            author="",
            web_url="https://url/11",
            language=None,
            content="Cyber Cyber Cyber - Security Security Security",
            collected_date=datetime.datetime(2023, 8, 1, 17, 1, 4, 801886),
            published_date=datetime.datetime(2023, 8, 1, 17, 1, 4, 801870),
            osint_source_id="78049551-dcef-45bd-a5cd-4fe842c4d5e2",
        )
    ],
    "tags": {
        "Azure": {"name": "Azure", "tag_type": "MISC"},
        "Europe": {"name": "Mein Highlight", "tag_type": "LOC"},
        "Microsoft": {"name": "Microsoft", "tag_type": "ORG"},
    },
}

stories = [story_1, story_2, story_3]

news_item_tags_1 = {"Cyber": {"name": "Cyber", "tag_type": "CySec"}}
news_item_tags_2 = {"Security": {"name": "Security", "tag_type": "Misc"}}
news_item_tags_3 = {"New Orleans": {"name": "New Orleans", "tag_type": "LOC"}}
news_item_tags_4 = {"CVE": {"name": "CVE", "tag_type": "CySec"}}
news_item_tags_5 = {"CVE-2021-1234": {"name": "CVE-2021-1234", "tag_type": "CVE"}}

news_items = [
    NewsItem(
        osint_source_id="544ac8f3-af17-44ba-a426-d04906f8ebcf",
        hash="e30c292902a87b51ae587b3dc046369b5e8bd4c0f85d04a6ec5e1e8b97df0b0f",
        title="Getting started with Microsoft Azure Data Explorer Add-On for Splunk",
        review='Microsoft Azure Data Explorer Add-On for Splunk allows users to effortlessly ingest data from Splunk to Azure Data Explorer which is a fast and scalable data analytics platform designed for real-time analysis of large volumes of data. \n \nThe following kinds of data are most suitable for ingestion into Azure Data Explorer, but are not limited to the following list:\n\nHigh-Volume Data: Azure Data Explorer is built to handle vast amounts of data efficiently. If your organization generates a significant volume of data that needs real-time analysis, Azure Data Explorer is a suitable choice. \nTime-Series Data: Azure Data Explorer excels at handling time-series data, such as logs, telemetry data, and sensor readings. It organizes data in time-based partitions, making it easy to perform time-based analysis and aggregations. \nReal-Time Analytics: If your organization requires real-time insights from the data flowing in, Azure Data Explorer\'s near real-time capabilities can be beneficial.\n\nIngesting Data from Splunk to Azure Data Explorer using Azure Data Explorer Addon\n \nMicrosoft Azure Data Explorer Add-On for Splunk allows Azure Data Explorer users to ingest logs from Splunk platform using the Kusto Python SDK.\nDetails on pre-requisites, configuring the add-on and viewing the data in Azure Data Explorer is covered in this section.\n \nBackground\n \nWhen we add data to Splunk, the Splunk indexer processes it and stores it in a designated index (either, by default, in the main index or custom index). Searching in Splunk involves using the indexed data for the purpose of creating metrics, dashboards and alerts. This Splunk add-on triggers an action based on the alert in Splunk. We can use Alert actions to send data to Azure Data Explorer using the specified addon.\n \nThis add-on uses kusto python sdk (https://learn.microsoft.com/en-us/azure/data-explorer/kusto/api/python/kusto-python-client-library) to send log data to Microsoft Azure Data Explorer. Hence, this addon supports queued mode of ingestion by default. This addon has a durable feature as well which helps to minimize data loss during any unexpected network error scenarios. Although durability in ingestion comes at the cost of throughput, therefore it is advised to use this option judiciously.\n \nPrerequisites\n \n\nA Splunk Enterprise instance (Platform Version v9.0 and above) with the required installation privileges to configure add-ons.\nAccess to an Azure Data Explorer cluster.\n\n \nStep 1: Install the Azure Data Explorer Addon\n \n\nDownload the Azure Data Explorer Addon from the Splunkbase website.\nLog in to your Splunk instance as an administrator.\nNavigate to "Apps" and click on "Manage Apps."\nClick on "Install app from file" and select the downloaded Splunk Addon for Azure Data Explorer file.\nFollow the prompts to complete the installation\n\nAfter installation of the Splunk Addon for alerts, it should be visible in the Dashboard -> Alert Actions\n \n\n \nStep 2: Create Splunk Index\n \n\nLog in to your Splunk instance.\nNavigate to "Settings" and click on "Indexes."\nClick on "New Index" to create a new index.\nProvide a name for the index and configure the necessary settings (e.g., retention period, data model, etc.).\nSave the index configuration.\n\n \nStep 3: Configure Splunk Addon for Azure Data Explorer\n \n\nIn Splunk dashboard, Enter your search query in the Search bar based on which alerts will be generated and this alert data will be ingested to Azure Data Explorer.\nClick on Save As and select Alert.\nProvide a name for the alert and provide the interval at which the alert should be triggered.\nSelect the alert action as "Send to Microsoft Azure Data Explorer".\n\n\xa0\n\n\xa0\n5. Configure the Azure Data Explorer connection details such as application client Id, application client secret, cluster name, database name, table name.\n\n\xa0\n\xa06.\xa0When the alert is created, it should be visible in Splunk Dashboard -> Alerts\n\n\xa0\nStep 4: Verify data in Azure Data Explorer\n\xa0\n\nStart monitoring the Azure Data Explorer logs to ensure proper data ingestion.\nOnce the alert is triggered in Splunk, the data will be ingested to Azure Data Explorer.\nVerify the data in Azure Data Explorer using the database and table name in the previous step.\n\n\n\xa0\nAzure Data Explorer Addon Parameters\n\xa0\nThe following is the list of parameters which need to be entered/selected while configuring the addon:\n\nAzure Cluster Ingestion URL: Represents the ingestion URL of the Azure Data Explorer cluster in the ADX portal.\nAzure Application Client Id: Represents the Azure Application Client Id credentials required to access the Azure Data Explorer cluster.\nAzure Application Client secret: Represents the Azure Application Client secret credentials required to access the Azure Data Explorer cluster.\nAzure Application Tenant Id: Represents the Azure Application Tenant Id required to access the Azure Data Explorer cluster.\nAzure Data Explorer Database Name: This represents the name of the database created in the Azure Data Explorer cluster, where we want our data to be ingested.\nAzure Data Explorer Table Name: This represents the name of the table inside the database created in the Azure Data Explorer cluster, where we want our data to be ingested.\nAzure Data Explorer Table Mapping Name: This represents the Azure Data Explorer table mapping used to map to the column of created Azure Data Explorer table.\nRemove Extra Fields: This represents whether we want to remove empty fields in the splunk event payload\nDurable Mode: This property specifies whether durability mode is required during ingestion. When set to true, the ingestion throughput is impacted.\n\n\xa0\nPlease refer to the following links for further details:Link to Splunk Base Addon :\xa0Microsoft Azure Data Explorer Add-On for Splunk | Splunkbase\nLink to Github Source code of Addon:\xa0azure-kusto-splunk/splunk-adx-alert-addon at main · Azure/azure-kusto-splunk (github.com)\n\xa0\nConclusion\n\xa0\nIn this blog post, we have seen how Microsoft Azure Data Explorer Add-On for Splunk can help us ingest data from Splunk to Azure Data Explorer, a powerful data analytics platform. We have also learned about the types of data that are most suitable for Azure Data Explorer, and how to configure the add-on and use alert actions to send data to Azure Data Explorer. By using this add-on, we can leverage the benefits of both Splunk and Azure Data Explorer, and gain deeper insights from our data.',
        web_url="https://techcommunity.microsoft.com/t5/azure-data-explorer-blog/getting-started-with-microsoft-azure-data-explorer-add-on-for/ba-p/3917176",
        published_date=datetime.datetime(2023, 10, 1, 18, 0, 0),
        author="tanmayapanda",
        content='Microsoft Azure Data Explorer Add-On for Splunk allows users to effortlessly ingest data from Splunk to Azure Data Explorer which is a fast and scalable data analytics platform designed for real-time analysis of large volumes of data. \n \nThe following kinds of data are most suitable for ingestion into Azure Data Explorer, but are not limited to the following list:\n\nHigh-Volume Data: Azure Data Explorer is built to handle vast amounts of data efficiently. If your organization generates a significant volume of data that needs real-time analysis, Azure Data Explorer is a suitable choice. \nTime-Series Data: Azure Data Explorer excels at handling time-series data, such as logs, telemetry data, and sensor readings. It organizes data in time-based partitions, making it easy to perform time-based analysis and aggregations. \nReal-Time Analytics: If your organization requires real-time insights from the data flowing in, Azure Data Explorer\'s near real-time capabilities can be beneficial.\n\nIngesting Data from Splunk to Azure Data Explorer using Azure Data Explorer Addon\n \nMicrosoft Azure Data Explorer Add-On for Splunk allows Azure Data Explorer users to ingest logs from Splunk platform using the Kusto Python SDK.\nDetails on pre-requisites, configuring the add-on and viewing the data in Azure Data Explorer is covered in this section.\n \nBackground\n \nWhen we add data to Splunk, the Splunk indexer processes it and stores it in a designated index (either, by default, in the main index or custom index). Searching in Splunk involves using the indexed data for the purpose of creating metrics, dashboards and alerts. This Splunk add-on triggers an action based on the alert in Splunk. We can use Alert actions to send data to Azure Data Explorer using the specified addon.\n \nThis add-on uses kusto python sdk (https://learn.microsoft.com/en-us/azure/data-explorer/kusto/api/python/kusto-python-client-library) to send log data to Microsoft Azure Data Explorer. Hence, this addon supports queued mode of ingestion by default. This addon has a durable feature as well which helps to minimize data loss during any unexpected network error scenarios. Although durability in ingestion comes at the cost of throughput, therefore it is advised to use this option judiciously.\n \nPrerequisites\n \n\nA Splunk Enterprise instance (Platform Version v9.0 and above) with the required installation privileges to configure add-ons.\nAccess to an Azure Data Explorer cluster.\n\n \nStep 1: Install the Azure Data Explorer Addon\n \n\nDownload the Azure Data Explorer Addon from the Splunkbase website.\nLog in to your Splunk instance as an administrator.\nNavigate to "Apps" and click on "Manage Apps."\nClick on "Install app from file" and select the downloaded Splunk Addon for Azure Data Explorer file.\nFollow the prompts to complete the installation\n\nAfter installation of the Splunk Addon for alerts, it should be visible in the Dashboard -> Alert Actions\n \n\n \nStep 2: Create Splunk Index\n \n\nLog in to your Splunk instance.\nNavigate to "Settings" and click on "Indexes."\nClick on "New Index" to create a new index.\nProvide a name for the index and configure the necessary settings (e.g., retention period, data model, etc.).\nSave the index configuration.\n\n \nStep 3: Configure Splunk Addon for Azure Data Explorer\n \n\nIn Splunk dashboard, Enter your search query in the Search bar based on which alerts will be generated and this alert data will be ingested to Azure Data Explorer.\nClick on Save As and select Alert.\nProvide a name for the alert and provide the interval at which the alert should be triggered.\nSelect the alert action as "Send to Microsoft Azure Data Explorer".\n\n\xa0\n\n\xa0\n5. Configure the Azure Data Explorer connection details such as application client Id, application client secret, cluster name, database name, table name.\n\n\xa0\n\xa06.\xa0When the alert is created, it should be visible in Splunk Dashboard -> Alerts\n\n\xa0\nStep 4: Verify data in Azure Data Explorer\n\xa0\n\nStart monitoring the Azure Data Explorer logs to ensure proper data ingestion.\nOnce the alert is triggered in Splunk, the data will be ingested to Azure Data Explorer.\nVerify the data in Azure Data Explorer using the database and table name in the previous step.\n\n\n\xa0\nAzure Data Explorer Addon Parameters\n\xa0\nThe following is the list of parameters which need to be entered/selected while configuring the addon:\n\nAzure Cluster Ingestion URL: Represents the ingestion URL of the Azure Data Explorer cluster in the ADX portal.\nAzure Application Client Id: Represents the Azure Application Client Id credentials required to access the Azure Data Explorer cluster.\nAzure Application Client secret: Represents the Azure Application Client secret credentials required to access the Azure Data Explorer cluster.\nAzure Application Tenant Id: Represents the Azure Application Tenant Id required to access the Azure Data Explorer cluster.\nAzure Data Explorer Database Name: This represents the name of the database created in the Azure Data Explorer cluster, where we want our data to be ingested.\nAzure Data Explorer Table Name: This represents the name of the table inside the database created in the Azure Data Explorer cluster, where we want our data to be ingested.\nAzure Data Explorer Table Mapping Name: This represents the Azure Data Explorer table mapping used to map to the column of created Azure Data Explorer table.\nRemove Extra Fields: This represents whether we want to remove empty fields in the splunk event payload\nDurable Mode: This property specifies whether durability mode is required during ingestion. When set to true, the ingestion throughput is impacted.\n\n\xa0\nPlease refer to the following links for further details:Link to Splunk Base Addon :\xa0Microsoft Azure Data Explorer Add-On for Splunk | Splunkbase\nLink to Github Source code of Addon:\xa0azure-kusto-splunk/splunk-adx-alert-addon at main · Azure/azure-kusto-splunk (github.com)\n\xa0\nConclusion\n\xa0\nIn this blog post, we have seen how Microsoft Azure Data Explorer Add-On for Splunk can help us ingest data from Splunk to Azure Data Explorer, a powerful data analytics platform. We have also learned about the types of data that are most suitable for Azure Data Explorer, and how to configure the add-on and use alert actions to send data to Azure Data Explorer. By using this add-on, we can leverage the benefits of both Splunk and Azure Data Explorer, and gain deeper insights from our data.',
        collected_date=datetime.datetime(2023, 10, 2, 2, 3, 46, 763784),
        attributes=[],
    ),
    NewsItem(
        hash="ad118e4a6674120e66ffabb4f2da9d4f9ce59b9685477ab4a16f5616557fdbfc",
        title="Microsoft wollte Apple die Suchmaschine Bing verkaufen",
        review="Es geht um viel Geld, wenn die großen Tech-Konzerne pokern, und Apple schien in Gesprächen bezüglich Suchmaschinen zuletzt die besten Karten gehabt zu haben",
        content="Es war ein verregneter Tag im Jahr 2020, als sich mehrere hochrangige Vertreter von Microsoft und Apple unter Ausschluss der Öffentlichkeit zusammensetzten. Grund des Meetings war eine Idee von Microsoft, die Suchmaschine Bing an Apple zu verkaufen. Der iPhone-Konzern scheint allerdings diese Idee nie ernsthaft in Erwägung gezogen zu haben.\nIT-Business\nMicrosoft wollte Apple die Suchmaschine Bing verkaufen\nEs geht um viel Geld, wenn die großen Tech-Konzerne pokern, und Apple schien in Gesprächen bezüglich Suchmaschinen zuletzt die besten Karten gehabt zu haben",
        web_url="https://www.derstandard.at/story/3000000189103/microsoft-wollte-apple-die-suchmaschine-bing-verkaufen?ref%3Drss",
        published_date=datetime.datetime(2023, 9, 30, 5, 0, 0),
        author="",
        collected_date=datetime.datetime(2023, 10, 1, 23, 56, 49, 738398),
        osint_source_id="eca31075-949d-40c7-83a3-300ed3433716",
        attributes=[],
    ),
    NewsItem(
        hash="c3a3c34282f6116eaa05d7bd3c7a1e3610e8a0f76d6e4e5366010f9506b1532a",
        title="Kommt noch ein Oktober-Event von Apple?",
        review="Die Gerüchteküche glaubt fest daran, dass Apple in diesem Monat noch neue Hardware vorstellen wird. Doch reicht es für eine Keynote?",
        web_url="https://www.heise.de/news/Kommt-noch-ein-Oktober-Event-von-Apple-9321813.html?wt_mc%3Drss.red.ho.ho.atom.beitrag.beitrag",
        content='Kommt noch ein Oktober-Event von Apple?\nDie Gerüchteküche glaubt fest daran, dass Apple in diesem Monat noch neue Hardware vorstellen wird. Doch reicht es für eine Keynote?\n- Ben Schwan\nDer Oktober ist da – und Apple-Interessierte fragen sich, ob Apple ein viertes Event für 2023 plant. Typischerweise gibt es Keynotes an vier Terminen im Jahr: Eine im Frühjahr, eine im Juni zur Entwicklerkonferenz WWDC, das iPhone-Event im September und – häufig – ein eigenes iPad- und/oder Mac-Event im Oktober. Doch in diesem Jahr könnte das langsame Vorankommen bei den ersten M3-Maschinen nur wenige neue Produkte bringen. Das könnte für eine Keynote nicht ausreichen.\nWas noch fehlt\nAktuell rechnen die meisten Beobachter damit, dass Apple höchstens am iPad schraubt. Hier stünden ein neues iPad Air, ein iPad 11 für Einsteiger und ein neues iPad mini zur Diskussion. Alle drei Updates dürften eher "minor" ausfallen, also mit leichten Verbesserungen des Innenlebens. Genau das spricht wiederum dafür, dass Apple sie nur per Pressemitteilung vorstellt. Von einem iPad Pro mit M3-SoC und OLED-Schirm ist frühestens für Anfang kommenden Jahres die Rede.\nBeim Mac wird auf ein erstes M3-Modell gewartet. Hier würden das MacBook Air mit 13 Zoll sowie das MacBook Pro mit Touch Bar (klassische Form) gute Kandidaten sein. Auch der iMac M3 ist längst überfällig. Ein neues MacBook Pro mit M3 Max und M3 Pro ist hingegen ebenfalls eher etwas für das kommende Frühjahr; auf diesen Takt war Apple mit M2 Max und M2 Pro gewechselt.\nBei den M3-SoCs stellt sich die Frage der Lieferbarkeit. Zwar hat Apple das komplette Angebot an 3-nm-Produkten von TSMC in diesem Jahr erworben. Das heißt aber nicht automatisch, dass für mehr als iPhone 15 Pro und 15 Pro Max Stückzahlen vorhanden sind.\nApple braucht bessere Zahlen\nEigentlich wäre es für Apple gut, ein Oktober-Event zu veranstalten. In Sachen Mac- und iPad-Umsätze gibt es Nachholbedarf. Das aktuelle Line-up ist nicht stark genug, den Einbruch zu stoppen. Ob dazu jedoch solche "einfachen" Upgrades reichen, ist unklar.\nApple hatte in den Jahren 2021, 2020, 2018, 2016, 2014 und 2013 Keynotes im Oktober durchgeführt. Die Herbst-Events in den Jahren 2022, 2019, 2017 und 2015 fielen also seit 2013 immer mal wieder aus. Doch reicht es zu sagen, Apple wäre hier wieder "fällig"? Leider nein, derzeit ist der Konzern stark von äußerlichen Faktoren tangiert. Zudem ist bereits bekannt, dass die Vision Pro einige Ressourcen bindet, die sonst in die reguläre Hardware-Entwicklung geflossen wären.\nEmpfohlener redaktioneller Inhalt\nMit Ihrer Zustimmmung wird hier ein externer Preisvergleich (heise Preisvergleich) geladen.\nIch bin damit einverstanden, dass mir externe Inhalte angezeigt werden. Damit können personenbezogene Daten an Drittplattformen (heise Preisvergleich) übermittelt werden. Mehr dazu in unserer Datenschutzerklärung.\n(bsc)',
        published_date=datetime.datetime(2023, 10, 2, 9, 9, 0),
        author="",
        collected_date=datetime.datetime(2023, 10, 2, 7, 28, 57, 881310),
        osint_source_id="137571e0-db78-4b08-a88b-b41c1eda20cc",
        attributes=[],
    ),
    NewsItem(
        hash="104b10fdbbb52f88b1c62bafc08fbbcad322cc4c2c4dd1c9015fb823e2f597cc",
        title="Linux Mint Debian Edition (LMDE) 6 “Faye” veröffentlicht",
        review='Das Mint-Entwicklerteam hat zum 27. September 2023 die Linux-Distribution LMDE 6 "Faye" nach einer kurzen Beta-Phase zum Download freigegeben. Das Kürzel LMDE steht für "Linux Mint Debian Edition", also eine Edition, die sich nahe an Debian anlehnt . LMDE zielt … Weiterlesen',
        content='Das Mint-Entwicklerteam hat zum 27. September 2023 die Linux-Distribution LMDE 6 "Faye" nach einer kurzen Beta-Phase zum Download freigegeben. Das Kürzel LMDE steht für "Linux Mint Debian Edition", also eine Edition, die sich nahe an Debian anlehnt .\nAnzeige\nLMDE zielt darauf ab, Linux Mint so ähnlich wie möglich zu sein, ohne jedoch Ubuntu zu verwenden. Die Paketbasis wird daher von Debian bereitgestellt. Ziel der Entwickler ist es mit der LMDE-Edition sicherzustellen, dass Linux Mint in der Lage wäre, weiterhin die gleiche Benutzererfahrung zu bieten, für den Fall, dass Ubuntu verschwinden sollte. Mit LMDE soll auch sichergestellt werden, dass die vom Mint-Team entwickelte Software auch außerhalb von Ubuntu kompatibel ist.\nIn diesem Blog-Beitrag finden sich einige Informationen wie beispielsweise die Upgrade-Informationen zum Umstieg von LMDE 5 sowie die nachfolgenden Systemspezifikationen, die zum Betrieb von Linux Mint Debian Edition 6 benötigt werden:\n- 2 GB RAM (4 GB empfohlen für eine komfortable Nutzung).\n- 20 GB Festplattenspeicher (100 GB empfohlen).\n- 1024×768 Auflösung (bei niedrigeren Auflösungen können Sie die ALT-Taste drücken, um Fenster mit der Maus zu verschieben, wenn sie nicht auf den Bildschirm passen).\nDie Release Notes lassen sich auf dieser Webseite ansehen. Es gibt sowohl 64-Bit als auch 32-Bit-ISOs auf dieser Webseite via Torrent. Faye basiert auf Debian Bookworm und kommt als Long term support release (LTS). (via)\nCookies blockieren entzieht uns die Finanzierung: Cookie-Einstellungen',
        web_url="https://www.borncity.com/blog/2023/09/30/linux-mint-debian-edition-lmde-6-faye-verffentlicht/",
        published_date=datetime.datetime(2023, 9, 29, 22, 3, 0),
        author="Günter Born",
        collected_date=datetime.datetime(2023, 10, 1, 23, 53, 31, 888330),
        osint_source_id="c8c90206-f50c-47b3-bae0-371d67c9d82b",
        attributes=[],
    ),
]

include_list = [
    {
        "id": 1,
        "name": "includelist",
        "description": "dummy test data",
        "usage": ["COLLECTOR_INCLUDELIST", "TAGGING_BOT"],
        "link": "",
        "entries": [
            {"value": "Microsoft", "category": "CVE_VENDOR", "description": ""},
            {"value": "Azure Data Explorer", "category": "CVE_PRODUCT", "description": ""},
            {"value": "SDK", "category": "CVE_PRODUCT", "description": ""},
        ],
    }
]

exclude_list = [
    {
        "id": 2,
        "name": "excludelist",
        "description": "dummy test data",
        "usage": ["COLLECTOR_EXCLUDELIST", "TAGGING_BOT"],
        "link": "",
        "entries": [
            {"value": "Apple", "category": "CVE_VENDOR", "description": ""},
            {"value": "iPhone-Event", "category": "MISC", "description": ""},
        ],
    }
]

include_exclude_list = [
    {
        "id": 1,
        "name": "includelist",
        "description": "dummy test data",
        "usage": ["COLLECTOR_INCLUDELIST", "TAGGING_BOT"],
        "link": "",
        "entries": [
            {"value": "Microsoft", "category": "CVE_VENDOR", "description": ""},
            {"value": "Azure Data Explorer", "category": "CVE_PRODUCT", "description": ""},
            {"value": "SDK", "category": "CVE_PRODUCT", "description": ""},
        ],
    },
    {
        "id": 2,
        "name": "excludelist",
        "description": "dummy test data",
        "usage": ["COLLECTOR_EXCLUDELIST", "TAGGING_BOT"],
        "link": "",
        "entries": [
            {"value": "Apple", "category": "CVE_VENDOR", "description": ""},
            {"value": "iPhone-Event", "category": "MISC", "description": ""},
        ],
    },
]

multiple_include_exclude_list = [
    {
        "id": 1,
        "name": "includelist",
        "description": "dummy test data",
        "usage": ["COLLECTOR_INCLUDELIST", "TAGGING_BOT"],
        "link": "",
        "entries": [{"value": "Azure Data Explorer", "category": "CVE_PRODUCT", "description": ""}],
    },
    {
        "id": 2,
        "name": "includelist2",
        "description": "dummy test data 2",
        "usage": ["COLLECTOR_INCLUDELIST", "TAGGING_BOT"],
        "link": "",
        "entries": [{"value": "Bing", "category": "MISC", "description": ""}],
    },
    {
        "id": 3,
        "name": "excludelist",
        "description": "dummy test data",
        "usage": ["COLLECTOR_EXCLUDELIST", "TAGGING_BOT"],
        "link": "",
        "entries": [{"value": "iPhone-Event", "category": "MISC", "description": ""}],
    },
    {
        "id": 4,
        "name": "excludelist2",
        "description": "dummy test data",
        "usage": ["COLLECTOR_EXCLUDELIST", "TAGGING_BOT"],
        "link": "",
        "entries": [{"value": "Apple", "category": "CVE_VENDOR", "description": ""}],
    },
]

include_multiple_list = [
    {
        "id": 1,
        "name": "includelist",
        "description": "dummy test data",
        "usage": ["COLLECTOR_INCLUDELIST", "TAGGING_BOT"],
        "link": "",
        "entries": [{"value": "Azure Data Explorer", "category": "CVE_PRODUCT", "description": ""}],
    },
    {
        "id": 2,
        "name": "includelist2",
        "description": "dummy test data 2",
        "usage": ["COLLECTOR_INCLUDELIST", "TAGGING_BOT"],
        "link": "",
        "entries": [{"value": "Bing", "category": "MISC", "description": ""}],
    },
]

exclude_multiple_list = [
    {
        "id": 1,
        "name": "excludelist",
        "description": "dummy test data",
        "usage": ["COLLECTOR_EXCLUDELIST", "TAGGING_BOT"],
        "link": "",
        "entries": [{"value": "iPhone-Event", "category": "MISC", "description": ""}],
    },
    {
        "id": 2,
        "name": "excludelist2",
        "description": "dummy test data",
        "usage": ["COLLECTOR_EXCLUDELIST", "TAGGING_BOT"],
        "link": "",
        "entries": [{"value": "Apple", "category": "CVE_VENDOR", "description": ""}],
    },
]

web_collector_url = "https://raw.example.com/testweb.html"
web_collector_ref_url = "https://raw.example.com/test/url/index.html"
web_collector_result_content = "In an era where digital security is paramount, the role of National Computer Emergency Response Teams (CERTs) has never been more critical."
web_collector_fav_icon_url = "https://raw.example.com/favicon.ico"
web_collector_source_data = {"id": 1, "parameters": {"WEB_URL": "https://raw.example.com/testweb.html"}}
web_collector_source_xpath = "/html/body/div/div[3]"
web_collector_result_title = "National CERT Importance"

rss_collector_url = "https://rss.example.com/en/category/security-news/feed/"
rss_collector_source_data = {"id": 1, "parameters": {"FEED_URL": f"{rss_collector_url}"}}
rss_collector_source_data_complex = {
    "description": "",
    "id": "1",
    "last_attempted": "2000-01-01T00:00:00.000000",
    "last_collected": "2000-01-01T00:00:00.000000",
    "last_error_message": None,
    "name": "TestName",
    "parameters": {
        "ADDITIONAL_HEADERS": '{"User-Agent": "Chromium/1.0", "Authorization": "Bearer Token1234", "X-API-KEY": "12345", "Cookie": "firstcookie=1234; second-cookie=4321"}',
        "FEED_URL": f"{rss_collector_url}",
        "USER_AGENT": "Mozilla/5.0",
    },
    "state": 0,
    "type": "rss_collector",
    "word_lists": [],
}
rss_collector_url_not_modified = "https://rss.example.com/en/archive/feed/"
rss_collector_source_data_not_modified = {"id": 1, "parameters": {"FEED_URL": f"{rss_collector_url_not_modified}"}}

rss_collector_url_no_content = "https://rss.example.com/en/wrong-feed"
rss_collector_source_data_no_content = {"id": 1, "parameters": {"FEED_URL": f"{rss_collector_url_no_content}"}}

rss_collector_fav_icon_url = "https://rss.example.com/favicon.ico"
rss_collector_targets = [
    "https://ai-policy.eu/blog/2024/1/ai-regulation-framework",
    "https://greentechnews.org/blog/2024/2/green-tech-energy-sector",
    "https://space-eu.org/blog/2024/3/european-space-exploration",
]

head_request = {
    "Connection": "keep-alive",
    "Content-Length": "1111",
    "Server": "example.com",
    "Content-Type": "text/html; charset=utf-8",
    "Last-Modified": "Mon, 1 Jan 2000 12:00:00 GMT",
    "Access-Control-Allow-Origin": "*",
    "Strict-Transport-Security": "max-age=11111111",
    "ETag": 'W/"11111111-1111"',
    "expires": "Mon, 1 Jan 2000 12:00:00 GMT",
    "Cache-Control": "max-age=111",
    "Content-Encoding": "gzip",
    "x-proxy-cache": "MISS",
    "X-Example-Request-Id": "1111:111111:1111111:1111111:11111111",
    "Accept-Ranges": "bytes",
    "Date": "Mon, 1 Jan 2000 00:00:00 GMT",
    "Via": "1.1 varnish",
    "Age": "1",
    "X-Served-By": "cache-vie1111-VIE",
    "X-Cache": "HIT",
    "X-Cache-Hits": "1",
    "X-Timer": "S1111111111.111111,VS0,VE2",
    "Vary": "Accept-Encoding",
    "X-Fastly-Request-ID": "aa11111111111111111111111111111111111111",
}

headers = {
    "AUTHORIZATION": "Bearer Token1234",
    "X-API-KEY": "12345",
    "Cookie": "firstcookie=1234; second-cookie=4321",
}

proxies = {
    "http": "http://test_username:test_password@example.com:80",
    "https": "http://test_username:test_password@example.com:80",
    "ftp": "http://test_username:test_password@example.com:80",
}

proxies_empty = {"http": "", "https": "", "ftp": ""}

proxy_parse_result = {"server": "http://test_username:test_password@example.com:80", "username": "test_username", "password": "test_password"}
