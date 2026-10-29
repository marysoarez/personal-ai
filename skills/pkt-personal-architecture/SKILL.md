---
name: pkt-personal-architecture
description: Explain, design, refactor, or migrate the architecture of the PKT Personal Flutter app. Use for architecture decisions, feature boundaries, layering, dependency injection, routing, and choices between the current Provider/Firebase setup and the documented Modular/MobX model.
---

# PKT Personal Architecture

## Start with repository evidence

1. Inspect the current app before proposing or changing its architecture.
2. Read `references/project-architecture.md` for the recorded current stack and target model, then verify those details against the live repository.
3. Distinguish the current implementation from the reference model. Do not assume the model architecture has already been adopted.
4. Keep architecture changes incremental, limited to the requested scope, and compatible with neighboring features.

## Current architecture principles

The recorded PKT Personal app uses Flutter/Dart, feature folders, Provider with `ChangeNotifier`, Firebase datasources, domain entities and repository contracts, and centralized `MaterialApp` routes. Verify this against the current checkout before relying on it.

For features still on this stack:

- Keep feature code under `lib/features/<feature>/`.
- Separate `domain`, `data`, and `presentation` responsibilities according to local conventions.
- Keep Firebase/Firestore access in data sources; keep data models and Firebase document mapping out of UI and domain layers.
- Define repository contracts in the domain and implement them in data, mapping models to entities at the boundary.
- Register providers and routes where the existing app expects them.

## Target model and migrations

The architecture reference also documents a modular feature model using Flutter Modular, MobX, Dio, Hive, and related services. Treat it as a target/reference, not as the current default. When a feature is already migrated, follow that feature's module and state-management conventions.

- Do not introduce a new state-management, routing, dependency-injection, networking, persistence, or code-generation package just because it appears in the target model.
- Explain material tradeoffs before broad architectural changes.
- Migrate one feature or boundary at a time, preserving public routes and behavior.
- Add adapters when old and new styles must coexist; avoid unrelated rewrites.
- Keep DTOs and infrastructure details out of domain and UI contracts.

Read `references/project-architecture.md` when a decision needs concrete folder examples, naming conventions, or the recorded migration shape.
