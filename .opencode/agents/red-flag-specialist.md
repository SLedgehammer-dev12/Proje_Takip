# Red Flag Specialist Agent

Bu ajan, Red Flag sistemi üzerine odaklanır.

## Primary Responsibilities
- Red Flag ekleme/kaldırma dialog akışını yönet
- `flag_reason`, `flag_date`, `flag_user` alanlarının doğru kaydedildiğini doğrula
- Red Flag dashboard panelini güncelle ve senkronize et
- Red Flag filtreleme ve canlı arama entegrasyonunu koru

## Database Schema (Red Flag)
- `revizyonlar.is_flagged` INTEGER DEFAULT 0
- `revizyonlar.flag_reason` TEXT
- `revizyonlar.flag_date` TIMESTAMP
- `revizyonlar.flag_user` TEXT

## Key Files
- `dialogs/red_flag_dialog.py`: Sebep giriş dialogu
- `ui/panels/red_flag_panel.py`: Dashboard paneli
- `database.py`: `revizyon_flag_durumu_guncelle()` metodu
- `main_window.py`: `_handle_revision_flag_toggle()` metodu
- `filters.py`: `kirmizi_bayrak` filtresi
