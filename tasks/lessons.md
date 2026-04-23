# Lessons Learned

Bu dosya, kullanıcı düzeltmelerinden ve tekrar eden hatalardan öğrenilen kuralları toplar.
Yeni bir ders eklerken hatayı, tetikleyiciyi ve gelecekte nasıl önleneceğini kısa şekilde yaz.

## Template

- Date:
- Context:
- Mistake:
- Prevention Rule:

## Entries

- Date: 2026-04-16
- Context: Coklu proje yukleme akisinda kategori secimi olan ama veritabani bos veya kategorisiz durumda calisan yeni proje insert'i
- Mistake: UI tarafindaki `Kategorisiz` sentinel degeri `0` olarak tutuldu ve dogrudan foreign key alanina yazildi
- Prevention Rule: UI sentinel degerleri (`0`, bos string, placeholder text) foreign key alanlarina yazilmadan once DB katmaninda mutlaka `NULL` veya gercek kayda normalize edilmelidir.

- Date: 2026-03-26
- Context: Packaged `.exe` validation after preview/document-open refactors
- Mistake: Source-level smoke tests passed, but the packaged Windows build still failed to open documents from the preview button.
- Prevention Rule: When a bug report explicitly mentions `.exe` behavior, verify the platform-specific open path and rebuild/package before considering the fix complete.
