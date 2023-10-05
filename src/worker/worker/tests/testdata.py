news_item_aggregate_1 = {
    "id": 1,
    "title": "Test Aggregate 1",
    "description": "CVE-2020-1234 - Test Aggregate 1",
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
        {
            "id": 13,
            "read": False,
            "important": False,
            "likes": 0,
            "dislikes": 0,
            "relevance": 0,
            "news_item_data_id": "4b9a5a9e-04d7-41fc-928f-99e5ad608ebb",
            "news_item_aggregate_id": 13,
            "news_item_data": {
                "id": "4b9a5a9e-04d7-41fc-928f-99e5ad608ebb",
                "hash": "a96e88baaff421165e90ac4bb9059971b86f88d5c2abba36d78a1264fb8e9c87",
                "title": "Test News Item 13",
                "review": "CVE-2020-1234 - Test Aggregate 1",
                "author": "",
                "source": "https://url/13",
                "link": "https://url/13",
                "language": None,
                "content": "CVE-2020-1234 - Test Aggregate 1",
                "collected": "2023-08-01T17:01:04.802015",
                "published": "2023-08-01T17:01:04.801998",
                "updated": "2023-08-01T17:00:39.893435",
                "osint_source_id": "78049551-dcef-45bd-a5cd-4fe842c4d5e2",
                "remote_source": None,
            },
        }
    ],
    "tags": {
        "CVE-2020-1234": {"name": "CVE-2020-1234", "tag_type": "CVE"},
        "Security": {"name": "Security", "tag_type": "MISC"},
    },
}

news_item_aggregate_2 = {
    "id": 2,
    "title": "Test Aggregate 2",
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
        {
            "id": 12,
            "read": False,
            "important": False,
            "likes": 0,
            "dislikes": 0,
            "relevance": 0,
            "news_item_data_id": "533086da-c8c1-4f8e-b3ee-103268983580",
            "news_item_aggregate_id": 12,
            "news_item_data": {
                "id": "533086da-c8c1-4f8e-b3ee-103268983580",
                "hash": "f4c7b52ecfe6ab612db30e7fa534b470fd11493fc92f30575577b356b2a1abc7",
                "title": "Test News Item 12",
                "review": "Long and random text - bla bla foo bar lorem ipsum",
                "author": "",
                "source": "https://url/12",
                "link": "https://url/12",
                "language": None,
                "content": "Long and random text - bla bla foo bar lorem ipsum",
                "collected": "2023-08-01T17:01:04.801951",
                "published": "2023-08-01T17:01:04.801934",
                "updated": "2023-08-01T17:00:39.893435",
                "osint_source_id": "78049551-dcef-45bd-a5cd-4fe842c4d5e2",
                "remote_source": None,
            },
        }
    ],
    "tags": {},
}
news_item_aggregate_3 = (
    {
        "id": 3,
        "title": "Test Aggregarte Number 3",
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
            {
                "id": 11,
                "read": False,
                "important": False,
                "likes": 0,
                "dislikes": 0,
                "relevance": 0,
                "news_item_data_id": "809f93ef-f00e-423b-89f8-59b917a9e039",
                "news_item_aggregate_id": 11,
                "news_item_data": {
                    "id": "809f93ef-f00e-423b-89f8-59b917a9e039",
                    "hash": "599fafee5eeb098239c57c78bf5cea6ea52b0e92a1abc9e80964150a3773f135",
                    "title": "Test News Item 11",
                    "review": "Cyber Cyber Cyber - Security Security Security",
                    "author": "",
                    "source": "https://url/11",
                    "link": "https://url/11",
                    "language": None,
                    "content": "Cyber Cyber Cyber - Security Security Security",
                    "collected": "2023-08-01T17:01:04.801886",
                    "published": "2023-08-01T17:01:04.801870",
                    "updated": "2023-08-01T17:00:39.893435",
                    "osint_source_id": "78049551-dcef-45bd-a5cd-4fe842c4d5e2",
                },
            }
        ],
        "tags": {
            "Azure": {"name": "Azure", "tag_type": "MISC"},
            "Europe": {"name": "Mein Highlight", "tag_type": "LOC"},
            "Microsoft": {"name": "Microsoft", "tag_type": "ORG"},
        },
    },
)

