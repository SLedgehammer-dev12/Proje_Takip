# Project Backlog

This file tracks project-level open work and technical debt across sessions.
Use `tasks/todo.md` for the active task execution plan.

## Current Priorities

- [ ] Write a safe modularization plan for the large business rules still living in `main_window.py`
- [ ] Clean the remaining mojibake/Turkish text corruption in `main_window.py`, starting with update dialogs and critical warning messages
- [ ] Analyze build-size-heavy dependencies and define a safe reduction strategy
- [ ] Ensure the `DejaVuSans.ttf` asset stays valid and covered by release verification
- [ ] Define at least a basic smoke-test set for real automated coverage
- [ ] Clarify the code-signing approach for release artifacts

## Technical Debt

- [ ] Write a modularization roadmap for `database.py` and `main_window.py`
- [x] Reduce duplicate preview/document-open methods in `main_window.py` to one canonical path
- [x] Move temp-file and OS document-open details behind `services/file_service.py`
- [x] Move document lookup and payload-building details out of `main_window.py`
- [x] Move preview-state synchronization behind a smaller helper layer
- [x] Move preview cache and render-preparation logic behind a dedicated helper/service
- [ ] Re-evaluate the next low-risk extraction target inside `main_window.py`
- [x] Apply the first safe lazy-import cleanup in export/reporting (`services/report_service.py` / `pandas`)
- [x] Replace the empty `DejaVuSans.ttf` asset with a real font file
- [x] Document the repo/update contract in `update.md`
- [x] Publish the `v2.0.2` source, tag, and release assets
- [ ] Identify the remaining lazy-import opportunities in export/reporting flows
- [ ] Manually validate the packaged `.exe` `Dokümanı Görüntüle` flow with a real user click path
- [ ] Strengthen update and release verification with a tighter checklist
- [ ] Decide which legacy `Archive/` contents should be retained

## Notes

- Items here are meant to survive across sessions
- When a backlog item becomes active implementation work, move the detailed execution steps into `tasks/todo.md`
