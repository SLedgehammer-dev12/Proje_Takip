# Session Guide

This file is used for session startup, context management during execution, and handoff notes at the end of a session.
For long-running or interruptible tasks, treat it like a lightweight handoff log.

## Session Start Checklist

- Read `skill.md`
- Read `agents.md`
- Scan the task-relevant modules in `architecture.md`
- Choose the suitable verification steps from `test.md`
- Revisit the risk checklist in `review.md`
- Check `tasks/lessons.md` for similar mistakes or warnings
- Write the active task into `tasks/todo.md`

## Investigation Notes Template

- Date:
- Goal:
- Related files:
- Constraints:
- Risks:
- Assumptions:
- Verification plan:

## Session Execution Rules

- Spend the first 10-15 minutes mapping the code before diving in
- In large files, inspect entry points, classes, and dependencies first
- Do not overwrite the user's local changes
- If something behaves unexpectedly, verify with logs, tracebacks, build output, or `git diff`

## Handoff Template

- Last completed step:
- Current status:
- Files touched:
- Verified:
- Not verified:
- Open risks:
- Recommended next step:

## Current Session Notes

- Date: 2026-03-31
- Goal: Deeply analyze the current `v2.1.5` project state and fix the reported dashboard counters, missing tracking-note buttons, and visible Turkish mojibake in the touched revision flows.
- Related files: `main_window.py`, `ui/panels/revision_panel.py`, `ui/main_window_ui.py`, `tasks/todo.md`, `todo.md`
- Constraints: Keep the edit surface focused; avoid broad text rewrites across all of `main_window.py` in one pass because the file still mixes legacy behavior and encoding damage.
- Risks: The project still contains many mojibake strings outside the touched paths, so a full-file cleanup would be higher risk than the targeted fixes requested in this turn.
- Assumptions: The active revision UI is produced by `AnaPencere._setup_revizyonlar_panel()` plus `ui/panels/revision_panel.py`, while the dashboard labels come from `ui/main_window_ui.py`.
- Verification plan: Run `py_compile`, then an offscreen Qt verification for revision-panel button presence and dashboard statistic updates.
- Last completed step: Restored the revision tracking quick-action buttons, reconnected them inside `AnaPencere`, and fixed the dashboard label update path to support the live UTF-8 labels.
- Current status: The requested user-visible fixes are implemented and targeted verification passed.
- Verified: `python -m py_compile main_window.py ui/panels/revision_panel.py`; offscreen verification for `RevisionPanel` tracking buttons; offscreen verification that `guncelle_gosterge_panelini()` updates `Toplam Görüntülenen Proje` and `Beklemede (Onaysız)` correctly.
- Open risks: `main_window.py` still has broader mojibake debt in update dialogs, confirmations, and several older messages that were not globally rewritten in this pass.
- Recommended next step: Continue with a staged mojibake cleanup backlog item for high-visibility dialogs in `main_window.py`, validating each slice with the same targeted offscreen checks.
