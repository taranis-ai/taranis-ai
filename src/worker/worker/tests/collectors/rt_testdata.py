from worker.config import Config

rt_collector_source_data = {
    "id": 1,
    "parameters": {
        "BASE_URL": "http://rt.taranis.ai/",
        "RT_TOKEN": "1-11-11111111111111111111111111111111",
        "SEARCH_QUERY": "Started > '2018-04-04' AND Status != 'resolved'",
        "FIELDS_TO_INCLUDE": "One, Two, Three, Four",
    },
}

favicon_url = "http://rt.taranis.ai/static/images/favicon.png"
rt_base_url = "http://rt.taranis.ai/REST/2.0/"
rt_ticket_search_url = f"{rt_base_url}tickets?query=Started%20%3E%20'2018-04-04'%20AND%20Status%20!=%20'resolved'"
rt_ticket_search_result = {
    "total": 1,
    "count": 1,
    "page": 1,
    "items": [
        {"type": "ticket", "id": "1", "_url": f"{rt_base_url}/ticket/1"},
    ],
    "per_page": 20,
    "pages": 1,
}

rt_no_tickets_url = f"{rt_base_url}tickets?query=Started%20%3E%20'2018-04-04'%20AND%20Started%20%3C%20'2018-04-06'"
rt_collector_no_tickets_source_data = {
    "id": 1,
    "parameters": {
        "BASE_URL": f"{rt_base_url}",
        "RT_TOKEN": "1-11-11111111111111111111111111111111",
        "SEARCH_QUERY": "Started > '2018-04-04' AND Started < '2018-04-06'",
        "FIELDS_TO_INCLUDE": "One, Two, Three, Four",
    },
}

rt_malformed_json_url = f"{rt_base_url}tickets?query=Started%20%3E%20'2018-04-04'%20AND%20Started%20%3C%20''"
rt_malformed_json_source_data = {
    "id": 1,
    "parameters": {
        "BASE_URL": f"{rt_base_url}",
        "RT_TOKEN": "1-11-11111111111111111111111111111111",
        "SEARCH_QUERY": "Started > '2018-04-04' AND Started < ''",
        "FIELDS_TO_INCLUDE": "",
    },
}

rt_ticket_url = f"{rt_base_url}ticket/1"
rt_ticket_1 = {
    "Type": "ticket",
    "Creator": {
        "type": "user",
        "id": "root",
    },
    "Due": "1970-01-01T00:00:00Z",
    "EffectiveId": {"id": "1", "type": "ticket"},
    "LastUpdated": "2024-01-01T12:00:00Z",
    "Starts": "1970-01-01T00:00:00Z",
    "Resolved": "1970-01-01T00:00:00Z",
    "LastUpdatedBy": {"type": "user", "id": "root"},
    "Started": "1970-01-01T00:00:00Z",
    "Requestor": [{"id": "root", "type": "user"}],
    "id": 1,
    "Status": "new",
    "Owner": {
        "id": "Nobody",
        "type": "user",
    },
    "Subject": "Test Ticket 1",
    "Queue": {"type": "queue", "id": "1"},
    "Created": "2024-01-01T12:00:00Z",
    "_hyperlinks": [
        {"id": "5", "_url": f"{rt_base_url}ticket/1", "type": "ticket", "ref": "self"},
        {"type": "customfield", "ref": "customfield", "id": "1", "name": "Email", "_url": f"{rt_base_url}customfield/1"},
    ],
    "CustomFields": [
        {"type": "customfield", "values": ["127.0.0.1"], "id": "27", "name": "IP", "_url": f"{rt_base_url}customfield/27"},
    ],
}

rt_attachment_1_url = f"{rt_base_url}attachment/1"
rt_ticket_attachment_1 = {
    "_hyperlinks": [{"ref": "self", "_url": f"{rt_base_url}attachment/1", "id": 1, "type": "attachment"}],
    "Creator": {"_url": f"{rt_base_url}user/root", "type": "user", "id": "root"},
    "MessageId": "rt-5.0.5-23-1707145019-227.0-0-0@example.com",
    "Content": "PHA+VGVzdCBUaWNrZXQgQ29udGVudDwvcD4K\n",
    "Subject": "Test Ticket 1",
    "ContentType": "text/html",
    "id": 1,
    "TransactionId": {"type": "transaction", "id": "1", "_url": f"{rt_base_url}transaction/1"},
    "Created": "2024-01-01T12:00:00Z",
}

rt_ticket_attachments_url = f"{rt_base_url}ticket/1/attachments"
rt_ticket_attachments = {
    "pages": 1,
    "items": [
        {"type": "attachment", "id": "1", "_url": f"{rt_base_url}attachment/1"},
    ],
    "page": 1,
    "per_page": 20,
    "count": 1,
    "total": 1,
}
worker_stories_url = f"{Config.TARANIS_CORE_URL}/worker/stories?source=1"
