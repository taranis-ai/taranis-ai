---
title: Publishers
description: Publishers allow handling created products.
weight: 6
---

### Supported options

[Publishers](https://github.com/taranis-ai/taranis-ai/blob/master/src/worker/worker/publishers/) send rendered Products to external systems.

| Publisher | Required parameters | Optional parameters |
| --- | --- | --- |
| FTP Publisher | `FTP_URL` | |
| SFTP Publisher | `SFTP_URL` | `PRIVATE_KEY` |
| Email Publisher | `SMTP_SERVER_ADDRESS`, `EMAIL_SENDER`, `EMAIL_RECIPIENT`, `EMAIL_SUBJECT` | `SMTP_SERVER_PORT`, `SERVER_TLS`, `EMAIL_USERNAME`, `EMAIL_PASSWORD` |
| MISP Publisher | `MISP_URL`, `MISP_API_KEY` | |
| S3 Publisher | `S3_ENDPOINT`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`, `S3_BUCKET_NAME` | `S3_SESSION_TOKEN`, `S3_REGION`, `S3_SECURE`, `S3_CERT_CHECK` |
| TAXII Publisher | `TAXII_COLLECTION_ID`, `AUTH_TYPE` | `TAXII_API_ROOT_URL`, `TAXII_DISCOVERY_URL`, `USERNAME`, `PASSWORD`, `API_TOKEN`, `SSL_VERIFY`, `PROXY_SERVER` |
| Wordpress Publisher | `WP_USER`, `WP_PYTHON_APP_SECRET`, `WP_URL` | |
| Kafka Publisher | `KAFKA_BOOTSTRAP_SERVERS`, `KAFKA_TOPIC` | `KAFKA_SECURITY_PROTOCOL`, `KAFKA_SASL_MECHANISM`, `KAFKA_SASL_USERNAME`, `KAFKA_SASL_PASSWORD`, `KAFKA_ACKS`, `KAFKA_RETRIES`, `KAFKA_SEND_TIMEOUT` |

Keep API keys, passwords, app secrets, and private keys in protected configuration. Do not reuse personal credentials for shared publishers.

## Email Publisher

The Email Publisher allows sending out Products.

- Fields:
  - SMTP_SERVER_ADDRESS*: Address of the SMTP server.
  - SMTP_SERVER_PORT*: Port of the SMTP server.
  - SERVER_TLS: Enable/Disable TLS.
  - EMAIL_USERNAME: Login username for the SMTP server.
  - EMAIL_PASSWORD: Login password for the SMTP server.
  - EMAIL_SENDER*: Sender of the email for message envelope.
  - EMAIL_RECIPIENT*: Email address of the recipient for message envelope. It is possible to use only one email recipient.
  - EMAIL_SUBJECT: Subject of the email.

_Note: The EMAIL_SENDER and EMAIL_RECIPIENT parameters are used to construct the message envelope used by the transport agents. Message headers are not modified by these parameters in any way._

_Required fields are marked with a *._

### General usage

Once the publisher is created, it becomes available in the "Publish" section of each product.
To send out a product via email, the product must be "Rendered" first. To render a product, use the option available in the product's view.

## Kafka Publisher

The Kafka Publisher sends each rendered Product as a JSON message to the configured topic.

- Message key: the generated product file name.
- Message body: `object_name`, `mime_type`, and `data`.
- `KAFKA_SECURITY_PROTOCOL` defaults to `PLAINTEXT`.
- Supported security protocols are `PLAINTEXT` and `SASL_PLAINTEXT`.
- When `KAFKA_SECURITY_PROTOCOL` is `SASL_PLAINTEXT`, set `KAFKA_SASL_MECHANISM`, `KAFKA_SASL_USERNAME`, and `KAFKA_SASL_PASSWORD`.
- `KAFKA_ACKS` defaults to `all`.
- `KAFKA_RETRIES` defaults to `3`.
- `KAFKA_SEND_TIMEOUT` defaults to `30` seconds.

## TAXII Publisher

The TAXII Publisher pushes STIX bundle objects to a TAXII 2.1 collection. The rendered Product must be valid JSON with `type: bundle` and a non-empty `objects` list.

Set `AUTH_TYPE` to `basic` with `USERNAME` and `PASSWORD`, or to `bearer` with `API_TOKEN`. Configure either `TAXII_API_ROOT_URL` directly or `TAXII_DISCOVERY_URL` so Taranis AI can discover the API root.

## S3 Publisher

The S3 Publisher uploads the rendered Product to S3-compatible object storage. If the configured bucket does not exist, Taranis AI creates it before uploading.
