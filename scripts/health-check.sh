#!/usr/bin/env bash
# Cloud District Club — Backend Health Check
# Usage: bash scripts/health-check.sh

ENDPOINT="https://vape-shop-staging.emergent.host/health"

if curl -fsS "$ENDPOINT" > /dev/null 2>&1; then
  echo "Cloud District backend healthy"
  exit 0
else
  echo "Cloud District backend DOWN"
  exit 1
fi
