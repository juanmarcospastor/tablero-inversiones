from datetime import datetime, timedelta, timezone
import json
import urllib.request

from flask import Flask, jsonify, render_template, request
import pandas as pd

from services.cartera import (
    calcular_cartera_actual,
    detalle_activo,
    obtener_operaciones,
    obtener_precios,
)

app = Flask(__name__)

CEDEAR_SYMBOLS = {
    "AAPL": "AAPL.BA",
    "ARKK": "ARKK.BA",
    "IBB": "IBB.BA",
    "NVDA": "NVDA.BA",
}

HIDDEN_TICKERS = {"BTC"}


def _epoch(date_value):
    return int(date_value.replace(tzinfo=timezone.utc).timestamp())


def _fetch_yahoo_chart(symbol, start, end, interval="1d"):
    url = (
        "https://query1.finance.yahoo.com/v8/finance/chart/"
        f"{symbol}?period1={_epoch(start)}&period2={_epoch(end)}&interval={interval}"
    )
    yahoo_request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(yahoo_request, timeout=20) as response:
        payload = json.loads(response.read().decode("utf-8"))

    result = payload.get("chart", {}).get("result", [])
    if not result:
        return []

    data = result[0]
    timestamps = data.get("timestamp", [])
    closes = data.get("indicators", {}).get("quote", [{}])[0].get("close", [])
    points = []
    for timestamp, close in zip(timestamps, closes):
        if close is None:
            continue
        date = datetime.fromtimestamp(timestamp, tz=timezone.utc)
        points.append({"date": date, "price": float(close)})
    return points


def _range_to_dates(range_value):
    end = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=1)
    if range_value == "1":
        return end - timedelta(days=3), end, "5m"
    if range_value == "30":
        return end - timedelta(days=30), end, "1d"
    if range_value == "365":
        return end - timedelta(days=365), end, "1d"
    return datetime(2025, 1, 1), end, "1d"


def _latest_cedear_prices(tickers):
    end = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=1)
    start = end - timedelta(days=10)
    latest_prices = {}

    for ticker in tickers:
        yahoo_symbol = CEDEAR_SYMBOLS.get(ticker)
        if yahoo_symbol is None:
            continue

        try:
            points = _fetch_yahoo_chart(yahoo_symbol, start, end, "1d")
        except Exception:
            continue

        if not points:
            continue

        latest = points[-1]
        latest_prices[ticker] = {
            "fecha": latest["date"].strftime("%Y-%m-%d"),
            "precio": round(latest["price"], 2),
        }

    return latest_prices


def _aplicar_precios_actuales(cartera):
    if cartera.empty:
        return cartera

    cartera = cartera.copy()
    latest_prices = _latest_cedear_prices(cartera["ticker"].tolist())
    if not latest_prices:
        return cartera

    for index, row in cartera.iterrows():
        latest = latest_prices.get(row["ticker"])
        if latest is None:
            continue

        precio_actual = latest["precio"]
        monto_invertido = row["monto_invertido"]
        valor_actual = row["cantidad_actual"] * precio_actual
        resultado_pesos = valor_actual - monto_invertido

        cartera.at[index, "precio_actual"] = precio_actual
        cartera.at[index, "fecha_precio"] = latest["fecha"]
        cartera.at[index, "valor_actual"] = valor_actual
        cartera.at[index, "resultado_pesos"] = resultado_pesos
        cartera.at[index, "rentabilidad_total"] = (resultado_pesos / monto_invertido * 100) if monto_invertido else 0

    return cartera.sort_values("valor_actual", ascending=False)


def _filtrar_visibles(cartera):
    if cartera.empty:
        return cartera
    return cartera[~cartera["ticker"].isin(HIDDEN_TICKERS)].copy()


def _resumen_desde_cartera(cartera):
    if cartera.empty:
        return {
            "valor_total": 0,
            "invertido_total": 0,
            "resultado_total": 0,
            "rentabilidad_total": 0,
            "cantidad_activos": 0,
            "mejor_activo": "-",
            "peor_activo": "-",
        }

    valor_total = cartera["valor_actual"].sum()
    invertido_total = cartera["monto_invertido"].sum()
    resultado_total = valor_total - invertido_total
    rentabilidad_total = (resultado_total / invertido_total * 100) if invertido_total else 0
    mejor = cartera.sort_values("rentabilidad_total", ascending=False).iloc[0]
    peor = cartera.sort_values("rentabilidad_total", ascending=True).iloc[0]

    return {
        "valor_total": valor_total,
        "invertido_total": invertido_total,
        "resultado_total": resultado_total,
        "rentabilidad_total": rentabilidad_total,
        "cantidad_activos": len(cartera),
        "mejor_activo": mejor["ticker"],
        "peor_activo": peor["ticker"],
    }


