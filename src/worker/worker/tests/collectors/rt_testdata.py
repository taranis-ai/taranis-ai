rt_collector_source_data = {"id": 1, "parameters": {"BASE_URL": "http://rt.taranis.ai/", "RT_TOKEN": "1-11-11111111111111111111111111111111"}}

rt_base_url = "http://rt.taranis.ai/REST/2.0/"
rt_ticket_search_url = f"{rt_base_url}tickets?query=*"
rt_ticket_search_result = {
    "total": 1,
    "count": 1,
    "page": 1,
    "items": [
        {"type": "ticket", "id": "1", "_url": "https://rt.taranis.ai/REST/2.0/ticket/1"},
    ],
    "per_page": 20,
    "pages": 1,
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
}

rt_history_url = f"{rt_base_url}ticket/1/history"
rt_ticket_history_1 = {
    "pages": 1,
    "per_page": 20,
    "items": [
        {"_url": "https://rt.taranis.ai/REST/2.0/transaction/1", "id": "1", "type": "transaction"},
        {"type": "transaction", "id": "2", "_url": "https://rt.taranis.ai/REST/2.0/transaction/2"},
    ],
    "page": 1,
    "total": 2,
    "count": 2,
}

rt_transaction_url = f"{rt_base_url}transaction/1"
rt_ticket_transaction_1 = {
    "Created": "2024-01-01T12:00:00Z",
    "id": 1,
    "Type": "Create",
    "Object": {"_url": "https://rt.taranis.ai/REST/2.0/ticket/1", "type": "ticket", "id": "1"},
    "Creator": {"_url": "https://rt.taranis.ai/REST/2.0/user/root", "type": "user", "id": "root"},
    "_hyperlinks": [
        {"id": 1, "type": "transaction", "_url": "https://rt.taranis.ai/REST/2.0/transaction/1", "ref": "self"},
        {"_url": "https://rt.taranis.ai/REST/2.0/attachment/1", "ref": "attachment"},
    ],
}

rt_attachment_url = f"{rt_base_url}attachment/1"
rt_ticket_attachment_1 = {
    "_hyperlinks": [{"ref": "self", "_url": "https://rt.taranis.ai/REST/2.0/attachment/1", "id": 1, "type": "attachment"}],
    "Creator": {"_url": "https://rt.taranis.ai/REST/2.0/user/root", "type": "user", "id": "root"},
    "MessageId": "rt-5.0.5-23-1707145019-227.0-0-0@example.com",
    "Content": "PHA+VGVzdCBUaWNrZXQgQ29udGVudDwvcD4K\n",
    "Subject": "Test Ticket 1",
    "ContentType": "text/html",
    "id": 1,
    "TransactionId": {"type": "transaction", "id": "1", "_url": "https://rt.taranis.ai/REST/2.0/transaction/1"},
    "Created": "2024-01-01T12:00:00Z",
}

rt_collector_result = {}
