"""
Result unit converter for displaying calculation results in different unit systems.

Handles conversion from SI (internal storage) to user-selected units.
"""

from typing import Dict
from enum import Enum


class UnitSystem(str, Enum):
    """Available unit systems for displaying results."""
    SI = "SI"
    IMPERIAL = "Imperial"
    MIXED = "Mixed"


# Conversion factors (from SI base units)
DENSITY_CONVERSIONS = {
    'kg/m³': 1.0,
    'lb/ft³': 0.062427961,  # 1 kg/m³ = 0.0624 lb/ft³
    'g/cm³': 0.001
}

ENERGY_MASS_CONVERSIONS = {
    'kJ/kg': 1.0,
    'Btu/lb': 0.429922614,  # 1 kJ/kg = 0.4299 Btu/lb
    'kcal/kg': 0.238845897
}

ENTROPY_CONVERSIONS = {
    'kJ/(kg·K)': 1.0,
    'Btu/(lb·°F)': 0.238845897,  # Same as energy_mass / temperature
    'Btu/(lb·R)': 0.238845897
}

SPEED_CONVERSIONS = {
    'm/s': 1.0,
    'ft/s': 3.28084,  # 1 m/s = 3.28084 ft/s
    'km/h': 3.6,
    'mph': 2.23694
}

HEATING_VALUE_MASS_CONVERSIONS = {
    'MJ/kg': 1.0,
    'Btu/lb': 429.922614,  # 1 MJ/kg = 429.92 Btu/lb
    'kcal/kg': 238.845897
}

HEATING_VALUE_VOLUME_CONVERSIONS = {
    'MJ/Sm³': 1.0,
    'Btu/SCF': 26.83910757,  # 1 MJ/Sm³ = 26.839 Btu/SCF
    'kcal/Sm³': 238.845897
}

VOLUME_CONVERSIONS = {
    'm³': 1.0,
    'ft³': 35.3146667,  # 1 m³ = 35.3147 ft³
    'L': 1000.0,
    'gal (US)': 264.172
}

MASS_CONVERSIONS = {
    'kg': 1.0,
    'lb': 2.20462262,  # 1 kg = 2.2046 lb
    'ton (metric)': 0.001,
    'ton (US)': 0.00110231
}


