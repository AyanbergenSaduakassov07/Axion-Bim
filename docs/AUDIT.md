# Axiom BIM — civil engineer audit and roadmap

2026-11-11. Written from the seat of a lead civil engineer / construction project manager (CPM) on the client side:
the person who receives design models from contractors and has to accept or reject each delivery.
Sources: the code at this commit, the browser tests on the buildingSMART Clinic, Schependomlaan and Chesapeake
samples (release-check rows 14, 17), and the CPM feedback round of 2026-11-10.
**Not validated by a practising engineer or a real project yet.** That is gap G0 and the first roadmap exit criterion.

## 1. Verdict

Axiom already answers the question a CPM asks at every delivery: *"is this model better or worse than the last one,
what exactly is wrong, and who fixes it?"* Findings are traceable (GlobalId, rule version, expected, actual),
revisions are compared honestly (a "resolved" finding caused by a deleted element is called out), and nothing is
reported as passed when it was not checked.

It is not yet a tool I could put in a contract. Three things stop it: the check library is thin (8 built-in rules
plus whatever IDS the client brings), responsibility is anonymous (no users, no history), and the result of an
audit is a score, not an accept/reject decision I can sign.

## 2. What holds up

| Strength | Why it matters on a project |
|---|---|
| Every finding carries GlobalId, rule id + version, expected, actual, evidence | A designer cannot argue with "column C2, no material, rule MAT-001 v1" |
| Statuses separate `fail` from `not_evaluated`; MHI reports the weight it covers | The score cannot look complete when IDS or classification was never checked |
| Revision events: new / resolved / persistent / recurring, with "resolved by removal" | Recurring issues are the ones that show a contractor is not fixing root causes |
| IDS (buildingSMART) as the requirement format, kept per project | The client's EIR becomes a machine-checked file, not a PDF nobody reads |
| Issue triage: state, assignee, due date, note; now exported in BCF and CSV | Findings turn into tracked work in the designers' own tools |
| Quantities name their method (`qto` vs `geometry`) and flag x1000 unit errors | Catches the classic mm³/m³ export mistake before it reaches an estimate |
| No structural-safety language anywhere | Keeps the tool out of liability it cannot carry |

## 3. Gaps, ranked by what blocks real use

| # | Gap | What I see as the engineer | Size |
|---|---|---|---|
| G0 | No real-project validation | Everything was tested on public samples by the developer. One pilot project is worth more than any feature below | — |
| G1 | No acceptance gate | I need "delivery r3: **rejected**, 2 blocking requirements unmet" against a threshold agreed in the BEP, per project stage, as a dated PDF with the file hash and ruleset version. Today I get a number (MHI) and a "Blocked" badge | M |
| G2 | Anonymous responsibility (F1) | "Who closed this issue and when?" has no answer. Assignee is free text. No change history. In a dispute this is the first thing asked | L |
| G3 | Thin requirement library | 8 rules: presence of name, material, classification, quantities, geometry, containment, unique GlobalId, storeys. A real EIR also asks: required properties per class **per stage**, naming conventions, valid classification codes (not just "has one"), type vs occurrence data, georeferencing and units, storey/grid consistency. Most of this is expressible as IDS, so the answer is requirement packs, not more Python | M |
| G4 | One-way loop to designers (F2) | BCF goes out, nothing comes back. The designer's reply ("fixed", "by design") in Revit/Solibri never reaches the tracker. The export is XSD-valid but has still not been opened in BIMcollab or Solibri | M |
| G5 | One model at a time | A project is ARCH + STR + MEP. There is no project-level gate and no cross-model check (same storeys, same origin, same coordinate system across disciplines). Misaligned origins are among the most common coordination defects and are cheap to detect | M |
| G6 | Quantities stop before the estimate | Totals by class, storey, material and classification with the revision delta exist, and export as CSV for Excel (D-37). The delta can be taken against any earlier revision, each labelled with its delivery decision (D-38) | S |
| G7 | No geometric sanity beyond presence | No duplicate/overlapping elements (two walls in the same place double every quantity), no elements far from the model, no elements outside their storey's height range. Full clash detection should stay out (see §5) | M |
| G8 | Local market (F4, F5) | Rule texts and reports are EN/RU only; Kazakh UI falls back to Russian. No requirement packs for Kazakhstan practice. The pack content must come from the actual normative documents and a local BIM manager — do not write it from memory | L |
| G9 | Re-exports break identity | If the authoring tool regenerates GlobalIds, every element reads as removed + added. The comparison is flagged "identity unstable", which is honest, but the history is lost | L |
| G10 | Nobody is told (F6) | The dashboard shows overdue issues. No weekly digest reaches the assignee | S |
| G11 | Single user, SQLite, no auth (F11) | Fine for one engineer on one machine. Not deployable for a client team | L |
| G12 | Copilot trust not demonstrated | Eval at 4/6 on 6 of 25 cases; the ≥90% target was never shown. Until it is, the copilot is a demo feature, and it should say so | S |
| G13 | MHI weights are defaults | 20/20/15/15/15/5/10 was chosen by the developer. On a project the weights belong in the BEP and must be visible in the report next to the score | S |

