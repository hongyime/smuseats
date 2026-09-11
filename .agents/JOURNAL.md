# Decisions

- 2026-09-11: Begin a bounded room-sharing repair using synthetic fixtures; preserve the existing floor-plan registry and URL data format. Separate data migration and wider UI work remain in the portfolio queue.
- 2026-09-11: Browser fixtures confirm stale history state, lost redirect payloads and incomplete shared links. Use the router location as durable link state, retain failed edits only as a clearly marked local draft, and never copy a known-incomplete selection.
- 2026-09-11: BrowserRouter defers location updates, so name inputs also need immediate local state while the URL catches up. Rapid typing exposed this in the proposed fix; both focused regressions now pass. Seven transitive minor/patch updates clear the existing dependency audit without changing the room registry.
