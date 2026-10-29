---
name: firebase-development
description: Implement and review Firebase integrations including Auth, Firestore, Realtime Database, Storage, Cloud Functions, Cloud Messaging, App Check, emulators, and Security Rules. For PKT Personal architecture-specific work, use the PKT skills.
---

# Firebase Development

## Workflow

1. Inspect app platforms, Firebase configuration, SDKs and package versions, initialization, environment setup, and existing data access patterns.
2. Identify which Firebase products are actually in use and read the relevant rules, indexes, functions, and client code before changing behavior.
3. Keep secrets and privileged credentials out of client code. Use server-side functions or trusted backends for operations requiring administrative authority.
4. Make the smallest change that preserves existing data contracts and security posture.
5. Prefer Firebase emulators for local integration checks when configured. Validate rules and focused behavior when the user requests verification or the project workflow calls for it.

## Data and security guidance

- Treat client input and client-side checks as untrusted; enforce authorization and validation in Security Rules or trusted server code.
- Apply least privilege to Firestore, Realtime Database, and Storage rules. Avoid broad public read/write access; begin with deny-by-default rules and add narrowly scoped grants.
- Firestore Security Rules are not filters: structure client queries so their constraints guarantee every possible returned document is authorized.
- Firestore server/Admin SDKs bypass client Security Rules. Protect these paths with IAM and enforce end-user authorization in the trusted backend.
- Check ownership and tenant boundaries on every relevant read, query, write, and storage path.
- Design Firestore queries with required indexes, pagination, and documented ordering; avoid unbounded collection reads.
- Consider offline persistence, retries, duplicate delivery, and idempotency for writes and event-driven functions.
- Handle authentication state changes, token refresh, account deletion, and provider errors deliberately.
- Keep sensitive data out of logs, analytics events, crash reports, and push notification payloads.
- Use App Check as a defense-in-depth measure where appropriate; do not treat it as a replacement for authorization rules.
- Keep Firebase Admin SDK and service account credentials on trusted servers only.

## Firebase Authentication

- For Flutter, use official Firebase Auth SDKs and providers appropriate to the requested platforms; account for platform-specific IDs, SHA configuration, redirect URLs, and consent flows.
- Handle account recovery, provider linking, email collisions, disabled accounts, account deletion, reauthentication for sensitive actions, and logout.
- In Node backends, verify Firebase ID tokens with Firebase Admin SDK, including signature, issuer, audience, and expiry; check revocation when the threat model requires it.
- Never trust a UID or role supplied in a request body as authentication. Resolve identity from the verified token and authorize access per resource and tenant on the server.
- Store profile and permission data under trusted server-controlled records; custom claims may assist lookup but do not replace resource-level authorization.
- Never log passwords, ID/refresh tokens, or sensitive account data. Test invalid/revoked tokens, disabled users, duplicate providers, and role spoofing in emulators or controlled tests.

## FlutterFire notes

- Follow the project's existing `firebase_core` initialization and generated Firebase options setup.
- Reuse established FlutterFire plugins and the project's repository/data-source boundaries.
- Use streams for live updates only when the UI needs them; cancel or dispose subscriptions at the owning lifecycle boundary.
- Separate emulator configuration from production configuration and avoid committing local credentials or production secrets.

## Review checklist

- Are Firebase rules restrictive and aligned with actual product authorization?
- Can a user access or mutate another user's data by changing a document ID or path?
- Are privileged operations isolated to trusted server environments?
- Are query indexes, pagination, offline behavior, and duplicate events considered?
- Are auth, network, permission, and rules-denied errors handled appropriately?
- Are secrets, tokens, and personal data excluded from source control and logs?
- Are rules and integration paths validated with emulators or focused tests when available?



