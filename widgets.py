# widgets.py

import fitz  # PyMuPDF
from PySide6.QtWidgets import QScrollArea, QTreeWidget, QTreeWidgetItem, QWidget, QVBoxLayout

# Qt, QObject, Signal, Slot, QThread importları yukarı taşındı ve düzenlendi
from PySide6.QtCore import Qt, QObject, Signal, Slot
from PySide6.QtGui import QImage, QPainter, QPixmap, QFont, QColor
import gc
import logging
import os

# Gerekli importlar eklendi
from models import ProjeModel
from typing import Optional

# YENİ (ADIM 4.2): Kategori ID rolünü ana pencereden kopyalıyoruz.
# Bu, main_window.py'deki KATEGORI_ID_ROL = Qt.UserRole + 1 tanımıyla eşleşir.
KATEGORI_ID_ROL = Qt.UserRole + 1

# =============================================================================
# ÖZEL WIDGET SINIFLARI
# =============================================================================


class KategoriAgaci(QTreeWidget):
    # --- GÜNCELLEME (ADIM 4.2) ---
    # Sinyal artık metin (str) yerine Kategori ID (int) gönderecek.
    # (int: proje_id, int: yeni_kategori_id)
    # 0 kategori_id'si "Kategorisiz" (NULL) anlamına gelecektir.
    projeTasindi = Signal(int, int)
    # --- GÜNCELLEME BİTTİ ---

    def __init__(self, parent):
        super().__init__(parent)
        # self.ana_pencere referansı kaldırıldı
        # self.ana_pencere = parent

    def _get_item_path(self, item: QTreeWidgetItem) -> str:
        """
        NOT: Bu fonksiyon artık sadece geriye dönük uyumluluk için
        (main_window.py'deki sağ tık -> yeni proje) kullanılmaktadır.
        Bu sınıfın kendisi (KategoriAgaci) artık bu fonksiyonu KULLANMAZ.
        """
        yol_parcalari = []
        gecerli_item = item
        while gecerli_item:
            if not gecerli_item.data(0, Qt.UserRole):  # Sadece kategori item'larını al
                yol_parcalari.insert(0, gecerli_item.text(0))
            gecerli_item = gecerli_item.parent()
        return "/".join(yol_parcalari)

    # --- GÜNCELLEME (ADIM 4.2) ---
    # dropEvent metodu, metin yolu ('hiyerarsi') yerine Kategori ID'si ile
    # çalışacak şekilde tamamen yeniden yazıldı.
    def dropEvent(self, event):
        target_item = self.itemAt(event.position().toPoint())
        dragged_items = self.selectedItems()

        if not dragged_items:
            event.ignore()
            return

        # Eğer bir projenin üzerine bırakıldıysa, onun üst kategorisini hedef al
        # (Bir projenin UserRole'ü dolu, kategori item'ınınki boştur)
        if target_item and target_item.data(0, Qt.UserRole) is not None:
            target_item = target_item.parent()

        yeni_kategori_id: Optional[int] = None

        if target_item:
            # Hedef item'ın Kategori ID'sini al
            # (Bu, Adım 2.2'de _hiyerarsik_projeleri_yukle_iliskisel'de ayarlandı)
            kategori_id_data = target_item.data(0, KATEGORI_ID_ROL)

            if kategori_id_data is not None:
                # Hedef bir kategori veya "Kategorisiz" (ID 0) item'ıdır.
                yeni_kategori_id = kategori_id_data
            else:
                # Bu durumun (kategori_id_data'nın None olması)
                # düzgün çalışan bir ağaçta olmaması gerekir.
                event.ignore()
                return
        else:
            # Ağacın boş bir alanına bırakıldı (root)
            # Bu işlemi görmezden geliyoruz.
            event.ignore()
            return

        # Sinyali ID ile gönder
        for item in dragged_items:
            proje_verisi: Optional[ProjeModel] = item.data(0, Qt.UserRole)
            if proje_verisi:
                # (int, int) sinyali gönderiliyor
                self.projeTasindi.emit(proje_verisi.id, yeni_kategori_id)

        event.accept()

    # --- GÜNCELLEME BİTTİ ---


