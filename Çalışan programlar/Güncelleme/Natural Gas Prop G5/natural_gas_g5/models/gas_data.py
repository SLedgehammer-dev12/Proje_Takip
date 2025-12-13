"""
Gas data models and mixture handling.

Defines Pydantic models for gas components and mixtures with validation.
"""

from typing import List, Literal
from pydantic import BaseModel, Field, field_validator, computed_field
import re

from natural_gas_g5.config.settings import config
from natural_gas_g5.core.exceptions import ValidationError


class GasComponent(BaseModel):
    """
    Represents a single gas component in a mixture.
    
    Attributes:
        name: Gas name (e.g., "Methane", "Ethane")
        fraction: Mole or mass fraction in percent (0-100)
    """
    
    name: str = Field(..., min_length=1, description="Gas component name")
    fraction: float = Field(..., gt=0, le=100, description="Fraction percentage (0-100)")
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate and clean gas name."""
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Gas name cannot be empty")
        return cleaned
    
    @field_validator('fraction')
    @classmethod
    def validate_fraction(cls, v: float) -> float:
        """Validate fraction is in valid range."""
        if v <= 0 or v > 100:
            raise ValueError(f"Fraction must be between 0 and 100, got {v}")
        return v
    
    def to_decimal(self) -> float:
        """Convert percentage to decimal (0-1 range)."""
        return self.fraction / 100.0
    
    model_config = {
        "frozen": False,  # Allow modification
        "validate_assignment": True  # Validate on assignment
    }


class GasMixture(BaseModel):
    """
    Represents a mixture of multiple gas components.
    
    Attributes:
        components: List of gas components
        fraction_type: Type of fractions ("molar" or "mass")
    """
    
    components: List[GasComponent] = Field(..., min_length=1, max_length=20)
    fraction_type: Literal["molar", "mass"] = Field(default="molar")
    
    @field_validator('components')
    @classmethod
    def validate_components(cls, v: List[GasComponent]) -> List[GasComponent]:
        """Validate component list."""
        if not v:
            raise ValueError("At least one gas component is required")
        
        if len(v) > config.MAX_COMPONENTS:
            raise ValueError(
                f"Maximum {config.MAX_COMPONENTS} components allowed, got {len(v)}"
            )
        
        # Check for duplicate gas names (case-insensitive)
        names = [comp.name.lower() for comp in v]
        if len(names) != len(set(names)):
            raise ValueError("Duplicate gas names are not allowed")
        
        return v
    
    @computed_field
    @property
    def total_fraction(self) -> float:
        """Calculate total fraction percentage."""
        return sum(comp.fraction for comp in self.components)
    
    def validate_total(self, tolerance: float = 1e-4) -> None:
        """
        Validate that fractions sum to 100%.
        
        Args:
            tolerance: Acceptable deviation from 100%
            
        Raises:
            ValidationError: If sum is not 100% within tolerance
        """
        total = self.total_fraction
        
        if abs(total - 100.0) > tolerance:
            raise ValidationError(
                "Gaz Kompozisyonu",
                f"Yüzdelerin toplamı 100 olmalıdır.  Mevcut toplam: {total:.4f}%"
            )
    
    def get_decimal_fractions(self) -> List[float]:
        """Get fractions as decimal values (0-1 range)."""
        return [comp.to_decimal() for comp in self.components]
    
    def get_gas_names(self) -> List[str]:
        """Get list of gas names."""
        return [comp.name for comp in self.components]
    
    def to_coolprop_string(self) -> str:
        """
        Convert mixture to CoolProp format string.
        
        Returns:
            Mixture string in format "Gas1&Gas2&Gas3"
            
        Examples:
            >>> mixture.to_coolprop_string()
            "Methane&Ethane&Propane"
        """
        formatted_names = [
            self._format_gas_name_for_coolprop(comp.name)
            for comp in self.components
        ]
        return '&'.join(formatted_names)
    
    @staticmethod
    def _format_gas_name_for_coolprop(gas_name: str) -> str:
        """
        Format gas name for CoolProp compatibility.
        
        Args:
            gas_name: Original gas name
            
        Returns:
            CoolProp-compatible gas name
        """
        # Remove spaces and convert to lowercase for matching
        clean_name = re.sub(r'\s+', '', gas_name.strip()).lower()
        
        # Mapping of common names to CoolProp names
        name_mapping = {
            'methane': 'Methane',
            'ethane': 'Ethane',
            'propane': 'Propane',
            'n-butane': 'n-Butane',
            'isobutane': 'Isobutane',
            'nitrogen': 'Nitrogen',
            'carbondioxide': 'CarbonDioxide',
            'hydrogen': 'Hydrogen',
            'oxygen': 'Oxygen',
            'argon': 'Argon',
            'helium': 'Helium',
            'water': 'Water',
            'air': 'Air',
            'hydrogensulfide': 'HydrogenSulfide',
            'carbonmonoxide': 'CarbonMonoxide',
            'r134a': 'R134a',
            'r22': 'R22',
            'r410a': 'R410A'
        }
        
        return name_mapping.get(clean_name, gas_name)
    
    def check_heos_compatibility(self) -> List[str]:
        """
        Check which gases are incompatible with HEOS backend.
        
        Returns:
            List of incompatible gas names (empty if all compatible)
        """
        heos_compatible = [g.lower() for g in config.HEOS_COMPATIBLE_GASES]
        incompatible = [
            comp.name for comp in self.components
            if comp.name.lower() not in heos_compatible
        ]
        return incompatible
    
    model_config = {
        "frozen": False,
        "validate_assignment": True
    }
