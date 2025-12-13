# Doğal Gaz Özellikleri G5

**Modern, modüler termodinamik gaz karışımı hesaplama uygulaması**

![Version](https://img.shields.io/badge/version-5.0.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.10+-green.svg)

## 🎯 Özellikler

- ✅ **Kapsamlı Hesaplamalar:** Z-faktörü, yoğunluk, entalpi, entropi, Cp, Cv, k, ses hızı, HHV/LHV, Wobbe indeksi
- ✅ **Çoklu Backend:** HEOS, SRK, PR termodinamik modelleri
- ✅ **Otomatik Fallback:** Hesaplama başarısız olursa alternatif backend'lere geçiş
- ✅ **Type Safety:** Pydantic modelleri ile tip güvenli veri yapıları
- ✅ **Modüler Mimari:** Kolay test, bakım ve genişletme
- ✅ **Detaylı Loglama:** Tüm hesaplamalar ve hatalar kaydedilir

## 📋 Gereksinimler

- Python 3.10 veya üzeri
- CoolProp >= 6.4.1
- Pydantic >= 2.0.0

## 🚀 Kurulum

### 1. Bağımlılıkları Yükleyin

```bash
pip install -r requirements.txt
```

### 2. (Opsiyonel) Geliştirme Araçlarını Yükleyin

```bash
pip install -r requirements-dev.txt
```

## 💻 Kullanım

### GUI Uygulaması

```bash
python -m natural_gas_g5.main
```

### Python API (Gelecek Sürüm)

```python
from natural_gas_g5.models.gas_data import GasComponent, GasMixture
from natural_gas_g5.models.calculator import ThermoCalculator

# Karışım tanımla
mixture = GasMixture(
    components=[
        GasComponent(name="Methane", fraction=90.0),
        GasComponent(name="Ethane", fraction=5.0),
        GasComponent(name="Nitrogen", fraction=5.0)
    ],
    fraction_type="molar"
)

# Hesapla
calc = ThermoCalculator(backend="HEOS")
result = calc.calculate_properties(
    mixture=mixture,
    temperature_k=298.15,  # 25°C
    pressure_pa=101325.0   # 1 atm
)

print(f"Yoğunluk: {result.actual.density:.4f} kg/m³")
print(f"Z-faktörü: {result.actual.compressibility_factor:.5f}")
```

## 📁 Proje Yapısı

```
Doğal Gaz Özellikleri G5/
├── natural_gas_g5/          # Ana paket
│   ├── config/              # Konfigürasyon
│   ├── core/                # Core utilities
│   ├── models/              # Data modelleri ve hesaplama
│   ├── ui/                  # Kullanıcı arayüzü
│   └── utils/               # Yardımcı fonksiyonlar
├── tests/                   # Test dosyaları
├── requirements.txt         # Bağımlılıklar
└── README.md               # Bu dosya
```

## 🔧 Konfigürasyon

Ayarlar `natural_gas_g5/config/settings.py` dosyasında merkezi olarak yönetilir:

- Fiziksel sabitler (atmosferik basınç, standart koşullar)
- Hesaplama limitleri (min/max sıcaklık, basınç)
- UI ayarları (pencere boyutu, tema)
- Loglama yapılandırması

## 📊 Desteklenen Birimler

### Sıcaklık
- Kelvin (K)
- Celsius (°C)
- Fahrenheit (°F)

### Basınç  
- Kilopascal (kPa)
- Bar absolute (bar(a))
- Bar gauge (bar(g))
- PSI absolute (psi(a))
- PSI gauge (psi(g))
- Megapascal (MPa)
- Atmosphere (atm)

## 🧪 Test

```bash
# Tüm testleri çalıştır
pytest

# Coverage raporu ile
pytest --cov=natural_gas_g5 --cov-report=html

# Tek bir test dosyası
pytest tests/test_calculator.py -v
```

## 📝 Değişiklik Geçmişi

### Sürüm 5.0.0 (2025-11-21)
- 🎉 İlk G5 sürümü - Komple modüler refactoring
- ✅ Pydantic ile veri validasyonu
- ✅ Type hints tüm kod tabanında
- ✅ UI ve hesaplama lojiği ayrımı
- ✅ Özel exception handling
- ✅ Merkezi konfigürasyon

### G4.9.1'den Farklar
- **Mimari:** Monolitik → Modüler (15+ modül)
- **Validasyon:** Manuel → Pydantic
- **Test Edilebilirlik:** Zor → Kolay
- **Bakım:** Karmaşık → Basit
- **Genişletilebilirlik:** Sınırlı → Yüksek

## 🤝 Katkıda Bulunma

Bu proje Kompresör Pompa tarafından geliştirilmektedir.

## 📄 Lisans

Tescilli yazılım - Kompresör Pompa

## 📧 İletişim

Sorular ve destek için lütfen proje yöneticisi ile iletişime geçin.

---

**Not:** G5, G4.9.1'in tüm özelliklerini korurken modern Python best practices ile yeniden yazılmıştır.
