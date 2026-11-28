"""What does one request cost? Model calls, tokens and seconds per agent step (GCP-02 Phase C, item 6).

    python ../landscape/measure.py [--runs 3] [--pause 10] [--compare] [--report FILE]
        (from genai-assistant-service; with E2A_PROVIDER_PROFILE=gemini_api, the key and the model id it measures the
         live model, without them the simulated one: calls are counted exactly, tokens and seconds mean little)

It runs the three requests of the scenario (a question, an explanation, a proposal plus its approval) against the
stand-ins and wraps the model service to count, per agent (told apart by the system prompt): calls, tokens the
provider reported (or a 4-characters-per-token estimate), and seconds. With --compare every request runs twice: with
the intent read by rules first (the default) and with it asked of the model (GENAI_INTENT_BY_RULES=false), so the
before and after come from the same run, the same model on the same day. A live run uses about
3 requests x 2 modes x runs x 3 model calls: 54 requests for --runs 3."""
import argparse
import functools
import json
import os
import statistics
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

print = functools.partial(print, flush=True)
import logging  # noqa: E402
logging.disable(logging.INFO)          # the services log every call; this tool prints a table
ROOT = Path(__file__).resolve().parents[1] / "genai-assistant-service"
sys.path.insert(0, str(ROOT / "src"))

from genai_assistant_service.services.assistant import AssistantService      # noqa: E402
from genai_assistant_service.standins.landscape import Landscape, S_FLAGGED   # noqa: E402
from genai_assistant_service.tools.catalog import tools                       # noqa: E402

ANA, BO = ("ana@acme.example", "investigator"), ("bo@acme.example", "finance-approver")
AGENTS = ("IntentAgent", "InvestigatorAgent", "ProposalAgent")


def agent_of(messages) -> str:
    system = str((messages or [{}])[0].get("content", ""))
    return next((a for a in AGENTS if system.startswith(f"You are {a}")), "other")


class Meter:
    """Wraps a model service: one record per call."""

    def __init__(self, llm):
        self.llm, self.records = llm, []
        self._inner = llm.process_inference

        async def counted(messages=None, *args, **kwargs):
            started = time.time()
            reply = await self._inner(messages, *args, **kwargs)
            tokens = ((reply or {}).get("metadata") or {}).get("tokens_used") or (reply or {}).get("tokens_used")
            if tokens is None:
                tokens = max(1, sum(len(str(m)) for m in (messages or [])) // 4)
            self.records.append({"agent": agent_of(messages), "tokens": int(tokens), "seconds": time.time() - started})
            return reply
        llm.process_inference = counted

    def take(self):
        out, self.records = self.records, []
        return out


def build():
    landscape = Landscape()
    assistant = AssistantService(tools=tools(transports=landscape.transports()))
    return landscape, assistant, Meter(assistant.llm)


REQUESTS = {
    "investigate": lambda a: a.ask("Why is bank line L-1001 unmatched?", "acme", *ANA),
    "explain": lambda a: a.ask(f"Why was settlement {S_FLAGGED} flagged?", "acme", *ANA),
    "propose+approve": lambda a: a.approve(a.ask("Propose a write-off for bank line L-1001", "acme", *ANA)["approval_id"],
                                           "acme", *BO),
}


def one(name, rules: bool) -> dict:
    os.environ["GENAI_INTENT_BY_RULES"] = "true" if rules else "false"
    landscape, assistant, meter = build()
    started = time.time()
    result = REQUESTS[name](assistant)
    wall = time.time() - started
    records = meter.take()
    return {"status": result.get("status"), "calls": len(records), "tokens": sum(r["tokens"] for r in records),
            "model_seconds": round(sum(r["seconds"] for r in records), 2), "wall_seconds": round(wall, 2),
            "by_agent": {a: sum(1 for r in records if r["agent"] == a) for a in AGENTS}}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--pause", type=float, default=float(os.getenv("LIVE_CASE_PAUSE", "10")))
    parser.add_argument("--compare", action="store_true", help="each request with and without intent-by-rules")
    parser.add_argument("--report", default="measure-report.json")
    args = parser.parse_args()
    live = os.getenv("E2A_PROVIDER_PROFILE", "simulated") != "simulated"
    modes = [("rules-first", True), ("model-asked", False)] if args.compare else [("rules-first", True)]
    report = {"started": datetime.now(timezone.utc).isoformat(timespec="seconds"), "live": live,
              "model": os.getenv("LLM_MODEL_ID", "simulated"), "runs": args.runs, "results": {}}
    for name in REQUESTS:
        for label, rules in modes:
            rows = []
            for _ in range(args.runs):
                try:
                    rows.append(one(name, rules))
                except Exception as error:                      # a 429 or a crash: report and stop, do not retry
                    report["stopped"] = f"{name}/{label}: {type(error).__name__}: {str(error)[:120]}"
                    break
                if live:
                    time.sleep(args.pause)
            if rows:
                report["results"][f"{name} [{label}]"] = {
                    "runs": len(rows), "calls": statistics.median(r["calls"] for r in rows),
                    "tokens": statistics.median(r["tokens"] for r in rows),
                    "model_seconds": statistics.median(r["model_seconds"] for r in rows),
                    "wall_seconds": statistics.median(r["wall_seconds"] for r in rows),
                    "statuses": sorted({str(r["status"]) for r in rows}), "by_agent": rows[-1]["by_agent"]}
            if report.get("stopped"):
                break
        if report.get("stopped"):
            break
    Path(args.report).write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"model: {report['model']} ({'live' if live else 'simulated: tokens and seconds are not meaningful'}), "
          f"{args.runs} run(s), medians\n")
    print("request [mode]".ljust(34) + "calls  tokens  model s  wall s  per agent")
    for key, r in report["results"].items():
        print(f"{key.ljust(34)}{str(r['calls']).ljust(7)}{str(r['tokens']).ljust(8)}{str(r['model_seconds']).ljust(9)}"
              f"{str(r['wall_seconds']).ljust(8)}{r['by_agent']}  {','.join(r['statuses'])}")
    if args.compare:
        print("\nsaved by reading the intent with rules first:")
        for name in REQUESTS:
            a, b = report["results"].get(f"{name} [model-asked]"), report["results"].get(f"{name} [rules-first]")
            if a and b and a["tokens"]:
                print(f"  {name.ljust(18)} calls {a['calls']:g} -> {b['calls']:g}, tokens {a['tokens']:g} -> {b['tokens']:g} "
                      f"({100 * (a['tokens'] - b['tokens']) / a['tokens']:.0f}% fewer), "
                      f"wall {a['wall_seconds']:g}s -> {b['wall_seconds']:g}s")
    if report.get("stopped"):
        print("STOPPED:", report["stopped"])
    print("report:", args.report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
