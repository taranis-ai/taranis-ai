#!/bin/bash

corepack enable
yes | pnpm update --save --include=dev
pnpm run dev
