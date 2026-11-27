#!/usr/bin/env bash
# Follow one scenario run through the services' logs (GCP-02 Phase B, item 3).
#   landscape/trace_check.sh scenario-ab12cd [PROJECT_ID] [FRESHNESS, default 2h]
# The scenario sends one X-Correlation-Id on every call and prints it at the end. Each Python service logs one JSON
# line per request with it; settlement-service passes it into its own logs. This counts the log entries per service.
set -euo pipefail
ID="${1:?usage: trace_check.sh CORRELATION_ID [PROJECT_ID] [FRESHNESS]}"
PROJECT="${2:-$(gcloud config get-value project 2>/dev/null)}"
FRESH="${3:-2h}"
missing=0
for service in o2c-agent-service-dev settlement-service audit-ai-service reconciliation-service genai-assistant-service; do
  n=$(gcloud logging read "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"$service\" AND (jsonPayload.correlation_id=\"$ID\" OR textPayload:\"$ID\" OR jsonPayload.message:\"$ID\")" \
        --project "$PROJECT" --freshness "$FRESH" --limit 200 --format='value(timestamp)' 2>/dev/null | wc -l)
  printf '%-28s %s entries\n' "$service" "$n"
  [ "$n" -gt 0 ] || missing=$((missing + 1))
done
if [ "$missing" -eq 0 ]; then echo "OK: $ID appears in all five services"; else echo "MISSING in $missing service(s)"; exit 1; fi
