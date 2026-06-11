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


def _latest_fx_rate(end):
    start = end - timedelta(days=14)
    fx_points = _fetch_yahoo_chart("ARS=X", start, end, "1d")
    if not fx_points:
        raise ValueError("No se pudo obtener USD/ARS")
    return fx_points[-1]["price"]


def _daily_fx_by_date(start, end):
    fx_points = _fetch_yahoo_chart("ARS=X", start - timedelta(days=10), end, "1d")
    rates = {}
    latest = None
    for point in fx_points:
        latest = point["price"]
        rates[point["date"].strftime("%Y-%m-%d")] = latest
    return rates, latest


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


@app.route("/api/nvda/chart")
def nvda_chart():
    range_value = request.args.get("range", "30")
    if range_value not in {"1", "30", "365", "max"}:
        range_value = "30"

    try:
        start, end, interval = _range_to_dates(range_value)
        nvda_points = _fetch_yahoo_chart("NVDA", start, end, interval)
        if not nvda_points:
            return jsonify({"error": "Yahoo Finance no devolvio precios de NVDA"}), 502

        prices = []
        if interval == "5m":
            fx_rate = _latest_fx_rate(end)
            prices = [
                [int(point["date"].timestamp() * 1000), round(point["price"] * fx_rate, 2)]
                for point in nvda_points
            ]
        else:
            fx_by_date, fallback_fx = _daily_fx_by_date(start, end)
            last_fx = fallback_fx
            for point in nvda_points:
                date_key = point["date"].strftime("%Y-%m-%d")
                last_fx = fx_by_date.get(date_key, last_fx)
                if last_fx is None:
                    continue
                prices.append([int(point["date"].timestamp() * 1000), round(point["price"] * last_fx, 2)])

        if not prices:
            return jsonify({"error": "No se pudo convertir NVDA a ARS"}), 502

        return jsonify({"ticker": "NVDA", "currency": "ARS", "prices": prices})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 502


if __name__ == "__main__":
    app.run(debug=True)
