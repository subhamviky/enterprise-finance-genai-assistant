# 0006: Scorer passed trials the model never answered

- **Date of the work:** 2026-11 (the exact day was not recorded)
- **Severity:** SEV-3 (see README)
- **Status:** Actions partly open
- **Authors:** repository owner, with Claude

## Summary

The first Gemma run in the model comparison measured nothing: every model call failed with a 400 (thinking level unsupported) and the agents fell back safely. Because nothing unsafe happened, the fact-based scorer printed `pass`.

## Impact

None on users. A model comparison would have reported a pass rate for a model that never answered.

## Timeline

- Live trials on a Gemma model: 400 errors in the logs, all trials 'pass'.
- Reading the log showed 'LLM inference failed' on every call.
- Fix in the scorer: count model failures per trial; a safe trial with model errors is a `fallback`, not a pass.
- Fix in the adapter (e2a-managed-providers main): do not send a thinking level to a model that refuses it; the assistant pinned tag v0.2.0 and needed `pip install ...@main` until a new tag exists.

## Root cause

1. A scorer that checks only outcomes cannot distinguish 'the model was right' from 'the model was not asked'.
2. I over-read a green result.

## Detection

Found by running the scenario, a drill or a test; see the timeline for what made it diagnosable.

## What went well

The model comparison's honest claim changed from a pass rate to 'did the model do the work'.

## Action items

| Action | Type | Status |
|---|---|---|
| Count `LLM inference failed` per trial and downgrade to fallback | detect | Done (landscape/live_trials.py) |
| Tag a new e2a-managed-providers release with the fix and pin it | prevent | Open (owner) |
