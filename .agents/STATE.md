# SMU Seats maintenance

Released through [PR #187](https://github.com/hongyime/smuseats/pull/187), main application commit `401e0c7f598f0190dec1f8653508c71ec4448edb`.

- Production: Vercel deployment `dpl_Gku9AwUANC4YaPEKUGecK931jg1H` is READY. Fourteen browser scenarios pass at smuseats.hong-yi.me and three mobile checks pass at smuseats.vercel.app. All sixteen compiled-file, selected floor-plan and direct-route comparisons match the main CI artifact/source.
- Behavior: browser history follows the current room/names; redirects retain the full selection; rapid typing is immediate; oversized or failed URL writes keep a visible temporary draft and cannot copy an older link. Clipboard failures provide retry feedback. Sidebar controls are labeled and mobile controls do not overlap.
- Validation: lint, the type-checked build, all 98 registry checks and fourteen final browser scenarios pass locally and in hosted CI. All 6,364 seats and floor plans are preserved. Seven transitive minor/patch updates clear the audit; GitHub marked the browserslist alert fixed.
- Scanning: GitHub default CodeQL stays active. `CODEQL_SETUP=default` skips the duplicate advanced workflow before runner allocation; changing scanning modes also requires updating this repository variable. All applicable final application checks pass.
- Remaining: deeper editor/import/pan/zoom review, shared workflow propagation and portfolio storage/capacity work. URL sharing remains outside Supabase; names are visible to anyone with the link. No monthly savings or completed data migration is claimed.
