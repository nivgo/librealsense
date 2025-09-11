#!/bin/bash
# Run the rs_viewer health test N times sequentially and aggregate results.
# Usage: (from librealsense repo root)
#   N=10 bash unit-tests/live/rs-viewer/run_batch_rs_viewer_health.sh
# Env you may set:
#   N                -> number of iterations (default 10)
#   PYTHON_BIN       -> python executable (default python)
#   SERVER_HOST/PORT -> passed through (AGENT_SERVER_HOST / AGENT_SERVER_PORT)
#   EXTRA_ENV        -> extra env vars e.g. 'AGENT_SERVER_FORCE=1'

set -u -o pipefail
# do NOT set -e; we want to continue after failures

N=${N:-50}
PYTHON_BIN=${PYTHON_BIN:-python}
TEST_PATH="unit-tests/live/rs-viewer/test_rs_viewer_health.py"
OUT_DIR="unit-tests/live/rs-viewer/batch_runs_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$OUT_DIR"
CSV="$OUT_DIR/summary.csv"
JSONL="$OUT_DIR/summary.jsonl"

# Header
echo "iteration,exit_code,ok,pass,wall_elapsed_sec,final_answer,details" > "$CSV"

run_one() {
  local i=$1
  echo "[INFO] ---- Iteration $i/$N ----" >&2
  local start_ts end_ts elapsed
  start_ts=$(date +%s)
  # Run with needed PYTHONPATH
  ( PYTHONPATH="$PWD/unit-tests/py:$PWD" \
    AGENT_SERVER_HOST="${AGENT_SERVER_HOST:-127.0.0.1}" \
    AGENT_SERVER_PORT="${AGENT_SERVER_PORT:-8099}" \
    ${EXTRA_ENV:-} \
    $PYTHON_BIN "$TEST_PATH" ) &> "$OUT_DIR/run_${i}.log"
  local rc=$?
  end_ts=$(date +%s)
  elapsed=$(( end_ts - start_ts ))

  local log_file="$OUT_DIR/run_${i}.log"
  # Extract fields
  local result_line final_line details_line
  result_line=$(grep -E "Result ok=" "$log_file" | tail -1 || true)
  final_line=$(grep -E "Final answer:" "$log_file" | tail -1 || true)
  details_line=$(grep -E "Details:" "$log_file" | tail -1 || true)

  # Defaults
  local ok="" pass="" exit_code="" final_answer="" details=""

  if [[ -n "$result_line" ]]; then
    # Expect pattern: Result ok= True pass= True exit_code= 0
    read ok pass exit_code < <(echo "$result_line" | sed -E 's/.*Result ok= *([^ ]*) pass= *([^ ]*) exit_code= *([^ ]*).*/\1 \2 \3/') || true
  fi
  if [[ -n "$final_line" ]]; then
    final_answer=$(echo "$final_line" | sed -E 's/.*Final answer: *//')
  fi
  if [[ -n "$details_line" ]]; then
    details=$(echo "$details_line" | sed -E 's/.*Details: *//')
  fi

  # CSV escaping (replace commas with semicolons)
  final_answer=${final_answer//,/;} 
  details=${details//,/;}

  echo "$i,$rc,$ok,$pass,$elapsed,$final_answer,$details" >> "$CSV"

  # JSON line (basic, no quotes escaping beyond simple sed)
  printf '{"iteration":%d,"exit_code":%d,"ok":"%s","pass":"%s","wall_elapsed_sec":%d,"final_answer":"%s","details":"%s"}\n' \
    "$i" "$rc" "$ok" "$pass" "$elapsed" \
    "$(echo "$final_answer" | sed 's/"/\\"/g')" \
    "$(echo "$details" | sed 's/"/\\"/g')" >> "$JSONL"

  echo "[INFO] Iteration $i done: rc=$rc ok=$ok pass=$pass elapsed=${elapsed}s" >&2
}

for i in $(seq 1 $N); do
  run_one $i
  # Optional small pause between runs
  sleep 2
done

echo "[INFO] Batch complete. Summary CSV: $CSV" >&2
echo "[INFO] JSONL summary: $JSONL" >&2

echo "First few lines of summary:" >&2
head "$CSV" >&2
