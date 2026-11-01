# Prototype Instructions

Run the local server yourself and open the preview in the browser available to this environment. Do not give the user server-start instructions when you can run it.

Before making substantial visual changes, use the Product Design plugin's `get-context` skill when the visual source is unclear or no longer matches the current goal. When the user gives durable prototype-specific design feedback, preferences, or decisions, record them in `AGENTS.md`.

When implementing from a selected generated mock, treat that image as the source of truth for layout, component anatomy, density, spacing, color, typography, visible content, and hierarchy.

Build app UI in `src/`. Keep `.openai/hosting.json`, `worker/index.js`, `scripts/prepare-sites-build.mjs`, and `tests/sites-worker.test.mjs` intact so the same local prototype can be handed to Sites. Before a Sites handoff, run `npm run build` and `npm run test:sites`; the build must leave `dist/client/index.html`, `dist/server/index.js`, and `dist/.openai/hosting.json`.

## Confirmed product decisions

- Exact product name: The Bonfire Faction Management. Use selected visual concept 1 (light table workspace, dark sidebar, teal rules panel).
- All requirements and prototype interface copy are English.
- Leadership audience; no additional personal keys or actions required from ordinary faction members. Exclude private battle and working stats.
- Default 10/10/80 allocation; free Xanax is a faction-reserve expense and must not reduce the player pool twice.
- Payment preparation opens Torn's documented prefilled form or the Pay Day fallback. Actual completion is automatically confirmed only from uniquely matched API transfer evidence, not from opening a link. Keep the prototype explicitly local/demo until a real backend is implemented.

## Revision 1.2 feedback

- Clearly distinguish point weights from dollars and show effective unit prices. Fixed-dollar rates use separate saved values.
- Review/approve calculation creates obligations only, never payments. Wars is calculation; Payments is a separate financial queue.
- Chain reports stay inside the app, with member/bonus/source views and CSV; Torn is optional source evidence.
- Show the current war, official start/end, display timezone and data readiness. No start/end inference from first or last attack.
- Make faction-key setup visible in Settings. This frontend prototype must not accept real credentials or claim a live API connection.

## Delivery

- Include a standalone HTML preview that opens by double-clicking without a development server. Keep the Vite source index and hosting template intact. The distribution ZIP must have an obvious top-level index.html preview.
