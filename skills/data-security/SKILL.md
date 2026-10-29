---
name: data-security
description: Apply privacy by design and protect sensitive personal data. Use for personal or health/legal data, data retention, access policies, logging, export/deletion flows, and privacy reviews.
---

# Data Security and Privacy

## Review data lifecycle

1. Identify personal and sensitive data, its purpose, sources, recipients, access paths, and retention needs.
2. Minimize collection and retention. Define deletion and export behavior by data category and involve the responsible privacy/legal owner for legal basis or policy decisions.
3. Enforce authorization on the backend per user, resource, and tenant; never trust client-supplied roles as the authority.
4. Separate operational metadata from sensitive content. Encrypt in transit and at rest, and manage keys through an approved secrets/key-management system.
5. Use synthetic data in development and testing; do not expose secrets, tokens, full identifiers, or health/legal content in logs.

## Firebase and audit considerations

- Keep Storage rules closed by default; validate ownership and consent for access, and use short-lived links where suitable.
- Audit sensitive reads and mutations without copying sensitive content into the audit log.
- Consider incident response, deletion/export requests, and retention controls for each data category.
- Verify controls using local tests and emulators rather than production data.

Treat jurisdiction-specific requirements as constraints to verify with the responsible legal/privacy owner; do not present this skill as legal advice. Report concrete findings and actual verification performed.
