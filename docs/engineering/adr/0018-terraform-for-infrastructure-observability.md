# ADR 0018: Terraform for infrastructure; the observability stack is applied by hand

- **Status:** Accepted
- **Date:** 2026-11 (GCP-01, Phase B)
- **Deciders:** repository owner

## Context

Infrastructure must be reproducible and destroyable on schedule.

## Options considered

A) Console clicks. B) Terraform stacks per concern, with mocked-provider tests in CI. C) Apply everything from CI.

## Decision

B for all stacks; CI runs fmt, validate and test; applies of foundation and observability are done by the owner in Cloud Shell, because the deployer deliberately cannot read logs or administer monitoring.

## Consequences

Reproducible and reviewable infrastructure; a destroy order for teardown. Applies depend on a person with Cloud Shell, which was flaky (post-incident review 0009), hence the ops workflow for deploys.
