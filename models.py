# models.py
from enum import Enum
from dataclasses import dataclass
from typing import Optional
from project_types import normalize_project_type

# =============================================================================
# ENUM VE EXCEPTION SINIFLARI
# =============================================================================


class Durum(Enum):
    ONAYSIZ = "Onaysiz"
    ONAYLI = "Onayli"
    REDDEDILDI = "Reddedildi"
    ONAYLI_NOTLU = "Notlu Onayli"


class DatabaseError(Exception):
    pass


# =============================================================================
# VERİ SINIFLARI (YENİ EKLENDİ)
# =============================================================================


@dataclass
class ProjeModel:
    """
    database.py ve filters.py'deki ana proje sorgularının
    döndürdüğü veriyi tutan sınıf. Tuple indeksleme yerine kullanılır.
    Sıralama, SELECT sorgularındaki sırayla eşleşmelidir.
    """

    id: int
    proje_kodu: str
    proje_ismi: str
    proje_turu: Optional[str]
    gelen_yazi_no: Optional[str]
    gelen_yazi_tarih: Optional[str]
    durum_renk: Optional[str]
    hiyerarsi: Optional[str]
    durum: Optional[str]
    tse_gonderildi: Optional[int]
    onay_yazi_no: Optional[str]
    red_yazi_no: Optional[str]
    kategori_id: Optional[int]  # <-- YENİ EKLENDİ (13. alan)

    def __post_init__(self):
        self.proje_turu = normalize_project_type(self.proje_turu)


@dataclass
class RevizyonModel:
    """
    database.py'deki revizyonlari_getir sorgusunun
    döndürdüğü veriyi tutan sınıf.
    Sıralama, SELECT sorgularındaki sırayla eşleşmelidir.
    """

    id: int
    proje_rev_no: int
    revizyon_kodu: str
    durum: str
    tarih: str
    aciklama: Optional[str]
    dokuman_durumu: str  # 'Var' / 'Yok'
    onay_yazi_no: Optional[str]
    onay_yazi_tarih: Optional[str]
    red_yazi_no: Optional[str]
    red_yazi_tarih: Optional[str]
    gelen_yazi_no: Optional[str]
    gelen_yazi_tarih: Optional[str]
    tse_gonderildi: int
    yazi_turu: Optional[str]  # YENİ: 'gelen', 'giden' veya 'yok'
    dosya_adi: Optional[str]
    yazi_dokuman_durumu: Optional[str] = None  # '-', 'Yüklü', 'Eksik'
    supheli_yazi_dokumani: int = 0  # 1: revizyon dokumaniyla birebir ayni
    takipte_mi: int = 0  # 1: takip listesinde aktif
    takip_notu: Optional[str] = None
