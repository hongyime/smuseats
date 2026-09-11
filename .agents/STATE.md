# SMU Seats maintenance

Task: repair room navigation and sharing without changing floor plans, seats or adding a data service.

- Baseline: main `680b8b04f9d803ffb6295da01e096a60e6b6acfe`; original checkout clean. Vercel production is READY at the preceding application-equivalent workflow commit.
- Reproduced: Back/Forward leaves stale names or returns to the wrong room; mismatched-room redirection drops the payload; oversized selections share the old URL on desktop/mobile; denied clipboard writes produce an unhandled error. Normal Unicode share/reload passes on both layouts.
- Prepared: router-backed URL state, scoped temporary drafts, guarded sharing, preserved redirect query/hash, clipboard feedback and labeled sidebar controls. Build now checks types before bundling.
- Validation: lint, all 98 registry checks and the type-checked build pass. Ten initial browser cases pass. The expanded suite passed twelve of fourteen and exposed a fast-typing regression in the proposed router update; immediate input state fixes it and both focused desktop/mobile cases now pass. Full final suite and hosted validation follow.
- Dependencies: seven transitive minor/patch updates resolve all three reported advisories; npm audit now reports zero. No major versions changed.
- Next: run the final fourteen-case suite, publish a PR, verify CI, merge and check the production deployment and original checkout.
- Preserve all registry and public-file bytes. Existing URL state is outside Supabase; monthly savings are not established by this repair.
