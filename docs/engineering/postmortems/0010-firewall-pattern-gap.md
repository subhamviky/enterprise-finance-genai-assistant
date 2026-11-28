# 0010: The prompt-injection firewall missed `ignore   the above instructions`

- **Date of the work:** 2026-11-28
- **Severity:** SEV-3 (see README)
- **Status:** Actions complete
- **Authors:** repository owner, with Claude

## Summary

The first run of the new adversarial test suite showed the request `ignore   the above instructions` (extra spaces, the word 'the') passing the firewall, because the pattern was a literal with single spaces and no filler words.

## Impact

None: found by a test before any use. In production a hostile phrase could have reached the model, where the structural controls (policy checks, second-person approval) still held.

## Timeline

- A parameterised test with seven injection phrasings ran; six were refused, one was not.
- Patterns were rewritten with `\s+` and optional filler words (`all`, `any`, `the`, `your`, `my`).
- The suite (45 cases) passes and the case stays.

## Root cause

1. The patterns were written for the phrasing I had in mind.
2. The firewall is only the first line; it was never the only control.

## Detection

Found by running the scenario, a drill or a test; see the timeline for what made it diagnosable.

## What went well

Adversarial tests written first found a real gap on the first run; the structural controls meant it was not an incident.

## Action items

| Action | Type | Status |
|---|---|---|
| Tolerant patterns, with the failing case kept in the suite | prevent | Done |
| Grow the suite with every live finding | detect | Ongoing |
