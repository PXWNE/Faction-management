# The Bonfire Faction Management

Interactive leadership prototype, based on the selected light/teal design. The production requirements are in `public/The_Bonfire_Faction_Management_Requirements_EN.pdf` (English, version 1.2).

## Run

For a preview without installing anything, open `Open Prototype.html` directly in a browser. The delivery ZIP also has a top-level `index.html` with the same self-contained preview. Scripts and styles are embedded; no local server or network is needed for the demo. Torn links still need internet. Browser file-storage policies may prevent saving demo changes between sessions.

Regenerate the self-contained preview after source edits: `pnpm build:portable`.

Requires Node 20.19+ / 22.12+ and pnpm.

```sh
pnpm install
pnpm dev --host 127.0.0.1 --port 4173
```

Build: `pnpm build`. Calculation and confirmation tests: `pnpm test:domain`. The bundled hosting worker remains available; this prototype has not been deployed.

## Try the core flow

1. Open the August war and change a weight. Payouts recalculate without changing other wars. Discard restores saved values.
2. Try the six presets. The visible Payout method selector separates point-based fund sharing from fixed dollars per action. Effective dollar prices are shown for all four actions; inactive-mode values are kept separate. Also try bonuses, search and payout breakdowns.
3. Use **Review calculation**, then **Approve calculation - no transfer**. This freezes amounts owed but leaves paid at zero. Payments is a separate financial queue, not a copy of the calculator.
4. Open Payments, choose a recipient and prepare a full or partial amount.
5. The Torn link prepares a form only. Give money prefills recipient/amount but changes the member's recorded faction balance. Pay Day has a different balance effect and no verified prefill contract here.
6. Click **Simulate Torn transfer** to create explicit demo API evidence. The matcher automatically confirms the unique transfer; opening a form alone never records payment.
7. Chains → View in-app report shows member contributions, regular/bonus respect, milestone history, source coverage and a chain-specific CSV. The external Torn link is secondary. Member-level chain fixtures are explicitly illustrative.
8. Overview → View current war opens the in-progress example; Wars shows official-window design, UTC/Kyiv display and blocked approval until final data is ready.
9. Settings → Faction API connection previews leadership key setup, demo access checks and connection states. Real-key input is disabled; no secret is accepted.
10. Settings → Reset demo workspace restores the original sample.

## Boundaries

- Local browser persistence, demonstration data and simulated transfer evidence. No live Torn credentials, server authentication, background API collector, funds-news parser, money transfers or Discord integration. The key-setup flow is a demonstration only; no real credential should be entered.
- August war-hit/respect totals reproduce the supplied spreadsheet. Other history, source-readiness labels and subtype detail are illustrative.
- The matcher uses normalized demo cash-transfer events. Production must parse real `faction/news?cat=giveFunds` responses, validate faction/recipient/amount/time and consume source IDs atomically on the server. Ambiguous evidence must stay in review.
- Pending intents and concurrency protection are demonstrated locally; production needs server-side locks, expiry/recovery and idempotency. Do not deploy this demo as a live payment system.
- Private battle/work stats and member-key onboarding are excluded.
- Quota editing, settlement revisions, shift planning, alerts and full source imports remain production/follow-on work as specified in the PDF. This is a functional frontend prototype, not the production backend.

## Structure

- `src/model.js`: exact integer/rational payout allocation, presets, demo data and idempotent evidence matching.
- `src/App.jsx`: navigation, forms, snapshots, payment preparation, demonstration ledger and exports.
- `src/styles.css`: responsive selected design.
- `tests/domain.test.mjs`: meaningful calculation and transfer-evidence regression checks.
- `design-qa.md` and `qa/`: visual comparison and browser evidence.

Official prefill reference: https://wiki.torn.com/wiki/Faction#Give_To_User

The original production tracker was not modified.

## Persistent backend (new)

A separate FastAPI service is included in `backend/`. It adds persistent SQLite storage, individual leadership accounts, role checks on every mutating route, encrypted server-side Torn-key storage, roster sync, war/settlement snapshots, payment intents, a payment ledger, reversals, audit history and CSV export. It does **not** send money or treat opening a Torn form as proof of payment.

### Local run

```sh
cd backend
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
# Create a Fernet key and a separate token secret; put both in your environment.
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
python -c "import secrets; print(secrets.token_urlsafe(48))"
# Set BONFIRE_FERNET_KEY and BONFIRE_TOKEN_SECRET before starting.
uvicorn app:app --reload --port 8000
```

Open `http://localhost:8000/docs`. On first setup, POST `/api/bootstrap` once to create the first administrator. The endpoint permanently locks after the first user exists. Then sign in at `/api/auth/login` and use the returned bearer token. Create additional leadership users with `/api/users`.

### Render deployment

`backend/render.yaml` defines a separate web service and persistent disk. Create it as a **new** Render service; do not attach it to or replace the existing Torn Chain Tracker. Set `BONFIRE_FERNET_KEY` to a valid Fernet key generated with the command above, `TORN_FACTION_ID` to the faction ID, and `BONFIRE_CORS_ORIGINS` to the exact frontend origin. Render's generated value is not suitable for the Fernet key unless it is a valid URL-safe base64 Fernet key.

### API workflow

1. Bootstrap the first admin, then create separate leader/officer/treasurer/viewer accounts.
2. Store the faction API key with `PUT /api/settings/torn-key`; it is encrypted at rest and never returned. The app uses the key server-side for `/api/sync/roster` and `/api/sync/give-funds`.
3. Import/verify wars and source coverage, then save a calculation draft with `POST /api/settlements`.
4. A leader approves the immutable snapshot with `POST /api/settlements/{id}/approve`. Approval creates obligations only.
5. A treasurer creates a time-limited payment intent with `POST /api/payment-intents`. The API returns a Torn link; the transfer still happens manually in Torn.
6. `/api/sync/give-funds` imports candidate faction news and confirms only a unique exact player/amount/time match. Unmatched or ambiguous news remains unconsumed. `/api/payments/manual` is available for evidence-backed manual reconciliation.
7. Incorrect local ledger entries can be reversed with a reason; the Torn transfer itself is never reversed by this API.

### Important production gates

- The Torn news parser intentionally fails closed when the live payload does not expose a clear recipient, amount and timestamp. Verify current Torn v2 response shapes and faction permissions against your own authorized faction before enabling reconciliation. Never loosen the matcher based on guessed field names.
- `source_state='complete'` and a non-null official `end_at` are required for approval. The current frontend prototype still uses local demo state and is **not yet wired to this API**. Do not use it for live settlements until the UI is connected to these endpoints and the full import pipeline has been tested.
- SQLite on a single persistent Render disk is a suitable first deployment for one service instance. Do not scale this service horizontally; move to managed PostgreSQL and distributed locking before multiple instances.
- Configure HTTPS, exact CORS origins, backups, alerting, and a verified restore test before production use. Rotate the encryption key only with a migration that re-encrypts stored credentials.
