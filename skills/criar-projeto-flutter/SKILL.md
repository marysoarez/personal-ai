---
name: criar-projeto-flutter
description: Bootstrap or adapt a reusable Flutter project. Use when creating a new Flutter app or establishing its initial architecture, environments, dependencies, and test setup.
---

# Criar Projeto Flutter

## Before scaffolding

1. Inspect the requested project location and existing files. Do not overwrite an existing project.
2. Confirm platforms, SDK constraints, product scope, and any existing repository conventions.
3. Check current compatible package versions before adding dependencies; never copy stale version pins blindly.
4. For an existing project, preserve its current architecture unless the user requested a migration.

## Optional modular baseline

When a new project calls for a feature-first modular MVVM architecture, a suitable shape is:

```text
lib/
  app/
  core/
  features/<feature>/
    module/
    domain/{entities,repositories,errors}/
    data/{dto,repositories,services}/
    ui/{pages,widgets,viewmodels,states}/
```

A possible flow is `Page -> ViewModel -> Repository contract -> Repository implementation -> Service -> API`. For new projects without a routing decision, start from the [current Flutter architecture recommendations](https://docs.flutter.dev/app-architecture/recommendations), including `go_router` where it fits. Flutter Modular, MobX, Dio, and typed failures such as `Either<Failure, T>` are optional alternatives; select them only when the product or team needs them. Keep transport and DTOs out of pages/viewmodels, keep the domain independent of Flutter, and keep sensitive authorization on trusted servers.

## Deliverable

Create a runnable starter with a small working feature, environment configuration that does not commit secrets, static analysis and tests, code-generation instructions when relevant, and a README with setup/run/test commands. Include only packages that fit the SDK and the requested product. Run `dart format`, `flutter analyze`, and `flutter test` when available and report actual results.

