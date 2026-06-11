import hashlib
import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd

try:
    from api_bitcoin import obtener_precio_bitcoin_coingecko
except Exception:
    obtener_precio_bitcoin_coingecko = None

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "inversiones.db"
CARPETA_PRECIOS = BASE_DIR / "data" / "precios"


def crear_hash_precio(row):
    texto = "|".join([
        str(row["fecha"]),
        str(row["ticker"]),
        str(row["precio"]),
        str(row["moneda"]),
        str(row.get("fuente", "")),
    ])
    return hashlib.md5(texto.encode("utf-8")).hexdigest()


def crear_tabla_precios():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS precios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT NOT NULL,
            ticker TEXT NOT NULL,
            precio REAL NOT NULL,
            moneda TEXT DEFAULT 'ARS',
            fuente TEXT,
            archivo_origen TEXT,
            hash_precio TEXT UNIQUE,
            fecha_ingesta TEXT
        )
    """)
    conn.commit()
    conn.close()


def leer_archivo(ruta):
    if ruta.suffix.lower() == ".csv":
        return pd.read_csv(ruta)
    if ruta.suffix.lower() in [".xlsx", ".xls"]:
        return pd.read_excel(ruta)
    return None


def normalizar_precios(df, archivo_origen):
    columnas_requeridas = ["fecha", "ticker", "precio"]
    faltantes = [c for c in columnas_requeridas if c not in df.columns]
    if faltantes:
        raise ValueError(f"Faltan columnas en {archivo_origen}: {faltantes}")

    out = pd.DataFrame()
    out["fecha"] = pd.to_datetime(df["fecha"]).dt.strftime("%Y-%m-%d")
    out["ticker"] = df["ticker"].astype(str).str.upper().str.strip()
    out["precio"] = df["precio"].astype(float)
    out["moneda"] = df.get("moneda", "ARS")
    out["fuente"] = df.get("fuente", "CSV")
    out["archivo_origen"] = archivo_origen
    out["fecha_ingesta"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    out["hash_precio"] = out.apply(crear_hash_precio, axis=1)
    return out


def insertar_precios(df):
    conn = sqlite3.connect(DB_PATH)
    insertados = 0
    for _, row in df.iterrows():
        try:
            row.to_frame().T.to_sql("precios", conn, if_exists="append", index=False)
            insertados += 1
        except sqlite3.IntegrityError:
            pass
    conn.close()
    return insertados


def ingestar_precios():
    crear_tabla_precios()
    CARPETA_PRECIOS.mkdir(parents=True, exist_ok=True)
    total = 0

    # 1) Ingesta desde archivos CSV / Excel
    for archivo in CARPETA_PRECIOS.iterdir():
        if archivo.suffix.lower() not in [".csv", ".xlsx", ".xls"]:
            continue
        df = leer_archivo(archivo)
        if df is None:
            continue
        normalizado = normalizar_precios(df, archivo.name)
        insertados = insertar_precios(normalizado)
        print(f"{archivo.name}: {insertados} precios nuevos")
        total += insertados

    # 2) Ingesta automática de Bitcoin desde CoinGecko
    if obtener_precio_bitcoin_coingecko is not None:
        try:
            df_btc = obtener_precio_bitcoin_coingecko()
            df_btc["archivo_origen"] = "api_bitcoin.py"
            df_btc["fecha_ingesta"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            df_btc["hash_precio"] = df_btc.apply(crear_hash_precio, axis=1)
            insertados_btc = insertar_precios(df_btc)
            print(f"CoinGecko BTC: {insertados_btc} precios nuevos")
            total += insertados_btc
        except Exception as e:
            print(f"No se pudo actualizar BTC desde CoinGecko: {e}")

    print(f"Total precios nuevos: {total}")
    return total


if __name__ == "__main__":
    ingestar_precios()