## 4. The product as it should be

One sentence: **the delivery gate between the people who model and the people who pay for the model.**

The full loop, in the order it happens on a project:

1. **Requirements once.** At project start the BIM manager loads the EIR as IDS, one pack per stage (concept,
   design, working documentation, as-built). Axiom ships starter packs per discipline; the client edits them.
2. **Self-check before submission.** The designer runs the same checks locally (`axiom audit` exists today; a
   button in the authoring tool comes later). Fewer rejected deliveries, same ruleset on both sides.
3. **Submission.** Each discipline uploads its model to the project. The file is hashed, stored, audited in a job.
4. **Gate.** The project shows one decision per delivery: accepted / accepted with comments / rejected, derived
   from blocking requirements and a threshold, never from the score alone. The decision is a signed, dated
   document that cites the file hash, ruleset version and IDS hash.
5. **Issues to the designers' tools.** Findings grouped per rule become BCF topics with assignee and due date.
   Replies and status changes come back by BCF import. Every change is recorded with user and time.
6. **Resubmission.** The next revision is compared automatically. Recurring issues and "resolved by deletion"
   are surfaced first. The trend per discipline is on the dashboard; overdue items reach people by digest.
7. **Quantities to the estimator.** Per storey / material / classification, with the delta against the last
   accepted revision, in Excel, each number labelled `qto` or `geometry`.
8. **Handover.** The as-built stage pack checks the data the operator needs (asset identifiers, type data,
   classification), and the final acceptance report closes the contract's information deliverable.

The copilot's place in this: explaining a report to someone who does not read IFC ("why was r3 rejected?"),
always with citations, never computing a result.

## 5. What it should never become

- A clash detection engine. Solibri and Navisworks own that; import their BCF instead.
- A structural or code-compliance checker. It checks that information exists and is consistent, not that a
  building is adequate. Missing data stays an information deficiency.
- An authoring tool or a scheduling/costing engine. It hands clean quantities to those tools.

## 6. Roadmap

Each phase has an exit criterion that can be observed, not a feature count.

### Done on 2026-11-11

