# Task Plan

## Active Task

- [x] Define the goal: continue stabilizing the project using the markdown workflow files as the active operating system
- [x] Re-read the relevant `.md` guidance before coding
- [x] Choose a low-risk stabilization task that does not expand the change surface unnecessarily

## Progress

- [x] Re-read `skill.md`, `agents.md`, `session.md`, `architecture.md`, `test.md`, `review.md`, `todo.md`, and `tasks/todo.md`
- [x] Record the current session and follow-up priorities
- [x] Reduce one legacy duplicate document-open implementation to the shared helper path
- [x] Re-run syntax and smoke verification
- [x] Summarize the next safest stabilization step
- [x] Remove the duplicate final document-open method block so only one canonical implementation remains
- [x] Move temp-file document opening behind `services/file_service.py` without changing user-visible behavior
- [x] Re-run targeted verification after the extraction
- [x] Move revision/letter document lookup and payload-building behind a dedicated service
- [x] Re-run targeted verification after the document service extraction
- [x] Move preview-state synchronization behind a UI-focused helper
- [x] Re-run targeted verification after the preview-state extraction
- [x] Move preview cache and PDF validation preparation behind a dedicated helper/service
- [x] Re-run targeted verification after the preview render preparation extraction
- [x] Move heavy `report_service.py` dependencies behind lazy imports where safe
- [x] Re-run targeted verification after the report-service dependency cleanup
- [x] Replace the empty `DejaVuSans.ttf` asset with a valid font file
- [x] Re-run targeted verification after the report font asset fix
- [x] Strengthen Windows packaged document-open flow with an `os.startfile`-first path
- [x] Bump the application to `v2.0.2` and prepare release notes/metadata
- [x] Build the `v2.0.2` Windows `.exe`, zip, and checksum artifacts
- [x] Add repo-level update contract documentation (`update.md`)
- [x] Push the `v2.0.2` source changes, tag, and GitHub release assets

## Verification

- [x] `session.md` reflects the current work
- [x] `todo.md` captures the new cross-session follow-up
- [x] `main_window.py` compiles successfully after the cleanup
- [x] Application smoke test still passes after the cleanup
- [x] `main_window.py` now exposes only one canonical `on_letter_clicked`, one preview wrapper, and one revision open method
- [x] `FileService` owns temp-file document opening and `main_window.py` delegates to it
- [x] Application still compiles and launches after the service extraction
- [x] `DocumentService` owns revision/letter payload building and DB-backed document opening
- [x] Application still compiles and launches after the document service extraction
- [x] `PreviewStateHelper` owns preview panel/legacy widget synchronization
- [x] Application still compiles and launches after the preview-state extraction
- [x] `PreviewRenderService` owns revision preview cache, PDF validation, and cache invalidation
- [x] Application still compiles and launches after the preview render preparation extraction
- [x] `ReportService` lazy-loads `pandas` instead of importing it at module load time
- [x] Application still compiles and launches after the report-service dependency cleanup
- [x] `DejaVuSans.ttf` is now a valid font asset and `rapor.py` resolves `DejaVu`
- [x] Application still compiles and launches after the report font asset fix
- [x] `FileService._open_file_with_system_handler()` returns success on the Windows `os.startfile` path in targeted verification
- [x] `dist\\v2.0.2\\ProjeTakip\\ProjeTakip.exe` launches in a short smoke run
- [x] `release\\v2.0.2\\ProjeTakip-v2.0.2-windows-x64.zip` and `SHA256SUMS` were produced
- [x] `main` branch and `v2.0.2` tag were pushed to `origin`
- [x] GitHub Release `v2.0.2` contains `ProjeTakip-v2.0.2-windows-x64.zip` and `SHA256SUMS`

## Review

- Summary: Continued under the markdown workflow, hardened the packaged Windows document-open path, bumped the app to `v2.0.2`, and produced new release artifacts.
- Files touched: session.md, tasks/todo.md, tasks/lessons.md, config.py, services/file_service.py, services/report_service.py, scripts/build_release.ps1, scripts/create_release_zip.py, docs/releases/v2.0.2.md, CHANGELOG.md, guncelleme_notlari.txt, DejaVuSans.ttf, update.md
- Risks: The final packaged button-click behavior still needs manual confirmation inside the built `.exe`; this turn verified the opening primitive, push/release pipeline, and release artifacts, not a full GUI click path.
- Follow-ups: Manually validate `Dokümanı Görüntüle` inside the `v2.0.2` `.exe` downloaded from GitHub Release and inspect logs if any packaged-only issue remains.
