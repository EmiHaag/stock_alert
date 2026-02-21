import yfinance as yf
import pandas as pd
import numpy as np
import ta.momentum
import ta.trend


def check_stock(ticker, period="5y", interval="1d"):
    """
    Analiza un ticker y devuelve un diccionario con ticker, recuento de filtros y mensajes.
    """
    try:
        stock = yf.Ticker(ticker)
        data = stock.history(period=period, interval=interval)

        if data.empty:
            return {
                "ticker": ticker,
                "pass_count": 0,
                "messages": [
                    {
                        "text": f"{ticker.upper()}: No se encontraron datos.",
                        "status": "fail",
                    }
                ],
            }

        # Cálculo de indicadores
        data["RSI_14"] = ta.momentum.rsi(data["Close"], window=14)
        macd_indicator = ta.trend.MACD(
            close=data["Close"], window_fast=12, window_slow=26, window_sign=9
        )
        data["MACD_12_26_9"] = macd_indicator.macd()
        data["MACDs_12_26_9"] = macd_indicator.macd_signal()
        data["ADX_14"] = ta.trend.adx(
            high=data["High"], low=data["Low"], close=data["Close"], window=14
        )

        # --- Cálculo de Konkorde (Versión Mejorada basada en PVI/NVI) ---
        # 1. Cálculo de PVI y NVI
        pvi = [100.0]
        nvi = [100.0]
        
        close_prices = data['Close'].values
        volumes = data['Volume'].values
        
        for i in range(1, len(data)):
            prev_close = close_prices[i-1]
            curr_close = close_prices[i]
            prev_vol = volumes[i-1]
            curr_vol = volumes[i]
            
            price_change = (curr_close - prev_close) / prev_close
            
            if curr_vol > prev_vol:
                pvi.append(pvi[-1] * (1 + price_change))
                nvi.append(nvi[-1])
            elif curr_vol < prev_vol:
                pvi.append(pvi[-1])
                nvi.append(nvi[-1] * (1 + price_change))
            else:
                pvi.append(pvi[-1])
                nvi.append(nvi[-1])
        
        data['PVI'] = pvi
        data['NVI'] = nvi
        
        # 2. Suavizado para obtener las líneas de Konkorde (Estándar Blai5: 15 periodos)
        # Manos Fuertes (Azul en TradingView) -> NVI - Media(NVI, 15)
        nvi_ema_15 = data['NVI'].ewm(span=15).mean()
        data['manos_fuertes'] = (data['NVI'] - nvi_ema_15)
        
        # Minoristas (Rojo en TradingView) -> PVI - Media(PVI, 15)
        pvi_ema_15 = data['PVI'].ewm(span=15).mean()
        data['minoristas'] = (data['PVI'] - pvi_ema_15)
        
        # Media de señal para Konkorde (Marrón en TradingView)
        data['konkorde_signal'] = data['manos_fuertes'].rolling(window=15).mean()
        
        # Lógica de Alertas
        pass_count = 0
        messages = []

        # Paso 1: RSI
        rsi_val = data["RSI_14"].iloc[-1]
        rsi_sobrecompra = rsi_val > 70
        rsi_sobreventa = rsi_val < 30
        rsi_status = "pass" if rsi_sobrecompra or rsi_sobreventa else "fail"
        rsi_text = f"RSI(14): {rsi_val:.2f}. {'Sobrecompra' if rsi_sobrecompra else 'Sobreventa' if rsi_sobreventa else 'Neutral'}"
        messages.append({"text": rsi_text, "status": rsi_status})
        if rsi_status == "pass":
            pass_count += 1

        # Paso 2: MACD (Detección de cruce en las últimas 4 velas)
        macd_series = data["MACD_12_26_9"]
        signal_series = data["MACDs_12_26_9"]
        
        cruce_alcista = False
        cruce_bajista = False
        dias_desde_cruce = 0

        # Buscamos en las últimas 4 velas (índices -1 a -4)
        for i in range(1, 5):
            idx_curr = -i
            idx_prev = -(i + 1)
            
            curr_macd = macd_series.iloc[idx_curr]
            curr_signal = signal_series.iloc[idx_curr]
            prev_macd = macd_series.iloc[idx_prev]
            prev_signal = signal_series.iloc[idx_prev]

            # Cruce Alcista: MACD pasa de estar debajo a estar arriba de la señal
            if prev_macd < prev_signal and curr_macd > curr_signal:
                cruce_alcista = True
                dias_desde_cruce = i - 1
                break
            # Cruce Bajista: MACD pasa de estar arriba a estar debajo de la señal
            if prev_macd > prev_signal and curr_macd < curr_signal:
                cruce_bajista = True
                dias_desde_cruce = i - 1
                break

        last_macdsignal = signal_series.iloc[-1]
        
        # Lógica de confirmación con RSI (para pass_count)
        macd_condition_met = (rsi_sobrecompra and cruce_bajista) or (
            rsi_sobreventa and cruce_alcista
        )
        macd_status = "pass" if macd_condition_met else "fail"
        
        cruce_text = "Sin cruce reciente"
        if cruce_alcista:
            cruce_text = f"Cruce Alcista ({'Hoy' if dias_desde_cruce == 0 else f'hace {dias_desde_cruce}d'})"
        elif cruce_bajista:
            cruce_text = f"Cruce Bajista ({'Hoy' if dias_desde_cruce == 0 else f'hace {dias_desde_cruce}d'})"

        macd_text = f"MACD ({last_macdsignal:.2f}): {cruce_text}. Confirmación RSI: {'OK' if macd_condition_met else 'NO'}"
        messages.append({"text": macd_text, "status": macd_status})
        
        if cruce_alcista or cruce_bajista:
            pass_count += 1

        if cruce_alcista:
            messages.append({'text': f"\n*** MACD: ALERTA DE COMPRA para {ticker.upper()} ***", 'status': 'alert_buy'})
            messages.append({'text': f"Motivo: {cruce_text} de MACD.", 'status': 'alert_buy'})
            pass_count += 1
        elif cruce_bajista:
            messages.append({'text': f"\n*** MACD: ALERTA DE VENTA para {ticker.upper()} ***", 'status': 'alert_sell'})
            messages.append({'text': f"Motivo: {cruce_text} de MACD.", 'status': 'alert_sell'})
            pass_count += 1

        # Análisis de la señal MACD con cuantiles históricos
        macd_signal_history = data['MACDs_12_26_9'].dropna() # Drop NaN values for accurate quantile calculation
        quantile_10 = macd_signal_history.quantile(0.10)
        quantile_90 = macd_signal_history.quantile(0.90)

        if last_macdsignal <= quantile_10:
            min_macd_text = f"MACD: Signal en el 10% inferior histórico ({quantile_10:.2f}). Posible oportunidad de compra."
            messages.append({'text': min_macd_text, 'status': 'alert_buy'})
            pass_count += 1

        if last_macdsignal >= quantile_90:
            max_macd_text = f"MACD: Signal en el 10% superior histórico ({quantile_90:.2f}). Posible oportunidad de venta."
            messages.append({'text': max_macd_text, 'status': 'alert_sell'})
            pass_count += 1

        # Paso 3: ADX
        # Get ADX, +DI, -DI
        data["ADX_14"] = ta.trend.adx(
            high=data["High"], low=data["Low"], close=data["Close"], window=14
        )
        data["ADX_POS_14"] = ta.trend.adx_pos(
            high=data["High"], low=data["Low"], close=data["Close"], window=14
        )
        data["ADX_NEG_14"] = ta.trend.adx_neg(
            high=data["High"], low=data["Low"], close=data["Close"], window=14
        )

        # --- Análisis de Canal de Tendencia (SMA 50/200) ---
        data["SMA_50"] = data["Close"].rolling(window=50).mean()
        data["SMA_200"] = data["Close"].rolling(window=200).mean()
        
        last_close = data["Close"].iloc[-1]
        last_sma50 = data["SMA_50"].iloc[-1]
        last_sma200 = data["SMA_200"].iloc[-1]
        
        # Calcular pendiente de SMA 50 (últimos 5 días)
        prev_sma50 = data["SMA_50"].iloc[-6]
        slope_sma50 = (last_sma50 - prev_sma50) / prev_sma50
        
        canal_status = "info"
        if last_close > last_sma200 and slope_sma50 > 0.001:
            canal_text = "Canal: ALCISTA (Basado en SMA 50/200 - Últimos 200 días)"
            canal_status = "pass"
        elif last_close < last_sma200 and slope_sma50 < -0.001:
            canal_text = "Canal: BAJISTA (Basado en SMA 50/200 - Últimos 200 días)"
            canal_status = "fail"
        else:
            canal_text = "Canal: LATERAL / CONSOLIDACIÓN (SMA 50/200)"
            canal_status = "info"

        adx_val = data["ADX_14"].iloc[-1]
        adx_pos = data["ADX_POS_14"].iloc[-1]
        adx_neg = data["ADX_NEG_14"].iloc[-1]

        # Determine Trend Strength
        adx_fuerte = adx_val > 23
        strength_text = "Fuerte" if adx_fuerte else "Débil o en rango"

        # Determine Trend Direction
        trend_direction_text = "Indefinida"
        if adx_pos > adx_neg and adx_val > 20:  # ADX > 20 to confirm a trend
            trend_direction_text = "Alcista"
        elif adx_neg > adx_pos and adx_val > 20:  # ADX > 20 to confirm a trend
            trend_direction_text = "Bajista"

        # Determine ADX overall status for pass_count
        # Consider a pass if ADX is strong and direction is defined.
        # Determine ADX status for coloring based on user's request
        adx_status_for_color = "info"  # Default to grey

        if adx_fuerte and trend_direction_text == "Alcista":
            adx_status_for_color = "pass"  # Green
        elif adx_fuerte and trend_direction_text == "Bajista":
            adx_status_for_color = "fail"  # Red-Orange
        else:  # Weak or undefined trend
            adx_status_for_color = "info"  # For now, use info for yellow-like behavior

        # Keep adx_status for pass_count consistent with previous logic
        adx_status = (
            "pass"
            if adx_fuerte
            and (trend_direction_text == "Alcista" or trend_direction_text == "Bajista")
            else "fail"
        )
        adx_text = (
            f"ADX: {adx_val:.2f}. Tendencia: {trend_direction_text} ({strength_text})"
        )
        messages.append(
            {"text": adx_text, "status": adx_status_for_color}
        )  # Use new status for color        messages.append({'text': adx_text, 'status': adx_status})
        if adx_status == "pass":
            pass_count += 1

        # Canal de Tendencia
        messages.append({"text": canal_text, "status": canal_status})

        # Paso 4: Konkorde
        # Análisis de Minoristas (PVI / Montaña)
        last_minorista = data['minoristas'].iloc[-1]
        prev_minorista = data['minoristas'].iloc[-2]
        
        minorista_cruce_cero = prev_minorista < 0 and last_minorista > 0
        if minorista_cruce_cero:
            messages.append({'text': "Konkorde: Interés minorista entrando (Cruce a cero). Alerta de COMPRA.", 'status': 'alert_buy'})
            pass_count += 1
        
        # Análisis de Manos Fuertes (NVI)
        last_mf = data['manos_fuertes'].iloc[-1]
        prev_mf = data['manos_fuertes'].iloc[-2]
        
        mf_acumulando = last_mf > 0
        mf_distribuyendo = last_mf < 0
        mf_aumentando = last_mf > prev_mf

        konkorde_status = "info"
        if mf_acumulando:
            konkorde_interpretation = "Manos Fuertes ACUMULANDO (Positivo)."
            konkorde_status = "pass"
            if mf_aumentando:
                konkorde_interpretation += " Incrementando posición."
        else:
            konkorde_interpretation = "Manos Fuertes DISTRIBUYENDO (Negativo)."
            konkorde_status = "fail"
            if not mf_aumentando:
                konkorde_interpretation += " Reduciendo posición."

        messages.append({"text": f"Konkorde: {konkorde_interpretation}", "status": konkorde_status})

        # Confirmación Konkorde + MACD
        if (cruce_alcista and mf_acumulando):
            messages.append({"text": "\n*** ESTRATEGIA: ALERTA DE COMPRA (Konkorde + MACD) ***", "status": "alert_buy"})
            messages.append({"text": "Motivo: Cruce MACD con Institucionales comprando.", "status": "alert_buy"})
            pass_count += 2
        elif (cruce_bajista and mf_distribuyendo):
            messages.append({"text": "\n*** ESTRATEGIA: ALERTA DE VENTA (Konkorde + MACD) ***", "status": "alert_sell"})
            messages.append({"text": "Motivo: Cruce MACD con Institucionales vendiendo.", "status": "alert_sell"})
            pass_count += 2
        company_name = stock.info.get("longName", "")
        header_text = f"{ticker.upper()}"
        if company_name:
            header_text += f" ({company_name})"
        
        current_price = data["Close"].iloc[-1]
        price_text = f"Precio: ${current_price:.2f} USD"

        # Create a list of all content lines to calculate max width
        content_lines = [header_text, price_text, "═" * 10] # Divider placeholder
        for m in messages:
            content_lines.append(m['text'].strip())

        # Find max width and add padding
        max_w = max(len(line) for line in content_lines)
        box_width = max_w + 4 # 2 spaces padding on each side

        # Re-build messages with borders
        framed_messages = []
        
        # Header
        top_border = "╔" + "═" * (box_width) + "╗"
        mid_border = "╠" + "═" * (box_width) + "╣"
        bot_border = "╚" + "═" * (box_width) + "╝"

        framed_messages.append({"text": top_border, "status": "info"})
        
        # Linea de Ticker
        line = f"║  {header_text.ljust(max_w)}  ║"
        framed_messages.append({"text": line, "status": "info"})
        
        # Linea de Precio
        line = f"║  {price_text.ljust(max_w)}  ║"
        framed_messages.append({"text": line, "status": "info"})
        
        framed_messages.append({"text": mid_border, "status": "info"})

        # Contenido de indicadores
        for m in messages:
            text = m['text'].strip()
            # If the text has multiple lines (like ALERTA), handle them
            for subline in text.split('\n'):
                subline = subline.strip()
                if not subline: continue
                
                # Check if it's an alert to keep its status
                line_str = f"║  {subline.ljust(max_w)}  ║"
                framed_messages.append({"text": line_str, "status": m['status']})

        framed_messages.append({"text": bot_border, "status": "info"})

        return {"ticker": ticker, "pass_count": pass_count, "messages": framed_messages}

    except Exception as e:
        return {
            "ticker": ticker,
            "pass_count": 0,
            "messages": [
                {"text": f"{ticker.upper()}: Error al procesar - {e}", "status": "fail"}
            ],
        }
