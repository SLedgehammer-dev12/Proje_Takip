"""
Input validation utilities.

Provides comprehensive validation for user inputs with detailed error messages.
"""

from typing import Optional, List

from natural_gas_g5.config.settings import config
from natural_gas_g5.core.exceptions import ValidationError


def validate_numeric_input(
    value_str: str,
    field_name: str,
    min_val: Optional[float] = None,
    max_val: Optional[float] = None,
    allow_zero: bool = True
) -> float:
    """
    Validate and convert numeric string input.
    
    Args:
        value_str: Input string to validate
        field_name: Name of the field (for error messages)
        min_val: Minimum allowed value (inclusive)
        max_val: Maximum allowed value (inclusive)
        allow_zero: Whether zero is allowed
        
    Returns:
        Validated numeric value
        
    Raises:
        ValidationError: If validation fails
        
    Examples:
        >>> validate_numeric_input("25.5", "Temperature", min_val=0, max_val=1000)
        25.5
        >>> validate_numeric_input("", "Pressure")
        Traceback (most recent call last):
        ...
        ValidationError: Pressure: Değer boş olamaz
    """
    # Check for empty input
    if not value_str.strip():
        raise ValidationError(field_name, "Değer boş olamaz.")
    
    # Try to convert to float (handle both comma and dot as decimal separator)
    try:
        value = float(value_str.replace(',', '.').strip())
    except ValueError:
        raise ValidationError(
            field_name,
            f"Geçerli bir sayı olmalıdır. Girilen: '{value_str}'"
        )
    
    # Check for zero (if not allowed)
    if not allow_zero and value == 0:
        raise ValidationError(field_name, "Değer sıfır olamaz.")
    
    # Check minimum value
    if min_val is not None and value < min_val:
        raise ValidationError(
            field_name,
            f"Değer {min_val}'den küçük olamaz. Girilen: {value}"
        )
    
    # Check maximum value
    if max_val is not None and value > max_val:
        raise ValidationError(
            field_name,
            f"Değer {max_val}'den büyük olamaz. Girilen: {value}"
        )
    
    return value


def validate_temperature(temperature_k: float) -> None:
    """
    Validate temperature value in Kelvin.
    
    Args:
        temperature_k: Temperature in Kelvin
        
    Raises:
        ValidationError: If temperature is out of valid range
    """
    if temperature_k <= config.MIN_TEMPERATURE:
        raise ValidationError(
            "Sıcaklık",
            f"Mutlak sıfıra çok yakın (≤ {config.MIN_TEMPERATURE}K)"
        )
    
    if temperature_k > config.MAX_TEMPERATURE:
        raise ValidationError(
            "Sıcaklık",
            f"Çok yüksek (> {config.MAX_TEMPERATURE}K)"
        )


def validate_pressure(pressure_pa: float) -> None:
    """
    Validate pressure value in Pascals.
    
    Args:
        pressure_pa: Pressure in Pascals
        
    Raises:
        ValidationError: If pressure is out of valid range
    """
    if pressure_pa <= 0:
        raise ValidationError("Basınç", "Pozitif olmalıdır.")
    
    if pressure_pa > config.MAX_PRESSURE:
        raise ValidationError(
            "Basınç",
            f"Çok yüksek (> {config.MAX_PRESSURE/1e5:.0f} bar)"
        )


def validate_volume(volume_m3: float) -> None:
    """
    Validate volume value in cubic meters.
    
    Args:
        volume_m3: Volume in m³
        
    Raises:
        ValidationError: If volume is out of valid range
    """
    if volume_m3 <= 0:
        raise ValidationError("Hacim", "Pozitif olmalıdır.")
    
    if volume_m3 > config.MAX_VOLUME:
        raise ValidationError(
            "Hacim",
            f"Çok büyük (> {config.MAX_VOLUME} m³)"
        )


def validate_gas_fraction(fraction: float) -> None:
    """
    Validate gas fraction percentage (0-100).
    
    Args:
        fraction: Gas fraction in percent (0-100)
        
    Raises:
        ValidationError: If fraction is out of valid range
    """
    if fraction <= 0 or fraction > 100:
        raise ValidationError(
            "Gaz Yüzdesi",
            f"0 ile 100 arasında olmalıdır. Girilen: {fraction}"
        )


def validate_total_fraction(fractions: List[float], tolerance: float = 1e-4) -> None:
    """
    Validate that gas fractions sum to 100%.
    
    Args:
        fractions: List of gas fractions in percent
        tolerance: Acceptable deviation from 100%
        
    Raises:
        ValidationError: If sum is not 100% within tolerance
    """
    total = sum(fractions)
    
    if abs(total - 100.0) > tolerance:
        raise ValidationError(
            "Gaz Kompozisyonu",
            f"Yüzdelerin toplamı 100 olmalıdır. Mevcut toplam: {total:.4f}%"
        )


def validate_backend(backend: str) -> None:
    """
    Validate thermodynamic backend selection.
    
    Args:
        backend: Backend name (e.g., "HEOS", "SRK", "PR")
        
    Raises:
        ValidationError: If backend is not supported
    """
    if backend not in config.AVAILABLE_BACKENDS:
        available = ", ".join(config.AVAILABLE_BACKENDS)
        raise ValidationError(
            "Hesaplama Yöntemi",
            f"Geçersiz backend: '{backend}'. Kullanılabilir: {available}"
        )


def validate_component_count(count: int) -> None:
    """
    Validate number of gas components.
    
    Args:
        count: Number of components
        
    Raises:
        ValidationError: If count exceeds limits
    """
    if count == 0:
        raise ValidationError(
            "Gaz Kompozisyonu",
            "En az bir gaz bileşeni eklenmelidir."
        )
    
    if count > config.MAX_COMPONENTS:
        raise ValidationError(
            "Gaz Kompozisyonu",
            f"Maksimum {config.MAX_COMPONENTS} gaz eklenebilir. Mevcut: {count}"
        )


def validate_gas_name(name: str, existing_names: Optional[List[str]] = None) -> None:
    """
    Validate gas component name.
    
    Args:
        name: Gas name to validate
        existing_names: List of already used gas names (for duplicate check)
        
    Raises:
        ValidationError: If name is invalid or duplicate
    """
    if not name or not name.strip():
        raise ValidationError("Gaz İsmi", "Boş olamaz.")
    
    # Check for duplicates (case-insensitive)
    if existing_names:
        name_lower = name.strip().lower()
        if name_lower in [g.lower() for g in existing_names]:
            raise ValidationError(
                "Gaz İsmi",
                f"'{name}' zaten listede. Aynı gaz birden fazla eklenemez."
            )
