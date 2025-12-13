"""
Reference heating values database.

Provides fallback heating values for common natural gas components
when CoolProp data is unavailable.
"""

from typing import Dict, Tuple, Optional


# Reference heating values at standard conditions (15°C, 101.325 kPa)
# Format: {gas_name: (HHV_MJ_per_kg, LHV_MJ_per_kg)}
# Source: Engineering Toolbox, GPSA Engineering Data Book, ISO 6976

REFERENCE_HEATING_VALUES: Dict[str, Tuple[float, float]] = {
    # Alkanes
    "Methane": (55.50, 50.01),
    "Ethane": (51.90, 47.51),
    "Propane": (50.36, 46.37),
    "n-Butane": (49.52, 45.75),
    "Isobutane": (49.36, 45.61),
    "n-Pentane": (49.01, 45.36),
    "Isopentane": (48.94, 45.24),
    "n-Hexane": (48.68, 45.10),
    "n-Heptane": (48.48, 44.93),
    "n-Octane": (48.32, 44.79),
    "n-Nonane": (48.19, 44.68),
    "n-Decane": (48.10, 44.60),
    
    # Alkenes
    "Ethylene": (50.30, 47.16),
    "Propylene": (48.95, 45.78),
    "1-Butene": (48.45, 45.33),
    
    # Aromatics
    "Benzene": (41.85, 40.17),
    "Toluene": (42.44, 40.53),
    
    # Other hydrocarbons
    "Acetylene": (49.91, 48.23),
    
    # Non-combustible (zero heating value)
    "Nitrogen": (0.0, 0.0),
    "CarbonDioxide": (0.0, 0.0),
    "Oxygen": (0.0, 0.0),
    "Argon": (0.0, 0.0),
    "Helium": (0.0, 0.0),
    "Water": (0.0, 0.0),
    "Air": (0.0, 0.0),
    
    # Combustible special cases
    "Hydrogen": (141.80, 119.96),  # Very high heating value
    "CarbonMonoxide": (10.10, 10.10),  # Same HHV and LHV (no H2O formed)
    "HydrogenSulfide": (15.24, 13.98),  # Toxic, but combustible
}


def get_reference_heating_values(gas_name: str) -> Optional[Tuple[float, float]]:
    """
    Get reference heating values for a gas.
    
    Args:
        gas_name: Gas component name
        
    Returns:
        Tuple of (HHV, LHV) in MJ/kg, or None if not found
        
    Examples:
        >>> get_reference_heating_values("Methane")
        (55.5, 50.01)
        >>> get_reference_heating_values("Nitrogen")
        (0.0, 0.0)
    """
    # Try exact match
    if gas_name in REFERENCE_HEATING_VALUES:
        return REFERENCE_HEATING_VALUES[gas_name]
    
    # Try case-insensitive match
    gas_lower = gas_name.lower()
    for ref_name, values in REFERENCE_HEATING_VALUES.items():
        if ref_name.lower() == gas_lower:
            return values
    
    return None


def get_all_reference_gases() -> list:
    """
    Get list of all gases with reference data.
    
    Returns:
        List of gas names
    """
    return list(REFERENCE_HEATING_VALUES.keys())
