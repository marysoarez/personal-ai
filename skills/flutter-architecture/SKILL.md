---
name: flutter-architecture
description: Design or review Flutter MVVM architecture using Modular and MobX when a project already adopts or explicitly requests that stack. For PKT Personal architecture, use `pkt-personal-architecture`.
---

# Flutter Architecture

## Verify the local architecture

1. Inspect the repository, SDK constraints, architecture docs/ADRs, and neighboring features.
2. Use this pattern only when the app already follows it or the user explicitly requests it; preserve a justified existing alternative.
3. Propose material migrations before changing them, and migrate incrementally.

Flutter also publishes [app architecture recommendations](https://docs.flutter.dev/app-architecture) centered on UI/data separation, views, view models, repositories, and services. That guidance is framework-level and does not require Flutter Modular or MobX. The stack below is a project-specific option; follow the live code and request.

## Modular MVVM pattern

```text
Page -> ViewModel -> DomainRepository -> DataRepository -> Service -> HTTP/Firebase
```

- Pages render UI and delegate actions; ViewModels expose asynchronous state and commands.
- Domain repository contracts and entities remain independent of Flutter, Dio, and Firebase.
- Data repositories map DTOs to domain entities and encapsulate data sources.
- Services perform I/O; keep HTTP/Firebase access out of pages and ViewModels.
- Feature modules register routes and dependency bindings with appropriate lifetimes; avoid a scattered service locator.
- Model loading, empty, success, and failure states explicitly; cancel requests and dispose resources correctly.
- Use MobX for state and Modular for DI/navigation when consistent with the project. Use `Either<Failure, T>` when typed failures improve clarity; do not add mandatory use-case layers without concrete value.
- Keep widgets and domain rules testable; cover ViewModels and repositories.


