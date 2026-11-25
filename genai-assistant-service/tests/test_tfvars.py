"""landscape/tfvars.py turns the placeholder files into one stack's Terraform inputs (GCP-01 §5, §9)."""
import importlib.util
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("tfvars", ROOT / "landscape" / "tfvars.py")
tfvars = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tfvars)

LANDSCAPE, BINDING = ROOT / "deploy/gcp/landscape.vars", ROOT / "deploy/gcp/binding.vars"


def test_the_assistants_inputs_come_from_both_files():
    out = tfvars.convert("assistant", [LANDSCAPE, BINDING])
    assert out["project_id"].endswith("PLACEHOLDER") and out["region"] == "us-central1"
    assert out["image"].endswith("genai-assistant-service:latest") and out["llm_profile"] == "simulated"
    assert out["invoker_members"] == ["user:investigator-PLACEHOLDER@example.com", "user:approver-PLACEHOLDER@example.com"]
    assert out["identity_subject_roles"]["approver-PLACEHOLDER@example.com"] == ["tenant:acme", "finance-approver"]
    assert "llm_model_id" not in out and "gemini_api_key_secret" in out        # empty values keep the stack's default


def test_the_binding_wins_over_the_landscape(tmp_path):
    first, second = tmp_path / "a.vars", tmp_path / "b.vars"
    first.write_text("GCP_REGION=us-east1\nMAX_INSTANCE_COUNT=3\n")
    second.write_text("GCP_REGION=us-west1\n")
    assert tfvars.convert("o2c", [first, second]) == {"region": "us-west1", "max_instance_count": 3}


def test_a_line_that_is_not_key_value_is_refused(tmp_path):
    bad = tmp_path / "bad.vars"
    bad.write_text("GCP_REGION us-east1\n")
    with pytest.raises(ValueError, match="not KEY=value"):
        tfvars.convert("foundation", [bad])


@pytest.mark.parametrize("stack,directory", [("foundation", "landscape/foundation"),
                                             ("assistant", "genai-assistant-service/infra")])
def test_every_input_it_writes_is_a_variable_of_the_stack(stack, directory):
    declared = set()
    for f in (ROOT / directory).glob("*.tf"):
        declared |= set(re.findall(r'^variable "([a-z0-9_]+)"', f.read_text(), re.M))
    assert {v for v, _ in tfvars.STACKS[stack].values()} <= declared


def test_every_key_of_the_assistants_files_is_used_or_a_reference_value():
    used = set().union(*[set(m) for m in tfvars.STACKS.values()])
    reference = {"APPROVER", "INVESTIGATOR", "AUDIT_SERVICE_ACCOUNT", "GENAI_SERVICE_ACCOUNT", "O2C_SERVICE_ACCOUNT",
                 "RECON_SERVICE_ACCOUNT", "GENAI_API_URL"}
    for path in (LANDSCAPE, BINDING):
        assert set(tfvars.read_vars(path)) <= used | reference, path
