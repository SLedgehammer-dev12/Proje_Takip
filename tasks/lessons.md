# Lessons Learned

Bu dosya, kullanıcı düzeltmelerinden ve tekrar eden hatalardan öğrenilen kuralları toplar.
Yeni bir ders eklerken hatayı, tetikleyiciyi ve gelecekte nasıl önleneceğini kısa şekilde yaz.

## Template

- Date:
- Context:
- Mistake:
- Prevention Rule:

## Entries

- Date: 2026-03-26
- Context: Packaged `.exe` validation after preview/document-open refactors
- Mistake: Source-level smoke tests passed, but the packaged Windows build still failed to open documents from the preview button.
- Prevention Rule: When a bug report explicitly mentions `.exe` behavior, verify the platform-specific open path and rebuild/package before considering the fix complete.
