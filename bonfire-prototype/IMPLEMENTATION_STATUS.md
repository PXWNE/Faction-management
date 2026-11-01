# The Bonfire implementation status

## Delivered in this revision

- A separate FastAPI backend under `backend/` with SQLite persistence and Render persistent-disk blueprint.
- Individual leadership users, hashed passwords, signed sessions, role-checked API operations, and one-time admin bootstrap.
- Encrypted server-side Torn API key storage; key verification checks the key owner's faction ID and required faction selections before sync.
- Torn roster sync and raw faction giveFunds news ingestion.
- War and settlement records, draft snapshots, leader approval, immutable approved obligations, and source-readiness gate.
- Expiring/idempotent payment intents, Torn Give to User / Pay Day links, partial/manual evidence records, reversals, unique evidence allocation, audit history and CSV export.
- A small frontend API adapter at `src/backend.js` for the next integration step.
- Backend workflow tests and original calculation regression tests.

## Not yet completed

- The React prototype still runs on local demo state; `src/backend.js` is an adapter, not yet connected to the screens or a login UI.
- Full ranked-war, attack and chain imports, pagination/checkpoints, raw-source storage for all data, and automatic background scheduling are not yet implemented.
- Torn v2 `News` has only `id`, `text`, and `timestamp`. Therefore giveFunds records are imported verbatim and must be classified by an authorized treasurer before exact matching. No guessed parser is used.
- Production multi-instance concurrency, PostgreSQL, backups/restore drill, rate-limit/backoff scheduler, security review and real authorized Torn API verification remain required.

Do not use the prototype's local demo data as live settlement data. Do not deploy it as the faction's payment source of truth until the UI/API integration and data-import acceptance tests are completed.
