# Review Guide

Bu dosya, değişiklik teslim edilmeden önce yapılacak iç review standardını tanımlar.

## Review Questions

- Bu değişiklik gerçekten kök nedeni çözüyor mu?
- Çözüm minimum yüzey alanıyla mı uygulandı?
- Mevcut kullanıcı verisine zarar verme riski var mı?
- Benzer bir akış başka yerde bozulmuş olabilir mi?
- Test veya smoke test kanıtı var mı?
- Bir staff engineer bu değişikliği yeterince temiz bulur mu?

## Risk Checklist

### Data Risk
- Şema, backup, restore, export veya dosya yazma davranışı etkilendi mi?
- Yanlış path, overwrite veya silme ihtimali var mı?

### UI Risk
- Sinyal-slot zinciri bozuldu mu?
- Uzun görevlerde thread veya UI freeze riski oluştu mu?
- Türkçe karakter, tarih formatı veya seçim koruma gibi yerel davranışlar bozuldu mu?

### Logic Risk
- `models.py` ile SQL sırası hâlâ uyumlu mu?
- Optional alanlar ve boş veri güvenli işleniyor mu?
- Hata durumunda rollback veya güvenli fallback var mı?

### Delivery Risk
- Build scripti çalışıyor mu?
- Resource dosyaları gerçekten mevcut mu?
- Release veya updater akışı dokümantasyonla tutarlı mı?

## Review Output Template

- What changed:
- Why it changed:
- Verified:
- Residual risk:
- Follow-up:

## Red Flags

- Sadece semptomu kapatan geçici çözüm
- Geniş refactor ama sınırlı doğrulama
- Build alınmadan release değişikliği yapma
- Log veya traceback incelemeden hata düzeltme
- `main_window.py` veya `database.py` içinde etkisi ölçülmemiş geniş düzenleme
