# ADR 0001: Run the landscape on the real Google Cloud free tier, and never upgrade

- **Status:** Accepted
- **Date:** 2026-11 (GCP-01)
- **Deciders:** repository owner

## Context

The goal is hands-on, visible GenAI forward-deployed-engineer experience on a real cloud, with no running cost. The Google Cloud trial gives a credit and Always Free products; upgrading would remove the spending ceiling.

## Options considered

A) Local emulators only. B) A paid account with budget alerts. C) The free trial, Always Free products only, never upgraded.

## Decision

C. Only Always Free products and the Gemini free tier are used; the trial is not upgraded; a budget alert fires at the first cent; Terraform refuses non-free regions and models. The trial ends about 23 February 2027 and the landscape is destroyed in the week of 8 February 2027.

## Consequences

Everything runs on real services (IAM, Pub/Sub, Cloud Run, Firestore) with no bill. The price is hard limits (one Firestore database, one e2-micro VM, small Gemini quotas, scale to zero with cold starts) that shaped several later decisions (ADR 0003, 0004, 0007). Nothing here is a production sizing.
