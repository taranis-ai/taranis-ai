email_publisher_admin_input = {
    "parameters": {
        "SMTP_SERVER_ADDRESS": "localhost",
        "SMTP_SERVER_PORT": 1025,
        "SERVER_TLS": False,
        "EMAIL_USERNAME": "",
        "EMAIL_PASSWORD": "",
        "EMAIL_SENDER": "sender@email.com",
        "EMAIL_RECIPIENT": "recipient@test.ai",
        "EMAIL_SUBJECT": "Test email subject",
    }
}

email_publisher_admin_input_no_smtp_address = {
    "parameters": {
        "SMTP_SERVER_ADDRESS": "",
        "SMTP_SERVER_PORT": 1025,
        "SERVER_TLS": False,
        "EMAIL_USERNAME": "",
        "EMAIL_PASSWORD": "",
        "EMAIL_SENDER": "sender@email.com",
        "EMAIL_RECIPIENT": "recipient@test.ai",
        "EMAIL_SUBJECT": "Test email subject",
    }
}


product_text = {
    "id": 1,
    "title": "Test_Text_Product",
    "type": "text_presenter",
    "type_id": 3,
    "mime_type": "text/plain",
    "report_items": [{"title": "test title"}],
}


sftp_test_private_key = """-----BEGIN OPENSSH PRIVATE KEY-----
b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAAAMwAAAAtzc2gtZW
QyNTUxOQAAACCOYlx3sXknINVUCZhDebq9NPgyncOjTGYMf/wEVkUbSwAAAJD/HjmA/x45
gAAAAAtzc2gtZWQyNTUxOQAAACCOYlx3sXknINVUCZhDebq9NPgyncOjTGYMf/wEVkUbSw
AAAEB9QKeLmRTBGWF0899ndYZzD7HC7vMDdL8CVe5tlXgbO45iXHexeScg1VQJmEN5ur00
+DKdw6NMZgx//ARWRRtLAAAADWJlbkBsM2RzczIxMDM=
-----END OPENSSH PRIVATE KEY-----
"""

product_render_data = b"# VULNERABILITY REPORT\nID: 1\nUUID:33a23a37-ec4c-42e9-b43a-1a65d32e83e7\nTITLE: hi\nCREATED: 2024-03-25T14:02:59.607682\nLAST_UPDATED: 2024-03-25T14:02:59.607687\nCOMPLETED: False\nUSER_ID: 1\nREPORT_ITEM_TYPE_ID: 3\n## ATTRIBUTES:\n\n## STORIES:\n\nID: 1\nTITLE: Micropatches Released for Microsoft Outlook &#34;MonikerLink&#34; Remote Code Execution Vulnerability (CVE-2024-21413)\nDESCRIPTION:  In February 2024, still-Supported Microsoft Outlook versions got an official patch for CVE-2024-21413,\n a vulnerability that allowed an attacker to execute arbitrary code on user&#39;s computer when the user opened a malicious hyperlink in attacker&#39;s email.\nCREATED: 2024-03-15T08:06:00\nREAD: False\nIMPORTANT: False\nLIKES: 0\nDISLIKES:0\nRELEVANCE: 0\n## NEWS_ITEMS:\n\nID: 1\nNEWS_ITEM_ID: 737f9b70-c20a-406b-8bf0-d15660d2d63a\nSTORY_ID: 1\n## NEWS_ITEM:\n\nID: 737f9b70-c20a-406b-8bf0-d15660d2d63a\nHASH: 6fb09d56c3c969dced1b261f92af1f810f8d5bdc397a4f7e2c862d46fa86366b\nTITLE: Micropatches Released for Microsoft Outlook &#34;MonikerLink&#34; Remote Code Execution Vulnerability (CVE-2024-21413)\nREVIEW:  In February 2024, still-Supported Microsoft Outlook versions got an official patch for CVE-2024-21413,\n a vulnerability that allowed an attacker to execute arbitrary code on user&#39;s computer when the user opened a malicious hyperlink in attacker&#39;s email.\nAUTHOR: Mitja Kolsek (noreply@blogger.com)\nSOURCE: https://blog.0patch.com/feeds/posts/default\nLINK: https://blog.0patch.com/2024/03/micropatches-released-for-microsoft.html\nLANGUAGE: None\nCONTENT: In February 2024, still-Supported Microsoft Outlook versions got an official patch for CVE-2024-21413, a vulnerability that allowed an attacker to execute arbitrary code on user&#39;s computer when the user opened a malicious hyperlink in attacker&#39;s email.\nThe vulnerability was discovered by Haifei Li of Check Point Research, who also wrote a detailed analysis. Haifei reported it as a bypass for an existing security mechanism, whereby Outlook refuses to open a file from a shared folder on the Internet (which could expose user&#39;s NTLM credentials in the process).\nCOLLECTED: 2024-03-25T14:02:46.016409\nPUBLISHED: 2024-03-15T08:06:00\nUPDATED: 2024-03-25T12:19:38.365866\nOSINT_SOURCE_ID: a9ceb02d-f148-4c56-b890-5a72b52f01cd\n## ATTRIBUTES:\n\n## TAGS:\n"  # noqa
product_render_mime = "text/plain"
product_render_data_pdf = b"IyBWVUxORVJBQklMSVRZIFJFUE9SVFxuSUQ6IDFcblVVSUQ6MzNhMjNhMzctZWM0Yy00MmU5LWI0M2EtMWE2NWQzMmU4M2U3XG5USVRMRTogaGlcbkNSRUFURUQ6IDIwMjQtMDMtMjVUMTQ6MDI6NTkuNjA3NjgyXG5MQVNUX1VQREFURUQ6IDIwMjQtMDMtMjVUMTQ6MDI6NTkuNjA3Njg3XG5DT01QTEVURUQ6IEZhbHNlXG5VU0VSX0lEOiAxXG5SRVBPUlRfSVRFTV9UWVBFX0lEOiAzXG4jIyBBVFRSSUJVVEVTOlxuXG4jIyBORVdTX0lURU1fQUdHUkVHQVRFUzpcblxuSUQ6IDFcblRJVExFOiBNaWNyb3BhdGNoZXMgUmVsZWFzZWQgZm9yIE1pY3Jvc29mdCBPdXRsb29rICYjMzQ7TW9uaWtlckxpbmsmIzM0OyBSZW1vdGUgQ29kZSBFeGVjdXRpb24gVnVsbmVyYWJpbGl0eSAoQ1ZFLTIwMjQtMjE0MTMpXG5ERVNDUklQVElPTjogIEluIEZlYnJ1YXJ5IDIwMjQsIHN0aWxsLVN1cHBvcnRlZCBNaWNyb3NvZnQgT3V0bG9vayB2ZXJzaW9ucyBnb3QgYW4gb2ZmaWNpYWwgcGF0Y2ggZm9yIENWRS0yMDI0LTIxNDEzLFxuIGEgdnVsbmVyYWJpbGl0eSB0aGF0IGFsbG93ZWQgYW4gYXR0YWNrZXIgdG8gZXhlY3V0ZSBhcmJpdHJhcnkgY29kZSBvbiB1c2VyJiMzOTtzIGNvbXB1dGVyIHdoZW4gdGhlIHVzZXIgb3BlbmVkIGEgbWFsaWNpb3VzIGh5cGVybGluayBpbg=="  # noqa
product_render_mime_pdf = "application/pdf"
