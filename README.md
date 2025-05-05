# Taranis AI

![Logo](./resources/images/logo.svg)

Taranis AI is an advanced Open-Source Intelligence (OSINT) tool, leveraging Artificial Intelligence to revolutionize information gathering and situational analysis.

Taranis navigates through diverse data sources like websites to collect unstructured news articles, utilizing Natural Language Processing and Artificial Intelligence to enhance content quality.
Analysts then refine these AI-augmented articles into structured reports that serve as the foundation for deliverables such as PDF files, which are ultimately published.

![Screenshot](./resources/images/screenshot.png)

## Getting Started

For production deployments see our [Deployment Guide using docker compose](https://taranis.ai/docs/getting-started/deployment/)

## Contributions

We welcome contributions from the community! If you're interested in contributing to Taranis AI, please read our [Development Setup Guide](./dev/README.md) to get started.

## Documentation

See [ADVANCED OSINT ANALYSIS FOR NIS AUTHORITIES, CSIRT TEAMS AND ORGANISATIONS](./doc/2023_IKTSichKonf_AWAKE_v3.pdf) for a presentation about the current features.

See [taranis.ai](https://taranis.ai/docs/) for documentation of user stories and deployment guides.

## Services

| Type       | Name      | Description                           |
| :--------- | :-------- | :------------------------------------ |
| Entrypoint | gui       | Nginx serving static assets and Vuejs3 based Frontend |
| Frontend   | frontend  | Flask, HTMX & tailwindcss based REST frontend |
| Backend    | core      | Backend for communication with the Database and offering REST Endpoints to workers and frontend |
| Worker     | worker    | Celery Worker offering collectors, bots, presenters and publisher features |

### Support services

| Type            | Name                 | Description                           |
| :-------------- | :------------------- | :------------------------------------ |
| Database        | database             | Supported are PostgreSQL and SQLite with PostgreSQL as our primary citizen |
| Message-broker  | rabbitmq             | Message Broker for distribution of Workers and Publish Subscribe Queue Management |
| SSE             | sse                  | [SSE Broker](https://github.com/taranis-ai/sse-broker) |

## Features

* Advanced OSINT Capabilities: Taranis AI scours multiple data sources, such as websites, for unstructured news articles, providing a comprehensive intelligence feed.
* AI-Enhanced Analysis: Utilizes Artificial Intelligence and Natural Language Processing to automatically enhance and enrich collected articles for higher content quality.
* Analyst-Friendly Workflow: Offers a streamlined process where analysts can easily convert unstructured news into structured report items, optimizing the data transformation journey.
* Multi-Format Output: Generates a variety of end products, including structured reports and PDF files, tailored to specific informational needs.
* Seamless Publishing: Facilitates the effortless publication of finalized intelligence products, ensuring timely dissemination of critical information.
* Collaborative Threat Intelligence (Experimental): Supports Story-level sharing between Taranis AI instances via [MISP](https://www.misp-project.org/), or directly between Taranis AI and MISP for flexible collaboration and information dissemination.

### OpenAPI

<img src="https://validator.swagger.io/validator?url=https://raw.githubusercontent.com/taranis-ai/taranis-ai/master/src/core/core/static/openapi3_1.yaml">

An [OpenAPI spec](./src/core/core/static/openapi3_1.yaml) for the REST API is included and can be accessed in a running installation under `config/openapi`.

### Hardware requirements

To use all NLP features make sure to have at least: 16 GB RAM, 4 CPU cores and 50GB of disk storage.

Without NLP: 2 GB of RAM, 2 CPU cores and 20 GB of disk storage

### Directory structure

* src/ - Taranis AI source code:
  * [core](src/core/) is the REST API, the central component of Taranis AI
  * [gui](src/gui/) vuejs part of the web user interface
  * [frontend](src/frontend/) flask & htmx part of the web user interface
  * [models](src/models/) pydantic models for validating inputs and outputs
  * [worker](src/worker/) retrieve OSINT information from various sources (such as web, twitter, email, atom, rss, slack, and more) and create **news items**.
* [docker/](docker/) - Support files for Docker image creation and example docker-compose file

## About

This project was inspired by [Taranis3](https://github.com/NCSC-NL/taranis3), as well as by [Taranis-NG](https://github.com/SK-CERT/Taranis-NG/).
It is released under terms of the [European Union Public Licence](https://eupl.eu/1.2/en/).

## EU Funding

![Co-financed by the Connecting Europe Facility of the European Union](https://ec.europa.eu/inea/sites/default/files/ceflogos/en_horizontal_cef_logo_2.png)
