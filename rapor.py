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
        doc = SimpleDocTemplate(
            dosya_yolu,
            pagesize=landscape(A4),
            rightMargin=2 * cm,
            leftMargin=2 * cm,
            topMargin=2 * cm,
            bottomMargin=2 * cm,
            encoding="utf-8",
        )
        story = []
        styles = getSampleStyleSheet()
        font_name = _resolve_report_font_name()
        baslik_style, alt_baslik_style, normal_style = _create_styles(styles, font_name)

        _add_header(story, rapor_verisi, baslik_style, alt_baslik_style, normal_style)
        _add_target_table(story, alt_baslik_style)
        _add_approved_table(story, rapor_verisi, alt_baslik_style)
        _add_summary(story, rapor_verisi, alt_baslik_style, normal_style)

        story.append(PageBreak())
        _add_charts(story, rapor_verisi, alt_baslik_style, normal_style)

        doc.build(story)
        logger.info(f"PDF rapor oluşturuldu: {dosya_yolu}")
        return True

    except Exception as e:
        logger.error(f"PDF oluşturma hatası: {e}", exc_info=True)
        return False


# =============================================================================
# PDF SECTION HELPERS
# =============================================================================

def _create_styles(styles, font_name):
    baslik_style = ParagraphStyle(
        "BaslikStyle", parent=styles["Heading1"],
        fontName=font_name, fontSize=18, textColor=colors.HexColor("#1a5490"),
        alignment=TA_CENTER, spaceAfter=12,
    )
    alt_baslik_style = ParagraphStyle(
        "AltBaslikStyle", parent=styles["Heading2"],
        fontName=font_name, fontSize=14, textColor=colors.HexColor("#2c5aa0"),
        spaceAfter=10,
    )
    normal_style = styles["Normal"]
    normal_style.fontName = font_name
    normal_style.fontSize = 10
    return baslik_style, alt_baslik_style, normal_style


def _add_header(story, rapor_verisi, baslik_style, alt_baslik_style, normal_style):
    story.append(Paragraph(f"<b>{APP_NAME}</b>", baslik_style))
    story.append(Paragraph("Proje Onay Durum Raporu", alt_baslik_style))
    story.append(Paragraph(f"Rapor Tarihi: {rapor_verisi.olusturma_tarihi}", normal_style))
    story.append(Spacer(1, 0.5 * cm))


def _base_table_style():
    return TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c5aa0")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("BACKGROUND", (0, 1), (-1, -2), colors.beige),
        ("FONTNAME", (0, 1), (-1, -2), "Helvetica"),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#4a7ba7")),
        ("TEXTCOLOR", (0, -1), (-1, -1), colors.whitesmoke),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 1, colors.black),
        ("LINEBELOW", (0, 0), (-1, 0), 2, colors.black),
    ])


def _add_target_table(story, alt_baslik_style):
    story.append(Paragraph("<b>1. Hedef Proje Sayıları</b>", alt_baslik_style))
    data = [["Proje Türü", "Hedef Sayı"]]
    for tur, hedef in HEDEF_PROJELER.items():
        data.append([tur, str(hedef)])
    data.append(["TOPLAM", str(TOPLAM_HEDEF)])
    style = _base_table_style()
    style.add("FONTSIZE", (0, 0), (-1, 0), 12)
    style.add("FONTSIZE", (0, 1), (-1, -2), 10)
    style.add("FONTSIZE", (0, -1), (-1, -1), 11)
    style.add("ALIGN", (0, 1), (0, -1), "LEFT")
    style.add("ALIGN", (1, 1), (1, -1), "CENTER")
    story.append(Table(data, colWidths=[10 * cm, 5 * cm]).setStyle(style))
    story.append(Spacer(1, 1 * cm))


