# Proje Takip Skill Guide

Bu dosya, `Proje Takip Sistemi v2.0.1` deposunda çalışan ajan için çalışma standardını tanımlar.
Amaç; daha az bağlam kaybı, daha net planlama, daha güvenli değişiklik ve doğrulanmış teslimattır.

## Required Read Order

Bu repo üzerinde geliştirme yaparken aşağıdaki dosyalar sırayla gözden geçirilmelidir:

1. `skill.md`
2. `agents.md`
3. `session.md`
4. `architecture.md`
5. `test.md`
6. `review.md`
7. `release.md` if the task touches packaging, updater, or delivery
8. `todo.md`
9. `tasks/todo.md`
10. `tasks/lessons.md`

Non-trivial bir görevde doğrudan koda geçmeden önce bu dosyaların ilgili bölümleri okunmalı ve plan buna göre kurulmalıdır.

## Project Context

- Stack: Python 3, PySide6, SQLite, bcrypt
- Entry point: `main.py`
- Main UI flow: `main_window.py`, `dialogs/`, `controllers/`, `ui/`
- Data-critical files: `database.py`, `config.py`, `services/`
- Release and automation helpers: `scripts/`, `docs/RELEASING.md`, `docs/UPDATER.md`
- Local database and generated outputs are sensitive; avoid accidental edits or commits

## Companion Files

- `agents.md`: Aktif roller, sorumluluklar, escalation ve multi-role çalışma düzeni
- `session.md`: Oturum açılışı, bağlam toplama, handoff ve kapanış şablonları
- `architecture.md`: Kod tabanı haritası, kritik modüller, değişmezler ve hotspot alanlar
- `test.md`: Test stratejisi, smoke testler, manuel doğrulama checklistleri
- `review.md`: Kendini denetleme, review kriterleri ve teslim öncesi risk taraması
- `release.md`: Build, paketleme, updater ve dağıtım kuralları
- `todo.md`: Repo seviyesinde kalıcı backlog ve öncelikler
- `tasks/todo.md`: O anki görevin ayrıntılı yürütme planı
- `tasks/lessons.md`: Kullanıcı düzeltmelerinden ve hatalardan çıkarılan kurallar

## Workflow Orchestration

### 1. Plan Mode Default
- Enter plan mode for ANY non-trivial task (3+ steps or architectural decisions)
- If something goes sideways, STOP and re-plan immediately
- Use plan mode for verification steps, not just building
- Write detailed specs upfront to reduce ambiguity
- Reflect the active task in `tasks/todo.md` before implementation starts

### 2. Subagent Strategy
- Use subagents liberally to keep main context window clean
- Offload research, exploration, and parallel analysis to subagents
- For complex problems, throw more compute at it via subagents
- One task per subagent for focused execution

### 3. Self-Improvement Loop
- After ANY correction from the user: update tasks/lessons.md with the pattern
- Write rules for yourself that prevent the same mistake
- Ruthlessly iterate on these lessons until mistake rate drops
- Review lessons at session start for relevant project

### 4. Verification Before Done
- Never mark a task complete without proving it works
- Diff behavior between main and your changes when relevant
- Ask yourself: "Would a staff engineer approve this?"
- Run tests, check logs, demonstrate correctness

### 5. Demand Elegance (Balanced)
- For non-trivial changes: pause and ask "is there a more elegant way?"
- If a fix feels hacky: "Knowing everything I know now, implement the elegant solution"
- Skip this for simple, obvious fixes -- don't over-engineer
- Challenge your own work before presenting it

### 6. Autonomous Bug Fixing
- When given a bug report: just fix it. Don't ask for hand-holding
- Point at logs, errors, failing tests -- then resolve them
- Zero context switching required from the user
- Go fix failing CI tests without being told how

## Task Management

1. Plan First: Write plan to tasks/todo.md with checkable items
2. Verify Plan: Check in before starting implementation
3. Track Progress: Mark items complete as you go
4. Explain Changes: High-level summary at each step
5. Document Results: Add review section to tasks/todo.md
6. Capture Lessons: Update tasks/lessons.md after corrections
7. Keep `todo.md` updated when a new cross-session backlog item or follow-up is discovered

## Core Principles

- Simplicity First: Make every change as simple as possible. Impact minimal code.
- No Laziness: Find root causes. No temporary fixes. Senior developer standards.
- Minimal Impact: Only touch what's necessary. No side effects with new bugs.

## Repository Guardrails

- Read related files before editing; avoid guessing UI or data flow
- Do not rename or relocate user-facing files unless required by the task
- Treat `projeler.db`, Excel outputs, logs, backups, and release artifacts as protected assets
- Avoid broad refactors when a local fix solves the problem cleanly
- Preserve existing release/update flows unless the task is explicitly about deployment
- Prefer existing scripts in `scripts/` over ad hoc release or prep commands
- If a task touches startup, database schema, PDF preview, or release packaging, explicitly review `architecture.md` and `test.md` first

## Verification Checklist

- For Python changes, run the smallest relevant verification first, then broader validation if needed
- If automated tests exist, run `pytest`
- If UI behavior changes, launch the app and validate the affected screen or workflow
- If database logic changes, verify migration safety, queries, and rollback behavior where applicable
- If updater or release logic changes, review `docs/UPDATER.md` or `docs/RELEASING.md` and validate the relevant script path
- Record what was verified and what could not be verified in `tasks/todo.md`

## Definition Of Done

- Plan exists in `tasks/todo.md`
- Session assumptions and findings are captured in `session.md` when the task is long-running or likely to resume later
- Relevant lessons were reviewed before implementation
- Change is implemented with minimal surface area
- Verification was run and documented
- Risks, assumptions, and follow-up items are written down
- User-facing summary is concise and technically accurate
