#!/usr/bin/env bash
# Moves the six stacks' Terraform state from the working directories (Cloud Shell's disk) into the state bucket
# the foundation created, so a reset of Cloud Shell cannot lose it (hub design note GCP-01, step 10).
# Run in the folder that holds the four cloned repositories (cd ~):
#   PROJECT=your-project-id bash enterprise-finance-genai-assistant/landscape/move-state.sh
# Safe to run again. It writes a backend_override.tf (git-ignored) in each stack, then `terraform init -migrate-state`.
set -euo pipefail
: "${PROJECT:?set PROJECT first: PROJECT=your-project-id}"
BUCKET="${BUCKET:-$PROJECT-tfstate}"
gcloud storage buckets describe "gs://$BUCKET" >/dev/null || { echo "STOP: no bucket gs://$BUCKET"; exit 1; }

move() {   # move DIRECTORY PREFIX
  local dir="$1" prefix="$2"
  [ -d "$dir" ] || { echo "skip $prefix: no $dir"; return; }
  [ -f "$dir/terraform.tfstate" ] || [ -f "$dir/backend_override.tf" ] || { echo "skip $prefix: no local state in $dir"; return; }
  cat > "$dir/backend_override.tf" <<EOF
terraform {
  backend "gcs" {
    bucket = "$BUCKET"
    prefix = "$prefix"
  }
}
EOF
  local exclude; exclude="$(git -C "$dir" rev-parse --git-path info/exclude 2>/dev/null || true)"
  if [ -n "$exclude" ]; then               # keep the override out of commits in every repository
    case "$exclude" in /*) ;; *) exclude="$dir/$exclude" ;; esac
    grep -qx 'backend_override.tf' "$exclude" 2>/dev/null || echo 'backend_override.tf' >> "$exclude"
  fi
  (cd "$dir" && terraform init -migrate-state -force-copy -input=false >/dev/null && echo "moved $prefix -> gs://$BUCKET/$prefix")
}

move enterprise-finance-genai-assistant/landscape/foundation              foundation
move financial-settlement-platform/settlement-service/infra/gcp           settlement
move payment-reconciliation-engine/reconciliation-service/infra/gcp       reconciliation
move financial-settlement-platform/audit-ai-service/infra/gcp             audit
move order-to-cash-agentic-ai/o2c-agent-service/infra                     o2c
move enterprise-finance-genai-assistant/genai-assistant-service/infra     assistant

echo
echo "Check: gcloud storage ls -r gs://$BUCKET/ | grep tfstate"
echo "Each stack now keeps its state in the bucket; the local terraform.tfstate files are left in place as a copy."
