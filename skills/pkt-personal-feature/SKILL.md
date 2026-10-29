---
name: pkt-personal-feature
description: Implement or modify a user-facing feature in the PKT Personal Flutter app. Use for feature folders, entities, repository contracts and implementations, Firebase datasources, Provider controllers, screens, routes, and dependency registration. Follow the architecture already used by the neighboring feature.
---

# PKT Personal Feature Implementation

## Workflow

1. Inspect `pubspec.yaml`, routes, provider registration, and the closest comparable feature before editing.
2. Confirm whether the target area uses the current Provider/Firebase pattern or an already migrated Modular/MobX pattern. Consult `references/project-architecture.md` for the recorded architecture, then verify against code.
3. Trace the feature end to end and identify the smallest complete change. Preserve existing public behavior and naming conventions.
4. Implement in the matching layers below. Do not mix patterns from different stacks in one feature without a migration reason.
5. Add or adjust focused tests for domain rules, model mapping, repository behavior, controller state, or route wiring as relevant.
6. Run `dart format`, `flutter analyze`, and focused tests when requested or required by the repository workflow; report what was actually run.

## Current Provider/Firebase feature shape

```text
lib/features/<feature>/
  domain/
    entities/
    repositories/
  data/
    datasources/
    models/
    repositories/
  presentation/
    controllers/
    pages/
    widgets/
```

For this pattern:

- Put business entities in `domain/entities` and repository contracts in `domain/repositories`.
- Put Firebase calls in `data/datasources`; map Firestore documents in `data/models`.
- Implement repository contracts in `data/repositories` and convert models to entities there.
- Keep UI and controllers from depending directly on Firebase SDKs or persistence DTOs.
- Use `ChangeNotifier` controllers when neighboring features use Provider; represent loading, success, empty, and error states clearly.
- Register controllers, repositories, and datasources with the existing `MultiProvider` setup and add routes to the existing route table.

## Already migrated feature shape

For a feature already using Flutter Modular and MobX, follow its module conventions:

- Keep route and dependency registration in that feature's module.
- Use the feature's established store/viewmodel and code generation workflow.
- Keep Dio, Firebase, or other service calls in data/services layers.
- Keep DTOs out of domain and presentation contracts.

## Naming and local conventions

- Follow the language already used in the feature's domain; preserve Portuguese names when that is the established vocabulary.
- Follow existing `snake_case` file and folder naming and class naming patterns.
- Read the nearby feature end to end before adding abstractions or changing dependency registration.
- Do not add Freezed, Riverpod, Bloc, Go Router, Dio, Hive, or other packages unless the task requires them or the feature already uses them.

## Feature checklist

- Are data access and mapping in the right layer?
- Are dependencies and routes registered in the established place?
- Are loading, empty, success, and failure states handled?
- Are existing behavior and API/data contracts preserved?
- Are important mapping and state transitions covered by focused tests?

