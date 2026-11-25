#!/usr/bin/env bash
set -euo pipefail

cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
export SHOP_HEADED="${SHOP_HEADED:-1}"
export SHOP_SLOW_MO_MS="${SHOP_SLOW_MO_MS:-500}"

uv sync --locked
uv run --locked playwright install "${SHOP_BROWSER:-chromium}"

mkdir -p artifacts
results=$(mktemp -d "$PWD/artifacts/allure-run.XXXXXX")
status=0
uv run --locked pytest autotest --alluredir="$results" "$@" || status=$?

if compgen -G "$results/*-result.json" > /dev/null; then
    report="$PWD/artifacts/allure-report"
    npx --yes allure-commandline@2.36.0 generate "$results" --single-file --clean -o "$report"
    printf '\nAllure: %s/index.html\n' "$report"
else
    printf '\npytest не записал результаты. Проверьте вывод выше.\n' >&2
    exit "$((status == 0 ? 1 : status))"
fi

exit "$status"
