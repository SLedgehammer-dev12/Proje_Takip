"""
Custom exception classes for the application.

Provides a hierarchy of exceptions for better error handling and debugging.
"""

from typing import List, Optional


class ThermoCalculationError(Exception):
    """Base exception for all thermodynamic calculation errors."""
    pass


class BackendNotAvailableError(ThermoCalculationError):
    """Raised when CoolProp or a specific backend is not available."""
    
    def __init__(self, backend: Optional[str] = None, message: Optional[str] = None):
        """
        Initialize backend error.
        
        Args:
            backend: Name of the unavailable backend (e.g., "HEOS", "CoolProp")
            message: Optional custom error message
        """
        self.backend = backend
        if message is None:
            if backend == "CoolProp":
                message = (
                    "CoolProp kütüphanesi yüklü değil. "
                    "Lütfen 'pip install CoolProp' komutuyla yükleyin."
                )
            elif backend:
                message = f"Backend '{backend}' kullanılamıyor."
            else:
                message = "İstenilen backend kullanılamıyor."
        super().__init__(message)


class MixtureCompatibilityError(ThermoCalculationError):
    """Raised when gas mixture is incompatible with selected backend."""
    
    def __init__(
        self,
        incompatible_gases: List[str],
        backend: str,
        message: Optional[str] = None
    ):
        """
        Initialize mixture compatibility error.
        
        Args:
            incompatible_gases: List of gases incompatible with backend
            backend: The backend name (e.g., "HEOS")
            message: Optional custom error message
        """
        self.incompatible_gases = incompatible_gases
        self.backend = backend
        
        if message is None:
            gases_str = ", ".join(incompatible_gases)
            message = (
                f"Seçilen gazlar ({gases_str}) {backend} backend'i ile "
                "uyumlu değil. Lütfen başka bir backend seçin (SRK veya PR)."
            )
        super().__init__(message)


class HeatingValueError(ThermoCalculationError):
    """Raised when heating value (HHV/LHV) calculation fails."""
    
    def __init__(self, component: Optional[str] = None, message: Optional[str] = None):
        """
        Initialize heating value error.
        
        Args:
            component: Gas component that failed (if applicable)
            message: Optional custom error message
        """
        self.component = component
        
        if message is None:
            if component:
                message = (
                    f"'{component}' için ısıl değer hesaplanamadı. "
                    "CoolProp verisinde bilgi eksik olabilir."
                )
            else:
                message = "Isıl değer hesaplanamadı."
        super().__init__(message)


class ValidationError(ThermoCalculationError):
    """Raised when input validation fails."""
    
    def __init__(self, field_name: str, message: str):
        """
        Initialize validation error.
        
        Args:
            field_name: Name of the field that failed validation
            message: Detailed error message
        """
        self.field_name = field_name
        super().__init__(f"{field_name}: {message}")


class CalculationConvergenceError(ThermoCalculationError):
    """Raised when calculation fails to converge."""
    
    def __init__(self, message: str = "Hesaplama yakınsamadı. Girdi değerlerini kontrol edin."):
        """
        Initialize convergence error.
        
        Args:
            message: Error description
        """
        super().__init__(message)


class StateUpdateError(ThermoCalculationError):
    """Raised when CoolProp state update fails."""
    
    def __init__(
        self,
        backend: str,
        temperature: float,
        pressure: float,
        original_error: Optional[Exception] = None
    ):
        """
        Initialize state update error.
        
        Args:
            backend: Backend used
            temperature: Temperature value (K)
            pressure: Pressure value (Pa)
            original_error: Original CoolProp exception
        """
        self.backend = backend
        self.temperature = temperature
        self.pressure = pressure
        self.original_error = original_error
        
        message = (
            f"CoolProp durumu güncellenemedi ({backend}). "
            f"T={temperature:.2f}K, P={pressure:.2f}Pa"
        )
        if original_error:
            message += f" | CoolProp hatası: {str(original_error)}"
        
        super().__init__(message)