class ResultUnitConverter:
    """Converts calculation results to different unit systems."""
    
    @staticmethod
    def convert_density(value_kg_m3: float, target_unit: str = 'kg/m³') -> tuple:
        """
        Convert density from kg/m³ to target unit.
        
        Args:
            value_kg_m3: Density in kg/m³
            target_unit: Target unit string
            
        Returns:
            Tuple of (converted_value, unit_string)
        """
        if target_unit not in DENSITY_CONVERSIONS:
            return value_kg_m3, 'kg/m³'
        
        factor = DENSITY_CONVERSIONS[target_unit]
        return value_kg_m3 * factor, target_unit
    
    @staticmethod
    def convert_energy_mass(value_kj_kg: float, target_unit: str = 'kJ/kg') -> tuple:
        """
        Convert specific energy from kJ/kg to target unit.
        
        Args:
            value_kj_kg: Energy in kJ/kg
            target_unit: Target unit string
            
        Returns:
            Tuple of (converted_value, unit_string)
        """
        if target_unit not in ENERGY_MASS_CONVERSIONS:
            return value_kj_kg, 'kJ/kg'
        
        factor = ENERGY_MASS_CONVERSIONS[target_unit]
        return value_kj_kg * factor, target_unit
    
    @staticmethod
    def convert_entropy(value_kj_kg_k: float, target_unit: str = 'kJ/(kg·K)') -> tuple:
        """
        Convert specific entropy from kJ/(kg·K) to target unit.
        
        Args:
            value_kj_kg_k: Entropy in kJ/(kg·K)
            target_unit: Target unit string
            
        Returns:
            Tuple of (converted_value, unit_string)
        """
        if target_unit not in ENTROPY_CONVERSIONS:
            return value_kj_kg_k, 'kJ/(kg·K)'
        
        factor = ENTROPY_CONVERSIONS[target_unit]
        return value_kj_kg_k * factor, target_unit
    
    @staticmethod
    def convert_speed(value_m_s: float, target_unit: str = 'm/s') -> tuple:
        """
        Convert speed from m/s to target unit.
        
        Args:
            value_m_s: Speed in m/s
            target_unit: Target unit string
            
        Returns:
            Tuple of (converted_value, unit_string)
        """
        if target_unit not in SPEED_CONVERSIONS:
            return value_m_s, 'm/s'
        
        factor = SPEED_CONVERSIONS[target_unit]
        return value_m_s * factor, target_unit
    
    @staticmethod
    def convert_heating_value_mass(value_mj_kg: float, target_unit: str = 'MJ/kg') -> tuple:
        """
        Convert mass-based heating value from MJ/kg to target unit.
        
        Args:
            value_mj_kg: Heating value in MJ/kg
            target_unit: Target unit string
            
        Returns:
            Tuple of (converted_value, unit_string)
        """
        if target_unit not in HEATING_VALUE_MASS_CONVERSIONS:
            return value_mj_kg, 'MJ/kg'
        
        factor = HEATING_VALUE_MASS_CONVERSIONS[target_unit]
        return value_mj_kg * factor, target_unit
    
    @staticmethod
    def convert_heating_value_volume(value_mj_sm3: float, target_unit: str = 'MJ/Sm³') -> tuple:
        """
        Convert volume-based heating value from MJ/Sm³ to target unit.
        
        Args:
            value_mj_sm3: Heating value in MJ/Sm³
            target_unit: Target unit string
            
        Returns:
            Tuple of (converted_value, unit_string)
        """
        if target_unit not in HEATING_VALUE_VOLUME_CONVERSIONS:
            return value_mj_sm3, 'MJ/Sm³'
        
        factor = HEATING_VALUE_VOLUME_CONVERSIONS[target_unit]
        return value_mj_sm3 * factor, target_unit
    
    @staticmethod
    def convert_volume(value_m3: float, target_unit: str = 'm³') -> tuple:
        """
        Convert volume from m³ to target unit.
        
        Args:
            value_m3: Volume in m³
            target_unit: Target unit string
            
        Returns:
            Tuple of (converted_value, unit_string)
        """
        if target_unit not in VOLUME_CONVERSIONS:
            return value_m3, 'm³'
        
        factor = VOLUME_CONVERSIONS[target_unit]
        return value_m3 * factor, target_unit
    
    @staticmethod
    def convert_mass(value_kg: float, target_unit: str = 'kg') -> tuple:
        """
        Convert mass from kg to target unit.
        
        Args:
            value_kg: Mass in kg
            target_unit: Target unit string
            
        Returns:
            Tuple of (converted_value, unit_string)
        """
        if target_unit not in MASS_CONVERSIONS:
            return value_kg, 'kg'
        
        factor = MASS_CONVERSIONS[target_unit]
        return value_kg * factor, target_unit
    
    @staticmethod
    def get_unit_preferences(unit_system: UnitSystem) -> Dict[str, str]:
        """
        Get preferred units for a given unit system.
        
        Args:
            unit_system: Unit system enum
            
        Returns:
            Dictionary mapping property type to preferred unit
        """
        if unit_system == UnitSystem.SI:
            return {
                'density': 'kg/m³',
                'energy_mass': 'kJ/kg',
                'entropy': 'kJ/(kg·K)',
                'speed': 'm/s',
                'heating_value_mass': 'MJ/kg',
                'heating_value_volume': 'MJ/Sm³',
                'volume': 'm³',
                'mass': 'kg'
            }
        elif unit_system == UnitSystem.IMPERIAL:
            return {
                'density': 'lb/ft³',
                'energy_mass': 'Btu/lb',
                'entropy': 'Btu/(lb·°F)',
                'speed': 'ft/s',
                'heating_value_mass': 'Btu/lb',
                'heating_value_volume': 'Btu/SCF',
                'volume': 'ft³',
                'mass': 'lb'
            }
        else:  # MIXED
            return {
                'density': 'kg/m³',
                'energy_mass': 'kJ/kg',
                'entropy': 'kJ/(kg·K)',
                'speed': 'm/s',
                'heating_value_mass': 'Btu/lb',  # Imperial for heating
                'heating_value_volume': 'Btu/SCF',  # Imperial for heating
                'volume': 'm³',
                'mass': 'kg'
            }
