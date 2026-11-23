---
title: Requirements
description: System requirements for setting up Taranis AI
weight: 6
---

For the best experience using **Taranis AI**, we recommend that your system meet the following requirements:

## System Requirements


| Resource | Minimal (w/o bots) | Recommended |
|-----------|----------|--------------|
| **CPU** | 2 cores | 12 cores |
| **RAM** | 2 GB | 16 GB |
| **Storage** | 16 GB | 40 GB |

> **Note:** The recommended requirements assume that all bots are active concurrently. You can estimate the requirements for running only some of the bots from this table:

| Bot | CPUs | RAM  | Storage |
|-----|------|------|---------|
| cybersec-classifier | 2 | 2.0 GB | 8.3 GB
| NER | 2 | 7.0 GB | 8.38 GB
| story-clustering | 2 | 1.5 GB | 6.8 GB
| summary | 2 | 1.5 GB | 8.4 GB
| sentiment-analysis | 2 | 2.5 GB | 8.12 GB


You can assume the number of CPUs and RAM to be cumulative, so for running two bots concurrently, sum up the required number of CPUs and RAM.
Reserve an additional 2 CPUs and 2 GB RAM for normal system operation.

Example: For running story-clustering and NER bots at the same time, your system should have 6 CPUs and 10.5 GB of RAM.



### GPU Acceleration *(Coming Soon)*

GPU support for accelerating bot performance will be available soon.
Further details and configuration options will be provided once this feature is launched.

## Recommended Setup

- **Display:** Full HD (1920×1080) or higher
- **Supported Browsers:**
  - Chromium
  - Mozilla Firefox
  - Microsoft Edge
