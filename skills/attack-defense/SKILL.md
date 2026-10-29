---
name: attack-defense
description: Threat-model and harden applications against OWASP risks, API abuse, and privilege escalation. Use for security reviews, attack-surface analysis, authorization checks, and defensive implementation.
---

# Attack Defense

## Threat-model workflow

1. Inspect repository guidance, architecture, dependencies, deployment boundaries, and the user-requested scope.
2. Identify assets, actors, trust boundaries, entry points, and plausible abuse cases before suggesting controls.
3. Prioritize authorization on the server for every resource ID, owner, tenant, sensitive field, and state transition.
4. Implement small defensive changes that preserve public contracts unless a security fix requires a documented break.
5. Validate controls with safe negative tests in local or emulator environments; do not probe third parties or production systems without explicit authorization.

Use the current OWASP Top 10 as an awareness baseline, not a complete threat model: [OWASP Top 10:2025](https://owasp.org/www-project-top-ten/). Include relevant supply-chain, integrity, misconfiguration, and exceptional-condition risks alongside application-specific threats.

Treat the Top 10 as awareness guidance, not a complete assurance standard; check the versioned OWASP guidance relevant to the application and supplement it with threat modeling and testing.

## Threats to examine

- Broken access control, IDOR/BOLA, authentication bypass, and privilege escalation.
- SQL/NoSQL injection, unsafe query interpolation, XSS, CSRF, SSRF, and unsafe deserialization where relevant.
- Upload validation using size limits, actual MIME/type checks, and malware scanning when appropriate.
- API abuse, missing per-user/IP rate limits, logical denial of service, and expensive unbounded operations.
- Weak webhook signature checks, exposed secrets, unsafe logs, and insufficient audit trails.
- Firebase rules that allow broad reads/writes or fail to isolate users and tenants.

## Output and safety

Classify findings by severity and include evidence, impact, a correction, and a regression test. Distinguish confirmed vulnerabilities from hypotheses that need validation. Never read, print, or commit credentials, tokens, or real sensitive personal data. Use synthetic data and local emulators. Report commands and actual results; do not claim checks passed unless executed.


