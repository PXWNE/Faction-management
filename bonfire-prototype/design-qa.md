# Design QA — The Bonfire Faction Management

final result: passed

## Reference and implementation

- Source visual truth: `qa/reference.png`, selected by the user.
- Source pixels: 1487 × 1058.
- Browser-rendered implementation: `qa/desktop-final.jpg`.
- CSS viewport: 1440 × 1024; browser content capture: 1425 × 1013. The in-app browser excludes/scales its scrollbar area. Source resized to the exact captured size for comparison; no artificial device frame.
- State: August 28 war, original preset, unmodified Draft, all players, desktop. Brand changed to The Bonfire Faction Management as explicitly requested.
- Combined full-view evidence: `qa/comparison.jpg`.
- Focused table/rules comparison: `qa/comparison-detail.jpg`.
- Mobile evidence: `qa/mobile.jpg`, 390 × 844 CSS viewport. Menu open/close and navigation were exercised.
- Payment evidence: `qa/payment-pending.jpg`, `qa/payment-confirmed.jpg`.

## Comparison history

1. First browser capture (`qa/desktop.jpg`) showed an unbounded 24-row table pushing the settlement total below the main workspace. Classified P2: the selected design keeps its total visible.
2. Fixed with a bounded table scroll region, sticky header/footer and 14px table content. Added an accessible search label, retained the last valid preview for invalid input, and prevented hidden mobile navigation from remaining keyboard-focusable.
3. Re-captured (`qa/desktop-final.jpg`) and compared with the selected mock in the same combined image. Eight rows and the full-population total are visible together. No unresolved actionable P0/P1/P2 findings.

## Required fidelity surfaces

- Fonts/typography: Inter/system sans, compact bold page heading, semibold row names and money, tabular numbers. Readable product-sized labels. No unexpected font fallback or clipping observed.
- Spacing/layout: preserved narrow dark sidebar, wide light workspace, horizontal budget summary and pale-teal rules panel. Table bounded to keep totals visible. Added war tabs and source readiness are intentional functional extensions, shifting the table down by about one tab row.
- Colors/tokens: dark blue-charcoal sidebar, white base, teal primary action and pale mint calculation panel match the chosen visual system. Amber Draft and green readiness have text labels.
- Assets/icons: the reference has no photos/illustrations. Standard icons use Phosphor; the renamed wordmark uses a library Flame icon. No handcrafted SVG/CSS artwork or placeholder imagery.
- Copy/content: exact requested name, English UI, correct spreadsheet totals (160 war hits, 1019.52 respect, 261.952 points), exact allocation and intentional whole-dollar remainder differences from the image. Incorrect mock totals were corrected rather than reproduced.
- Responsive/focus: 390px layout has a working collapsed navigation and two-column amounts; global horizontal overflow was checked and not present. Only tables scroll horizontally. Labelled inputs, real controls, focus outline and modal Tab/Escape behavior included. This is not a complete WCAG audit.

## Functional browser verification

- Respect weight 0.1 → 0.2 changed total points 261.952 → 363.904 while preserving the fund. Discard restored the draft.
- Switching to October loaded independent hit-only rules and a $100m player pool; switching back retained August rules.
- Search narrowed to OZONE03 without changing full-population totals.
- Review/approve froze the $145,828,616 settlement and enabled payment preparation.
- Prepared OZONE03's exact remaining $11,899,457. Verified the rendered Torn prefill URL without opening or submitting a transfer.
- Preparing left paid amount at $0 and displayed Pending API confirmation.
- Explicit Simulate Torn transfer supplied a demo cash-transfer event; matching automatically recorded $11,899,457 paid and $0 due for that player.
- Overview reflected the confirmed amount; Settings reset restored clean demo data. Mobile navigation exercised after reset.
- Browser console errors checked after final rendering: none returned.
- Domain tests cover total preservation, deterministic remainder ties, bad input/fixed-rate deficits, actual-transfer vs balance-credit evidence, idempotency, ambiguity and prefill validation.

## Limitations and P3 follow-up

- No live API credential, real funds-news text parser or real transfer tested. No production auth/concurrency backend. These are implementation tasks, not hidden working capabilities of this demo.
- Quota editing, settlement revisions, coordination, imports and notifications are specified in the PDF but outside this frontend demonstration.
- P3: optional fixed trailing decimals for all respect/point cells; minor density differences from generated typography. Neither affects calculation or core use.

## Implementation checklist

- [x] Compare normalized full frame and focused table/rules evidence.
- [x] Fix bounded table/total visibility, focus and search label issues.
- [x] Re-capture and verify desktop and mobile behavior.
- [x] Exercise the calculation → approval → payment evidence flow without sending money.
- [x] Preserve clear demo/live boundary and selected visual direction.

