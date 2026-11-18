#!/usr/bin/env bash
# Run from any directory: bash /path/to/project/util.sh test
set -euo pipefail
cd "$(dirname "$0")"
case "${1:-test}" in
  test)
    mkdir -p output
    docker build -t nlp-course-assistant .
    docker run --rm -v "$PWD/input:/nlp/input" -v "$PWD/output:/nlp/output" nlp-course-assistant
    ;;
  *) echo 'Dùng: bash util.sh test' >&2; exit 2 ;;
esac
