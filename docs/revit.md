# Working with Revit

Axiom does not write into Revit files. The hand-off is the BCF issue format: Axiom exports the issues, a
Revit BCF add-in opens them, and each issue selects its element in Revit. The designer fixes the model,
exports IFC again, and Axiom checks the new revision.

## The loop

1. **Revit → IFC.** File › Export › IFC, IFC4 Reference View or IFC2x3 Coordination View 2.0. Turn on
   *Store the IFC GUID in an element parameter after export*, so GlobalIds stay the same between exports.
   Revisions are matched by GlobalId; new ids show up as removed + added elements.
2. **Axiom.** Upload the IFC as the next revision of the model. It runs the audit and the comparison.
3. **Axiom → BCF.** *Export report* › **BCF 2.1 for Revit add-ins and Autodesk Construction Cloud**,
   or from the CLI:
   ```bash
   uv run axiom report <audit-id> --format bcf21 --out issues.bcf
   ```
   Use `--format bcf` (BCF 3.0) for tools that read 3.0: BIMcollab, Solibri, newer BCF Managers.
4. **BCF → Revit.** Open `issues.bcf` in a Revit BCF add-in, for example the free BIMcollab Zoom / BCF
   Manager for Revit, BCFier, or Autodesk Construction Cloud *Issues › Import BCF*, then the ACC Issues
   add-in inside Revit. Clicking an issue selects the element and moves the camera to it.
5. **Fix and repeat.** Fix the element in Revit, export IFC again (step 1) and upload it. Each topic keeps its
   GUID across revisions. A re-export of the BCF updates the same topics in the add-in instead of adding
   duplicates, and fixed findings show as `resolved` in Axiom.

## What each issue carries

| BCF field | From Axiom |
|---|---|
| Topic GUID | derived from the finding identity: stable across revisions |
| Title, description | rule id, element, message, expected / actual values, rule version, audit id |
| Status, assigned to, due date | the issue triage in Axiom (Open, In Progress, Disputed, Accepted, Closed) |
| Comments | the issue history (who changed what, when) and the current note |
| Labels, priority | rule id and dimension, severity |
| Viewpoint component | `IfcGuid` = GlobalId, `AuthoringToolId` = Revit ElementId (from `IfcElement.Tag`) |
| Camera | looks at the element's placement from about 11 m away |

Revit writes its ElementId to `IfcElement.Tag`. Axiom stores it with every element and puts it in the BCF
as `AuthoringToolId`, so an add-in can find the element even when the IFC GUID parameter was not stored.

## Checked

- Both exports were validated against the buildingSMART XSDs (BCF-XML `release_2_1` and `release_3_0`) on
  `Ifc4_Revit_ARC.ifc`. All 202 topics and 202 viewpoints validate, and every viewpoint carries the Revit
  ElementId (for example `997032` for *White Porcelain Plate:Fine China - Plate:997032*).
- **Not checked yet:** importing into a running Revit with an add-in. Do that once before relying on it on a
  project.
- Status changes made in the Revit add-in do not flow back into Axiom; there is no BCF import. Triage stays
  in Axiom, and the next upload shows what was fixed.
