# Taranis NG

Taranis NG is an OSINT gathering and analysis tool for CSIRT teams and
organisations. It allows osint gathering, analysis and reporting; team-to-team
collaboration; and contains a user portal for simple self asset management.

Taranis crawls various **data sources** such as web sites or tweets to gather
unstructured **news items**. These are processed by analysts to create
structured **report items**, which are used to create **products** such as PDF
files, which are finally **published**.

Taranis supports **team-to-team collaboration**, and includes a light weight
**self service asset management** which automatically links to the advisories
that mention vulnerabilities in the software.

## Documentation

See [doc/2023_IKTSichKonf_AWAKE_v2.pdf](ADVANCED OSINT ANALYSIS FOR NIS AUTHORITIES, CSIRT TEAMS AND ORGANISATIONS) for a presentation about the current features.

See [wiki](https://github.com/ait-cs-IaaS/Taranis-NG/wiki) for documentation of user stories and deployment guides.


## Services
| Type      | Name      | Description                           |
| :-------- | :-------- | :------------------------------------ |
| Backend   | core      | Backend for communication with the Databese and offering REST Endpoints to workers and frontend |
| Frontend  | gui       | Vuejs3 based Frontend |
| Woker     | worker    | Celery Worker offering collectors, bots, presenters and publisher features |
| Worker    | beat      | Celery Beat instance for scheduling tasks |


## Support services
| Type            | Name                 | Description                           |
| :-------------- | :------------------- | :------------------------------------ |
| Database        | database             | Supported are PostgreSQL and SQLite with PostgreSQL as our primary citizen |
| Message-broker  | rabbitmq             | Message Broker for distribution of Workers and Publish Subscribe Queue Management |


This is just a taste of its features:

- crawl the raw data using various collectors, perhaps located in different environments.
- process even those javascript-generated web pages with advanced data extraction techniques
- create different analyses with completely customizable report item types
- generate many different products with help of product templates
- easily publish to different channels
- time is money: collaborate with other teams by sharing interesting data. Each partnership can be configured and customized.
- split the work responsibilities any way you like, or have multiple teams process partially overlapping data using advanced role and permission system
- use wordlists for filtering and highlighting
- publish the self-service asset management portal to your constituency and allow them to set various notification profiles for those times when a vulnerability hits their product.

### Hardware requirements
To use all NLP features make sure to have at least: 16 GB RAM, 4 CPU cores and 50GB of disk storage.


Without NLP: 2 GB of RAM, 2 CPU cores and 20 GB of disk storage


Taranis NG was developed by [SK-CERT](https://www.sk-cert.sk/) with a help from
wide CSIRT community, and is released under terms of the [European Union Public
Licence](https://eupl.eu/1.2/en/).

## Directory structure

- src/ - Taranis NG source code:
  - [Core](src/core/) is the REST API, the central component of Taranis NG
  - [GUI](src/gui/) is the web user interface
  - [Worker](src/worker/) retrieve OSINT information from various sources (such as web, twitter, email, atom, rss, slack, and more) and create **news items**.
- [docker/](docker/) - Support files for Docker image creation and example docker-compose file

## About...

This project was inspired by [Taranis3](https://github.com/NCSC-NL/taranis3),
a great tool made by NCSC-NL. It aims to become a next generation of this
category of tools. The project was made in collaboration with a wide
group of European CSIRT teams who are developers and users of Taranis3,
and would not be possible without their valuable input especially
during the requirements collection phase. The architecture and design
of new Taranis NG is a collective brain child of this community.

This project has been co-funded by European Regional Development Fund as part of [Operational Programme Integrated Infrastructure (OPII)](https://www.opii.gov.sk/opii-en/titulka-en).

Further development has been co-funded by “Connecting Europe Facility – Cybersecurity Digital Service Infrastructure Maintenance and Evolution of Core Service Platform Cooperation Mechanism for CSIRTs – MeliCERTes Facility” (SMART 2018/1024).

Further development is being co-funded by European Commission through the Connecting Europe Facility action entitled "Joint Threat Analysis Network", action number 2020-EU-IA-0260.
