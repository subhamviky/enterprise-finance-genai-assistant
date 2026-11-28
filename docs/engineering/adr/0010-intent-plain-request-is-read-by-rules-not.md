# ADR 0010: The intent of a plain request is read by rules, not the model

- **Status:** Accepted
- **Date:** 2026-11 (Phase C)
- **Deciders:** repository owner

## Context

Measured per request, the intent step cost one of two or three model calls although the request often says plainly what it wants and names the record.

## Options considered

A) Always ask the model. B) Rules first when a record id and plain words are present, else the model (switchable with `GENAI_INTENT_BY_RULES`).

## Decision

B. `sure_intent` returns an intent only for an unambiguous request; an unclear request still goes to the model; the ids are always the ones in the text.

## Consequences

One model call fewer per plain request (simulated: 2 to 1 calls, 12 to 23% fewer tokens; live numbers in EVALUATION_REPORT.md). A rule-misread is limited because policy checks and approval still apply.
