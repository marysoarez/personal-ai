---
name: code-review
description: Review code changes for concrete bugs, regressions, security issues, and missing coverage. Use for pull requests, diffs, commits, or implementations; for PKT Personal, use `pkt-personal-code-review`. Prioritize actionable findings and cite precise file and line locations.
---

# Code Review

## Review workflow

1. Identify the requested scope and the exact change under review. Inspect the diff and surrounding code needed to understand behavior.
2. Read repository guidance such as `AGENTS.md`, contributor instructions, and relevant architecture docs.
3. Trace changed code through its callers, data sources, persistence, API boundaries, and UI states where relevant.
4. Look for defects introduced by the change: incorrect behavior, regressions, security or privacy risks, data loss, compatibility failures, and missing error handling.
5. Report only actionable findings supported by the code. Do not report style preferences, hypothetical issues without a plausible path, or pre-existing problems unrelated to the change.

## Finding requirements

Each finding should:

- Describe the concrete scenario that triggers the problem and its user or system impact.
- Point to the smallest relevant changed line range. Use exact file paths and line numbers when available.
- Be concise and independently actionable.
- Use a severity label consistent with the project's review convention; otherwise use `P1` for urgent, broad impact, `P2` for normal defects, and `P3` for minor issues.
- Focus on one issue per finding rather than combining unrelated concerns.
- Check authorization, personal-data exposure, concurrency, error handling, contract compatibility, performance, and relevant test gaps.
- Distinguish confirmed defects from hypotheses that need validation; do not modify code unless asked.

Before reporting a finding, verify that it is introduced by the change and that the cited location falls within the diff when the review format requires it. If uncertain, investigate further or omit it.

## Areas to inspect

- Boundary conditions, nullability, empty inputs, ordering, and concurrency.
- Authentication, authorization, validation, injection, secrets, and sensitive data exposure.
- Persistence, transactions, retries, idempotency, and partial failure.
- Dependency and build-pipeline changes, lockfiles, package provenance, and exceptional/error paths (including OWASP Top 10:2025 risks where applicable).
- API contracts, schema compatibility, migrations, and backward compatibility.
- UI loading, empty, error, and success states; accessibility where UI changes are in scope.
- Tests that fail to cover the changed behavior or important regression paths.

## Output format

List findings first, ordered by severity. Use this format:

```text
[P1] Short title — path/to/file.ext:line
Explain the triggering scenario and impact, then suggest a specific correction.
```

If no actionable issues are found, say so plainly. Then mention any relevant verification performed and any limits of the review. Do not claim that tests passed unless they were run.




