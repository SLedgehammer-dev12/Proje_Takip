"""
Input panel component.

Handles user inputs for gas composition, thermodynamic conditions, and calculation settings.
"""

import tkinter as tk
from tkinter import ttk
from typing import List, Tuple, Optional
import logging

from natural_gas_g5.models.gas_data import GasComponent, GasMixture
from natural_gas_g5.core.exceptions import ValidationError
from natural_gas_g5.core import validators
from natural_gas_g5.core import converters
from natural_gas_g5.config.settings import config


class InputPanel(ttk.Frame):
    """
    Input panel for gas composition and calculation parameters.
    
    Provides widgets for:
    - Gas component selection and composition
    - Temperature and pressure inputs with unit selection
    - Volume input (optional)
    - Backend method selection
    """
    
    def __init__(self, parent, gas_list: List[str], *args, **kwargs):
        """
        Initialize input panel.
        
        Args:
            parent: Parent widget
            gas_list: List of available gas names
        """
        super().__init__(parent, *args, **kwargs)
        
        self.gas_list = gas_list
        self.logger = logging.getLogger(__name__)
        
        self.create_widgets()
    
    def create_widgets(self):
        """Create and layout all input widgets."""
        self._create_composition_section()
        self._create_standard_section()
        self._create_conditions_section()
        self._create_volume_method_section()
    
    def _create_composition_section(self):
        """Create gas composition input widgets."""
        # Frame
        comp_frame = ttk.LabelFrame(
            self,
            text="1. Gaz Kompozisyonu",
            padding="10"
        )
        comp_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Layout: Left (Gas List), Right (Composition)
        paned = ttk.PanedWindow(comp_frame, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)
        
        # Left Panel: Gas Selection
        left_frame = ttk.Frame(paned)
        paned.add(left_frame, weight=1)
        
        # Search box
        ttk.Label(left_frame, text="Gaz Ara:").pack(anchor="w")
        self.search_var = tk.StringVar()
        self.search_var.trace("w", self._on_gas_search)
        search_entry = ttk.Entry(left_frame, textvariable=self.search_var)
        search_entry.pack(fill=tk.X, pady=(0, 5))
        
        # Gas Listbox
        list_frame = ttk.Frame(left_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.gas_listbox = tk.Listbox(
            list_frame,
            selectmode=tk.SINGLE,
            yscrollcommand=scrollbar.set,
            height=6
        )
        self.gas_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.gas_listbox.yview)
        
        # Initial population
        self._update_gas_list()
        
        # Add Button
        ttk.Button(
            left_frame,
            text="Ekle >>",
            command=self._on_add_gas
        ).pack(fill=tk.X, pady=5)
        
        # Right Panel: Selected Composition
        right_frame = ttk.Frame(paned)
        paned.add(right_frame, weight=2)
        
        # Treeview
        cols = ("Bileşen", "Oran (%)")
        self.tree = ttk.Treeview(
            right_frame,
            columns=cols,
            show="headings",
            height=6
        )
        
        self.tree.heading("Bileşen", text="Bileşen")
        self.tree.heading("Oran (%)", text="Oran (%)")
        
        self.tree.column("Bileşen", width=120)
        self.tree.column("Oran (%)", width=80)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Scrollbar for tree
        tree_scroll = ttk.Scrollbar(
            right_frame,
            orient=tk.VERTICAL,
            command=self.tree.yview
        )
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.configure(yscrollcommand=tree_scroll.set)
        
        # Bind double click to edit
        self.tree.bind("<Double-1>", self._on_double_click_composition)
        
        # Remove and Clear Buttons
        btn_frame = ttk.Frame(right_frame)
        btn_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(
            btn_frame,
            text="Seçileni Sil",
            command=self._on_remove_gas
        ).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 2))
        
        ttk.Button(
            btn_frame,
            text="Tümünü Temizle",
            command=self._on_clear_all
        ).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(2, 0))
        
        # Total label
        self.total_label = ttk.Label(
            comp_frame,
            text="Toplam: 0.00%",
            font=('TkDefaultFont', 9, 'bold')
        )
        self.total_label.pack(anchor="e", pady=5)
        
        # Fraction type selector
        type_frame = ttk.Frame(comp_frame)
        type_frame.pack(fill=tk.X)
        
        ttk.Label(type_frame, text="Oran Tipi:").pack(side=tk.LEFT)
        
        self.fraction_type_var = tk.StringVar(value="molar")
        ttk.Radiobutton(
            type_frame,
            text="Molar %",
            variable=self.fraction_type_var,
            value="molar"
        ).pack(side=tk.LEFT, padx=10)
        
        ttk.Radiobutton(
            type_frame,
            text="Kütlesel %",
            variable=self.fraction_type_var,
            value="mass"
        ).pack(side=tk.LEFT)

    def _create_standard_section(self):
        """Create standard condition selection widgets."""
        frame = ttk.LabelFrame(
            self,
            text="2. Referans Standart Koşullar",
            padding="10"
        )
        frame.pack(fill=tk.X, pady=(0, 10))
        
        # Standard Selection
        ttk.Label(frame, text="Standart Seçimi:").grid(row=0, column=0, sticky="w", padx=5)
        
        self.standard_var = tk.StringVar()
        standards = list(config.STANDARD_CONDITIONS.keys()) + ["Özel..."]
        
        self.standard_combo = ttk.Combobox(
            frame,
            textvariable=self.standard_var,
            values=standards,
            state="readonly",
            width=30
        )
        self.standard_combo.grid(row=0, column=1, sticky="w", padx=5)
        self.standard_combo.current(0)  # Select first (ISO)
        self.standard_combo.bind('<<ComboboxSelected>>', self._on_standard_change)
        
        # Info label
        self.std_info_label = ttk.Label(
            frame,
            text="",
            font=('TkDefaultFont', 8),
            foreground="#666"
        )
        self.std_info_label.grid(row=1, column=0, columnspan=2, sticky="w", padx=5, pady=(5, 0))
        
        # Trigger initial update
        self._on_standard_change()

    def _create_conditions_section(self):
        """Create thermodynamic conditions input widgets."""
        frame = ttk.LabelFrame(
            self,
            text="3. İşletme Koşulları",
            padding="10"
        )
        frame.pack(fill=tk.X, pady=(0, 10))
        
        # Temperature
        ttk.Label(frame, text="Sıcaklık:").grid(row=0, column=0, sticky="w", padx=5)
        
        self.temp_var = tk.DoubleVar(value=15.0)
        ttk.Entry(frame, textvariable=self.temp_var, width=10).grid(row=0, column=1, padx=5)
        
        self.temp_unit_var = tk.StringVar(value="°C")
        temp_units = ["°C", "°F", "K"]
        ttk.Combobox(
            frame,
            textvariable=self.temp_unit_var,
            values=temp_units,
            state="readonly",
            width=5
        ).grid(row=0, column=2, padx=5)
        
        # Pressure
        ttk.Label(frame, text="Basınç:").grid(row=0, column=3, sticky="w", padx=5)
        
        self.press_var = tk.DoubleVar(value=1.01325)
        ttk.Entry(frame, textvariable=self.press_var, width=10).grid(row=0, column=4, padx=5)
        
        self.press_unit_var = tk.StringVar(value="bar(a)")
        press_units = ["bar(a)", "bar(g)", "kPa", "MPa", "psi(a)", "psi(g)", "atm"]
        ttk.Combobox(
            frame,
            textvariable=self.press_unit_var,
            values=press_units,
            state="readonly",
            width=8
        ).grid(row=0, column=5, padx=5)
    
    def _create_volume_method_section(self):
        """Create volume and method selection widgets."""
        volume_frame = ttk.LabelFrame(self, text="3. Hacim ve Metot", padding="10")
        volume_frame.pack(fill=tk.X, pady=10)
        
        # Volume (optional)
        ttk.Label(volume_frame, text="Hacim (ACM - Gerçek m³):").grid(
            row=0, column=0, padx=5, pady=5, sticky="w"
        )
        
        self.volume_entry = ttk.Entry(volume_frame, width=12)
        self.volume_entry.grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Label(volume_frame, text="m³").grid(row=0, column=2, padx=5, pady=5, sticky="w")
        
        # Backend method
        ttk.Label(volume_frame, text="Yöntem:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        
        self.method = tk.StringVar(value=config.DEFAULT_BACKEND)
        methods = config.AVAILABLE_BACKENDS
        self.method_combo = ttk.Combobox(
            volume_frame,
            textvariable=self.method,
            values=methods,
            state="readonly",
            width=15
        )
        self.method_combo.grid(row=1, column=1, padx=5, pady=5, columnspan=2, sticky="ew")
        self.method_combo.grid(row=1, column=1, padx=5, pady=5, columnspan=2, sticky="ew")

    def _update_gas_list(self):
        """Update gas listbox with available gases."""
        self.gas_listbox.delete(0, tk.END)
        for gas in self.gas_list:
            self.gas_listbox.insert(tk.END, gas)
    
    # Event handlers
    
    def _on_gas_search(self, *args):
        """Handle gas search box key release."""
        search_term = self.search_var.get().lower()
        
        self.gas_listbox.delete(0, tk.END)
        
        if search_term:
            filtered = [gas for gas in self.gas_list if search_term in gas.lower()]
            for gas in filtered:
                self.gas_listbox.insert(tk.END, gas)
        else:
            for gas in self.gas_list:
                self.gas_listbox.insert(tk.END, gas)
    
    def _on_add_gas(self):
        """Handle add gas button click."""
        selection = self.gas_listbox.curselection()
        if not selection:
            from natural_gas_g5.ui.dialogs import show_warning
            show_warning("Giriş Hatası", "Lütfen bir gaz seçin.")
            return

        gas_name = self.gas_listbox.get(selection[0])
        
        # Check for duplicates
        existing_items = self.tree.get_children()
        for item in existing_items:
            existing_name = self.tree.item(item)['values'][0]
            if existing_name == gas_name:
                from natural_gas_g5.ui.dialogs import show_warning
                show_warning("Giriş Hatası", f"{gas_name} zaten ekli.")
                return

        # Prompt for fraction (simple dialog for now, or assume user edits later)
        # Ideally we have an entry, but current design has entry elsewhere or removed
        # Let's add with default 0 and ask user to edit, OR bring back the simple fraction entry
        pass # Wait, previous design had a prompt? Using a dialog is cleaner for now to avoid messy UI
        
        # Better: Re-implement the fraction input that was in the design?
        # The new design has "Ekle >>" button. Let's assume it adds with 0 or asks?
        # Let's use a simple input dialog here for stability
        
        from tkinter import simpledialog
        fraction_str = simpledialog.askstring("Oran Girişi", f"{gas_name} için oran girin:")
        
        if not fraction_str: return
        
        try:
             fraction = float(fraction_str.replace(',', '.'))
             validators.validate_gas_fraction(fraction)
             self.tree.insert("", tk.END, values=(gas_name, f"{fraction:.4f}"))
             self._update_total_label()
        except ValueError:
             from natural_gas_g5.ui.dialogs import show_warning
             show_warning("Hata", "Geçersiz sayısal değer.")
        except Exception as e:
             from natural_gas_g5.ui.dialogs import show_warning
             show_warning("Hata", str(e))

    def _on_remove_gas(self):
        """Handle remove gas button click."""
        selected_items = self.tree.selection()
        
        if not selected_items:
            from natural_gas_g5.ui.dialogs import show_warning
            show_warning("Seçim Hatası", "Lütfen silmek için tablodan bir gaz seçin.")
            return
        
        for item in selected_items:
            self.tree.delete(item)
        self._update_total_label()

    def _on_clear_all(self):
        """Clear all gases from composition."""
        for item in self.tree.get_children():
            self.tree.delete(item)
        self._update_total_label()
        
    def _update_total_label(self):
        """Update total composition label."""
        total = 0.0
        for item in self.tree.get_children():
            try:
                val = float(self.tree.item(item)['values'][1])
                total += val
            except: pass
            
        self.total_label.config(text=f"Toplam: {total:.4f}%")
        if abs(total - 100.0) > 0.0001:
            self.total_label.config(foreground="red")
        else:
            self.total_label.config(foreground="green")

    def _on_double_click_composition(self, event):
        """Handle double click on composition tree to edit fraction."""
        region = self.tree.identify("region", event.x, event.y)
        if region != "cell": return
        
        column = self.tree.identify_column(event.x)
        if column != "#2": return # Only fraction
        
        item = self.tree.identify_row(event.y)
        if not item: return
        
        current_val = self.tree.item(item)['values'][1]
        bbox = self.tree.bbox(item, column)
        
        entry = ttk.Entry(self.tree)
        entry.place(x=bbox[0], y=bbox[1], width=bbox[2], height=bbox[3])
        entry.insert(0, str(current_val))
        entry.select_range(0, tk.END)
        entry.focus()
        
        def save(event=None):
            try:
                val = float(entry.get().replace(',', '.'))
                validators.validate_gas_fraction(val)
                values = list(self.tree.item(item, "values"))
                values[1] = f"{val:.4f}"
                self.tree.item(item, values=values)
                self._update_total_label()
                entry.destroy()
            except Exception as e:
                from natural_gas_g5.ui.dialogs import show_warning
                show_warning("Hata", "Geçersiz değer")
                entry.destroy() # Or keep focus? destroy for now to avoid lock
        
        entry.bind("<Return>", save)
        entry.bind("<FocusOut>", lambda e: entry.destroy())
    
    # Public methods for getting inputs
    
    def _on_standard_change(self, event=None):
        """Handle standard selection change."""
        selected = self.standard_var.get()
        
        if selected in config.STANDARD_CONDITIONS:
            # Update info label
            params = config.STANDARD_CONDITIONS[selected]
            t_val = params["T"]
            p_val = params["P"]
            
            # Helper to format meaningful text
            t_c = t_val - 273.15
            p_kpa = p_val / 1000.0
            p_psi = p_val / 6894.76
            
            info_text = f"Referans: {t_c:.2f}°C, {p_kpa:.3f} kPa ({p_psi:.3f} psi)"
            self.std_info_label.config(text=info_text)
            
            # Auto-update conditions if user hasn't manually modified them yet 
            # (Optional: for now we just show info, maybe we can add a checkbox "Sync conditions")
            # Or better: We set these as the "Standard" parameters that passed to calculator
        else:
            self.std_info_label.config(text="Özel tanımlı standart koşullar")

    def get_mixture(self) -> GasMixture:
        """
        Get gas mixture from composition tree.
        
        Returns:
            GasMixture object
            
        Raises:
            ValidationError: If composition is invalid
        """
        # Collect components
        components = []
        for item in self.tree.get_children():
            values = self.tree.item(item)['values']
            name = values[0]
            fraction = float(values[1])
            components.append(GasComponent(name=name, fraction=fraction))
        
        if not components:
            raise ValidationError("Gaz Kompozisyonu", "En az bir gaz bileşeni eklemelisiniz.")
        
        # Create mixture
        mixture = GasMixture(
            components=components,
            fraction_type=self.fraction_type_var.get()
        )
        
        # Validate total
        mixture.validate_total()
        
        return mixture
    
    def get_standard_conditions(self) -> Tuple[float, float, str]:
        """
        Get selected standard conditions.
        
        Returns:
            Tuple of (Temperature K, Pressure Pa, Standard Name)
        """
        selected = self.standard_var.get()
        
        if selected in config.STANDARD_CONDITIONS:
            params = config.STANDARD_CONDITIONS[selected]
            return params["T"], params["P"], selected
        else:
            # Custom or fallback
            return config.T_STANDARD, config.P_STANDARD, "Özel"

    def get_temperature_k(self) -> float:
        """
        Get temperature in Kelvin.
        
        Returns:
            Temperature in Kelvin
            
        Raises:
            ValidationError: If temperature is invalid
        """
        try:
            val = self.temp_var.get()
            unit = self.temp_unit_var.get()
            return converters.convert_temperature_to_K(val, unit)
        except Exception as e:
            if isinstance(e, ValidationError): raise
            raise ValidationError("Sıcaklık", "Geçersiz değer")
    
    def get_pressure_pa(self) -> float:
        """
        Get pressure in Pascals.
        
        Returns:
            Pressure in Pascals
            
        Raises:
            ValidationError: If pressure is invalid
        """
        try:
            val = self.press_var.get()
            unit = self.press_unit_var.get()
            return converters.convert_pressure_to_Pa(val, unit)
        except Exception as e:
            if isinstance(e, ValidationError): raise
            raise ValidationError("Basınç", "Geçersiz değer")
    
    def get_volume_m3(self) -> Optional[float]:
        """
        Get volume in cubic meters (optional).
        
        Returns:
            Volume in m³ or None if not provided
            
        Raises:
            ValidationError: If volume is invalid
        """
        # Assuming self.volume_entry is still the entry widget for volume
        vol_str = self.volume_entry.get().strip()
        
        if not vol_str:
            return None
            
        try:
            val = float(vol_str) # Use the value from the entry directly
            # The original code did not have a vol_unit_var, so we assume m3 for now
            # If unit conversion is needed, self.vol_unit_var would need to be defined
            
            # Simple validation for now, more robust validation can be added
            if not (1e-10 <= val <= 1e9):
                raise ValidationError("Hacim", "Hacim 1e-10 ile 1e9 arasında olmalıdır.")
            
            return val
        except ValueError:
            raise ValidationError("Hacim", "Geçersiz sayısal değer")
    
    def get_backend(self) -> str:
        """
        Get selected backend.
        
        Returns:
            Backend name
            
        Raises:
            ValidationError: If backend is invalid
        """
        backend = self.method.get() # Assuming self.method is still the correct variable
        validators.validate_backend(backend)
        return backend
    
    def set_backend(self, backend: str) -> None:
        """
        Set backend selection.
        
        Args:
            backend: Backend name to set
        """
        self.method.set(backend)
    
    def get_all_inputs(self) -> dict:
        """
        Get all inputs as dictionary.
        
        Returns:
            Dictionary with all input values
        """
        return {
            'mixture': self.get_mixture(),
            'temperature_k': self.get_temperature_k(),
            'pressure_pa': self.get_pressure_pa(),
            'volume_m3': self.get_volume_m3(),
            'backend': self.get_backend(),
        }
    
    def get_save_data(self) -> dict:
        """
        Get all inputs in a format suitable for saving to file.
        
        Returns:
            Dictionary with serializable input values
        """
        # Collect composition
        composition = []
        for item in self.tree.get_children():
            values = self.tree.item(item)['values']
            composition.append({
                "name": values[0],
                "fraction": float(values[1])
            })
        
        # Collect other settings
        data = {
            "composition": composition,
            "fraction_type": self.fraction_type_var.get(),
            "standard": self.standard_var.get(),
            "temperature": {
                "value": self.temp_var.get(),
                "unit": self.temp_unit_var.get()
            },
            "pressure": {
                "value": self.press_var.get(),
                "unit": self.press_unit_var.get()
            },
            "volume": self.volume_entry.get().strip() or None,
            "backend": self.method.get()
        }
        
        return data
    
    def set_load_data(self, data: dict) -> None:
        """
        Load inputs from a dictionary (typically from a saved file).
        
        Args:
            data: Dictionary with saved input values
        """
        # Clear existing composition
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Load composition
        composition = data.get("composition", [])
        for comp in composition:
            name = comp.get("name", "")
            fraction = comp.get("fraction", 0.0)
            self.tree.insert("", "end", values=(name, f"{fraction:.4f}"))
        
        self._update_total_label()
        
        # Load fraction type
        if "fraction_type" in data:
            self.fraction_type_var.set(data["fraction_type"])
        
        # Load standard
        if "standard" in data:
            self.standard_var.set(data["standard"])
            self._on_standard_change()
        
        # Load temperature
        if "temperature" in data:
            temp_data = data["temperature"]
            if "value" in temp_data:
                self.temp_var.set(temp_data["value"])
            if "unit" in temp_data:
                self.temp_unit_var.set(temp_data["unit"])
        
        # Load pressure
        if "pressure" in data:
            press_data = data["pressure"]
            if "value" in press_data:
                self.press_var.set(press_data["value"])
            if "unit" in press_data:
                self.press_unit_var.set(press_data["unit"])
        
        # Load volume
        if "volume" in data and data["volume"]:
            self.volume_entry.delete(0, "end")
            self.volume_entry.insert(0, str(data["volume"]))
        
        # Load backend
        if "backend" in data:
            self.method.set(data["backend"])

