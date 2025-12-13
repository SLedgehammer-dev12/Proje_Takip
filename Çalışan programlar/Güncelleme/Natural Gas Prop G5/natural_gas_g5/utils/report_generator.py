"""
Report generation utilities.

Generates formatted text reports from calculation results with detailed logging.
"""

from datetime import datetime
from typing import Dict, Any, List, Tuple, Optional
from pathlib import Path
import logging
import os


class ReportGenerator:
    """Generates formatted text reports from calculation results."""
    
    @staticmethod
    def generate_text_report(
        input_params: Dict[str, Any],
        results: List[Tuple[str, str, str]],
        gas_composition: List[Tuple[str, float]],
        log_file: Optional[str] = None,
        include_full_log: bool = False
    ) -> str:
        """
        Generate formatted text report with timestamped log.
        
        Args:
            input_params: Dictionary with calculation inputs
                - temperature: str (with unit)
                - pressure: str (with unit)
                - backend: str
                - volume: Optional[str] (with unit)
                - fraction_type: str ("molar" or "mass")
            results: List of (property, value, unit) tuples
            gas_composition: List of (gas_name, fraction) tuples
            log_file: Optional path to log file for extracting calculation logs
            include_full_log: If True, include all recent log entries
            
        Returns:
            Formatted report as string
        """
        report_lines = []
        timestamp = datetime.now()
        
        # Header
        report_lines.append("=" * 90)
        report_lines.append(" TERMODİNAMİK GAZ KARIŞIMI HESAPLAMA RAPORU")
        report_lines.append(" Doğal Gaz Özellikleri G5 - Modüler Sürüm")
        report_lines.append(f" Rapor Tarihi: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append(f" Timestamp: {timestamp.isoformat()}")
        report_lines.append("=" * 90)
        report_lines.append("")
        
        # Input parameters
        report_lines.append("╔" + "═" * 88 + "╗")
        report_lines.append("║" + " GİRİLEN PARAMETRELER".center(88) + "║")
        report_lines.append("╚" + "═" * 88 + "╝")
        report_lines.append("")
        report_lines.append(f"  Sıcaklık           : {input_params.get('temperature', 'N/A')}")
        report_lines.append(f"  Basınç             : {input_params.get('pressure', 'N/A')}")
        report_lines.append(f"  Hesaplama Yöntemi  : {input_params.get('backend', 'N/A')}")
        
        if 'volume' in input_params and input_params['volume']:
            report_lines.append(f"  Hacim (ACM)        : {input_params['volume']} m³")
        
        fraction_type = input_params.get('fraction_type', 'molar')
        report_lines.append(f"  Kompozisyon Tipi   : {fraction_type.capitalize()}")
        report_lines.append("")
        
        # Gas composition
        report_lines.append("  Gaz Kompozisyonu:")
        report_lines.append("  " + "-" * 60)
        for gas_name, fraction in gas_composition:
            report_lines.append(f"    • {gas_name:<30s} : {fraction:>8.4f} %")
        report_lines.append("")
        
        # Results
        report_lines.append("╔" + "═" * 88 + "╗")
        report_lines.append("║" + " HESAPLAMA SONUÇLARI".center(88) + "║")
        report_lines.append("╚" + "═" * 88 + "╝")
        report_lines.append("")
        report_lines.append(f"  {'Özellik':<42} | {'Değer':<22} | {'Birim'}")
        report_lines.append("  " + "-" * 85)
        
        for prop, value, unit in results:
            if prop.startswith('-'):
                # Section header
                report_lines.append("")
                report_lines.append(f"  {prop}")
                report_lines.append("  " + "-" * 85)
            else:
                report_lines.append(f"  {prop:<42} | {value:<22} | {unit}")
        
        report_lines.append("")
        
        # Calculation Log Section
        report_lines.append("╔" + "═" * 88 + "╗")
        report_lines.append("║" + " HESAPLAMA LOG KAYDI (TIMESTAMP'Lİ)".center(88) + "║")
        report_lines.append("╚" + "═" * 88 + "╝")
        report_lines.append("")
        
        log_entries = ReportGenerator._get_calculation_log(log_file, include_full_log)
        
        if log_entries:
            report_lines.append("  Son Hesaplama İşlemlerinin Detaylı Kaydı:")
            report_lines.append("  " + "-" * 85)
            for entry in log_entries:
                report_lines.append(f"  {entry}")
        else:
            report_lines.append("  [Log kaydı bulunamadı veya okunamadı]")
        
        report_lines.append("")
        
        # Footer
        report_lines.append("=" * 90)
        report_lines.append(f"  Rapor Oluşturma Zamanı: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append("  Doğal Gaz Özellikleri G5 © 2025 Kompresör Pompa")
        report_lines.append("=" * 90)
        
        return "\n".join(report_lines)
    
    @staticmethod
    def _get_calculation_log(log_file: Optional[str], include_full: bool = False) -> List[str]:
        """
        Extract calculation log entries from log file.
        
        Args:
            log_file: Path to log file
            include_full: If True, include all recent entries; if False, filter calculation-related
            
        Returns:
            List of formatted log entries
        """
        if not log_file or not os.path.exists(log_file):
            return []
        
        try:
            with open(log_file, 'r', encoding='utf-8-sig') as f:
                lines = f.readlines()
            
            # Get last 50 lines or all lines
            recent_lines = lines[-50:] if len(lines) > 50 else lines
            
            # Filter for calculation-related entries if not including full log
            if not include_full:
                keywords = [
                    'Trying backend',
                    'Successfully calculated',
                    'failed',
                    'HHV',
                    'LHV',
                    'Component-based',
                    'Reference',
                    'Creating state',
                    'Backend',
                    'Heating',
                    'calculation'
                ]
                filtered_lines = [
                    line.strip() for line in recent_lines
                    if any(keyword in line for keyword in keywords)
                ]
                return filtered_lines[-20:]  # Last 20 relevant entries
            else:
                return [line.strip() for line in recent_lines]
                
        except Exception as e:
            return [f"[Log okuma hatası: {e}]"]
    
    @staticmethod
    def save_to_file(report_content: str, file_path: str) -> None:
        """
        Save report to file.
        
        Args:
            report_content: Report text content
            file_path: Path to save file
            
        Raises:
            IOError: If file cannot be written
        """
        try:
            with open(file_path, 'w', encoding='utf-8-sig') as f:
                f.write(report_content)
        except Exception as e:
            raise IOError(f"Rapor kaydedilemedi: {str(e)}")
    
    @staticmethod
    def generate_and_save(
        input_params: Dict[str, Any],
        results: List[Tuple[str, str, str]],
        gas_composition: List[Tuple[str, float]],
        file_path: str,
        log_file: Optional[str] = None
    ) -> None:
        """
        Generate report and save to file in one step.
        
        Args:
            input_params: Calculation inputs
            results: Calculation results
            gas_composition: Gas composition list
            file_path: Path to save file
            log_file: Optional log file path for including calculation logs
        """
        report = ReportGenerator.generate_text_report(
            input_params,
            results,
            gas_composition,
            log_file=log_file
        )
        ReportGenerator.save_to_file(report, file_path)

