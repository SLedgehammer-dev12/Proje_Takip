"""
Thermodynamic calculator module.

Provides the core calculation engine using CoolProp, independent of UI.
"""

from typing import Optional, Tuple, List
import logging

from natural_gas_g5.config.settings import config
from natural_gas_g5.core.exceptions import (
    BackendNotAvailableError,
    StateUpdateError,
    HeatingValueError,
    CalculationConvergenceError
)
from natural_gas_g5.models.gas_data import GasMixture
from natural_gas_g5.models.calculation_result import (
    CalculationResult,
    ActualConditionResults,
    StandardConditionResults,
    HeatingValues,
    VolumeConversion
)
from natural_gas_g5.models.heating_value_db import get_reference_heating_values

# Try to import CoolProp
CP = None
COOLPROP_AVAILABLE = False

try:
    import CoolProp.CoolProp as CP
    COOLPROP_AVAILABLE = True
    logging.info("CoolProp başarıyla yüklendi")
except ImportError as e:
    logging.error(f"CoolProp içe aktarılamadı: {e}")
    CP = None


class ThermoCalculator:
    """
    Thermodynamic properties calculator.
    
    Handles all thermodynamic calculations using CoolProp library.
    Provides fallback mechanisms for different backends.
    """
    
    def __init__(self, backend: str = "HEOS"):
        """
        Initialize calculator.
        
        Args:
            backend: CoolProp backend to use (HEOS, SRK, or PR)
            
        Raises:
            BackendNotAvailableError: If CoolProp is not installed
        """
        if not COOLPROP_AVAILABLE:
            raise BackendNotAvailableError("CoolProp")
        
        self.backend = backend
        self.logger = logging.getLogger(__name__)
        
    def calculate_properties(
        self,
        mixture: GasMixture,
        temperature_k: float,
        pressure_pa: float,
        volume_m3: Optional[float] = None,
        standard_T: float = config.T_STANDARD,
        standard_P: float = config.P_STANDARD,
        standard_name: Optional[str] = None
    ) -> CalculationResult:
        """
        Calculate thermodynamic properties for gas mixture.
        
        Args:
            mixture: Gas mixture definition
            temperature_k: Temperature in Kelvin
            pressure_pa: Pressure in Pascals
            volume_m3: Optional volume in cubic meters for conversion
            standard_T: Reference standard temperature (K)
            standard_P: Reference standard pressure (Pa)
            standard_name: Optional name of the standard used
            
        Returns:
            Complete calculation results
            
        Raises:
            StateUpdateError: If state update fails
            Various exceptions from validation
        """
        # Validate mixture total
        mixture.validate_total()
        
        # Get backend to use
        backend = self._select_backend(mixture)
        
        try:
            # Calculate properties
            result = self._calculate_with_backend(
                mixture,
                temperature_k,
                pressure_pa,
                volume_m3,
                backend,
                standard_T,
                standard_P,
                standard_name
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"Calculation failed with {backend}: {e}")
            raise
    
    def calculate_with_fallback(
        self,
        mixture: GasMixture,
        temperature_k: float,
        pressure_pa: float,
        volume_m3: Optional[float] = None,
        standard_T: float = config.T_STANDARD,
        standard_P: float = config.P_STANDARD,
        standard_name: Optional[str] = None
    ) -> Tuple[Optional[CalculationResult], str]:
        """
        Calculate with automatic backend fallback.
        
        Tries backends in order: [preferred, SRK, PR]
        HEOS is skipped if mixture is incompatible.
        
        Args:
            mixture: Gas mixture
            temperature_k: Temperature (K)
            pressure_pa: Pressure (Pa)
            volume_m3: Optional volume (m³)
            standard_T: Reference standard temperature (K)
            standard_P: Reference standard pressure (Pa)
            
        Returns:
            Tuple of (result, backend_used) or (None, "")
        """
        # Determine backend order
        backends = self._get_backend_order(mixture)
        
        result = None
        used_backend = ""
        
        for backend in backends:
            try:
                self.logger.info(f"Trying backend: {backend}")
                result = self._calculate_with_backend(
                    mixture,
                    temperature_k,
                    pressure_pa,
                    volume_m3,
                    backend,
                    standard_T,
                    standard_P,
                    standard_name
                )
                used_backend = backend
                self.logger.info(f"Successfully calculated with {backend}")
                break
                
            except Exception as e:
                self.logger.warning(f"Backend {backend} failed: {e}")
                continue
        
        return result, used_backend
    
    def _select_backend(self, mixture: GasMixture) -> str:
        """
        Select appropriate backend based on mixture compatibility.
        
        Args:
            mixture: Gas mixture to check
            
        Returns:
            Backend name to use
        """
        if self.backend == "HEOS":
            incompatible = mixture.check_heos_compatibility()
            if incompatible:
                self.logger.warning(
                    f"HEOS incompatible gases: {incompatible}. "
                    "Consider using SRK or PR."
                )
        
        return self.backend
    
    def _get_backend_order(self, mixture: GasMixture) -> List[str]:
        """
        Get prioritized list of backends to try.
        
        Args:
            mixture: Gas mixture
            
        Returns:
            Ordered list of backend names
        """
        backends = [self.backend]
        
        # Skip HEOS if incompatible
        incompatible = mixture.check_heos_compatibility()
        if incompatible and self.backend == "HEOS":
            backends = ["SRK", "PR"]
        else:
            # Add fallbacks
            for fallback in ["SRK", "PR"]:
                if fallback not in backends:
                    backends.append(fallback)
        
        return backends
    
    def _calculate_with_backend(
        self,
        mixture: GasMixture,
        temperature_k: float,
        pressure_pa: float,
        volume_m3: Optional[float],
        backend: str,
        standard_T: float = config.T_STANDARD,
        standard_P: float = config.P_STANDARD,
        standard_name: Optional[str] = None
    ) -> CalculationResult:
        """
        Perform calculation with specific backend.
        
        Args:
            mixture: Gas mixture
            temperature_k: Temperature (K)
            pressure_pa: Pressure (Pa)
            volume_m3: Optional volume (m³)
            backend: Backend to use
            standard_T: Reference standard temperature (K)
            standard_P: Reference standard pressure (Pa)
            
        Returns:
            Calculation results
        """
        # Create CoolProp state
        state = self._create_state(mixture, temperature_k, pressure_pa, backend)
        
        # Calculate actual condition properties
        actual_results = self._calculate_actual_conditions(state)
        
        # Calculate standard condition properties
        standard_results = self._calculate_standard_conditions(
            mixture, backend, standard_T, standard_P, standard_name
        )
        
        # Calculate heating values
        # Note: We use the selected Standard T for combustion reference as well
        # This is generally acceptable for common standards
        heating_results = self._calculate_heating_values(
            mixture,
            standard_results.density_std,
            standard_results.specific_gravity,
            backend,
            standard_T,
            standard_P
        )
        
        # Calculate volume conversion if provided
        volume_results = None
        if volume_m3 is not None:
            volume_results = self._calculate_volume_conversion(
                volume_m3,
                actual_results.density,
                standard_results.density_std,
                mixture,
                backend
            )
        
        # Package results
        return CalculationResult(
            backend_used=backend,
            actual=actual_results,
            standard=standard_results,
            heating=heating_results,
            volume_conversion=volume_results
        )
    
    def _create_state(
        self,
        mixture: GasMixture,
        temperature_k: float,
        pressure_pa: float,
        backend: str
    ) -> 'CP.AbstractState':
        """
        Create and update CoolProp state.
        
        Args:
            mixture: Gas mixture
            temperature_k: Temperature (K)
            pressure_pa: Pressure (Pa)
            backend: Backend name
            
        Returns:
            Updated CoolProp AbstractState
            
        Raises:
            StateUpdateError: If state creation/update fails
        """
        try:
            # Create state
            mixture_string = mixture.to_coolprop_string()
            self.logger.debug(f"Creating state: {backend}, {mixture_string}")
            
            state = CP.AbstractState(backend, mixture_string)
            
            # Set fractions
            fractions = mixture.get_decimal_fractions()
            if mixture.fraction_type == 'molar':
                state.set_mole_fractions(fractions)
            else:
                state.set_mass_fractions(fractions)
            
            # Update state
            state.update(CP.PT_INPUTS, pressure_pa, temperature_k)
            
            return state
            
        except Exception as e:
            raise StateUpdateError(backend, temperature_k, pressure_pa, e)
    
    def _calculate_actual_conditions(
        self,
        state: 'CP.AbstractState'
    ) -> ActualConditionResults:
        """
        Calculate properties at actual operating conditions.
        
        Args:
            state: CoolProp state at operating conditions
            
        Returns:
            Actual condition results
        """
        # Basic properties
        density = state.rhomass()
        molar_mass = state.molar_mass()
        z_factor = state.compressibility_factor()
        
        # Thermodynamic properties (convert J to kJ)
        u = state.umass() / 1000.0  # kJ/kg
        h = state.hmass() / 1000.0  # kJ/kg
        s = state.smass() / 1000.0  # kJ/(kg·K)
        cp = state.cpmass() / 1000.0  # kJ/(kg·K)
        cv = state.cvmass() / 1000.0  # kJ/(kg·K)
        
        # Derived properties
        k = None
        try:
            k = cp / cv if cv > 1e-10 else None
        except:
            pass
        
        speed_sound = None
        try:
            speed_sound = state.speed_sound()
        except Exception as e:
            self.logger.warning(f"Speed of sound calculation failed: {e}")
        
        return ActualConditionResults(
            density=density,
            molar_mass=molar_mass,
            compressibility_factor=z_factor,
            internal_energy=u,
            enthalpy=h,
            entropy=s,
            cp=cp,
            cv=cv,
            isentropic_exponent=k,
            speed_of_sound=speed_sound
        )
    
    def _calculate_standard_conditions(
        self,
        mixture: GasMixture,
        backend: str,
        T_std: float,
        P_std: float,
        standard_name: Optional[str] = None
    ) -> StandardConditionResults:
        """
        Calculate properties at standard conditions.
        
        Args:
            mixture: Gas mixture
            backend: Backend to use
            T_std: Standard temperature (K)
            P_std: Standard pressure (Pa)
            standard_name: Name of standard used
            
        Returns:
            Standard condition results
        """
        # Create state at standard conditions
        state_std = self._create_state(mixture, T_std, P_std, backend)
        rho_std = state_std.rhomass()
        
        # Calculate specific gravity (relative to air at same conditions)
        try:
            # We must calculate air density at the SAME standard conditions
            # to be scientifically correct for SG
            rho_air = CP.PropsSI('D', 'T', T_std, 'P', P_std, 'Air')
        except:
            rho_air = 1.225  # kg/m³ (approximate at 15C)
            self.logger.warning("Could not get air density from CoolProp, using approximate value")
        
        sg = rho_std / rho_air
        
        return StandardConditionResults(
            density_std=rho_std,
            specific_gravity=sg,
            reference_temperature=T_std,
            reference_pressure=P_std,
            standard_name=standard_name
        )
    
    def _calculate_heating_values(
        self,
        mixture: GasMixture,
        rho_std: float,
        sg: float,
        backend: str,
        T_ref: float,
        P_ref: float
    ) -> Optional[HeatingValues]:
        """
        Calculate heating values with 3-stage fallback.
        
        Args:
            mixture: Gas mixture
            rho_std: Standard density (kg/Sm³)
            sg: Specific gravity
            backend: Backend being used
            T_ref: Reference temperature for combustion (K)
            P_ref: Reference pressure (Pa)
            
        Returns:
            Heating values or None if calculation fails
        """
        # Try Stage 1: Built-in method (HEOS only)
        if backend == "HEOS":
            try:
                hhv_mass, lhv_mass = self._calculate_heating_values_builtin(
                    mixture,
                    backend,
                    T_ref,
                    P_ref
                )
                if hhv_mass > 0 and lhv_mass > 0:
                    return self._package_heating_values(
                        hhv_mass,
                        lhv_mass,
                        rho_std,
                        sg,
                        "CoolProp yerleşik"
                    )
            except Exception as e:
                self.logger.warning(f"Built-in HHV/LHV failed: {e}")
        
        # Try Stage 2: Component-based CoolProp
        try:
            hhv_mass, lhv_mass = self._calculate_heating_values_component_based(
                mixture,
                backend,
                T_ref,
                P_ref
            )
            if hhv_mass > 0 and lhv_mass > 0:
                return self._package_heating_values(
                    hhv_mass,
                    lhv_mass,
                    rho_std,
                    sg,
                    "Bileşen bazlı (CoolProp)"
                )
        except Exception as e:
            self.logger.warning(f"Component-based HHV/LHV failed: {e}")
        
        # Try Stage 3: Reference database
        try:
            # Note: Database values are typically at 15°C or 25°C.
            # If user selected a very different standard (e.g. 0°C),
            # this might introduce a small error.
            if abs(T_ref - 288.15) > 5.0 and abs(T_ref - 298.15) > 5.0:
                 self.logger.warning(
                     f"Using reference DB values (15°C/25°C base) for T={T_ref:.2f}K. "
                     "Result may have slight deviation."
                 )
            
            hhv_mass, lhv_mass = self._calculate_heating_values_reference(
                mixture
            )
            if hhv_mass > 0 and lhv_mass > 0:
                self.logger.info("Using reference database heating values")
                return self._package_heating_values(
                    hhv_mass,
                    lhv_mass,
                    rho_std,
                    sg,
                    "Referans veri tabanı"
                )
        except Exception as e:
            self.logger.warning(f"Reference database HHV/LHV failed: {e}")
        
        # All methods failed
        self.logger.error("All heating value calculation methods failed")
        return None
    
    def _calculate_heating_values_builtin(
        self,
        mixture: GasMixture,
        backend: str,
        T_ref: float,
        P_ref: float
    ) -> Tuple[float, float]:
        """
        Calculate heating values using CoolProp built-in method.
        """
        state_std = self._create_state(mixture, T_ref, P_ref, backend)
        
        hhv = state_std.HHVmass() / 1e6  # Convert J/kg to MJ/kg
        lhv = state_std.LHVmass() / 1e6
        
        if hhv < 1e-6 or lhv < 1e-6:
            raise HeatingValueError(message="Built-in method returned zero values")
        
        return hhv, lhv
    
    def _calculate_heating_values_component_based(
        self,
        mixture: GasMixture,
        backend: str,
        T_ref: float,
        P_ref: float
    ) -> Tuple[float, float]:
        """
        Calculate heating values by summing component contributions.
        """
        total_hhv = 0.0
        total_lhv = 0.0
        
        for component in mixture.components:
            try:
                # Create state for single component
                state = CP.AbstractState(backend, component.name)
                state.update(CP.PT_INPUTS, P_ref, T_ref)
                
                hhv = state.HHVmass() / 1e6  # MJ/kg
                lhv = state.LHVmass() / 1e6
                
                # Zero values mean no data available
                if hhv < 1e-6: hhv = 0.0
                if lhv < 1e-6: lhv = 0.0
                
                # Add weighted contribution
                fraction_decimal = component.to_decimal()
                total_hhv += fraction_decimal * hhv
                total_lhv += fraction_decimal * lhv
                
            except Exception as e:
                self.logger.warning(
                    f"Could not get heating values for {component.name}: {e}. "
                    "Using 0 contribution."
                )
                continue
        
        if total_hhv < 1e-6:
            raise HeatingValueError(
                message="No combustible components with heating value data"
            )
            
        return total_hhv, total_lhv
    
    def _calculate_heating_values_reference(
        self,
        mixture: GasMixture
    ) -> Tuple[float, float]:
        """
        Calculate heating values using reference database.
        
        Args:
            mixture: Gas mixture
            
        Returns:
            Tuple of (HHV, LHV) in MJ/kg
        """
        total_hhv = 0.0
        total_lhv = 0.0
        components_found = 0
        
        for component in mixture.components:
            ref_values = get_reference_heating_values(component.name)
            
            if ref_values is not None:
                hhv, lhv = ref_values
                fraction_decimal = component.to_decimal()
                total_hhv += fraction_decimal * hhv
                total_lhv += fraction_decimal * lhv
                components_found += 1
                
                self.logger.debug(
                    f"Reference values for {component.name}: "
                    f"HHV={hhv:.2f}, LHV={lhv:.2f} MJ/kg"
                )
            else:
                self.logger.warning(
                    f"No reference heating values for {component.name}"
                )
        
        if components_found == 0:
            raise HeatingValueError(
                message="No reference data available for any component"
            )
        
        if total_hhv < 1e-6:
            raise HeatingValueError(
                message="No combustible components in reference database"
            )
        
        self.logger.info(
            f"Reference database calculation: HHV={total_hhv:.4f}, "
            f"LHV={total_lhv:.4f} MJ/kg ({components_found}/{len(mixture.components)} components found)"
        )
        
        return total_hhv, total_lhv
    
    def _package_heating_values(
        self,
        hhv_mass: float,
        lhv_mass: float,
        rho_std: float,
        sg: float,
        method: str
    ) -> HeatingValues:
        """
        Package heating values into result model.
        
        Args:
            hhv_mass: HHV in MJ/kg
            lhv_mass: LHV in MJ/kg
            rho_std: Standard density (kg/Sm³)
            sg: Specific gravity
            method: Calculation method description
            
        Returns:
            Heating values model
        """
        # Volumetric basis
        hhv_vol = hhv_mass * rho_std  # MJ/Sm³
        lhv_vol = lhv_mass * rho_std  # MJ/Sm³
        
        # Wobbe index
        wobbe = hhv_vol / (sg ** 0.5)
        
        # Industrial units (Btu/SCF)
        hhv_btu_scf = hhv_vol * config.MMBTU_PER_MJ / config.M3_TO_SCF * 1e6
        
        return HeatingValues(
            hhv_mass=hhv_mass,
            lhv_mass=lhv_mass,
            hhv_volume=hhv_vol,
            lhv_volume=lhv_vol,
            wobbe_index=wobbe,
            hhv_btu_scf=hhv_btu_scf,
            calculation_method=method
        )
    
    def _calculate_volume_conversion(
        self,
        volume_actual: float,
        rho_actual: float,
        rho_std: float,
        mixture: GasMixture,
        backend: str
    ) -> VolumeConversion:
        """
        Calculate volume conversion from actual to standard and normal conditions.
        
        Args:
            volume_actual: Actual volume (m³)
            rho_actual: Actual density (kg/m³)
            rho_std: Standard density (kg/Sm³)
            mixture: Gas mixture definition
            backend: Backend to use for normal density calculation
            
        Returns:
            Volume conversion results
        """
        mass = rho_actual * volume_actual  # kg
        volume_std = mass / rho_std  # Sm³
        
        # Calculate Normal Volume (NCM) @ 0°C, 1 atm
        volume_norm = None
        try:
            # Create state at Normal conditions
            state_norm = self._create_state(
                mixture, 
                config.T_NORMAL, 
                config.P_NORMAL, 
                backend
            )
            rho_norm = state_norm.rhomass()
            volume_norm = mass / rho_norm
        except Exception as e:
            self.logger.warning(f"Failed to calculate NCM volume: {e}")
        
        return VolumeConversion(
            actual_volume=volume_actual,
            mass=mass,
            standard_volume=volume_std,
            normal_volume=volume_norm
        )
