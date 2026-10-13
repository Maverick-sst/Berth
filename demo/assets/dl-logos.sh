#!/usr/bin/env bash
# Fetch official tech logos for the deck (Simple Icons = real brand glyphs).
set -e
cd "$(dirname "$0")"
for name in fastapi postgresql react sqlalchemy docker githubactions prometheus grafana kubernetes helm terraform trivy python nginx; do
  curl -sf -o "$name.svg" "https://cdn.simpleicons.org/$name/18181b" || echo "MISS $name"
done
ls -la *.svg | head -20
