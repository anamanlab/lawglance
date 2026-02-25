#!/usr/bin/env bash
set -euo pipefail

if [ -z "${IMMCAD_API_BASE_URL:-}" ]; then
  echo "ERROR: IMMCAD_API_BASE_URL is required."
  exit 1
fi

if [ -z "${IMMCAD_API_BEARER_TOKEN:-}" ]; then
  echo "ERROR: IMMCAD_API_BEARER_TOKEN is required."
  exit 1
fi

REQUESTS="${REQUESTS:-20}"
CONCURRENCY="${CONCURRENCY:-5}"
MAX_P95_SECONDS="${MAX_P95_SECONDS:-2.5}"
CHAT_PATH="${CHAT_PATH:-/api/chat}"

if ! [[ "$REQUESTS" =~ ^[0-9]+$ ]] || [ "$REQUESTS" -le 0 ]; then
  echo "ERROR: REQUESTS must be a positive integer."
  exit 1
fi

if ! [[ "$CONCURRENCY" =~ ^[0-9]+$ ]] || [ "$CONCURRENCY" -le 0 ]; then
  echo "ERROR: CONCURRENCY must be a positive integer."
  exit 1
fi

tmp_results="$(mktemp)"
tmp_times="$(mktemp)"
trap 'rm -f "$tmp_results" "$tmp_times"' EXIT

run_one() {
  local idx="$1"
  local payload
  payload=$(printf '{"session_id":"perf-smoke-%s","message":"performance canary probe"}' "$idx")
  curl --silent --show-error --output /dev/null \
    --write-out '%{http_code} %{time_total}\n' \
    --request POST "${IMMCAD_API_BASE_URL}${CHAT_PATH}" \
    --header "content-type: application/json" \
    --header "authorization: Bearer ${IMMCAD_API_BEARER_TOKEN}" \
    --data "$payload" >>"$tmp_results"
}

export -f run_one
export IMMCAD_API_BASE_URL IMMCAD_API_BEARER_TOKEN CHAT_PATH tmp_results

seq 1 "$REQUESTS" | xargs -I{} -P "$CONCURRENCY" bash -lc 'run_one "$@"' _ {}

total="$(wc -l < "$tmp_results" | tr -d ' ')"
success_count="$(awk '$1 ~ /^2/ {count++} END {print count+0}' "$tmp_results")"
failure_count=$((total - success_count))

awk '{print $2}' "$tmp_results" | sort -n >"$tmp_times"

if [ "$total" -eq 0 ]; then
  echo "ERROR: No results captured."
  exit 1
fi

p50_idx=$(( (total + 1) / 2 ))
p95_idx=$(( (total * 95 + 99) / 100 ))

p50="$(sed -n "${p50_idx}p" "$tmp_times")"
p95="$(sed -n "${p95_idx}p" "$tmp_times")"
avg="$(awk '{sum += $2} END {printf "%.6f", sum/NR}' "$tmp_results")"

echo "Cloudflare backend perf smoke summary"
echo "  base_url: ${IMMCAD_API_BASE_URL}"
echo "  path: ${CHAT_PATH}"
echo "  requests: ${REQUESTS}"
echo "  concurrency: ${CONCURRENCY}"
echo "  successes: ${success_count}"
echo "  failures: ${failure_count}"
echo "  avg_seconds: ${avg}"
echo "  p50_seconds: ${p50}"
echo "  p95_seconds: ${p95}"
echo "  max_p95_seconds_threshold: ${MAX_P95_SECONDS}"

if [ "$failure_count" -gt 0 ]; then
  echo "ERROR: One or more perf smoke requests failed."
  exit 1
fi

if ! awk -v p95="$p95" -v max="$MAX_P95_SECONDS" 'BEGIN {exit !(p95 <= max)}'; then
  echo "ERROR: p95 latency exceeds threshold."
  exit 1
fi

echo "[OK] Performance smoke check passed."
