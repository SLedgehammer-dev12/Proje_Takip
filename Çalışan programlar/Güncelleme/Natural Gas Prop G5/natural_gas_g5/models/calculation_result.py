"""
Calculation result models.

Defines structured data models for storing thermodynamic calculation results.
"""

from typing import Optional, Dict, List, Tuple, Any
from pydantic import BaseModel, Field

from natural_gas_g5.utils.result_unit_converter import ResultUnitConverter, UnitSystem


class ActualConditionResults(BaseModel):
    """Results at actual (operating) conditions."""
    
    density: float = Field(..., description="Mass density (kg/m³)")
    molar_mass: float = Field(..., description="Molar mass (kg/mol)")
    compressibility_factor: float = Field(..., description="Z-factor (dimensionless)")
    internal_energy: float = Field(..., description="Specific internal energy (kJ/kg)")
    enthalpy: float = Field(..., description="Specific enthalpy (kJ/kg)")
    entropy: float = Field(..., description="Specific entropy (kJ/kg·K)")
    cp: float = Field(..., description="Specific heat at constant pressure (kJ/kg·K)")
    cv: float = Field(..., description="Specific heat at constant volume (kJ/kg·K)")
    isentropic_exponent: Optional[float] = Field(None, description="k = Cp/Cv (dimensionless)")
    speed_of_sound: Optional[float] = Field(None, description="Speed of sound (m/s)")
    
    model_config = {"frozen": False}


class StandardConditionResults(BaseModel):
    """
    Results at standard conditions (e.g., 15°C, 101.325 kPa).
    
    Attributes:
        density_std: Density at standard conditions (kg/Sm³)
        specific_gravity: Specific gravity relative to air (dimensionless)
        reference_temperature: Reference temperature used (K)
        reference_pressure: Reference pressure used (Pa)
        standard_name: Name of the standard used
    """
    
    density_std: float = Field(..., description="Density at standard conditions (kg/Sm³)")
    specific_gravity: float = Field(..., description="Specific gravity relative to air (dimensionless)")
    
    # Metadata about the standard used
    reference_temperature: float = Field(..., description="Reference temperature used (K)")
    reference_pressure: float = Field(..., description="Reference pressure used (Pa)")
    standard_name: Optional[str] = Field(None, description="Name of the standard used")
    
    model_config = {
        "frozen": False,
        "validate_assignment": True
    }


class HeatingValues(BaseModel):
    """Heating value calculation results."""
    
    hhv_mass: float = Field(..., description="Higher heating value, mass basis (MJ/kg)")
    lhv_mass: float = Field(..., description="Lower heating value, mass basis (MJ/kg)")
    hhv_volume: float = Field(..., description="HHV, volumetric basis (MJ/Sm³)")
    lhv_volume: float = Field(..., description="LHV, volumetric basis (MJ/Sm³)")
    wobbe_index: float = Field(..., description="Wobbe index (MJ/Sm³)")
    hhv_btu_scf: float = Field(..., description="HHV in industrial units (Btu/SCF)")
    calculation_method: str = Field(..., description="Method used for calculation")
    
    model_config = {"frozen": False}


class VolumeConversion(BaseModel):
    """Volume conversion results."""
    
    actual_volume: float = Field(..., description="Actual volume (ACM) (m³)")
    mass: float = Field(..., description="Total mass (kg)")
    standard_volume: float = Field(..., description="Standard volume (SCM) (Sm³)")
    normal_volume: Optional[float] = Field(None, description="Normal volume (NCM) (Nm³)")
    
    model_config = {"frozen": False}


