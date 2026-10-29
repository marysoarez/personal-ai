---
name: criar-feature
description: Implement an end-to-end feature across UI, API, data, authorization, and tests in the current repository. Use this general workflow across Flutter, Node, Firebase, or full-stack work; for PKT Personal, use `pkt-personal-feature`.
---

# Criar Feature

## Workflow

1. Extract user stories, actors, states, failure cases, permissions, and acceptance criteria from the request.
2. Identify the actual stack and inspect repository instructions, dependencies, architecture, and neighboring features.
3. Define or verify API and data contracts, ownership, and server-side authorization before building UI flows.
4. Plan the smallest complete change across domain, repositories, services, viewmodels/controllers, pages/widgets, routes, and dependency injection as the project requires.
5. Implement using existing conventions. Do not apply Flutter-specific or Node-specific architecture to a different stack.
6. Cover success, invalid input, denied access, integration failure, concurrency, and boundaries where relevant.
7. Update documentation when contracts or setup change; report files, commands, results, and any unverified work.

## Quality rules

- Do not duplicate business logic across layers or invent placeholders that look like real integrations.
- Never use test mocks in production code.
- Preserve public APIs and compatibility unless the user authorizes a change or a security fix requires one.
- Connect each acceptance criterion to implementation and an appropriate test or verification.
- Enforce resource-level authorization on the server; client identifiers and roles are not proof of access.
- Do not expose credentials, tokens, or sensitive personal data. Do not invent test results.

