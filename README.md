# Monitor de Alertas de Trading para Acciones v2

Este proyecto es una aplicación de escritorio creada en Python que permite monitorear acciones y generar alertas de compra o venta basadas en una serie de indicadores técnicos. Esta versión incluye persistencia de datos, análisis automático en horario de mercado y una interfaz con códigos de color para una mejor visualización.

## Nuevas Funcionalidades (v2)

*   **Persistencia de Acciones**: La lista de acciones que ingresas se guarda automáticamente en un archivo `stocks.json`. La próxima vez que abras la aplicación, la lista se cargará para que no tengas que volver a escribirla.
*   **Análisis Automático**: Se ha añadido una casilla para activar un modo de análisis automático. Si está activada, la aplicación volverá a analizar la lista de acciones cada 10 minutos.
*   **Horario de Mercado**: El análisis automático solo se ejecuta si el mercado de Argentina está abierto (Lunes a Viernes, de 11:00 a 17:00 ART). Fuera de ese horario, la aplicación se pondrá en espera.
*   **Codificación por Colores**: Los resultados del análisis ahora se muestran con colores para una rápida identificación:
    *   **Verde**: El filtro se ha cumplido con éxito.
    *   **Rojo**: El filtro no se ha cumplido.
    *   **Cyan/Dorado**: Se ha generado una alerta de compra o venta.
*   **Ordenamiento por Relevancia**: Las acciones se ordenan automáticamente según la cantidad de filtros de indicadores que hayan pasado con éxito, mostrando las más relevantes (con más filtros en verde) al principio de la lista.
*   **Selección de Temporalidad**: Se han añadido botones de radio para seleccionar la temporalidad del análisis (ej. 1 día, 5 días, 1 mes, 1 año). Al cambiar la selección, la aplicación realizará un nuevo análisis automáticamente. La temporalidad por defecto es de 1 año.

## Mejoras en la Lógica de Análisis (v3)

Se han introducido mejoras significativas en la lógica de los indicadores para proporcionar alertas más precisas y relevantes.

*   **Periodo de Datos Extendido**: El periodo por defecto para el análisis histórico se ha ampliado a **5 años** para las temporalidades diaria y semanal. Esto mejora significativamente la precisión de los indicadores basados en medias móviles, como el MACD, al alinearlos mejor con los estándares de las plataformas de trading.

*   **Análisis MACD Avanzado**:
    *   **Alertas de Cruce Directo**: Ahora se generan alertas explícitas de `COMPRA` o `VENTA` cuando la línea MACD cruza su línea de señal.
    *   **Análisis de Zonas Históricas por Cuantiles**: En lugar de depender de los mínimos y máximos absolutos, el sistema ahora detecta si la línea de señal del MACD ha entrado en una zona de sobre-extensión. Se genera una alerta de "posible oportunidad" si la señal entra en el **10% inferior (compra)** o en el **10% superior (venta)** de su rango histórico de 5 años.
    *   **Valor de Señal Visible**: El valor numérico de la línea de señal del MACD ahora se muestra entre paréntesis para una referencia rápida.

*   **Análisis Detallado de Konkorde**:
    *   Además de rastrear a los grandes inversores (manos fuertes), ahora se analiza la línea que representa a los **inversores minoristas** (línea azul/roja en los gráficos).
    *   **Señal de Compra por Cruce a Cero**: Se genera una alerta de `COMPRA` cuando la línea de minoristas cruza el nivel cero hacia arriba, indicando un posible inicio de interés comprador minorista.
    *   **Señal de Venta por Euforia Minorista**: Se genera una alerta de `VENTA` cuando la línea de minoristas alcanza el **10% superior** de su rango histórico, lo que puede indicar un nivel de euforia insostenible que a menudo precede a una corrección.

## Lógica de Alertas y Análisis de Indicadores

La aplicación analiza las acciones utilizando cuatro indicadores técnicos principales: RSI, MACD, ADX y Konkorde. A diferencia de versiones anteriores, **los indicadores ya no se aplican en una lógica de decisión en cascada**. Esto significa que todos los indicadores se calculan y sus resultados se muestran de forma independiente.

