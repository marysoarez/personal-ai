---
name: criar-testes
description: Design and implement useful tests for existing code. Use for unit, widget, integration, contract, authorization, security, and concurrency test coverage.
---

# Criar Testes

## Strategy

1. Inspect the project test setup and the behavior being changed.
2. Map critical flows and boundaries; choose unit tests for business rules, widget tests for UI, integration tests for API/database flows, and contract tests for client/server guarantees.
3. Cover happy paths, validation, denied authorization, integration failures, boundary values, and concurrency/idempotency where relevant.
4. Keep tests deterministic, isolated, and independent of execution order.
5. Run the added and related tests; report commands and failures. Report coverage only when measured.

## Stack guidance

- Flutter: follow existing test patterns for ViewModels, repositories, and widgets; use `flutter test`.
- Node: use the project's Jest/Vitest setup and HTTP test tools such as Supertest when already present.
- Firebase: prefer the Emulator Suite for Auth, Firestore, Storage, and rules. Never use production accounts, credentials, or data for local tests.

Avoid brittle snapshots and mocks that merely reproduce the implementation. Prefer behavior assertions, controlled dependencies, and regression cases tied to observable outcomes.
