---
name: flutter-development
description: Build, debug, refactor, or review Flutter and Dart applications outside the PKT Personal-specific architecture workflow. Use for widgets, navigation, state, forms, responsive layouts, platform integration, performance, accessibility, and tests. Follow the app's existing architecture and packages.
---

# Flutter Development

## Workflow

1. Inspect `pubspec.yaml`, SDK constraints, project structure, and nearby implementation before choosing a pattern.
2. Identify existing state management, routing, dependency injection, styling, and localization conventions.
3. Read the touched feature across its UI and data/domain boundaries where present.
4. Make the smallest complete change that preserves public behavior and reuses existing packages and shared widgets.
5. Format, analyze, and run focused tests when requested or required by the repository workflow; report exactly what was run.

## Architecture guidance

- When a project lacks an established pattern, consult the [official Flutter app architecture guide](https://docs.flutter.dev/app-architecture) as a starting point, then scale layers to the app complexity.
- Do not assume Flutter Modular/MobX is the default; use the dedicated `flutter-architecture` skill only when that stack is already present or explicitly requested.

## Implementation guidance

- Keep widget build methods readable and business logic out of widgets where the app already separates it.
- Model loading, empty, error, and success states explicitly.
- Use the state management and navigation tools already adopted by the app; do not migrate architecture as a side effect.
- Dispose controllers, focus nodes, streams, and other owned resources at the correct lifecycle boundary.
- Adapt layouts to supported screen sizes, text scaling, orientation, and platform conventions.
- Support semantics, usable tap targets, keyboard and screen-reader behavior where applicable, and sufficient contrast.
- Handle async errors and cancellation deliberately; do not silently swallow failures.
- Add or adjust tests for meaningful state transitions and regression paths using existing test patterns.

## Review checklist

- Does the change match the app's architecture, SDK constraints, and package versions?
- Are state, async errors, and resource lifecycles handled correctly?
- Are loading, empty, and failure cases represented?
- Does the UI adapt to supported devices and accessibility settings?
- Are routes and dependencies registered consistently?
- Are relevant tests updated and analyzer/formatter findings addressed?

Do not add packages or introduce new architecture, state-management, or routing patterns unless requested or required by the existing design.

