# rapor.py
"""
Profesyonel PDF raporlama modülü
Proje takip sisteminden veri çeker ve analiz raporları oluşturur
"""

import logging
import os
from datetime import datetime
from typing import Dict
from dataclasses import dataclass
from app_paths import get_resource_path, get_internal_path

# ReportLab kütüphanesi
try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import (
        SimpleDocTemplate,
        Table,
        TableStyle,
        Paragraph,
        Spacer,
        PageBreak,
    )
    from reportlab.lib.enums import TA_CENTER
    from reportlab.graphics.shapes import Drawing
    from reportlab.graphics.charts.piecharts import Pie
    from reportlab.graphics.charts.barcharts import VerticalBarChart
    from reportlab.graphics.charts.legends import Legend

    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    logging.warning(
        "ReportLab kütüphanesi bulunamadı. PDF raporları oluşturulamayacak."
    )

from database import ProjeTakipDB
from config import APP_NAME
from project_types import get_project_type_aliases

logger = logging.getLogger(__name__)


def _resolve_report_font_name() -> str:
    """Return a safe report font name, falling back when the bundled TTF is unusable."""
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    import reportlab.rl_config

    reportlab.rl_config.warnOnMissingFontGlyphs = 0

    font_path = get_internal_path("DejaVuSans.ttf")
    try:
        if not os.path.exists(font_path):
            raise FileNotFoundError(font_path)
        if os.path.getsize(font_path) <= 0:
            raise ValueError("DejaVuSans.ttf is empty")
        pdfmetrics.registerFont(TTFont("DejaVu", font_path))
        return "DejaVu"
    except Exception as exc:
        logger.warning("Report font fallback in use: %s", exc)
        return "Helvetica"

# =============================================================================
# HEDEF PROJE SAYILARI (Kullanıcıdan alınan veri)
# =============================================================================

HEDEF_PROJELER = {"Mekanik": 114, "Elektrik": 151, "I&C": 46, "İnşaat": 260}

TOPLAM_HEDEF = sum(HEDEF_PROJELER.values())  # 571

# =============================================================================
# VERİ SINIFI
# =============================================================================


@dataclass
class RaporVerisi:
    """Rapor için toplanan veri"""

    # Onaylı projeler (türlere göre)
    onayli_projeler: Dict[str, int]
    toplam_onayli: int

    # Siemens projeleri (onaylı olanlar)
    siemens_projeler: Dict[str, int]
    toplam_siemens: int

    # Oranlar
    oran_siemens_dahil: Dict[str, float]  # Onaylı / Hedef
    oran_siemens_haric: Dict[str, float]  # (Onaylı - Siemens) / Hedef

    # Genel oranlar
    genel_oran_siemens_dahil: float  # Toplam Onaylı / Toplam Hedef
    genel_oran_siemens_haric: float  # (Toplam Onaylı - Toplam Siemens) / Toplam Hedef

    # Meta
    olusturma_tarihi: str


# =============================================================================
# VERİ TOPLAMA FONKSİYONU
# =============================================================================


