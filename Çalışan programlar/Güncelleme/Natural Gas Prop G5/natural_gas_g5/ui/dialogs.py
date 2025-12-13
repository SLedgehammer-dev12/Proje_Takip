"""
Dialog windows and user prompts.

Provides reusable dialog functions for user interaction.
"""

from tkinter import messagebox
from typing import List, Optional


def show_heos_compatibility_warning(
    incompatible_gases: List[str],
    heos_supported_gases: List[str]
) -> bool:
    """
    Show HEOS compatibility warning and ask user if they want to switch to SRK.
    
    Args:
        incompatible_gases: List of incompatible gas names
        heos_supported_gases: List of HEOS-compatible gases
        
    Returns:
        True if user wants to switch to SRK, False otherwise
    """
    gases_str = ", ".join(incompatible_gases)
    
    message = (
        f"HEOS Backend Uyumluluk Uyarısı\n\n"
        f"Seçilen karışım HEOS backend'i için tam karışım desteğine sahip değil.\n"
        f"Uyumsuz gazlar: {gases_str}\n\n"
        f"KRİTİK UYARI: HEOS ile devam etmek hatalı sonuçlara yol açabilir.\n\n"
        f"Doğruluk için SRK yöntemine otomatik geçiş yapılsın mı?\n"
        f"(ÖNERİLİR)"
    )
    
    result = messagebox.askyesno(
        "HEOS Uyumluluk Uyarısı",
        message,
        icon='warning'
    )
    
    if result:
        messagebox.showinfo(
            "Backend Değişikliği",
            "Hesaplama HEOS yerine SRK yöntemi ile devam edecek."
        )
    else:
        messagebox.showwarning(
            "Risk Kabul Edildi",
            "HEOS ile devam etme riskini kabul ettiniz. "
            "Hesaplama başarısız olabilir."
        )
    
    return result


def show_heating_value_method_warning(method: str) -> None:
    """
    Show warning when heating values are calculated using component-based method.
    
    Args:
        method: Calculation method used
    """
    if method == "Bileşen bazlı":
        messagebox.showwarning(
            "Isıl Değer Hesaplama Uyarısı ⚠️",
            "CoolProp yerleşik modeli ısıl değerleri doğrudan hesaplayamadığı için,\n"
            "daha sağlam 'Bileşen Bazlı Toplama' yöntemi kullanılmıştır.\n\n"
            "Bu yöntem karışım etkileşimlerini ihmal eder ve CoolProp yerleşik\n"
            "hesabına göre daha düşük doğrulukta olabilir.\n\n"
            "**Sonuçları mühendislik onayı ile kullanınız.**"
        )


def show_backend_fallback_info(error_message: str, failed_backend: str) -> None:
    """
    Show information when backend fallback occurs.
    
    Args:
        error_message: Error message from failed backend
        failed_backend: Name of the backend that failed
    """
    messagebox.showwarning(
        "Backend Değişikliği",
        f"{failed_backend} backend'i başarısız oldu:\n\n"
        f"CoolProp Hatası: {error_message}\n\n"
        f"Program otomatik olarak alternatif bir yöntem deneyecek."
    )


def show_backend_used_info(requested_backend: str, used_backend: str) -> None:
    """
    Show info when different backend was used than requested.
    
    Args:
        requested_backend: Backend user requested
        used_backend: Backend actually used
    """
    if requested_backend != used_backend:
        messagebox.showinfo(
            "Backend Değişikliği",
            f"Hesaplama {used_backend} yöntemi ile tamamlandı.\n"
            f"(İstenilen: {requested_backend})"
        )


def show_about_dialog() -> None:
    """Show application about information."""
    about_text = (
        "Termodinamik Gaz Karışımı Hesaplayıcı\n"
        "Sürüm 5.0.0 - Modüler Mimari\n\n"
        "Bu program, CoolProp kütüphanesini kullanarak gaz karışımlarının\n"
        "termodinamik özelliklerini hesaplar.\n\n"
        "Doğal gaz/petrol sektöründe sıkça kullanılan kritik özellikleri\n"
        "(Z-faktörü, k, a, HHV/LHV) sağlamak üzere tasarlanmıştır.\n\n"
        "© 2025 Kompresör Pompa"
    )
    messagebox.showinfo("Hakkında", about_text)


