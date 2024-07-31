def test_initalize_bots():
    import worker.bots as bots

    bots.AnalystBot()
    bots.IOCBot()
    bots.GroupingBot()
    bots.NLPBot()
    bots.TaggingBot()
    bots.SummaryBot()
    bots.WordlistBot()


def test_ioc_bot(story_get_mock, tags_update_mock):
    import worker.bots as bots

    ioc_bot = bots.IOCBot()
    ioc_bot.execute()

    assert story_get_mock.call_count == 1
    assert tags_update_mock.call_count == 1

    assert tags_update_mock.last_request.json() == {
        "1": {"CVE-2020-1234": "cves"},
        "2": {"CVE-2021-5678": "cves"},
        "6": {"CVE-2023-7891": "cves"},
        "7": {"CVE-2023-1234": "cves"},
        "8": {"CVE-2023-5678": "cves"},
    }


def test_nlp_bot(story_get_mock, tags_update_mock):
    import worker.bots as bots

    nlp_bot = bots.NLPBot()
    nlp_bot.execute()

    assert story_get_mock.call_count == 1
    assert tags_update_mock.call_count == 1

    assert tags_update_mock.last_request.json() == {
        "1": {
            "CVE-2020-1234": "CVE",
            "Cisco": "Vendor",
            "Google": "Vendor",
            "Linux": "Product",
            "Microsoft": "Vendor",
            "breaches": "CySec",
            "community": "MISC",
            "protocols": "MISC",
            "security": "MISC",
            "vulnerabilities": "CySec",
        },
        "10": {
            "Cybersecurity": "MISC",
            "blog": "MISC",
            "vulnerability": "MISC",
        },
        "2": {
            "Apple": "Vendor",
            "CVE-2021-5678": "CVE",
            "Intel": "Vendor",
            "Oracle": "Vendor",
            "Windows": "Product",
            "cloud": "MISC",
            "infrastructures": "MISC",
            "security": "MISC",
            "systems": "MISC",
            "vulnerabilities": "MISC",
        },
        "3": {
            "AI": "MISC",
            "AWS": "Vendor",
            "Amazon": "Vendor",
            "IBM": "Vendor",
            "NVIDIA": "Vendor",
            "attacks": "MISC",
            "cyber": "MISC",
            "modules": "MISC",
            "security": "MISC",
            "vulnerabilities": "MISC",
        },
        "4": {
            "DevOps": "MISC",
            "Industries": "MISC",
            "Lady Penelope": "MISC",
            "Thunderbird 3": "Product",
            "cybersecurity": "CySec",
            "moon": "MISC",
            "remedy": "MISC",
            "rocket": "MISC",
            "solution": "MISC",
            "tech wizard": "MISC",
            "wizard": "MISC",
        },
        "5": {
            "Facebook": "Vendor",
            "Salesforce": "Vendor",
            "attacks": "MISC",
            "countermeasures": "MISC",
            "customer": "MISC",
            "data": "MISC",
            "encryption": "MISC",
            "phishing": "MISC",
            "technologies": "MISC",
            "user": "MISC",
        },
        "6": {
            "Adobe": "MISC",
            "CVE-2023-7891": "CVE",
            "SAP": "MISC",
            "Twitter": "MISC",
            "enterprise": "MISC",
            "infrastructure": "MISC",
            "malware": "MISC",
            "mechanisms": "MISC",
            "solutions": "MISC",
            "vulnerabilities": "MISC",
        },
        "7": {
            "CVE-2023-1234": "CVE",
            "HP": "Vendor",
            "LinkedIn": "Vendor",
            "Qualcomm": "MISC",
            "data": "MISC",
            "devices": "MISC",
            "firewall": "MISC",
            "mobile": "MISC",
            "systems": "MISC",
            "vulnerabilities": "MISC",
        },
        "8": {
            "CVE-2023-5678": "CVE",
            "Dell": "Vendor",
            "GitHub": "Vendor",
            "VMware": "Vendor",
            "phishing": "MISC",
            "platform": "MISC",
            "scams": "MISC",
            "security": "MISC",
            "stance": "MISC",
            "threats": "MISC",
        },
        "9": {
            "CVE": "MISC",
            "Software": "MISC",
            "vulnerability": "MISC",
        },
    }
