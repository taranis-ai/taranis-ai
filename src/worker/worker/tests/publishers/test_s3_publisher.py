from worker.publishers.s3_publisher import S3Publisher
from worker.tests.publishers.publishers_data import product_text


class FakeMinio:
    def __init__(self, existing_buckets=None):
        self.existing_buckets = set(existing_buckets or [])
        self.bucket_exists_calls = []
        self.make_bucket_calls = []
        self.put_calls = []

    def bucket_exists(self, bucket_name):
        self.bucket_exists_calls.append(bucket_name)
        return bucket_name in self.existing_buckets

    def make_bucket(self, bucket_name):
        self.make_bucket_calls.append(bucket_name)
        self.existing_buckets.add(bucket_name)

    def put_object(self, bucket_name, data, object_name, length, content_type):
        self.put_calls.append(
            {
                "bucket_name": bucket_name,
                "object_name": object_name,
                "content_type": content_type,
                "data": data.read(),
                "length": length,
            }
        )


def test_s3_publisher_publish_creates_bucket_and_uploads(s3_publisher_testdata, get_product_mock):
    client = FakeMinio()
    publisher = S3Publisher(client=client)

    result = publisher.publish(s3_publisher_testdata, product_text, get_product_mock)
    assert result["status"] == "success"

    bucket_name = s3_publisher_testdata["parameters"]["S3_BUCKET_NAME"]

    assert client.bucket_exists_calls == [bucket_name]
    assert client.make_bucket_calls == [bucket_name]

    assert len(client.put_calls) == 1
    upload = client.put_calls[0]
    assert upload["bucket_name"] == bucket_name
    assert upload["object_name"] == result["object_name"]
    assert upload["object_name"].startswith(product_text["title"])
    assert upload["content_type"] == get_product_mock.mime_type
    assert upload["data"] == get_product_mock.data
    assert upload["length"] == len(get_product_mock.data)