def _composicion_desde_cartera(cartera):
    if cartera.empty:
        return []
    return cartera.groupby("tipo_activo", as_index=False).agg(valor=("valor_actual", "sum")).to_dict(orient="records")


def _evolucion_visible(tickers_visibles):
    operaciones = obtener_operaciones()
    precios = obtener_precios()
    if operaciones.empty or precios.empty or not tickers_visibles:
        return []

    operaciones = operaciones[operaciones["ticker"].isin(tickers_visibles)].copy()
    precios = precios[precios["ticker"].isin(tickers_visibles)].copy()
    if operaciones.empty or precios.empty:
        return []

    operaciones["fecha_operacion"] = pd.to_datetime(operaciones["fecha_operacion"])
    precios["fecha"] = pd.to_datetime(precios["fecha"])
    fechas = sorted(precios["fecha"].unique())

    serie = []
    for fecha in fechas:
        ops_hasta_fecha = operaciones[operaciones["fecha_operacion"] <= fecha].copy()
        if ops_hasta_fecha.empty:
            continue
        ops_hasta_fecha["cantidad_ajustada"] = ops_hasta_fecha.apply(
            lambda r: r["cantidad"] if r["operacion"].upper() in ["COMPRA", "SUSCRIPCION"] else -r["cantidad"],
            axis=1,
        )
        tenencias = ops_hasta_fecha.groupby("ticker", as_index=False).agg(cantidad=("cantidad_ajustada", "sum"))
        valor_total = 0
        for _, row in tenencias.iterrows():
            precios_hasta_fecha = precios[
                (precios["ticker"] == row["ticker"]) & (precios["fecha"] <= fecha)
            ].sort_values("fecha")
            if not precios_hasta_fecha.empty:
                valor_total += row["cantidad"] * float(precios_hasta_fecha.iloc[-1]["precio"])
        serie.append({"fecha": pd.to_datetime(fecha).strftime("%Y-%m-%d"), "valor": round(valor_total, 2)})
    return serie


@app.template_filter("money")
def money(value):
    try:
        return "$ {:,.2f}".format(float(value)).replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "-"


@app.template_filter("pct")
def pct(value):
    try:
        return "{:,.2f}%".format(float(value)).replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "-"


@app.route("/")
def index():
    cartera = _aplicar_precios_actuales(_filtrar_visibles(calcular_cartera_actual()))
    tickers_visibles = set(cartera["ticker"].tolist()) if not cartera.empty else set()
    resumen = _resumen_desde_cartera(cartera)
    evolucion = _evolucion_visible(tickers_visibles)
    composicion = _composicion_desde_cartera(cartera)
    return render_template(
        "index.html",
        cartera=cartera.to_dict(orient="records"),
        resumen=resumen,
        evolucion=evolucion,
        composicion=composicion,
    )


@app.route("/activo/<ticker>")
def activo(ticker):
    activo_data, historial = detalle_activo(ticker)
    return render_template("activo_detalle.html", activo=activo_data, historial=historial, ticker=ticker.upper())


@app.route("/api/cedear/<ticker>/chart")
def cedear_chart(ticker):
    ticker = ticker.upper()
    yahoo_symbol = CEDEAR_SYMBOLS.get(ticker)
    if yahoo_symbol is None:
        return jsonify({"error": f"No hay simbolo CEDEAR configurado para {ticker}"}), 404

    range_value = request.args.get("range", "30")
    if range_value not in {"1", "30", "365", "max"}:
        range_value = "30"

    try:
        start, end, interval = _range_to_dates(range_value)
        cedear_points = _fetch_yahoo_chart(yahoo_symbol, start, end, interval)
        if not cedear_points:
            return jsonify({"error": f"Yahoo Finance no devolvio precios de {yahoo_symbol}"}), 502

        prices = [
            [int(point["date"].timestamp() * 1000), round(point["price"], 2)]
            for point in cedear_points
        ]

        if not prices:
            return jsonify({"error": f"No se pudo obtener {yahoo_symbol} en ARS"}), 502

        return jsonify({"ticker": yahoo_symbol, "currency": "ARS", "prices": prices})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 502


@app.route("/api/nvda/chart")
def nvda_chart():
    return cedear_chart("NVDA")


if __name__ == "__main__":
    app.run(debug=True)