def show_user_guide_dialog() -> None:
    """Show user guide information."""
    from natural_gas_g5.config.settings import config
    
    guide_text = (
        "KULLANIM KILAVUZU - Doğal Gaz Özellikleri G5\n\n"
        "1. GAZ KOMPOZİSYONU:\n"
        "   • Yüzde toplamı tam 100% olmalıdır\n"
        "   • Maksimum 20 gaz bileşeni eklenebilir\n"
        "   • Arama kutusu ile gaz seçimi hızlandırılabilir\n\n"
        "2. BASINÇ GİRİŞİ:\n"
        f"   • Gauge (g) basınçları için atmosferik basınç ({config.P_ATM_BAR} bar) referans alınır\n"
        "   • Absolute (a) basınçlar doğrudan kullanılır\n\n"
        "3. HESAPLAMA YÖNTEMİ:\n"
        "   • HEOS: En doğru, ancak sınırlı gaz desteği\n"
        "   • SRK/PR: Daha geniş kapsam, cubic equations of state\n"
        "   • Uyumsuzluk durumunda otomatik geçiş yapılabilir\n\n"
        "4. ISIL DEĞER GÜVENİLİRLİĞİ (KRİTİK):\n"
        "   • 'CoolProp yerleşik': En doğru yöntem\n"
        "   • 'Bileşen bazlı': Yedekleme yöntemi, daha düşük doğruluk\n"
        "   • Uyarı mesajları dikkate alınmalıdır\n\n"
        "5. SONUÇLAR:\n"
        "   • Gerçek koşullar (girilen T ve P'de)\n"
        "   • Standart koşullar (15°C, 101.325 kPa)\n"
        "   • Isıl değerler (HHV, LHV, Wobbe)\n"
        "   • Hacim dönüşümü (isteğe bağlı)"
    )
    messagebox.showinfo("Kullanım Kılavuzu", guide_text)


def show_new_features_info() -> None:
    """Show new features information for G5."""
    info = (
        "✨ DOĞAL GAZ ÖZELLİKLERİ G5 - YENİ SÜRÜM\n\n"
        "🔥 YENİ ÖZELLİKLER:\n"
        "• 📏 Gelişmiş Standartlar: ISO, GPA, API, GOST standartları desteği\n"
        "• 📉 NCM/SCM Ayrımı: Normal (0°C) ve Standart (seçilen) hacim dönüşümü\n"
        "• 💾 Kaydet/Yükle: Çalışmalarınızı JSON olarak kaydedip tekrar yükleyin\n"
        "• 📝 Canlı Loglar: Hesaplama adımlarını ve hataları anlık takip edin\n\n"
        "🎉 TEMİZ, MODÜLER MİMARİ:\n"
        "• 15+ modül ile organize kod yapısı\n"
        "• Her modül tek sorumluluk prensibi ile tasarlanmıştır\n\n"
        "✅ GELİŞMİŞ DOĞRULAMA:\n"
        "• Pydantic ile tip güvenli veri yapıları\n"
        "• Anında girdi doğrulama\n"
        "• Detaylı hata mesajları\n\n"
        "🚀 PERFORMANS:\n"
        "• Optimize edilmiş hesaplama akışı\n"
        "• Daha hızlı başlangıç (lazy loading)\n\n"
        "📊 AYNI DOĞRULUK:\n"
        "• G4.9.1 ile aynı hesaplama sonuçları\n"
        "• CoolProp entegrasyonu korunmuştur\n\n"
        "G4.9.1'den G5'e Hoş Geldiniz!"
    )
    messagebox.showinfo("Yeni Sürüm - G5", info)


def confirm_calculation_start() -> bool:
    """
    Ask user confirmation before starting heavy calculation (if needed).
    
    Returns:
        True if user confirms, False otherwise
    """
    # For now, always return True (no confirmation needed)
    # Can be extended for very large calculations
    return True


def show_error(title: str, message: str) -> None:
    """
    Show error message dialog.
    
    Args:
        title: Dialog title
        message: Error message
    """
    messagebox.showerror(title, message)


def show_warning(title: str, message: str) -> None:
    """
    Show warning message dialog.
    
    Args:
        title: Dialog title
        message: Warning message
    """
    messagebox.showwarning(title, message)


def show_info(title: str, message: str) -> None:
    """
    Show information message dialog.
    
    Args:
        title: Dialog title
        message: Information message
    """
    messagebox.showinfo(title, message)