def rapor_verisi_topla(db: ProjeTakipDB) -> RaporVerisi:
    """
    Veritabanından rapor için gerekli verileri topla

    Args:
        db: Veritabanı bağlantısı

    Returns:
        RaporVerisi: Toplanan veriler
    """
    try:
        # Onaylı projeleri türlere göre say
        onayli_projeler = {}
        for tur in HEDEF_PROJELER.keys():
            aliases = list(get_project_type_aliases(tur))
            placeholders = ",".join("?" * len(aliases))
            cursor = db.conn.execute(
                f"""
                SELECT COUNT(DISTINCT p.id) 
                FROM projeler p
                WHERE p.proje_turu IN ({placeholders})
                AND EXISTS (
                    SELECT 1 FROM revizyonlar r 
                    WHERE r.proje_id = p.id 
                    AND r.durum = 'Onayli'
                )
            """,
                aliases,
            )
            onayli_projeler[tur] = cursor.fetchone()[0]

        toplam_onayli = sum(onayli_projeler.values())

        # Siemens projelerini say (onaylı olanlar)
        # NOT: Siemens proje kodunda "SIEMENS" veya "SMN" içeren projeler
        siemens_projeler = {}
        for tur in HEDEF_PROJELER.keys():
            aliases = list(get_project_type_aliases(tur))
            placeholders = ",".join("?" * len(aliases))
            cursor = db.conn.execute(
                f"""
                SELECT COUNT(DISTINCT p.id) 
                FROM projeler p
                WHERE p.proje_turu IN ({placeholders})
                AND (p.proje_kodu LIKE '%SIEMENS%' OR p.proje_kodu LIKE '%SMN%')
                AND EXISTS (
                    SELECT 1 FROM revizyonlar r 
                    WHERE r.proje_id = p.id 
                    AND r.durum = 'Onayli'
                )
            """,
                aliases,
            )
            siemens_projeler[tur] = cursor.fetchone()[0]

        toplam_siemens = sum(siemens_projeler.values())

        # Oranları hesapla
        oran_siemens_dahil = {}
        oran_siemens_haric = {}

        for tur in HEDEF_PROJELER.keys():
            hedef = HEDEF_PROJELER[tur]
            onayli = onayli_projeler[tur]
            siemens = siemens_projeler[tur]
            # Siemens dahil oran: (Onaylı / Hedef) * 100
            oran_siemens_dahil[tur] = (onayli / hedef * 100.0) if hedef > 0 else 0.0
            # Siemens hariç oran: ((Onaylı - Siemens) / (Hedef - Siemens)) * 100
            hedef_haric = max(hedef - siemens, 1)  # Sıfıra bölme engeli
            onayli_haric = max(onayli - siemens, 0)
            oran_siemens_haric[tur] = (
                (onayli_haric / hedef_haric * 100.0) if hedef_haric > 0 else 0.0
            )
        # Genel oranlar
        genel_oran_siemens_dahil = (
            (toplam_onayli / TOPLAM_HEDEF * 100.0) if TOPLAM_HEDEF > 0 else 0.0
        )
        toplam_hedef_haric = max(TOPLAM_HEDEF - toplam_siemens, 1)
        toplam_onayli_haric = max(toplam_onayli - toplam_siemens, 0)
        genel_oran_siemens_haric = (
            (toplam_onayli_haric / toplam_hedef_haric * 100.0)
            if toplam_hedef_haric > 0
            else 0.0
        )

        return RaporVerisi(
            onayli_projeler=onayli_projeler,
            toplam_onayli=toplam_onayli,
            siemens_projeler=siemens_projeler,
            toplam_siemens=toplam_siemens,
            oran_siemens_dahil=oran_siemens_dahil,
            oran_siemens_haric=oran_siemens_haric,
            genel_oran_siemens_dahil=genel_oran_siemens_dahil,
            genel_oran_siemens_haric=genel_oran_siemens_haric,
            olusturma_tarihi=datetime.now().strftime("%d.%m.%Y %H:%M"),
        )

    except Exception as e:
        logger.error(f"Rapor verisi toplama hatası: {e}")
        raise


# =============================================================================
# PDF OLUŞTURMA FONKSİYONU
# =============================================================================


