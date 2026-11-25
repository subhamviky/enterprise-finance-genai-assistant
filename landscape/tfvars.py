"""Turns the landscape's placeholder files into one stack's Terraform inputs (hub design note GCP-01, §5, §9).

    python landscape/tfvars.py STACK [--landscape deploy/gcp/landscape.vars] [--binding PATH ...] [--out FILE]

STACK is one of: foundation, assistant, settlement, audit, reconciliation, o2c. The values come from
landscape.vars (shared) and then the stack's own binding.vars (which win); the result is a
terraform.tfvars.json that `terraform apply` picks up. A key a stack does not use is ignored, and an empty
value is left out, so the stack's own default applies. Nothing secret is in these files.

    set -e
    python landscape/tfvars.py settlement --binding ../financial-settlement-platform/deploy/gcp/binding.vars \
        --out ../financial-settlement-platform/settlement-service/infra/gcp/terraform.tfvars.json
"""
import argparse
import json
import sys
from pathlib import Path

# the variable each key feeds, per stack: {KEY: (terraform variable, kind)}; kind: str | int | list | map
SHARED = {"GCP_PROJECT_ID": ("project_id", "str"), "GCP_REGION": ("region", "str")}
LLM = {"E2A_PROVIDER_PROFILE": ("llm_profile", "str"), "LLM_MODEL_ID": ("llm_model_id", "str"),
       "GEMINI_API_KEY_SECRET": ("gemini_api_key_secret", "str")}
STACKS = {
    "foundation": {**SHARED, "GITHUB_OWNER": ("github_owner", "str"), "BILLING_ACCOUNT": ("billing_account", "str"),
                   "BUDGET_AMOUNT": ("budget_amount", "int"), "BUDGET_CURRENCY": ("budget_currency", "str")},
    "assistant": {**SHARED, **LLM, "GENAI_IMAGE": ("image", "str"), "FIRESTORE_DATABASE": ("firestore_database", "str"),
                  "RECONCILIATION_API_URL": ("reconciliation_api_url", "str"), "SETTLEMENT_API_URL": ("settlement_api_url", "str"),
                  "O2C_API_URL": ("o2c_api_url", "str"), "AUDIT_API_URL": ("audit_api_url", "str"),
                  "INVOKER_MEMBERS": ("invoker_members", "list"), "IDENTITY_SUBJECT_ROLES": ("identity_subject_roles", "map")},
    "settlement": {**SHARED, "SETTLEMENT_IMAGE": ("image", "str"), "POSTGRES_IMAGE": ("postgres_image", "str"),
                   "INVOKER_MEMBERS": ("invoker_members", "list"),
                   "SETTLEMENT_IDENTITY_SUBJECT_ROLES": ("identity_subject_roles", "map")},
    "audit": {**SHARED, **LLM, "AUDIT_IMAGE": ("image", "str"), "FIRESTORE_DATABASE": ("firestore_database", "str"),
              "SETTLEMENT_API_URL": ("settlement_api_url", "str"), "INVOKER_MEMBERS": ("invoker_members", "list"),
              "AUDIT_IDENTITY_SUBJECT_ROLES": ("identity_subject_roles", "map")},
    "reconciliation": {**SHARED, **LLM, "RECON_IMAGE": ("image", "str"), "FIRESTORE_DATABASE": ("firestore_database", "str"),
                       "SETTLEMENT_API_URL": ("settlement_api_url", "str"), "INVOKER_MEMBERS": ("invoker_members", "list"),
                       "IDENTITY_SUBJECT_ROLES": ("identity_subject_roles", "map")},
    "o2c": {**SHARED, **LLM, "O2C_IMAGE": ("image", "str"), "IMAGE_REPOSITORY": ("image_repository", "str"),
            "FIRESTORE_DATABASE": ("firestore_database", "str"), "COMBINED_SCHEDULE": ("combined_schedule", "str"),
            "MAX_INSTANCE_COUNT": ("max_instance_count", "int"), "SETTLEMENT_API_URL": ("settlement_api_url", "str"),
            "RECONCILIATION_API_URL": ("reconciliation_api_url", "str"), "IDENTITY_SOURCE": ("identity_source", "str"),
            "WORKLOAD_IDENTITY": ("workload_identity", "str"), "INVOKER_MEMBERS": ("invoker_members", "list"),
            "IDENTITY_SUBJECT_ROLES": ("identity_subject_roles", "map")},
}


def read_vars(path: Path) -> dict:
    """KEY=value lines; comments and blank lines are skipped; the value is everything after the first '='."""
    values = {}
    for number, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        text = line.strip()
        if not text or text.startswith("#"):
            continue
        if "=" not in text:
            raise ValueError(f"{path}:{number}: not KEY=value: {line!r}")
        key, value = text.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def convert(stack: str, sources: list) -> dict:
    if stack not in STACKS:
        raise ValueError(f"unknown stack {stack!r}: one of {', '.join(sorted(STACKS))}")
    merged = {}
    for source in sources:                                  # later sources win
        merged.update(read_vars(source))
    out = {}
    for key, (variable, kind) in STACKS[stack].items():
        raw = merged.get(key, "")
        if raw == "":
            continue
        if kind == "int":
            out[variable] = int(raw)
        elif kind == "list":
            out[variable] = [v.strip() for v in raw.split(",") if v.strip()]
        elif kind == "map":
            out[variable] = json.loads(raw)
        else:
            out[variable] = raw
    return out


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("stack", choices=sorted(STACKS))
    parser.add_argument("--landscape", default="deploy/gcp/landscape.vars")
    parser.add_argument("--binding", action="append", default=[], help="the stack's own binding.vars (repeatable)")
    parser.add_argument("--out", help="the file to write (default: standard output)")
    args = parser.parse_args(argv)
    result = convert(args.stack, [args.landscape, *args.binding])
    text = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)
    if any("PLACEHOLDER" in json.dumps(v) for v in result.values()):
        print("warning: placeholder values remain; fill them in before applying", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
