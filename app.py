from datetime import datetime, timedelta, timezone
import json
import urllib.request

from flask import Flask, jsonify, render_template, request

from services.cartera import (
    calcular_cartera_actual,
    composicion_por_tipo,
    detalle_activo,
    evolucion_valor_cartera,
    obtener_resumen,
)

app = Flask(__name__)

CEDEAR_SYMBOLS = {
    "AAPL": "AAPL.BA",
    "NVDA": "NVDA.BA",
}


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
    cartera = calcular_cartera_actual()
    resumen = obtener_resumen()
    evolucion = evolucion_valor_cartera()
    composicion = composicion_por_tipo()
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
