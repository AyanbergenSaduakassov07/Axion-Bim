# Execution queue

`/next` picks the first `todo` row whose deps are all `done`, sets it `doing`, runs it, then sets `done` or `blocked`.
Edit only the Status cell. One prompt per session; `/clear` between.

| ID | Prompt | Deps | Status | Milestone |
|---|---|---|---|---|
| P00 | [De-risk spike: viewer + ifcopenshell + ifctester](P00-spike.md) | — | done | M0 |
| P01 | [Repo skeleton + fixture factory](P01-skeleton-fixtures.md) | P00 | done | M1 |
| P02 | [Extraction → Snapshot → SQLite](P02-extract.md) | P01 | done | M1 |
| P03 | [Rule engine + Finding + `axiom audit`](P03-rules.md) | P02 | done | M1 |
| P04 | [IDS validation via IfcTester](P04-ids.md) | P03 | done | M1 |
| P05 | [Model Health Index](P05-mhi.md) | P03 | done | M1 |
| P06 | [Revision engine + issue regression](P06-revision.md) | P04, P05 | todo | M2 |
| P07 | [Quantity intelligence](P07-quantities.md) | P02 | todo | M2 |
| P08 | [FastAPI + subprocess job runner](P08-api-jobs.md) | P06 | todo | M3 |
| P09 | [Web shell + Quality Center](P09-web-quality.md) | P08 | todo | M3 |
| P10 | [3D explorer + finding→element](P10-viewer.md) | P09 | todo | M3 |
| P11 | [Revision UI + HTML/CSV report](P11-revision-ui-report.md) | P10, P07 | todo | M3 |
| P12 | [Grounded copilot + eval set](P12-copilot.md) | P08 | todo | M4 |
| P13 | [Hardening, benchmarks, README, demo](P13-ship.md) | P11, P12 | todo | M5 |

Parallel-safe after P03: {P04, P05, P07}. After P08: {P09→P10→P11} and {P12}.