news_item_list = [news_item_aggregate_1, news_item_aggregate_2, news_item_aggregate_3]

news_item_tags_1 = {"Cyber": {"name": "Cyber", "tag_type": "CySec"}}
news_item_tags_2 = {"Security": {"name": "Security", "tag_type": "Misc"}}
news_item_tags_3 = {"New Orleans": {"name": "New Orleans", "tag_type": "LOC"}}
news_item_tags_4 = {"CVE": {"name": "CVE", "tag_type": "CySec"}}
news_item_tags_5 = {"CVE-2021-1234": {"name": "CVE-2021-1234", "tag_type": "CVE"}}

news_items = [
    {
        "id": "544ac8f3-af17-44ba-a426-d04906f8ebcf",
        "hash": "e30c292902a87b51ae587b3dc046369b5e8bd4c0f85d04a6ec5e1e8b97df0b0f",
        "title": "Getting started with Microsoft Azure Data Explorer Add-On for Splunk",
        "review": 'Microsoft Azure Data Explorer Add-On for Splunk allows users to effortlessly ingest data from Splunk to Azure Data Explorer which is a fast and scalable data analytics platform designed for real-time analysis of large volumes of data. \n \nThe following kinds of data are most suitable for ingestion into Azure Data Explorer, but are not limited to the following list:\n\nHigh-Volume Data: Azure Data Explorer is built to handle vast amounts of data efficiently. If your organization generates a significant volume of data that needs real-time analysis, Azure Data Explorer is a suitable choice. \nTime-Series Data: Azure Data Explorer excels at handling time-series data, such as logs, telemetry data, and sensor readings. It organizes data in time-based partitions, making it easy to perform time-based analysis and aggregations. \nReal-Time Analytics: If your organization requires real-time insights from the data flowing in, Azure Data Explorer\'s near real-time capabilities can be beneficial.\n\nIngesting Data from Splunk to Azure Data Explorer using Azure Data Explorer Addon\n \nMicrosoft Azure Data Explorer Add-On for Splunk allows Azure Data Explorer users to ingest logs from Splunk platform using the Kusto Python SDK.\nDetails on pre-requisites, configuring the add-on and viewing the data in Azure Data Explorer is covered in this section.\n \nBackground\n \nWhen we add data to Splunk, the Splunk indexer processes it and stores it in a designated index (either, by default, in the main index or custom index). Searching in Splunk involves using the indexed data for the purpose of creating metrics, dashboards and alerts. This Splunk add-on triggers an action based on the alert in Splunk. We can use Alert actions to send data to Azure Data Explorer using the specified addon.\n \nThis add-on uses kusto python sdk (https://learn.microsoft.com/en-us/azure/data-explorer/kusto/api/python/kusto-python-client-library) to send log data to Microsoft Azure Data Explorer. Hence, this addon supports queued mode of ingestion by default. This addon has a durable feature as well which helps to minimize data loss during any unexpected network error scenarios. Although durability in ingestion comes at the cost of throughput, therefore it is advised to use this option judiciously.\n \nPrerequisites\n \n\nA Splunk Enterprise instance (Platform Version v9.0 and above) with the required installation privileges to configure add-ons.\nAccess to an Azure Data Explorer cluster.\n\n \nStep 1: Install the Azure Data Explorer Addon\n \n\nDownload the Azure Data Explorer Addon from the Splunkbase website.\nLog in to your Splunk instance as an administrator.\nNavigate to "Apps" and click on "Manage Apps."\nClick on "Install app from file" and select the downloaded Splunk Addon for Azure Data Explorer file.\nFollow the prompts to complete the installation\n\nAfter installation of the Splunk Addon for alerts, it should be visible in the Dashboard -> Alert Actions\n \n\n \nStep 2: Create Splunk Index\n \n\nLog in to your Splunk instance.\nNavigate to "Settings" and click on "Indexes."\nClick on "New Index" to create a new index.\nProvide a name for the index and configure the necessary settings (e.g., retention period, data model, etc.).\nSave the index configuration.\n\n \nStep 3: Configure Splunk Addon for Azure Data Explorer\n \n\nIn Splunk dashboard, Enter your search query in the Search bar based on which alerts will be generated and this alert data will be ingested to Azure Data Explorer.\nClick on Save As and select Alert.\nProvide a name for the alert and provide the interval at which the alert should be triggered.\nSelect the alert action as "Send to Microsoft Azure Data Explorer".\n\n\xa0\n\n\xa0\n5. Configure the Azure Data Explorer connection details such as application client Id, application client secret, cluster name, database name, table name.\n\n\xa0\n\xa06.\xa0When the alert is created, it should be visible in Splunk Dashboard -> Alerts\n\n\xa0\nStep 4: Verify data in Azure Data Explorer\n\xa0\n\nStart monitoring the Azure Data Explorer logs to ensure proper data ingestion.\nOnce the alert is triggered in Splunk, the data will be ingested to Azure Data Explorer.\nVerify the data in Azure Data Explorer using the database and table name in the previous step.\n\n\n\xa0\nAzure Data Explorer Addon Parameters\n\xa0\nThe following is the list of parameters which need to be entered/selected while configuring the addon:\n\nAzure Cluster Ingestion URL: Represents the ingestion URL of the Azure Data Explorer cluster in the ADX portal.\nAzure Application Client Id: Represents the Azure Application Client Id credentials required to access the Azure Data Explorer cluster.\nAzure Application Client secret: Represents the Azure Application Client secret credentials required to access the Azure Data Explorer cluster.\nAzure Application Tenant Id: Represents the Azure Application Tenant Id required to access the Azure Data Explorer cluster.\nAzure Data Explorer Database Name: This represents the name of the database created in the Azure Data Explorer cluster, where we want our data to be ingested.\nAzure Data Explorer Table Name: This represents the name of the table inside the database created in the Azure Data Explorer cluster, where we want our data to be ingested.\nAzure Data Explorer Table Mapping Name: This represents the Azure Data Explorer table mapping used to map to the column of created Azure Data Explorer table.\nRemove Extra Fields: This represents whether we want to remove empty fields in the splunk event payload\nDurable Mode: This property specifies whether durability mode is required during ingestion. When set to true, the ingestion throughput is impacted.\n\n\xa0\nPlease refer to the following links for further details:Link to Splunk Base Addon :\xa0Microsoft Azure Data Explorer Add-On for Splunk | Splunkbase\nLink to Github Source code of Addon:\xa0azure-kusto-splunk/splunk-adx-alert-addon at main · Azure/azure-kusto-splunk (github.com)\n\xa0\nConclusion\n\xa0\nIn this blog post, we have seen how Microsoft Azure Data Explorer Add-On for Splunk can help us ingest data from Splunk to Azure Data Explorer, a powerful data analytics platform. We have also learned about the types of data that are most suitable for Azure Data Explorer, and how to configure the add-on and use alert actions to send data to Azure Data Explorer. By using this add-on, we can leverage the benefits of both Splunk and Azure Data Explorer, and gain deeper insights from our data.',
        "source": "https://techcommunity.microsoft.com/plugins/custom/microsoft/o365/custom-blog-rss?tid%3D-1562856755638734148&amp%3Bboard%3DExchange&amp%3Blabel%3DSecurity&amp%3Bmessages%3D&amp%3Bsize%3D30",
        "link": "https://techcommunity.microsoft.com/t5/azure-data-explorer-blog/getting-started-with-microsoft-azure-data-explorer-add-on-for/ba-p/3917176",
        "published": "2023-10-01T18:00:00",
        "author": "tanmayapanda",
        "collected": "2023-10-02T02:03:46.763784",
        "content": 'Microsoft Azure Data Explorer Add-On for Splunk allows users to effortlessly ingest data from Splunk to Azure Data Explorer which is a fast and scalable data analytics platform designed for real-time analysis of large volumes of data. \n \nThe following kinds of data are most suitable for ingestion into Azure Data Explorer, but are not limited to the following list:\n\nHigh-Volume Data: Azure Data Explorer is built to handle vast amounts of data efficiently. If your organization generates a significant volume of data that needs real-time analysis, Azure Data Explorer is a suitable choice. \nTime-Series Data: Azure Data Explorer excels at handling time-series data, such as logs, telemetry data, and sensor readings. It organizes data in time-based partitions, making it easy to perform time-based analysis and aggregations. \nReal-Time Analytics: If your organization requires real-time insights from the data flowing in, Azure Data Explorer\'s near real-time capabilities can be beneficial.\n\nIngesting Data from Splunk to Azure Data Explorer using Azure Data Explorer Addon\n \nMicrosoft Azure Data Explorer Add-On for Splunk allows Azure Data Explorer users to ingest logs from Splunk platform using the Kusto Python SDK.\nDetails on pre-requisites, configuring the add-on and viewing the data in Azure Data Explorer is covered in this section.\n \nBackground\n \nWhen we add data to Splunk, the Splunk indexer processes it and stores it in a designated index (either, by default, in the main index or custom index). Searching in Splunk involves using the indexed data for the purpose of creating metrics, dashboards and alerts. This Splunk add-on triggers an action based on the alert in Splunk. We can use Alert actions to send data to Azure Data Explorer using the specified addon.\n \nThis add-on uses kusto python sdk (https://learn.microsoft.com/en-us/azure/data-explorer/kusto/api/python/kusto-python-client-library) to send log data to Microsoft Azure Data Explorer. Hence, this addon supports queued mode of ingestion by default. This addon has a durable feature as well which helps to minimize data loss during any unexpected network error scenarios. Although durability in ingestion comes at the cost of throughput, therefore it is advised to use this option judiciously.\n \nPrerequisites\n \n\nA Splunk Enterprise instance (Platform Version v9.0 and above) with the required installation privileges to configure add-ons.\nAccess to an Azure Data Explorer cluster.\n\n \nStep 1: Install the Azure Data Explorer Addon\n \n\nDownload the Azure Data Explorer Addon from the Splunkbase website.\nLog in to your Splunk instance as an administrator.\nNavigate to "Apps" and click on "Manage Apps."\nClick on "Install app from file" and select the downloaded Splunk Addon for Azure Data Explorer file.\nFollow the prompts to complete the installation\n\nAfter installation of the Splunk Addon for alerts, it should be visible in the Dashboard -> Alert Actions\n \n\n \nStep 2: Create Splunk Index\n \n\nLog in to your Splunk instance.\nNavigate to "Settings" and click on "Indexes."\nClick on "New Index" to create a new index.\nProvide a name for the index and configure the necessary settings (e.g., retention period, data model, etc.).\nSave the index configuration.\n\n \nStep 3: Configure Splunk Addon for Azure Data Explorer\n \n\nIn Splunk dashboard, Enter your search query in the Search bar based on which alerts will be generated and this alert data will be ingested to Azure Data Explorer.\nClick on Save As and select Alert.\nProvide a name for the alert and provide the interval at which the alert should be triggered.\nSelect the alert action as "Send to Microsoft Azure Data Explorer".\n\n\xa0\n\n\xa0\n5. Configure the Azure Data Explorer connection details such as application client Id, application client secret, cluster name, database name, table name.\n\n\xa0\n\xa06.\xa0When the alert is created, it should be visible in Splunk Dashboard -> Alerts\n\n\xa0\nStep 4: Verify data in Azure Data Explorer\n\xa0\n\nStart monitoring the Azure Data Explorer logs to ensure proper data ingestion.\nOnce the alert is triggered in Splunk, the data will be ingested to Azure Data Explorer.\nVerify the data in Azure Data Explorer using the database and table name in the previous step.\n\n\n\xa0\nAzure Data Explorer Addon Parameters\n\xa0\nThe following is the list of parameters which need to be entered/selected while configuring the addon:\n\nAzure Cluster Ingestion URL: Represents the ingestion URL of the Azure Data Explorer cluster in the ADX portal.\nAzure Application Client Id: Represents the Azure Application Client Id credentials required to access the Azure Data Explorer cluster.\nAzure Application Client secret: Represents the Azure Application Client secret credentials required to access the Azure Data Explorer cluster.\nAzure Application Tenant Id: Represents the Azure Application Tenant Id required to access the Azure Data Explorer cluster.\nAzure Data Explorer Database Name: This represents the name of the database created in the Azure Data Explorer cluster, where we want our data to be ingested.\nAzure Data Explorer Table Name: This represents the name of the table inside the database created in the Azure Data Explorer cluster, where we want our data to be ingested.\nAzure Data Explorer Table Mapping Name: This represents the Azure Data Explorer table mapping used to map to the column of created Azure Data Explorer table.\nRemove Extra Fields: This represents whether we want to remove empty fields in the splunk event payload\nDurable Mode: This property specifies whether durability mode is required during ingestion. When set to true, the ingestion throughput is impacted.\n\n\xa0\nPlease refer to the following links for further details:Link to Splunk Base Addon :\xa0Microsoft Azure Data Explorer Add-On for Splunk | Splunkbase\nLink to Github Source code of Addon:\xa0azure-kusto-splunk/splunk-adx-alert-addon at main · Azure/azure-kusto-splunk (github.com)\n\xa0\nConclusion\n\xa0\nIn this blog post, we have seen how Microsoft Azure Data Explorer Add-On for Splunk can help us ingest data from Splunk to Azure Data Explorer, a powerful data analytics platform. We have also learned about the types of data that are most suitable for Azure Data Explorer, and how to configure the add-on and use alert actions to send data to Azure Data Explorer. By using this add-on, we can leverage the benefits of both Splunk and Azure Data Explorer, and gain deeper insights from our data.',
        "osint_source_id": "3b876031-fab5-4144-ad8b-4ce49c5cd77f",
        "attributes": [],
    },
    {
        "id": "0b1919fe-98a6-4187-ac25-7b440f1a4cef",
        "hash": "ad118e4a6674120e66ffabb4f2da9d4f9ce59b9685477ab4a16f5616557fdbfc",
        "title": "Microsoft wollte Apple die Suchmaschine Bing verkaufen",
        "review": "Es geht um viel Geld, wenn die großen Tech-Konzerne pokern, und Apple schien in Gesprächen bezüglich Suchmaschinen zuletzt die besten Karten gehabt zu haben",
        "source": "https://www.derstandard.at/rss/web",
        "link": "https://www.derstandard.at/story/3000000189103/microsoft-wollte-apple-die-suchmaschine-bing-verkaufen?ref%3Drss",
        "published": "2023-09-30T05:00:00",
        "author": "",
        "collected": "2023-10-01T23:56:49.738398",
        "content": "Es war ein verregneter Tag im Jahr 2020, als sich mehrere hochrangige Vertreter von Microsoft und Apple unter Ausschluss der Öffentlichkeit zusammensetzten. Grund des Meetings war eine Idee von Microsoft, die Suchmaschine Bing an Apple zu verkaufen. Der iPhone-Konzern scheint allerdings diese Idee nie ernsthaft in Erwägung gezogen zu haben.\nIT-Business\nMicrosoft wollte Apple die Suchmaschine Bing verkaufen\nEs geht um viel Geld, wenn die großen Tech-Konzerne pokern, und Apple schien in Gesprächen bezüglich Suchmaschinen zuletzt die besten Karten gehabt zu haben",
        "osint_source_id": "eca31075-949d-40c7-83a3-300ed3433716",
        "attributes": [],
    },
    {
        "id": "544ac8f3-af17-44ba-a426-d04906f8ebcf",
        "hash": "c3a3c34282f6116eaa05d7bd3c7a1e3610e8a0f76d6e4e5366010f9506b1532a",
        "title": "Kommt noch ein Oktober-Event von Apple?",
        "review": "Die Gerüchteküche glaubt fest daran, dass Apple in diesem Monat noch neue Hardware vorstellen wird. Doch reicht es für eine Keynote?",
        "source": "https://www.heise.de/rss/heise-atom.xml",
        "link": "https://www.heise.de/news/Kommt-noch-ein-Oktober-Event-von-Apple-9321813.html?wt_mc%3Drss.red.ho.ho.atom.beitrag.beitrag",
        "published": "2023-10-02T09:09:00",
        "author": "",
        "collected": "2023-10-02T07:28:57.881310",
        "content": 'Kommt noch ein Oktober-Event von Apple?\nDie Gerüchteküche glaubt fest daran, dass Apple in diesem Monat noch neue Hardware vorstellen wird. Doch reicht es für eine Keynote?\n- Ben Schwan\nDer Oktober ist da – und Apple-Interessierte fragen sich, ob Apple ein viertes Event für 2023 plant. Typischerweise gibt es Keynotes an vier Terminen im Jahr: Eine im Frühjahr, eine im Juni zur Entwicklerkonferenz WWDC, das iPhone-Event im September und – häufig – ein eigenes iPad- und/oder Mac-Event im Oktober. Doch in diesem Jahr könnte das langsame Vorankommen bei den ersten M3-Maschinen nur wenige neue Produkte bringen. Das könnte für eine Keynote nicht ausreichen.\nWas noch fehlt\nAktuell rechnen die meisten Beobachter damit, dass Apple höchstens am iPad schraubt. Hier stünden ein neues iPad Air, ein iPad 11 für Einsteiger und ein neues iPad mini zur Diskussion. Alle drei Updates dürften eher "minor" ausfallen, also mit leichten Verbesserungen des Innenlebens. Genau das spricht wiederum dafür, dass Apple sie nur per Pressemitteilung vorstellt. Von einem iPad Pro mit M3-SoC und OLED-Schirm ist frühestens für Anfang kommenden Jahres die Rede.\nBeim Mac wird auf ein erstes M3-Modell gewartet. Hier würden das MacBook Air mit 13 Zoll sowie das MacBook Pro mit Touch Bar (klassische Form) gute Kandidaten sein. Auch der iMac M3 ist längst überfällig. Ein neues MacBook Pro mit M3 Max und M3 Pro ist hingegen ebenfalls eher etwas für das kommende Frühjahr; auf diesen Takt war Apple mit M2 Max und M2 Pro gewechselt.\nBei den M3-SoCs stellt sich die Frage der Lieferbarkeit. Zwar hat Apple das komplette Angebot an 3-nm-Produkten von TSMC in diesem Jahr erworben. Das heißt aber nicht automatisch, dass für mehr als iPhone 15 Pro und 15 Pro Max Stückzahlen vorhanden sind.\nApple braucht bessere Zahlen\nEigentlich wäre es für Apple gut, ein Oktober-Event zu veranstalten. In Sachen Mac- und iPad-Umsätze gibt es Nachholbedarf. Das aktuelle Line-up ist nicht stark genug, den Einbruch zu stoppen. Ob dazu jedoch solche "einfachen" Upgrades reichen, ist unklar.\nApple hatte in den Jahren 2021, 2020, 2018, 2016, 2014 und 2013 Keynotes im Oktober durchgeführt. Die Herbst-Events in den Jahren 2022, 2019, 2017 und 2015 fielen also seit 2013 immer mal wieder aus. Doch reicht es zu sagen, Apple wäre hier wieder "fällig"? Leider nein, derzeit ist der Konzern stark von äußerlichen Faktoren tangiert. Zudem ist bereits bekannt, dass die Vision Pro einige Ressourcen bindet, die sonst in die reguläre Hardware-Entwicklung geflossen wären.\nEmpfohlener redaktioneller Inhalt\nMit Ihrer Zustimmmung wird hier ein externer Preisvergleich (heise Preisvergleich) geladen.\nIch bin damit einverstanden, dass mir externe Inhalte angezeigt werden. Damit können personenbezogene Daten an Drittplattformen (heise Preisvergleich) übermittelt werden. Mehr dazu in unserer Datenschutzerklärung.\n(bsc)',
        "osint_source_id": "137571e0-db78-4b08-a88b-b41c1eda20cc",
        "attributes": [],
    },
    {
        "id": "10a93aab-ed94-4696-a04a-2c5e6f703058",
        "hash": "104b10fdbbb52f88b1c62bafc08fbbcad322cc4c2c4dd1c9015fb823e2f597cc",
        "title": "Linux Mint Debian Edition (LMDE) 6 “Faye” veröffentlicht",
        "review": 'Das Mint-Entwicklerteam hat zum 27. September 2023 die Linux-Distribution LMDE 6 "Faye" nach einer kurzen Beta-Phase zum Download freigegeben. Das Kürzel LMDE steht für "Linux Mint Debian Edition", also eine Edition, die sich nahe an Debian anlehnt . LMDE zielt … Weiterlesen',
        "source": "https://www.borncity.com/blog/feed/",
        "link": "https://www.borncity.com/blog/2023/09/30/linux-mint-debian-edition-lmde-6-faye-verffentlicht/",
        "published": "2023-09-29T22:03:00",
        "author": "Günter Born",
        "collected": "2023-10-01T23:53:31.888330",
        "content": 'Das Mint-Entwicklerteam hat zum 27. September 2023 die Linux-Distribution LMDE 6 "Faye" nach einer kurzen Beta-Phase zum Download freigegeben. Das Kürzel LMDE steht für "Linux Mint Debian Edition", also eine Edition, die sich nahe an Debian anlehnt .\nAnzeige\nLMDE zielt darauf ab, Linux Mint so ähnlich wie möglich zu sein, ohne jedoch Ubuntu zu verwenden. Die Paketbasis wird daher von Debian bereitgestellt. Ziel der Entwickler ist es mit der LMDE-Edition sicherzustellen, dass Linux Mint in der Lage wäre, weiterhin die gleiche Benutzererfahrung zu bieten, für den Fall, dass Ubuntu verschwinden sollte. Mit LMDE soll auch sichergestellt werden, dass die vom Mint-Team entwickelte Software auch außerhalb von Ubuntu kompatibel ist.\nIn diesem Blog-Beitrag finden sich einige Informationen wie beispielsweise die Upgrade-Informationen zum Umstieg von LMDE 5 sowie die nachfolgenden Systemspezifikationen, die zum Betrieb von Linux Mint Debian Edition 6 benötigt werden:\n- 2 GB RAM (4 GB empfohlen für eine komfortable Nutzung).\n- 20 GB Festplattenspeicher (100 GB empfohlen).\n- 1024×768 Auflösung (bei niedrigeren Auflösungen können Sie die ALT-Taste drücken, um Fenster mit der Maus zu verschieben, wenn sie nicht auf den Bildschirm passen).\nDie Release Notes lassen sich auf dieser Webseite ansehen. Es gibt sowohl 64-Bit als auch 32-Bit-ISOs auf dieser Webseite via Torrent. Faye basiert auf Debian Bookworm und kommt als Long term support release (LTS). (via)\nCookies blockieren entzieht uns die Finanzierung: Cookie-Einstellungen',
        "osint_source_id": "c8c90206-f50c-47b3-bae0-371d67c9d82b",
        "attributes": [],
    },
]

