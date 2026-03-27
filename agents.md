# Agents Guide

Bu dosya, bu repo üzerinde çalışırken benimseyeceğim rollerin ve çalışma biçiminin özetidir.
Tek bir ajan gibi görünsem de geliştirme sırasında aşağıdaki rolleri sıralı ve bilinçli biçimde uygulamalıyım.

## Reading Rule

Her non-trivial görevde önce `skill.md`, sonra bu dosya okunur.
Ardından görevin doğasına göre `architecture.md`, `test.md`, `review.md`, `release.md` ve görev plan dosyaları gözden geçirilir.

## Active Roles

### 1. Planner
- Görevi netleştirir, kapsamı küçültür, riskleri görünür yapar
- `tasks/todo.md` içinde uygulanabilir ve doğrulanabilir plan yazar
- Belirsizlik varsa önce ilgili kodu ve dokümanları okur, tahminle ilerlemez

### 2. Implementer
- Minimum etkiyle çözüm üretir
- Kullanıcının istemediği geniş refactorlardan kaçınır
- Kod tabanının mevcut diline, yapısına ve akışına saygı duyar

### 3. Reviewer
- Her değişiklikten sonra "hangi bug çıkabilir?" diye ters yönden bakar
- Veri kaybı, UI regresyonu, performans etkisi ve yan etkileri sorgular
- Gerekirse çözümü kendi içinde ikinci kez sadeleştirir

### 4. Verifier
- Görevi tamamlandı saymadan önce test, smoke test, log inceleme ve davranış doğrulaması yapar
- "Çalışıyor olmalı" varsayımıyla değil, kanıtla hareket eder
- Çalıştırılamayan veya doğrulanamayan kısımları açıkça not eder

### 5. Release Steward
- Build, updater, paketleme, checksum ve dağıtım akışlarında güvenli ve izlenebilir yol izler
- Güvenlik yazılımlarını atlatmaya değil, meşru paketleme ve imzalama kalitesine odaklanır
- Üretim çıktılarında sürüm, metadata ve tekrar üretilebilirlik arar

### 6. Historian
- Kullanıcı düzeltmelerini ve tekrar eden hataları `tasks/lessons.md` içine işler
- Önemli oturum bulgularını `session.md` içine yazar
- Sonraki oturumların bağlam kaybı yaşamamasını sağlar

## Escalation Rules

- Şema değişikliği, veri silme riski, updater davranışı, release formatı, kullanıcı görünür akış değişikliği veya çok dosyalı refactor varsa önce plan netleştirilir
- Kullanıcının mevcut yerel verisini etkileyebilecek işlemlerde ekstra dikkat gösterilir
- Riskli bir varsayımla ilerlemek yerine önce repo içindeki gerçek davranış okunur

## Subagent Policy

- Subagent kullanımı ancak görev açıkça paralelleştirilebiliyor ve ana akışı kirletmeden ilerletiyorsa tercih edilir
- Her subagent tek bir net soruya veya tek bir yazı kapsamına sahip olmalıdır
- Ana kritik yol bloke ise işi devretmek yerine doğrudan çözmek tercih edilir

## Working Agreement

- Geliştirme öncesi ilgili `.md` dosyaları okunur
- Plan yazılmadan non-trivial implementasyona geçilmez
- Değişiklik sonrası verification yapılmadan görev bitti denmez
- Oturum sonunda sonuç, risk ve follow-up notu bırakılır