| Item | Result |
|---|---|
| F2 (export half) | BCF topics carry status, assignee, due date and the note as a comment; CSV gains `state, assignee, due_date, note` |
| F3 (part) | Rename and remove an IDS library entry; the Quality Center names the requirements file the audit used |
| F7 | "Overdue" is judged against the viewer's timezone (`?tz=`), not the server's date |
| F8 | Revisions list returns MHI score and blocked flag; the timeline no longer fires one request per revision |
| F9 | Explorer tree rows skip layout/paint off-screen (`content-visibility`) |
| G1 (core) | Acceptance gate (D-36): accepted / accepted with comments / rejected / not decided per audit, from a per-project policy and reviewer waivers; shown on the Quality Center and at the top of the report. Still open: per-stage policy, frozen signed certificate |
| G6 | Quantities table exports as CSV (Excel) with unit, method, previous total and change (D-37) |
| F3 | IDS version diff: specifications added / removed / changed between two library entries (D-37) |
| G1, loop step 2 | Delivery decision on every timeline row and in `axiom audit`; `--gate` exits 1 unless the delivery would be accepted, for a designer's pre-submission self-check (D-38) |
| G6 | Quantities: "Compare with" any earlier revision, labelled with its decision, so the delta can be read against the last accepted delivery (D-38) |
| G5 (core) | Project coordination (D-39): one decision over the latest delivery of every model (worst wins, a model without a delivery leaves it undecided) and cross-model checks of length unit, georeferencing and storey levels |
| G10 (core) | `axiom digest --project NAME` prints open issues per assignee, overdue first, as Markdown for email or a chat; run it from cron (D-40). Sending is left to the mail/Telegram tool |
| G2 (part) | Issue change history (D-41): every field an update changes is recorded with old value, new value, time and the author name typed by the user; shown under "History" in the issue editor. Real users/login still open |
| Bug | An IDS uploaded with a revision did not appear in the library until the cache expired |

### R1 — usable by one team on one real project

| # | Work | Closes |
|---|---|---|
| 1 | Find a pilot: one real project, three deliveries, one engineer who is not the developer | G0 |
| 2 | Acceptance gate: per-project threshold + blocking rules, decision per delivery, PDF certificate | G1, G13 |
| 3 | Users + login, assignee from the user list, issue change history | G2 (F1) |
| 4 | Open the BCF in BIMcollab Zoom and Solibri, fix what they reject, then BCF import | G4 (F2) |
| 5 | Starter IDS packs per discipline and stage; IDS version diff (EIR v1 → v2) | G3 (F3) |
| 6 | Finish the copilot eval (19 cases left); publish the score in the UI or hide the feature | G12 |

Exit: the pilot engineer accepts or rejects three deliveries using only Axiom's report, and the designers
receive and answer the issues in their own tool.

### R2 — the whole project, not one model

| # | Work | Closes |
|---|---|---|
| 7 | Project-level gate over all discipline models; cross-model origin / units / storey consistency | G5 |
| 8 | Quantities by storey, material, classification with revision delta; Excel export | G6 |
| 9 | Duplicate/overlap rule, far-from-model rule, storey height-range rule (geometry job, opt-in) | G7 |
| 10 | Overdue digest per assignee (email or Telegram) | G10 (F6) |
| 11 | Kazakh rule texts and reports, reviewed by a native speaker | G8 (F4) |

Exit: a three-discipline project gets one accept/reject per delivery and an estimator uses the quantity delta.

### R3 — a product others can run

| # | Work | Closes |
|---|---|---|
| 12 | Kazakhstan requirement packs, written with a local BIM manager from the source documents | G8 (F5) |
| 13 | Postgres, organisations, roles, hosted deployment | G11 (F11) |
| 14 | Self-check from the authoring tool (Revit add-in or pyRevit button calling the CLI) | loop step 2 |
| 15 | Heuristic element matching when GlobalIds are regenerated, always marked `uncertain` | G9 |
| 16 | As-built / handover pack | loop step 8 |

Exit: a second company installs it without the developer in the room.

## 7. Open small items

- F10: the one-off "useEffect returned a Promise" warning was not reproduced; no effect in `apps/web/src` returns a Promise today.
- F3 remainder: archive (remove covers it for now); the IDS diff names the changed part, not the facet inside it.
- G7: a snapshot-only duplicate rule gave false positives at wall/beam corners (D-37); build it on the geometry pass.
- G1 remainder: per-stage gate policy, frozen signed certificate.
- G5 remainder: origin offset between models needs the geometry pass (shared reference points); checks compare the latest revision only, not a chosen delivery set.
- "Fragments: Problematic geometry" console noise from the converter worker is still unfiltered.
- BCF `extensions.xml` is empty; a strict BCF tool may want the five topic statuses declared there. Check in R1 #4.
