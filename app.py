import customtkinter as ctk
from analysis import check_stock
import threading
import time
import json
import os
import sys
from datetime import datetime
import pytz

STOCKS_FILE = "stocks.json"

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.spinner_chars = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
        self.spinner_idx = 0
        self.is_loading = False

        # Datos de las listas
        self.stock_lists = {"Mi Portfolio": []}
        self.active_list_name = "Mi Portfolio"

        # --- CONFIGURACIÓN DE LA VENTANA ---
        self.title("Monitor de Alertas de Acciones v2")
        self.geometry("900x700")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.is_auto_analyzing = ctk.BooleanVar(value=False)
        self.last_analysis_time = None
        
        # Mapping user-friendly period names to yfinance (period, interval)
        self.YFINANCE_PERIOD_INTERVAL_MAP = {
            "1h": {"period": "60d", "interval": "1h"},  # Max 60 days for 1h interval
            "1 dia": {"period": "5y", "interval": "1d"}, # 5 years of daily data
            "1 semana": {"period": "5y", "interval": "1wk"}, # 5 years of weekly data
        }
        self.period_var = ctk.StringVar(value="1 dia") # Default period label

        # --- FRAME SUPERIOR (CONTROLES) ---
        self.top_frame = ctk.CTkFrame(self, corner_radius=10)
        self.top_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        self.top_frame.grid_columnconfigure(1, weight=1)
        
        # Fila 0: Gestión de Listas
        self.label_list = ctk.CTkLabel(self.top_frame, text="Lista:", font=ctk.CTkFont(size=14, weight="bold"))
        self.label_list.grid(row=0, column=0, padx=10, pady=5, sticky="w")
        
        self.list_selector = ctk.CTkOptionMenu(self.top_frame, values=list(self.stock_lists.keys()), command=self.change_active_list)
        self.list_selector.grid(row=0, column=1, padx=10, pady=5, sticky="w")
        
        self.list_buttons_frame = ctk.CTkFrame(self.top_frame, fg_color="transparent")
        self.list_buttons_frame.grid(row=0, column=2, padx=10, pady=5, sticky="e")
        
        self.new_list_btn = ctk.CTkButton(self.list_buttons_frame, text="+ Nueva", width=80, command=self.create_new_list)
        self.new_list_btn.pack(side="left", padx=2)
        
        self.del_list_btn = ctk.CTkButton(self.list_buttons_frame, text="- Borrar", width=80, fg_color="#A52A2A", hover_color="#8B0000", command=self.delete_current_list)
        self.del_list_btn.pack(side="left", padx=2)

        # Fila 1: Tickers
        self.label_tickers = ctk.CTkLabel(self.top_frame, text="Acciones:", font=ctk.CTkFont(size=14))
        self.label_tickers.grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.entry_tickers = ctk.CTkEntry(self.top_frame, placeholder_text="ej: AAPL, TSLA, GGAL, MELI")
        self.entry_tickers.grid(row=1, column=1, padx=10, pady=5, sticky="ew")
        
        # BIND ENTER KEY
        self.entry_tickers.bind("<Return>", lambda event: self.start_analysis_thread())

        self.analyze_button = ctk.CTkButton(self.top_frame, text="Analizar", command=self.start_analysis_thread)
        self.analyze_button.grid(row=1, column=2, padx=10, pady=5)
        
        self.auto_checkbox = ctk.CTkCheckBox(self.top_frame, text="Análisis Automático (cada 10 min)", variable=self.is_auto_analyzing, command=self.toggle_auto_analysis)
        self.auto_checkbox.grid(row=2, column=1, columnspan=2, padx=10, pady=5, sticky="w")

        # --- FRAME PARA SELECCIÓN DE TEMPORALIDAD ---
        self.periods_frame = ctk.CTkFrame(self.top_frame, corner_radius=10)
        self.periods_frame.grid(row=2, column=0, columnspan=3, padx=5, pady=5, sticky="ew")
        self.periods_frame.grid_columnconfigure(0, weight=0) # Label
        for i in range(1, len(self.YFINANCE_PERIOD_INTERVAL_MAP) + 1): # For radiobuttons
            self.periods_frame.grid_columnconfigure(i, weight=1)

        self.label_periods = ctk.CTkLabel(self.periods_frame, text="Temporalidad:", font=ctk.CTkFont(size=12))
        self.label_periods.grid(row=0, column=0, padx=(10, 5), pady=5, sticky="w")

        for i, period_label in enumerate(self.YFINANCE_PERIOD_INTERVAL_MAP.keys()):
            rb = ctk.CTkRadioButton(self.periods_frame, text=period_label, variable=self.period_var, value=period_label, command=self.period_changed)
            rb.grid(row=0, column=i+1, padx=2, pady=5, sticky="ew")
        
        # --- TEXTBOX DE RESULTADOS ---
        self.results_textbox = ctk.CTkTextbox(self, corner_radius=10, font=ctk.CTkFont(family="Consolas", size=13))
        self.results_textbox.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="nsew")
        self.configure_tags()
        self.update_results([{'text': "Bienvenido. Cargue acciones y presione 'Analizar' o active el modo automático.", 'status': 'info'}])

        # --- CARGA INICIAL Y LOOP AUTOMÁTICO ---
        self.load_stocks()
        self.auto_analysis_thread = None
        self.protocol("WM_DELETE_WINDOW", self.on_closing) # Manejar cierre de ventana
        self.run_auto = True

    def period_changed(self):
        # Trigger analysis if not in auto mode and tickers are present
        if not self.is_auto_analyzing.get() and self.entry_tickers.get():
            self.start_analysis_thread()

    def configure_tags(self):
        self.results_textbox.tag_config('info', foreground='gray80')
        self.results_textbox.tag_config('pass', foreground='#32CD32') # Verde lima
        self.results_textbox.tag_config('fail', foreground='#FF4500') # Naranja-Rojo
        self.results_textbox.tag_config('alert_buy', foreground='#00FFFF') # Cyan
        self.results_textbox.tag_config('alert_sell', foreground='#FFD700') # Oro
        self.results_textbox.tag_config('spinner', foreground='#00FFFF') # Color del spinner
        self.results_textbox.configure(state="disabled")

    def animate_spinner(self):
        if self.is_loading:
            char = self.spinner_chars[self.spinner_idx % len(self.spinner_chars)]
            self.results_textbox.configure(state="normal")
            # Overwrite the character at the very end
            self.results_textbox.delete("end-2c", "end-1c")
            self.results_textbox.insert("end-1c", char, "spinner")
            self.results_textbox.configure(state="disabled")
            self.spinner_idx += 1
            self.after(80, self.animate_spinner)
        else:
            # Clean up spinner character and clear line
            self.results_textbox.configure(state="normal")
            self.results_textbox.delete("end-2c", "end-1c")
            self.results_textbox.configure(state="disabled")

    def start_analysis_thread(self, from_auto=False):
        if not from_auto and self.is_auto_analyzing.get():
            self.update_results([{'text': "Info: El análisis automático ya está en ejecución.", 'status': 'info'}])
            return
            
        self.analyze_button.configure(state="disabled")
        self.last_analysis_time = datetime.now()
        
        if not from_auto:
            self.clear_textbox()
            self.results_textbox.see("0.0") # Scroll to top when starting a new analysis
            
            # Start the line without a newline so spinner can append
            self.results_textbox.configure(state="normal")
            self.results_textbox.insert("end", "Iniciando análisis manual...  ", "info")
            self.results_textbox.configure(state="disabled")
            
            self.is_loading = True
            self.animate_spinner()

        selected_period_label = self.period_var.get()
        yfinance_params = self.YFINANCE_PERIOD_INTERVAL_MAP.get(selected_period_label, {"period": "1y", "interval": "1d"}) # Default to 1y, 1d
        yfinance_period = yfinance_params["period"]
        yfinance_interval = yfinance_params["interval"]
        
        thread = threading.Thread(target=self.run_analysis, args=(yfinance_period, yfinance_interval,))
        thread.daemon = True
        thread.start()

    # --- LÓGICA DE GESTIÓN DE LISTAS ---
    def change_active_list(self, new_name):
        # Primero guardamos lo que haya en la lista actual antes de cambiar
        self.update_active_list_data()
        
        # Cambiamos a la nueva lista
        self.active_list_name = new_name
        tickers = self.stock_lists.get(new_name, [])
        
        # Actualizamos el entry
        self.entry_tickers.delete(0, "end")
        self.entry_tickers.insert(0, ", ".join(tickers))
        self.save_stocks()

    def update_active_list_data(self):
        # Lee el entry y lo guarda en el diccionario de memoria
        tickers_input = self.entry_tickers.get()
        tickers_list = [t.strip().upper() for t in tickers_input.split(',') if t.strip()]
        self.stock_lists[self.active_list_name] = tickers_list

    def create_new_list(self):
        dialog = ctk.CTkInputDialog(text="Nombre de la nueva lista:", title="Nueva Lista")
        name = dialog.get_input()
        if name and name.strip():
            name = name.strip()
            if name not in self.stock_lists:
                self.stock_lists[name] = []
                self.list_selector.configure(values=list(self.stock_lists.keys()))
                self.list_selector.set(name)
                self.change_active_list(name)
            else:
                self.update_results([{'text': "Esa lista ya existe.", 'status': 'fail'}])

    def delete_current_list(self):
        if len(self.stock_lists) <= 1:
            self.update_results([{'text': "No puedes borrar la única lista.", 'status': 'fail'}])
            return
        
        name_to_del = self.active_list_name
        del self.stock_lists[name_to_del]
        
        # Seleccionar la primera lista disponible
        self.active_list_name = list(self.stock_lists.keys())[0]
        self.list_selector.configure(values=list(self.stock_lists.keys()))
        self.list_selector.set(self.active_list_name)
        
        # Actualizar el entry con la nueva lista activa
        tickers = self.stock_lists[self.active_list_name]
        self.entry_tickers.delete(0, "end")
        self.entry_tickers.insert(0, ", ".join(tickers))
        self.save_stocks()

    def run_analysis(self, yfinance_period, yfinance_interval):
        tickers_input = self.entry_tickers.get()
        if not tickers_input:
            self.is_loading = False
            self.update_results([{'text': "Error: Ingrese al menos un ticker.", 'status': 'fail'}])
            self.after(100, self.on_analysis_complete)
            return

        tickers_list = [ticker.strip().upper() for ticker in tickers_input.split(',') if ticker.strip()]
        
        # Guardamos en la lista activa antes de analizar
        self.update_active_list_data()
        self.save_stocks()
        
        all_reports = []
        for ticker in tickers_list:
            if ticker:
                report = check_stock(ticker, yfinance_period, yfinance_interval)
                all_reports.append(report)
        
        # Sort reports by pass_count in descending order
        all_reports.sort(key=lambda x: x['pass_count'], reverse=True)

        # DETENER SPINNER Y AGREGAR SALTOS DE LINEA ANTES DE MOSTRAR RESULTADOS
        self.is_loading = False
        self.after(0, self.insert_separator_newlines)

        for report in all_reports:
            self.after(100, self.update_results, report['messages'])
            self.after(100, self.update_results, [{'text': "\n", 'status': 'info'}]) # Add a newline for separation
        
        self.after(200, self.on_analysis_complete)

    def save_stocks(self):
        try:
            # Guardamos todo el objeto (listas y activa)
            data = {
                "active_list": self.active_list_name,
                "lists": self.stock_lists
            }
            with open(STOCKS_FILE, 'w') as f:
                json.dump(data, f)
        except Exception as e:
            self.update_results([{'text': f"Error guardando acciones: {e}", 'status': 'fail'}])

    def insert_separator_newlines(self):
        self.results_textbox.configure(state="normal")
        self.results_textbox.insert("end", "\n\n\n")
        self.results_textbox.configure(state="disabled")

    def toggle_auto_analysis(self):
        if self.is_auto_analyzing.get():
            self.clear_textbox()
            self.update_results([{'text': "Modo automático ACTIVADO.", 'status': 'info'}])
            self.analyze_button.configure(state="disabled")
            self.auto_analysis_thread = threading.Thread(target=self.auto_analysis_loop)
            self.auto_analysis_thread.daemon = True
            self.auto_analysis_thread.start()
        else:
            self.update_results([{'text': "Modo automático DESACTIVADO.", 'status': 'info'}])
            self.analyze_button.configure(state="normal")
            # El loop se detendrá naturalmente en la próxima iteración al chequear `is_auto_analyzing`

    def auto_analysis_loop(self):
        while self.is_auto_analyzing.get() and self.run_auto:
            if self.is_market_open():
                self.clear_textbox()
                self.update_results([{'text': f"Mercado ABIERTO. Analizando automáticamente... (Último análisis: {self.last_analysis_time.strftime('%H:%M:%S') if self.last_analysis_time else 'Nunca'})", 'status': 'info'}])
                self.start_analysis_thread(from_auto=True)
                time.sleep(600) # Espera 10 minutos
            else:
                self.clear_textbox()
                self.update_results([{'text': "Mercado CERRADO. El análisis automático se reanudará en horario de mercado.", 'status': 'info'}])
                time.sleep(60) # Espera 1 minuto y vuelve a chequear
        self.after(100, self.on_auto_analysis_stopped)

    def is_market_open(self):
        try:
            tz = pytz.timezone('America/Argentina/Buenos_Aires')
            now_ar = datetime.now(tz)
            is_weekday = now_ar.weekday() < 5 # Lunes=0, Domingo=6
            is_market_time = 11 <= now_ar.hour < 17
            return is_weekday and is_market_time
        except Exception: # Si falla pytz, asumimos que está cerrado por seguridad
            return False

    def update_results(self, messages):
        self.results_textbox.configure(state="normal")
        for msg in messages:
            if isinstance(msg, dict) and 'text' in msg and 'status' in msg:
                self.results_textbox.insert("end", f"{msg['text']}\n", msg['status'])
            else:
                # Fallback for unexpected message format, print as plain text
                self.results_textbox.insert("end", f"Error: Mensaje con formato inesperado: {msg}\n", 'fail')

        self.results_textbox.configure(state="disabled")

    def on_analysis_complete(self):
        self.is_loading = False
        if not self.is_auto_analyzing.get():
            self.analyze_button.configure(state="normal")

    def on_auto_analysis_stopped(self):
        self.analyze_button.configure(state="normal")
        
    def clear_textbox(self):
        self.results_textbox.configure(state="normal")
        self.results_textbox.delete("0.0", "end")
        self.results_textbox.configure(state="disabled")

    def load_stocks(self):
        if os.path.exists(STOCKS_FILE):
            try:
                with open(STOCKS_FILE, 'r') as f:
                    data = json.load(f)
                    
                    # Compatibilidad con formato viejo (si era una lista simple)
                    if isinstance(data, list):
                        self.stock_lists = {"Mi Portfolio": data}
                        self.active_list_name = "Mi Portfolio"
                    else:
                        self.stock_lists = data.get("lists", {"Mi Portfolio": []})
                        self.active_list_name = data.get("active_list", "Mi Portfolio")
                    
                    # Actualizar UI
                    self.list_selector.configure(values=list(self.stock_lists.keys()))
                    self.list_selector.set(self.active_list_name)
                    
                    tickers = self.stock_lists.get(self.active_list_name, [])
                    self.entry_tickers.delete(0, "end")
                    self.entry_tickers.insert(0, ", ".join(tickers))
                    
            except Exception as e:
                self.update_results([{'text': f"Error cargando acciones: {e}", 'status': 'fail'}])
    
    def on_closing(self):
        self.run_auto = False # Señal para que el loop del thread se detenga
        if self.is_auto_analyzing.get():
            self.is_auto_analyzing.set(False)
            time.sleep(1.1) # Dar tiempo al thread para que termine su ciclo
        self.destroy()

if __name__ == "__main__":
    app = App()
    app.mainloop()