# ADR 0005: GitHub Actions authenticates to Google Cloud through Workload Identity Federation; no key exists

- **Status:** Accepted
- **Date:** 2026-11 (GCP-01)
- **Deciders:** repository owner

## Context

CI must deploy and run the cloud scenario. A service-account JSON key in a repository secret is the classic leak.

## Options considered

A) A JSON key in a secret. B) Workload Identity Federation limited to the owner's repositories.

## Decision

B. The deployer service account is impersonated through a WIF provider restricted to the owner's repositories; the two scenario people are stand-in service accounts the deployer impersonates to mint ID tokens.

## Consequences

No long-lived credential to rotate or leak. The deployer's roles are broad for a demo (run.admin, artifactregistry.writer, datastore.owner and others) and deliberately lack `logging.viewer`, so the trace check runs in Cloud Shell. At teardown the WIF provider and secrets are deleted.
