"""Excel Loader Service for proje_listesi.xlsx

This service loads and queries the master project list from Excel,
providing validation for uploaded projects.
"""

import logging
import os
from typing import Optional, Dict, Tuple
from pathlib import Path
from project_types import normalize_project_type


class ExcelLoaderService:
    """Service to load and query project data from proje_listesi.xlsx"""
    
    def __init__(self, excel_path: str = "proje_listesi.xlsx"):
        """Initialize the Excel loader service.
        
        Args:
            excel_path: Path to the Excel file (relative or absolute)
        """
        self.logger = logging.getLogger(__name__)
        self.excel_path = excel_path
        self._data_cache: Optional[Dict[str, Tuple[str, str]]] = None
        self._load_error: Optional[str] = None
        
    def _load_excel_data(self) -> Dict[str, Tuple[str, str]]:
        """Load Excel data and cache it.
        
        Returns:
            Dictionary mapping project codes to (project_type, project_name)
        """
        if self._data_cache is not None:
            return self._data_cache
            
        data = {}
        
        try:
            # Check if file exists
            if not os.path.exists(self.excel_path):
                self._load_error = f"Excel dosyası bulunamadı: {self.excel_path}"
                self.logger.warning(self._load_error)
                return data
            
            # Try using openpyxl first (more reliable for parsing)
            try:
                import openpyxl
                
                wb = openpyxl.load_workbook(self.excel_path, read_only=True, data_only=True)
                ws = wb.active
                
                # Read rows starting from row 2 (skip header row 1)
                for row_num, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
                    try:
                        # Expected columns: None, index, proje_turu, proje_kodu, proje_ismi
                        if len(row) < 5:
                            continue
                            
                        index_col = row[1]
                        proje_turu = row[2]
                        proje_kodu = row[3]
                        proje_ismi = row[4]
                        
                        # Skip empty rows
                        if not proje_kodu or proje_kodu is None:
                            continue
                            
                        # Clean up the data
                        proje_kodu = str(proje_kodu).strip()
                        proje_turu = normalize_project_type(proje_turu) or "-"
                        proje_ismi = str(proje_ismi).strip() if proje_ismi else "-"
                        
                        # Store in cache
                        data[proje_kodu] = (proje_turu, proje_ismi)
                        
                    except Exception as e:
                        self.logger.debug(f"Satır {row_num} atlandı: {e}")
                        continue
                
                wb.close()
                self.logger.info(f"Excel dosyası yüklendi: {len(data)} proje kaydı bulundu")
                
            except ImportError:
                # Fallback to pandas if openpyxl not available
                self.logger.debug("openpyxl bulunamadı, pandas kullanılıyor")
                import pandas as pd
                
                df = pd.read_excel(self.excel_path)
                
                # Assuming columns are: Unnamed:0, Unnamed:1 (index), Unnamed:2 (tür), Unnamed:3 (kod), Unnamed:4 (isim)
                for idx, row in df.iterrows():
                    try:
                        if len(row) < 5:
                            continue
                            
                        proje_kodu = row.iloc[3]  # 4th column (index 3)
                        proje_turu = row.iloc[2]  # 3rd column (index 2)
                        proje_ismi = row.iloc[4]  # 5th column (index 4)
                        
                        # Skip NaN values
                        if pd.isna(proje_kodu):
                            continue
                            
                        proje_kodu = str(proje_kodu).strip()
                        proje_turu = normalize_project_type(proje_turu) or "-"
                        proje_ismi = str(proje_ismi).strip() if not pd.isna(proje_ismi) else "-"
                        
                        data[proje_kodu] = (proje_turu, proje_ismi)
                        
                    except Exception as e:
                        self.logger.debug(f"Satır {idx} atlandı: {e}")
                        continue
                
                self.logger.info(f"Excel dosyası yüklendi (pandas): {len(data)} proje kaydı bulundu")
                
        except Exception as e:
            self._load_error = f"Excel dosyası yüklenirken hata: {str(e)}"
            self.logger.error(self._load_error, exc_info=True)
            
        # Cache the data
        self._data_cache = data
        return data
    
    def find_project(self, proje_kodu: str) -> Optional[Tuple[str, str]]:
        """Find a project by its code.
        
        Args:
            proje_kodu: Project code to search for
            
        Returns:
            Tuple of (project_type, project_name) if found, None otherwise
        """
        if not proje_kodu:
            return None
            
        data = self._load_excel_data()
        
        # Clean up the search key
        search_key = str(proje_kodu).strip()
        
        return data.get(search_key)
    
    def is_project_in_list(self, proje_kodu: str) -> bool:
        """Check if a project exists in the Excel list.
        
        Args:
            proje_kodu: Project code to check
            
        Returns:
            True if project is found, False otherwise
        """
        return self.find_project(proje_kodu) is not None
    
    def get_project_type(self, proje_kodu: str) -> Optional[str]:
        """Get the project type from Excel list.
        
        Args:
            proje_kodu: Project code to look up
            
        Returns:
            Project type if found, None otherwise
        """
        result = self.find_project(proje_kodu)
        if result:
            return result[0]
        return None
    
    def reload(self):
        """Force reload of Excel data (clear cache)"""
        self._data_cache = None
        self._load_error = None
        self.logger.info("Excel verisi yeniden yüklenecek")
        
    def get_load_error(self) -> Optional[str]:
        """Get the last load error if any.
        
        Returns:
            Error message if loading failed, None otherwise
        """
        # Trigger load if not already attempted
        if self._data_cache is None and self._load_error is None:
            self._load_excel_data()
        return self._load_error
    
    def is_loaded(self) -> bool:
        """Check if Excel data is successfully loaded.
        
        Returns:
            True if data is loaded, False otherwise
        """
        # Trigger load if not already attempted
        if self._data_cache is None and self._load_error is None:
            self._load_excel_data()
        return self._data_cache is not None and len(self._data_cache) > 0