class ZoomableScrollArea(QScrollArea):
    def __init__(self, parent_window):
        super().__init__()
        self.parent_window = parent_window  # Bu, AnaPencere'ye bir referanstır
        self.setWidgetResizable(True)
        self.setAlignment(Qt.AlignCenter)

    def wheelEvent(self, event):
        if event.modifiers() == Qt.ControlModifier:
            if event.angleDelta().y() > 0:
                self.parent_window.zoom_in()
            else:
                self.parent_window.zoom_out()
            event.accept()
        else:
            super().wheelEvent(event)


class PdfRenderWorker(QObject):
    # --- ÇÖKME DÜZELTMESİ (ADIM 5): Sinyallere rev_id (int) eklendi ---
    image_ready = Signal(QImage, int)
    # New: yazi_image_ready emits (image, yazi_no)
    yazi_image_ready = Signal(QImage, str)
    error = Signal(str, int)

    def __init__(self):
        super().__init__()
        # Önbellekleme mekanizması - aynı revizyonun tekrar render edilmesini önle
        self._last_rendered_id = None
        self._last_rendered_image = None
        self._max_cache_size = 5 * 1024 * 1024  # 5 MB max cache

    # --- ÇÖKME DÜZELTMESİ (ADIM 6): Slot'a rev_id (int) eklendi ---
    @Slot(bytes, float, int)
    def render_page(self, dokuman_verisi, zoom_factor, rev_id):
        """PDF sayfasını görüntüye dönüştür ve önbelleğe al - optimize edilmiş"""

        logger = logging.getLogger(__name__)
        logger.debug(f"PdfRenderWorker.render_page called for rev_id={rev_id}, zoom={zoom_factor}, dokuman_size={len(dokuman_verisi) if dokuman_verisi else 0}")

        # Aynı revizyon için önceki render varsa ve zoom aynıysa, cache'den döndür
        if (
            self._last_rendered_id == rev_id
            and self._last_rendered_image is not None
            and not self._last_rendered_image.isNull()
        ):
            # Cache kontrolü - bellek sınırını kontrol et
            image_size = self._last_rendered_image.sizeInBytes()
            if image_size < self._max_cache_size:
                logger.debug(f"PdfRenderWorker: returning cached image for rev_id={rev_id}")
                self.image_ready.emit(self._last_rendered_image, rev_id)
                return

        pdf_doc = None
        pix = None
        image = None

        try:
            # İşlem öncesi bellek temizliği - sadece gerektiğinde
            if (
                self._last_rendered_image
                and self._last_rendered_image.sizeInBytes() > 2 * 1024 * 1024
            ):
                self._last_rendered_image = None
                gc.collect()

            # PDF belgesini aç ve kontrol et
            pdf_doc = fitz.open(stream=dokuman_verisi, filetype="pdf")
            if not pdf_doc or pdf_doc.page_count == 0:
                raise ValueError("Geçersiz PDF belgesi")

            # Bellek kullanımını azaltmak için önizleme çözünürlüğünü optimize et
            # Büyük zoom faktörleri için kaliteyi koru, küçük için belleği koru
            if zoom_factor <= 1.0:
                preview_zoom = zoom_factor
            elif zoom_factor <= 2.0:
                preview_zoom = min(zoom_factor, 1.8)
            else:
                preview_zoom = 2.0

            pix = pdf_doc.load_page(0).get_pixmap(
                matrix=fitz.Matrix(preview_zoom, preview_zoom),
                alpha=False,  # Alpha kanalını devre dışı bırak
            )

            # PNG formatına dönüştürmeyi dene - daha hızlı
            try:
                png_bytes = (
                    pix.tobytes(output="png")
                    if hasattr(pix, "tobytes")
                    else pix.tobytes("png")
                )
                image = QImage.fromData(png_bytes)
                del png_bytes  # PNG verilerini hemen temizle
            except Exception:
                # PNG dönüşümü başarısız olursa doğrudan RGB formatını kullan
                image = QImage(
                    pix.samples, pix.width, pix.height, pix.stride, QImage.Format_RGB888
                )

            # Görüntü oluşturulamadıysa hata fırlat
            if image.isNull():
                raise ValueError("Görüntü oluşturulamadı")

            # Büyük görüntüleri ölçekle - akıllı boyutlandırma
            w, h = image.width(), image.height()
            max_dim = 3500  # Bellek optimizasyonu için düşürüldü

            if max(w, h) > max_dim:
                scale_factor = max_dim / max(w, h)
                new_w = max(1, int(w * scale_factor))
                new_h = max(1, int(h * scale_factor))
                # FastTransformation küçük zoom'larda, SmoothTransformation büyük zoom'larda
                transform = (
                    Qt.SmoothTransformation
                    if zoom_factor > 1.5
                    else Qt.FastTransformation
                )
                image = image.scaled(new_w, new_h, Qt.KeepAspectRatio, transform)

            # Cache'e kaydet
            if not image.isNull():
                self._last_rendered_id = rev_id
                self._last_rendered_image = image
                logger.debug(f"PdfRenderWorker: emitting image_ready for rev_id={rev_id}, size={image.width()}x{image.height()} bytes={image.sizeInBytes()}")
                self.image_ready.emit(image, rev_id)
            else:
                raise ValueError("Görüntü işleme başarısız")

        except Exception as e:
            # Hata durumunu bildir
            error_msg = f"PDF işleme hatası: {str(e)}"
            try:
                self.error.emit(error_msg, rev_id)
            except Exception:
                pass  # Hata bildirimi başarısız olursa sessizce devam et

        finally:
            # Kaynakları temizle
            try:
                if pix is not None:
                    del pix
                if pdf_doc is not None:
                    try:
                        pdf_doc.close()
                    except Exception:
                        pass
            except Exception:
                pass  # Temizlik hataları önemsiz

    def clear_cache(self):
        """Cache'i temizle"""
        self._last_rendered_id = None
        self._last_rendered_image = None
        gc.collect()

    @Slot(bytes, float, str)
    def render_yazi(self, dokuman_verisi, zoom_factor, yazi_no):
        """Render a yazi (incoming letter) document and emit image that contains the yazi number instead of rev id."""
        logger = logging.getLogger(__name__)
        logger.debug(f"PdfRenderWorker.render_yazi called for yazi_no={yazi_no}, zoom={zoom_factor}, dokuman_size={len(dokuman_verisi) if dokuman_verisi else 0}")

        try:
            if not dokuman_verisi:
                raise ValueError("Yazi document empty")
            pdf_doc = fitz.open(stream=dokuman_verisi, filetype="pdf")
            if not pdf_doc or pdf_doc.page_count == 0:
                raise ValueError("Geçersiz PDF belgesi")
            # Use the same preview_zoom logic as render_page
            if zoom_factor <= 1.0:
                preview_zoom = zoom_factor
            elif zoom_factor <= 2.0:
                preview_zoom = min(zoom_factor, 1.8)
            else:
                preview_zoom = 2.0

            pix = pdf_doc.load_page(0).get_pixmap(matrix=fitz.Matrix(preview_zoom, preview_zoom), alpha=False)
            try:
                png_bytes = (pix.tobytes(output="png") if hasattr(pix, "tobytes") else pix.tobytes("png"))
                image = QImage.fromData(png_bytes)
                del png_bytes
            except Exception:
                image = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format_RGB888)

            if image.isNull():
                raise ValueError("Görüntü oluşturulamadı")

            # Scale as needed
            w, h = image.width(), image.height()
            max_dim = 3500
            if max(w, h) > max_dim:
                scale_factor = max_dim / max(w, h)
                new_w = max(1, int(w * scale_factor))
                new_h = max(1, int(h * scale_factor))
                transform = (Qt.SmoothTransformation if zoom_factor > 1.5 else Qt.FastTransformation)
                image = image.scaled(new_w, new_h, Qt.KeepAspectRatio, transform)

            logger.debug(f"PdfRenderWorker: emitting yazi_image_ready for yazi_no={yazi_no}, size={image.width()}x{image.height()} bytes={image.sizeInBytes()}")
            self.yazi_image_ready.emit(image, yazi_no)
        except Exception as e:
            logger.error(f"Yazi render error: {e}", exc_info=True)
            try:
                self.error.emit(f"Yazi render error: {str(e)}", -1)
            except Exception:
                pass
        finally:
            try:
                if pix is not None:
                    del pix
                if pdf_doc is not None:
                    try:
                        pdf_doc.close()
                    except Exception:
                        pass
            except Exception:
                pass


