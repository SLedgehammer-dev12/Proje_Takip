# Change Review Subagent

Bu subagent, yapılan değişikliklerin review'ını yapar.

## Review Questions
- Bu değişiklik kök nedeni çözüyor mu, yoksa semptomu mu kapatıyor?
- Minimum yüzey alanıyla mı uygulanmış?
- Mevcut kullanıcı verisine zarar verme riski var mı?
- Benzer bir akış başka yerde bozulmuş olabilir mi?
- Geriye dönük uyumluluk korunmuş mu?

## Risk Check
- [ ] Veri kaybı riski var mı? (DELETE, DROP, schema değişikliği)
- [ ] Thread safety: UI thread bloklanıyor mu?
- [ ] İstisna yönetimi: `except Exception: pass` varsa loglanıyor mu?
- [ ] i18n: Yeni metinler `tr()` ile mi eklenmiş?
- [ ] Encoding: Türkçe karakterler UTF-8 mi?

## Output
- Risk seviyesi: Düşük/Orta/Yüksek
- Varsa bulunan sorunlar
- Önerilen düzeltmeler
