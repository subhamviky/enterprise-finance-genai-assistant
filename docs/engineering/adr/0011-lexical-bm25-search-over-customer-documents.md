# ADR 0011: Lexical (BM25) search over the customer's documents, not embeddings

- **Status:** Accepted
- **Date:** 2026-11 (Phase C)
- **Deciders:** repository owner

## Context

Questions about rules ('What is the write-off limit?') should be answered from the customer's own documents with citations.

## Options considered

A) A vector store with embeddings. B) BM25 over `##` passages, in process.

## Decision

B. `services/documents.py`; tenant-scoped; no model, account or network; the seam for a vector store is `DocumentStore.search`. A CI test compares each customer's documents with the enforced policy.

## Consequences

Deterministic, free and enough for a handful of passages. A paraphrase sharing no word finds nothing (the answer is NOT_FOUND, never invented). A real corpus would need embeddings.
