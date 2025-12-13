"""
Application configuration settings.

Centralizes all constants, limits, and configurable parameters.
"""

from typing import List, Dict
from pydantic import BaseModel, Field


class AppConfig(BaseModel):
    """Application configuration with validation."""
    
    # Physical Constants
    P_ATM_BAR: float = Field(
        default=1.01325,
        description="Standard atmospheric pressure (bar absolute)"
    )
    P_ATM_PSI: float = Field(
        default=14.6959,
        description="Standard atmospheric pressure (psi absolute)"
    )
    
    # Standard Conditions (ISO 13443 default)
    T_STANDARD: float = Field(
        default=288.15,
        description="Standard temperature (K) - 15°C"
    )
    P_STANDARD: float = Field(
        default=101325.0,
        description="Standard pressure (Pa) - 101.325 kPa"
    )
    
    # Normal Conditions (0°C, 1 atm) - for NCM calculation
    T_NORMAL: float = Field(
        default=273.15,
        description="Normal temperature (K) - 0°C"
    )
    P_NORMAL: float = Field(
        default=101325.0,
        description="Normal pressure (Pa) - 101.325 kPa"
    )

    # Predefined Standard Conditions
    STANDARD_CONDITIONS: dict = Field(
        default={
            "ISO 13443 (15°C, 1 atm)": {"T": 288.15, "P": 101325.0},
            "GPA 2172 (60°F, 14.696 psi)": {"T": 288.706, "P": 101325.0},
            "API MPMS (60°F, 14.73 psi)": {"T": 288.706, "P": 101560.0},
            "EPDK (15°C, 1.01325 bar)": {"T": 288.15, "P": 101325.0},
            "GOST 2939 (20°C, 1 atm)": {"T": 293.15, "P": 101325.0},
            "Normal Şartlar (0°C, 1 atm)": {"T": 273.15, "P": 101325.0},
        },
        description="Predefined standard conditions"
    )
    
    # Predefined Standards
    AVAILABLE_STANDARDS: Dict[str, Dict[str, float]] = Field(
        default={
            "ISO 13443": {"temp_k": 288.15, "press_pa": 101325.0, "desc": "15°C, 1 atm"},
            "GPA 2172": {"temp_k": 288.706, "press_pa": 101325.0, "desc": "60°F, 14.696 psi"},
            "GOST 2939": {"temp_k": 293.15, "press_pa": 101325.0, "desc": "20°C, 1 atm"},
            "NTP (Normal)": {"temp_k": 273.15, "press_pa": 101325.0, "desc": "0°C, 1 atm"},
            "SATP": {"temp_k": 298.15, "press_pa": 100000.0, "desc": "25°C, 1 bar"},
        },
        description="Available standard conditions"
    )
    
    # Calculation Limits
    MAX_COMPONENTS: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Maximum number of gas components in mixture"
    )
    MIN_TEMPERATURE: float = Field(
        default=0.1,
        description="Minimum temperature (K)"
    )
    MAX_TEMPERATURE: float = Field(
        default=5000.0,
        description="Maximum temperature (K)"
    )
    MIN_PRESSURE: float = Field(
        default=1e-10,
        description="Minimum pressure (Pa)"
    )
    MAX_PRESSURE: float = Field(
        default=1e9,
        description="Maximum pressure (Pa) - ~10000 bar"
    )
    MIN_VOLUME: float = Field(
        default=1e-10,
        description="Minimum volume (m³)"
    )
    MAX_VOLUME: float = Field(
        default=1e9,
        description="Maximum volume (m³)"
    )
    
    # UI Settings
    WINDOW_WIDTH: int = Field(
        default=1050,
        description="Main window width (pixels)"
    )
    WINDOW_HEIGHT: int = Field(
        default=850,
        description="Main window height (pixels)"
    )
    WINDOW_TITLE: str = Field(
        default="Termodinamik Gaz Karışımı Hesaplayıcı (Sürüm 5.0 - Modüler)",
        description="Application window title"
    )
    UI_THEME: str = Field(
        default="clam",
        description="TTK theme name"
    )
    
    # Logging Configuration
    LOG_FILE: str = Field(
        default="thermo_gas_calculator.log",
        description="Log file path"
    )
    LOG_LEVEL: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)"
    )
    LOG_ENCODING: str = Field(
        default="utf-8-sig",
        description="Log file encoding"
    )
    
    # Calculation Settings
    DEFAULT_BACKEND: str = Field(
        default="HEOS",
        description="Default CoolProp backend"
    )
    AVAILABLE_BACKENDS: List[str] = Field(
        default=["HEOS", "SRK", "PR"],
        description="Available thermodynamic backends"
    )
    
    # HEOS Compatible Gases (for mixture calculations)
    HEOS_COMPATIBLE_GASES: List[str] = Field(
        default=[
            "Methane", "Ethane", "Propane", "n-Butane", "Isobutane",
            "Nitrogen", "CarbonDioxide", "Hydrogen", "Oxygen", "Argon", "Water"
        ],
        description="Gases compatible with HEOS backend for mixtures"
    )
    
    # Fallback Gas List (if CoolProp fails to load)
    FALLBACK_GAS_LIST: List[str] = Field(
        default=[
            "Methane", "Ethane", "Propane", "n-Butane", "Isobutane",
            "Nitrogen", "CarbonDioxide", "HydrogenSulfide", "Water", "Air"
        ],
        description="Fallback gas list when CoolProp database unavailable"
    )
    
    # Conversion Constants
    MMBTU_PER_MJ: float = Field(
        default=9.4781712e-4,
        description="MMBtu per MJ conversion factor"
    )
    M3_TO_SCF: float = Field(
        default=35.3147,
        description="Cubic meters to standard cubic feet"
    )
    
    # Update Configuration
    APP_VERSION: str = Field(
        default="5.1.0",
        description="Current application version"
    )
    REPO_USER: str = Field(
        default="SLedgehammer-dev12",
        description="GitHub username"
    )
    REPO_NAME: str = Field(
        default="Programlar",
        description="GitHub repository name"
    )
    BRANCH_NAME: str = Field(
        default="Natural-Gas-Prop",
        description="Branch name for updates"
    )
    REPO_PATH: str = Field(
        default="Çalışan programlar/Güncelleme/Natural Gas Prop G5",
        description="Path to application folder in repository"
    )
    
    @property
    def UPDATE_CHECK_URL(self) -> str:
        """Get URL to check for updates (raw JSON)."""
        from urllib.parse import quote
        path = quote(self.REPO_PATH)
        return f"https://raw.githubusercontent.com/{self.REPO_USER}/{self.REPO_NAME}/{self.BRANCH_NAME}/{path}/version.json"
    
    @property
    def REPO_URL(self) -> str:
        """Get main repository URL."""
        from urllib.parse import quote
        path = quote(self.REPO_PATH)
        return f"https://github.com/{self.REPO_USER}/{self.REPO_NAME}/tree/{self.BRANCH_NAME}/{path}"

    class Config:
        """Pydantic configuration."""
        validate_assignment = True
        frozen = False  # Allow runtime modifications if needed


# Global configuration instance
config = AppConfig()