def rapor_pdf_olustur(rapor_verisi: RaporVerisi, dosya_yolu: str) -> bool:
    """
    Profesyonel PDF raporu oluştur

    Args:
        rapor_verisi: Rapor verileri
        dosya_yolu: PDF dosyasının kaydedileceği yol

    Returns:
        bool: Başarılı ise True
    """
    if not REPORTLAB_AVAILABLE:
        logger.error("ReportLab kütüphanesi yüklü değil!")
        return False

    try:
        # PDF belgesi oluştur (A4 landscape)
        doc = SimpleDocTemplate(
            dosya_yolu,
            pagesize=landscape(A4),
            rightMargin=2 * cm,
            leftMargin=2 * cm,
            topMargin=2 * cm,
            bottomMargin=2 * cm,
            encoding="utf-8",
        )
        # İçerik listesi
        story = []
        # Stiller
        styles = getSampleStyleSheet()
        # Türkçe karakter desteği için font ayarla
        font_name = _resolve_report_font_name()
        # Başlık stili
        baslik_style = ParagraphStyle(
            "BaslikStyle",
            parent=styles["Heading1"],
            fontName=font_name,
            fontSize=18,
            textColor=colors.HexColor("#1a5490"),
            alignment=TA_CENTER,
            spaceAfter=12,
        )
        # Alt başlık stili
        alt_baslik_style = ParagraphStyle(
            "AltBaslikStyle",
            parent=styles["Heading2"],
            fontName=font_name,
            fontSize=14,
            textColor=colors.HexColor("#2c5aa0"),
            spaceAfter=10,
        )
        # Normal metin
        normal_style = styles["Normal"]
        normal_style.fontName = font_name
        normal_style.fontSize = 10

        # =============================================================================
        # BAŞLIK
        # =============================================================================

        story.append(Paragraph(f"<b>{APP_NAME}</b>", baslik_style))
        story.append(Paragraph("Proje Onay Durum Raporu", alt_baslik_style))
        story.append(
            Paragraph(f"Rapor Tarihi: {rapor_verisi.olusturma_tarihi}", normal_style)
        )
        story.append(Spacer(1, 0.5 * cm))

        # =============================================================================
        # TABLO 1: HEDEF PROJE SAYILARI
        # =============================================================================

        story.append(Paragraph("<b>1. Hedef Proje Sayıları</b>", alt_baslik_style))

        tablo1_data = [["Proje Türü", "Hedef Sayı"]]

        for tur, hedef in HEDEF_PROJELER.items():
            tablo1_data.append([tur, str(hedef)])

        tablo1_data.append(["TOPLAM", str(TOPLAM_HEDEF)])

        tablo1 = Table(tablo1_data, colWidths=[10 * cm, 5 * cm])
        tablo1.setStyle(
            TableStyle(
                [
                    # Başlık satırı
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c5aa0")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 12),
                    ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                    # Veri satırları
                    ("BACKGROUND", (0, 1), (-1, -2), colors.beige),
                    ("FONTNAME", (0, 1), (-1, -2), "Helvetica"),
                    ("FONTSIZE", (0, 1), (-1, -2), 10),
                    ("ALIGN", (0, 1), (0, -1), "LEFT"),
                    ("ALIGN", (1, 1), (1, -1), "CENTER"),
                    # Toplam satırı
                    ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#4a7ba7")),
                    ("TEXTCOLOR", (0, -1), (-1, -1), colors.whitesmoke),
                    ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                    ("FONTSIZE", (0, -1), (-1, -1), 11),
                    # Çizgiler
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                    ("LINEBELOW", (0, 0), (-1, 0), 2, colors.black),
                ]
            )
        )

        story.append(tablo1)
        story.append(Spacer(1, 1 * cm))

        # =============================================================================
        # TABLO 2: ONAYLI PROJELER VE ORANLAR
        # =============================================================================

        story.append(
            Paragraph(
                "<b>2. Onaylı Projeler ve Gerçekleşme Oranları</b>", alt_baslik_style
            )
        )

        tablo2_data = [
            [
                "Proje Türü",
                "Hedef",
                "Onaylı\n(Toplam)",
                "Siemens",
                "Oran\n(Siemens Dahil)",
                "Oran\n(Siemens Hariç)",
            ]
        ]

        for tur in HEDEF_PROJELER.keys():
            hedef = HEDEF_PROJELER[tur]
            onayli = rapor_verisi.onayli_projeler[tur]
            siemens = rapor_verisi.siemens_projeler[tur]
            oran_dahil = rapor_verisi.oran_siemens_dahil[tur]
            oran_haric = rapor_verisi.oran_siemens_haric[tur]

            tablo2_data.append(
                [
                    tur,
                    str(hedef),
                    str(onayli),
                    str(siemens),
                    f"%{oran_dahil:.1f}",
                    f"%{oran_haric:.1f}",
                ]
            )

        # Toplam satırı
        tablo2_data.append(
            [
                "TOPLAM",
                str(TOPLAM_HEDEF),
                str(rapor_verisi.toplam_onayli),
                str(rapor_verisi.toplam_siemens),
                f"%{rapor_verisi.genel_oran_siemens_dahil:.1f}",
                f"%{rapor_verisi.genel_oran_siemens_haric:.1f}",
            ]
        )

        tablo2 = Table(
            tablo2_data, colWidths=[5 * cm, 3 * cm, 3 * cm, 3 * cm, 4 * cm, 4 * cm]
        )
        tablo2.setStyle(
            TableStyle(
                [
                    # Başlık satırı
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c5aa0")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 10),
                    ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                    ("VALIGN", (0, 0), (-1, 0), "MIDDLE"),
                    # Veri satırları
                    ("BACKGROUND", (0, 1), (-1, -2), colors.beige),
                    ("FONTNAME", (0, 1), (-1, -2), "Helvetica"),
                    ("FONTSIZE", (0, 1), (-1, -2), 9),
                    ("ALIGN", (0, 1), (0, -1), "LEFT"),
                    ("ALIGN", (1, 1), (-1, -1), "CENTER"),
                    # Toplam satırı
                    ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#4a7ba7")),
                    ("TEXTCOLOR", (0, -1), (-1, -1), colors.whitesmoke),
                    ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                    ("FONTSIZE", (0, -1), (-1, -1), 10),
                    # Çizgiler
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                    ("LINEBELOW", (0, 0), (-1, 0), 2, colors.black),
                ]
            )
        )

        story.append(tablo2)
        story.append(Spacer(1, 1 * cm))

        # =============================================================================
        # ÖZET AÇIKLAMALAR
        # =============================================================================

        story.append(Paragraph("<b>3. Özet Değerlendirme</b>", alt_baslik_style))

        ozet_text = f"""
        <b>Toplam Hedef Proje Sayısı:</b> {TOPLAM_HEDEF}<br/>
        <b>Onaylanan Toplam Proje Sayısı:</b> {rapor_verisi.toplam_onayli}<br/>
        <b>Siemens Projesi (Onaylı):</b> {rapor_verisi.toplam_siemens}<br/>
        <br/>
        <b>Genel Gerçekleşme Oranı (Siemens Dahil):</b> %{rapor_verisi.genel_oran_siemens_dahil:.1f}<br/>
        <b>Genel Gerçekleşme Oranı (Siemens Hariç):</b> %{rapor_verisi.genel_oran_siemens_haric:.1f}<br/>
        <br/>
        <i>Not: Siemens projeleri, proje kodunda 'SIEMENS' veya 'SMN' içeren ve en az bir revizyonu onaylanmış projelerdir.</i>
        """

        story.append(Paragraph(ozet_text, normal_style))
        story.append(Spacer(1, 1 * cm))

        # =============================================================================
        # GRAFİKLER
        # =============================================================================

        story.append(PageBreak())  # Yeni sayfa
        story.append(Paragraph("<b>4. Grafiksel Analiz</b>", alt_baslik_style))
        story.append(Spacer(1, 0.5 * cm))

        # =============================================================================
        # GRAFİK 1: PASTA GRAFİĞİ - HEDEF PROJE DAĞILIMI
        # =============================================================================

        story.append(
            Paragraph("<b>4.1. Hedef Proje Türleri Dağılımı</b>", normal_style)
        )
        story.append(Spacer(1, 0.3 * cm))

        pasta_drawing = Drawing(400, 200)
        pasta = Pie()
        pasta.x = 100
        pasta.y = 20
        pasta.width = 150
        pasta.height = 150

        # Veri ve etiketler
        pasta.data = [HEDEF_PROJELER[tur] for tur in HEDEF_PROJELER.keys()]
        pasta.labels = [
            f"{tur}\n({HEDEF_PROJELER[tur]})" for tur in HEDEF_PROJELER.keys()
        ]

        # Renkler
        pasta.slices.strokeWidth = 1
        pasta.slices.strokeColor = colors.white
        pasta_renkleri = [
            colors.HexColor("#4a7ba7"),  # Mavi
            colors.HexColor("#e8743b"),  # Turuncu
            colors.HexColor("#19a979"),  # Yeşil
            colors.HexColor("#ed6a5a"),  # Kırmızı
        ]
        for i, renk in enumerate(pasta_renkleri):
            pasta.slices[i].fillColor = renk

        pasta_drawing.add(pasta)

        # Legend
        legend = Legend()
        legend.x = 280
        legend.y = 100
        legend.dx = 8
        legend.dy = 8
        legend.fontName = "Helvetica"
        legend.fontSize = 9
        legend.boxAnchor = "w"
        legend.columnMaximum = 10
        legend.strokeWidth = 1
        legend.strokeColor = colors.black
        legend.deltax = 75
        legend.deltay = 10
        legend.autoXPadding = 5
        legend.yGap = 0
        legend.dxTextSpace = 5
        legend.alignment = "right"
        legend.dividerLines = 1 | 2 | 4
        legend.dividerOffsY = 4.5
        legend.subCols.rpad = 30

        legend.colorNamePairs = [
            (
                pasta_renkleri[i],
                f"{list(HEDEF_PROJELER.keys())[i]}: {list(HEDEF_PROJELER.values())[i]}",
            )
            for i in range(len(HEDEF_PROJELER))
        ]

        pasta_drawing.add(legend)
        story.append(pasta_drawing)
        story.append(Spacer(1, 1 * cm))

        # =============================================================================
        # GRAFİK 2: BAR GRAFİĞİ - ONAYLI PROJE KARŞILAŞTIRMASI
        # =============================================================================

        story.append(
            Paragraph("<b>4.2. Hedef vs Onaylı Proje Karşılaştırması</b>", normal_style)
        )
        story.append(Spacer(1, 0.3 * cm))

        bar_drawing = Drawing(700, 300)
        bar_chart = VerticalBarChart()
        bar_chart.x = 50
        bar_chart.y = 50
        bar_chart.height = 200
        bar_chart.width = 600

        # Veriler: [Hedef, Onaylı, Siemens]
        turler = list(HEDEF_PROJELER.keys())
        bar_chart.data = [
            [HEDEF_PROJELER[tur] for tur in turler],  # Hedef
            [rapor_verisi.onayli_projeler[tur] for tur in turler],  # Onaylı
            [rapor_verisi.siemens_projeler[tur] for tur in turler],  # Siemens
        ]

        # Kategori isimleri
        bar_chart.categoryAxis.categoryNames = turler
        bar_chart.categoryAxis.labels.boxAnchor = "ne"
        bar_chart.categoryAxis.labels.dx = 8
        bar_chart.categoryAxis.labels.dy = -2
        bar_chart.categoryAxis.labels.angle = 30
        bar_chart.categoryAxis.labels.fontName = "Helvetica"
        bar_chart.categoryAxis.labels.fontSize = 9

        # Y ekseni
        bar_chart.valueAxis.valueMin = 0
        bar_chart.valueAxis.valueMax = max([HEDEF_PROJELER[tur] for tur in turler]) + 20
        bar_chart.valueAxis.valueStep = 50
        bar_chart.valueAxis.labels.fontName = "Helvetica"
        bar_chart.valueAxis.labels.fontSize = 9

        # Bar renkleri
        bar_chart.bars[0].fillColor = colors.HexColor("#4a7ba7")  # Hedef - Mavi
        bar_chart.bars[1].fillColor = colors.HexColor("#19a979")  # Onaylı - Yeşil
        bar_chart.bars[2].fillColor = colors.HexColor("#e8743b")  # Siemens - Turuncu

        # Bar stilleri
        bar_chart.barSpacing = 2
        bar_chart.groupSpacing = 15
        bar_chart.barWidth = 15

        bar_drawing.add(bar_chart)

        # Bar chart legend
        bar_legend = Legend()
        bar_legend.x = 50
        bar_legend.y = 20
        bar_legend.dx = 8
        bar_legend.dy = 8
        bar_legend.fontName = "Helvetica"
        bar_legend.fontSize = 9
        bar_legend.boxAnchor = "sw"
        bar_legend.columnMaximum = 1
        bar_legend.alignment = "right"
        bar_legend.colorNamePairs = [
            (colors.HexColor("#4a7ba7"), "Hedef"),
            (colors.HexColor("#19a979"), "Onaylı"),
            (colors.HexColor("#e8743b"), "Siemens"),
        ]

        bar_drawing.add(bar_legend)
        story.append(bar_drawing)
        story.append(Spacer(1, 1 * cm))

        # =============================================================================
        # GRAFİK 3: YÜZDE BAR GRAFİĞİ - GERÇEKLEŞME ORANLARI
        # =============================================================================

        story.append(Paragraph("<b>4.3. Gerçekleşme Oranları (%)</b>", normal_style))
        story.append(Spacer(1, 0.3 * cm))

        oran_drawing = Drawing(700, 300)
        oran_chart = VerticalBarChart()
        oran_chart.x = 50
        oran_chart.y = 50
        oran_chart.height = 200
        oran_chart.width = 600

        # Veriler: [Siemens Dahil, Siemens Hariç]
        oran_chart.data = [
            [rapor_verisi.oran_siemens_dahil[tur] for tur in turler],  # Siemens Dahil
            [rapor_verisi.oran_siemens_haric[tur] for tur in turler],  # Siemens Hariç
        ]

        # Kategori isimleri
        oran_chart.categoryAxis.categoryNames = turler
        oran_chart.categoryAxis.labels.boxAnchor = "ne"
        oran_chart.categoryAxis.labels.dx = 8
        oran_chart.categoryAxis.labels.dy = -2
        oran_chart.categoryAxis.labels.angle = 30
        oran_chart.categoryAxis.labels.fontName = "Helvetica"
        oran_chart.categoryAxis.labels.fontSize = 9

        # Y ekseni (0-100%)
        oran_chart.valueAxis.valueMin = 0
        oran_chart.valueAxis.valueMax = 100
        oran_chart.valueAxis.valueStep = 10
        oran_chart.valueAxis.labels.fontName = "Helvetica"
        oran_chart.valueAxis.labels.fontSize = 9
        oran_chart.valueAxis.labelTextFormat = "%d%%"

        # Bar renkleri
        oran_chart.bars[0].fillColor = colors.HexColor(
            "#2c5aa0"
        )  # Siemens Dahil - Koyu Mavi
        oran_chart.bars[1].fillColor = colors.HexColor(
            "#4a7ba7"
        )  # Siemens Hariç - Açık Mavi

        # Bar stilleri
        oran_chart.barSpacing = 3
        oran_chart.groupSpacing = 20
        oran_chart.barWidth = 20

        oran_drawing.add(oran_chart)

        # Oran chart legend
        oran_legend = Legend()
        oran_legend.x = 50
        oran_legend.y = 20
        oran_legend.dx = 8
        oran_legend.dy = 8
        oran_legend.fontName = "Helvetica"
        oran_legend.fontSize = 9
        oran_legend.boxAnchor = "sw"
        oran_legend.columnMaximum = 1
        oran_legend.alignment = "right"
        oran_legend.colorNamePairs = [
            (colors.HexColor("#2c5aa0"), "Oran (Siemens Dahil)"),
            (colors.HexColor("#4a7ba7"), "Oran (Siemens Hariç)"),
        ]

        oran_drawing.add(oran_legend)
        story.append(oran_drawing)

        # =============================================================================
        # PDF OLUŞTUR
        # =============================================================================

        doc.build(story)
        logger.info(f"PDF rapor oluşturuldu: {dosya_yolu}")
        return True

    except Exception as e:
        logger.error(f"PDF oluşturma hatası: {e}", exc_info=True)
        return False


# =============================================================================
# ANA FONKSİYON (TEST İÇİN)
# =============================================================================


def rapor_olustur(
    db_yolu: str = "projeler.db", cikti_yolu: str = "proje_raporu.pdf"
) -> bool:
    """
    Ana rapor oluşturma fonksiyonu

    Args:
        db_yolu: Veritabanı dosya yolu
        cikti_yolu: Çıktı PDF dosyası yolu

    Returns:
        bool: Başarılı ise True
    """
    try:
        # Veritabanı bağlantısı
        db = ProjeTakipDB(db_yolu)

        # Veri topla
        logger.info("Rapor verisi toplanıyor...")
        veri = rapor_verisi_topla(db)

        # PDF oluştur
        logger.info("PDF raporu oluşturuluyor...")
        basarili = rapor_pdf_olustur(veri, cikti_yolu)

        if basarili:
            logger.info(f"Rapor başarıyla oluşturuldu: {cikti_yolu}")
        else:
            logger.error("Rapor oluşturulamadı!")

        return basarili

    except Exception as e:
        logger.error(f"Rapor oluşturma hatası: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    # Test için
    logging.basicConfig(level=logging.INFO)
    rapor_olustur()
