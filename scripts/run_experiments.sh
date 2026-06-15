#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

for topology in ring_12 circulant_3_12 circulant_4_12; do
  python3 -m p2p_search benchmark \
    "examples/${topology}.json" \
    examples/queries.json \
    --runs 100 \
    --seed 2026 \
    --csv "docs/results/${topology}.csv" \
    --chart "docs/results/${topology}.svg"
done

python3 -m p2p_search graph \
  examples/circulant_3_12.json \
  --output docs/results/topology.dot

