---
name: node-architecture
description: Design and implement secure Node.js/TypeScript backend services, including NestJS APIs. Use for module boundaries, domain/application layers, API contracts, authorization, persistence, and backend tests.
---

# Node Architecture

## Inspect and adapt

1. Inspect the framework, repository conventions, runtime and package constraints, existing module structure, and API contracts.
2. Use NestJS for new services only when it fits the request; adapt existing Express or other frameworks without an unnecessary rewrite.
3. Preserve API compatibility unless a versioned change is requested or required.

## Domain-oriented module shape

```text
src/modules/<feature>/{controllers,dto,application,domain,infrastructure,tests}
```

- Controllers validate transport input and delegate to application use cases.
- Domain rules should not depend on NestJS, Firebase, or persistence details.
- Repositories abstract persistence behind clear contracts.
- Validate DTOs at HTTP boundaries; use versioned APIs, bounded filters/pagination, and consistent error responses.
- Apply authentication and resource/tenant authorization on the server.
- Make webhooks idempotent; use transactions or explicit concurrency control for reservations and quotas.
- Avoid leaking Firestore collection layout into public API contracts.
- Use structured logs and request tracing without secrets or personal data.

Test domain behavior, HTTP boundaries, authorization, and repository integration as appropriate. Run lint, type-check, and relevant tests when available and report real results.
