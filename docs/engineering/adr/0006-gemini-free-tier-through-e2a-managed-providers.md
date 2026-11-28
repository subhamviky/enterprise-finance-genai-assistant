# ADR 0006: Gemini free tier through e2a-managed-providers, with deterministic fallbacks

- **Status:** Accepted
- **Date:** 2026-11 (GCP-01)
- **Deciders:** repository owner

## Context

A language model is needed for intent, explanation and proposals, but the free tier is quota-limited, sometimes busy (429, 503), and not deterministic.

## Options considered

A) A paid model. B) A self-hosted model. C) The Gemini free tier through the `gemini_api` profile, with every agent able to fall back to the verified facts.

## Decision

C. The model is chosen by `LLM_MODEL_ID` (a configuration change, not a code change). Every model call is bounded (timeout, retries, token budget). A failed or ungrounded model answer degrades to the verified facts or to no proposal; it never invents.

## Consequences

Availability does not depend on the model; the model's share of the work is measurable (degraded rate, ADR 0022). The cost is quality variance across models, which the multi-trial evaluation records (EVALUATION_REPORT.md).