source_include_list = {
    "id": "05cd3b9b-5480-4c31-8818-9973504d7542",
    "name": "0patch Blog",
    "description": "Security Patching Simplified To The Extreme",
    "type": "rss_collector",
    "state": 0,
    "last_collected": "2023-09-22T11:43:41.859559",
    "last_attempted": "2023-09-22T11:43:41.859519",
    "last_error_message": None,
    "word_lists": [
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
    ],
    "parameters": {"FEED_URL": ""},
}

source_exclude_list = {
    "id": "05cd3b9b-5480-4c31-8818-9973504d7543",
    "name": "0patch Blog",
    "description": "Security Patching Simplified To The Extreme",
    "type": "rss_collector",
    "state": 0,
    "last_collected": "2023-09-22T11:43:41.859559",
    "last_attempted": "2023-09-22T11:43:41.859519",
    "last_error_message": None,
    "word_lists": [
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
    ],
    "parameters": {"FEED_URL": ""},
}

source_include_list_exclude_list = {
    "id": "05cd3b9b-5480-4c31-8818-9973504d7542",
    "name": "0patch Blog",
    "description": "Security Patching Simplified To The Extreme",
    "type": "rss_collector",
    "state": 0,
    "last_collected": "2023-09-22T11:43:41.859559",
    "last_attempted": "2023-09-22T11:43:41.859519",
    "last_error_message": None,
    "word_lists": [
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
    ],
    "parameters": {"FEED_URL": ""},
}