Cada indicador genera una señal o estado que contribuye a un contador de "pasos" (`pass_count`). Este `pass_count` se utiliza para ordenar la relevancia de las acciones, mostrando primero aquellas con más señales positivas.

1.  **RSI (Relative Strength Index):** Verifica si la acción está en una zona de **sobrecompra** (RSI > 70) o **sobreventa** (RSI < 30).
2.  **MACD (Moving Average Convergence Divergence):** Busca confirmación de una posible reversión a través de un cruce alcista o bajista del MACD.
3.  **ADX (Average Directional Index):**
    *   **Mide la fuerza de la tendencia:** Clasificándola como 'Fuerte' o 'Débil/En rango'.
    *   **Determina la dirección de la tendencia:** 'Alcista', 'Bajista' o 'Indefinida' basándose en los valores de +DI y -DI.
    *   **Codificación por Colores:** La tendencia Alcista Fuerte se muestra en verde, Bajista Fuerte en rojo/naranja, y Débil/Indefinida en gris.
4.  **Konkorde:**
    *   Proporciona una visión sobre la actividad de las "manos fuertes" (grandes inversores), indicando si están acumulando o distribuyendo la acción.
    *   **Valor Escala:** Los valores grandes de Konkorde se escalan y se muestran en millones (ej. "36.11M") para una mejor comprensión.
    *   **Interpretación Directa:** La interpretación se presenta de forma concisa (ej. "Manos grandes acumulando.") sin señales confusas.

Cuando un número suficiente de estas condiciones se alinean (indicado por un alto `pass_count`) y se produce una señal clara (por ejemplo, un cruce MACD confirmado por Konkorde), la aplicación generará una **ALERTA DE COMPRA** o **ALERTA DE VENTA**.

## Mejoras Recientes en la Interfaz y Presentación

*   **Encabezado de Análisis Mejorado:** Cada análisis de acción comienza con un encabezado claro que incluye el Ticker, el Nombre de la Compañía y el Precio Actual en USD (ej. `AAPL (Apple Inc.) - $170.50 USD`).
*   **Separación de Reportes:** Se ha añadido una línea en blanco entre los reportes de cada acción para mejorar la legibilidad.
*   **Scroll Automático:** Al iniciar un nuevo análisis, el área de resultados se desplaza automáticamente al principio para que los últimos resultados sean visibles desde el inicio.
*   **Claridad de Mensajes:** Se han eliminado los emojis (✅ y 🚫) de los mensajes de estado de los indicadores para evitar confusiones.

### 1. Prerrequisitos

Asegúrate de tener Python 3 instalado en tu sistema.

### 2. Instalación

1.  Abre una terminal o línea de comandos en la carpeta del proyecto.
2.  Instala las dependencias necesarias ejecutando:
    ```
    pip install -r requirements.txt
    ```

### 3. Ejecución

Para iniciar la aplicación, ejecuta el siguiente comando en la terminal:
```
python app.py
```

### 4. Funcionamiento

1.  En la ventana, ingresa los tickers de las acciones que deseas analizar, separados por comas. La lista se guardará para futuras sesiones.
2.  Haz clic en **"Analizar"** para una revisión única.
3.  Opcionalmente, marca la casilla **"Análisis Automático"** para que la aplicación revise las acciones cada 10 minutos durante el horario de mercado.
4.  Observa los resultados codificados por colores en la ventana principal.

## Estructura del Proyecto

*   `app.py`: Contiene el código de la interfaz gráfica (GUI), la lógica de persistencia y el gestor del análisis automático.
*   `analysis.py`: Contiene la lógica para el análisis de las acciones: descarga de datos, cálculo de indicadores y aplicación de la lógica de decisión.
*   `requirements.txt`: Archivo que lista todas las librerías de Python necesarias.
*   `stocks.json`: Archivo que se crea automáticamente para guardar tu lista de acciones.
*   `README.md`: Este archivo, con la documentación del proyecto.