def _add_approved_table(story, rapor_verisi, alt_baslik_style):
    story.append(Paragraph("<b>2. Onaylı Projeler ve Gerçekleşme Oranları</b>", alt_baslik_style))
    data = [
        ["Proje Türü", "Hedef", "Onaylı\n(Toplam)", "Siemens",
         "Oran\n(Siemens Dahil)", "Oran\n(Siemens Hariç)"]
    ]
    for tur in HEDEF_PROJELER.keys():
        hedef = HEDEF_PROJELER[tur]
        onayli = rapor_verisi.onayli_projeler[tur]
        siemens = rapor_verisi.siemens_projeler[tur]
        oran_dahil = rapor_verisi.oran_siemens_dahil[tur]
        oran_haric = rapor_verisi.oran_siemens_haric[tur]
        data.append([tur, str(hedef), str(onayli), str(siemens),
                     f"%{oran_dahil:.1f}", f"%{oran_haric:.1f}"])
    data.append([
        "TOPLAM", str(TOPLAM_HEDEF), str(rapor_verisi.toplam_onayli),
        str(rapor_verisi.toplam_siemens),
        f"%{rapor_verisi.genel_oran_siemens_dahil:.1f}",
        f"%{rapor_verisi.genel_oran_siemens_haric:.1f}",
    ])
    style = _base_table_style()
    style.add("FONTSIZE", (0, 0), (-1, 0), 10)
    style.add("VALIGN", (0, 0), (-1, 0), "MIDDLE")
    style.add("FONTSIZE", (0, 1), (-1, -2), 9)
    style.add("FONTSIZE", (0, -1), (-1, -1), 10)
    style.add("ALIGN", (0, 1), (0, -1), "LEFT")
    style.add("ALIGN", (1, 1), (-1, -1), "CENTER")
    story.append(Table(data, colWidths=[5*cm, 3*cm, 3*cm, 3*cm, 4*cm, 4*cm]).setStyle(style))
    story.append(Spacer(1, 1 * cm))


def _add_summary(story, rapor_verisi, alt_baslik_style, normal_style):
    story.append(Paragraph("<b>3. Özet Değerlendirme</b>", alt_baslik_style))
    ozet_text = (
        f"<b>Toplam Hedef Proje Sayısı:</b> {TOPLAM_HEDEF}<br/>"
        f"<b>Onaylanan Toplam Proje Sayısı:</b> {rapor_verisi.toplam_onayli}<br/>"
        f"<b>Siemens Projesi (Onaylı):</b> {rapor_verisi.toplam_siemens}<br/>"
        f"<br/>"
        f"<b>Genel Gerçekleşme Oranı (Siemens Dahil):</b> %{rapor_verisi.genel_oran_siemens_dahil:.1f}<br/>"
        f"<b>Genel Gerçekleşme Oranı (Siemens Hariç):</b> %{rapor_verisi.genel_oran_siemens_haric:.1f}<br/>"
        f"<br/>"
        "<i>Not: Siemens projeleri, proje kodunda 'SIEMENS' veya 'SMN' içeren "
        "ve en az bir revizyonu onaylanmış projelerdir.</i>"
    )
    story.append(Paragraph(ozet_text, normal_style))
    story.append(Spacer(1, 1 * cm))


def _add_charts(story, rapor_verisi, alt_baslik_style, normal_style):
    story.append(Paragraph("<b>4. Grafiksel Analiz</b>", alt_baslik_style))
    story.append(Spacer(1, 0.5 * cm))
    _add_pie_chart(story, normal_style)
    _add_bar_chart(story, rapor_verisi, normal_style)
    _add_ratio_chart(story, rapor_verisi, normal_style)


_PASTA_RENKLERI = [
    colors.HexColor("#4a7ba7"),
    colors.HexColor("#e8743b"),
    colors.HexColor("#19a979"),
    colors.HexColor("#ed6a5a"),
]


def _add_pie_chart(story, normal_style):
    story.append(Paragraph("<b>4.1. Hedef Proje Türleri Dağılımı</b>", normal_style))
    story.append(Spacer(1, 0.3 * cm))
    drawing = Drawing(400, 200)
    pie = Pie()
    pie.x, pie.y, pie.width, pie.height = 100, 20, 150, 150
    pie.data = [HEDEF_PROJELER[t] for t in HEDEF_PROJELER]
    pie.labels = [f"{t}\n({HEDEF_PROJELER[t]})" for t in HEDEF_PROJELER]
    pie.slices.strokeWidth = 1
    pie.slices.strokeColor = colors.white
    for i, renk in enumerate(_PASTA_RENKLERI):
        pie.slices[i].fillColor = renk
    drawing.add(pie)

    legend = Legend()
    legend.x, legend.y = 280, 100
    legend.dx, legend.dy = 8, 8
    legend.fontName, legend.fontSize = "Helvetica", 9
    legend.boxAnchor, legend.columnMaximum = "w", 10
    legend.strokeWidth, legend.strokeColor = 1, colors.black
    legend.deltax, legend.deltay = 75, 10
    legend.autoXPadding, legend.yGap = 5, 0
    legend.dxTextSpace, legend.alignment = 5, "right"
    legend.dividerLines, legend.dividerOffsY, legend.subCols.rpad = 1 | 2 | 4, 4.5, 30
    turler = list(HEDEF_PROJELER.keys())
    degerler = list(HEDEF_PROJELER.values())
    legend.colorNamePairs = [
        (_PASTA_RENKLERI[i], f"{turler[i]}: {degerler[i]}") for i in range(len(turler))
    ]
    drawing.add(legend)
    story.append(drawing)
    story.append(Spacer(1, 1 * cm))


