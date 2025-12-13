"""
Output panel component.

Displays calculation results in a TreeView widget with selectable unit systems.
"""

import tkinter as tk
from tkinter import ttk
from typing import List, Tuple, Optional

from natural_gas_g5.models.calculation_result import CalculationResult


class OutputPanel(ttk.Frame):
    """
    Output panel for displaying calculation results.
    
    Shows results in a TreeView with columns: Property, Value, Unit
    """
    
    def __init__(self, parent, *args, **kwargs):
        """
        Initialize output panel.
        
        Args:
            parent: Parent widget
        """
        super().__init__(parent, *args, **kwargs)
        
        # Store current result for re-displaying with different units
        self.current_result: Optional[CalculationResult] = None
        
        self.create_widgets()
    
    def create_widgets(self):
        """Create and layout widgets."""
        # Main label frame
        main_frame = ttk.LabelFrame(
            self,
            text="4. Hesaplama Sonuçları",
            padding="10"
        )
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Notebook for tabs
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # ============== TAB 1: Results ==============
        results_tab = ttk.Frame(self.notebook)
        self.notebook.add(results_tab, text="Sonuçlar")
        
        # Unit system selector
        unit_select_frame = ttk.Frame(results_tab)
        unit_select_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(unit_select_frame, text="Birim Sistemi:").pack(side=tk.LEFT, padx=(0, 5))
        
        self.unit_system_var = tk.StringVar(value="SI")
        unit_combo = ttk.Combobox(
            unit_select_frame,
            textvariable=self.unit_system_var,
            values=["SI", "Imperial", "Mixed"],
            state="readonly",
            width=15
        )
        unit_combo.pack(side=tk.LEFT)
        unit_combo.bind('<<ComboboxSelected>>', self._on_unit_change)
        
        # TreeView with columns
        cols = ("Özellik", "Değer", "Birim")
        self.results_tree = ttk.Treeview(
            results_tab,
            columns=cols,
            show="headings",
            height=20
        )
        
        # Configure columns
        self.results_tree.heading("Özellik", text="Özellik")
        self.results_tree.heading("Değer", text="Değer")
        self.results_tree.heading("Birim", text="Birim")
        
        self.results_tree.column("Özellik", width=250)
        self.results_tree.column("Değer", width=170)
        self.results_tree.column("Birim", width=120)
        
        # Scrollbar for results
        scrollbar = ttk.Scrollbar(
            results_tab,
            orient=tk.VERTICAL,
            command=self.results_tree.yview
        )
        self.results_tree.configure(yscrollcommand=scrollbar.set)
        
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.results_tree.pack(fill=tk.BOTH, expand=True)
        
        # Configure tag styles
        self.results_tree.tag_configure(
            'header',
            background='#E0E0E0',
            font=('TkDefaultFont', 9, 'bold')
        )
        self.results_tree.tag_configure(
            'error_header',
            background='#FFCCCC',
            font=('TkDefaultFont', 9, 'bold')
        )
        
        # ============== TAB 2: Logs ==============
        logs_tab = ttk.Frame(self.notebook)
        self.notebook.add(logs_tab, text="Loglar")
        
        # Log level filter
        filter_frame = ttk.Frame(logs_tab)
        filter_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(filter_frame, text="Seviye:").pack(side=tk.LEFT, padx=(0, 5))
        
        self.log_level_var = tk.StringVar(value="Hepsi")
        level_combo = ttk.Combobox(
            filter_frame,
            textvariable=self.log_level_var,
            values=["Hepsi", "DEBUG", "INFO", "WARNING", "ERROR"],
            state="readonly",
            width=10
        )
        level_combo.pack(side=tk.LEFT)
        level_combo.bind('<<ComboboxSelected>>', self._on_log_level_change)
        
        # Clear button
        ttk.Button(
            filter_frame,
            text="Temizle",
            command=self._clear_logs
        ).pack(side=tk.RIGHT, padx=5)
        
        # Auto-scroll checkbox
        self.auto_scroll_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            filter_frame,
            text="Otomatik Kaydır",
            variable=self.auto_scroll_var
        ).pack(side=tk.RIGHT)
        
        # Log text widget
        log_frame = ttk.Frame(logs_tab)
        log_frame.pack(fill=tk.BOTH, expand=True)
        
        self.log_text = tk.Text(
            log_frame,
            wrap=tk.WORD,
            height=20,
            font=('Consolas', 9),
            state=tk.DISABLED
        )
        
        log_scrollbar = ttk.Scrollbar(
            log_frame,
            orient=tk.VERTICAL,
            command=self.log_text.yview
        )
        self.log_text.configure(yscrollcommand=log_scrollbar.set)
        
        log_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # Configure log text tags for colors
        self.log_text.tag_configure("DEBUG", foreground="#888888")
        self.log_text.tag_configure("INFO", foreground="#000000")
        self.log_text.tag_configure("WARNING", foreground="#CC8800")
        self.log_text.tag_configure("ERROR", foreground="#CC0000")
        self.log_text.tag_configure("CRITICAL", foreground="#FF0000", background="#FFEEEE")
        
        # Setup logging handler
        self._setup_log_handler()
    
    def _setup_log_handler(self):
        """Setup custom logging handler to capture logs to Text widget."""
        import logging
        
        # Store all log records for filtering
        self.log_records = []
        
        # Level name to numeric mapping
        self.level_map = {
            "Hepsi": 0,
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR
        }
        
        panel = self  # Reference for inner class
        
        class TextHandler(logging.Handler):
            def __init__(self, text_widget, auto_scroll_var):
                super().__init__()
                self.text_widget = text_widget
                self.auto_scroll_var = auto_scroll_var
            
            def emit(self, record):
                msg = self.format(record)
                level = record.levelname
                
                # Store record for filtering
                panel.log_records.append((msg, level, record.levelno))
                
                # Check if should display based on current filter
                selected_level = panel.log_level_var.get()
                min_level = panel.level_map.get(selected_level, 0)
                
                if record.levelno >= min_level:
                    def append():
                        self.text_widget.configure(state=tk.NORMAL)
                        self.text_widget.insert(tk.END, msg + '\n', level)
                        if self.auto_scroll_var.get():
                            self.text_widget.see(tk.END)
                        self.text_widget.configure(state=tk.DISABLED)
                    
                    # Schedule on main thread
                    self.text_widget.after(0, append)
        
        # Create and add handler
        self.text_handler = TextHandler(self.log_text, self.auto_scroll_var)
        self.text_handler.setFormatter(
            logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s', datefmt='%H:%M:%S')
        )
        
        # Add to root logger
        logging.getLogger().addHandler(self.text_handler)
    
    def _on_log_level_change(self, event=None):
        """Handle log level filter change - refresh display."""
        selected_level = self.log_level_var.get()
        min_level = self.level_map.get(selected_level, 0)
        
        # Clear and re-display filtered logs
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        
        for msg, level, levelno in self.log_records:
            if levelno >= min_level:
                self.log_text.insert(tk.END, msg + '\n', level)
        
        if self.auto_scroll_var.get():
            self.log_text.see(tk.END)
        
        self.log_text.configure(state=tk.DISABLED)
    
    def _clear_logs(self):
        """Clear log text widget."""
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.configure(state=tk.DISABLED)
    
    def display_results(self, result: CalculationResult) -> None:
        """
        Display calculation results in tree view.
        
        Args:
            result: Calculation result object
        """
        # Clear existing results
        self.clear_results()
        
        # Store result for unit switching
        self.current_result = result
        
        # Get current unit system
        unit_system = self.unit_system_var.get()
        
        # Display Standard Info header
        std_info = "Standart: "
        if result.standard.standard_name:
            std_info += f"{result.standard.standard_name} "
        
        # Format T and P for display info
        t_c = result.standard.reference_temperature - 273.15
        p_kpa = result.standard.reference_pressure / 1000.0
        
        std_info += f"({t_c:.2f}°C, {p_kpa:.3f} kPa)"
        
        self.results_tree.insert(
            "",
            tk.END,
            values=(f"--- {std_info} ---", "", ""),
            tags=('header',)
        )
        
        # Get formatted results with selected unit system
        results_list = result.to_display_list(unit_system=unit_system)
        
        # Insert into tree
        for prop_name, value, unit in results_list:
            if prop_name.startswith('-'):
                # Header row
                self.results_tree.insert("", tk.END, values=(prop_name, value, unit), tags=('header',))
            else:
                # Normal row
                self.results_tree.insert("", tk.END, values=(prop_name, value, unit))
    
    def _on_unit_change(self, event=None) -> None:
        """
        Handle unit system change event.
        
        Re-displays current results with new unit system.
        """
        if self.current_result is not None:
            # Re-display with new unit system
            self.display_results(self.current_result)
    
    def display_error(self, error_message: str, log_lines: List[str] = None) -> None:
        """
        Display error message and optional log lines.
        
        Args:
            error_message: Main error message
            log_lines: Optional list of log lines to display
        """
        self.clear_results()
        
        # Error header
        self.results_tree.insert(
            "",
            tk.END,
            values=("--- KRİTİK HESAPLAMA HATASI ---", "", ""),
            tags=('error_header',)
        )
        
        # Error message
        self.results_tree.insert(
            "",
            tk.END,
            values=("Hata Mesajı", str(error_message), "")
        )
        
        # Log lines if provided
        if log_lines:
            self.results_tree.insert(
                "",
                tk.END,
                values=("- SON HATA LOGU (İPUCU) -", "", ""),
                tags=('error_header',)
            )
            
            for line in log_lines:
                self.results_tree.insert(
                    "",
                    tk.END,
                    values=(line.strip(), "", "")
                )
    
    def clear_results(self) -> None:
        """Clear all results from tree view."""
        for item in self.results_tree.get_children():
            self.results_tree.delete(item)
    
    def get_results_as_list(self) -> List[Tuple[str, str, str]]:
        """
        Get current results as list of tuples.
        
        Returns:
            List of (property, value, unit) tuples
        """
        results = []
        for item in self.results_tree.get_children():
            values = self.results_tree.item(item)['values']
            results.append(tuple(values))
        return results
