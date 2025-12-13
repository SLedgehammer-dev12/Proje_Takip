"""
Unit conversion utilities.

Provides type-safe temperature and pressure conversions with comprehensive
unit support.
"""

from enum import Enum
from typing import Union

from natural_gas_g5.config.settings import config
from natural_gas_g5.core.exceptions import ValidationError


class TemperatureUnit(str, Enum):
    """Supported temperature units."""
    KELVIN = "K"
    CELSIUS = "°C"
    FAHRENHEIT = "°F"


class PressureUnit(str, Enum):
    """Supported pressure units."""
    KPA = "kPa"
    BAR_ABSOLUTE = "bar(a)"
    BAR_GAUGE = "bar(g)"
    PSI_ABSOLUTE = "psi(a)"
    PSI_GAUGE = "psi(g)"
    MPA = "MPa"
    ATM = "atm"
    PA = "Pa"


def convert_temperature_to_K(
    value: float,
    unit: Union[str, TemperatureUnit]
) -> float:
    """
    Convert temperature to Kelvin.
    
    Args:
        value: Temperature value in source unit
        unit: Source unit (K, °C, or °F)
        
    Returns:
        Temperature in Kelvin
        
    Raises:
        ValidationError: If unit is invalid or conversion fails
        
    Examples:
        >>> convert_temperature_to_K(25, "°C")
        298.15
        >>> convert_temperature_to_K(77, "°F")
        298.15
    """
    try:
        unit_str = unit.value if isinstance(unit, TemperatureUnit) else str(unit)
        
        if unit_str == "K" or unit_str == TemperatureUnit.KELVIN:
            return value
        elif unit_str == "°C" or unit_str == TemperatureUnit.CELSIUS:
            return value + 273.15
        elif unit_str == "°F" or unit_str == TemperatureUnit.FAHRENHEIT:
            return (value - 32) * 5 / 9 + 273.15
        else:
            raise ValidationError(
                "Sıcaklık Birimi",
                f"Geçersiz birim: '{unit_str}'. Kullanılabilir: K, °C, °F"
            )
    except Exception as e:
        if isinstance(e, ValidationError):
            raise
        raise ValidationError(
            "Sıcaklık Dönüşümü",
            f"Dönüşüm hatası: {str(e)}"
        )


def convert_temperature_from_K(
    value_k: float,
    target_unit: Union[str, TemperatureUnit]
) -> float:
    """
    Convert temperature from Kelvin to target unit.
    
    Args:
        value_k: Temperature in Kelvin
        target_unit: Target unit (K, °C, or °F)
        
    Returns:
        Temperature in target unit
        
    Examples:
        >>> convert_temperature_from_K(298.15, "°C")
        25.0
    """
    unit_str = target_unit.value if isinstance(target_unit, TemperatureUnit) else str(target_unit)
    
    if unit_str == "K" or unit_str == TemperatureUnit.KELVIN:
        return value_k
    elif unit_str == "°C" or unit_str == TemperatureUnit.CELSIUS:
        return value_k - 273.15
    elif unit_str == "°F" or unit_str == TemperatureUnit.FAHRENHEIT:
        return (value_k - 273.15) * 9 / 5 + 32
    else:
        raise ValidationError(
            "Sıcaklık Birimi",
            f"Geçersiz birim: '{unit_str}'"
        )


def convert_pressure_to_Pa(
    value: float,
    unit: Union[str, PressureUnit]
) -> float:
    """
    Convert pressure to Pascals.
    
    Args:
        value: Pressure value in source unit
        unit: Source unit (kPa, bar(a), bar(g), psi(a), psi(g), MPa, atm)
        
    Returns:
        Pressure in Pascals
        
    Raises:
        ValidationError: If unit is invalid
        
    Examples:
        >>> convert_pressure_to_Pa(101.325, "kPa")
        101325.0
        >>> convert_pressure_to_Pa(1, "bar(a)")
        100000.0
    """
    try:
        unit_str = unit.value if isinstance(unit, PressureUnit) else str(unit)
        
        if unit_str == "Pa" or unit_str == PressureUnit.PA:
            return value
        elif unit_str == "kPa" or unit_str == PressureUnit.KPA:
            return value * 1000
        elif unit_str == "bar(a)" or unit_str == PressureUnit.BAR_ABSOLUTE:
            return value * 1e5
        elif unit_str == "bar(g)" or unit_str == PressureUnit.BAR_GAUGE:
            return (value + config.P_ATM_BAR) * 1e5
        elif unit_str == "psi(a)" or unit_str == PressureUnit.PSI_ABSOLUTE:
            return value * 6894.76
        elif unit_str == "psi(g)" or unit_str == PressureUnit.PSI_GAUGE:
            return (value + config.P_ATM_PSI) * 6894.76
        elif unit_str == "MPa" or unit_str == PressureUnit.MPA:
            return value * 1e6
        elif unit_str == "atm" or unit_str == PressureUnit.ATM:
            return value * 101325.0
        else:
            raise ValidationError(
                "Basınç Birimi",
                f"Geçersiz birim: '{unit_str}'. Kullanılabilir: kPa, bar(a), bar(g), psi(a), psi(g), MPa, atm"
            )
    except Exception as e:
        if isinstance(e, ValidationError):
            raise
        raise ValidationError(
            "Basınç Dönüşümü",
            f"Dönüşüm hatası: {str(e)}"
        )


def convert_pressure_from_Pa(
    value_pa: float,
    target_unit: Union[str, PressureUnit]
) -> float:
    """
    Convert pressure from Pascals to target unit.
    
    Args:
        value_pa: Pressure in Pascals
        target_unit: Target unit
        
    Returns:
        Pressure in target unit
        
    Examples:
        >>> convert_pressure_from_Pa(101325, "bar(a)")
        1.01325
    """
    unit_str = target_unit.value if isinstance(target_unit, PressureUnit) else str(target_unit)
    
    if unit_str == "Pa" or unit_str == PressureUnit.PA:
        return value_pa
    elif unit_str == "kPa" or unit_str == PressureUnit.KPA:
        return value_pa / 1000
    elif unit_str == "bar(a)" or unit_str == PressureUnit.BAR_ABSOLUTE:
        return value_pa / 1e5
    elif unit_str == "bar(g)" or unit_str == PressureUnit.BAR_GAUGE:
        return value_pa / 1e5 - config.P_ATM_BAR
    elif unit_str == "psi(a)" or unit_str == PressureUnit.PSI_ABSOLUTE:
        return value_pa / 6894.76
    elif unit_str == "psi(g)" or unit_str == PressureUnit.PSI_GAUGE:
        return value_pa / 6894.76 - config.P_ATM_PSI
    elif unit_str == "MPa" or unit_str == PressureUnit.MPA:
        return value_pa / 1e6
    elif unit_str == "atm" or unit_str == PressureUnit.ATM:
        return value_pa / 101325.0
    else:
        raise ValidationError(
            "Basınç Birimi",
            f"Geçersiz birim: '{unit_str}'"
        )
