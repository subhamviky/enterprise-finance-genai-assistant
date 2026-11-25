"""Run chosen golden cases against the configured model and print what the assistant answered (GCP-01, live evidence).

    python ../landscape/live_cases.py ID [ID ...]        (from genai-assistant-service, with the gate's environment)

For each case: the status, intent, whether the answer is degraded, the model errors (a 429 or a 503 shows here), the
records read, and the answer's first 300 characters. It waits between cases so a free-tier limit of 15 requests a
minute is not hit by the script itself (LIVE_CASE_PAUSE seconds, default 15)."""
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "genai-assistant-service"
sys.path.insert(0, str(ROOT / "src"))

from genai_assistant_service.release.gate import ReleaseGate        # noqa: E402


def main(ids) -> int:
    cases = json.loads((ROOT / "evals" / "golden.json").read_text(encoding="utf-8"))
    cases = cases.get("cases", cases) if isinstance(cases, dict) else cases
    wanted = [c for c in cases if c.get("id") in ids]
    missing = sorted(set(ids) - {c["id"] for c in wanted})
    if missing:
        print("unknown case ids:", ", ".join(missing))
        return 2
    gate = ReleaseGate.__new__(ReleaseGate)                          # only _run_case is needed
    pause = float(os.getenv("LIVE_CASE_PAUSE", "15"))
    for i, case in enumerate(wanted):
        state = gate._run_case(case)
        answer = json.loads(state["response"])
        print(f"--- {case['id']}  | {case['input']['query']}")
        print(f"    status={answer.get('status')} intent={answer.get('intent')} degraded={answer.get('degraded')} "
              f"evaluation={state.get('evaluation')} refusal={bool(state.get('refusal'))}")
        errors = [str(e)[:160] for e in state.get("model_errors") or []]
        if errors:
            print("    model errors:", errors)
        if state.get("grounding_failure") or state.get("proposal_refused"):
            print("    why:", state.get("grounding_failure") or state.get("proposal_refused"))
        print("    read:", answer.get("records_read"))
        print("    answer:", str(answer.get("answer"))[:300].replace("\n", " "))
        if i < len(wanted) - 1:
            time.sleep(pause)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
