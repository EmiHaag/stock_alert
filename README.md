# Monitor de Alertas de Trading para Acciones v4 (EmiHaag Edition)

Este proyecto es una aplicación de escritorio avanzada creada en Python que permite monitorear acciones y generar alertas de compra o venta basadas en una combinación de indicadores técnicos profesionales.

## 🚀 Nuevas Funcionalidades y Mejoras (v4)

### 📊 Gestión de Múltiples Listas
*   **Listas Personalizadas**: Ahora puedes crear, renombrar y eliminar múltiples listas de seguimiento (ej. "Mi Portfolio", "Opciones Semanales", "Watchlist Tech").
*   **Persistencia Inteligente**: El sistema guarda automáticamente qué lista tienes activa y los tickers que contiene en `stocks.json`.
*   **Cambio Rápido**: Selector desplegable para alternar entre diferentes estrategias o grupos de acciones al instante.

### 🔍 Filtros de Oportunidad
*   **Filtro Compra/Venta**: Nuevo sistema de filtrado que permite mostrar únicamente las acciones que presentan señales de compra o de venta, limpiando el ruido de las acciones neutrales.
*   **Análisis Focalizado**: Al seleccionar "Compra", la aplicación solo listará aquellas acciones con alertas alcistas activas.

### 📈 Indicadores y Lógica de Análisis Mejorada
*   **Canal de Tendencia (SMA 20/50)**: Análisis de corto/mediano plazo (últimos 50 días) que identifica si la acción está en un canal Alcista, Bajista o Lateral.
*   **MACD de Ventana Ampliada**: Detección de cruces en las últimas 4 velas para no perder señales ocurridas recientemente (ej. "Cruce hace 2 días").
*   **Konkorde Institucional (PVI/NVI)**: Separación precisa entre "Manos Fuertes" y "Minoristas" basada en el estándar Blai5 de 15 periodos.
*   **Etiquetado de Alertas**: Cada mensaje de alerta especifica qué indicador la disparó (ej. `MACD: Alerta de Venta`).

### 🎨 Interfaz de Usuario (UX) Profesional
*   **Encuadre Dinámico**: Los reportes de cada acción están encuadrados con caracteres especiales (`╔═╗`) y cuentan con padding automático que se ajusta al ancho del mensaje.
*   **Spinner Animado (Braille)**: Animación de carga fluida (`⠋⠙⠹`) integrada directamente en el log de resultados para indicar que el análisis está en curso.
*   **Atajos de Teclado**: Presiona **Enter** en el campo de tickers para iniciar el análisis instantáneamente.

## 🛠 Lógica de Indicadores

1.  **RSI (Relative Strength Index):** Zonas de sobrecompra (>70) y sobreventa (<30).
2.  **MACD:** Cruces de línea de señal y análisis de cuantiles históricos (10% superior/inferior).
3.  **ADX:** Medición de la fuerza de la tendencia y dirección (+DI/-DI).
4.  **Konkorde:** Rastreo de volumen institucional (Manos Fuertes) vs volumen minorista.
5.  **SMA 20/50**: Definición del canal de tendencia inmediato.

## ⚙️ Instalación y Uso

### 1. Prerrequisitos
*   Python 3.10 o superior.

### 2. Instalación
```bash
pip install -r requirements.txt
```

### 3. Ejecución
```bash
python app.py
```

### 4. Funcionamiento
1.  **Carga**: Selecciona una lista o crea una nueva con el botón `+`.
2.  **Configura**: Elige la temporalidad (1h, 1 día, 1 semana) y el tipo de oportunidad que buscas.
3.  **Analiza**: Presiona "Analizar" o activa el **Análisis Automático** para un monitoreo cada 10 minutos durante el horario de mercado (ARG).

## 📁 Estructura del Proyecto
*   `app.py`: Interfaz gráfica (CustomTkinter) y lógica de la aplicación.
*   `analysis.py`: Motor de análisis técnico y descarga de datos (yfinance).
*   `stocks.json`: Base de datos local de tus listas y preferencias.
*   `.gitignore`: Configurado para proteger tus datos locales y archivos temporales.

---
*Desarrollado para optimizar el análisis técnico diario.*