def _add_bar_chart(story, rapor_verisi, normal_style):
    story.append(Paragraph("<b>4.2. Hedef vs Onaylı Proje Karşılaştırması</b>", normal_style))
    story.append(Spacer(1, 0.3 * cm))
    turler = list(HEDEF_PROJELER.keys())
    drawing = Drawing(700, 300)
    chart = VerticalBarChart()
    chart.x, chart.y, chart.height, chart.width = 50, 50, 200, 600
    chart.data = [
        [HEDEF_PROJELER[t] for t in turler],
        [rapor_verisi.onayli_projeler[t] for t in turler],
        [rapor_verisi.siemens_projeler[t] for t in turler],
    ]
    _configure_category_axis(chart, turler)
    chart.valueAxis.valueMin = 0
    chart.valueAxis.valueMax = max(HEDEF_PROJELER.values()) + 20
    chart.valueAxis.valueStep = 50
    chart.valueAxis.labels.fontName = "Helvetica"
    chart.valueAxis.labels.fontSize = 9
    chart.bars[0].fillColor = colors.HexColor("#4a7ba7")
    chart.bars[1].fillColor = colors.HexColor("#19a979")
    chart.bars[2].fillColor = colors.HexColor("#e8743b")
    chart.barSpacing, chart.groupSpacing, chart.barWidth = 2, 15, 15
    drawing.add(chart)

    legend = Legend()
    legend.x, legend.y = 50, 20
    legend.dx, legend.dy = 8, 8
    legend.fontName, legend.fontSize = "Helvetica", 9
    legend.boxAnchor, legend.columnMaximum, legend.alignment = "sw", 1, "right"
    legend.colorNamePairs = [
        (colors.HexColor("#4a7ba7"), "Hedef"),
        (colors.HexColor("#19a979"), "Onaylı"),
        (colors.HexColor("#e8743b"), "Siemens"),
    ]
    drawing.add(legend)
    story.append(drawing)
    story.append(Spacer(1, 1 * cm))


def _add_ratio_chart(story, rapor_verisi, normal_style):
    story.append(Paragraph("<b>4.3. Gerçekleşme Oranları (%)</b>", normal_style))
    story.append(Spacer(1, 0.3 * cm))
    turler = list(HEDEF_PROJELER.keys())
    drawing = Drawing(700, 300)
    chart = VerticalBarChart()
    chart.x, chart.y, chart.height, chart.width = 50, 50, 200, 600
    chart.data = [
        [rapor_verisi.oran_siemens_dahil[t] for t in turler],
        [rapor_verisi.oran_siemens_haric[t] for t in turler],
    ]
    _configure_category_axis(chart, turler)
    chart.valueAxis.valueMin = 0
    chart.valueAxis.valueMax = 100
    chart.valueAxis.valueStep = 10
    chart.valueAxis.labels.fontName = "Helvetica"
    chart.valueAxis.labels.fontSize = 9
    chart.valueAxis.labelTextFormat = "%d%%"
    chart.bars[0].fillColor = colors.HexColor("#2c5aa0")
    chart.bars[1].fillColor = colors.HexColor("#4a7ba7")
    chart.barSpacing, chart.groupSpacing, chart.barWidth = 3, 20, 20
    drawing.add(chart)

    legend = Legend()
    legend.x, legend.y = 50, 20
    legend.dx, legend.dy = 8, 8
    legend.fontName, legend.fontSize = "Helvetica", 9
    legend.boxAnchor, legend.columnMaximum, legend.alignment = "sw", 1, "right"
    legend.colorNamePairs = [
        (colors.HexColor("#2c5aa0"), "Oran (Siemens Dahil)"),
        (colors.HexColor("#4a7ba7"), "Oran (Siemens Hariç)"),
    ]
    drawing.add(legend)
    story.append(drawing)


def _configure_category_axis(chart, turler):
    chart.categoryAxis.categoryNames = turler
    chart.categoryAxis.labels.boxAnchor = "ne"
    chart.categoryAxis.labels.dx = 8
    chart.categoryAxis.labels.dy = -2
    chart.categoryAxis.labels.angle = 30
    chart.categoryAxis.labels.fontName = "Helvetica"
    chart.categoryAxis.labels.fontSize = 9


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
