"""The fact scorers of landscape/live_trials.py (GCP-02 A.2): they pass on the simulated model and they fail when a fact is wrong."""
import importlib.util
from pathlib import Path

SPEC = importlib.util.spec_from_file_location("live_trials", Path(__file__).resolve().parents[2] / "landscape" / "live_trials.py")
trials = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(trials)


def test_every_fact_case_passes_on_the_simulated_model():
    for name, case in trials.CASES.items():
        landscape, assistant = trials.fresh()
        ok, fails, _ = case(landscape, assistant)
        assert ok, (name, fails)


def test_the_scorers_notice_a_wrong_fact():
    landscape, assistant = trials.fresh()
    landscape._resolve = lambda *a, **k: __import__("httpx").Response(503, json={})       # reconciliation down
    ok, fails, kind = trials.approve_posts_once_and_closes(landscape, assistant)
    assert not ok and "the exception was not closed" in fails and kind == "wrong-fact"
