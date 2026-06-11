import sqlite3
from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "inversiones.db"


def _empty_cartera():
    return pd.DataFrame(columns=[
        "ticker", "nombre", "tipo_activo", "cantidad_actual", "monto_invertido",
        "precio_promedio", "precio_actual", "fecha_precio", "valor_actual",
        "resultado_pesos", "rentabilidad_total", "rent_1d", "rent_7d", "rent_30d"
    ])


def obtener_operaciones():
    conn = sqlite3.connect(DB_PATH)
    try:
        df = pd.read_sql_query("SELECT * FROM operaciones", conn)
    except Exception:
        df = pd.DataFrame()
    conn.close()
    return df


def obtener_precios():
    conn = sqlite3.connect(DB_PATH)
    try:
        df = pd.read_sql_query("SELECT * FROM precios", conn)
    except Exception:
        df = pd.DataFrame()
    conn.close()
    return df


def obtener_ultimos_precios():
    precios = obtener_precios()
    if precios.empty:
        return pd.DataFrame(columns=["ticker", "fecha", "precio"])
    precios["fecha"] = pd.to_datetime(precios["fecha"])
    precios = precios.sort_values(["ticker", "fecha"])
    ultimos = precios.groupby("ticker", as_index=False).tail(1)
    ultimos["fecha"] = ultimos["fecha"].dt.strftime("%Y-%m-%d")
    return ultimos[["ticker", "fecha", "precio"]]


def precio_en_periodo(precios, ticker, fecha_objetivo):
    datos = precios[(precios["ticker"] == ticker) & (precios["fecha"] <= fecha_objetivo)].sort_values("fecha")
    if datos.empty:
        return None
    return float(datos.iloc[-1]["precio"])


def calcular_rentabilidad_periodos(row, precios):
    if precios.empty or pd.isna(row["precio_actual"]):
        return pd.Series({"rent_1d": None, "rent_7d": None, "rent_30d": None})

    ticker = row["ticker"]
    precio_actual = row["precio_actual"]
    fecha_actual = pd.to_datetime(row["fecha_precio"])

    resultados = {}
    for dias, nombre in [(1, "rent_1d"), (7, "rent_7d"), (30, "rent_30d")]:
        fecha_base = fecha_actual - pd.Timedelta(days=dias)
        precio_base = precio_en_periodo(precios, ticker, fecha_base)
        if precio_base and precio_base != 0:
            resultados[nombre] = ((precio_actual / precio_base) - 1) * 100
        else:
            resultados[nombre] = None
    return pd.Series(resultados)


def calcular_cartera_actual():
    operaciones = obtener_operaciones()
    precios = obtener_precios()
    ultimos = obtener_ultimos_precios()

    if operaciones.empty:
        return _empty_cartera()

    operaciones["operacion"] = operaciones["operacion"].str.upper()
    operaciones["cantidad_ajustada"] = operaciones.apply(
        lambda r: r["cantidad"] if r["operacion"] in ["COMPRA", "SUSCRIPCION"] else -r["cantidad"], axis=1
    )
    operaciones["monto_ajustado"] = operaciones.apply(
        lambda r: r["monto_total"] if r["operacion"] in ["COMPRA", "SUSCRIPCION"] else -r["monto_total"], axis=1
    )

    cartera = operaciones.groupby(["ticker", "nombre", "tipo_activo"], as_index=False).agg(
        cantidad_actual=("cantidad_ajustada", "sum"),
        monto_invertido=("monto_ajustado", "sum"),
        fecha_primera_compra=("fecha_operacion", "min")
    )

    cartera = cartera[cartera["cantidad_actual"].abs() > 0.000001]
    cartera["precio_promedio"] = cartera["monto_invertido"] / cartera["cantidad_actual"]

    cartera = cartera.merge(ultimos, on="ticker", how="left")
    cartera = cartera.rename(columns={"precio": "precio_actual", "fecha": "fecha_precio"})
    cartera["valor_actual"] = cartera["cantidad_actual"] * cartera["precio_actual"]
    cartera["resultado_pesos"] = cartera["valor_actual"] - cartera["monto_invertido"]
    cartera["rentabilidad_total"] = cartera["resultado_pesos"] / cartera["monto_invertido"] * 100

    if not precios.empty:
        precios["fecha"] = pd.to_datetime(precios["fecha"])
        rent_periodos = cartera.apply(lambda row: calcular_rentabilidad_periodos(row, precios), axis=1)
        cartera = pd.concat([cartera, rent_periodos], axis=1)
    else:
        cartera["rent_1d"] = None
        cartera["rent_7d"] = None
        cartera["rent_30d"] = None

    return cartera.sort_values("valor_actual", ascending=False)


def obtener_resumen():
    cartera = calcular_cartera_actual()
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


def evolucion_valor_cartera():
    operaciones = obtener_operaciones()
    precios = obtener_precios()
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
            lambda r: r["cantidad"] if r["operacion"].upper() in ["COMPRA", "SUSCRIPCION"] else -r["cantidad"], axis=1
        )
        tenencias = ops_hasta_fecha.groupby("ticker", as_index=False).agg(cantidad=("cantidad_ajustada", "sum"))
        valor_total = 0
        for _, row in tenencias.iterrows():
            p = precios[(precios["ticker"] == row["ticker"]) & (precios["fecha"] <= fecha)].sort_values("fecha")
            if not p.empty:
                valor_total += row["cantidad"] * float(p.iloc[-1]["precio"])
        serie.append({"fecha": pd.to_datetime(fecha).strftime("%Y-%m-%d"), "valor": round(valor_total, 2)})
    return serie


def composicion_por_tipo():
    cartera = calcular_cartera_actual()
    if cartera.empty:
        return []
    comp = cartera.groupby("tipo_activo", as_index=False).agg(valor=("valor_actual", "sum"))
    return comp.to_dict(orient="records")


def detalle_activo(ticker):
    cartera = calcular_cartera_actual()
    precios = obtener_precios()
    activo = cartera[cartera["ticker"] == ticker.upper()]
    if activo.empty:
        return None, []
    historial = precios[precios["ticker"] == ticker.upper()].sort_values("fecha")
    return activo.iloc[0].to_dict(), historial.to_dict(orient="records")
