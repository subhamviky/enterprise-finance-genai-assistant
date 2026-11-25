# genai-assistant-service — specification (A2C RequirementsAgent)

## Context
A finance investigator over three systems of record (reconciliation, settlement, order-to-cash) and the audit findings: answers why a payment is unmatched or a settlement delayed or flagged, from their data with citations, separating verified from inferred; proposes a write-off or refund within policy; executes an adjustment only after a second person approves.

## Clean Architecture layer map
| Layer | Responsibility | Location |
|---|---|---|
| Data model | Request/response DTOs and events | models / domain |
| Interface contract | Ports for stores, queues and tools | services (interfaces) |
| Service layer | Domain logic behind one public entry point | services |
| Exposure layer | HTTP routes and queue handlers | routers / controller |

## Mandatory NFRs and their enforcing mechanism
| NFR | Mechanism |
|---|---|
| Audit | Every material decision is recorded with its evidence |
| Idempotency | Atomic claim per (tenant, request_id) before the material effect; replay returns the stored result |
| Observability | JSON logs with correlation id, operation timing, counters, p95 SLO check |
| CircuitBreaker | Breaker per dependency; open circuit fails fast |
| RetryWithBackoff | Bounded retries with jittered exponential backoff and a retry budget |
| HealthCheck | Liveness endpoint used by the container platform |
| GracefulShutdown | SIGTERM stops intake and drains in-flight work |

## E2A class mapping
| E2A class | Use in this service |
|---|---|
| BaseAgent / BaseWorkflow | Agentic steps, when the service reasons with a model |
| BaseToolService | Every outbound integration (REST or MCP) |
| BaseIdempotencyStore | Claim per request_id before any material effect |
| BaseObservability | Structured logs, traces, metrics, SLO evidence |
