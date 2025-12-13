"""
Main application window.

Coordinates between input panel, output panel, calculator, and user interactions.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import logging
import os
from pathlib import Path

from natural_gas_g5.config.settings import config
from natural_gas_g5.models.calculator import ThermoCalculator, COOLPROP_AVAILABLE
from natural_gas_g5.core.exceptions import (
    ValidationError,
    BackendNotAvailableError,
    ThermoCalculationError
)
from natural_gas_g5.ui.input_panel import InputPanel
from natural_gas_g5.ui.output_panel import OutputPanel
from natural_gas_g5.ui import dialogs
from natural_gas_g5.utils.report_generator import ReportGenerator
from natural_gas_g5.utils.data_serializer import (
    save_inputs_to_file,
    load_inputs_from_file,
    validate_loaded_data,
    DataSerializationError,
    FILE_EXTENSION,
    FILE_TYPE_NAME
)
from natural_gas_g5.utils.updater import UpdateChecker


class ThermoApp(tk.Tk):
    """
    Main application window.
    
    Manages the GUI, user interactions, and calculation workflow.
    """
    
    def __init__(self):
        """Initialize main application window."""
        super().__init__()
        
        self.title(config.WINDOW_TITLE)
        self.geometry(f"{config.WINDOW_WIDTH}x{config.WINDOW_HEIGHT}")
        
        self.logger = logging.getLogger(__name__)
        self.logger.info("Initializing ThermoApp")
        
        # Load gas list
        self.gas_list = self._load_gas_list()
        
        # Apply theme
        style = ttk.Style(self)
        style.theme_use(config.UI_THEME)
        
        # Initialize calculator
        self.calculator = ThermoCalculator()
        
        # Create UI
        self._create_menu()
        self._create_main_layout()
        self._create_status_bar()
        
        # Show welcome message
        self.after(100, self._show_welcome)
    
    def _load_gas_list(self) -> list:
        """
        Load gas list from CoolProp or use fallback.
        
        Returns:
            List of gas names
        """
        if COOLPROP_AVAILABLE:
            try:
                import CoolProp.CoolProp as CP
                fluids = CP.get_global_param_string("FluidsList")
                if fluids:
                    gas_list = sorted([f.strip() for f in fluids.split(',') if f.strip()])
                    self.logger.info(f"Loaded {len(gas_list)} gases from CoolProp")
                    return gas_list
            except Exception as e:
                self.logger.error(f"Failed to load CoolProp gas list: {e}")
        
        # Fallback list
        self.logger.warning("Using fallback gas list")
        messagebox.showwarning(
            "CoolProp Uyarısı",
            "CoolProp akışkan listesi yüklenemedi.\n"
            "Kısıtlı yedek akışkan listesi kullanılıyor."
        )
        return config.FALLBACK_GAS_LIST
    
    def _create_menu(self):
        """Create menu bar."""
        menubar = tk.Menu(self)
        self.config(menu=menubar)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Dosya", menu=file_menu)
        file_menu.add_command(label="Aç...", command=self._on_load_data, accelerator="Ctrl+O")
        file_menu.add_command(label="Kaydet...", command=self._on_save_data, accelerator="Ctrl+S")
        file_menu.add_separator()
        file_menu.add_command(label="Rapor Kaydet", command=self._on_save_report)
        file_menu.add_separator()
        file_menu.add_command(label="Çıkış", command=self.quit)
        
        # Keyboard shortcuts
        self.bind_all("<Control-o>", lambda e: self._on_load_data())
        self.bind_all("<Control-s>", lambda e: self._on_save_data())
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Yardım", menu=help_menu)
        help_menu.add_command(label="Kullanım Kılavuzu", command=dialogs.show_user_guide_dialog)
        help_menu.add_separator()
        help_menu.add_command(label="Güncellemeleri Denetle", command=self._check_for_updates_manual)
        help_menu.add_separator()
        help_menu.add_command(label="Hakkında", command=dialogs.show_about_dialog)
    
    def _create_main_layout(self):
        """Create main content layout with input and output panels."""
        main_content = ttk.Frame(self, padding="10")
        main_content.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        
        # Input panel (left side)
        input_frame = ttk.Frame(main_content, padding="10")
        input_frame.pack(side=tk.LEFT, fill=tk.Y, expand=False, padx=10, pady=10)
        
        self.input_panel = InputPanel(input_frame, self.gas_list)
        self.input_panel.pack(fill=tk.BOTH, expand=True)
        
        # Calculate button
        self.calc_button = ttk.Button(
            input_frame,
            text="Hesapla",
            command=self._on_calculate
        )
        self.calc_button.pack(pady=15, fill=tk.X, ipady=5)
        
        # Output panel (right side)
        output_frame = ttk.Frame(main_content, padding="10")
        output_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.output_panel = OutputPanel(output_frame)
        self.output_panel.pack(fill=tk.BOTH, expand=True)
        
        # Report button
        report_button = ttk.Button(
            output_frame,
            text="Sonuçları Raporla (.txt)",
            command=self._on_save_report
        )
        report_button.pack(pady=10, fill=tk.X, ipady=5)
    
    def _create_status_bar(self):
        """Create status bar at bottom."""
        self.status_var = tk.StringVar(value="Hazır.")
        status_frame = ttk.Frame(self)
        status_frame.pack(side=tk.BOTTOM, fill=tk.X)
        
        status_label = ttk.Label(
            status_frame,
            textvariable=self.status_var,
            relief=tk.SUNKEN,
            anchor=tk.W
        )
        status_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5, pady=2)
        
        self.progress_bar = ttk.Progressbar(status_frame, mode='indeterminate', length=100)
    
    def _show_welcome(self):
        """Show welcome/new features message."""
        dialogs.show_new_features_info()
    
    # Event handlers
    
    def _on_calculate(self):
        """Handle calculate button click."""
        # Validate inputs
        try:
            inputs = self.input_panel.get_all_inputs()
        except ValidationError as e:
            dialogs.show_error("Giriş Hatası", str(e))
            return
        except Exception as e:
            self.logger.error(f"Input validation error: {e}", exc_info=True)
            dialogs.show_error("Giriş Hatası", f"Beklenmeyen hata: {str(e)}")
            return
        
        # Check HEOS compatibility
        try:
            # Get inputs
            mixture = self.input_panel.get_mixture()
            temp_k = self.input_panel.get_temperature_k()
            press_pa = self.input_panel.get_pressure_pa()
            vol_m3 = self.input_panel.get_volume_m3()
            backend = self.input_panel.get_backend()
            
            # Get standard conditions
            std_T, std_P, std_name = self.input_panel.get_standard_conditions()
            
            # Package inputs
            inputs = {
                "mixture": mixture,
                "temp_k": temp_k,
                "press_pa": press_pa,
                "vol_m3": vol_m3,
                "backend": backend,
                "standard_T": std_T,
                "standard_P": std_P,
                "standard_name": std_name
            }
            
            # Show progress
            self.status_var.set("Hesaplanıyor...")
            self.config(cursor="watch") # Changed self.root to self
            self.calc_button.state(['disabled'])
            
            # Run in thread
            thread = threading.Thread(
                target=self._run_calculation,
                args=(inputs,),
                daemon=True
            )
            thread.start()
            
        except ThermoCalculationError as e:
            messagebox.showerror("Giriş Hatası", str(e))
        except Exception as e:
            messagebox.showerror("Hata", f"Beklenmeyen hata: {e}")
            logging.error(f"Input processing failed: {e}", exc_info=True)

    def _run_calculation(self, inputs: dict):
        """
        Run calculation in background thread.
        
        Args:
            inputs: Dictionary of validated inputs
        """
        try:
            # Extract inputs
            mixture = inputs["mixture"]
            temp_k = inputs["temp_k"]
            press_pa = inputs["press_pa"]
            vol_m3 = inputs["vol_m3"]
            
            # Set backend
            self.calculator.backend = inputs["backend"]
            
            # Calculate
            result = self.calculator.calculate_properties(
                mixture=mixture,
                temperature_k=temp_k,
                pressure_pa=press_pa,
                volume_m3=vol_m3,
                standard_T=inputs.get("standard_T", config.T_STANDARD),
                standard_P=inputs.get("standard_P", config.P_STANDARD),
                standard_name=inputs.get("standard_name")
            )
            
            # Check if fallback was needed (if calculator supports tracking)
            # Currently we use primary calculation directly
            # If we wanted auto fallback for main calc:
            # result, used = self.calculator.calculate_with_fallback(...)
            
            used_backend = self.calculator.backend
            
            # Schedule success update
            self.after(0, self._on_calculation_success, result, used_backend, inputs) # Changed self.root to self
            
        except Exception as e:
            # Schedule error update
            self.after(0, self._on_calculation_error, e) # Changed self.root to self
    
    def _on_calculation_success(self, result, used_backend: str, inputs: dict):
        """
        Handle successful calculation.
        
        Args:
            result: Calculation result
            used_backend: Backend that was used
            inputs: Original inputs
        """
        # Stop progress
        self.progress_bar.stop()
        self.progress_bar.pack_forget()
        
        # Display results
        self.output_panel.display_results(result)
        
        # Store for report generation
        self.last_result = result
        self.last_inputs = inputs
        
        # Show warnings if applicable
        if result.heating:
            dialogs.show_heating_value_method_warning(result.heating.calculation_method)
        
        if used_backend != inputs['backend']:
            dialogs.show_backend_used_info(inputs['backend'], used_backend)
            self.status_var.set(
                f"Hesaplama tamamlandı. "
                f"({inputs['backend']} yerine {used_backend} kullanıldı)"
            )
        else:
            self.status_var.set("Hesaplama tamamlandı.")
        
        # Re-enable UI
        self.calc_button.state(['!disabled'])
        self.config(cursor="")
    
    def _on_calculation_error(self, error: Exception):
        """
        Handle calculation error.
        
        Args:
            error: Exception that occurred
        """
        # Stop progress
        self.progress_bar.stop()
        self.progress_bar.pack_forget()
        
        # Re-enable UI
        self.calc_button.state(['!disabled'])
        self.config(cursor="")
        
        # Get log lines
        log_lines = self._get_recent_log_lines(10)
        
        # Display error
        self.output_panel.display_error(str(error), log_lines)
        self.status_var.set("Hesaplama hatası oluştu.")
        
        # Show error dialog
        dialogs.show_error(
            "Hesaplama Hatası",
            f"Hesaplama sırasında bir hata oluştu:\n\n{str(error)}\n\n"
            "Detaylar için Sonuçlar Tablosunu kontrol edin."
        )
    
    def _get_recent_log_lines(self, count: int = 10) -> list:
        """
        Get recent lines from log file.
        
        Args:
            count: Number of lines to retrieve
            
        Returns:
            List of log lines
        """
        log_file = config.LOG_FILE
        
        if not os.path.exists(log_file):
            return []
        
        try:
            with open(log_file, 'r', encoding='utf-8-sig') as f:
                lines = f.readlines()
                return [line.strip() for line in lines[-count:]]
        except Exception as e:
            self.logger.error(f"Could not read log file: {e}")
            return [f"Log okunamadı: {e}"]
    
    def _on_save_report(self):
        """Handle save report button click."""
        if not hasattr(self, 'last_result') or self.last_result is None:
            dialogs.show_warning("Rapor Hatası", "Önce bir hesaplama yapmalısınız.")
            return
        
        try:
            # Ask for file path
            file_path = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[("Metin Dosyaları", "*.txt")],
                title="Raporu Kaydet"
            )
            
            if not file_path:
                return
            
            # Prepare input parameters for report
            inputs = self.last_inputs
            input_params = {
                'temperature': inputs['temperature_display'],
                'pressure': inputs['pressure_display'],
                'backend': self.last_result.backend_used,
                'volume': inputs.get('volume_display'),
                'fraction_type': inputs['mixture'].fraction_type
            }
            
            # Get gas composition
            gas_composition = [
                (comp.name, comp.fraction)
                for comp in inputs['mixture'].components
            ]
            
            # Get results
            results = self.output_panel.get_results_as_list()
            
            # Generate and save report with log file
            ReportGenerator.generate_and_save(
                input_params,
                results,
                gas_composition,
                file_path,
                log_file=config.LOG_FILE  # Pass log file for timestamped logs
            )
            
            dialogs.show_info("Başarılı", f"Rapor başarıyla kaydedildi:\n{file_path}")
            self.status_var.set(f"Rapor kaydedildi: {file_path}")
            
        except Exception as e:
            self.logger.error(f"Report generation failed: {e}", exc_info=True)
            dialogs.show_error("Rapor Hatası", f"Rapor kaydedilirken bir hata oluştu:\n{e}")

    def _on_save_data(self):
        """Handle save data menu item."""
        try:
            # Get data from input panel
            data = self.input_panel.get_save_data()
            
            # Check if there's any data to save
            if not data.get("composition"):
                dialogs.show_warning("Kaydetme Hatası", "Kaydedilecek gaz bileşeni yok.")
                return
            
            # Ask for file path
            file_path = filedialog.asksaveasfilename(
                defaultextension=FILE_EXTENSION,
                filetypes=[(FILE_TYPE_NAME, f"*{FILE_EXTENSION}"), ("Tüm Dosyalar", "*.*")],
                title="Verileri Kaydet"
            )
            
            if not file_path:
                return
            
            # Save to file
            save_inputs_to_file(data, file_path)
            
            dialogs.show_info("Başarılı", f"Veriler başarıyla kaydedildi:\n{file_path}")
            self.status_var.set(f"Kaydedildi: {file_path}")
            
        except DataSerializationError as e:
            dialogs.show_error("Kaydetme Hatası", str(e))
        except Exception as e:
            self.logger.error(f"Save data failed: {e}", exc_info=True)
            dialogs.show_error("Kaydetme Hatası", f"Beklenmeyen hata: {e}")

    def _on_load_data(self):
        """Handle load data menu item."""
        try:
            # Ask for file path
            file_path = filedialog.askopenfilename(
                defaultextension=FILE_EXTENSION,
                filetypes=[(FILE_TYPE_NAME, f"*{FILE_EXTENSION}"), ("Tüm Dosyalar", "*.*")],
                title="Verileri Aç"
            )
            
            if not file_path:
                return
            
            # Load from file
            data = load_inputs_from_file(file_path)
            
            # Validate data
            if not validate_loaded_data(data):
                dialogs.show_warning("Yükleme Uyarısı", "Dosya formatı beklenen şekilde değil. Bazı veriler yüklenemeyebilir.")
            
            # Apply to input panel
            self.input_panel.set_load_data(data)
            
            dialogs.show_info("Başarılı", f"Veriler başarıyla yüklendi:\n{file_path}")
            self.status_var.set(f"Yüklendi: {file_path}")
            
        except DataSerializationError as e:
            dialogs.show_error("Yükleme Hatası", str(e))
        except Exception as e:
            dialogs.show_error("Yükleme Hatası", f"Beklenmeyen hata: {e}")
            
    def _check_for_updates_manual(self):
        """Check for updates manually triggered by user."""
        try:
            self.status_var.set("Güncellemeler kontrol ediliyor...")
            self.config(cursor="watch")
            self.update();
            
            checker = UpdateChecker()
            has_update, update_info = checker.check_for_updates()
            
            self.config(cursor="")
            
            if has_update:
                msg = (
                    f"✨ YENİ SÜRÜM MEVCUT!\n\n"
                    f"Versiyon: {update_info.get('version')}\n"
                    f"Tarih: {update_info.get('date')}\n\n"
                    f"Değişiklikler:\n{update_info.get('changelog', '-')}\n\n"
                    f"İndirme sayfasına gitmek ister misiniz?"
                )
                if messagebox.askyesno("Güncelleme Mevcut", msg):
                    checker.open_download_page(update_info.get('download_url'))
            else:
                messagebox.showinfo(
                    "Güncel",
                    f"Programınız güncel.\n"
                    f"Versiyon: {config.APP_VERSION}"
                )
                
            self.status_var.set("Hazır.")
            
        except Exception as e:
            self.config(cursor="")
            self.logger.error(f"Manual update check failed: {e}")
            messagebox.showerror("Hata", f"Güncelleme kontrolü başarısız:\n{e}")
            self.status_var.set("Güncelleme kontrolü başarısız.")
