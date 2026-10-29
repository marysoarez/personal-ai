# PKT Personal Architecture Reference

## Current Workspace Snapshot

The current `pkt_personal` workspace is a Flutter/Dart app with a feature-first, layered structure in progress.

Observed stack:

- Flutter + Dart.
- Firebase Core, Firebase Auth, Cloud Firestore, Firebase Storage.
- Provider with `ChangeNotifier` controllers.
- `MaterialApp` with centralized app routes.
- Local feature folders under `lib/features`.
- Repository contracts in `domain/repositories`.
- Repository implementations in `data/repositories`.
- Remote datasources in `data/datasources`.
- Domain entities in `domain/entities`.
- UI/controller code under `presentation`.

Observed dependency setup:

- `main.dart` initializes Firebase through `FirebaseSetup.init()`.
- `MultiProvider` wires controllers.
- Controllers receive repository implementations.
- Repository implementations receive remote datasources.
- Remote datasources receive Firebase services from `FirebaseSetup`.

## Target/Model Architecture

The desired model architecture is modular + feature-first + layered, close to Clean Architecture.

Feature folders should separate:

- `domain`: entities, repository contracts, use-case/business contracts, and domain errors.
- `data`: DTOs/models, concrete repositories, remote datasources, local datasources, HTTP/Firebase services.
- `ui` or `presentation`: views/pages, viewmodels/controllers/stores, widgets.
- `module`: route and dependency registration when using Flutter Modular.

Reference feature names from the model:

- `feature_alpha`
- `feature_beta`
- `feature_gamma`

Reference module files:

- `feature_alpha_module.dart`
- `feature_beta_module.dart`
- `feature_gamma_module.dart`

Model stack:

- Flutter + Dart.
- Flutter Modular for navigation and dependency injection.
- MobX with code generation for reactive state.
- Dio for HTTP calls.
- Firebase Core, Crashlytics, Messaging, and Remote Config.
- Hive for local storage.
- Datadog for observability.
- Project-specific design system packages.

Potential modern evolution options:

- Riverpod or Bloc/Cubit instead of MobX.
- Go Router instead of Flutter Modular.
- Freezed for immutable models and unions.

Treat these as options, not defaults.

## Default Feature Shape

Use this shape for a new feature unless nearby code establishes a different convention:

```text
lib/features/<feature_name>/
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

Use this shape for a migrated Modular/MobX feature:

```text
lib/features/<feature_name>/
  domain/
    entities/
    errors/
    repositories/
  data/
    datasources/
    dtos/
    repositories/
    services/
  ui/
    pages/
    viewmodels/
    widgets/
  <feature_name>_module.dart
```

## Implementation Pattern

For current Provider/Firebase features:

1. Create or update the entity in `domain/entities`.
2. Create or update the repository contract in `domain/repositories`.
3. Create or update the model in `data/models` with `fromMap`, `toMap`, `fromEntity`, and `toEntity` when matching existing style.
4. Put Firestore calls in `data/datasources`.
5. Implement the contract in `data/repositories`, converting models to entities.
6. Put state and orchestration in `presentation/controllers`.
7. Put rendering and user interaction in pages/widgets.
8. Register dependencies in `main.dart` and routes in app route config.

For Modular/MobX features:

1. Define the domain first.
2. Keep DTOs out of domain and UI.
3. Register services, repositories, and stores in the feature module.
4. Register routes in the same module.
5. Run code generation for MobX when stores change.

## Naming

Prefer Portuguese domain names if the existing feature uses Portuguese (`aluno`, `professor`, `treino`, `dieta`).

Prefer snake_case for folder and file names:

- `aluno_repository.dart`
- `aluno_repository_impl.dart`
- `aluno_remote_data_source.dart`
- `aluno_controller.dart`

Prefer class names that mirror the file name:

- `AlunoRepository`
- `AlunoRepositoryImpl`
- `AlunoRemoteDataSource`
- `AlunoRemoteDataSourceImpl`
- `AlunoController`

## Validation

Use:

```powershell
dart format .
flutter analyze
flutter test
```

If full tests are too broad, run focused tests for the touched feature and report what was not run.