source_empty_wordlist = {
    "id": "05cd3b9b-5480-4c31-8818-9973504d7542",
    "name": "0patch Blog",
    "description": "Security Patching Simplified To The Extreme",
    "type": "rss_collector",
    "state": 0,
    "last_collected": "2023-09-22T11:43:41.859559",
    "last_attempted": "2023-09-22T11:43:41.859519",
    "last_error_message": None,
    "word_lists": [],
    "parameters": {"FEED_URL": ""},
}

source_include_multiple_list_exclude_multiple_list = {
    "id": "05cd3b9b-5480-4c31-8818-9973504d7542",
    "name": "0patch Blog",
    "description": "Security Patching Simplified To The Extreme",
    "type": "rss_collector",
    "state": 0,
    "last_collected": "2023-09-22T11:43:41.859559",
    "last_attempted": "2023-09-22T11:43:41.859519",
    "last_error_message": None,
    "word_lists": [
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
    ],
    "parameters": {"FEED_URL": ""},
}

source_include_multiple_list = {
    "id": "05cd3b9b-5480-4c31-8818-9973504d7542",
    "name": "0patch Blog",
    "description": "Security Patching Simplified To The Extreme",
    "type": "rss_collector",
    "state": 0,
    "last_collected": "2023-09-22T11:43:41.859559",
    "last_attempted": "2023-09-22T11:43:41.859519",
    "last_error_message": None,
    "word_lists": [
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
    ],
    "parameters": {"FEED_URL": ""},
}

source_exclude_multiple_list = {
    "id": "05cd3b9b-5480-4c31-8818-9973504d7542",
    "name": "0patch Blog",
    "description": "Security Patching Simplified To The Extreme",
    "type": "rss_collector",
    "state": 0,
    "last_collected": "2023-09-22T11:43:41.859559",
    "last_attempted": "2023-09-22T11:43:41.859519",
    "last_error_message": None,
    "word_lists": [
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
    ],
    "parameters": {"FEED_URL": ""},
}