## Revision 1.2 — user-requested workflow corrections

final result: passed

This revision intentionally expands the selected concept's functional layout in response to explicit feedback. The original remains the visual-system reference (sidebar, typography, palette, table and teal editing panel); new war timing and visible dollar prices are requested changes, not accidental drift.

### Latest evidence

- Same 1440 × 1024 CSS viewport: `qa/v12-desktop-final.jpg`; full document `qa/v12-calculator-full.jpg`.
- Combined source/latest comparison: `qa/v12-comparison.jpg`.
- Legible pricing regions: `qa/v12-prices-summary.jpg`, `qa/v12-pricing-detail.jpg`.
- Distinct financial queue: `qa/v12-payment-queue.jpg`.
- Full internal chain/member report: `qa/v12-chain-report.jpg`; milestones: `qa/v12-bonus-report.jpg`.
- Ongoing war and timezone: `qa/v12-current-war.jpg`.
- Key setup demonstration: `qa/v12-key-setup.jpg`.
- Responsive check: `qa/v12-mobile.jpg`, CSS viewport 390 × 844, body/content width 375 (scrollbar excluded), no global horizontal overflow.

### Findings corrected

- P1: a weight of 1 lacked a clear monetary interpretation. Added a visible payout-method selector, labelled points versus dollars, per-input dollar hints and an above-table unit-price summary. Fixed-dollar inputs have separate saved values and are never populated by reinterpreting point weights.
- P1: approval looked like bulk payment. Renamed Review calculation / Approve calculation - no transfer; clear no-money message; approval opens a separate payment queue. Browser check confirmed $0 paid and no pending intents after approval.
- P2: Wars and Payments duplicated the same workspace. Removed inline Payments from Wars. The payment view now has Recipient/Status/Approved/Paid/Remaining/Action and financial filters, without income/reserve or calculator panels.
- P1: chain detail primarily linked out to Torn. Added an internal report with member contributions, regular/bonus respect, milestones, coverage, search and report-specific export. External source is optional; illustrative member data is labelled.
- P2: ongoing-war discovery and API setup were not visible. Added Overview current-war entry, Current war shortcut, exact war-window demonstration, timezone and a Settings connection panel. Real key input stays disabled; no fake live connection.

### Browser checks

- Pool sample displays war hit ≈ $556,699.76 and respect ≈ $55,669.98.
- Switching to fixed rates starts with separate zero dollar inputs. Entering $500,000 per war hit produced $6,500,000 for OZONE03's 13 hits and $80,000,000 overall. Returning to pool restored the point values.
- Review/approve created an obligation snapshot and kept paid at zero. No calculator or income summary remained in Payments.
- Current-war example showed In progress, no final end, incomplete coverage and disabled Review calculation. UTC 12:00 displayed as Kyiv 14:00 without changing eligibility or totals.
- Connection preview required demo checks before enabling Use demo connection; real key field disabled throughout.
- Chain report contained 20 contributors and reconciled 5,000 hits, 21,512 respect and 9 bonuses. Bonus timestamps remain unavailable rather than invented.
- Domain/build checks: 11 tests passed; browser console errors checked after the latest render: none.

### Fidelity surfaces and limits

Typography, table alignment, teal/ink tokens, standard Phosphor icons and responsive forms preserve the chosen visual direction. Added blocks deliberately change above-the-fold density. Full-view and focused comparisons were inspected; no unresolved P0/P1/P2 issues. The repeated large price table was consolidated into an above-table summary and per-input hints.

Production source parsing, encrypted key storage, server collection, auth and concurrency remain specification work; no real API credential or transfer was used. The English PDF is revision 1.2, 24 pages.


## Portable file delivery correction

Added a self-contained classic-script HTML build and top-level archive index.html. The React/Vite source index remains unchanged. Embedded JavaScript syntax, complete inlining, PDF relative paths and absence of external startup assets were checked. Standard hosted production build passed. Direct file:// interaction could not be browser-tested because the browser tool permits only HTTP/HTTPS; no file-protocol success is claimed. Local storage failures now fall back to session memory without breaking the render.


## Portable CSS regression — corrected

User screenshot exposed unstyled content. Root cause: the font-import removal regex stopped at a semicolon inside the quoted Google Fonts URL, leaving an unclosed CSS string. Replaced it with removal that respects quoted URLs and added build-time validation of the CSS prefix and removal completeness. Rebuilt both portable copies. Browser verification of the exact standalone HTML over a plain local HTTP server found one stylesheet / 218 rules, sidebar background rgb(19,35,44), fixed position, and zero external script/style assets. Review calculation modal worked; browser console errors: none. Screenshot: qa/portable-css-fixed.png. Direct file:// browser access remains outside the browser tool protocol policy.
