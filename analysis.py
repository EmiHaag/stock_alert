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

        price_range = data["High"] - data["Low"]
        price_range = price_range.replace(0, 1)
        blue_line = (
            pd.Series(
                ((data["Close"] - data["Low"]) - (data["High"] - data["Close"]))
                / price_range
                * data["Volume"]
            )
            .rolling(window=10)
            .sum()
        )
        green_line = (
            pd.Series(
                ((data["High"] + data["Low"]) / 2 - data["Close"].shift(1))
                * data["Volume"]
            )
            .rolling(window=20)
            .mean()
        )
        brown_line = (blue_line + green_line).rolling(window=5).mean()
        data["konkorde_brown"] = brown_line

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

        # Paso 2: MACD
        last_macd = data["MACD_12_26_9"].iloc[-1]
        last_macdsignal = data["MACDs_12_26_9"].iloc[-1]
        prev_macd = data["MACD_12_26_9"].iloc[-2]
        prev_macdsignal = data["MACDs_12_26_9"].iloc[-2]
        cruce_alcista = prev_macd < prev_macdsignal and last_macd > last_macdsignal
        cruce_bajista = prev_macd > prev_macdsignal and last_macd < last_macdsignal
        macd_condition_met = (rsi_sobrecompra and cruce_bajista) or (
            rsi_sobreventa and cruce_alcista
        )
        macd_status = "pass" if macd_condition_met else "fail"
        macd_text = f"MACD ({last_macdsignal:.2f}): {'Cruce Alcista' if cruce_alcista else 'Cruce Bajista' if cruce_bajista else 'Sin cruce reciente'}. Confirmación: {'OK' if macd_condition_met else 'NO'}"
        messages.append({"text": macd_text, "status": macd_status})
        if macd_status == "pass":
            pass_count += 1

        if cruce_alcista:
            messages.append({'text': f"\n*** ALERTA DE COMPRA para {ticker.upper()} ***", 'status': 'alert_buy'})
            messages.append({'text': "Motivo: Cruce Alcista de MACD.", 'status': 'alert_buy'})
            pass_count += 1
        elif cruce_bajista:
            messages.append({'text': f"\n*** ALERTA DE VENTA para {ticker.upper()} ***", 'status': 'alert_sell'})
            messages.append({'text': "Motivo: Cruce Bajista de MACD.", 'status': 'alert_sell'})
            pass_count += 1

        # Análisis de la señal MACD con cuantiles históricos
        macd_signal_history = data['MACDs_12_26_9'].dropna() # Drop NaN values for accurate quantile calculation
        quantile_10 = macd_signal_history.quantile(0.10)
        quantile_90 = macd_signal_history.quantile(0.90)

        if last_macdsignal <= quantile_10:
            min_macd_text = f"MACD Signal en el 10% inferior histórico ({quantile_10:.2f}). Posible oportunidad de compra."
            messages.append({'text': min_macd_text, 'status': 'alert_buy'})
            pass_count += 1

        if last_macdsignal >= quantile_90:
            max_macd_text = f"MACD Signal en el 10% superior histórico ({quantile_90:.2f}). Posible oportunidad de venta."
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

        # Paso 4: Konkorde
        # Análisis de la línea azul (minoristas), a menudo representada como roja/azul.
        last_blue = blue_line.iloc[-1]
        prev_blue = blue_line.iloc[-2]
        cruce_cero_azul = prev_blue < 0 and last_blue > 0

        if cruce_cero_azul:
            blue_line_text = f"Konkorde (minoristas): Cruce alcista de línea ({last_blue/1_000_000:.2f}M). Posible señal de compra."
            messages.append({'text': blue_line_text, 'status': 'alert_buy'})
            pass_count += 1
        
        # Chequeo de euforia de minoristas (línea azul en el 10% superior)
        blue_line_history = blue_line.dropna()
        quantile_90_blue = blue_line_history.quantile(0.90)

        if last_blue >= quantile_90_blue:
            blue_line_text = f"Konkorde (minoristas): Euforia detectada ({last_blue/1_000_000:.2f}M > {quantile_90_blue/1_000_000:.2f}M). Posible señal de venta."
            messages.append({'text': blue_line_text, 'status': 'alert_sell'})
            pass_count += 1

        konkorde_val = data["konkorde_brown"].iloc[-1]
        konkorde_val_display = (
            konkorde_val / 1_000_000 if abs(konkorde_val) >= 1_000_000 else konkorde_val
        )  # Scale if large, otherwise keep original
        konkorde_unit = (
            "M" if abs(konkorde_val) >= 1_000_000 else ""
        )  # Unit for millions

        # Define a neutral zone around zero for Konkorde
        konkorde_neutral_threshold = 0.15  # Small threshold for "near zero"

        konkorde_interpretation = "Neutral."
        konkorde_status = "info"  # Default to info, as it's not a strict filter anymore

        konkorde_compra_signal = konkorde_val > konkorde_neutral_threshold
        konkorde_venta_signal = konkorde_val < -konkorde_neutral_threshold
        konkorde_cerca_cero = (
            -konkorde_neutral_threshold <= konkorde_val <= konkorde_neutral_threshold
        )

        if konkorde_compra_signal:
            konkorde_interpretation = "Manos grandes acumulando."
            konkorde_status = "alert_buy"
        elif konkorde_venta_signal:
            konkorde_interpretation = "Manos grandes distribuyendo."
            konkorde_status = "alert_sell"
        elif konkorde_cerca_cero:
            konkorde_interpretation = (
                "Konkorde cerca de cero, posible consolidación o indecisión."
            )

        konkorde_text = f"Konkorde: {konkorde_val_display:.2f}{konkorde_unit}. {konkorde_interpretation}"
        messages.append({"text": konkorde_text, "status": konkorde_status})

        # Konkorde now contributes to pass_count if it strongly aligns with MACD signals
        # and has a clear interpretation (not neutral around zero).
        if (cruce_alcista and konkorde_compra_signal) or (
            cruce_bajista and konkorde_venta_signal
        ):
            pass_count += 1

        if cruce_alcista and konkorde_compra_signal:
            messages.append(
                {
                    "text": f"\n*** ALERTA DE COMPRA para {ticker.upper()} ***",
                    "status": "alert_buy",
                }
            )
            messages.append(
                {
                    "text": "Motivo: Confirmación de compra por Konkorde.",
                    "status": "alert_buy",
                }
            )
        elif cruce_bajista and konkorde_venta_signal:
            messages.append(
                {
                    "text": f"\n*** ALERTA DE VENTA para {ticker.upper()} ***",
                    "status": "alert_sell",
                }
            )
            messages.append(
                {
                    "text": "Motivo: Confirmación de venta por Konkorde.",
                    "status": "alert_sell",
                }
            )
        # After all pass_count increments, create the initial header message and prepend it
        company_name = stock.info.get("longName", "")
        header_message_text = f"{ticker.upper()}"
        if company_name:
            header_message_text += f" ({company_name})"

        # Add current price
        current_price = data["Close"].iloc[-1]
        header_message_text += f" - ${current_price:.2f} USD"

        header_message = {"text": header_message_text, "status": "info"}
        messages.insert(0, header_message)  # Insert at the beginning

        return {"ticker": ticker, "pass_count": pass_count, "messages": messages}

    except Exception as e:
        return {
            "ticker": ticker,
            "pass_count": 0,
            "messages": [
                {"text": f"{ticker.upper()}: Error al procesar - {e}", "status": "fail"}
            ],
        }
