from worker.collectors.reddit_collector import RedditCollector
from worker.config import Config


def test_collect_reddit_listing_replies_and_removals(requests_mock):
    source = {"id": "rail", "parameters": {"CLIENT_ID": "test", "CLIENT_SECRET": "secret", "USER_AGENT": "test", "SUBREDDIT": "rail"}}
    endpoint = f"{Config.TARANIS_CORE_URL}/worker/social/rail"
    requests_mock.post("https://www.reddit.com/api/v1/access_token", json={"access_token": "token"})
    requests_mock.get(endpoint, json={"keys": ["t1_gone"]})
    requests_mock.get("https://oauth.reddit.com/api/info", json={"data": {"children": []}})
    submission = {"name": "t3_root", "title": "Station", "permalink": "/r/rail/test", "created_utc": 1000, "url": "https://i.redd.it/a.png"}
    comment = {
        "name": "t1_reply",
        "link_id": "t3_root",
        "parent_id": "t3_root",
        "permalink": "/r/rail/test/reply",
        "created_utc": 1010,
        "author": "[deleted]",
        "body": "Open",
    }
    requests_mock.get("https://oauth.reddit.com/r/rail/new", json={"data": {"children": [{"data": submission}]}})
    requests_mock.get("https://oauth.reddit.com/r/rail/comments", json={"data": {"children": [{"data": comment}]}})
    image = requests_mock.get("https://i.redd.it/a.png", content=b"image")
    stored = requests_mock.post(endpoint, json={"id": "post"})
    RedditCollector().collect(source)
    deleted, root, reply = [r.json() for r in stored.request_history]
    assert deleted == {"removed": "t1_gone"}
    assert root["images"] == [{"key": "t3_root", "alt": "", "data": "aW1hZ2U="}]
    assert reply["thread"] == root["key"] == reply["parent"] and reply["author"] == ""
    assert "Authorization" not in image.last_request.headers
