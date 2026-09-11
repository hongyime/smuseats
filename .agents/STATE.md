# SMU Seats maintenance

Task: repair room navigation and sharing without changing floor plans, seats or adding a data service.

- Baseline: main `680b8b04f9d803ffb6295da01e096a60e6b6acfe`; original checkout clean. Vercel production is READY at the preceding application-equivalent workflow commit.
- Reproduced: Back/Forward leaves stale names or returns to the wrong room; mismatched-room redirection drops the payload; oversized selections share the old URL on desktop/mobile; denied clipboard writes produce an unhandled error. Normal Unicode share/reload passes on both layouts.
- Prepared: router-backed URL state, scoped temporary drafts, guarded sharing, preserved redirect query/hash, clipboard feedback and labeled sidebar controls. Build now checks types before bundling.
- Validation: lint, all 98 registry checks, the type-checked build and all fourteen final desktop/mobile browser scenarios pass. This includes rapid typing, browser history, real room-picker navigation, complete links, clipboard refusal and failed URL writes.
- Dependencies: seven transitive minor/patch updates resolve all three reported advisories; npm audit now reports zero. No major versions changed.
- PR: https://github.com/hongyime/smuseats/pull/187. Hosted build/browser tests and Vercel preview pass. GitHub default CodeQL passes, but the duplicate advanced workflow cannot upload while default setup is enabled; its detection step now checks ownership before creating a duplicate analysis matrix.
- Next: verify CI, merge, check production and synchronize the original checkout while preserving its data.
- Preserve all registry and public-file bytes. Existing URL state is outside Supabase; monthly savings are not established by this repair.