# =============================================================================
# WATERMARK OVERLAY
# =============================================================================


class WatermarkOverlay(QScrollArea):
    """A transparent overlay that draws a centered, low-opacity watermark image (or text fallback).

    - Does not block mouse/keyboard (transparent for mouse events)
    - Automatically centers and scales the image
    - If image can't be loaded, draws a text fallback
    """

    def __init__(
        self,
        parent=None,
        image_path: Optional[str] = None,
        opacity: float = 0.08,
        scale_ratio: float = 0.35,
        alignment: Qt.AlignmentFlag = Qt.AlignCenter,
        margin: int = 24,
    ):
        super().__init__(parent)
        self.setFrameShape(QScrollArea.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setWidgetResizable(True)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        self.setStyleSheet("background: transparent;")

        self._opacity = max(0.0, min(opacity, 1.0))
        self._scale_ratio = max(0.05, min(scale_ratio, 0.9))
        self._alignment = alignment
        self._margin = max(0, margin)
        self._pixmap: Optional[QPixmap] = None
        self._image_path = image_path
        if image_path and os.path.exists(image_path):
            pm = QPixmap(image_path)
            if not pm.isNull():
                self._pixmap = pm

    def setImage(self, image_path: str):
        self._image_path = image_path
        pm = QPixmap(image_path)
        self._pixmap = pm if not pm.isNull() else None
        self.update()

    def setOpacity(self, opacity: float):
        self._opacity = max(0.0, min(opacity, 1.0))
        self.update()

    def _aligned_top_left(self, rect, size):
        margin = self._margin

        if self._alignment & Qt.AlignLeft:
            x = rect.left() + margin
        elif self._alignment & Qt.AlignRight:
            x = rect.right() - size.width() - margin
        else:
            x = rect.center().x() - size.width() // 2

        if self._alignment & Qt.AlignTop:
            y = rect.top() + margin
        elif self._alignment & Qt.AlignBottom:
            y = rect.bottom() - size.height() - margin
        else:
            y = rect.center().y() - size.height() // 2

        return x, y

    def paintEvent(self, event):
        # Transparent background
        painter = QPainter(self.viewport())
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
        painter.setOpacity(self._opacity)

        rect = self.viewport().rect()
        if self._pixmap and not self._pixmap.isNull():
            target_max = int(min(rect.width(), rect.height()) * self._scale_ratio)
            if target_max <= 0:
                return
            pm = self._pixmap
            scaled = pm.scaled(
                target_max, target_max, Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            x, y = self._aligned_top_left(rect, scaled.size())
            painter.drawPixmap(x, y, scaled)
        else:
            # Text fallback watermark
            painter.setOpacity(self._opacity)
            painter.setPen(QColor(0, 0, 0, int(255 * self._opacity)))
            font = QFont()
            font.setPointSize(max(16, int(min(rect.width(), rect.height()) * 0.04)))
            font.setBold(True)
            painter.setFont(font)
            text = "Proje Takip Sistemi"
            painter.drawText(rect.adjusted(self._margin, self._margin, -self._margin, -self._margin), self._alignment, text)
        painter.end()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Ensure we always cover the parent area
        if self.parent():
            self.setGeometry(self.parent().rect())


class WatermarkedPanelContainer(QWidget):
    """Wrap a content widget with a subtle non-interactive watermark overlay."""

    def __init__(
        self,
        content: QWidget,
        *,
        image_path: Optional[str] = None,
        opacity: float = 0.06,
        scale_ratio: float = 0.18,
        alignment: Qt.AlignmentFlag = Qt.AlignBottom | Qt.AlignRight,
        margin: int = 20,
        parent=None,
    ):
        super().__init__(parent)
        self._content = content
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(content)

        self._overlay = WatermarkOverlay(
            parent=self,
            image_path=image_path,
            opacity=opacity,
            scale_ratio=scale_ratio,
            alignment=alignment,
            margin=margin,
        )
        self._overlay.setGeometry(self.rect())
        self._overlay.raise_()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._overlay.setGeometry(self.rect())
