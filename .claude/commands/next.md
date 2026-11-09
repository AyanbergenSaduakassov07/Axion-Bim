---
description: Run the next ready prompt from the Axiom queue
---
1. Read `prompts/INDEX.md`. Pick the first row with Status `todo` whose Deps are all `done` (or the ID in $ARGUMENTS if given). None → say "nothing ready" + what blocks it, stop.
2. Edit that row's Status to `doing`. Read the prompt file and `CLAUDE.md`. Load the skills in its front matter via the Skill tool (skip missing ones).
3. Execute fully. New decisions → append to `docs/DECISIONS.md`.
4. Check DONE WHEN honestly (run the tests). Met → Status `done`. Not met → `blocked` + one-line reason in the row.
5. Reply: what was produced (paths), test result, decisions needing the user, next ready ID(s). Suggest `/clear`.
