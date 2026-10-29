---
name: pkt-personal-code-review
description: Review Flutter/Dart changes in the PKT Personal app. Use for diffs involving feature architecture, Provider/ChangeNotifier, Firebase/Firestore data flow, repositories, routes, dependency registration, or migrations between app patterns.
---

# PKT Personal Flutter Code Review

## Review workflow

1. Read repository instructions, the diff, and nearby feature code. Verify the architecture in the live code; consult `references/project-architecture.md` as context, not as proof that the target model is implemented.
2. Trace changed behavior across UI/controller, repository, datasource, model/entity, route, and dependency-registration boundaries that the diff touches.
3. Report only concrete defects introduced by the change. Prioritize runtime failures, data corruption, security issues, broken navigation, and regressions.

## PKT-specific checks

- Does the feature follow the pattern used by neighboring code: current Provider/Firebase or migrated Modular/MobX?
- Is Firebase/Firestore access leaking into widgets, controllers, or domain entities?
- Are repository contracts and implementations consistent, with model/entity mapping at the intended boundary?
- Are providers and routes registered where this feature's app pattern expects them?
- Are loading, empty, success, and error states complete and consistent?
- Are async subscriptions, controllers, and other resources disposed by their owner?
- Do changes to Firebase rules or paths preserve authorization and prevent cross-user data access?
- Are generated MobX/Freezed outputs and documented generation steps consistent when applicable?
- Are focused tests missing for changed mapping, state transitions, or dependency/route wiring?

## Findings

List actionable findings first, ordered by severity. Point to the smallest relevant changed line range and explain the triggering scenario and impact. Use the repository's severity convention; otherwise use P1 for urgent broad-impact defects, P2 for normal defects, and P3 for minor issues. Omit style preferences and speculative risks.

If no actionable issues are found, say so plainly. Mention verification only when it was actually performed; do not claim tests or analysis passed unless run.