class CalculationResult(BaseModel):
    """
    Complete calculation results container.
    
    Aggregates all results from thermodynamic calculations.
    """
    
    backend_used: str = Field(..., description="Thermodynamic backend used (HEOS, SRK, PR)")
    actual: ActualConditionResults = Field(..., description="Actual condition results")
    standard: StandardConditionResults = Field(..., description="Standard condition results")
    heating: Optional[HeatingValues] = Field(None, description="Heating values (if calculable)")
    volume_conversion: Optional[VolumeConversion] = Field(None, description="Volume conversion (if provided)")
    
    def to_display_list(self, unit_system: str = "SI") -> List[Tuple[str, str, str]]:
        """
        Convert results to display format for UI TreeView.
        
        Args:
            unit_system: Unit system for display ("SI", "Imperial", or "Mixed")
        
        Returns:
            List of (property_name, value, unit_string) tuples
        """
        results = []
        
        # Get unit preferences based on system
        try:
            unit_sys = UnitSystem(unit_system)
        except ValueError:
            unit_sys = UnitSystem.SI
        
        prefs = ResultUnitConverter.get_unit_preferences(unit_sys)
        
        # Header - Actual Conditions
        results.append(("- GERÇEK KOŞULLAR SONUÇLARI -", "", ""))
        results.append(("Hesaplama Yöntemi (Termo)", self.backend_used, ""))
        
        # Density
        density_val, density_unit = ResultUnitConverter.convert_density(
            self.actual.density, prefs['density']
        )
        results.append(("Yoğunluk (Gerçek - ρ)", f"{density_val:.4f}", density_unit))
        
        results.append(("Mol Kütlesi (Karışım - M)", f"{self.actual.molar_mass:.4f}", "kg/mol"))
        results.append(("Sıkıştırılabilirlik Faktörü (Z)", f"{self.actual.compressibility_factor:.5f}", "-"))
        
        # Energy properties
        u_val, u_unit = ResultUnitConverter.convert_energy_mass(
            self.actual.internal_energy, prefs['energy_mass']
        )
        h_val, h_unit = ResultUnitConverter.convert_energy_mass(
            self.actual.enthalpy, prefs['energy_mass']
        )
        s_val, s_unit = ResultUnitConverter.convert_entropy(
            self.actual.entropy, prefs['entropy']
        )
        cp_val, cp_unit = ResultUnitConverter.convert_entropy(
            self.actual.cp, prefs['entropy']
        )
        cv_val, cv_unit = ResultUnitConverter.convert_entropy(
            self.actual.cv, prefs['entropy']
        )
        
        results.append(("İç Enerji (u)", f"{u_val:.4f}", u_unit))
        results.append(("Entalpi (h)", f"{h_val:.4f}", h_unit))
        results.append(("Entropi (s)", f"{s_val:.4f}", s_unit))
        results.append(("Cp", f"{cp_val:.4f}", cp_unit))
        results.append(("Cv", f"{cv_val:.4f}", cv_unit))
        
        if self.actual.isentropic_exponent is not None:
            results.append(("İzotropik Üs (k)", f"{self.actual.isentropic_exponent:.4f}", "-"))
        else:
            results.append(("İzotropik Üs (k)", "Hesaplanamadı", "-"))
        
        if self.actual.speed_of_sound is not None:
            speed_val, speed_unit = ResultUnitConverter.convert_speed(
                self.actual.speed_of_sound, prefs['speed']
            )
            results.append(("Ses Hızı (a)", f"{speed_val:.2f}", speed_unit))
        else:
            results.append(("Ses Hızı (a)", "Hesaplanamadı", "-"))
        
        # Header - Standard Conditions
        results.append(("- STANDART ÇEVRİM BİLGİLERİ (SCM @ 15°C, 101.325 kPa) -", "", ""))
        results.append(("Standart Koşullar", "288.15 K, 101.325 kPa", "-"))
        
        # Standard density
        std_density_val, std_density_unit = ResultUnitConverter.convert_density(
            self.standard.density_std, prefs['density']
        )
        results.append(("Yoğunluk (SCM - ρ_std)", f"{std_density_val:.4f}", std_density_unit.replace('m³', 'Sm³') if 'm³' in std_density_unit else std_density_unit))
        results.append(("Bağıl Yoğunluk (SG - Hava=1)", f"{self.standard.specific_gravity:.4f}", "-"))
        
        # Header - Heating Values
        if self.heating:
            results.append(("- ISIL DEĞERLER (SCM) -", "", ""))
            results.append(("Hesaplama Yöntemi (HHV/LHV)", self.heating.calculation_method, ""))
            
            # Mass-based heating values
            hhv_m_val, hhv_m_unit = ResultUnitConverter.convert_heating_value_mass(
                self.heating.hhv_mass, prefs['heating_value_mass']
            )
            lhv_m_val, lhv_m_unit = ResultUnitConverter.convert_heating_value_mass(
                self.heating.lhv_mass, prefs['heating_value_mass']
            )
            
            results.append(("Üst Isıl Değer (HHV)", f"{hhv_m_val:.4f}", hhv_m_unit))
            results.append(("Alt Isıl Değer (LHV)", f"{lhv_m_val:.4f}", lhv_m_unit))
            
            # Volume-based heating values
            hhv_v_val, hhv_v_unit = ResultUnitConverter.convert_heating_value_volume(
                self.heating.hhv_volume, prefs['heating_value_volume']
            )
            wobbe_val, wobbe_unit = ResultUnitConverter.convert_heating_value_volume(
                self.heating.wobbe_index, prefs['heating_value_volume']
            )
            
            results.append(("HHV (Hacimsel)", f"{hhv_v_val:.4f}", hhv_v_unit))
            results.append(("Wobbe İndeksi", f"{wobbe_val:.2f}", wobbe_unit))
            
            # Always show Btu/SCF for reference if not already in that unit
            if prefs['heating_value_volume'] != 'Btu/SCF':
                results.append(("HHV (Endüstriyel)", f"{self.heating.hhv_btu_scf:.2f}", "Btu/SCF"))
        else:
            results.append(("- ISIL DEĞERLER (SCM) -", "", ""))
            results.append(("Hesaplama Yöntemi (HHV/LHV)", "Veri/Yöntem Yok", ""))
            results.append(("Üst Isıl Değer (HHV)", "Hesaplanamadı", "-"))
            results.append(("Alt Isıl Değer (LHV)", "Hesaplanamadı", "-"))
            results.append(("Wobbe İndeksi", "Hesaplanamadı", "-"))
            results.append(("HHV (Endüstriyel)", "Hesaplanamadı", "-"))
        
        # Header - Volume Conversion
        if self.volume_conversion:
            results.append(("- HACİM DÖNÜŞÜMÜ -", "", ""))
            
            vol_act_val, vol_act_unit = ResultUnitConverter.convert_volume(
                self.volume_conversion.actual_volume, prefs['volume']
            )
            mass_val, mass_unit = ResultUnitConverter.convert_mass(
                self.volume_conversion.mass, prefs['mass']
            )
            vol_std_val, vol_std_unit = ResultUnitConverter.convert_volume(
                self.volume_conversion.standard_volume, prefs['volume']
            )
            
            # Add 'S' prefix for standard volume if using m³
            if 'm³' in vol_std_unit:
                vol_std_unit = vol_std_unit.replace('m³', 'Sm³')
            elif 'ft³' in vol_std_unit:
                vol_std_unit = vol_std_unit.replace('ft³', 'SCF')
            
            results.append(("Girilen Hacim (ACM)", f"{vol_act_val:.4f}", vol_act_unit))
            results.append(("Toplam Kütle", f"{mass_val:.4f}", mass_unit))
            results.append(("Standart Hacim (SCM)", f"{vol_std_val:.4f}", vol_std_unit))
            
            # Normal Volume (NCM)
            if self.volume_conversion.normal_volume is not None:
                vol_norm_val, vol_norm_unit = ResultUnitConverter.convert_volume(
                    self.volume_conversion.normal_volume, prefs['volume']
                )
                if 'm³' in vol_norm_unit:
                    vol_norm_unit = 'Nm³'
                
                results.append(("Normal Hacim (NCM)", f"{vol_norm_val:.4f}", vol_norm_unit))
                results.append(("", f"@ 0°C, 101.325 kPa", "(Normal)"))
        
        return results
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary format.
        
        Returns:
            Dictionary representation of all results
        """
        return self.model_dump()
    
    model_config = {"frozen": False}
