# ADR 0020: Remove pip from the runtime image

- **Status:** Accepted
- **Date:** 2026-11 (Phase B)
- **Deciders:** repository owner

## Context

The vulnerability scan flagged setuptools inside the runtime venv; upgrading setuptools did not remove the finding because pip vendors its own copy.

## Options considered

A) Pin and upgrade. B) Waive the finding. C) Do not ship pip (or setuptools) in the runtime venv.

## Decision

C. The runtime image contains only what runs; installs happen in the builder stage.

## Consequences

Smaller attack surface and a clean scan. The runtime cannot install packages (intended).
