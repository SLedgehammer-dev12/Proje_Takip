#!/bin/bash

# GitHub Push Script for Proje Takip Sistemi v1.3
# Bu script kodu GitHub'a push etmek için kullanılır

echo "🚀 Proje Takip Sistemi v1.3 - GitHub Push"
echo "=========================================="
echo ""

# Git durumunu kontrol et
echo "📊 Git durumu kontrol ediliyor..."
git status

echo ""
echo "⚠️  DİKKAT: Aşağıdaki dosyalar .gitignore sayesinde PUSH EDİLMEYECEK:"
echo "  - *.db (veritabanı dosyaları)"
echo "  - *.xlsx (Excel dosyaları)"
echo "  - veritabani_yedekleri/ (yedek dosyaları)"
echo "  - *.pdf (PDF raporları)"
echo ""

read -p "Devam etmek istiyor musunuz? (E/H): " choice
if [ "$choice" != "E" ] && [ "$choice" != "e" ]; then
    echo "❌ İşlem iptal edildi."
    exit 1
fi

echo ""
echo "📝 Dosyalar staging area'ya ekleniyor..."
git add .

echo ""
echo "💾 Commit oluşturuluyor..."
git commit -m "Release v1.3: User authentication, bug fixes, and security improvements

- Kullanıcı kimlik doğrulama sistemi (bcrypt)
- Yetki tabanlı erişim kontrolü (admin/guest)
- Database yolu ve revizyon seçimi hataları düzeltildi
- Arama çubuğu filtreleme düzeltmesi
- Güvenlik iyileştirmeleri ve permission checks"

echo ""
echo "🌐 GitHub'a push ediliyor..."
git push origin main

echo ""
echo "✅ Push işlemi tamamlandı!"
echo ""
echo "📋 Sonraki adımlar:"
echo "  1. GitHub'da release oluşturun: https://github.com/YOUR-USERNAME/YOUR-REPO/releases/new"
echo "  2. Tag: v1.3"
echo "  3. CHANGELOG.md'den release notlarını kopyalayın"
echo ""
