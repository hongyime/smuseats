# SMU Seats maintenance

## Loading and filter task list — 2026-09-13

- [x] Measure homepage/route JavaScript and diagnostic build outputs; reproduce incompatible building/floor selection.
- [x] Defer detailed route data and exclude diagnostic-only build outputs while preserving all source files and public floor plans.
- [x] Repair confirmed filter behavior and verify registry, sharing, contributor, routing and failed-load behavior.
- [ ] Release through hosted checks to existing production with the contributor editor disabled.
- [ ] Verify preservation and update Markdown and hosted PostPlan.

The branch starts from current main `ecd952b`. The previous editor/gesture release is already verified in production. All 611 original tracked files were hashed before this rotation. No Supabase writes or data migration are part of these loading fixes; those portfolio tasks remain open.

Baseline desktop/mobile checks reproduce the 432,946-byte homepage script and incompatible floor filter. The first type-checked build/lint/registry checks pass. Browsing uses derived metadata; detailed coordinates are deferred to room/editor chunks, and 197 diagnostic overlay files are excluded only from build output. Existing public originals and masked floor plans remain. New route-failure recovery and existing sharing/editor browser checks are running before release.

Final local validation: ten loading/filter/recovery cases, fourteen sharing cases and sixteen editor/gesture cases pass; lint, type-checked production build and all 98 registry checks pass. Homepage JavaScript is 258,295 bytes (40.3% smaller). Public build files are 94,846,355 bytes (59.0% smaller); all 200 non-diagnostic public files match source bytes. All 611 original tracked files are unchanged before synchronization. No dependency or committed data edits. Hosted checks and production verification are next.

Released through [PR #187](https://github.com/hongyime/smuseats/pull/187), main application commit `401e0c7f598f0190dec1f8653508c71ec4448edb`.

- Production: Vercel deployment `dpl_Gku9AwUANC4YaPEKUGecK931jg1H` is READY. Fourteen browser scenarios pass at smuseats.hong-yi.me and three mobile checks pass at smuseats.vercel.app. All sixteen compiled-file, selected floor-plan and direct-route comparisons match the main CI artifact/source.
- Behavior: browser history follows the current room/names; redirects retain the full selection; rapid typing is immediate; oversized or failed URL writes keep a visible temporary draft and cannot copy an older link. Clipboard failures provide retry feedback. Sidebar controls are labeled and mobile controls do not overlap.
- Validation: lint, the type-checked build, all 98 registry checks and fourteen final browser scenarios pass locally and in hosted CI. All 6,364 seats and floor plans are preserved. Seven transitive minor/patch updates clear the audit; GitHub marked the browserslist alert fixed.
- Scanning: GitHub default CodeQL stays active. `CODEQL_SETUP=default` skips the duplicate advanced workflow before runner allocation; changing scanning modes also requires updating this repository variable. All applicable final application checks pass.
- Remaining: deeper editor/import/pan/zoom review, shared workflow propagation and portfolio storage/capacity work. URL sharing remains outside Supabase; names are visible to anyone with the link. No monthly savings or completed data migration is claimed.


## Portfolio upkeep task list — 2026-09-11

- [x] Reproduce cancelled pointer edits, keyboard coordinate bounds and editor/viewer pan/zoom behavior with synthetic local sessions.
- [x] Repair confirmed interaction defects and retain all existing room/seat data and URL-sharing behavior.
- [x] Verify desktop/mobile editor/export and viewer controls, registry integrity, lint/build and targeted regressions.
- [ ] Pass hosted checks, release to existing production without enabling contributor features, and update both portfolio plan formats.


### Editor and map gesture repair — verified locally

Cancelled or lost pointer capture previously committed contributor edits; keyboard nudges could place seats outside the floor plan; moving both touch points together did not move the public map. Separate cancellation from commit, retain the active pointer/last drag preview, clamp coordinates centrally without adding no-op undo entries, and transform two-finger gestures from their starting midpoint and viewport.

Sixteen contributor/gesture browser cases and fourteen existing sharing cases pass at desktop/mobile widths. Lint, registry checks and the production build pass. All 400 original data/asset files retain their bytes and the committed data is unchanged; four fresh-checkout text files use the LF endings required by .gitattributes, with identical content. All 98 rooms and 6,364 seats remain intact.

The contributor editor remains disabled in production. CI enables it only for an isolated dist-editor fixture and uploads compact result evidence. Hosted checks and production verification follow. Shared styling and wider interaction review remain open.
