"""
Report service for handling Excel exports and PDF report generation.

This service encapsulates all reporting operations including Excel export
with statistics and PDF report generation.
"""

import logging
import re
import sys
import subprocess
from typing import Optional, Dict, Any, List
from datetime import datetime

from PySide6.QtWidgets import QFileDialog, QMessageBox, QProgressDialog, QWidget
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication


class ReportService:
    """
    Service class for report generation and Excel export operations.

    Handles creation of Excel exports with statistics and PDF reports.
    """

    def __init__(self, db, parent: Optional[QWidget] = None):
        """
        Initialize the ReportService.

        Args:
            db: Database instance
            parent: Parent widget for dialogs
        """
        self.db = db
        self.parent = parent
        self.logger = logging.getLogger(__name__)

    # Corporate color palette
    COLORS = {
        'primary': '#1a365d',      # Koyu mavi
        'secondary': '#2d4a6f',    # Orta mavi
        'approved': '#22c55e',     # Yeşil - Onaylı
        'noted': '#f59e0b',        # Turuncu - Notlu Onaylı
        'pending': '#3b82f6',      # Mavi - Bekleyen
        'rejected': '#ef4444',     # Kırmızı - Reddedilen
        'header_bg': '#1a365d',    # Header arka plan
        'header_fg': '#ffffff',    # Header yazı
        'alt_row': '#f8fafc',      # Alternatif satır
    }

    def _require_pandas(self):
        """Import pandas only when an Excel/report workflow actually needs it."""
        try:
            import pandas as pd
        except ImportError as e:
            self.logger.error(f"pandas yüklenemedi: {e}")
            QMessageBox.critical(
                self.parent,
                "Hata",
                "Excel raporu için pandas kütüphanesi gerekli.\n\n"
                "Lütfen bağımlılıkları yükleyin: pip install pandas",
            )
            raise
        return pd

    def export_to_excel(
        self,
        statistics_labels: Dict[str, Any],
        report_table=None,
        report_text_widget=None,
    ) -> bool:
        """
        Export project data to Excel with statistics, charts, and corporate styling.

        Args:
            statistics_labels: Dictionary of statistic labels
            report_table: Optional QTableWidget for project type data
            report_text_widget: Optional QTextEdit for project type data

        Returns:
            True if export was successful, False otherwise
        """
        save_path, _ = QFileDialog.getSaveFileName(
            self.parent,
            "Excel'e Aktar",
            "proje_listesi.xlsx",
            "Excel Dosyaları (*.xlsx)",
        )

        if not save_path:
            return False

        try:
            pd = self._require_pandas()
            # Get project data
            data = self.db.excel_verisi_getir()
            headers = [
                "Proje Kodu",
                "Proje İsmi",
                "Proje Türü",
                "Hiyerarşi",
                "Son Gelen Yazı No",
                "Son Gelen Yazı Tarihi",
                "Gelen Yazı Rev Kodu",
                "Son Giden Yazı No",
                "Son Giden Yazı Tarihi",
                "Giden Yazı Rev Kodu",
                "Son Revizyon Kodu",
                "Revizyon Durumu",
                "İşlem Beklenen",
                "Onaylı Doküman Revizyonu",
            ]
            df = pd.DataFrame(data, columns=headers)

            try:
                with pd.ExcelWriter(save_path, engine="xlsxwriter") as writer:
                    workbook = writer.book
                    
                    # Create corporate formats
                    formats = self._create_corporate_formats(workbook)
                    
                    # 1. Projects sheet with corporate styling
                    self._write_projects_sheet(writer, df, formats)
                    
                    # 2. Dashboard sheet with charts
                    self._write_dashboard_sheet(writer, statistics_labels, report_table, formats)
                    
                    # 3. Trend Analysis sheet with line chart
                    self._write_trend_sheet(writer, formats)

            except ImportError:
                self.logger.critical(
                    "xlsxwriter kurulu değil. Düz Excel aktarımı yapılıyor."
                )
                df.to_excel(save_path, index=False)
            except Exception as e:
                self.logger.critical(f"Excel (xlsxwriter) yazma hatası: {e}")
                df.to_excel(save_path, index=False)

            QMessageBox.information(
                self.parent, "Başarılı", "Veriler başarıyla Excel'e aktarıldı.\n\nGösterge Paneli ve Trend Analizi sayfalarında grafikler bulunmaktadır."
            )
            return True

        except Exception as e:
            self.logger.critical(f"Excel aktarım hatası: {e}", exc_info=True)
            QMessageBox.critical(
                self.parent, "Hata", f"Excel'e aktarma sırasında bir hata oluştu: {e}"
            )
            return False

    def export_revision_tracking_to_excel(self) -> bool:
        """Export revision tracking notes/signals to Excel."""
        save_path, _ = QFileDialog.getSaveFileName(
            self.parent,
            "Takip Listesini Excel'e Aktar",
            "revizyon_takip_listesi.xlsx",
            "Excel Dosyaları (*.xlsx)",
        )
        if not save_path:
            return False

        try:
            pd = self._require_pandas()
            data = self.db.takip_listesi_excel_verisi_getir(sadece_aktif=True)
            if not data:
                QMessageBox.information(
                    self.parent,
                    "Bilgi",
                    "Excel'e aktarılacak aktif takip kaydı bulunamadı.",
                )
                return False

            headers = [
                "Proje Kodu",
                "Proje İsmi",
                "Proje Türü",
                "Revizyon Kodu",
                "Revizyon Durumu",
                "Yazı No",
                "Yazı Tarihi",
                "Takip Notu",
                "Takip Durumu",
                "İşaretleme Tarihi",
                "Son Güncelleme",
                "Kapanış Tarihi",
            ]
            df = pd.DataFrame(data, columns=headers)
            df.to_excel(save_path, index=False)
            QMessageBox.information(
                self.parent,
                "Başarılı",
                f"Takip listesi Excel'e aktarıldı:\n{save_path}",
            )
            return True
        except Exception as e:
            self.logger.error(f"Takip listesi Excel aktarımı hatası: {e}", exc_info=True)
            QMessageBox.critical(
                self.parent,
                "Hata",
                f"Takip listesi Excel'e aktarılırken hata oluştu: {e}",
            )
            return False

    def _get_database_statistics(self) -> Dict[str, int]:
        """Get all statistics directly from database."""
        try:
            # Get project count
            self.db.cursor.execute("SELECT COUNT(*) FROM projeler")
            toplam = self.db.cursor.fetchone()[0] or 0
            
            # Get status counts from latest revisions
            # Note: Durum enum values are: Onayli, Onaysiz, Notlu Onayli, Reddedildi
            query = """
            SELECT 
                SUM(CASE WHEN r.durum = 'Onayli' THEN 1 ELSE 0 END) as onayli,
                SUM(CASE WHEN r.durum = 'Notlu Onayli' THEN 1 ELSE 0 END) as notlu,
                SUM(CASE WHEN r.durum = 'Reddedildi' THEN 1 ELSE 0 END) as red,
                SUM(CASE WHEN r.durum = 'Onaysiz' OR r.durum IS NULL THEN 1 ELSE 0 END) as bekleyen
            FROM projeler p
            LEFT JOIN revizyonlar r ON p.id = r.proje_id 
                AND r.id = (
                    SELECT id FROM revizyonlar WHERE proje_id = p.id 
                    ORDER BY proje_rev_no DESC, id DESC LIMIT 1
                )
            """
            self.db.cursor.execute(query)
            row = self.db.cursor.fetchone()
            
            return {
                'toplam': toplam,
                'onayli': row[0] or 0,
                'notlu': row[1] or 0,
                'red': row[2] or 0,
                'bekleyen': row[3] or 0,
            }
        except Exception as e:
            self.logger.error(f"İstatistik alınamadı: {e}")
            return {
                'toplam': 0, 'onayli': 0, 'notlu': 0, 
                'red': 0, 'bekleyen': 0
            }

    def _create_corporate_formats(self, workbook):
        """Create corporate styled formats."""
        formats = {}
        
        # Title format
        formats['title'] = workbook.add_format({
            'bold': True,
            'font_size': 16,
            'font_color': self.COLORS['primary'],
            'align': 'left',
            'valign': 'vcenter',
        })
        
        # Subtitle format
        formats['subtitle'] = workbook.add_format({
            'bold': True,
            'font_size': 12,
            'font_color': self.COLORS['secondary'],
            'align': 'left',
        })
        
        # Header format
        formats['header'] = workbook.add_format({
            'bold': True,
            'font_size': 11,
            'font_color': self.COLORS['header_fg'],
            'bg_color': self.COLORS['header_bg'],
            'border': 1,
            'align': 'center',
            'valign': 'vcenter',
            'text_wrap': True,
        })
        
        # Data formats
        formats['data'] = workbook.add_format({
            'font_size': 10,
            'border': 1,
            'align': 'left',
            'valign': 'vcenter',
        })
        
        formats['data_alt'] = workbook.add_format({
            'font_size': 10,
            'border': 1,
            'bg_color': self.COLORS['alt_row'],
            'align': 'left',
            'valign': 'vcenter',
        })
        
        formats['data_center'] = workbook.add_format({
            'font_size': 10,
            'border': 1,
            'align': 'center',
            'valign': 'vcenter',
        })
        
        # Status formats
        formats['approved'] = workbook.add_format({
            'font_size': 10,
            'border': 1,
            'font_color': self.COLORS['approved'],
            'bold': True,
            'align': 'center',
        })
        
        formats['noted'] = workbook.add_format({
            'font_size': 10,
            'border': 1,
            'font_color': self.COLORS['noted'],
            'bold': True,
            'align': 'center',
        })
        
        formats['rejected'] = workbook.add_format({
            'font_size': 10,
            'border': 1,
            'font_color': self.COLORS['rejected'],
            'bold': True,
            'align': 'center',
        })
        
        formats['pending'] = workbook.add_format({
            'font_size': 10,
            'border': 1,
            'font_color': self.COLORS['pending'],
            'align': 'center',
        })
        
        # Number format
        formats['number'] = workbook.add_format({
            'font_size': 11,
            'bold': True,
            'align': 'center',
            'valign': 'vcenter',
        })
        
        return formats

    def _write_projects_sheet(self, writer, df, formats):
        """Write projects sheet with corporate styling."""
        pd = self._require_pandas()
        sheet_name = "Projeler"
        df.to_excel(writer, index=False, sheet_name=sheet_name, startrow=2)
        worksheet = writer.sheets[sheet_name]
        
        # Title
        worksheet.write('A1', 'PROJE TAKİP SİSTEMİ - PROJE LİSTESİ', formats['title'])
        worksheet.write('A2', f'Oluşturulma: {datetime.now().strftime("%d.%m.%Y %H:%M")}', formats['subtitle'])
        
        # Apply header format
        for col_num, header in enumerate(df.columns):
            worksheet.write(2, col_num, header, formats['header'])
        
        # Apply data formatting with conditional status colors
        for row_num in range(len(df)):
            excel_row = row_num + 3  # Account for title rows
            row_format = formats['data_alt'] if row_num % 2 == 0 else formats['data']
            
            for col_num, col_name in enumerate(df.columns):
                value = df.iloc[row_num, col_num]
                value = "" if pd.isna(value) else value
                
                # Apply status-specific formatting for "Revizyon Durumu" column
                # Durum enum values: Onayli, Notlu Onayli, Reddedildi, Onaysiz
                if col_name == "Revizyon Durumu":
                    if value == "Onayli":
                        worksheet.write(excel_row, col_num, value, formats['approved'])
                    elif value == "Notlu Onayli":
                        worksheet.write(excel_row, col_num, value, formats['noted'])
                    elif value == "Reddedildi":
                        worksheet.write(excel_row, col_num, value, formats['rejected'])
                    else:
                        worksheet.write(excel_row, col_num, value, formats['pending'])
                else:
                    worksheet.write(excel_row, col_num, value, row_format)
        
        # Auto-adjust column widths
        for i, col in enumerate(df.columns):
            max_len_data = df[col].astype(str).map(len).max()
            if pd.isna(max_len_data):
                max_len_data = 0
            column_len = max(max_len_data, len(col)) + 2
            worksheet.set_column(i, i, min(column_len, 50))
        
        # Freeze top rows
        worksheet.freeze_panes(3, 0)

    def _write_dashboard_sheet(self, writer, statistics_labels, report_table, formats):
        """Write dashboard sheet with statistics and bar chart."""
        sheet_name = "Gösterge Paneli"
        workbook = writer.book
        worksheet = workbook.add_worksheet(sheet_name)
        
        # Title
        worksheet.write('A1', 'PROJE TAKİP SİSTEMİ - GÖSTERGE PANELİ', formats['title'])
        worksheet.write('A2', f'Rapor Tarihi: {datetime.now().strftime("%d.%m.%Y %H:%M")}', formats['subtitle'])
        
        # Get statistics directly from database
        stats = self._get_database_statistics()
        
        # General statistics section
        worksheet.write('A4', 'Genel İstatistikler', formats['subtitle'])
        
        general_labels = [
            'Toplam Sunulan Proje',
            'Onaylı Projeler',
            'Notlu Onaylı Projeler',
            'Reddedilen Projeler',
            'Beklemede (Onaysız) Projeler',
        ]
        
        general_values = [
            stats['toplam'],
            stats['onayli'],
            stats['notlu'],
            stats['red'],
            stats['bekleyen'],
        ]
        
        row = 5
        for i, (label, value) in enumerate(zip(general_labels, general_values)):
            worksheet.write(row + i, 0, label, formats['data'])
            worksheet.write(row + i, 1, value, formats['number'])
        
        # Project type statistics with chart
        worksheet.write('D4', 'Proje Türü Dağılımı', formats['subtitle'])
        
        # Get project type data from database
        type_stats = self.db.get_project_type_statistics()
        
        if type_stats:
            # Write headers
            type_headers = ['Proje Türü', 'Toplam', 'Onaylı', 'Notlu', 'Reddedilen', 'Bekleyen']
            for col, header in enumerate(type_headers):
                worksheet.write(4, 3 + col, header, formats['header'])
            
            # Write data
            for row_idx, row_data in enumerate(type_stats):
                for col_idx, value in enumerate(row_data):
                    worksheet.write(5 + row_idx, 3 + col_idx, value, formats['data_center'])
            
            # Create bar chart
            chart = workbook.add_chart({'type': 'column'})
            
            data_end_row = 5 + len(type_stats) - 1
            
            # Add series for each status
            chart.add_series({
                'name': 'Onaylı',
                'categories': [sheet_name, 5, 3, data_end_row, 3],
                'values': [sheet_name, 5, 5, data_end_row, 5],
                'fill': {'color': self.COLORS['approved']},
            })
            chart.add_series({
                'name': 'Notlu Onaylı',
                'categories': [sheet_name, 5, 3, data_end_row, 3],
                'values': [sheet_name, 5, 6, data_end_row, 6],
                'fill': {'color': self.COLORS['noted']},
            })
            chart.add_series({
                'name': 'Reddedilen',
                'categories': [sheet_name, 5, 3, data_end_row, 3],
                'values': [sheet_name, 5, 7, data_end_row, 7],
                'fill': {'color': self.COLORS['rejected']},
            })
            chart.add_series({
                'name': 'Bekleyen',
                'categories': [sheet_name, 5, 3, data_end_row, 3],
                'values': [sheet_name, 5, 8, data_end_row, 8],
                'fill': {'color': self.COLORS['pending']},
            })
            
            chart.set_title({'name': 'Proje Türlerine Göre Durum Dağılımı', 'name_font': {'color': self.COLORS['primary'], 'bold': True}})
            chart.set_x_axis({'name': 'Proje Türü'})
            chart.set_y_axis({'name': 'Proje Sayısı'})
            chart.set_legend({'position': 'bottom'})
            chart.set_size({'width': 600, 'height': 350})
            
            worksheet.insert_chart('D15', chart)
        
        # Set column widths
        worksheet.set_column('A:A', 30)
        worksheet.set_column('B:B', 12)
        worksheet.set_column('D:D', 18)
        worksheet.set_column('E:I', 12)

    def _write_trend_sheet(self, writer, formats):
        """Write trend analysis sheet with line chart."""
        sheet_name = "Trend Analizi"
        workbook = writer.book
        worksheet = workbook.add_worksheet(sheet_name)
        
        # Title
        worksheet.write('A1', 'PROJE TAKİP SİSTEMİ - TREND ANALİZİ', formats['title'])
        worksheet.write('A2', 'Son 12 Aylık Revizyon İstatistikleri', formats['subtitle'])
        
        # Get trend data
        trend_data = self.db.get_approval_trend_data()
        
        if trend_data:
            # Write headers
            headers = ['Ay', 'Onaylı', 'Notlu Onaylı', 'Reddedilen', 'Toplam']
            for col, header in enumerate(headers):
                worksheet.write(3, col, header, formats['header'])
            
            # Write data
            for row_idx, row_data in enumerate(trend_data):
                for col_idx, value in enumerate(row_data):
                    worksheet.write(4 + row_idx, col_idx, value, formats['data_center'])
            
            data_end_row = 4 + len(trend_data) - 1
            
            # Create line chart
            chart = workbook.add_chart({'type': 'line'})
            
            chart.add_series({
                'name': 'Onaylı',
                'categories': [sheet_name, 4, 0, data_end_row, 0],
                'values': [sheet_name, 4, 1, data_end_row, 1],
                'line': {'color': self.COLORS['approved'], 'width': 2.5},
                'marker': {'type': 'circle', 'fill': {'color': self.COLORS['approved']}},
            })
            chart.add_series({
                'name': 'Notlu Onaylı',
                'categories': [sheet_name, 4, 0, data_end_row, 0],
                'values': [sheet_name, 4, 2, data_end_row, 2],
                'line': {'color': self.COLORS['noted'], 'width': 2.5},
                'marker': {'type': 'square', 'fill': {'color': self.COLORS['noted']}},
            })
            chart.add_series({
                'name': 'Reddedilen',
                'categories': [sheet_name, 4, 0, data_end_row, 0],
                'values': [sheet_name, 4, 3, data_end_row, 3],
                'line': {'color': self.COLORS['rejected'], 'width': 2.5},
                'marker': {'type': 'diamond', 'fill': {'color': self.COLORS['rejected']}},
            })
            
            chart.set_title({'name': 'Aylık Revizyon Onay Trendi', 'name_font': {'color': self.COLORS['primary'], 'bold': True}})
            chart.set_x_axis({'name': 'Tarih'})
            chart.set_y_axis({'name': 'Revizyon Sayısı'})
            chart.set_legend({'position': 'bottom'})
            chart.set_size({'width': 700, 'height': 400})
            
            worksheet.insert_chart('A' + str(data_end_row + 3), chart)
        else:
            worksheet.write('A4', 'Trend verisi bulunamadı. Revizyonlara tarih bilgisi eklendiğinde grafik oluşturulacaktır.', formats['data'])
        
        # Set column widths
        worksheet.set_column('A:E', 15)

    def _prepare_general_statistics(
        self, statistics_labels: Dict[str, Any]
    ) -> Dict[str, List]:
        """Prepare general statistics data."""
        return {
            "Özet Durum": [
                "Toplam Görüntülenen Proje",
                "Onaylı Projeler",
                "Reddedilen Projeler",
                "Onaysız (Beklemede) Projeler",
            ],
            "Sayı": [
                (
                    statistics_labels.get("Toplam Görüntülenen Proje:", None).text()
                    if statistics_labels.get("Toplam Görüntülenen Proje:")
                    else "0"
                ),
                (
                    statistics_labels.get("Onaylı:", None).text()
                    if statistics_labels.get("Onaylı:")
                    else "0"
                ),
                (
                    statistics_labels.get("Reddedilen:", None).text()
                    if statistics_labels.get("Reddedilen:")
                    else "0"
                ),
                (
                    statistics_labels.get("Beklemede (Onaysız):", None).text()
                    if statistics_labels.get("Beklemede (Onaysız):")
                    else "0"
                ),
            ],
        }

    def _prepare_tse_statistics(
        self, statistics_labels: Dict[str, Any]
    ) -> Dict[str, List]:
        """Prepare TSE statistics data."""
        return {
            "TSE Durumu": ["TSE'ye Gönderilen", "Henüz Gönderilmeyen"],
            "Sayı": [
                (
                    statistics_labels.get("TSE'ye Gönderilen:", None).text()
                    if statistics_labels.get("TSE'ye Gönderilen:")
                    else "0"
                ),
                (
                    statistics_labels.get("Henüz Gönderilmeyen:", None).text()
                    if statistics_labels.get("Henüz Gönderilmeyen:")
                    else "0"
                ),
            ],
        }

    def _prepare_type_statistics(
        self, report_table=None, report_text_widget=None
    ) -> Any:
        """Prepare project type statistics data."""
        pd = self._require_pandas()
        type_data_processed = []

        # Prefer table data if available
        if report_table:
            try:
                row_count = report_table.rowCount()
                for r in range(row_count):
                    type_name = (
                        report_table.item(r, 0).text()
                        if report_table.item(r, 0)
                        else ""
                    )
                    total = (
                        int(report_table.item(r, 1).text())
                        if report_table.item(r, 1)
                        and report_table.item(r, 1).text().isdigit()
                        else 0
                    )
                    approved = (
                        int(report_table.item(r, 2).text())
                        if report_table.item(r, 2)
                        and report_table.item(r, 2).text().isdigit()
                        else 0
                    )
                    noted = (
                        int(report_table.item(r, 3).text())
                        if report_table.item(r, 3)
                        and report_table.item(r, 3).text().isdigit()
                        else 0
                    )
                    rejected = (
                        int(report_table.item(r, 4).text())
                        if report_table.item(r, 4)
                        and report_table.item(r, 4).text().isdigit()
                        else 0
                    )
                    type_data_processed.append(
                        [type_name, total, approved, noted, rejected]
                    )
            except Exception:
                pass
        elif report_text_widget:
            # Parse from text widget
            type_data_raw = report_text_widget.toPlainText().split("\n")
            for line in type_data_raw:
                if ":" in line:
                    parts = line.split(":", 1)
                    type_name = parts[0].strip()
                    numbers = re.findall(r"(\d+)", line)

                    if len(numbers) >= 4:
                        total, approved, noted, rejected = [int(n) for n in numbers[:4]]
                    elif len(numbers) == 1:
                        total = int(numbers[0])
                        approved = noted = rejected = 0
                    else:
                        total = approved = noted = rejected = 0

                    type_data_processed.append(
                        [type_name, total, approved, noted, rejected]
                    )

        return pd.DataFrame(
            type_data_processed,
            columns=["Proje Türü", "Sayı", "Onaylı", "Notlu Onaylı", "Reddedilen"],
        )

    def generate_pdf_report(self) -> bool:
        """
        Generate PDF report for projects.

        Returns:
            True if report was generated successfully, False otherwise
        """
        try:
            from rapor import rapor_olustur as rapor_olustur_func, REPORTLAB_AVAILABLE

            if not REPORTLAB_AVAILABLE:
                QMessageBox.critical(
                    self.parent,
                    "Hata",
                    "ReportLab kütüphanesi yüklü değil!\n\n"
                    "PDF raporu oluşturmak için ReportLab kütüphanesini yükleyin:\n"
                    "pip install reportlab",
                )
                return False

            # Get file path from user
            file_path, _ = QFileDialog.getSaveFileName(
                self.parent,
                "Rapor Kaydet",
                f"Proje_Raporu_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                "PDF Dosyaları (*.pdf)",
            )

            if not file_path:
                return False  # User cancelled

            self.logger.info(f"Rapor oluşturuluyor: {file_path}")

            # Show progress dialog
            progress = QProgressDialog(
                "Rapor oluşturuluyor...", "İptal", 0, 0, self.parent
            )
            progress.setWindowModality(Qt.WindowModal)
            progress.setMinimumDuration(0)
            progress.setValue(0)
            QApplication.processEvents()

            # Generate report
            success = rapor_olustur_func(self.db.db_adi, file_path)

            progress.close()

            if success:
                # Ask user if they want to open the report
                answer = QMessageBox.information(
                    self.parent,
                    "Rapor Oluşturuldu",
                    f"PDF raporu başarıyla oluşturuldu:\n\n{file_path}\n\n"
                    "Raporu şimdi açmak ister misiniz?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.Yes,
                )

                # Open file if user chose yes
                if answer == QMessageBox.Yes:
                    self._open_file(file_path)

                self.logger.info("Rapor başarıyla oluşturuldu")
                return True
            else:
                QMessageBox.warning(
                    self.parent,
                    "Hata",
                    "Rapor oluşturulurken bir hata oluştu.\n"
                    "Lütfen log dosyasını kontrol edin.",
                )
                self.logger.error("Rapor oluşturulamadı")
                return False

        except ImportError as e:
            self.logger.error(f"Rapor modülü import hatası: {e}")
            QMessageBox.critical(
                self.parent,
                "Hata",
                f"Rapor modülü yüklenemedi:\n{e}\n\n"
                "Lütfen rapor.py dosyasının mevcut olduğundan emin olun.",
            )
            return False
        except Exception as e:
            self.logger.error(f"Rapor oluşturma hatası: {e}", exc_info=True)
            QMessageBox.critical(self.parent, "Hata", f"Rapor oluşturma hatası:\n{e}")
            return False

    def _open_file(self, file_path: str):
        """Open a file with the system default application."""
        try:
            if sys.platform == "win32":
                import os

                os.startfile(file_path)
            elif sys.platform == "darwin":
                subprocess.run(["open", file_path])
            else:
                subprocess.run(["xdg-open", file_path])
        except Exception as e:
            self.logger.warning(f"Dosya açılamadı: {e}")
