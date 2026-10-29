---
name: escalabilidade
description: Plan performance, capacity, availability, and cost for Flutter, Node, and Firebase systems. Use before optimizing hot paths or designing for growth.
---

# Escalabilidade

## Establish evidence first

1. Inspect the architecture, deployment model, current bottlenecks, and available telemetry.
2. Record expected traffic, peaks, data volumes, latency/error SLOs, and cost constraints as assumptions before recommending an optimization.
3. Measure the current baseline. Avoid claims about capacity without load-test or production evidence.
4. Prefer gradual changes that preserve correctness and security; test load only in an authorized controlled environment.

## Design checks

- Firestore: required composite indexes, pagination and query limits, small documents, hotspot avoidance, and N+1 patterns.
- APIs: stateless services, bounded timeouts, retries with backoff for idempotent operations, and queues/DLQs for asynchronous work where appropriate.
- Concurrency: make reservations, quotas, and unique confirmations atomic or guarded by an explicit concurrency strategy.
- Observability: traces, p95/p99 latency, throughput, error rate, cost per operation, and actionable alerts.
- Caching: define invalidation and freshness explicitly; isolate cached data by user/tenant to prevent leaks.

Compare before/after latency, errors, throughput, and cost. Do not optimize by weakening authorization or data correctness.
